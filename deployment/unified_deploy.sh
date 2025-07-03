#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

# --- Configuration Variables ---
# Project and App Identifiers (Update these if they change)
PROJECT_ID="jose-genai-demos"
LOCATION="us-central1"
BUCKET_NAME="${PROJECT_ID}-adk-staging"
APP_ID="agentspace-demo_1747752211490" # From create_new_agent.sh

# Agent Details from create_new_agent.sh
AGENT_DISPLAY_NAME="Agente de Consulta Unificado"
AGENT_DESCRIPTION="Agente unificado para exploração de dados."
AGENT_ICON_URI="https://fonts.gstatic.com/s/i/short-term/release/googlesymbols/smart_toy/default/24px.svg"
TOOL_DESCRIPTION="Agente utilizado para exploração de dados que pode fazer queries e gerar gráficos"

# --- Step 1: Deploy the Reasoning Engine using deploy.py ---
echo "--- Step 1: Deploying Reasoning Engine ---"

# Execute the Python script and capture its full output.
# The 'tee' command allows us to see the output in the terminal while also capturing it.
DEPLOY_OUTPUT=$(python3 deployment/deploy.py --create --project_id="${PROJECT_ID}" --location="${LOCATION}" --bucket="${BUCKET_NAME}" | tee /dev/tty)

# Extract the Reasoning Engine resource name from the output.
# It looks for the line starting with "Successfully created agent: " and extracts the resource name.
REASONING_ENGINE=$(echo "${DEPLOY_OUTPUT}" | grep "Successfully created agent:" | awk '{print $4}')

# --- Validation ---
if [ -z "$REASONING_ENGINE" ]; then
  echo "Error: Could not find Reasoning Engine resource name in the output."
  echo "Deployment failed."
  exit 1
fi

echo ""
echo "--- Successfully extracted Reasoning Engine ---"
echo "REASONING_ENGINE: ${REASONING_ENGINE}"
echo ""


# --- Step 2: Create the Agent in Agent Space using the new Reasoning Engine ---
echo "--- Step 2: Creating Agent in Agent Space ---"

# Derived Variables for the curl command
ACCESS_TOKEN=$(gcloud auth print-access-token)
API_ENDPOINT="https://discoveryengine.googleapis.com/v1alpha/projects/${PROJECT_ID}/locations/global/collections/default_collection/engines/${APP_ID}/assistants/default_assistant/agents"

# JSON Payload using a here-document for readability
# The ADK_REASONING_ENGINE_PATH is now dynamically set from the output of deploy.py
read -r -d '' JSON_PAYLOAD <<EOF
{
  "displayName": "${AGENT_DISPLAY_NAME}",
  "description": "${AGENT_DESCRIPTION}",
  "icon": {
    "uri": "${AGENT_ICON_URI}"
  },
  "adk_agent_definition": {
    "tool_settings": {
      "tool_description": "${TOOL_DESCRIPTION}"
    },
    "provisioned_reasoning_engine": {
      "reasoning_engine": "${REASONING_ENGINE}"
    },
    "authorizations": []
  }
}
EOF

# Execute Curl Command
echo "Attempting to create agent: ${AGENT_DISPLAY_NAME}..."
echo "Endpoint: ${API_ENDPOINT}"
# echo "Payload: ${JSON_PAYLOAD}" # Uncomment for debugging

curl -X POST \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  -H "X-Goog-User-Project: ${PROJECT_ID}" \
  "${API_ENDPOINT}" \
  -d "${JSON_PAYLOAD}" \
  --fail # Exit with an error code if the server returns an error

# --- Final Status ---
if [ $? -eq 0 ]; then
  echo ""
  echo "--- Unified deployment completed successfully! ---"
else
  echo ""
  echo "--- Agent creation command failed. Check the output above for errors. ---"
  exit 1
fi

echo "Script finished."
