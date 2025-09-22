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

"""This module provides a simple in-memory cache for the agent."""


class CacheManager:
    """A simple in-memory cache manager."""

    def __init__(self):
        """Initializes the CacheManager with two dictionaries."""
        self.query_cache = {}
        self.question_cache = {}

    def get_from_query_cache(self, query: str) -> dict | None:
        """Retrieves an item from the query cache.

        Args:
            query: The SQL query to use as the key.

        Returns:
            The cached response dictionary or None if not found.
        """
        return self.query_cache.get(query)

    def set_to_query_cache(self, query: str, response: dict) -> None:
        """Sets an item in the query cache.

        Args:
            query: The SQL query to use as the key.
            response: The response dictionary to cache.
        """
        self.query_cache[query] = response

    def get_from_question_cache(self, question: str) -> str | None:
        """Retrieves a query from the question cache.

        Args:
            question: The natural language question to use as the key.

        Returns:
            The cached SQL query or None if not found.
        """
        return self.question_cache.get(question)

    def set_to_question_cache(self, question: str, query: str) -> None:
        """Sets an item in the question cache.

        Args:
            question: The natural language question to use as the key.
            query: The SQL query to cache.
        """
        self.question_cache[question] = query
