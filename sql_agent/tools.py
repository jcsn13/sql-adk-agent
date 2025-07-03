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

"""Top level agent for data agent multi-agents.

-- it get data from database (e.g., BQ) using NL2SQL
-- then, it use NL2Py to do further data analysis as needed
"""

from google.adk.tools import ToolContext
from google.adk.agents.callback_context import CallbackContext
from google.adk.tools import load_artifacts
from google.adk.tools.agent_tool import AgentTool
from google.genai.types import Part as Artifact
from typing import List, Union, Optional, Dict
from datetime import datetime
import base64

# Added imports
import httpx
import mimetypes

from .sub_agents import ds_agent, db_agent


async def call_db_agent(
    question: str,
    tool_context: ToolContext,
):
    """Tool to call database (nl2sql) agent."""
    print(
        "\n call_db_agent.use_database:"
        f' {tool_context.state["all_db_settings"]["use_database"]}'
    )

    agent_tool = AgentTool(agent=db_agent)

    db_agent_output = await agent_tool.run_async(
        args={"request": question}, tool_context=tool_context
    )
    tool_context.state["db_agent_output"] = db_agent_output
    return db_agent_output


async def call_ds_agent(
    question: str,
    tool_context: ToolContext,
):
    """Tool to call data science (nl2py) agent."""

    if question == "N/A":
        return tool_context.state["db_agent_output"]

    input_data = tool_context.state["query_result"]

    question_with_data = f"""
  Question to answer: {question}

  Actual data to analyze prevoius quesiton is already in the following:
  {input_data}

  """

    agent_tool = AgentTool(agent=ds_agent)

    ds_agent_output = await agent_tool.run_async(
        args={"request": question_with_data}, tool_context=tool_context
    )
    tool_context.state["ds_agent_output"] = ds_agent_output
    return ds_agent_output


async def download_image_and_save_to_artifacts(
    image_url: str, tool_context: ToolContext
) -> Dict[str, str]:
    """
    Downloads an image (JPG, JPEG, PNG only) from a URL,
    saves it to artifacts, and returns status.
    """
    allowed_content_types = {
        "image/jpeg": ".jpg",
        "image/jpg": ".jpg",  # Often image/jpeg is used for .jpg
        "image/png": ".png",
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(image_url)
            response.raise_for_status()

        image_bytes = response.content
        content_type = response.headers.get("Content-Type", "").lower()

        if content_type not in allowed_content_types:
            return {
                "status": "failed",
                "detail": (
                    f"Unsupported or missing Content-Type. "
                    f"Expected one of {', '.join(allowed_content_types.keys())}, "
                    f"got '{content_type}'."
                ),
                "filename": "",
            }

        file_extension = allowed_content_types[content_type]
        # Ensure jpg consistency
        if content_type == "image/jpg":  # mimetypes often maps image/jpeg to .jpe
            file_extension = ".jpg"

        filename = f"downloaded_image{file_extension}"

        artifact_part = Artifact.from_bytes(data=image_bytes, mime_type=content_type)
        await tool_context.save_artifact(filename, artifact_part)

        return {
            "status": "success",
            "detail": f"Image downloaded successfully from {image_url} and stored as {filename}.",
            "filename": filename,
        }
    except httpx.HTTPStatusError as e:
        error_detail = (
            f"HTTP error occurred: {e.request.url} - Status {e.response.status_code}"
        )
        if e.response.status_code == 404:
            error_detail = f"Image not found at URL: {e.request.url} (404 Error)"
        elif e.response.status_code == 403:
            error_detail = f"Access forbidden to URL: {e.request.url} (403 Error)"
        return {
            "status": "failed",
            "detail": error_detail,
            "filename": "",
        }
    except httpx.TimeoutException as e:
        return {
            "status": "failed",
            "detail": f"Request timed out while trying to download {e.request.url}: {str(e)}",
            "filename": "",
        }
    except httpx.RequestError as e:
        return {
            "status": "failed",
            "detail": f"Request error occurred while trying to download {e.request.url}: {str(e)}",
            "filename": "",
        }
    except Exception as e:
        return {
            "status": "failed",
            "detail": f"An unexpected error occurred: {str(e)}",
            "filename": "",
        }
