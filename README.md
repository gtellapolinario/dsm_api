# dsm_api

Repositório de dados operacionais DSM-5 para ingestão e consumo por serviços de API.

## Release disponível

A release atualmente versionada está em:

```text
data/
  dsm/
    releases/
      dsm5_operational_2026_05_28/
        final_json/
        normalized_registry/
        INDEX_MASTER_2B.md
        manifest.json
```

## Estrutura dos dados

- `manifest.json`: metadados da release, contagens consolidadas e caminhos relativos para os artefatos principais.
- `INDEX_MASTER_2B.md`: índice mestre da redução operacional DSM-5, com resumo por capítulo, critérios de aceitação e validações da rodada.
- `final_json/`: 21 arquivos JSON renderizáveis por capítulo, contendo itens `FULL` e `SHORT` para entrevista estruturada.
- `normalized_registry/`: registros normalizados não renderizáveis para ingestão complementar, incluindo itens mínimos e excluídos.

## Contagens consolidadas

| Categoria | Total |
| --- | ---: |
| FULL | 79 |
| SHORT | 81 |
| Renderizáveis | 160 |
| Minimal | 26 |
| Exclude | 24 |
| Registry | 50 |

## Observações de uso

- A release é marcada como `release_candidate` no manifesto.
- Os caminhos declarados no manifesto são relativos à pasta da própria release.
- Os itens em `final_json/` são a fonte operacional para renderização de entrevistas estruturadas.
- Os itens em `normalized_registry/` não renderizam entrevista estruturada e devem ser tratados como registros auxiliares.

## Aviso

Este repositório contém dados operacionais para software. Ele não substitui julgamento clínico, validação médica, licenciamento de materiais diagnósticos ou revisão regulatória antes de uso em produção.
