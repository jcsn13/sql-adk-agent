#!/bin/bash

# This script expects the following environment variables to be set by the caller (e.g., Cloud Build):
# PROJECT_ID
# APP_ID
# AGENT_DISPLAY_NAME
# AGENT_ICON_URI
# TOOL_DESCRIPTION
# AUTH_PATH (optional, used if authorizations are needed)
# ADK_REASONING_ENGINE_PATH (path to the deployed reasoning engine)

# --- Log received environment variables for debugging ---
echo "--- Environment Variables Received by Script ---"
echo "PROJECT_ID: ${PROJECT_ID}"
echo "APP_ID: ${APP_ID}"
echo "AGENT_DISPLAY_NAME: ${AGENT_DISPLAY_NAME}"
echo "AGENT_ICON_URI: ${AGENT_ICON_URI}"
echo "TOOL_DESCRIPTION (for agent and tool): ${TOOL_DESCRIPTION}"
echo "AUTH_PATH: ${AUTH_PATH}"
echo "ADK_REASONING_ENGINE_PATH: ${ADK_REASONING_ENGINE_PATH}"
echo "------------------------------------------------"

# --- Derived Variables ---
ACCESS_TOKEN=$(gcloud auth print-access-token)
API_ENDPOINT="https://discoveryengine.googleapis.com/v1alpha/projects/${PROJECT_ID}/locations/global/collections/default_collection/engines/${APP_ID}/assistants/default_assistant/agents"

# --- JSON Payload ---
# Using a here-document for readability.
# Variables are directly expanded from the environment.
read -r -d '' JSON_PAYLOAD <<EOF
{
  "displayName": "${AGENT_DISPLAY_NAME}",
  "description": "${TOOL_DESCRIPTION}",
  "icon": {
    "uri": "${AGENT_ICON_URI}"
  },
  "adk_agent_definition": {
    "tool_settings": {
      "tool_description": "${TOOL_DESCRIPTION}"
    },
    "provisioned_reasoning_engine": {
      "reasoning_engine": "${ADK_REASONING_ENGINE_PATH}"
    },
    "authorizations": [
    ]
  }
}
EOF

# --- Execute Curl Command ---
echo "Attempting to create agent: ${AGENT_DISPLAY_NAME}..."
echo "Endpoint: ${API_ENDPOINT}"
echo "Processed Payload: ${JSON_PAYLOAD}"

curl -X POST -v \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  -H "X-Goog-User-Project: ${PROJECT_ID}" \
  "${API_ENDPOINT}" \
  -d "${JSON_PAYLOAD}" \
  --fail

# --- Basic Error Handling ---
if [ $? -eq 0 ]; then
  echo "Agent creation command executed successfully."
else
  echo "Agent creation command failed. Exit code: $?"
fi

echo "Script finished."
