# DSM Operational API

API FastAPI operacional para servir uma redução DSM estruturada a aplicações clínicas, educacionais e de apoio a triagem. A API usa PostgreSQL, SQLAlchemy async, pgvector, Alembic, busca textual, busca vetorial opcional e RAG extrativo com citações.

## O que esta API é

- Um backend operacional para expor documentos DSM renderizáveis (`FULL` e `SHORT`).
- Um registry para itens não renderizáveis (`MINIMAL` e `EXCLUDE`).
- Um serviço de ingestão versionada da release em `data/dsm/releases/dsm5_operational_2026_05_28/`.
- Um serviço de busca FTS e híbrida com fallback quando embeddings estão desativados.
- Um serviço RAG que só responde com chunks citados.

## O que esta API não é

- Não é dispositivo médico.
- Não substitui julgamento clínico.
- Não faz diagnóstico autônomo.
- Não deve ser usada como fonte normativa sem revisão profissional e validação regulatória.

## Arquitetura

- `app/main.py`: fábrica FastAPI, CORS e middleware de request id.
- `app/models/`: modelos SQLAlchemy.
- `app/repositories/`: consultas e comandos de banco.
- `app/services/`: ingestão, versionamento, chunking, embeddings, busca e RAG.
- `app/api/routes/`: endpoints HTTP.
- `alembic/`: migrações do schema PostgreSQL/pgvector.
- `data/dsm/releases/`: releases DSM versionadas.
- `clients/typescript/`: cliente TypeScript e exemplos.

## Banco de dados

O banco usa PostgreSQL com as extensões `vector` e `pgcrypto`. As tabelas principais são:

- `diagnostic_versions`: versões DSM, com apenas uma ativa.
- `diagnostic_documents`: itens renderizáveis.
- `diagnostic_registry`: itens não renderizáveis.
- `diagnostic_chunks`: chunks pesquisáveis, com FK composta para documentos.
- `diagnostic_ingestion_runs`: auditoria de ingestões.

## Rodar localmente

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload
```

Health check:

```bash
curl http://localhost:8000/api/health
```

## Rodar com Docker Compose

```bash
docker compose up --build
```

O serviço `api` aguarda o Postgres ficar saudável, executa `alembic upgrade head` e inicia `uvicorn` na porta `8000`.

## Validar a release DSM

```bash
python app/scripts/validate_dsm_files.py \
  --release-path data/dsm/releases/dsm5_operational_2026_05_28 \
  --report-json validation_report.json \
  --report-md validation_report.md
```

A validação bloqueia:

- `renderable != 160`.
- `registry != 50`.
- IDs duplicados.
- `FULL`/`SHORT` sem `diagnostic_rule`.
- `MINIMAL`/`EXCLUDE` em `final_json`.
- estruturas, severidade ou `ui_mode` inválidos.

## Importar e ativar release

```bash
python app/scripts/import_dsm.py \
  --release-path data/dsm/releases/dsm5_operational_2026_05_28 \
  --activate
```

Via API administrativa:

```bash
curl -X POST http://localhost:8000/api/dsm/ingest \
  -H 'content-type: application/json' \
  -H 'x-admin-token: change-me' \
  -d '{
    "final_json_path": "data/dsm/releases/dsm5_operational_2026_05_28/final_json",
    "registry_path": "data/dsm/releases/dsm5_operational_2026_05_28/normalized_registry",
    "version_id": "dsm5_operational_2026_05_28",
    "label": "DSM-5 Operational Reduction v2C",
    "activate": true,
    "generate_embeddings": false
  }'
```

Ativar versão já importada:

```bash
curl -X POST http://localhost:8000/api/dsm/versions/dsm5_operational_2026_05_28/activate \
  -H 'x-admin-token: change-me'
```

## Endpoints principais

```bash
curl http://localhost:8000/api/dsm/versions
curl http://localhost:8000/api/dsm/versions/current
curl 'http://localhost:8000/api/dsm/documents?limit=20&category=FULL&chapter_id=01'
curl http://localhost:8000/api/dsm/documents/tdah
curl http://localhost:8000/api/dsm/registry/minimal
curl http://localhost:8000/api/dsm/registry/excluded
```

## Busca FTS

```bash
curl -X POST http://localhost:8000/api/dsm/search \
  -H 'content-type: application/json' \
  -d '{"query":"transtorno de pânico", "use_vector":false, "use_fts":true, "top_k":8}'
```

Python requests:

```python
import requests

response = requests.post(
    "http://localhost:8000/api/dsm/search",
    json={"query": "transtorno de pânico", "use_vector": False, "use_fts": True},
    timeout=20,
)
print(response.json()["results"])
```

## Busca vetorial

Configure:

```bash
EMBEDDINGS_ENABLED=true
EMBEDDINGS_REQUIRED=true
OPENAI_API_KEY=sk-...
```

Depois importe com `--generate-embeddings`. Se embeddings estiverem desativados, a busca vetorial pode fazer fallback para FTS quando `allow_fallback=true`.

## RAG com chunks citados

```bash
curl -X POST http://localhost:8000/api/dsm/rag/answer \
  -H 'content-type: application/json' \
  -d '{"question":"Quais critérios diferenciam TDAH de ansiedade?", "top_k":5}'
```

A resposta inclui `chunks` e `citations`. Se nenhum chunk for recuperado, a API não inventa resposta.

## Consumir em TypeScript fetch

```ts
const response = await fetch("http://localhost:8000/api/dsm/search", {
  method: "POST",
  headers: { "content-type": "application/json" },
  body: JSON.stringify({ query: "transtorno de pânico", use_vector: false, use_fts: true })
});
const result = await response.json();
console.log(result.results);
```

Ou use `clients/typescript/src/index.ts`:

```ts
import { DsmApiClient } from "./clients/typescript/src/index";

const client = new DsmApiClient("http://localhost:8000");
const docs = await client.documents({ limit: 10 });
```

## React hook

```tsx
import { useEffect, useState } from "react";

export function useDsmDocuments() {
  const [documents, setDocuments] = useState([]);
  useEffect(() => {
    fetch("http://localhost:8000/api/dsm/documents?limit=50")
      .then((r) => r.json())
      .then(setDocuments);
  }, []);
  return documents;
}
```

## TanStack Query

```tsx
import { useQuery } from "@tanstack/react-query";

export function useDsmSearch(query: string) {
  return useQuery({
    queryKey: ["dsm-search", query],
    enabled: query.length > 2,
    queryFn: async () => {
      const response = await fetch("http://localhost:8000/api/dsm/search", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ query, use_vector: false, use_fts: true })
      });
      if (!response.ok) throw new Error(await response.text());
      return response.json();
    }
  });
}
```

## CORS

Configure origens separadas por vírgula:

```env
CORS_ORIGINS=http://localhost:3000,http://localhost:5173,https://app.example.com
```

Use `*` apenas em ambientes controlados.

## Endpoints administrativos

Endpoints de ingestão e ativação exigem:

```http
X-Admin-Token: change-me
```

Configure em produção:

```env
ADMIN_TOKEN=um-token-forte
APP_ENV=production
DSM_RELEASE_ROOT=/app/data/dsm/releases
```

Em produção, paths de ingestão precisam ficar abaixo de `DSM_RELEASE_ROOT`; path traversal com `..` é bloqueado.

## Backup e restore

Backup:

```bash
DATABASE_URL=postgresql://dsm:dsm_password@localhost:5432/dsm_api scripts/backup_db.sh
```

Restore:

```bash
DATABASE_URL=postgresql://dsm:dsm_password@localhost:5432/dsm_api scripts/restore_db.sh backups/dsm_api.dump
```

## Deploy em VPS

1. Instale Docker e Docker Compose.
2. Clone o repositório.
3. Copie `.env.example` para `.env` e ajuste `ADMIN_TOKEN`, `CORS_ORIGINS` e secrets.
4. Execute `docker compose up -d --build`.
5. Rode validação e ingestão se o volume de banco estiver limpo.
6. Monitore `/api/health/readiness`.

## Traefik

Exemplo de labels para o serviço `api`:

```yaml
labels:
  - traefik.enable=true
  - traefik.http.routers.dsm.rule=Host(`dsm.example.com`)
  - traefik.http.routers.dsm.entrypoints=websecure
  - traefik.http.routers.dsm.tls.certresolver=letsencrypt
  - traefik.http.services.dsm.loadbalancer.server.port=8000
```

## Atualizar versão DSM

1. Adicione nova pasta em `data/dsm/releases/<nova_versao>/`.
2. Inclua `manifest.json`, `final_json/` e `normalized_registry/`.
3. Rode `validate_dsm_files.py`.
4. Rode `import_dsm.py --release-path ...` sem `--activate`.
5. Revise contagens, busca e chunks.
6. Ative com endpoint administrativo.

## Observabilidade

- `X-Request-ID` é propagado/respeitado.
- Logs são JSON estruturados.
- Busca, ingestão e RAG registram duração.
- Health checks: `/api/health`, `/api/health/db`, `/api/health/vector`, `/api/health/readiness`.

## Troubleshooting

- `ModuleNotFoundError: app`: execute comandos a partir da raiz do repo ou use os scripts atualizados.
- `vector extension missing`: use a imagem `pgvector/pgvector:pg16` e rode `alembic upgrade head`.
- `Invalid admin token`: envie `X-Admin-Token` igual a `ADMIN_TOKEN`.
- `Path must be inside DSM_RELEASE_ROOT`: ajuste `DSM_RELEASE_ROOT` ou mova a release para a pasta permitida.
- Busca vetorial retorna erro: configure embeddings ou envie `use_vector=false`.

## CI

O workflow executa ruff, pytest, Alembic, validação da release, importação e docker build. Pull requests devem passar antes do merge.

## Limitações clínicas e regulatórias

Esta API é infraestrutura de dados. Ela não valida diagnóstico, não substitui profissional habilitado e não deve ser apresentada a usuários finais como ferramenta diagnóstica sem governança clínica, auditoria, revisão de conteúdo e avaliação regulatória aplicável.

## Knowledge Graph / Graphify experimental

A API inclui uma camada experimental de Knowledge Graph derivada das tabelas canônicas `diagnostic_versions`, `diagnostic_documents`, `diagnostic_registry` e `diagnostic_chunks`. Graphify é opcional: por padrão, a API gera exports locais em JSON e continua funcionando sem Graphify instalado.

Configuração básica:

```env
GRAPH_ENABLED=true
GRAPHIFY_ENABLED=false
GRAPHIFY_CLI_PATH=
GRAPH_EXPORT_DIR=graph_exports
```

Gerar grafo local:

```bash
python -m app.scripts.export_dsm_graph --version-id active --persist
```

Validar export:

```bash
python -m app.scripts.validate_dsm_graph graph_exports/<version_id>/graph.json
```

Testar visualmente:

```txt
http://localhost:8000/static/graph_test.html
```

Documentação completa: [`docs/graphify_integration.md`](docs/graphify_integration.md).
