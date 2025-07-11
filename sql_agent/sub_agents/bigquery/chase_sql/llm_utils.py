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

"""This code contains the LLM utils for the CHASE-SQL Agent."""

import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, List, Optional

import dotenv
from google import genai
from google.genai import types

dotenv.load_dotenv(override=True)

# Safety filter configuration using new format
SAFETY_FILTER_CONFIG = [
    types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="OFF"),
    types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="OFF"),
    types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="OFF"),
    types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="OFF"),
]

GCP_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT")


class GeminiModel:
    """Class for the Gemini model using the new google-genai library."""

    def __init__(
        self,
        model_name: str = "gemini-2.0-flash-001",
        finetuned_model: bool = False,
        cache_name: str | None = None,
        temperature: float = 0.01,
        **kwargs,
    ):
        """Initialize the Gemini model with global region support.

        Args:
            model_name: The name of the model to use
            finetuned_model: Whether this is a finetuned model (kept for compatibility)
            cache_name: Cache name (kept for compatibility, may need implementation)
            temperature: Temperature for generation
            **kwargs: Additional generation config parameters
        """
        self.model_name = model_name
        self.finetuned_model = finetuned_model
        self.cache_name = cache_name
        self.temperature = temperature
        self.arguments = kwargs

        # Initialize the client with global location
        self.client = genai.Client(
            vertexai=True,
            project=GCP_PROJECT,
            location="global",
        )

    def call(self, prompt: str, parser_func=None) -> str:
        """Calls the Gemini model with the given prompt.

        Args:
            prompt (str): The prompt to call the model with.
            parser_func (callable, optional): A function that processes the LLM
              output. It takes the model's response as input and returns the
              processed result.

        Returns:
            str: The processed response from the model.
        """
        # Prepare content in the new format
        contents = [types.Content(role="user", parts=[types.Part(text=prompt)])]

        # Prepare generation config
        generate_content_config = types.GenerateContentConfig(
            temperature=self.temperature,
            safety_settings=SAFETY_FILTER_CONFIG,
            **self.arguments,
        )

        # Generate content
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=contents,
            config=generate_content_config,
        )

        # Extract text from response
        response_text = response.text

        if parser_func:
            return parser_func(response_text)
        return response_text

    def call_parallel(
        self,
        prompts: List[str],
        parser_func: Optional[Callable[[str], str]] = None,
        timeout: int = 60,
        max_retries: int = 5,  # Kept for compatibility but not used
    ) -> List[Optional[str]]:
        """Calls the Gemini model for multiple prompts in parallel using threads.

        Args:
            prompts (List[str]): A list of prompts to call the model with.
            parser_func (callable, optional): A function to process each response.
            timeout (int): The maximum time (in seconds) to wait for each thread.
            max_retries (int): Kept for compatibility (not used with global region).

        Returns:
            List[Optional[str]]:
            A list of responses, or None for threads that failed.
        """
        results = [None] * len(prompts)

        def worker(index: int, prompt: str):
            """Thread worker function to call the model and store the result."""
            try:
                return self.call(prompt, parser_func)
            except Exception as e:  # pylint: disable=broad-exception-caught
                print(f"Error for prompt {index}: {str(e)}")
                return f"Error: {str(e)}"

        # Create and start one thread for each prompt
        with ThreadPoolExecutor(max_workers=len(prompts)) as executor:
            future_to_index = {
                executor.submit(worker, i, prompt): i
                for i, prompt in enumerate(prompts)
            }

            for future in as_completed(future_to_index, timeout=timeout):
                index = future_to_index[future]
                try:
                    results[index] = future.result()
                except Exception as e:  # pylint: disable=broad-exception-caught
                    print(f"Unhandled error for prompt {index}: {e}")
                    results[index] = "Unhandled Error"

        # Handle remaining unfinished tasks after the timeout
        for future in future_to_index:
            index = future_to_index[future]
            if not future.done():
                print(f"Timeout occurred for prompt {index}")
                results[index] = "Timeout"

        return results
