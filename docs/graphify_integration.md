# Knowledge Graph / Graphify experimental

## 1. O que é a camada de grafo

A camada de Knowledge Graph transforma os registros canônicos da DSM Operational API em um grafo derivado com `nodes`, `edges`, export JSON local, endpoints de consulta e uma página HTML standalone para inspeção visual. Ela foi desenhada para responder perguntas estruturais sobre capítulos, transtornos, critérios, chunks, perfis operacionais, gravidade, diferenciais, registry e relações compartilhadas.

Fluxo correto:

```txt
PostgreSQL -> GraphBuilder -> Local Graph Export -> optional GraphifyAdapter -> API endpoints -> HTML test
```

## 2. O que ela não é

O grafo não é a fonte oficial do DSM. A fonte canônica permanece em PostgreSQL, especialmente nas tabelas:

- `diagnostic_versions`
- `diagnostic_documents`
- `diagnostic_registry`
- `diagnostic_chunks`

Não leia Graphify como origem da verdade para respostas clínicas ou para reconstruir a base operacional.

## 3. Por que Graphify é opcional

Graphify é tratado como integração experimental e externa. A API deve subir e funcionar sem SDK, serviço ou CLI Graphify instalado. Quando `GRAPHIFY_ENABLED=false`, a API usa apenas o export local (`graph_exports`). Quando `GRAPHIFY_ENABLED=true`, o adapter tenta chamar um CLI configurado em `GRAPHIFY_CLI_PATH`; se falhar, a exportação local continua disponível e a falha vira warning.

Variáveis relevantes:

```env
GRAPH_ENABLED=true
GRAPHIFY_ENABLED=false
GRAPHIFY_CLI_PATH=
GRAPH_EXPORT_DIR=graph_exports
```

## 4. Como gerar grafo

Via CLI:

```bash
python -m app.scripts.export_dsm_graph --version-id active --persist
```

Com tentativa opcional de Graphify:

```bash
python -m app.scripts.export_dsm_graph --version-id active --persist --send-to-graphify
```

Via API administrativa:

```bash
curl -X POST http://localhost:8000/api/dsm/graph/rebuild \
  -H "Content-Type: application/json" \
  -H "X-Admin-Token: change-me" \
  -d '{"version_id":"active","persist":true,"send_to_graphify":false}'
```

Arquivos gerados:

```txt
graph_exports/{version_id}/graph.json
graph_exports/{version_id}/nodes.json
graph_exports/{version_id}/edges.json
graph_exports/{version_id}/GRAPH_REPORT.md
```

## 5. Como consultar endpoints

Status:

```bash
curl http://localhost:8000/api/dsm/graph/status
```

Export completo:

```bash
curl 'http://localhost:8000/api/dsm/graph/export?version_id=active'
```

Transtornos:

```bash
curl 'http://localhost:8000/api/dsm/graph/nodes?version_id=active&type=Disorder&limit=50'
```

Busca textual de nodes:

```bash
curl 'http://localhost:8000/api/dsm/graph/nodes?version_id=active&type=Disorder&q=autismo&limit=20'
```

Subgrafo relacionado:

```bash
curl 'http://localhost:8000/api/dsm/graph/related/disorder:tea?version_id=active&depth=1&limit=100'
```

Consulta estruturada:

```bash
curl -X POST http://localhost:8000/api/dsm/graph/query \
  -H "Content-Type: application/json" \
  -d '{"version_id":"active","node_type":"Disorder","query":"autismo","depth":1,"limit":100}'
```

## 6. Como abrir o HTML de teste

Com a API rodando:

```txt
http://localhost:8000/static/graph_test.html
```

O arquivo também pode ser aberto diretamente no navegador como `file://.../static/graph_test.html`, desde que o backend permita CORS para a origem usada pelo navegador.

## 7. Como interpretar nodes e edges

Principais tipos de node:

- `Version`: versão DSM exportada.
- `Chapter`: capítulos.
- `Disorder`: documentos renderizáveis.
- `RegistryItem`: itens `MINIMAL` ou `EXCLUDE`.
- `Criterion`, `Cluster`, `Specifier`, `Subtype`, `OperationalProfile`, `Differential`, `KeyQuestion`, `Alert`: conteúdo extraído de JSON tolerante a variações de campos.
- `Chunk`: chunks RAG vinculados ao transtorno.
- `StructureType`, `SeverityType`, `UiMode`: taxonomias operacionais compartilhadas.

Principais edges:

- `HAS_CHAPTER`, `BELONGS_TO_CHAPTER`
- `HAS_CRITERION`, `HAS_CLUSTER`, `HAS_CHUNK`
- `HAS_SEVERITY_TYPE`, `HAS_STRUCTURE_TYPE`, `HAS_UI_MODE`
- `REGISTRY_BELONGS_TO_CHAPTER`, `CROSS_REFERENCES`
- `SHARES_SEVERITY_TYPE`, `SHARES_STRUCTURE_TYPE`

As arestas de similaridade são limitadas para evitar explosão combinatória.

## 8. Uso futuro com PydanticAI

A exportação local pode alimentar ferramentas PydanticAI como uma lente estrutural para pré-filtrar contexto antes de consultar chunks RAG. O padrão recomendado é: usar o grafo para descobrir entidades e relações, depois buscar o conteúdo oficial nos documentos/chunks canônicos em PostgreSQL.

## 9. Limitações

- A extração de critérios e diferenciais é tolerante, não ontologicamente perfeita.
- Relações textuais profundas ainda dependem de campos explícitos ou futuras heurísticas.
- O adapter Graphify não assume SDK específico.
- O HTML é uma ferramenta de desenvolvimento, não um produto clínico.

## 10. Troubleshooting

- `No active DSM version found`: importe e ative uma release DSM.
- `Invalid admin token`: envie `X-Admin-Token` igual a `ADMIN_TOKEN`.
- `Graphify CLI not configured`: esperado quando `GRAPHIFY_ENABLED=false` ou `GRAPHIFY_CLI_PATH` vazio.
- `graph_exports` vazio: rode rebuild via API ou o script CLI com `--persist`.
- HTML sem grafo: confirme `API Base URL`, CORS e se `/api/dsm/graph/status` responde.

## Graph Agents / PydanticAI

The DSM graph agent layer is optional and evidence-bound. Agents use controlled tools backed by `DsmGraphService` and, for clinical relation fallback only, `HybridSearchService`. They never access SQL directly, never mutate graph/database state, never rebuild graph exports, and never treat LLM output as canonical DSM content.

Configuration:

```env
AGENTS_ENABLED=false
AGENT_MODEL=openai:gpt-4.1-mini
GRAPH_AGENT_ENABLED=true
```

If graph agents are disabled, the agent endpoints return `{"detail":"Agents are disabled."}`.

Endpoints under `/api/dsm/graph/agents`:

- `POST /ask` → `GraphTraversalAgent` for structural graph questions.
- `POST /clinical-relations` → `GraphClinicalRelationAgent` for relation exploration with optional chunk search fallback.
- `POST /audit` → `GraphAuditAgent` for deterministic consistency checks.
- `POST /plan-query` → `GraphQueryPlannerAgent` for natural-language to graph-plan conversion.

Examples:

```bash
curl -X POST http://localhost:8000/api/dsm/graph/agents/ask \
  -H "Content-Type: application/json" \
  -d '{
    "query": "quais transtornos têm gravidade por funcionamento adaptativo?",
    "version_id": "active",
    "limit": 20
  }'
```

```bash
curl -X POST http://localhost:8000/api/dsm/graph/agents/audit \
  -H "Content-Type: application/json" \
  -d '{"version_id":"active"}'
```

The browser test page `static/graph_test.html` has a **Graph Agents** panel for running these endpoints and highlighting returned `used_nodes` in the visualization.
