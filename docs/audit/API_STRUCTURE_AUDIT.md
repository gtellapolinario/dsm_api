# Auditoria Estrutural Completa da DSM Operational API

**Gerado em:** 2026-05-29T15:40:00Z  
**Repo declarado:** `gtellapolinario/dsm_api`  
**Branch declarada pelo usuário:** `Projetos`  
**Branch local auditada:** `work`  
**Status final:** `BLOCKED`

## 1. Sumário executivo

A auditoria foi executada de forma adversarial com leitura estática, comparação de camadas e comandos reais. O código Python compila, `ruff` passa e a suíte unitária existente passa. A release DSM canônica em `data/dsm/releases/dsm5_operational_2026_05_28` valida com 160 documentos renderizáveis e 50 entradas de registry.

O veredito de prontidão é **BLOCKED** porque o ambiente auditado não possui Docker nem PostgreSQL em execução; por isso `alembic upgrade head`, ingestão real, ingestão em banco limpo, consultas SQL pós-ingestão, endpoints dependentes de banco, busca FTS, busca vetorial, RAG sobre chunks e rebuild/export de grafo não puderam ser concluídos. Além disso, há achados reais de código/documentação: divergência de dimensão de embedding entre settings/model e migration, FK extra em migration não representada no model, documentação Graph com comando inválido de validação, exemplo README apontando para item `tdah` inexistente na release, e default de `debug=True` expondo tracebacks em respostas HTTP quando o banco está indisponível.

## 2. Status final

`BLOCKED`

Critério usado: a API sobe e expõe OpenAPI sem banco, mas a prontidão operacional exigida depende de banco limpo, migrations, ingestão, versão ativa e endpoints pós-ingestão. Esses passos ficaram bloqueados por ausência de Docker/PostgreSQL no ambiente (`docker: command not found`; conexão recusada em `localhost:5432`).

## 3. Ambiente de execução

| Item | Valor |
|---|---|
| CWD | `/workspace/dsm_api` |
| Python | `Python 3.14.4` |
| Branch local | `work` |
| Data | `2026-05-29` |
| Docker | Indisponível (`docker: command not found`) |
| PostgreSQL local | Indisponível (`Connect call failed ... 5432`) |
| Network/PyPI | Bloqueado por proxy/túnel `403 Forbidden` durante instalação editable |

## 4. Estrutura de arquivos

### Arquivos obrigatórios encontrados

| Caminho | Status |
|---|---|
| `app/main.py` | OK |
| `app/core/` | OK |
| `app/models/` | OK |
| `app/schemas/` | OK |
| `app/repositories/` | OK |
| `app/services/` | OK |
| `app/api/routes/` | OK |
| `app/scripts/` | OK |
| `alembic/env.py` | OK |
| `alembic/versions/` | OK |
| `data/dsm/releases/dsm5_operational_2026_05_28/manifest.json` | OK |
| `data/dsm/releases/dsm5_operational_2026_05_28/final_json/` | OK |
| `data/dsm/releases/dsm5_operational_2026_05_28/normalized_registry/` | OK |
| `data/dsm/releases/dsm5_operational_2026_05_28/INDEX_MASTER_2B.md` | OK |
| `tests/` | OK |
| `pyproject.toml` | OK |
| `docker-compose.yml` | OK |
| `Dockerfile` | OK |
| `alembic.ini` | OK |
| `.env.example` | OK |
| `README.md` | OK |

### Graph/Graphify

| Caminho | Status |
|---|---|
| `app/graph/` | OK |
| `app/services/graph_service.py` | OK |
| `app/api/routes/dsm_graph.py` | OK |
| `app/scripts/export_dsm_graph.py` | OK |
| `app/scripts/validate_dsm_graph.py` | OK |
| `static/graph_test.html` | OK |
| `docs/graphify_integration.md` | OK |

## 5. Conferência de dependências

`pyproject.toml` inclui as dependências centrais: FastAPI, uvicorn, SQLAlchemy asyncio, asyncpg, Alembic, Pydantic, pydantic-settings, python-dotenv, pgvector, openai, pytest/httpx/ruff em extras dev. `pydantic-ai` está em dependências obrigatórias; Graphify não aparece como dependência obrigatória, o que é coerente com a integração opcional via CLI.

Comando `pip install -e ".[dev]"` falhou por indisponibilidade de rede/PyPI no ambiente, não por erro de metadata do projeto.

## 6. Conferência FastAPI/app/main.py

`app.main:create_app()` importa e registra routers de health, versões, documentos, registry, search, agent, RAG, graph e ingestão. O OpenAPI foi servido com HTTP 200. A API inicia sem tocar no banco durante import/startup.

Risco observado: `StaticFiles(directory="static")` é montado incondicionalmente. Funciona neste repo porque `static/` existe; se a imagem/runtime omitir essa pasta, o app pode falhar no startup.

## 7. Conferência de rotas

OpenAPI obtido via `curl http://localhost:8000/openapi.json` retornou HTTP 200.

| Route | Exists in code | Exists in OpenAPI | Documented | Auth required | Status |
|---|---:|---:|---:|---:|---|
| GET `/api/health` | sim | sim | sim | não | OK |
| GET `/api/health/db` | sim | sim | sim | não | OK |
| GET `/api/health/vector` | sim | sim | sim | não | OK |
| GET `/api/health/readiness` | sim | sim | sim | não | OK |
| GET `/api/dsm/versions` | sim | sim | sim | não | DB não testado |
| GET `/api/dsm/versions/current` | sim | sim | sim | não | 500 sem DB |
| POST `/api/dsm/versions/{version_id}/activate` | sim | sim | sim | `X-Admin-Token` | DB não testado |
| GET `/api/dsm/chapters` | sim | sim | implícito | não | DB não testado |
| GET `/api/dsm/documents` | sim | sim | sim | não | 500 sem DB |
| GET `/api/dsm/documents/{item_id}` | sim | sim | sim | não | DB não testado |
| GET `/api/dsm/registry` | sim | sim | parcial | não | DB não testado |
| GET `/api/dsm/registry/minimal` | sim | sim | sim | não | 500 sem DB |
| GET `/api/dsm/registry/excluded` | sim | sim | sim | não | 500 sem DB |
| POST `/api/dsm/search` | sim | sim | sim | rate limit | 500 sem DB |
| POST `/api/dsm/rag/retrieve` | sim | sim | não destacado no README | não | schema usa `question`, não `query` |
| POST `/api/dsm/rag/answer` | sim | sim | sim | rate limit | schema usa `question`, não `query` |
| POST `/api/dsm/ingest` | sim | sim | sim | `X-Admin-Token` | DB não testado |
| GET `/api/dsm/graph/status` | sim | sim | sim | não | OK |
| POST `/api/dsm/graph/rebuild` | sim | sim | sim | `X-Admin-Token` | 401 sem token; 500 sem DB com token |
| GET `/api/dsm/graph/export` | sim | sim | sim | não | DB/export não testado |
| GET `/api/dsm/graph/nodes` | sim | sim | sim | não | DB/export não testado |
| GET `/api/dsm/graph/node/{node_id}` | sim | sim | parcial | não | DB/export não testado |
| GET `/api/dsm/graph/related/{node_id}` | sim | sim | sim | não | DB/export não testado |
| POST `/api/dsm/graph/query` | sim | sim | sim | não | DB/export não testado |
| POST `/api/dsm/agent/answer` | sim | sim | não | não | endpoint existente não documentado no README principal |
| POST `/api/dsm/agent/interview-plan` | sim | sim | não | não | endpoint existente não documentado no README principal |
| POST `/api/dsm/agent/critic` | sim | sim | não | não | endpoint existente não documentado no README principal |

## 8. Conferência de schemas Pydantic

Schemas existem para DSM, ingestion, search e RAG. Achado principal: os endpoints RAG requerem campo `question`; os exemplos solicitados na tarefa usam `query`, e chamadas com `query` retornaram 422. Isso não quebra o código, mas é uma divergência operacional relevante para clientes que esperem simetria com `/api/dsm/search`.

## 9. Conferência de modelos SQLAlchemy

Modelos encontrados: `DiagnosticVersion`, `DiagnosticDocument`, `DiagnosticRegistry`, `DiagnosticChunk`, `DiagnosticIngestionRun`. As tabelas esperadas estão modeladas.

Divergências encontradas contra migrations:

- `DiagnosticChunk.embedding` usa `Vector(settings.embedding_dimensions)`, mas a migration inicial fixa `Vector(1536)`. Se `EMBEDDING_DIMENSIONS` for alterado, model/runtime e banco divergem.
- A migration inicial cria `diagnostic_chunks.version_id` com FK simples para `diagnostic_versions.id`; o model não declara essa FK simples, apenas FK composta para `diagnostic_documents(version_id,item_id)`. Essa diferença pode afetar autogenerate e introspecção futura.

## 10. Conferência de Alembic/migrations

Migrations presentes:

- `20260528_0001_initial.py`
- `20260529_0002_hardening.py`

A migration inicial habilita `vector` e `pgcrypto`, cria tabelas operacionais e índices GIN/HNSW. A migration de hardening adiciona `diagnostic_ingestion_runs`, constraints adicionais e índices de lookup.

`alembic upgrade head` não pôde concluir porque o Postgres local não está disponível. Evidência: conexão recusada em `::1:5432` e `127.0.0.1:5432`.

## 11. Conferência de banco/Postgres/pgvector

Bloqueada por ausência de PostgreSQL/Docker no ambiente. Não foi possível executar:

```sql
SELECT extname FROM pg_extension WHERE extname IN ('vector', 'pgcrypto');
SELECT COUNT(*) FROM diagnostic_documents;
SELECT COUNT(*) FROM diagnostic_registry;
SELECT COUNT(*) FROM diagnostic_chunks;
SELECT * FROM diagnostic_versions;
```

A leitura das migrations confirma intenção de criar `vector`, `pgcrypto`, GIN em JSONB/TSVECTOR, HNSW em embedding e índices por versão/capítulo/categoria.

## 12. Conferência da release DSM

`python -m app.scripts.validate_dsm_files --release-path data/dsm/releases/dsm5_operational_2026_05_28` passou.

Contagens verificadas:

| Métrica | Esperado | Observado |
|---|---:|---:|
| `manifest.version_id` | `dsm5_operational_2026_05_28` | OK |
| `full` | 79 | 79 |
| `short` | 81 | 81 |
| `renderable` | 160 | 160 |
| `minimal` | 26 | 26 |
| `exclude` | 24 | 24 |
| `registry` | 50 | 50 |
| arquivos `final_json/*.json` | 21 | 21 |
| `minimal_all.json` entries | 26 | 26 |
| `excluded_all.json` entries | 24 | 24 |

Invariantes verificados por script local:

- `final_json` contém 79 FULL e 81 SHORT.
- Todos os 160 itens renderizáveis têm `render_structured_interview=true`.
- Registry contém 26 MINIMAL e 24 EXCLUDE, todos com `render_structured_interview=false`.
- Não há IDs duplicados em `final_json` nem registry.
- Nenhum item renderizável sem `diagnostic_rule`.
- Invariantes clínicas solicitadas passaram para TDAH, TEA, Deficiência Intelectual, Tique Transitório, Cleptomania, TOD e capítulo 16.

## 13. Conferência da ingestão

Bloqueada por ausência de PostgreSQL. O comando de ingestão alcançou o serviço de ingestão, mas falhou ao tentar abrir conexão com o banco. Portanto não foi possível validar em banco limpo:

- criação de `diagnostic_versions` ativa;
- 160 documentos em `diagnostic_documents`;
- 50 entradas em `diagnostic_registry`;
- chunks `>160`;
- idempotência/erro controlado em reimportação da mesma versão.

## 14. Conferência de chunks/FTS/vector search

Bloqueada sem banco e sem ingestão. `/api/dsm/search` está registrado no OpenAPI, mas chamadas reais retornaram HTTP 500 por indisponibilidade de banco antes de validar FTS/vector.

Leitura do serviço indica comportamento esperado quando embeddings estão desabilitados: se `use_vector=true` e `allow_fallback=false` ou `use_fts=false`, retorna HTTP 400 `Vector search requested but embeddings are disabled`. Isso não pôde ser observado via endpoint porque a resolução de versão ativa consulta o banco antes.

## 15. Conferência RAG

Endpoints RAG estão registrados. Chamadas usando payload com `query` retornaram 422 porque o schema exige `question`. A execução real com chunks ficou bloqueada sem banco/ingestão.

Leitura do serviço indica que `/rag/answer` não gera resposta sem chunks e, por default, `rag_answer_enabled=false`, retorna mensagem informando que answer está desabilitado e os resultados de retrieval foram retornados. Prompt injection não pôde ser validado em runtime sem chunks.

## 16. Conferência Graph/Graphify, se existir

Graph existe. `/api/dsm/graph/status` retornou HTTP 200 com `graph_enabled=true`, `graphify_enabled=false`, `graphify_available=false` e `available_exports=[]`.

`POST /api/dsm/graph/rebuild` sem token e com token incorreto retornou 401, como esperado. Com token correto, falhou em 500 por ausência de banco.

`python -m app.scripts.export_dsm_graph --version-id active --persist` falhou por ausência de banco. `python -m app.scripts.validate_dsm_graph --version-id active` falhou porque o script real não aceita `--version-id`; ele espera caminho de arquivo de grafo. A documentação principal usa o formato correto com caminho, mas `docs/graphify_integration.md` documenta o comando de export com `--version-id` e não documenta validação por `--version-id`.

## 17. Conferência static HTML, se existir

`curl http://localhost:8000/static/graph_test.html` retornou HTTP 200 e o HTML contém controles para status, rebuild, load graph, search nodes e related. Interação visual completa no navegador não foi executada neste ambiente sem browser; chamadas de API subjacentes foram parcialmente testadas via curl.

## 18. Conferência de segurança

Achados:

- Endpoints administrativos de ingestão, ativação de versão e graph rebuild usam `X-Admin-Token`.
- `POST /api/dsm/graph/rebuild` retornou 401 sem token e com token incorreto.
- `resolve_safe_path()` rejeita `..` e restringe release path sob `DSM_RELEASE_ROOT` quando exigido ou em produção.
- `debug=True` é default; com banco indisponível, endpoints retornaram tracebacks completos no corpo HTTP. Isso é aceitável apenas em desenvolvimento e perigoso se produção herdar defaults.
- `cors_origin_list` permite `*` se `CORS_ORIGINS=*`; não há hard fail em produção.
- Busca por segredos não encontrou chave real; encontrou apenas placeholders (`OPENAI_API_KEY=sk-...`) e senhas locais de exemplo (`dsm_password`).

## 19. Conferência de testes

`pytest -q` passou: 30 testes, 1 warning de depreciação Starlette/httpx.

Cobertura mínima observada:

| Teste esperado | Status |
|---|---|
| `tests/test_health.py` | existe |
| `tests/test_ingestion_validation.py` | existe |
| `tests/test_dsm_routes.py` | existe |
| `tests/test_registry_routes.py` | existe |
| `tests/test_chunking.py` | existe |
| `tests/test_hybrid_search_sql.py` | existe |
| `tests/test_graph_builder.py` | existe |
| `tests/test_graph_routes.py` | existe |

Limitação: testes passam, mas não substituem ingestão real em PostgreSQL/pgvector neste ambiente.

## 20. Conferência Docker

`docker compose down -v` e `docker compose up --build -d` não puderam rodar porque `docker` não está instalado no ambiente (`command not found`). Leitura de `docker-compose.yml` mostra Postgres `pgvector/pgvector:pg16`, healthcheck e API aguardando Postgres healthy antes de rodar `alembic upgrade head && uvicorn`.

## 21. Conferência README/documentação

README cobre setup local, Docker, `.env`, Alembic, validação, importação, ativação, endpoints, busca FTS/vector, RAG, exemplos curl/Python/fetch/React/TanStack, backup/restore, operação, CI, limitações clínicas e Graph/Graphify.

Divergências:

- README documenta `curl http://localhost:8000/api/dsm/documents/tdah`, mas a release usa ID `deficit_de_atencao_hiperatividade`; não existe item `tdah` nos dados canônicos.
- Endpoints agent (`/api/dsm/agent/answer`, `/interview-plan`, `/critic`) existem no OpenAPI e não estão documentados no README principal.
- Exemplos de RAG devem deixar claro que o payload usa `question`, não `query`.
- Documentação Graph precisa padronizar validação: o script `validate_dsm_graph` real espera caminho de arquivo (`graph_exports/<version_id>/graph.json`), não `--version-id active`.

## 22. Lista de problemas por severidade

### critical

#### ISSUE-001 — Verificação operacional bloqueada por ausência de PostgreSQL/Docker

**Severidade:** critical  
**Área:** runtime | migration | ingestion | docker  
**Arquivo(s):**
- `docker-compose.yml`
- `alembic.ini`
- `app/scripts/import_dsm.py`

**Descrição:** `alembic upgrade head`, ingestão, consultas SQL e endpoints dependentes de banco não puderam ser validados porque não há Docker nem PostgreSQL local disponível.

**Evidência:**

```txt
docker: command not found
OSError: Multiple exceptions: [Errno 111] Connect call failed ('::1', 5432), [Errno 111] Connect call failed ('127.0.0.1', 5432)
```

**Impacto:** Não é possível afirmar prontidão de produção: banco limpo, migrations, ingestão, versão ativa, search, RAG e graph rebuild não foram comprovados.

**Correção recomendada:** Reexecutar auditoria em ambiente com Docker ou PostgreSQL/pgvector real disponível; rodar migrations, ingestão e testes de endpoints pós-ingestão.

**Bloqueia produção?** sim

### high

#### ISSUE-002 — Dimensão de embedding configurável diverge da migration fixa

**Severidade:** high  
**Área:** migration | model | search  
**Arquivo(s):**
- `app/models/dsm.py`
- `app/core/config.py`
- `alembic/versions/20260528_0001_initial.py`

**Descrição:** O model usa `Vector(settings.embedding_dimensions)`, mas a migration cria `Vector(1536)`. `Settings.embedding_dimensions` pode ser alterado via env sem migration correspondente.

**Evidência:**

```txt
model: mapped_column(Vector(settings.embedding_dimensions))
migration: sa.Column("embedding", Vector(1536))
settings default: embedding_dimensions = 1536
```

**Impacto:** Alterar dimensão em runtime pode quebrar inserts/search vetorial ou deixar banco e model incompatíveis.

**Correção recomendada:** Fixar dimensão em código/migration como contrato versionado, ou gerar migration explícita quando a dimensão mudar; validar env contra dimensão do banco no startup/readiness.

**Bloqueia produção?** sim, se embeddings forem habilitados com dimensão diferente.

#### ISSUE-003 — Debug default expõe tracebacks completos em respostas HTTP

**Severidade:** high  
**Área:** security | runtime  
**Arquivo(s):**
- `app/core/config.py`
- `app/main.py`

**Descrição:** `debug=True` é default. Com erro de banco, endpoints retornaram stack traces completos em texto ao cliente.

**Evidência:**

```txt
GET /api/dsm/versions/current -> HTTP/1.1 500 Internal Server Error
content-type: text/plain; charset=utf-8
Traceback ... asyncpg ... Connect call failed ...
```

**Impacto:** Em produção mal configurada, detalhes internos de paths, dependências e banco podem vazar para clientes.

**Correção recomendada:** Default `debug=False`; exigir `APP_ENV=development` para debug; adicionar teste de produção garantindo resposta genérica em 500.

**Bloqueia produção?** sim, se defaults forem usados em produção.

#### ISSUE-004 — README documenta item_id inexistente `tdah`

**Severidade:** high  
**Área:** docs | data | routes  
**Arquivo(s):**
- `README.md`
- `data/dsm/releases/dsm5_operational_2026_05_28/final_json/01_neurodesenvolvimento_full_short.json`

**Descrição:** README usa `/api/dsm/documents/tdah`, mas a release canônica usa `deficit_de_atencao_hiperatividade`.

**Evidência:**

```txt
README: curl http://localhost:8000/api/dsm/documents/tdah
Release: id='deficit_de_atencao_hiperatividade'
```

**Impacto:** Cliente seguindo README receberá 404 após banco/ingestão corretos.

**Correção recomendada:** Atualizar README para o ID real ou criar alias documentado se essa for decisão funcional posterior.

**Bloqueia produção?** não, mas bloqueia documentação confiável.

#### ISSUE-005 — FK extra de `diagnostic_chunks.version_id` existe na migration e não no model

**Severidade:** high  
**Área:** migration | model  
**Arquivo(s):**
- `app/models/dsm.py`
- `alembic/versions/20260528_0001_initial.py`
- `alembic/versions/20260529_0002_hardening.py`

**Descrição:** A migration inicial cria FK simples `diagnostic_chunks.version_id -> diagnostic_versions.id`; o model declara FK composta para `diagnostic_documents(version_id,item_id)`. Após hardening, o banco tem as duas relações; o model só representa a composta.

**Evidência:**

```txt
migration inicial: sa.Column("version_id", sa.Text(), sa.ForeignKey("diagnostic_versions.id", ondelete="CASCADE"), nullable=False)
model: ForeignKeyConstraint(["version_id", "document_item_id"], ["diagnostic_documents.version_id", "diagnostic_documents.item_id"], ...)
```

**Impacto:** Autogenerate futuro pode propor drop/criação indevida; divergência schema-model prejudica manutenção determinística.

**Correção recomendada:** Decidir se a FK simples é intencional; se sim, representar no model; se não, gerar migration de remoção controlada.

**Bloqueia produção?** não imediatamente, mas é incompatibilidade model/migration relevante.

### medium

#### ISSUE-006 — Payload RAG usa `question`, divergindo de exemplos com `query` e do endpoint search

**Severidade:** medium  
**Área:** schema | rag | docs  
**Arquivo(s):**
- `app/schemas/rag.py`
- `app/api/routes/dsm_rag.py`

**Descrição:** `/api/dsm/rag/retrieve` e `/api/dsm/rag/answer` exigem `question`; chamadas com `query` retornam 422.

**Evidência:**

```txt
HTTP/1.1 422 Unprocessable Content
{"detail":[{"type":"missing","loc":["body","question"],"msg":"Field required" ...}]}
```

**Impacto:** Clientes que reutilizam payload de search ou seguem exemplos genéricos falharão.

**Correção recomendada:** Documentar claramente ou aceitar alias `query` em etapa posterior.

**Bloqueia produção?** não

#### ISSUE-007 — Script `validate_dsm_graph` não aceita `--version-id`

**Severidade:** medium  
**Área:** graph | docs | scripts  
**Arquivo(s):**
- `app/scripts/validate_dsm_graph.py`
- `docs/graphify_integration.md`
- `README.md`

**Descrição:** O script real espera caminho de arquivo; comando com `--version-id active` falha. README usa caminho correto, mas o procedimento operacional deve ser padronizado.

**Evidência:**

```txt
python -m app.scripts.validate_dsm_graph --version-id active
error: unrecognized arguments: --version-id
```

**Impacto:** Operador seguindo comando incorreto não consegue validar grafo.

**Correção recomendada:** Padronizar documentação ou adicionar suporte a `--version-id` no script em etapa posterior.

**Bloqueia produção?** não

#### ISSUE-008 — Endpoints agent existem mas não estão documentados no README principal

**Severidade:** medium  
**Área:** docs | routes  
**Arquivo(s):**
- `app/api/routes/dsm_agents.py`
- `README.md`

**Descrição:** OpenAPI expõe `/api/dsm/agent/answer`, `/interview-plan`, `/critic`; README principal não descreve contratos, finalidade, limitações ou segurança desses endpoints.

**Evidência:**

```txt
OpenAPI: /api/dsm/agent/answer, /api/dsm/agent/interview-plan, /api/dsm/agent/critic
README: sem seção equivalente
```

**Impacto:** Funcionalidade pública sem documentação operacional/segurança clara.

**Correção recomendada:** Documentar ou remover/ocultar se experimental.

**Bloqueia produção?** não

### low

#### ISSUE-009 — `StaticFiles(directory="static")` é montado incondicionalmente

**Severidade:** low  
**Área:** runtime | static  
**Arquivo(s):**
- `app/main.py`

**Descrição:** O mount funciona neste repositório porque `static/` existe, mas é frágil em empacotamentos que omitam a pasta.

**Evidência:**

```txt
app.mount("/static", StaticFiles(directory="static"), name="static")
```

**Impacto:** Startup pode falhar em imagem minimalista ou deploy incompleto.

**Correção recomendada:** Montar condicionalmente ou garantir cópia da pasta no Dockerfile.

**Bloqueia produção?** não, desde que static exista.

## 23. Lista de correções recomendadas

1. Reexecutar auditoria com PostgreSQL/pgvector real e Docker disponível.
2. Tornar `debug=False` por padrão e validar comportamento de erro em produção.
3. Harmonizar dimensão de embedding entre settings, model e migration.
4. Resolver divergência de FK em `diagnostic_chunks` entre model e migration.
5. Corrigir README para usar `deficit_de_atencao_hiperatividade` no exemplo de TDAH.
6. Documentar/aliasar `question` nos endpoints RAG.
7. Padronizar comando de validação Graph ou adicionar `--version-id` ao script.
8. Documentar endpoints agent ou marcá-los como experimentais/protegidos.
9. Revalidar search FTS, vector fallback, RAG e graph rebuild após ingestão real.

## 24. Critérios de bloqueio

Bloqueios atuais:

- Banco limpo não pôde ser criado/verificado.
- `alembic upgrade head` não concluiu.
- Importação DSM real não concluiu.
- Versão ativa não pôde ser criada/verificada.
- Endpoints principais pós-ingestão retornaram 500 sem banco.
- Search FTS/vector e RAG não puderam ser validados com dados reais.
- Graph rebuild/export não pôde ser validado com dados reais.

## 25. Veredito final

`BLOCKED`

A base de código tem boa estrutura inicial e passou nas validações locais sem banco (`compileall`, `ruff`, `pytest`, validação de release). Porém a auditoria exigida explicitamente depende de PostgreSQL/pgvector e Docker; como esses recursos estavam indisponíveis, não há evidência suficiente para aprovar produção. A próxima rodada deve executar exatamente os passos bloqueados em ambiente com banco limpo e registrar contagens pós-ingestão, respostas dos endpoints, busca FTS/vector, RAG e Graph.

## Apêndice A — Comandos executados

| Comando | Status | Resultado resumido |
|---|---|---|
| `python --version` | PASS | `Python 3.14.4` |
| `pip install -e ".[dev]"` | WARN | Falha por proxy/PyPI `403 Forbidden` ao buscar setuptools |
| `python -m compileall app` | PASS | Compilou todos os módulos em `app/` |
| `ruff check .` | PASS | `All checks passed!` |
| `pytest -q` | PASS | `30 passed, 1 warning` |
| `docker compose down -v` | WARN | `docker: command not found` |
| `docker compose up --build -d` | WARN | `docker: command not found` |
| `alembic upgrade head` | BLOCKED | Conexão recusada em `localhost:5432` |
| `python -m app.scripts.validate_dsm_files --release-path data/dsm/releases/dsm5_operational_2026_05_28` | PASS | Documents 160, Minimal 26, Excluded 24, Errors 0 |
| `python -m app.scripts.import_dsm --release-path data/dsm/releases/dsm5_operational_2026_05_28 --activate` | BLOCKED | Conexão recusada em `localhost:5432` |
| `uvicorn app.main:app --host 127.0.0.1 --port 8000` | PASS | Startup completo |
| `curl http://localhost:8000/openapi.json` | PASS | HTTP 200 |
| `curl http://localhost:8000/docs` | PASS | HTTP 200 |
| `curl http://localhost:8000/api/health` | PASS | HTTP 200, database unavailable |
| `curl http://localhost:8000/api/dsm/versions/current` | BLOCKED | HTTP 500 sem DB |
| `curl "http://localhost:8000/api/dsm/documents?chapter_id=01"` | BLOCKED | HTTP 500 sem DB |
| `curl http://localhost:8000/api/dsm/registry/minimal` | BLOCKED | HTTP 500 sem DB |
| `curl http://localhost:8000/api/dsm/registry/excluded` | BLOCKED | HTTP 500 sem DB |
| `curl -X POST http://localhost:8000/api/dsm/search ...` | BLOCKED | HTTP 500 sem DB |
| `curl -X POST http://localhost:8000/api/dsm/rag/retrieve ...` com `query` | FAIL | HTTP 422, schema exige `question` |
| `curl http://localhost:8000/api/dsm/graph/status` | PASS | HTTP 200 |
| `curl -X POST http://localhost:8000/api/dsm/graph/rebuild` sem token | PASS | HTTP 401 |
| `curl -X POST http://localhost:8000/api/dsm/graph/rebuild` com token errado | PASS | HTTP 401 |
| `curl -X POST http://localhost:8000/api/dsm/graph/rebuild` com token correto | BLOCKED | HTTP 500 sem DB |
| `python -m app.scripts.export_dsm_graph --version-id active --persist` | BLOCKED | Conexão recusada em `localhost:5432` |
| `python -m app.scripts.validate_dsm_graph --version-id active` | FAIL | Argumento `--version-id` não reconhecido |
| `curl http://localhost:8000/static/graph_test.html` | PASS | HTTP 200 |
| `rg -n --hidden ... 'sk-' 'OPENAI_API_KEY=' 'ANTHROPIC_API_KEY=' 'password'` | PASS | Sem segredo real; placeholders/senhas locais de exemplo |

## Apêndice B — Matriz de consistência entre camadas

| Funcionalidade | Router | Service | Repository | Schema | Model | Migration | Test | README | Status |
|---|---|---|---|---|---|---|---|---|---|
| Health | sim | n/a | n/a | n/a | n/a | n/a | sim | sim | OK |
| Versions | sim | sim | sim | sim | sim | sim | parcial | sim | DB bloqueado |
| Documents | sim | n/a | sim | sim | sim | sim | sim | sim | DB bloqueado; exemplo `tdah` inválido |
| Registry | sim | n/a | sim | sim | sim | sim | sim | sim | DB bloqueado |
| Ingestion | sim | sim | n/a | sim | sim | sim | sim | sim | DB bloqueado |
| Search | sim | sim | sim | sim | chunks | sim | sim | sim | DB bloqueado |
| RAG retrieve | sim | sim | via search | sim | chunks | sim | parcial | pouco claro | schema `question` |
| RAG answer | sim | sim | via search | sim | chunks | sim | parcial | sim | DB bloqueado |
| Graph status | sim | sim | n/a | sim | n/a | n/a | sim | sim | OK |
| Graph rebuild | sim | sim | via graph builder | sim | documents/chunks | sim | sim | sim | DB bloqueado |
| Graph export | sim | sim | via store | sim | n/a | n/a | sim | sim | DB/export bloqueado |
| Graph HTML | static | n/a | n/a | n/a | n/a | n/a | não | sim | HTTP 200; interação visual não testada |
| Agent answer/interview/critic | sim | sim | via search/RAG | sim | chunks | sim | sim | não | endpoint não documentado |
