# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Undeployment script for SQL Agent from Google Cloud Agent Engine and AgentSpace.

This script:
1. Removes the agent from AgentSpace
2. Deletes OAuth authorization from AgentSpace
3. Deletes the agent from Vertex AI Agent Engine
4. Cleans up deployment state

Usage:
    python deployment/undeploy.py
"""

import os
import sys
import json
import logging
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional

import requests
from dotenv import load_dotenv
import vertexai
from vertexai import agent_engines
from google.api_core import exceptions as google_exceptions

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class UndeploymentError(Exception):
    """Custom exception for undeployment errors"""

    pass


class AgentUndeployer:
    """Handles undeployment of SQL Agent from Agent Engine and AgentSpace"""

    def __init__(self):
        """Initialize undeployer with configuration"""
        load_dotenv()

        # Deployment state file
        self.state_file = Path("deployment/.deployment_state.json")
        self.deployment_state = None

        # Load deployment state
        self._load_deployment_state()

        logger.info(
            f"Undeployer initialized for project: {self.deployment_state.get('project_id')}"
        )

    def _load_deployment_state(self) -> Dict[str, Any]:
        """Load deployment state from file"""
        if not self.state_file.exists():
            raise UndeploymentError(
                f"Deployment state file not found: {self.state_file}\n"
                "The agent may not be deployed or the state file was deleted."
            )

        try:
            with open(self.state_file, "r") as f:
                self.deployment_state = json.load(f)

            # Validate required fields (authorization_id is optional for M2M OAuth)
            required_fields = [
                "project_id",
                "location",
                "agent_resource_name",
                "agent_id",
                "agentspace_app_id",
            ]

            missing_fields = [
                field for field in required_fields if field not in self.deployment_state
            ]

            if missing_fields:
                raise UndeploymentError(
                    f"Invalid deployment state file. Missing fields: {missing_fields}"
                )

            # Check if this is an M2M OAuth deployment
            self.is_m2m_deployment = self.deployment_state.get("oauth_mode") == "m2m"
            if self.is_m2m_deployment:
                logger.info(
                    "Detected M2M OAuth deployment - skipping authorization cleanup"
                )

            # Check if network attachment was used (for informational purposes)
            self.used_network_attachment = (
                self.deployment_state.get("network_attachment_id") is not None
            )
            if self.used_network_attachment:
                network_attachment_id = self.deployment_state.get(
                    "network_attachment_id"
                )
                logger.info(
                    f"Deployment used network attachment: {network_attachment_id}"
                )
                logger.info(
                    "Note: Network infrastructure cleanup should be handled separately via Terraform"
                )

            logger.info(f"Loaded deployment state from: {self.state_file}")
            return self.deployment_state

        except json.JSONDecodeError as e:
            raise UndeploymentError(f"Invalid JSON in deployment state file: {e}")
        except Exception as e:
            raise UndeploymentError(f"Failed to load deployment state: {e}")

    def _get_access_token(self) -> str:
        """Get Google Cloud access token"""
        try:
            result = subprocess.run(
                ["gcloud", "auth", "print-access-token"],
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            raise UndeploymentError(f"Failed to get access token: {e}")

    def list_agentspace_agents(self, access_token: str) -> list:
        """List all agents in AgentSpace"""
        project_id = self.deployment_state["project_id"]
        agentspace_app_id = self.deployment_state["agentspace_app_id"]

        agents_url = (
            f"https://discoveryengine.googleapis.com/v1alpha/"
            f"projects/{project_id}/locations/global/collections/default_collection/"
            f"engines/{agentspace_app_id}/assistants/default_assistant/agents"
        )

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "X-Goog-User-Project": project_id,
        }

        try:
            response = requests.get(agents_url, headers=headers)

            if response.status_code == 200:
                data = response.json()
                return data.get("agents", [])
            elif response.status_code == 404:
                logger.warning("AgentSpace engine not found or no agents exist")
                return []
            else:
                logger.warning(
                    f"Failed to list AgentSpace agents: {response.status_code} - {response.text}"
                )
                return []

        except requests.RequestException as e:
            logger.warning(f"Failed to list AgentSpace agents: {e}")
            return []

    def delete_from_agentspace(self, access_token: str) -> bool:
        """Delete agent from AgentSpace"""
        logger.info("Removing agent from AgentSpace...")

        project_id = self.deployment_state["project_id"]
        agentspace_app_id = self.deployment_state["agentspace_app_id"]
        agent_id = self.deployment_state["agent_id"]

        # First, check if the agent exists
        agents = self.list_agentspace_agents(access_token)
        agent_exists = False

        for agent in agents:
            if agent.get("name", "").endswith(f"/{agent_id}"):
                agent_exists = True
                break

        if not agent_exists:
            logger.info(
                f"Agent {agent_id} not found in AgentSpace (may already be deleted)"
            )
            return True

        # Delete the agent
        delete_url = (
            f"https://discoveryengine.googleapis.com/v1alpha/"
            f"projects/{project_id}/locations/global/collections/default_collection/"
            f"engines/{agentspace_app_id}/assistants/default_assistant/agents/{agent_id}"
        )

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "X-Goog-User-Project": project_id,
        }

        try:
            response = requests.delete(delete_url, headers=headers)

            if response.status_code in [200, 204]:
                logger.info(f"Successfully deleted agent from AgentSpace: {agent_id}")
                return True
            elif response.status_code == 404:
                logger.info(
                    f"Agent {agent_id} not found in AgentSpace (may already be deleted)"
                )
                return True
            else:
                logger.error(
                    f"Failed to delete agent from AgentSpace: {response.status_code} - {response.text}"
                )
                return False

        except requests.RequestException as e:
            logger.error(f"Failed to delete agent from AgentSpace: {e}")
            return False

    def delete_oauth_authorization(self, access_token: str) -> bool:
        """Delete OAuth authorization from AgentSpace"""

        # Skip authorization deletion for M2M OAuth deployments
        if self.is_m2m_deployment:
            logger.info("Skipping OAuth authorization deletion (M2M OAuth deployment)")
            return True

        # Check if authorization_id exists in deployment state
        if "authorization_id" not in self.deployment_state:
            logger.info(
                "No authorization_id found in deployment state - skipping OAuth authorization deletion"
            )
            return True

        logger.info("Deleting OAuth authorization...")

        project_id = self.deployment_state["project_id"]
        authorization_id = self.deployment_state["authorization_id"]

        delete_url = (
            f"https://discoveryengine.googleapis.com/v1alpha/"
            f"projects/{project_id}/locations/global/authorizations/{authorization_id}"
        )

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "X-Goog-User-Project": project_id,
        }

        try:
            response = requests.delete(delete_url, headers=headers)

            if response.status_code in [200, 204]:
                logger.info(
                    f"Successfully deleted OAuth authorization: {authorization_id}"
                )
                return True
            elif response.status_code == 404:
                logger.info(
                    f"OAuth authorization {authorization_id} not found (may already be deleted)"
                )
                return True
            else:
                logger.warning(
                    f"Failed to delete OAuth authorization: {response.status_code} - {response.text}"
                )
                return False

        except requests.RequestException as e:
            logger.warning(f"Failed to delete OAuth authorization: {e}")
            return False

    def delete_from_agent_engine(self) -> bool:
        """Delete agent from Vertex AI Agent Engine"""
        logger.info("Deleting agent from Vertex AI Agent Engine...")

        project_id = self.deployment_state["project_id"]
        location = self.deployment_state["location"]
        agent_resource_name = self.deployment_state["agent_resource_name"]

        try:
            # Initialize Vertex AI
            vertexai.init(project=project_id, location=location)

            # Get the agent
            try:
                remote_agent = agent_engines.get(agent_resource_name)
            except google_exceptions.NotFound:
                logger.info(
                    f"Agent {agent_resource_name} not found in Agent Engine (may already be deleted)"
                )
                return True

            # Delete the agent
            remote_agent.delete(force=True)
            logger.info(
                f"Successfully deleted agent from Agent Engine: {agent_resource_name}"
            )
            return True

        except google_exceptions.NotFound:
            logger.info(
                f"Agent {agent_resource_name} not found in Agent Engine (may already be deleted)"
            )
            return True
        except Exception as e:
            logger.error(f"Failed to delete agent from Agent Engine: {e}")
            return False

    def cleanup_deployment_state(self):
        """Remove deployment state file"""
        logger.info("Cleaning up deployment state...")

        try:
            if self.state_file.exists():
                self.state_file.unlink()
                logger.info(f"Deployment state file deleted: {self.state_file}")
            else:
                logger.info("Deployment state file already removed")
        except Exception as e:
            logger.warning(f"Failed to delete deployment state file: {e}")

    def undeploy(self) -> Dict[str, Any]:
        """Execute complete undeployment process"""
        logger.info("Starting SQL Agent undeployment...")

        # Track what was successfully cleaned up
        results = {
            "agentspace_deleted": False,
            "authorization_deleted": False,
            "agent_engine_deleted": False,
            "state_cleaned": False,
            "errors": [],
        }

        try:
            # Step 1: Get access token
            try:
                access_token = self._get_access_token()
            except Exception as e:
                results["errors"].append(f"Failed to get access token: {e}")
                logger.error(f"Cannot proceed without access token: {e}")
                return results

            # Step 2: Delete from AgentSpace
            try:
                results["agentspace_deleted"] = self.delete_from_agentspace(
                    access_token
                )
            except Exception as e:
                results["errors"].append(f"AgentSpace deletion error: {e}")
                logger.error(f"AgentSpace deletion failed: {e}")

            # Step 3: Delete OAuth authorization
            try:
                results["authorization_deleted"] = self.delete_oauth_authorization(
                    access_token
                )
            except Exception as e:
                results["errors"].append(f"OAuth authorization deletion error: {e}")
                logger.error(f"OAuth authorization deletion failed: {e}")

            # Step 4: Delete from Agent Engine
            try:
                results["agent_engine_deleted"] = self.delete_from_agent_engine()
            except Exception as e:
                results["errors"].append(f"Agent Engine deletion error: {e}")
                logger.error(f"Agent Engine deletion failed: {e}")

            # Step 5: Cleanup state file
            try:
                self.cleanup_deployment_state()
                results["state_cleaned"] = True
            except Exception as e:
                results["errors"].append(f"State cleanup error: {e}")
                logger.error(f"State cleanup failed: {e}")

            # Summary
            if results["errors"]:
                logger.warning("Undeployment completed with some errors")
            else:
                logger.info("Undeployment completed successfully!")

            return results

        except Exception as e:
            results["errors"].append(f"Unexpected error: {e}")
            logger.error(f"Undeployment failed with unexpected error: {e}")
            return results


def main():
    """Main undeployment function"""
    try:
        undeployer = AgentUndeployer()
        results = undeployer.undeploy()

        print("\n" + "=" * 60)
        print("🧹 UNDEPLOYMENT RESULTS")
        print("=" * 60)

        # Show what was cleaned up
        if results["agentspace_deleted"]:
            print("✅ Agent removed from AgentSpace")
        else:
            print("❌ Failed to remove agent from AgentSpace")

        if results["authorization_deleted"]:
            print("✅ OAuth authorization deleted")
        else:
            print("❌ Failed to delete OAuth authorization")

        if results["agent_engine_deleted"]:
            print("✅ Agent deleted from Agent Engine")
        else:
            print("❌ Failed to delete agent from Agent Engine")

        if results["state_cleaned"]:
            print("✅ Deployment state cleaned up")
        else:
            print("❌ Failed to clean up deployment state")

        # Show errors if any
        if results["errors"]:
            print("\n⚠️  ERRORS ENCOUNTERED:")
            for error in results["errors"]:
                print(f"   • {error}")

        print("=" * 60)

        # Check if Terraform cleanup is needed
        if (
            hasattr(undeployer, "used_network_attachment")
            and undeployer.used_network_attachment
        ):
            print("\n🔧 TERRAFORM CLEANUP REQUIRED:")
            print("   This deployment used Terraform-managed network infrastructure.")
            print("   To complete cleanup, run:")
            print("   cd terraform/ && terraform destroy")

        # Determine exit code
        if results["errors"]:
            if any([results["agentspace_deleted"], results["agent_engine_deleted"]]):
                print("\n⚠️  Partial cleanup completed. Some resources may remain.")
                return 2  # Partial success
            else:
                print("\n❌ Undeployment failed.")
                return 1  # Failure
        else:
            print("\n🎉 Complete cleanup successful!")
            return 0  # Success

    except UndeploymentError as e:
        print(f"\n❌ Undeployment Error: {e}")
        return 1
    except Exception as e:
        print(f"\n💥 Unexpected Error: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
