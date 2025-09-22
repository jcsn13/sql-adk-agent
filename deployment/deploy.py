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
Deployment script for SQL ADK Agent to Google Cloud Agent Engine and AgentSpace.

This script:
1. Deploys the agent to Vertex AI Agent Engine using ADK
2. Registers the agent in AgentSpace for enterprise discovery
3. Saves deployment state for later undeployment

Usage:
    python deployment/deploy.py
"""

import os
import sys
import json
import logging
import subprocess
import argparse
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

import requests
from dotenv import load_dotenv
import vertexai
from vertexai.preview import reasoning_engines
from vertexai import agent_engines
from google.cloud import storage
from google.api_core import exceptions as google_exceptions

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Add project root to path for proper package imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class DeploymentError(Exception):
    """Custom exception for deployment errors"""

    pass


class AgentDeployer:
    """Handles deployment of the SQL ADK Agent"""

    def __init__(self):
        """Initialize deployer with environment configuration"""
        load_dotenv()

        # Required environment variables
        self.project_id = self._get_env_var("GOOGLE_CLOUD_PROJECT")
        self.project_number = self._get_env_var("GOOGLE_CLOUD_PROJECT_NUMBER")
        self.location = self._get_env_var("GOOGLE_CLOUD_LOCATION")
        self.bucket_name = self._get_env_var("GOOGLE_CLOUD_STORAGE_BUCKET")

        # AgentSpace configuration
        self.agentspace_app_id = self._get_env_var("APP_ID")
        self.agent_display_name = self._get_env_var("AGENT_DISPLAY_NAME")
        self.agent_description = self._get_env_var("TOOL_DESCRIPTION")
        self.agent_icon_uri = self._get_env_var("AGENT_ICON_URI")

        # OAuth configuration
        self.client_id = self._get_env_var("CLIENT_ID")
        self.client_secret = self._get_env_var("CLIENT_SECRET")

        # Check if running from Terraform (OAuth client managed externally)
        self.terraform_managed = self._is_terraform_managed()

        # Auth path will be generated dynamically or from environment
        self.auth_path = os.getenv(
            "AUTH_PATH"
        )  # Optional, will be created if not provided
        self.authorization_id: Optional[str] = None

        # Environment variables to pass to the agent
        self.agent_env_vars = {
            "ROOT_AGENT_MODEL": os.getenv("ROOT_AGENT_MODEL"),
            "ANALYTICS_AGENT_MODEL": os.getenv("ANALYTICS_AGENT_MODEL"),
            "BASELINE_NL2SQL_MODEL": os.getenv("BASELINE_NL2SQL_MODEL"),
            "BIGQUERY_AGENT_MODEL": os.getenv("BIGQUERY_AGENT_MODEL"),
            "CHASE_NL2SQL_MODEL": os.getenv("CHASE_NL2SQL_MODEL"),
            "BQ_DATASET_ID": os.getenv("BQ_DATASET_ID"),
            "BQ_PROJECT_ID": os.getenv("BQ_PROJECT_ID"),
            "AUTH_ID": os.getenv("AUTH_ID"),
            "NL2SQL_METHOD": os.getenv("NL2SQL_METHOD"),
        }

        # Filter out None and empty string values
        self.agent_env_vars = {
            k: v for k, v in self.agent_env_vars.items() if v is not None and v != ""
        }

        # Deployment state
        self.state_file = Path("deployment/.deployment_state.json")
        self.deployed_agent = None

        logger.info(f"Deployer initialized for project: {self.project_id}")
        if self.terraform_managed:
            logger.info(
                "Running in Terraform-managed mode (OAuth client managed by Terraform)"
            )
        else:
            logger.info("Running in standalone mode")

    def _get_env_var(self, name: str) -> str:
        """Get required environment variable or raise error"""
        value = os.getenv(name)
        if not value:
            raise DeploymentError(f"Required environment variable {name} not set")
        return value

    def _is_terraform_managed(self) -> bool:
        """Check if OAuth client is managed by Terraform"""
        # Detect Terraform execution by checking for Terraform-specific environment patterns
        terraform_indicators = [
            "TF_VAR_",  # Terraform variable prefix
            "TERRAFORM_",  # Terraform-specific vars
        ]

        # Check if any environment variables suggest Terraform execution
        env_vars = os.environ.keys()
        for indicator in terraform_indicators:
            if any(var.startswith(indicator) for var in env_vars):
                return True

        # Also check for a direct Terraform flag
        return os.getenv("TERRAFORM_MANAGED", "false").lower() == "true"

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
            raise DeploymentError(f"Failed to get access token: {e}")

    def create_oauth_authorization(self, access_token: str) -> Dict[str, str]:
        """Create OAuth authorization using Discovery Engine API"""
        logger.info("Creating OAuth authorization...")

        # Use AUTH_ID from environment or generate unique authorization ID using timestamp
        auth_id = os.getenv("AUTH_ID", f"sql-agent-auth-{int(time.time())}")

        # Build authorization creation URL (using project_id for API calls)
        auth_url = (
            f"https://discoveryengine.googleapis.com/v1alpha/"
            f"projects/{self.project_id}/locations/global/authorizations"
            f"?authorizationId={auth_id}"
        )

        # Prepare OAuth payload (using project_id for API calls)
        payload = {
            "name": f"projects/{self.project_id}/locations/global/authorizations/{auth_id}",
            "serverSideOauth2": {
                "clientId": self.client_id,
                "clientSecret": self.client_secret,
                "authorizationUri": (
                    "https://accounts.google.com/o/oauth2/v2/auth"
                    "?client_id={OAUTH_CLIENT_ID}&response_type=code&access_type=offline"
                    "&prompt=consent&scope=openid%20https%3A%2F%2Fwww.googleapis.com"
                    "%2Fauth%2Fuserinfo.email%20https%3A%2F%2Fwww.googleapis.com"
                    "%2Fauth%2Fuserinfo.profile%20https%3A%2F%2Fwww.googleapis.com"
                    "%2Fauth%2Fbigquery"
                ),
                "tokenUri": "https://oauth2.googleapis.com/token",
            },
        }

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "X-Goog-User-Project": self.project_id,
        }

        try:
            response = requests.post(auth_url, json=payload, headers=headers)

            if response.status_code in [200, 201]:
                logger.info(f"OAuth authorization created successfully: {auth_id}")
                auth_path = f"projects/{self.project_number}/locations/global/authorizations/{auth_id}"
                return {"auth_id": auth_id, "auth_path": auth_path}
            elif response.status_code == 409:
                # Authorization already exists, use it
                logger.info(f"OAuth authorization already exists: {auth_id}")
                auth_path = f"projects/{self.project_number}/locations/global/authorizations/{auth_id}"
                return {"auth_id": auth_id, "auth_path": auth_path}
            else:
                raise DeploymentError(
                    f"OAuth authorization creation failed: {response.status_code} - {response.text}"
                )

        except requests.RequestException as e:
            raise DeploymentError(f"Failed to create OAuth authorization: {e}")

    def setup_staging_bucket(self) -> str:
        """Setup or verify staging bucket exists"""
        logger.info(f"Setting up staging bucket: {self.bucket_name}")
        storage_client = storage.Client(project=self.project_id)
        try:
            bucket = storage_client.lookup_bucket(self.bucket_name)
            if bucket:
                logger.info(f"Staging bucket gs://{self.bucket_name} already exists")
            else:
                logger.info(f"Creating staging bucket: gs://{self.bucket_name}")
                new_bucket = storage_client.create_bucket(
                    self.bucket_name, project=self.project_id, location=self.location
                )
                new_bucket.iam_configuration.uniform_bucket_level_access_enabled = True
                new_bucket.patch()
                logger.info(
                    f"Created staging bucket with uniform access: gs://{new_bucket.name}"
                )
        except google_exceptions.Forbidden as e:
            raise DeploymentError(
                f"Permission denied for bucket {self.bucket_name}: {e}"
            )
        except google_exceptions.Conflict as e:
            logger.warning(f"Bucket conflict (may exist in another project): {e}")
        except Exception as e:
            raise DeploymentError(f"Failed to setup staging bucket: {e}")
        return f"gs://{self.bucket_name}"

    def deploy_to_agent_engine(self) -> str:
        """Deploy agent to Vertex AI Agent Engine"""
        logger.info("Deploying to Vertex AI Agent Engine...")
        try:
            staging_bucket_uri = self.setup_staging_bucket()
            vertexai.init(
                project=self.project_id,
                location=self.location,
                staging_bucket=staging_bucket_uri,
            )
            from sql_agent.agent import root_agent

            adk_app = reasoning_engines.AdkApp(
                agent=root_agent,
                enable_tracing=True,
            )
            requirements = [
                "google-cloud-aiplatform[adk,agent_engines]>=1.102.0",
                "google-cloud-storage>=2.10.0",
                "requests>=2.31.0",
                "python-dotenv>=1.0.1",
                "google-adk>=1.6.1",
                "immutabledict>=4.2.1",
                "sqlglot>=26.10.1",
                "db-dtypes>=1.4.2",
                "regex>=2024.11.6",
                "tabulate>=0.9.0",
                "google-genai>=1.21.1",
                "absl-py>=2.2.2",
                "pydantic>=2.11.3",
            ]
            logger.info("Creating Agent Engine deployment...")
            self.deployed_agent = agent_engines.create(
                agent_engine=adk_app,
                requirements=requirements,
                extra_packages=["sql_agent"],
                env_vars=self.agent_env_vars,
            )
            resource_name = self.deployed_agent.resource_name
            logger.info(f"Successfully deployed to Agent Engine: {resource_name}")
            return resource_name
        except ImportError as e:
            raise DeploymentError(f"Failed to import root_agent: {e}")
        except Exception as e:
            logger.error(f"Agent Engine deployment error details: {e}")
            raise DeploymentError(f"Agent Engine deployment failed: {e}")

    def register_in_agentspace(
        self, agent_resource_name: str, access_token: str
    ) -> str:
        """Register agent in AgentSpace"""
        logger.info("Registering agent in AgentSpace...")
        agents_url = (
            f"https://discoveryengine.googleapis.com/v1alpha/"
            f"projects/{self.project_id}/locations/global/collections/default_collection/"
            f"engines/{self.agentspace_app_id}/assistants/default_assistant/agents"
        )
        payload = {
            "displayName": self.agent_display_name,
            "description": self.agent_description,
            "icon": {"uri": self.agent_icon_uri},
            "adk_agent_definition": {
                "tool_settings": {"tool_description": self.agent_description},
                "provisioned_reasoning_engine": {
                    "reasoning_engine": agent_resource_name
                },
                "authorizations": [self.auth_path],
            },
        }
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "X-Goog-User-Project": self.project_id,
        }
        try:
            response = requests.post(agents_url, json=payload, headers=headers)
            if response.status_code in [200, 201]:
                agent_data = response.json()
                agent_id = agent_data.get("name", "").split("/")[-1]
                logger.info(f"Agent registered in AgentSpace: {agent_id}")
                return agent_id
            else:
                raise DeploymentError(
                    f"AgentSpace registration failed: {response.status_code} - {response.text}"
                )
        except requests.RequestException as e:
            raise DeploymentError(f"Failed to register in AgentSpace: {e}")

    def save_deployment_state(self, agent_resource_name: str, agent_id: str):
        """Save deployment state for undeployment"""
        state_data = {
            "deployment_timestamp": datetime.now().isoformat(),
            "project_id": self.project_id,
            "location": self.location,
            "agent_resource_name": agent_resource_name,
            "agent_id": agent_id,
            "agentspace_app_id": self.agentspace_app_id,
            "agent_display_name": self.agent_display_name,
            "auth_path": self.auth_path,
            "oauth_mode": "u2m",  # User-to-Machine OAuth
            "terraform_managed": self.terraform_managed,  # Track OAuth management mode
        }

        # Include authorization_id if it was created during deployment
        if self.authorization_id:
            state_data["authorization_id"] = self.authorization_id

        self.state_file.parent.mkdir(exist_ok=True)
        with open(self.state_file, "w") as f:
            json.dump(state_data, f, indent=2)
        logger.info(f"Deployment state saved to: {self.state_file}")

    def rollback_deployment(self):
        """Rollback deployment in case of partial failure"""
        logger.warning("Rolling back deployment due to failure...")

        # Clean up Agent Engine deployment
        try:
            if self.deployed_agent:
                logger.info("Deleting Agent Engine deployment...")
                self.deployed_agent.delete(force=True)
                logger.info("Agent Engine deployment deleted")
        except Exception as e:
            logger.error(f"Failed to rollback Agent Engine deployment: {e}")

        # Clean up OAuth authorization if created (but not if Terraform-managed)
        if self.authorization_id and not self.terraform_managed:
            try:
                logger.info(f"Cleaning up OAuth authorization: {self.authorization_id}")
                access_token = self._get_access_token()
                delete_url = (
                    f"https://discoveryengine.googleapis.com/v1alpha/"
                    f"projects/{self.project_id}/locations/global/authorizations/{self.authorization_id}"
                )
                headers = {
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                    "X-Goog-User-Project": self.project_id,
                }
                response = requests.delete(delete_url, headers=headers)
                if response.status_code in [200, 204]:
                    logger.info("OAuth authorization cleaned up successfully")
                else:
                    logger.warning(
                        f"Failed to clean up OAuth authorization: {response.status_code}"
                    )
            except Exception as e:
                logger.error(f"Failed to rollback OAuth authorization: {e}")
        elif self.authorization_id and self.terraform_managed:
            logger.info("OAuth authorization cleanup skipped (managed by Terraform)")

        # Clean up deployment state file
        if self.state_file.exists():
            self.state_file.unlink()
            logger.info("Cleaned up deployment state file")

    def deploy(self) -> Dict[str, Any]:
        """Execute complete deployment process"""
        logger.info("Starting SQL ADK Agent deployment...")
        try:
            # Step 1: Get access token
            access_token = self._get_access_token()

            # Step 2: Handle OAuth authorization based on management mode
            if not self.auth_path:
                if self.terraform_managed:
                    logger.info(
                        "AUTH_PATH not provided, creating OAuth authorization with Terraform-managed credentials..."
                    )
                else:
                    logger.info(
                        "AUTH_PATH not provided, creating OAuth authorization..."
                    )

                oauth_result = self.create_oauth_authorization(access_token)
                self.auth_path = oauth_result["auth_path"]
                self.authorization_id = oauth_result["auth_id"]
                logger.info(f"Using dynamically created AUTH_PATH: {self.auth_path}")
            else:
                logger.info(f"Using existing AUTH_PATH: {self.auth_path}")

            # Step 3: Deploy to Agent Engine
            agent_resource_name = self.deploy_to_agent_engine()

            # Step 4: Register in AgentSpace
            agent_id = self.register_in_agentspace(agent_resource_name, access_token)

            # Step 5: Save deployment state
            self.save_deployment_state(agent_resource_name, agent_id)

            result = {
                "status": "success",
                "agent_resource_name": agent_resource_name,
                "agent_id": agent_id,
                "agentspace_url": f"https://agentspace.google.com/studio/{self.project_id}",
                "message": "SQL ADK Agent successfully deployed and registered.",
                "auth_path": self.auth_path,
                "oauth_created": self.authorization_id is not None,
            }

            logger.info("Deployment completed successfully!")
            logger.info(f"Agent Resource: {agent_resource_name}")
            logger.info(f"AgentSpace Agent ID: {agent_id}")
            logger.info(f"AUTH_PATH: {self.auth_path}")
            if self.authorization_id:
                logger.info(f"OAuth Authorization ID: {self.authorization_id}")
            logger.info(f"AgentSpace URL: {result['agentspace_url']}")
            return result
        except Exception as e:
            logger.error(f"Deployment failed: {e}")
            self.rollback_deployment()
            raise


def main():
    """Main deployment function"""
    parser = argparse.ArgumentParser(
        description="Deploy SQL ADK Agent to Google Cloud."
    )
    args = parser.parse_args()
    try:
        deployer = AgentDeployer()
        result = deployer.deploy()
        print("\n" + "=" * 60)
        print("🎉 DEPLOYMENT SUCCESSFUL!")
        print("=" * 60)
        print(f"Agent Resource: {result['agent_resource_name']}")
        print(f"AgentSpace Agent ID: {result['agent_id']}")
        print(f"AgentSpace URL: {result['agentspace_url']}")
        print("\nYour SQL ADK Agent is now available in Google AgentSpace!")
        print("=" * 60)
        return 0
    except DeploymentError as e:
        print(f"\n❌ Deployment Error: {e}")
        return 1
    except Exception as e:
        print(f"\n💥 Unexpected Error: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
