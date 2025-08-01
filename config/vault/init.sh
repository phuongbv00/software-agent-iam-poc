#!/bin/bash
set -e

# Wait for Vault to start
sleep 5

# Check if Vault is initialized
INITIALIZED=$(vault status -format=json | jq -r '.initialized')

if [ "$INITIALIZED" = "false" ]; then
  echo "Initializing Vault..."
  vault operator init -key-shares=1 -key-threshold=1 -format=json > /vault/config/init.json
  
  # Extract root token and unseal key
  VAULT_TOKEN=$(cat /vault/config/init.json | jq -r '.root_token')
  UNSEAL_KEY=$(cat /vault/config/init.json | jq -r '.unseal_keys_b64[0]')
  
  # Save token and key to files for later use
  echo "$VAULT_TOKEN" > /vault/config/root-token
  echo "$UNSEAL_KEY" > /vault/config/unseal-key
else
  echo "Vault already initialized"
  VAULT_TOKEN=$(cat /vault/config/root-token)
  UNSEAL_KEY=$(cat /vault/config/unseal-key)
fi

# Check if Vault is sealed
SEALED=$(vault status -format=json | jq -r '.sealed')

if [ "$SEALED" = "true" ]; then
  echo "Unsealing Vault..."
  vault operator unseal "$UNSEAL_KEY"
else
  echo "Vault already unsealed"
fi

# Login with root token
vault login "$VAULT_TOKEN"

# Enable JWT auth method for issuing JWTs
echo "Enabling JWT auth method..."
vault auth enable jwt || echo "JWT auth already enabled"

# Create a policy for the RAG agent
echo "Creating policy for RAG agent..."
cat > /tmp/rag-agent-policy.hcl << EOF
# Allow RAG agent to access MinIO and ChromaDB
path "auth/token/create" {
  capabilities = ["create", "read", "update"]
}
EOF

vault policy write rag-agent /tmp/rag-agent-policy.hcl

# Enable cert auth method for SPIFFE authentication
echo "Enabling cert auth method..."
vault auth enable cert || echo "Cert auth already enabled"

# Configure cert auth method with SPIFFE trust domain
echo "Configuring cert auth method..."
vault write auth/cert/certs/spire \
  certificate=@/vault/config/spire-ca.pem \
  allowed_common_names="*" \
  allowed_uri_sans="spiffe://rag-app.local/sa/rag-agent" \
  token_policies="rag-agent" \
  token_ttl=10m \
  token_max_ttl=30m

# Create a role for JWT issuance
echo "Creating JWT role..."
vault write auth/jwt/config \
  jwks_url="http://vault:8200/v1/identity/oidc/.well-known/keys" \
  jwt_supported_algs="RS256" \
  default_role="rag-agent"

vault write auth/jwt/role/rag-agent \
  role_type="jwt" \
  token_ttl="10m" \
  token_max_ttl="30m" \
  bound_audiences="rag-app" \
  user_claim="sub" \
  claim_mappings=spiffe_id=spiffe_id \
  claim_mappings=role=role \
  token_policies="rag-agent"

echo "Vault setup complete!"