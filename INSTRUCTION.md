## GOAL

Build a local PoC system to demonstrate secure identity and access control for an LLM agent that performs RAG (Retrieval-Augmented Generation) using:

- ChromaDB (vector database)
- MinIO (object storage)
- Cerbos (policy engine)
- HashiCorp Vault (for JIT access token issuance)
- SPIRE (for workload identity via mTLS and SPIFFE ID)
- Envoy Proxy (as auth gateway)

---

## REQUIREMENTS

### 1. Identity Layer (SPIRE)
- Deploy SPIRE server and agent (dockerized)
- Configure one agent workload:
  - SPIFFE ID: `spiffe://rag-app.local/sa/rag-agent`
  - Selector: match binary name or container label

### 2. Token Issuance Layer (Vault)
- Configure Vault to authenticate workloads using SPIFFE x.509 certificates (mTLS)
- Use Vault `jwt` auth or `cert` auth method to issue short-lived JWTs (5–10 minutes)
- JWT should contain claims:
  - `sub`, `spiffe_id`, `role`

### 3. Policy Engine (Cerbos)
- Run Cerbos PDP server
- Create two resource policies:
  - `minio-object`: allow GET on bucket `public-contracts` for `retriever` role
  - `vector-collection`: allow `search` on collection `legal-docs` for `retriever` role

### 4. Auth Gateway (Envoy)
- Envoy should:
  - Validate JWT from Vault
  - Use `ext_authz` filter to query Cerbos with token-derived identity + resource + action
  - Forward request to backend only if Cerbos allows

### 5. Backend Services
- Launch ChromaDB with sample embedding collection
- Launch MinIO with sample document bucket
- Each service should be behind Envoy proxy (all traffic goes through auth gateway)

### 6. LLM Agent (FastAPI Service)
- Build a FastAPI service that:
  - Exposes a `/chat` endpoint for RAG workflow
  - Uses spiffe and spiffe-tls SDKs to communicate with SPIRE agent
  - Uses hvac SDK to communicate with Vault for JWT retrieval
  - Uses chromadb SDK to query ChromaDB for vector retrieval
  - Uses boto3 SDK to download files from MinIO
  - Uses OpenAI SDK to generate embeddings and LLM responses
  - Combines content for RAG prompt generation and returns response to user

---

## OUTPUTS
- Docker Compose file to orchestrate all components
- SPIRE config for workloads
- Vault policy + role setup scripts
- Cerbos policy files
- Envoy config with JWT validation + ext_authz
- FastAPI service for LLM agent with RAG workflow and /chat endpoint
- Readme file with setup + run instructions

---

## CONSTRAINTS
- All communication between agent and Vault must use mTLS (client cert)
- JWTs must be validated with public key and contain proper expiration
- No hardcoded API keys or static credentials
- Every decision must be logged and auditable
