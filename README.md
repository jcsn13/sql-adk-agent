# Agente SQL ADK com Múltiplos Agentes

Este projeto implementa um sistema de múltiplos agentes usando o Agent Development Kit (ADK) do Google. O agente principal (`root_agent`) é projetado para interagir com bancos de dados (como o BigQuery) usando conversão de linguagem natural para SQL (NL2SQL) e, em seguida, realizar análises de dados adicionais usando conversão de linguagem natural para Python (NL2Py), se necessário.

## Visão Geral

O sistema é composto por:

1.  **Root Agent (`root_agent`):** O orquestrador principal que recebe a pergunta do usuário.
2.  **Database Agent (`db_agent`):** Um sub-agente especializado em traduzir perguntas em linguagem natural para consultas SQL e buscar dados no banco de dados.
3.  **Data Science Agent (`ds_agent`):** Um sub-agente que pode realizar análises e manipulações de dados mais complexas usando Python sobre os dados recuperados pelo `db_agent`.

## Como Funciona

O fluxo de interação do agente pode ser resumido da seguinte forma:

1.  O usuário envia uma pergunta em linguagem natural (ex: "Quais foram as vendas totais do último trimestre?").
2.  O `root_agent` recebe a pergunta.
3.  O `root_agent` invoca o `call_db_agent`, que utiliza o `db_agent` (sub-agente NL2SQL).
4.  O `db_agent` converte a pergunta em uma consulta SQL apropriada para o banco de dados configurado (ex: BigQuery).
5.  A consulta SQL é executada no banco de dados.
6.  Os dados brutos resultantes (`query_result`) são retornados ao `root_agent`.
7.  Se a pergunta original ou uma subsequente necessitar de análise adicional que vá além da simples recuperação de dados (ex: "calcule a média e plot um gráfico"), o `root_agent` invoca o `call_ds_agent`.
8.  O `call_ds_agent` utiliza o `ds_agent` (sub-agente NL2Py), fornecendo os dados (`query_result`) e a tarefa de análise.
9.  O `ds_agent` gera e executa código Python para realizar a análise.
10. O resultado da análise é retornado ao `root_agent`.
11. O `root_agent` formula e envia a resposta final ao usuário.

### Diagrama do Fluxo

```mermaid
graph TD
    A[Usuário: Pergunta em Linguagem Natural] --> B{Root Agent};
    
    %% Documentação do Dataset alimenta o contexto
    I[Documentação do Dataset<br/>documentation/] --> B;
    I --> D;
    
    B -- Pergunta --> C(call_db_agent);
    C -- NL2SQL + Contexto --> D[Sub-Agente de BD (db_agent)];
    D -- Consulta SQL --> E[Banco de Dados (e.g., BigQuery)];
    E -- Dados Brutos --> D;
    D -- Dados Brutos (query_result) --> B;
    B -- Dados Brutos + Pergunta de Análise (opcional) --> F(call_ds_agent);
    F -- NL2Py --> G[Sub-Agente de Ciência de Dados (ds_agent)];
    G -- Código Python --> H[Executor de Código];
    H -- Resultado da Análise --> G;
    G -- Resultado da Análise --> B;
    B -- Resposta Final --> A;
    
    %% Styling para destacar a documentação
    classDef docStyle fill:#e1f5fe,stroke:#01579b,stroke-width:2px,color:#000
    class I docStyle
```

## Configuração da Documentação do Dataset

Antes de realizar o deployment, é essencial configurar a documentação do seu dataset na pasta `documentation/`. Esta documentação é automaticamente carregada pelo agente e injetada nos prompts para melhorar significativamente a interpretação dos dados e a geração de consultas SQL precisas.

### Como Funciona

O sistema utiliza a função `load_documentation_files()` (localizada em `sql_agent/utils/utils.py`) para ler automaticamente todos os arquivos `.md` e `.sql` da pasta `documentation/` e incluir seu conteúdo no contexto do agente principal. Esta documentação é carregada durante a inicialização do agente e fica disponível em todos os prompts.

### Conteúdo Recomendado

Adicione arquivos na pasta `documentation/` com informações detalhadas sobre seu dataset. Quanto mais contexto você fornecer, melhor será a performance do agente. Inclua:

#### **Metadados das Tabelas**
- Descrição do propósito de cada tabela
- Relacionamentos entre tabelas (chaves primárias e estrangeiras)
- Cardinalidade dos relacionamentos
- Regras de integridade dos dados

#### **Star Schema e Modelagem Dimensional**
- Identificação de tabelas fato e dimensão
- Hierarquias dimensionais
- Medidas e métricas calculadas
- Agregações pré-computadas

#### **Métricas de Negócio e KPIs**
- Definições precisas de indicadores de performance
- Fórmulas de cálculo para métricas complexas
- Regras de negócio específicas
- Filtros e segmentações importantes

#### **Exemplos de Queries**
- Consultas SQL comuns para casos de uso frequentes
- Queries complexas com joins e agregações
- Exemplos de análises típicas do domínio
- Padrões de consulta recomendados

#### **Dicionário de Dados**
- Significado detalhado de cada coluna
- Valores possíveis para campos categóricos
- Unidades de medida e formatos
- Regras de validação de dados

#### **Contexto de Domínio**
- Informações sobre o negócio ou área de aplicação
- Terminologia específica do domínio
- Sazonalidades e padrões temporais
- Limitações e particularidades dos dados

### Estrutura Sugerida

Organize a documentação em arquivos temáticos para facilitar a manutenção:

```
documentation/
├── dataset-overview.md          # Visão geral do dataset e contexto de negócio
├── tables-schema.md             # Estrutura detalhada das tabelas e relacionamentos
├── star-schema.md               # Modelagem dimensional (fatos e dimensões)
├── business-metrics.md          # KPIs e métricas de negócio importantes
├── data-dictionary.md           # Dicionário de dados com significado das colunas
└── example-queries.sql          # Queries de exemplo para casos de uso comuns
```

### Impacto na Performance

Uma documentação bem estruturada resulta em:
- **Maior precisão** na geração de consultas SQL
- **Melhor interpretação** de perguntas ambíguas
- **Respostas mais contextualizadas** para o domínio específico
- **Redução de erros** em consultas complexas
- **Melhor experiência do usuário** com respostas mais relevantes

### Exemplo de Conteúdo

**Arquivo: `documentation/business-metrics.md`**
```markdown
# Métricas de Negócio

## Revenue (Receita)
- **Definição**: Soma total de vendas em um período
- **Fórmula**: SUM(orders.total_amount)
- **Filtros**: Apenas pedidos com status 'completed'

## Customer Lifetime Value (CLV)
- **Definição**: Valor total gasto por um cliente durante seu relacionamento
- **Fórmula**: SUM(orders.total_amount) WHERE customer_id = X
- **Observações**: Considerar apenas pedidos dos últimos 24 meses
```

**Arquivo: `documentation/example-queries.sql`**
```sql
-- Vendas mensais por categoria
SELECT 
    DATE_TRUNC(DATE(order_date), MONTH) as month,
    product_category,
    SUM(total_amount) as monthly_revenue
FROM `project.dataset.orders` o
JOIN `project.dataset.products` p ON o.product_id = p.id
GROUP BY month, product_category
ORDER BY month DESC, monthly_revenue DESC;
```

## Requisitos para Deployment

*   **Google Cloud Project:** Um projeto no Google Cloud com faturamento ativo.
*   **APIs Habilitadas:**
    *   Cloud Build API
    *   Vertex AI API
    *   IAM API
    *   BigQuery API
*   **`gcloud` CLI:** A interface de linha de comando do Google Cloud, autenticada e configurada para o seu projeto.
*   **Poetry:** Ferramenta para gerenciamento de dependências e empacotamento Python (versão especificada em `cloudbuild.yaml`, ex: `1.8.3`).
*   **Permissões:** A conta de serviço do Cloud Build (`[PROJECT_NUMBER]@cloudbuild.gserviceaccount.com`) e o usuário/conta de serviço que executa o `gcloud builds submit` precisam de permissões adequadas (ex: Vertex AI Admin, Service Account User, Cloud Build Editor, etc.) para criar e gerenciar os recursos.

## Deployment

O deployment é realizado usando o Google Cloud Build, que automatiza o processo de construção e implantação do agente.

### 1. Configuração de Variáveis

Antes de iniciar o deployment, você precisa configurar as variáveis de substituição no arquivo `cloudbuild.yaml`. Estas variáveis personalizam o deployment para o seu ambiente específico.

Abra o arquivo `cloudbuild.yaml` e edite a seção `substitutions`:

```yaml
substitutions:
  _PROJECT_ID: "seu-project-id-aqui"  # Substitua pelo ID do seu projeto GCP
  _LOCATION: "sua-regiao-aqui"       # Ex: us-central1
  _ROOT_AGENT_MODEL: "gemini-1.5-flash-preview-0514" # Modelo para o agente raiz
  _ANALYTICS_AGENT_MODEL: "gemini-1.0-pro-001" # Modelo para o agente de analytics (se aplicável)
  _BASELINE_NL2SQL_MODEL: "gemini-1.5-flash-preview-0514" # Modelo para NL2SQL base
  _BIGQUERY_AGENT_MODEL: "gemini-1.0-pro-001" # Modelo para o sub-agente BigQuery
  _CHASE_NL2SQL_MODEL: "gemini-1.5-flash-preview-0514" # Modelo para NL2SQL com CHASE
  _BQ_DATASET_ID: "seu-dataset-id-aqui" # ID do seu dataset no BigQuery
  _BQ_PROJECT_ID: "seu-bq-project-id-aqui" # ID do projeto onde o dataset BigQuery reside (pode ser o mesmo que _PROJECT_ID)
  _CODE_INTERPRETER_EXTENSION_NAME: "" # Deixe em branco para criar uma nova extensão de interpretador de código, ou forneça o nome de uma existente
  _NL2SQL_METHOD: "CHASE" # Método NL2SQL a ser usado (ex: CHASE, BASELINE)
  _APP_ID: "seu-agentspace-app-id" # ID do seu aplicativo no Agent Space / Dialogflow CX Agent ID / Vertex AI Agent Builder App ID
  _AGENT_DISPLAY_NAME: "Nome de Exibição do Agente" # Nome que aparecerá para o agente
  _AGENT_ICON_URI: "https://fonts.gstatic.com/s/i/short-term/release/googlesymbols/smart_toy/default/24px.svg" # URI para o ícone do agente
  _TOOL_DESCRIPTION: "Descrição da ferramenta do agente" # Descrição da ferramenta que será criada
  _AUTH_PATH: "projects/${_PROJECT_ID}/locations/global/authorizations/seu-auth-id" # Caminho para a autorização do Reasoning Engine (se necessário para a ferramenta)
```

**Principais variáveis a serem configuradas:**

*   `_PROJECT_ID`: O ID do seu projeto Google Cloud.
*   `_LOCATION`: A região onde os recursos serão implantados (ex: `us-central1`).
*   `_BQ_DATASET_ID`: O ID do seu conjunto de dados no BigQuery que o agente irá consultar.
*   `_BQ_PROJECT_ID`: O ID do projeto GCP onde seu conjunto de dados BigQuery está localizado.
*   `_APP_ID`: O ID do aplicativo de front-end do agente (por exemplo, um ID de Agente do Dialogflow CX ou um ID de Aplicativo do Vertex AI Agent Builder).
*   `_AGENT_DISPLAY_NAME`: O nome de exibição para o seu agente.
*   `_AUTH_PATH`: O caminho para um recurso de Autorização do Reasoning Engine, se sua ferramenta de agente exigir autenticação específica. Pode ser necessário criar isso manualmente no console do Vertex AI se for a primeira vez.

### 2. Executando o Cloud Build

Após configurar as variáveis, você pode iniciar o processo de build e deployment com o seguinte comando `gcloud`, executado a partir do diretório raiz do projeto (onde `cloudbuild.yaml` está localizado):

```bash
gcloud builds submit --config cloudbuild.yaml .
```

Este comando instrui o Cloud Build a executar os passos definidos em `cloudbuild.yaml`:

1.  **`build-wheel`**:
    *   Instala o Poetry.
    *   Configura o Poetry para não usar ambientes virtuais neste passo.
    *   Instala as dependências do projeto definidas em `pyproject.toml`.
    *   Constrói o arquivo wheel (`.whl`) do seu pacote Python (`sql_agent`).
    *   Copia o arquivo wheel para o diretório `deployment/`.

2.  **`deploy-reasoning-engine`**:
    *   Este passo é executado no diretório `deployment/`.
    *   Define variáveis de ambiente com base nas substituições do `cloudbuild.yaml`.
    *   Instala o arquivo wheel do agente (copiado no passo anterior) e suas dependências.
    *   Executa o script `python deploy.py --create`. Este script é responsável por:
        *   Criar ou atualizar o Reasoning Engine no Vertex AI com a lógica do seu `sql_agent`.
        *   Salvar o nome do recurso do Reasoning Engine criado no arquivo `deployment/agent_resource_name.txt`.

3.  **`create-discovery-engine-agent`** (ou agente de front-end):
    *   Este passo também é executado no diretório `deployment/`.
    *   Lê o nome do recurso do Reasoning Engine do arquivo `deployment/agent_resource_name.txt`.
    *   Torna o script `create_new_agent.sh` executável.
    *   Executa o script `bash create_new_agent.sh`. Este script é responsável por:
        *   Criar um novo agente no Dialogflow CX ou Vertex AI Agent Builder (dependendo do conteúdo do script).
        *   Configurar este agente para usar o Reasoning Engine implantado no passo anterior como uma ferramenta ou fulfillment.

### 3. Verificando o Deployment

Após a conclusão bem-sucedida do Cloud Build, você poderá encontrar e testar seu agente:

*   **Reasoning Engine:** No console do Google Cloud, navegue até Vertex AI > Reasoning Engines.
*   **Agente de Frontend:** No console do Dialogflow CX ou Vertex AI > Agent Builder, dependendo de como `create_new_agent.sh` está configurado.

## Desenvolvimento Local (Opcional)

Para desenvolvimento e testes locais do `sql_agent` antes do deployment:

1.  Certifique-se de ter Python (versão compatível com `pyproject.toml`) e Poetry instalados.
2.  Configure um ambiente virtual:
    ```bash
    poetry shell
    poetry install
    ```
3.  Configure as variáveis de ambiente necessárias localmente (por exemplo, através de um arquivo `.env` carregado pelo seu código ou configuradas diretamente no seu shell).
4.  Execute ou teste os componentes do seu agente.

Lembre-se que para interagir com serviços Google Cloud (como BigQuery) localmente, você precisará ter o `gcloud` CLI autenticado (`gcloud auth application-default login`).
