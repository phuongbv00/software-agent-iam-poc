import logging
import os
import time

import boto3
import chromadb
import hvac
import openai
import uvicorn
from botocore.client import Config
from cryptography.hazmat.primitives import serialization
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constants
SPIFFE_SOCKET = "/tmp/spire-agent/public/api.sock"
VAULT_ADDR = "http://vault:8200"
ENVOY_ADDR = "http://envoy:9090"
ROLE = "retriever"
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

# Initialize OpenAI client
openai_client = openai.OpenAI(api_key=OPENAI_API_KEY)

# Initialize FastAPI app
app = FastAPI(title="RAG Agent API", description="API for RAG workflow with secure identity and access control")


# Pydantic models for request/response
class ChatRequest(BaseModel):
    query: str


class ChatResponse(BaseModel):
    response: str


def get_spiffe_x509_svid():
    """Get a SPIFFE JWT from the SPIRE agent using spiffe and spiffe-tls SDKs."""
    logger.info("Getting SPIFFE JWT from SPIRE agent using spiffe and spiffe-tls SDKs")

    try:
        # Initialize the workload API client
        from spiffe import WorkloadApiClient, X509Source

        # Create a workload API client with the socket path
        with WorkloadApiClient(SPIFFE_SOCKET) as client:
            x509_svid = client.fetch_x509_svid()
            x509_svid.save("/tmp/cert.pem", "/tmp/key.pem", serialization.Encoding.PEM)

        logger.info("SPIFFE certificate and key saved to temporary files")
        return "/tmp/cert.pem", "/tmp/key.pem"
    except Exception as e:
        logger.error(f"Error getting SPIFFE JWT: {str(e)}")
        raise


def get_vault_token(cert_path, key_path):
    """Get a token from Vault using mTLS with SPIFFE certificate using hvac SDK."""
    logger.info("Getting token from Vault using mTLS with hvac SDK")

    try:
        # Create a Vault client with cert auth
        client = hvac.Client(
            url=VAULT_ADDR,
            cert=(cert_path, key_path),
            verify=False
        )

        # Login using cert auth
        auth_response = client.auth.cert.login()

        # Extract client token
        client_token = auth_response['auth']['client_token']
        logger.info("Successfully obtained Vault token using hvac SDK")

        return client_token
    except Exception as e:
        logger.error(f"Failed to login to Vault: {str(e)}")
        raise


def get_jwt_from_vault(vault_token):
    """Get a JWT from Vault using the client token with hvac SDK."""
    logger.info("Getting JWT from Vault using hvac SDK")

    try:
        # Create a Vault client with the token
        client = hvac.Client(
            url=VAULT_ADDR,
            token=vault_token,
            verify=False
        )

        # Create JWT with claims
        payload = {
            "role": ROLE,
            "spiffe_id": "spiffe://rag-app.local/sa/rag-agent"
        }

        # Use the JWT auth method to create a token
        response = client.auth.jwt.create_token(
            role="rag-agent",
            jwt=None,  # Not providing a JWT as we're creating one
            meta=payload
        )

        # Extract JWT
        jwt = response["auth"]["client_token"]
        logger.info("Successfully obtained JWT from Vault using hvac SDK")

        return jwt
    except Exception as e:
        logger.error(f"Failed to get JWT from Vault: {str(e)}")
        raise


def query_chromadb(jwt):
    """Query ChromaDB to retrieve vectors using chromadb SDK."""
    logger.info("Querying ChromaDB using chromadb SDK")

    try:
        # Initialize ChromaDB client
        client = chromadb.HttpClient(
            host="chromadb",
            port=8000,
            headers={"Authorization": f"Bearer {jwt}"}
        )

        # Get the collection
        collection = client.get_collection(name="legal-docs")

        # Query the collection
        results = collection.query(
            query_texts=["contract terms and conditions"],
            n_results=5
        )

        logger.info(f"Successfully queried ChromaDB using SDK: {results}")
        return results
    except Exception as e:
        logger.error(f"Failed to query ChromaDB: {str(e)}")
        raise


def download_from_minio(jwt, bucket, object_name):
    """Download a file from MinIO using boto3 SDK."""
    logger.info(f"Downloading {object_name} from MinIO bucket {bucket} using boto3 SDK")

    try:
        # Initialize MinIO client using boto3 (S3 compatible)
        s3_client = boto3.client(
            's3',
            endpoint_url='http://minio:9000',
            aws_access_key_id='minioadmin',  # These should be retrieved securely
            aws_secret_access_key='minioadmin',  # These should be retrieved securely
            config=Config(signature_version='s3v4'),
            verify=False
        )

        # Create a temporary file to store the downloaded object
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_path = temp_file.name

        # Download the file
        s3_client.download_file(bucket, object_name, temp_path)

        # Read the file content
        with open(temp_path, 'rb') as f:
            content = f.read()

        # Clean up the temporary file
        import os
        os.unlink(temp_path)

        logger.info(f"Successfully downloaded {len(content)} bytes from MinIO using boto3 SDK")
        return content
    except Exception as e:
        logger.error(f"Failed to download from MinIO: {str(e)}")
        raise


def query_chromadb_with_user_query(jwt, user_query):
    """Query ChromaDB to retrieve vectors based on user query using chromadb SDK."""
    logger.info(f"Querying ChromaDB with user query using chromadb SDK: {user_query}")

    try:
        # Initialize ChromaDB client
        client = chromadb.HttpClient(
            host="chromadb",
            port=8000,
            headers={"Authorization": f"Bearer {jwt}"}
        )

        # Get the collection
        collection = client.get_collection(name="legal-docs")

        # Query the collection with user query
        results = collection.query(
            query_texts=[user_query],
            n_results=5
        )

        logger.info(f"Successfully queried ChromaDB with user query using SDK: {results}")
        return results
    except Exception as e:
        logger.error(f"Failed to query ChromaDB with user query: {str(e)}")
        raise


def generate_embedding(text):
    """Generate embedding for text using OpenAI API."""
    try:
        response = openai_client.embeddings.create(
            model="text-embedding-ada-002",
            input=text
        )
        return response.data[0].embedding
    except Exception as e:
        logger.error(f"Error generating embedding: {str(e)}")
        raise


def generate_llm_response(prompt):
    """Generate response using OpenAI API."""
    try:
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system",
                 "content": "You are a helpful assistant that provides information based on retrieved documents."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1000
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Error generating LLM response: {str(e)}")
        raise


def perform_rag_workflow(user_query):
    """Perform the RAG workflow with user query."""
    try:
        # Get SPIFFE certificate and key
        cert_path, key_path = get_spiffe_x509_svid()

        # Get Vault token using mTLS
        vault_token = get_vault_token(cert_path, key_path)

        # Get JWT from Vault
        jwt = get_jwt_from_vault(vault_token)

        # Query ChromaDB with user query
        vector_results = query_chromadb_with_user_query(jwt, user_query)

        # Download file from MinIO
        document_content = download_from_minio(jwt, "public-contracts", "sample-contract.pdf")

        # Generate RAG prompt
        logger.info("Generating RAG prompt")
        prompt = f"""
        Based on the retrieved vector results and the document content, 
        generate a response to the user's query: {user_query}

        Vector Results: {vector_results}

        Document Content: {document_content[:1000]}...
        """

        # Generate response using OpenAI
        logger.info("Generating response using OpenAI")
        response = generate_llm_response(prompt)

        return response
    except Exception as e:
        logger.error(f"Error in RAG workflow: {str(e)}")
        raise


@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """
    Chat endpoint that triggers the RAG workflow.

    Args:
        request: ChatRequest object containing the user query

    Returns:
        ChatResponse object containing the generated response
    """
    try:
        logger.info(f"Received chat request with query: {request.query}")
        response = perform_rag_workflow(request.query)
        return ChatResponse(response=response)
    except Exception as e:
        logger.error(f"Error processing chat request: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    # Wait for services to be ready
    time.sleep(30)

    # Run the FastAPI app
    logger.info("Starting FastAPI app")
    uvicorn.run(app, host="0.0.0.0", port=8000)
