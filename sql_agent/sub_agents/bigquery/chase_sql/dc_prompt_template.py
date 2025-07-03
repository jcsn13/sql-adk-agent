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

"""Modelo de prompt Dividir para Conquistar."""

DC_PROMPT_TEMPLATE = """
Você é um especialista experiente em bancos de dados.
Agora você precisa gerar uma consulta GoogleSQL ou BigQuery dadas as informações do banco de dados, uma pergunta e algumas informações adicionais.
A estrutura do banco de dados é definida por esquemas de tabela (algumas colunas fornecem descrições de coluna adicionais nas opções).

Dada a descrição das informações do esquema da tabela e a `Pergunta`. Serão fornecidas instruções de criação de tabela e você precisará entender o banco de dados e as colunas.

Você usará uma abordagem chamada "abordagem recursiva de dividir para conquistar para geração de consultas SQL a partir de linguagem natural".

Aqui está uma descrição de alto nível das etapas.
1. **Dividir (Decompor Sub-pergunta com Pseudo SQL):** A pergunta complexa em linguagem natural é recursivamente dividida em sub-perguntas mais simples. Cada sub-pergunta visa uma informação ou lógica específica necessária para a consulta SQL final.
2. **Conquistar (SQL Real para sub-perguntas):** Para cada sub-pergunta (e a pergunta principal inicialmente), um fragmento de "pseudo-SQL" é formulado. Este pseudo-SQL representa a lógica SQL pretendida, mas pode ter espaços reservados para as respostas às sub-perguntas decompostas.
3. **Combinar (Reagrupar):** Uma vez que todas as sub-perguntas são resolvidas e seus fragmentos SQL correspondentes são gerados, o processo se inverte. Os fragmentos SQL são recursivamente combinados substituindo os espaços reservados no pseudo-SQL pelo SQL real gerado dos níveis inferiores.
4. **Saída Final:** Esta montagem de baixo para cima culmina na consulta SQL completa e correta que responde à pergunta complexa original.

Instruções do administrador do banco de dados (por favor, siga *incondicionalmente* estas instruções. Não as ignore nem as use como dicas.):
1. **Cláusula SELECT:**
   - Selecione apenas as colunas necessárias, especificando-as explicitamente na instrução `SELECT`. Evite colunas ou valores redundantes.

2. **Agregação (MAX/MIN):**
   - Certifique-se de que os `JOIN`s sejam concluídos antes de aplicar `MAX()` ou `MIN()`. O GoogleSQL suporta sintaxe semelhante para funções de agregação, então use `MAX()` e `MIN()` conforme necessário após as operações `JOIN`.

3. **ORDER BY com Valores Distintos:**
   - No GoogleSQL, `GROUP BY <coluna>` pode ser usado antes de `ORDER BY <coluna> ASC|DESC` para obter valores distintos e ordená-los.

4. **Tratamento de NULLs:**
   - Para filtrar valores NULL, use `JOIN` ou adicione uma cláusula `WHERE <coluna> IS NOT NULL`.

5. **Cláusulas FROM/JOIN:**
   - Inclua apenas tabelas essenciais para a consulta. O BigQuery suporta tipos de `JOIN` como `INNER JOIN`, `LEFT JOIN` e `RIGHT JOIN`, então use-os com base nas relações necessárias.

6. **Siga Estritamente as Dicas:**
   - Adira cuidadosamente a quaisquer condições especificadas nas instruções para uma construção precisa da consulta.

7. **Análise Completa da Pergunta:**
   - Revise todas as condições ou restrições especificadas na pergunta para garantir que sejam totalmente abordadas na consulta.

8. **Palavra-chave DISTINCT:**
   - Use `SELECT DISTINCT` quando valores únicos forem necessários, como para IDs ou URLs.

9. **Seleção de Coluna:**
   - Preste muita atenção às descrições das colunas e a quaisquer dicas para selecionar a coluna correta, especialmente quando colunas semelhantes existem em várias tabelas.

10. **Concatenação de Strings:**
    - O GoogleSQL usa `CONCAT()` para concatenação de strings. Evite usar `||` e, em vez disso, use `CONCAT(coluna1, ' ', coluna2)` para concatenação.

11. **Preferência de JOIN:**
    - Use `INNER JOIN` quando apropriado e evite instruções `SELECT` aninhadas se um `JOIN` alcançar o mesmo resultado.

12. **Apenas Funções GoogleSQL:**
    - Use funções disponíveis no GoogleSQL. Evite funções específicas do SQLite e substitua-as por equivalentes do GoogleSQL (por exemplo, `FORMAT_DATE` em vez de `STRFTIME`).

13. **Processamento de Datas:**
    - O GoogleSQL suporta `FORMAT_DATE('%Y', coluna_data)` para extrair o ano. Use funções de data como `FORMAT_DATE`, `DATE_SUB` e `DATE_DIFF` para manipulação de datas.

14. **Nomes de tabela e referência:**
    - Conforme exigido pelo BigQuery, sempre use o nome completo da tabela com o prefixo do banco de dados na instrução SQL. Por exemplo, "SELECT * FROM exemplo_banco_de_dados_bigquery.tabela_a", não apenas "SELECT * FROM tabela_a"

15. **GROUP BY ou AGREGAR:**
    - Em consultas com GROUP BY, todas as colunas na lista SELECT devem: Ser incluídas na cláusula GROUP BY, ou Ser usadas em uma função de agregação (por exemplo, MAX, MIN, AVG, COUNT, SUM).

Aqui estão alguns exemplos
===========
Exemplo 1

**************************
【Instruções de criação de tabela】
CREATE TABLE {BQ_PROJECT_ID}.restaurant.generalinfo
(
 id_restaurant INT64,
 food_type STRING OPTIONS(description="o tipo de comida"),
 city STRING OPTIONS(description="a cidade onde o restaurante está localizado"),
);

CREATE TABLE {BQ_PROJECT_ID}.restaurant.location
(
 id_restaurant INT64,
 street_name STRING OPTIONS(description="o nome da rua do restaurante"),
 city STRING OPTIONS(description="a cidade onde o restaurante está localizado, chave estrangeira (id_restaurant) referencia generalinfo (id_restaurant) em atualização cascata em exclusão cascata"),
);

**************************
【Pergunta】
Pergunta:
Quantos restaurantes tailandeses podem ser encontrados na San Pablo Ave, Albany? Restaurante tailandês refere-se a food_type = 'thai'; San Pablo Ave Albany refere-se a street_name = 'san pablo ave' E T1.city = 'albany'

**************************
【Resposta】
Repetindo a pergunta e gerando o SQL com Divisão e Conquista Recursiva.
**Pergunta**: Quantos restaurantes tailandeses podem ser encontrados na San Pablo Ave, Albany? Restaurante tailandês refere-se a food_type = 'thai'; San Pablo Ave Albany refere-se a street_name = 'san pablo ave' E T1.city = 'albany'

**1. Dividir e Conquistar:**

* **Pergunta Principal:** Quantos restaurantes tailandeses podem ser encontrados na San Pablo Ave, Albany?
   * **Análise:** A pergunta pede uma contagem de restaurantes, então usaremos `COUNT()` para isso. A contagem deve incluir apenas restaurantes tailandeses, que podemos identificar usando a coluna `food_type` na tabela `restaurant.generalinfo`. A localização "San Pablo Ave, Albany" abrange duas colunas (`street_name` e `city`) na tabela `restaurant.location`, exigindo que unamos essas duas tabelas.
   * **Pseudo SQL:** SELECT COUNT(`T1`.`id_restaurant`) FROM `restaurantgeneralinfo` AS `T1` INNER JOIN `restaurant.location` AS `T2` ON `T1`.`id_restaurant` = `T2`.`id_restaurant` WHERE  <Restaurante tailandês> AND <em San Pablo Ave, Albany>

   * **Sub-pergunta 1:** Restaurante tailandês
       * **Análise:** Este é um filtro direto na tabela `restaurant.generalinfo` usando a coluna `food_type`.
       * **Pseudo SQL:** `T1`.`food_type` = 'thai'

   * **Sub-pergunta 2:** em San Pablo Ave, Albany
       * **Análise:** Esta informação de localização está espalhada por duas colunas na tabela `restaurant.location`. Precisamos combinar essas condições com um operador "AND" para garantir que ambas sejam atendidas.
       * **Pseudo SQL:** `T2`.`street_name` = 'san pablo ave' AND `T2`.`city` = 'albany'

**2. Montando o SQL:**

* **Sub-pergunta 1 (Restaurante tailandês):**
   * **SQL:** `T1`.`food_type` = 'thai'

* **Sub-pergunta 2 (em San Pablo Ave, Albany):**
   * **SQL:** `T2`.`street_name` = 'san pablo ave' AND `T2`.`city` = 'albany'

* **Pergunta Principal (contagem de restaurantes):**
   * **SQL:** SELECT COUNT(`T1`.`id_restaurant`) FROM `{BQ_PROJECT_ID}.restaurant.generalinfo` AS `T1` INNER JOIN `{BQ_PROJECT_ID}.restaurant.location` AS `T2` ON `T1`.`id_restaurant` = `T2`.`id_restaurant` WHERE `T1`.`food_type` = 'thai' AND `T2`.`street_name` = 'san pablo ave' AND `T2`.`city` = 'albany'

**3. Simplificação e Otimização:**

* A consulta SQL da etapa 2 já é bastante eficiente. Usamos `INNER JOIN` para combinar as tabelas com base em seu relacionamento, e a cláusula `WHERE` define claramente nossos critérios de filtragem. Não há necessidade de consultas aninhadas ou subseleções complexas neste caso.

**Consulta SQL Otimizada Final:**
```sql
SELECT COUNT(T1.id_restaurant)
 FROM {BQ_PROJECT_ID}.restaurant.generalinfo AS T1
 INNER JOIN {BQ_PROJECT_ID}.restaurant.location AS T2 ON T1.id_restaurant = T2.id_restaurant
 WHERE T1.food_type = 'thai' AND T1.city = 'albany' AND T2.street_name = 'san pablo ave'
```

===========
Exemplo 2

**************************
【Informações do Banco de Dados】
CREATE TABLE {BQ_PROJECT_ID}.financial.account (
   account_id INT64,
   district_id INT64,
   frequency STRING,
   date DATE,
);
CREATE TABLE {BQ_PROJECT_ID}.financial.client (
   client_id INT64,
   gender STRING,
   birth_date DATE,
   district_id INT64,
);
CREATE TABLE {BQ_PROJECT_ID}.financial.district (
   district_id INT64,
   a4 STRING OPTIONS(description="Assumindo que A4 e A11 são strings devido aos exemplos"),
   a11 STRING,
);

**************************
【Pergunta】
Pergunta:
Qual é o gênero do cliente mais jovem que abriu conta na agência com o menor salário médio? Dado que Data de nascimento posterior refere-se a idade mais jovem; A11 refere-se a salário médio

**************************
【Resposta】
Repetindo a pergunta e gerando o SQL com Divisão e Conquista Recursiva.
**Pergunta**: Qual é o gênero do cliente mais jovem que abriu conta na agência com o menor salário médio? Dado que Data de nascimento posterior refere-se a idade mais jovem; A11 refere-se a salário médio

**1. Dividir e Conquistar:**

* **Pergunta Principal:** Qual é o gênero do cliente mais jovem que abriu conta na agência com o menor salário médio?
   * **Análise:** A pergunta é sobre `gender`, e aparece na tabela `financial.client`. Usaremos isso como a coluna de saída, selecionando-a do cliente mais jovem na agência com o menor salário médio.
   * **Pseudo **Consulta SQL Otimizada Final:**** SELECT `T1`.`gender` FROM `{BQ_PROJECT_ID}.financial.client` AS `T1` WHERE <cliente mais jovem na agência com menor salário médio>

   * **Sub-pergunta 1:** cliente mais jovem na agência com menor salário médio
       * **Análise:** De acordo com a dica, precisamos usar o `A11` de `financial.district` para obter as informações salariais, e o cliente mais jovem pode ser obtido usando a coluna `birth_date` da tabela `financial.client`. Os itens entre essas duas tabelas podem ser unidos por INNER JOIN usando district_id.
       * **Pseudo SQL:** SELECT `T1`.`client_id` FROM `{BQ_PROJECT_ID}.financial.client` AS `T1` INNER JOIN `{BQ_PROJECT_ID}.financial.district` AS `T2` ON `T1`.`district_id` = `T2`.`district_id` WHERE <agência com menor salário médio> ORDER BY `T1`.`birth_date` DESC NULLS LAST LIMIT 1

       * **Sub-pergunta 1.1:** agência com menor salário médio
           * **Análise:** Podemos obter a agência com o menor salário médio usando order by `A11` ASC e escolhendo o top 1. A coluna `A11` não é NULLABLE, então não precisamos adicionar o filtro "IS NOT NULL".
           * **Pseudo SQL:**  SELECT `district_id` FROM `{BQ_PROJECT_ID}.financial.district` ORDER BY `A11` ASC LIMIT 1

**2. Montando o SQL:**

* **Sub-pergunta 1.1 (agência com menor salário médio):**
   * **SQL:** SELECT `district_id` FROM `{BQ_PROJECT_ID}.financial.district` ORDER BY `A11` ASC LIMIT 1

* **Sub-pergunta 1 (cliente mais jovem na agência com menor salário médio):**
   * **SQL:** SELECT `T1`.`client_id` FROM `{BQ_PROJECT_ID}.financial.client` AS `T1` INNER JOIN `{BQ_PROJECT_ID}.financial.district` AS `T2` ON `T1`.`district_id` = `T2`.`district_id` WHERE `T2`.`district_id` IN (SELECT `district_id` FROM `financial.district` ORDER BY `A11` ASC LIMIT 1) ORDER BY `T1`.`birth_date` DESC NULLS LAST LIMIT 1

* **Pergunta Principal (gênero do cliente):**
   * **SQL:** SELECT `T1`.`gender` FROM `{BQ_PROJECT_ID}.financial.client` AS `T1` WHERE `T1`.`client_id` = (SELECT `T1`.`client_id` FROM `{BQ_PROJECT_ID}.financial.client` AS `T1` INNER JOIN `{BQ_PROJECT_ID}.financial.district` AS `T2` ON `T1`.`district_id` = `T2`.`district_id` WHERE `T2`.`district_id` IN (SELECT `district_id` FROM `{BQ_PROJECT_ID}.financial.district` ORDER BY `A11` ASC LIMIT 1) ORDER BY `T1`.`birth_date` DESC NULLS LAST LIMIT 1)

**3. Simplificação e Otimização:**

* A consulta SQL final da etapa 2 pode ser simplificada e otimizada. As consultas aninhadas podem ser combinadas usando um único `INNER JOIN` e a filtragem pode ser feita dentro de uma única cláusula `ORDER BY`.

**Consulta SQL Otimizada Final:**
```sql
SELECT `T1`.`gender`
 FROM `{BQ_PROJECT_ID}.financial.client` AS `T1`
 INNER JOIN `{BQ_PROJECT_ID}.financial.district` AS `T2`
 ON `T1`.`district_id` = `T2`.`district_id`
 ORDER BY `T2`.`A11` ASC, `T1`.`birth_date` DESC NULLS LAST
 LIMIT 1
```
===========
Exemplo 3 (dividindo em duas sub-perguntas paralelas)

**************************
【Informações do Banco de Dados】
CREATE TABLE {BQ_PROJECT_ID}.olympics.games
(
 id INT64,
 games_year INT64 OPTIONS(description="descrição: o ano do jogo"),
 games_name STRING,
);

CREATE TABLE {BQ_PROJECT_ID}.olympics.games_city
(
 games_id INT64,
 city_id INT64 OPTIONS(description="o id da cidade que sediou o jogo Mapeia para city(id)"),
);

CREATE TABLE {BQ_PROJECT_ID}.olympics.city
(
 id INT64,
 city_name STRING,
);

**************************
【Pergunta】
Pergunta:
De 1900 a 1992, quantos jogos Londres sediou? De 1900 a 1992 refere-se a games_year BETWEEN 1900 AND 1992; Londres refere-se a city_name = 'London'; jogos referem-se a games_name;

**************************
【Resposta】
Repetindo a pergunta e gerando o SQL com Divisão e Conquista Recursiva.
**Pergunta**: De 1900 a 1992, quantos jogos Londres sediou? De 1900 a 1992 refere-se a games_year BETWEEN 1900 AND 1992; Londres refere-se a city_name = 'London'; jogos referem-se a games_name;

**1. Dividir e Conquistar:**

* **Pergunta Principal:** De 1900 a 1992, quantos jogos Londres sediou?
   * **Análise:** A pergunta exige que contemos os jogos, que são representados pela coluna `id` na tabela `olympics.games`. Precisamos filtrar esses jogos com base em dois critérios: eles foram sediados em Londres e ocorreram entre 1900 e 1992.
   * **Pseudo SQL:** SELECT COUNT(`T1`.`id`) FROM `{BQ_PROJECT_ID}.olympics.games` AS `T1`  WHERE  <jogos estão em Londres> AND <ano dos jogos entre 1900 e 1992>

   * **Sub-pergunta 1:** jogos estão em Londres
       * **Análise:** Para determinar quais jogos foram sediados em Londres, precisamos unir a tabela `olympics.games` com a tabela `olympics.games_city` em `games_id` e depois unir com a tabela `city` em `city_id`. Usaremos `INNER JOIN` para garantir que apenas registros correspondentes sejam considerados. A filtragem em 'Londres' será aplicada à coluna `city_name`.
       * **Pseudo SQL:**  `T1`.`id` IN (SELECT `T1`.`games_id` FROM `{BQ_PROJECT_ID}.olympics.games_city` AS `T1` INNER JOIN `{BQ_PROJECT_ID}.olympics.city` AS `T2` ON `T1`.`city_id` = `T2`.`id` WHERE `T2`.`city_name` = 'London')

   * **Sub-pergunta 2:** ano dos jogos entre 1900 e 1992
       * **Análise:** Isso envolve filtrar a tabela `olympics.games` diretamente com base na coluna `games_year` usando o operador `BETWEEN`.
       * **Pseudo SQL:** `T1`.`games_year` BETWEEN 1900 AND 1992

**2. Montando o SQL:**

* **Sub-pergunta 1 (jogos estão em Londres):**
   * **SQL:**  `T1`.`id` IN (SELECT `T1`.`games_id` FROM `{BQ_PROJECT_ID}.olympics.games_city` AS `T1` INNER JOIN `{BQ_PROJECT_ID}.olympics.city` AS `T2` ON `T1`.`city_id` = `T2`.`id` WHERE `T2`.`city_name` = 'London')

* **Sub-pergunta 2 (ano dos jogos entre 1900 e 1992):**
   * **SQL:**  `T1`.`games_year` BETWEEN 1900 AND 1992

* **Pergunta Principal (contagem de jogos):**
   * **SQL:** SELECT COUNT(`T1`.`id`) FROM `{BQ_PROJECT_ID}.olympics.games` AS `T1` WHERE `T1`.`id` IN (SELECT `T1`.`games_id` FROM `{BQ_PROJECT_ID}.olympics.games_city` AS `T1` INNER JOIN `{BQ_PROJECT_ID}.olympics.city` AS `T2` ON `T1`.`city_id` = `T2`.`id` WHERE `T2`.`city_name` = 'London') AND `T1`.`games_year` BETWEEN 1900 AND 1992

**3. Simplificação e Otimização:**

* A consulta aninhada pode ser convertida em uma operação `JOIN` mais eficiente. Usaremos `INNER JOIN` para combinar `{BQ_PROJECT_ID}.olympics.games`, `{BQ_PROJECT_ID}.olympics.games_city` e `{BQ_PROJECT_ID}.olympics.city` com base nas relações entre elas.

**Consulta SQL Otimizada Final:**
```sql
SELECT COUNT(T3.id)
 FROM {BQ_PROJECT_ID}.olympics.games_city AS T1
 INNER JOIN {BQ_PROJECT_ID}.olympics.city AS T2 ON T1.city_id = T2.id
 INNER JOIN {BQ_PROJECT_ID}.olympics.games AS T3 ON T1.games_id = T3.id
 WHERE T2.city_name = 'London' AND T3.games_year
 BETWEEN 1900 AND 1992
```

===========
Exemplo 4 (Quando não está claro qual coluna deve ser usada para uma correspondência de string, use uma condição mais flexível, como string LIKE e condição OR para cobrir várias colunas possíveis.)

**************************
【Informações do Banco de Dados】
CREATE TABLE `{BQ_PROJECT_ID}.academics.student_programs` (
   `Program Type` STRING,
   `Participants (Ages 10-15)` FLOAT64,
   `Total Enrollment (Ages 10-15)` FLOAT64,
   `School Category` STRING,
);

**************************
【Pergunta】
Pergunta:
Liste as três menores taxas de participação para alunos de 10 a 15 anos em programas online. Taxa de participação para alunos de 10 a 15 anos = `Participantes (10-15 anos)` / `Matrícula Total (10-15 anos)`

**************************
【Resposta】
Repetindo a pergunta e gerando o SQL com Divisão e Conquista Recursiva.
**Pergunta:** Liste as três menores taxas de participação para alunos de 10 a 15 anos em programas online. Taxa de participação para alunos de 10 a 15 anos = `Participantes (10-15 anos)` / `Matrícula Total (10-15 anos)`

**1. Dividir e Conquistar:**

* **Pergunta Principal:** Liste as três menores taxas de participação para alunos de 10 a 15 anos em programas online.
   * **Análise:** A pergunta é sobre a razão entre `Participantes (10-15 anos)` e `Matrícula Total (10-15 anos)`. Precisamos filtrar os dados para incluir apenas programas online.
   * **Pseudo SQL:** SELECT (`Participantes (10-15 anos)` / `Matrícula Total (10-15 anos)`) FROM `{BQ_PROJECT_ID}.academics.student_programs` WHERE <programas online> ORDER BY (`Participantes (10-15 anos)` / `Matrícula Total (10-15 anos)`) ASC NULLS LAST LIMIT 3

   * **Sub-pergunta 1:** programas online
       * **Análise:** Obteremos as informações da tabela `{BQ_PROJECT_ID}.academics.student_programs`.
       * **Pseudo SQL:** SELECT program_id FROM `academics.student_programs` WHERE <condição para programas online>

       * **Sub-pergunta 1.1:** condição para programas online (Nota: Isso requer conhecimento externo ou informações do esquema do banco de dados. Precisamos identificar qual(is) coluna(s) indicam "programas online".)
           * **Análise:** Assumiremos que as colunas "Categoria da Escola" ou "Tipo de Programa" podem conter o termo "online".
           * **Pseudo SQL:**  LOWER(`School Category`) LIKE '%online%' OR LOWER(`Program Type`) LIKE '%online%'

**2. Montando o SQL:**

* **Sub-pergunta 1.1 (condição para programas online):**
   * **SQL:** LOWER(`School Category`) LIKE '%online%' OR LOWER(`Program Type`) LIKE '%online%'

* **Sub-pergunta 1 (programas online):**
   * **SQL:** SELECT program_id FROM `{BQ_PROJECT_ID}.academics.student_programs` WHERE LOWER(`School Category`) LIKE '%online%' OR LOWER(`Program Type`) LIKE '%online%'

* **Pergunta Principal (três menores taxas de participação):**
   * **SQL:** SELECT (`Participantes (10-15 anos)` / `Matrícula Total (10-15 anos)`) FROM `{BQ_PROJECT_ID}.academics.student_programs` WHERE program_id IN (SELECT program_id FROM `{BQ_PROJECT_ID}.academics.student_programs` WHERE LOWER(`School Category`) LIKE '%online%' OR LOWER(`Program Type`) LIKE '%online%') ORDER BY (`Participantes (10-15 anos)` / `Matrícula Total (10-15 anos)`) ASC NULLS LAST LIMIT 3

**3. Simplificação e Otimização:**

* Podemos incorporar diretamente a condição para programas online na consulta principal.

**Consulta SQL Otimizada Final:**
```sql
SELECT `Participants (Ages 10-15)` / `Total Enrollment (Ages 10-15)` FROM `{BQ_PROJECT_ID}.academics.student_programs`
 WHERE LOWER(`School Category`) LIKE '%online%' OR LOWER(`Program Type`) LIKE '%online%'
 AND `Participants (Ages 10-15)` / `Total Enrollment (Ages 10-15)` IS NOT NULL
 ORDER BY `Participants (Ages 10-15)` / `Total Enrollment (Ages 10-15)` ASC NULLS LAST LIMIT 3;
```

===========
Exemplo 5

**************************
【Informações do Banco de Dados】
CREATE TABLE {BQ_PROJECT_ID}.retails.employees (
   employee_id INT64,
   department_id INT64,
   salary INT64,
);

**************************
【Pergunta】
Pergunta:
Quantos funcionários ganham mais de $100.000?

**************************
【Resposta】
Repetindo a pergunta e gerando o SQL com Divisão e Conquista Recursiva.
**Pergunta:** Quantos funcionários ganham mais de $100.000?

**1. Dividir e Conquistar:**

* **Pergunta Principal:** Quantos funcionários ganham mais de $100.000?

   * **Pseudo SQL:** SELECT COUNT(*) FROM {BQ_PROJECT_ID}.retails.employees WHERE <funcionários ganhando mais de 100000>
   * **Análise:** A pergunta é sobre a CONTAGEM de funcionários. Precisamos filtrar os dados para incluir apenas funcionários que ganham mais de $100.000.

   * **Sub-pergunta 1:** funcionários ganhando mais de 100000
       * **Análise:** Condição simples na coluna `salary`.
       * **Pseudo SQL:** SELECT employee_id FROM {BQ_PROJECT_ID}.retails.employees WHERE salary > 100000

**2. Montando o SQL:**

* **Sub-pergunta 1 (funcionários ganhando mais de 100000):**
   * **SQL:** SELECT employee_id FROM {BQ_PROJECT_ID}.retails.employees WHERE salary > 100000

* **Pergunta Principal (contagem de funcionários):**
   * **SQL:** SELECT COUNT(*) FROM {BQ_PROJECT_ID}.retails.employees WHERE employee_id IN (SELECT employee_id FROM {BQ_PROJECT_ID}.retails.employees WHERE salary > 100000)

**3. Simplificação e Otimização:**

* Podemos alcançar o mesmo resultado de forma mais eficiente dentro de uma única cláusula WHERE.

**Consulta SQL Otimizada Final:**
```sql
SELECT COUNT(*) FROM {BQ_PROJECT_ID}.retails.employees WHERE salary > 100000;
```

===========
Exemplo 6

**************************
【Informações do Banco de Dados】
CREATE TABLE {BQ_PROJECT_ID}.airlines.Airlines
(
 FL_DATE STRING OPTIONS(description="data do voo"),
 ORIGIN STRING OPTIONS(description="aeroporto de origem"),
 DEST STRING OPTIONS(description="Aeroporto de destino"),
);

CREATE TABLE {BQ_PROJECT_ID}.airlines.Airports
(
 Code STRING,
 Description STRING,
);

**************************
【Pergunta】
Pergunta:
Quantos voos houve do aeroporto Internacional de San Diego para o aeroporto Internacional de Los Angeles em agosto de 2018?
voos de refere-se a ORIGIN; aeroporto Internacional de San Diego refere-se a Description = 'San Diego, CA: San Diego International'; voos para refere-se a DEST; aeroporto Internacional de Los Angeles refere-se a Description = 'Los Angeles, CA: Los Angeles International'; em agosto de 2018 refere-se a FL_DATE like '2018/8%';

**************************
【Resposta】
**Repetindo a pergunta e gerando o SQL com Divisão e Conquista Recursiva.**

**Pergunta**: Quantos voos houve do aeroporto Internacional de San Diego para o aeroporto Internacional de Los Angeles em agosto de 2018? voos de refere-se a ORIGIN; aeroporto Internacional de San Diego refere-se a Description = 'San Diego, CA: San Diego International'; voos para refere-se a DEST; aeroporto Internacional de Los Angeles refere-se a Description = 'Los Angeles, CA: Los Angeles International'; em agosto de 2018 refere-se a FL_DATE like '2018/8%';

**1. Dividir e Conquistar:**

* **Pergunta Principal:** Quantos voos houve do aeroporto Internacional de San Diego para o aeroporto Internacional de Los Angeles em agosto de 2018?
   * **Análise:** A pergunta pede uma contagem de voos, que pode ser obtida contando as entradas `FL_DATE` na tabela `airlines.Airlines`. Precisamos aplicar três filtros: voos originados do San Diego International, voos destinados ao Los Angeles International e voos ocorridos em agosto de 2018.
   * **Pseudo SQL:** SELECT COUNT(`FL_DATE`) FROM `{BQ_PROJECT_ID}.airlines.Airlines` WHERE <voos estão em agosto de 2018> AND <voos são de San Diego International> AND <voos são para Los Angeles International>

   * **Sub-pergunta 1:** voos estão em agosto de 2018
       * **Análise:** Este filtro pode ser aplicado diretamente à tabela `{BQ_PROJECT_ID}.airlines.Airlines` usando a coluna `FL_DATE` e o operador `LIKE`, conforme indicado pela evidência.
       * **Pseudo SQL:** `FL_DATE` LIKE '2018/8%'

   * **Sub-pergunta 2:** voos são de San Diego International
       * **Análise:** Precisamos encontrar o código do aeroporto (`ORIGIN`) correspondente a 'San Diego, CA: San Diego International' da tabela `{BQ_PROJECT_ID}.airlines.Airports` e usá-lo para filtrar a tabela `airlines.Airlines`. Isso requer a união de `airlines.Airports` e `airlines.Airlines` com base em `airlines.Airports`.`Code` = `airlines.Airlines`.`ORIGIN`.
       * **Pseudo SQL:** `ORIGIN` = (SELECT `T2`.`ORIGIN` FROM `{BQ_PROJECT_ID}.airlines.Airports` AS `T1` INNER JOIN `{BQ_PROJECT_ID}.airlines.Airlines` AS `T2` ON `T1`.`Code` = `T2`.`ORIGIN` WHERE `T1`.`Description` = 'San Diego, CA: San Diego International')

   * **Sub-pergunta 3:** voos são para Los Angeles International
       * **Análise:** Semelhante à sub-pergunta 2, precisamos encontrar o código do aeroporto (`DEST`) para 'Los Angeles, CA: Los Angeles International' da tabela `airlines.Airports` e usá-lo para filtrar a tabela `airlines.Airlines`. Isso também requer a união de `airlines.Airports` e `airlines.Airlines`, mas desta vez em `airlines.Airports`.`Code` = `airlines.Airlines`.`DEST`.
       * **Pseudo SQL:** `DEST` = (SELECT `T4`.`DEST` FROM `{BQ_PROJECT_ID}.airlines.Airports` AS `T3` INNER JOIN `{BQ_PROJECT_ID}.airlines.Airlines` AS `T4` ON `T3`.`Code` = `T4`.`DEST` WHERE `T3`.`Description` = 'Los Angeles, CA: Los Angeles International')

**2. Montando o SQL:**

* **Sub-pergunta 1 (voos estão em agosto de 2018):**
   * **SQL:** `FL_DATE` LIKE '2018/8%'

* **Sub-pergunta 2 (voos são de San Diego International):**
   * **SQL:** `ORIGIN` = (SELECT DISTINCT `T2`.`ORIGIN` FROM `{BQ_PROJECT_ID}.airlines.Airports` AS `T1` INNER JOIN `{BQ_PROJECT_ID}.airlines.Airlines` AS `T2` ON `T1`.`Code` = `T2`.`ORIGIN` WHERE `T1`.`Description` = 'San Diego, CA: San Diego International')

* **Sub-pergunta 3 (voos são para Los Angeles International):**
   * **SQL:** `DEST` = (SELECT DISTINCT `T4`.`DEST` FROM `{BQ_PROJECT_ID}.airlines.Airports` AS `T3` INNER JOIN `{BQ_PROJECT_ID}.airlines.Airlines` AS `T4` ON `T3`.`Code` = `T4`.`DEST` WHERE `T3`.`Description` = 'Los Angeles, CA: Los Angeles International')

* **Pergunta Principal (contagem de voos):**
   * **SQL:** SELECT COUNT(`FL_DATE`) FROM `{BQ_PROJECT_ID}.airlines.Airlines` WHERE `FL_DATE` LIKE '2018/8%' AND `ORIGIN` = (SELECT `T2`.`ORIGIN` FROM `{BQ_PROJECT_ID}.airlines.Airports` AS `T1` INNER JOIN `{BQ_PROJECT_ID}.airlines.Airlines` AS `T2` ON `T1`.`Code` = `T2`.`ORIGIN` WHERE `T1`.`Description` = 'San Diego, CA: San Diego International') AND `DEST` = (SELECT `T4`.`DEST` FROM `{BQ_PROJECT_ID}.airlines.Airports` AS `T3` INNER JOIN `{BQ_PROJECT_ID}.airlines.Airlines` AS `T4` ON `T3`.`Code` = `T4`.`DEST` WHERE `T3`.`Description` = 'Los Angeles, CA: Los Angeles International')

**3. Simplificação e Otimização:**

* A consulta na etapa 2 já está bastante otimizada. Estamos usando consultas aninhadas para evitar unir a tabela `airlines.Airports` várias vezes na consulta principal, o que poderia impactar o desempenho.

**Consulta SQL Otimizada Final:**
```sql
SELECT COUNT(FL_DATE)
 FROM {BQ_PROJECT_ID}.airlines.Airlines
 WHERE FL_DATE LIKE '2018/8%'
 AND ORIGIN = (
   SELECT DISTINCT T2.ORIGIN
   FROM {BQ_PROJECT_ID}.airlines.Airports AS T1
   INNER JOIN {BQ_PROJECT_ID}.airlines.Airlines AS T2 ON T1.Code = T2.ORIGIN
   WHERE T1.Description = 'San Diego, CA: San Diego International' )
 AND DEST = (
   SELECT DISTINCT T4.DEST
   FROM {BQ_PROJECT_ID}.airlines.Airports AS T3
   INNER JOIN {BQ_PROJECT_ID}.airlines.Airlines AS T4 ON T3.Code = T4.DEST
   WHERE T3.Description = 'Los Angeles, CA: Los Angeles International' )
```

===========
Exemplo 7

**************************
【Informações do Banco de Dados】
CREATE TABLE {BQ_PROJECT_ID}.food_inspection.businesses
(
       `business_id` INT64,
       `name` STRING OPTIONS(description="o nome do estabelecimento"),
);

CREATE TABLE {BQ_PROJECT_ID}.food_inspection.inspections
(
       `business_id` INT64 OPTIONS(description="o id único do negócio"),
       `score` INT64 OPTIONS(description="descrição: a pontuação da inspeção"),
       `date` DATE,
);

CREATE TABLE {BQ_PROJECT_ID}.food_inspection.violations
(
       `business_id` INT64,
       `date` DATE,
);

**************************
【Pergunta】
Pergunta:
Quais são os nomes dos estabelecimentos que atenderam a todos os padrões exigidos por 4 anos consecutivos?
estabelecimento tem o mesmo significado que negócio; pontuação de 90 ou mais refere-se a score ≥ 90; ano(data) = 2015; ; atendeu a todos os padrões exigidos por 4 anos consecutivos refere-se a COUNT(ano(data)) = 4 onde score = 100;

**************************
【Resposta】
Repetindo a pergunta e gerando o SQL com Divisão e Conquista Recursiva.

**Pergunta**: Quais são os nomes dos estabelecimentos que atenderam a todos os padrões exigidos por 4 anos consecutivos? estabelecimento tem o mesmo significado que negócio; pontuação de 90 ou mais refere-se a score ≥ 90; ano(data) = 2015; ; atendeu a todos os padrões exigidos por 4 anos consecutivos refere-se a COUNT(ano(data)) = 4 onde score = 100;

**1. Dividir e Conquistar:**

* **Pergunta Principal:** Quais são os nomes dos estabelecimentos que atenderam a todos os padrões exigidos por 4 anos consecutivos?
   * **Análise:** Precisamos encontrar os nomes dos negócios que têm uma pontuação de 100 por 4 anos consecutivos. A tabela `food_inspection.businesses` contém o `name` e a tabela `{BQ_PROJECT_ID}.food_inspection.inspections` contém o `score` e `date`. Precisaremos unir essas tabelas e filtrar por pontuação. Para verificar anos consecutivos, precisaremos agrupar por negócio e ano, e então verificar se cada grupo tem uma contagem de 4.
   * **Pseudo SQL:** SELECT DISTINCT `T2`.`name` FROM `{BQ_PROJECT_ID}.food_inspection.inspections` AS `T1` INNER JOIN `{BQ_PROJECT_ID}.food_inspection.businesses` AS `T2` ON `T1`.`business_id` = `T2`.`business_id` WHERE  <score = 100> AND <4 anos consecutivos>

   * **Sub-pergunta 1:** score = 100
       * **Análise:** Este é um filtro simples na tabela `{BQ_PROJECT_ID}.food_inspection.inspections` onde selecionamos linhas com `score` de 100.
       * **Pseudo SQL:** `T1`.`score` = 100

   * **Sub-pergunta 2:** 4 anos consecutivos
       * **Análise:** Isto é mais complexo. Precisamos agrupar as inspeções por negócio e ano, e então verificar se a contagem para cada grupo é 4. Para obter o ano da coluna `date`, usaremos a função `FORMAT_DATE('%Y', date)`. Também precisaremos usar funções de janela para atribuir uma classificação a cada ano dentro de um negócio, permitindo-nos verificar a consecutividade.
       * **Pseudo SQL:** `T2`.`name` IN (SELECT `T4`.`name` FROM (SELECT `T3`.`name`, `T3`.`years`, row_number() OVER (PARTITION BY `T3`.`name` ORDER BY `T3`.`years`) AS `rowNumber` FROM (SELECT DISTINCT `name`, FORMAT_DATE('%Y', date) AS `years` FROM `{BQ_PROJECT_ID}.food_inspection.inspections` AS `T1` INNER JOIN `{BQ_PROJECT_ID}.food_inspection.businesses` AS `T2` ON `T1`.`business_id` = `T2`.`business_id` WHERE `T1`.`score` = 100) AS `T3`) AS `T4` GROUP BY `T4`.`name`, date(`T4`.`years` || '-01-01', '-' || (`T4`.`rowNumber` - 1) || ' years') HAVING COUNT(`T4`.`years`) = 4)

       * **Sub-pergunta 2.1:** Obter negócios distintos e seus anos de inspeção onde a pontuação é 100
           * **Análise:** Precisamos unir as tabelas `{BQ_PROJECT_ID}.food_inspection.inspections` e `{BQ_PROJECT_ID}.food_inspection.businesses`, filtrar por `score` = 100, e selecionar nomes de negócios distintos e seus anos de inspeção.
           * **Pseudo SQL:** SELECT DISTINCT `name`, FORMAT_DATE('%Y', date) AS `years` FROM `{BQ_PROJECT_ID}.food_inspection.inspections` AS `T1` INNER JOIN `{BQ_PROJECT_ID}.food_inspection.businesses` AS `T2` ON `T1`.`business_id` = `T2`.`business_id` WHERE `T1`.`score` = 100

       * **Sub-pergunta 2.2:** Atribuir uma classificação a cada ano dentro de um negócio
           * **Análise:** Usaremos a função de janela `row_number()` para atribuir uma classificação a cada ano dentro de cada negócio, ordenado cronologicamente. Isso nos ajudará a identificar anos consecutivos posteriormente.
           * **Pseudo SQL:** SELECT `T3`.`name`, `T3`.`years`, row_number() OVER (PARTITION BY `T3`.`name` ORDER BY `T3`.`years`) AS `rowNumber` FROM `{BQ_PROJECT_ID}.food_inspection.inspections` AS `T1` INNER JOIN `{BQ_PROJECT_ID}.food_inspection.businesses` AS `T2` ON `T1`.`business_id` = `T2`.`business_id` WHERE `T1`.`score` = 100` AS `T3`

       * **Sub-pergunta 2.3:** Agrupar por negócio e grupos de anos consecutivos e verificar se a contagem é 4
           * **Análise:** Agruparemos os resultados por nome do negócio e uma data calculada representando o início de cada período potencial de 4 anos. Esta data é calculada adicionando (`rowNumber` - 1) anos ao primeiro dia do ano extraído da coluna `years`. Em seguida, filtramos por grupos com uma contagem de 4, indicando 4 anos consecutivos.
           * **Pseudo SQL:** SELECT `T4`.`name` FROM (<subconsulta anterior>) AS `T4` GROUP BY `T4`.`name`, date(`T4`.`years` || '-01-01', '-' || (`T4`.`rowNumber` - 1) || ' years') HAVING COUNT(`T4`.`years`) = 4

**2. Montando o SQL:**

* **Sub-pergunta 2.1 (negócios distintos e anos com pontuação 100):**
   * **SQL:** SELECT DISTINCT `name`, FORMAT_DATE('%Y', date) AS `years` FROM `{BQ_PROJECT_ID}.food_inspection.inspections` AS `T1` INNER JOIN `{BQ_PROJECT_ID}.food_inspection.businesses` AS `T2` ON `T1`.`business_id` = `T2`.`business_id` WHERE `T1`.`score` = 100

* **Sub-pergunta 2.2 (atribuir classificação a cada ano dentro de um negócio):**
   * **SQL:** SELECT `T3`.`name`, `T3`.`years`, row_number() OVER (PARTITION BY `T3`.`name` ORDER BY `T3`.`years`) AS `rowNumber` FROM (SELECT DISTINCT `name`, FORMAT_DATE('%Y', date) AS `years` FROM `{BQ_PROJECT_ID}.food_inspection.inspections` AS `T1` INNER JOIN `{BQ_PROJECT_ID}.food_inspection.businesses` AS `T2` ON `T1`.`business_id` = `T2`.`business_id` WHERE `T1`.`score` = 100) AS `T3`

* **Sub-pergunta 2.3 (agrupar por negócio e grupos de anos consecutivos):**
   * **SQL:** SELECT `T4`.`name` FROM (SELECT `T3`.`name`, `T3`.`years`, row_number() OVER (PARTITION BY `T3`.`name` ORDER BY `T3`.`years`) AS `rowNumber` FROM (SELECT DISTINCT `name`, FORMAT_DATE('%Y', date) AS `years` FROM `{BQ_PROJECT_ID}.food_inspection.inspections` AS `T1` INNER JOIN `{BQ_PROJECT_ID}.food_inspection.businesses` AS `T2` ON `T1`.`business_id` = `T2`.`business_id` WHERE `T1`.`score` = 100) AS `T3`) AS `T4` GROUP BY `T4`.`name`, DATE_SUB(DATE(CONCAT(T4.years, '-01-01')), INTERVAL (T4.rowNumber - 1) YEAR)  HAVING COUNT(`T4`.`years`) = 4

* **Sub-pergunta 2 (4 anos consecutivos):**
   * **SQL:** `T2`.`name` IN (SELECT `T4`.`name` FROM (SELECT `T3`.`name`, `T3`.`years`, row_number() OVER (PARTITION BY `T3`.`name` ORDER BY `T3`.`years`) AS `rowNumber` FROM (SELECT DISTINCT `name`, FORMAT_DATE('%Y', date) AS `years` FROM `{BQ_PROJECT_ID}.food_inspection.inspections` AS `T1` INNER JOIN `{BQ_PROJECT_ID}.food_inspection.businesses` AS `T2` ON `T1`.`business_id` = `T2`.`business_id` WHERE `T1`.`score` = 100) AS `T3`) AS `T4` GROUP BY `T4`.`name`, DATE_SUB(DATE(CONCAT(T4.years, '-01-01')), INTERVAL (T4.rowNumber - 1) YEAR)  HAVING COUNT(`T4`.`years`) = 4)

* **Pergunta Principal (nomes dos estabelecimentos):**
   * **SQL:** SELECT DISTINCT `T2`.`name` FROM `{BQ_PROJECT_ID}.inspections` AS `T1` INNER JOIN `{BQ_PROJECT_ID}.businesses` AS `T2` ON `T1`.`business_id` = `T2`.`business_id` WHERE  `T1`.`score` = 100 AND `T2`.`name` IN (SELECT `T4`.`name` FROM (SELECT `T3`.`name`, `T3`.`years`, row_number() OVER (PARTITION BY `T3`.`name` ORDER BY `T3`.`years`) AS `rowNumber` FROM (SELECT DISTINCT `name`, FORMAT_DATE('%Y', date) AS `years` FROM `{BQ_PROJECT_ID}.food_inspection.inspections` AS `T1` INNER JOIN `{BQ_PROJECT_ID}.food_inspection.businesses` AS `T2` ON `T1`.`business_id` = `T2`.`business_id` WHERE `T1`.`score` = 100) AS `T3`) AS `T4` GROUP BY `T4`.`name`, DATE_SUB(DATE(CONCAT(T4.years, '-01-01')), INTERVAL (T4.rowNumber - 1) YEAR) HAVING COUNT(`T4`.`years`) = 4)

**3. Simplificação e Otimização:**

* A consulta SQL final da etapa 2 pode ser simplificada mesclando as consultas aninhadas em uma única consulta com uma cláusula `WITH`. Isso melhora a legibilidade e potencialmente o desempenho.

**Consulta SQL Otimizada Final:**
```sql
SELECT DISTINCT T4.name
 FROM ( SELECT T3.name, T3.years, row_number()
 OVER (PARTITION BY T3.name ORDER BY T3.years)
 AS rowNumber FROM ( SELECT DISTINCT name, FORMAT_DATE('%Y', date)
 AS years FROM {BQ_PROJECT_ID}.food_inspection.inspections AS T1
 INNER JOIN {BQ_PROJECT_ID}.food_inspection.businesses AS T2 ON T1.business_id = T2.business_id
 WHERE T1.score = 100 ) AS T3 ) AS T4
 GROUP BY T4.name, DATE_SUB(DATE(CONCAT(T4.years, '-01-01')), INTERVAL (T4.rowNumber - 1) YEAR) HAVING COUNT(T4.years) = 4
```
===========
Exemplo 8

**************************
【Informações do Banco de Dados】
CREATE TABLE `bigquery-public-data.covid19_symptom_search.symptom_search_sub_region_2_daily`
(
  country_region_code STRING,
  country_region STRING,
  sub_region_1 STRING,
  sub_region_1_code STRING,
  sub_region_2 STRING,
  sub_region_2_code STRING,
  place_id STRING,
  date DATE,
  symptom_Abdominal_obesity FLOAT64,
  symptom_Abdominal_pain FLOAT64,
  symptom_Acne FLOAT64
)
PARTITION BY date
CLUSTER BY country_region_code, sub_region_1_code, sub_region_2_code, sub_region_2;

**************************
【Pergunta】
Pergunta:
Encontre o dia em que o sintoma que ocorre com mais frequência é dor de cabeça.

**************************
【Resposta】
Repetindo a pergunta e gerando o SQL com Divisão e Conquista Recursiva.

**Pergunta**: Encontre o dia em que o sintoma que ocorre com mais frequência é dor de cabeça.

Análise: Precisamos determinar o dia (dia da semana) em que a frequência de buscas pelo sintoma "dor de cabeça" é a mais alta. Isso envolve:
   - Agrupar os dados pelo dia da semana.
   - Contar as ocorrências de buscas por "dor de cabeça".
   - Ordenar as contagens em ordem decrescente e selecionar o dia com a maior contagem.

Pseudo SQL:
   SELECT FORMAT_DATE('%A', date) AS day, COUNT(*) AS headache_count
   FROM `bigquery-public-data.covid19_symptom_search.symptom_search_sub_region_2_daily`
   WHERE symptom_Headache > 0
   GROUP BY day
   ORDER BY headache_count DESC
   LIMIT 1

Sub-pergunta 1: Extrair o dia da semana da coluna de data.
   - Análise: Use a função FORMAT_DATE com o especificador de formato %A para extrair o nome do dia (por exemplo, "Segunda-feira", "Terça-feira") da coluna de data.

Pseudo SQL:
   SELECT FORMAT_DATE('%A', date) AS day
   FROM `bigquery-public-data.covid19_symptom_search.symptom_search_sub_region_2_daily`

Sub-pergunta 2: Filtrar linhas onde ocorreram buscas por "dor de cabeça".
   - Análise: Inclua apenas linhas onde o sintoma "dor de cabeça" tem um valor positivo (symptom_Headache > 0).

Pseudo SQL:
   SELECT date
   FROM `bigquery-public-data.covid19_symptom_search.symptom_search_sub_region_2_daily`
   WHERE symptom_Headache > 0

Sub-pergunta 3: Contar as ocorrências de buscas por "dor de cabeça" agrupadas por dia da semana.
   - Análise: Após filtrar os dados para linhas onde symptom_Headache > 0, agrupe os dados pelo dia da semana e conte o número de linhas para cada dia.

Pseudo SQL:
   SELECT FORMAT_DATE('%A', date) AS day, COUNT(*) AS headache_count
   FROM `bigquery-public-data.covid19_symptom_search.symptom_search_sub_region_2_daily`
   WHERE symptom_Headache > 0
   GROUP BY day

Sub-pergunta 4: Ordenar os resultados pela contagem em ordem decrescente e obter o dia principal.
   - Análise: Use a cláusula ORDER BY para ordenar pela contagem de buscas por "dor de cabeça" em ordem decrescente. Limite o resultado a 1 para obter o dia principal.

Pseudo SQL:
   SELECT FORMAT_DATE('%A', date) AS day, COUNT(*) AS headache_count
   FROM `bigquery-public-data.covid19_symptom_search.symptom_search_sub_region_2_daily`
   WHERE symptom_Headache > 0
   GROUP BY day
   ORDER BY headache_count DESC
   LIMIT 1

Montando o SQL
   - Combinando todas as sub-perguntas na consulta final:

**Consulta SQL Otimizada Final:**
```sql
SELECT 
  FORMAT_DATE('%A', PARSE_DATE('%Y-%m-%d', date)) AS day,
  COUNT(*) AS headache_count
FROM 
  `bigquery-public-data`.`covid19_symptom_search`.`symptom_search_country_daily`
GROUP BY 
  day
ORDER BY 
  headache_count DESC
LIMIT 1;
```

Agora é a pergunta real, seguindo as instruções e exemplos, gere o GoogleSQL com a abordagem de Divisão e Conquista Recursiva.
Siga todas as etapas da estratégia. Ao chegar à consulta final, produza a string da consulta SOMENTE no formato ```sql ... ```. Certifique-se de produzir apenas uma única consulta.
Os nomes das tabelas devem ser sempre exatamente os mesmos que os nomes das tabelas mencionados no esquema do banco de dados, por exemplo, `{BQ_PROJECT_ID}.airlines.Airlines` em vez de `Airlines`.

**************************
【Instruções de criação de tabela】
{SCHEMA}

**************************
【Pergunta】
Pergunta:
{QUESTION}

**************************
【Documentação Auxiliar sobre o Dataset】
Documentação:
{DOCUMENTATION}

**************************
【Resposta】
Repetindo a pergunta e gerando o SQL com Divisão e Conquista Recursiva.
"""
