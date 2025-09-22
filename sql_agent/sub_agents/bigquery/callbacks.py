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

"""Callback functions for the BigQuery agent."""

from typing import Optional

from google.adk.agents.callback_context import CallbackContext
from google.adk.models import LlmRequest, LlmResponse
from google.genai import types
from sql_agent.cache import CacheManager

cache_manager = CacheManager()


def before_model_callback(
    callback_context: CallbackContext, llm_request: LlmRequest
) -> Optional[LlmResponse]:
    """Checks for a cached response before calling the model.

    Args:
        callback_context: The context object for the callback.
        llm_request: The request object for the LLM.

    Returns:
        An LlmResponse object if a cached response is found, otherwise None.
    """
    if llm_request.contents:
        question = llm_request.contents[-1].parts[0].text
        cached_query = cache_manager.get_from_question_cache(question)
        if cached_query:
            cached_response = cache_manager.get_from_query_cache(cached_query)
            if cached_response:
                return LlmResponse(
                    content=types.Content(
                        role="model",
                        parts=cached_response["response"].parts,
                    )
                )
    return None


def after_model_callback(
    callback_context: CallbackContext, llm_response: LlmResponse
) -> None:
    """Caches the response after the model is called.

    Args:
        callback_context: The context object for the callback.
        llm_response: The response object from the LLM.
    """
    if llm_response.content and llm_response.content.parts:
        query = llm_response.content.parts[0].text
        if callback_context.history:
            question = callback_context.history[-1].parts[0].text
            cache_manager.set_to_query_cache(
                query, {"response": llm_response.content, "artifacts": []}
            )
            cache_manager.set_to_question_cache(question, query)
