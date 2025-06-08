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

"""Modelo de prompt para fazer quaisquer correções na tradução de SQL."""

CORRECTION_PROMPT_TEMPLATE_V1_0 = """
Você é um especialista em múltiplos bancos de dados e dialetos SQL.
É fornecida uma consulta SQL formatada para o dialeto SQL:
{sql_dialect}

A consulta SQL é:
{sql_query}
{schema_insert}
Esta consulta SQL pode ter os seguintes erros:
{errors}

Por favor, corrija a consulta SQL para garantir que ela esteja formatada corretamente para o dialeto SQL:
{sql_dialect}

NÃO altere nenhum nome de tabela ou coluna na consulta. No entanto, você pode qualificar nomes de colunas com nomes de tabelas.
Não altere nenhum literal na consulta.
Você pode *apenas* reescrever a consulta para que ela seja formatada corretamente para o dialeto SQL especificado.
Não retorne nenhuma outra informação além da consulta SQL corrigida.

Consulta SQL corrigida:
"""
