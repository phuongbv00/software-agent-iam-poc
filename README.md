# Software Agent IAM PoC
This repository contains a Proof of Concept (PoC) system demonstrating secure identity and access control for an LLM agent that performs RAG (Retrieval-Augmented Generation) using various security components.

## Architecture

The system consists of the following components:

1. **SPIRE** - For workload identity via mTLS and SPIFFE ID
2. **HashiCorp Vault** - For JIT access token issuance
3. **Cerbos** - For policy-based access control
4. **Envoy Proxy** - As an auth gateway
5. **ChromaDB** - Vector database for embeddings
6. **MinIO** - Object storage for documents
7. **RAG Agent** - Python client that simulates an LLM agent with RAG workflow

## Security Flow

1. The RAG agent obtains a SPIFFE certificate from the SPIRE agent
2. The agent authenticates to Vault using mTLS with the SPIFFE certificate
3. Vault issues a short-lived JWT with claims (sub, spiffe_id, role)
4. The agent uses the JWT to access backend services via Envoy
5. Envoy validates the JWT and queries Cerbos for authorization
6. If authorized, Envoy forwards the request to the backend service
7. The agent retrieves vectors from ChromaDB and documents from MinIO
8. The agent combines the data to simulate RAG prompt generation

## Prerequisites

- Docker and Docker Compose
- At least 4GB of RAM available for Docker

## Setup and Run

1. Clone this repository:
   ```
   git clone <repository-url>
   cd <repository-directory>
   ```

2. Start the services:
   ```
   docker-compose up -d
   ```

3. Monitor the logs:
   ```
   docker-compose logs -f rag-agent
   ```

4. To shut down:
   ```
   docker-compose down
   ```

## Components Details

### SPIRE

SPIRE provides workload identity through SPIFFE IDs and X.509 SVIDs. The RAG agent is assigned the SPIFFE ID `spiffe://rag-app.local/sa/rag-agent`.

### Vault

Vault authenticates workloads using SPIFFE certificates and issues short-lived JWTs (10 minutes) with claims for identity and authorization.

### Cerbos

Cerbos enforces access control policies:
- `minio-object`: Allows GET on bucket `public-contracts` for `retriever` role
- `vector-collection`: Allows search on collection `legal-docs` for `retriever` role

### Envoy

Envoy acts as an auth gateway that:
- Validates JWTs from Vault
- Queries Cerbos for authorization decisions
- Forwards requests to backend services if authorized

### ChromaDB and MinIO

These services provide the backend functionality for the RAG workflow:
- ChromaDB stores vector embeddings for semantic search
- MinIO stores the actual documents

### RAG Agent

The Python client that:
- Authenticates using SPIFFE and Vault
- Retrieves data from ChromaDB and MinIO
- Simulates RAG prompt generation

## Security Constraints

- All communication between agent and Vault uses mTLS (client cert)
- JWTs are validated with public key and contain proper expiration
- No hardcoded API keys or static credentials
- Every decision is logged and auditable

## Troubleshooting

If you encounter issues:

1. Check the logs for each service:
   ```
   docker-compose logs <service-name>
   ```

2. Ensure all services are running:
   ```
   docker-compose ps
   ```

3. Verify network connectivity between containers:
   ```
   docker-compose exec <service-name> ping <other-service-name>
   ```