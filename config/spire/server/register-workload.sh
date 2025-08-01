#!/bin/bash
set -e

# Wait for the SPIRE server to be ready
sleep 10

# Create a join token for the SPIRE agent
JOIN_TOKEN=$(/opt/spire/bin/spire-server token generate -spiffeID spiffe://rag-app.local/agent | awk '{print $2}')
echo "Generated join token: $JOIN_TOKEN"

# Create a registration entry for the RAG agent workload
/opt/spire/bin/spire-server entry create \
    -parentID spiffe://rag-app.local/agent \
    -spiffeID spiffe://rag-app.local/sa/rag-agent \
    -selector docker:label:app:rag-agent \
    -ttl 3600

echo "Registration entry created for RAG agent"

# Keep the script running to maintain the container
tail -f /dev/null