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

"""This file contains the tools used by the database agent."""

import datetime
import logging
import os
import re

from ...utils.utils import get_env_var
from google.adk.tools import ToolContext
from google.cloud import bigquery
from google.genai import Client
from google.oauth2 import credentials

from .chase_sql import chase_constants

# Assume that `BQ_PROJECT_ID` is set in the environment. See the
# `data_agent` README for more details.
project = os.getenv("BQ_PROJECT_ID", None)
location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
llm_client = Client(vertexai=True, project=project, location=location)

MAX_NUM_ROWS = 80


def get_bq_client(tool_context: ToolContext) -> bigquery.Client:
    """Initializes and returns a BigQuery client.

    This function creates a BigQuery client, using OAuth credentials if an access
    token is available in the tool context's state. This allows the agent to
    authenticate and interact with BigQuery on behalf of the user.

    Args:
        tool_context: The context object for the tool, which may contain OAuth
          tokens.

    Returns:
        A `bigquery.Client` instance, configured with credentials if available.
    """
    auth_id = get_env_var("AUTH_ID")
    token_key = f"temp:{auth_id}"

    if token_key in tool_context.state:
        access_token = tool_context.state[token_key]
        creds = credentials.Credentials(token=access_token)
        return bigquery.Client(project=get_env_var("BQ_PROJECT_ID"), credentials=creds)


def get_database_settings(tool_context: ToolContext) -> dict:
    """Retrieves database settings, initializing them if not already present.

    This function checks if the database settings are already loaded in the tool
    context's state. If not, it calls `update_database_settings` to fetch them
    and stores them in the state for subsequent use.

    Args:
        tool_context: The context object for the tool, used for state management.

    Returns:
        A dictionary containing the database settings.
    """
    if "database_settings" not in tool_context.state:
        tool_context.state["database_settings"] = update_database_settings(tool_context)
    return tool_context.state["database_settings"]


def update_database_settings(tool_context: ToolContext) -> dict:
    """Fetches and updates the database settings.

    This function retrieves the latest database schema (DDL) for the configured
    BigQuery dataset and combines it with other settings, such as project and
    dataset IDs, and constants required for ChaseSQL.

    Args:
        tool_context: The context object for the tool, used to get the BigQuery
          client.

    Returns:
        A dictionary containing the updated database settings.
    """
    bq_client = get_bq_client(tool_context)
    ddl_schema = get_bigquery_schema(
        get_env_var("BQ_DATASET_ID"),
        client=bq_client,
        project_id=get_env_var("BQ_PROJECT_ID"),
    )
    database_settings = {
        "bq_project_id": get_env_var("BQ_PROJECT_ID"),
        "bq_dataset_id": get_env_var("BQ_DATASET_ID"),
        "bq_ddl_schema": ddl_schema,
        # Include ChaseSQL-specific constants.
        **chase_constants.chase_sql_constants_dict,
    }
    return database_settings


def get_bigquery_schema(dataset_id, client=None, project_id=None):
    """Retrieves schema and generates DDL with example values for a BigQuery dataset.

    This function inspects a BigQuery dataset, extracts the schema for each table,
    and generates `CREATE TABLE` DDL statements. It also includes example rows
    (up to 5) as `INSERT INTO` statements to provide context on the data.

    Args:
        dataset_id: The ID of the BigQuery dataset (e.g., 'my_dataset').
        client: An optional `bigquery.Client` instance. If not provided, a new
          one will be created.
        project_id: The ID of the Google Cloud Project.

    Returns:
        A string containing the generated DDL statements for all tables in the
        dataset.
    """

    if client is None:
        client = bigquery.Client(project=project_id)

    # dataset_ref = client.dataset(dataset_id)
    dataset_ref = bigquery.DatasetReference(project_id, dataset_id)

    ddl_statements = ""

    for table in client.list_tables(dataset_ref):
        table_ref = dataset_ref.table(table.table_id)
        table_obj = client.get_table(table_ref)

        # Check if table is a view
        if table_obj.table_type != "TABLE":
            continue

        ddl_statement = f"CREATE OR REPLACE TABLE `{table_ref}` (\n"

        for field in table_obj.schema:
            ddl_statement += f"  `{field.name}` {field.field_type}"
            if field.mode == "REPEATED":
                ddl_statement += " ARRAY"
            if field.description:
                ddl_statement += f" COMMENT '{field.description}'"
            ddl_statement += ",\n"

        ddl_statement = ddl_statement[:-2] + "\n);\n\n"

        # Add example values if available (limited to first row)
        rows = client.list_rows(table_ref, max_results=5).to_dataframe()
        if not rows.empty:
            ddl_statement += f"-- Example values for table `{table_ref}`:\n"
            for _, row in rows.iterrows():  # Iterate over DataFrame rows
                ddl_statement += f"INSERT INTO `{table_ref}` VALUES\n"
                example_row_str = "("
                for value in row.values:  # Now row is a pandas Series and has values
                    if isinstance(value, str):
                        example_row_str += f"'{value}',"
                    elif value is None:
                        example_row_str += "NULL,"
                    else:
                        example_row_str += f"{value},"
                example_row_str = (
                    example_row_str[:-1] + ");\n\n"
                )  # remove trailing comma
                ddl_statement += example_row_str

        ddl_statements += ddl_statement

    return ddl_statements


def initial_bq_nl2sql(
    question: str,
    tool_context: ToolContext,
) -> str:
    """Generates an initial SQL query from a natural language question.

    This function uses a large language model to convert a user's natural
    language question into a BigQuery SQL query. It constructs a prompt that
    includes the database schema and the user's question to guide the model in
    generating a relevant and syntactically correct query.

    Args:
        question: The natural language question from the user.
        tool_context: The tool context, used to access database settings and
          store the generated SQL query.

    Returns:
        A string containing the generated SQL query.
    """

    prompt_template = """
Você é um especialista em SQL para BigQuery encarregado de responder às perguntas dos usuários sobre tabelas do BigQuery, gerando consultas SQL no dialeto GoogleSql.  Sua tarefa é escrever uma consulta SQL do BigQuery que responda à seguinte pergunta, utilizando o contexto fornecido.

**Diretrizes:**

- **Referência de Tabela:** Sempre use o nome completo da tabela com o prefixo do banco de dados na instrução SQL.  As tabelas devem ser referenciadas usando um nome totalmente qualificado entre crases (`) e.g. `nome_do_projeto.nome_do_conjunto_de_dados.nome_da_tabela`.  Os nomes das tabelas diferenciam maiúsculas de minúsculas.
- **Junções (Joins):** Junte o mínimo de tabelas possível. Ao juntar tabelas, certifique-se de que todas as colunas de junção sejam do mesmo tipo de dados. Analise o banco de dados e o esquema da tabela fornecido para entender as relações entre colunas e tabelas.
- **Agregações:**  Use todas as colunas não agregadas da instrução `SELECT` na cláusula `GROUP BY`.
- **Sintaxe SQL:** Retorne SQL sintática e semanticamente correto para BigQuery com o mapeamento de relação apropriado (ou seja, project_id, proprietário, tabela e relação de coluna). Use a instrução SQL `AS` para atribuir um novo nome temporariamente a uma coluna de tabela ou até mesmo a uma tabela, sempre que necessário. Sempre coloque subconsultas e consultas de união entre parênteses.
- **Uso de Coluna:** Use *SOMENTE* os nomes de coluna (nome_da_coluna) mencionados no Esquema da Tabela. *NÃO* use nenhum outro nome de coluna. Associe `nome_da_coluna` mencionado no Esquema da Tabela apenas ao `nome_da_tabela` especificado no Esquema da Tabela.
- **FILTROS:** Você deve escrever a consulta de forma eficaz  para reduzir e minimizar o total de linhas a serem retornadas. Por exemplo, você pode usar filtros (como `WHERE`, `HAVING`, etc.) e funções de agregação (como 'COUNT', 'SUM', etc.) na consulta SQL.
- **LIMITAR LINHAS:**  O número máximo de linhas retornadas deve ser inferior a {MAX_NUM_ROWS}.

**Esquema:**

A estrutura do banco de dados é definida pelos seguintes esquemas de tabela (possivelmente com linhas de exemplo):

```
{SCHEMA}
```

**Pergunta em linguagem natural:**

```
{QUESTION}
```

**Pense Passo a Passo:** Considere cuidadosamente o esquema, a pergunta, as diretrizes e as melhores práticas descritas acima para gerar o SQL correto para o BigQuery.

   """

    ddl_schema = get_database_settings(tool_context)["bq_ddl_schema"]

    prompt = prompt_template.format(
        MAX_NUM_ROWS=MAX_NUM_ROWS, SCHEMA=ddl_schema, QUESTION=question
    )

    response = llm_client.models.generate_content(
        model=os.getenv("BASELINE_NL2SQL_MODEL"),
        contents=prompt,
        config={"temperature": 0.1},
    )

    sql = response.text
    if sql:
        sql = sql.replace("```sql", "").replace("```", "").strip()

    print("\n sql:", sql)

    tool_context.state["sql_query"] = sql

    return sql


def run_bigquery_validation(
    sql_string: str,
    tool_context: ToolContext,
) -> str:
    """Validates and executes a BigQuery SQL query.

    This function first cleans up the provided SQL string, then checks for any
    disallowed DML/DDL operations. It then executes the query against BigQuery.
    If the query is successful, it returns the results; otherwise, it returns an
    error message.

    Args:
        sql_string: The SQL query to validate and execute.
        tool_context: The tool context, used to get the BigQuery client and
          store the query results.

    Returns:
        A dictionary containing either the 'query_result' on success or an
        'error_message' on failure.
    """

    def cleanup_sql(sql_string):
        """Processes the SQL string to get a printable, valid SQL string."""

        # 1. Remove backslashes escaping double quotes
        sql_string = sql_string.replace('\\"', '"')

        # 2. Remove backslashes before newlines (the key fix for this issue)
        sql_string = sql_string.replace("\\\n", "\n")  # Corrected regex

        # 3. Replace escaped single quotes
        sql_string = sql_string.replace("\\'", "'")

        # 4. Replace escaped newlines (those not preceded by a backslash)
        sql_string = sql_string.replace("\\n", "\n")

        # 5. Add limit clause if not present
        if "limit" not in sql_string.lower():
            sql_string = sql_string + " limit " + str(MAX_NUM_ROWS)

        return sql_string

    logging.info("Validating SQL: %s", sql_string)
    sql_string = cleanup_sql(sql_string)
    logging.info("Validating SQL (after cleanup): %s", sql_string)

    final_result = {"query_result": None, "error_message": None}

    # More restrictive check for BigQuery - disallow DML and DDL
    if re.search(
        r"(?i)(update|delete|drop|insert|create|alter|truncate|merge)", sql_string
    ):
        final_result["error_message"] = (
            "Invalid SQL: Contains disallowed DML/DDL operations."
        )
        return final_result

    try:
        bq_client = get_bq_client(tool_context)
        query_job = bq_client.query(sql_string)
        results = query_job.result()  # Get the query results

        if results.schema:  # Check if query returned data
            rows = [
                {
                    key: (
                        value
                        if not isinstance(value, datetime.date)
                        else value.strftime("%Y-%m-%d")
                    )
                    for (key, value) in row.items()
                }
                for row in results
            ][
                :MAX_NUM_ROWS
            ]  # Convert BigQuery RowIterator to list of dicts
            # return f"Valid SQL. Results: {rows}"
            final_result["query_result"] = rows

            tool_context.state["query_result"] = rows

        else:
            final_result["error_message"] = (
                "Valid SQL. Query executed successfully (no results)."
            )

    except (
        Exception
    ) as e:  # Catch generic exceptions from BigQuery  # pylint: disable=broad-exception-caught
        final_result["error_message"] = f"Invalid SQL: {e}"

    print("\n run_bigquery_validation final_result: \n", final_result)

    return final_result
