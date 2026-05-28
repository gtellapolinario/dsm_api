# DSM Operational API

API backend para operar uma base DSM normalizada com FastAPI, PostgreSQL 16, SQLAlchemy 2.0 async, Alembic, pgvector, full-text search e endpoints RAG.

## Arquitetura

```text
final_json/ = fonte canônica de release
PostgreSQL = fonte operacional de produção
diagnostic_documents = documentos estruturados do app
diagnostic_registry = itens técnicos MINIMAL/EXCLUDE
diagnostic_chunks = trechos semânticos para busca/RAG
API FastAPI = camada de acesso para frontend e agentes
```

A aplicação preserva cada JSON DSM original em `jsonb`, mantém colunas relacionais para filtros comuns, separa itens renderizáveis de registry não renderizável e gera chunks semânticos para busca textual/vetorial.

## Estrutura

- `app/core`: configuração, sessão async, logging e dependências de segurança.
- `app/models`: modelos SQLAlchemy das tabelas operacionais.
- `app/repositories`: acesso a dados e SQL especializado de FTS/vector search.
- `app/services`: ingestão, chunking, embeddings, busca híbrida, RAG e versionamento.
- `app/api/routes`: endpoints REST versionados em `/api`.
- `app/scripts`: CLIs para importar, validar, reconstruir chunks e criar índices.
- `alembic`: migrações async.
- `tests`: testes unitários e de rotas.

## Rodando com Docker

```bash
cp .env.example .env
docker compose up -d postgres
alembic upgrade head
uvicorn app.main:app --reload
```

Para subir API e banco juntos:

```bash
docker compose up --build
```

## Migrações

A migração inicial habilita `vector` e `pgcrypto`, cria as tabelas `diagnostic_versions`, `diagnostic_documents`, `diagnostic_registry` e `diagnostic_chunks`, constraints de categoria/renderização, índices GIN para JSON/FTS e índice HNSW para embeddings.

```bash
alembic upgrade head
```

Se o índice HNSW falhar por incompatibilidade local da extensão pgvector, use busca sequencial temporariamente ou crie índice IVFFlat/HNSW depois com:

```bash
python -m app.scripts.create_indexes
```

## Importação DSM

Fluxo completo esperado:

```bash
python -m app.scripts.import_dsm \
  --final-json ./dsm-reducao/final_json \
  --registry ./dsm-reducao/normalized_registry \
  --version-id dsm5_operational_2026_05_28 \
  --label "DSM-5 Operational Reduction v2C" \
  --source-package "Kimi_Agent_DSM二轮修订 (4)" \
  --activate
```

O importador:

1. lê todos os JSONs em `final_json/*.json`;
2. lê `minimal_all.json` e `excluded_all.json`;
3. valida categorias, IDs, `diagnostic_rule`, severidade, estrutura e `ui_mode`;
4. cria uma versão em `draft`;
5. insere documentos renderizáveis e registry separadamente;
6. gera chunks semânticos por campos como `diagnostic_rule`, `criteria`, `severity`, `critical_differentials` e `key_questions`;
7. preenche `search_vector` com `to_tsvector('portuguese', ...)`;
8. gera embeddings quando habilitado;
9. ativa a versão se `--activate` for usado.

Validação sem importação:

```bash
python -m app.scripts.validate_dsm_files \
  --final-json ./dsm-reducao/final_json \
  --registry ./dsm-reducao/normalized_registry
```

## Ativando versão

```bash
curl -X POST http://localhost:8000/api/dsm/versions/dsm5_operational_2026_05_28/activate
```

Ao ativar uma versão, qualquer versão ativa anterior é arquivada. Uma constraint parcial garante apenas uma versão `active`.

## Endpoints principais

```bash
curl http://localhost:8000/api/health
curl http://localhost:8000/api/dsm/versions
curl http://localhost:8000/api/dsm/versions/current
curl "http://localhost:8000/api/dsm/documents?chapter_id=01"
curl http://localhost:8000/api/dsm/documents/transtorno_deficit_atencao_hiperatividade
curl http://localhost:8000/api/dsm/chapters
curl http://localhost:8000/api/dsm/registry/minimal
curl http://localhost:8000/api/dsm/registry/excluded
```

Ingestão via API exige `X-Admin-Token`:

```bash
curl -X POST http://localhost:8000/api/dsm/ingest \
  -H "Content-Type: application/json" \
  -H "X-Admin-Token: change-me" \
  -d '{
    "final_json_path":"./dsm-reducao/final_json",
    "registry_path":"./dsm-reducao/normalized_registry",
    "version_id":"dsm5_operational_2026_05_28",
    "label":"DSM-5 Operational Reduction v2C",
    "activate":true,
    "generate_embeddings":false
  }'
```

## Embeddings

Configure no `.env`:

```env
EMBEDDINGS_ENABLED=true
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSIONS=1536
OPENAI_API_KEY=...
```

Com `EMBEDDINGS_ENABLED=false`, a API funciona em modo FTS. Se `use_vector=true` e embeddings estiverem desativados, a busca cai para FTS quando `allow_fallback=true`; caso contrário retorna erro controlado.

## Busca híbrida

```bash
curl -X POST http://localhost:8000/api/dsm/search \
  -H "Content-Type: application/json" \
  -d '{
    "query":"diferença entre tique transitório e Tourette",
    "version_id":"active",
    "chapter_id":"01",
    "chunk_types":["diagnostic_rule","critical_differentials"],
    "top_k":5,
    "use_fts":true,
    "use_vector":false
  }'
```

A busca combina filtros de metadados, full-text search e, quando configurado, similaridade vetorial com `pgvector`.

## RAG

Recuperar chunks:

```bash
curl -X POST http://localhost:8000/api/dsm/rag/retrieve \
  -H "Content-Type: application/json" \
  -d '{"question":"Como diferenciar tique transitório de Tourette?","version_id":"active","top_k":5}'
```

Gerar resposta:

```bash
curl -X POST http://localhost:8000/api/dsm/rag/answer \
  -H "Content-Type: application/json" \
  -d '{"question":"Como diferenciar tique transitório de Tourette?","version_id":"active","top_k":5}'
```

Por padrão `RAG_ANSWER_ENABLED=false`, então o endpoint retorna os chunks e a mensagem `RAG answer disabled. Retrieval results returned.`. Quando habilitado, a resposta deve ficar estritamente limitada às evidências recuperadas e não substitui julgamento clínico.

## Uso no frontend

1. Chame `/api/dsm/versions/current` para descobrir a versão ativa.
2. Liste capítulos em `/api/dsm/chapters`.
3. Liste transtornos renderizáveis em `/api/dsm/documents` com filtros de capítulo/categoria.
4. Busque detalhes de entrevista em `/api/dsm/documents/{item_id}`.
5. Use `/api/dsm/registry/*` apenas para painéis técnicos/residuais; esses itens não devem aparecer como entrevistas estruturadas.
6. Use `/api/dsm/search` ou `/api/dsm/rag/retrieve` para suporte semântico contextual.

## Qualidade

```bash
ruff check .
pytest
```
