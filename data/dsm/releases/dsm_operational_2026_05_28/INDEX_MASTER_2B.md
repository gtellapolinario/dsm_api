# DSM-5 Chapter Reduction — INDEX MASTER 2B (Rodada 2D)

**Pipeline:** dsm-chapter-reduction-swarm
**Data:** 2026-05-24
**Rodada:** 2D (Correcao Canonica Cap 16)
**Status:** READY_FOR_DEV

---

## Resumo Consolidado

| Categoria | Contagem |
|-----------|----------|
| **FULL** | 79 |
| **SHORT** | 81 |
| **MINIMAL** | 26 |
| **EXCLUDE** | 24 |
| **Total renderizavel** | 160 |
| **Total registry** | 50 |
| **Capitulos processados** | 21 |
| **Validacoes** | 11/11 PASS |
| **Mismatches** | 0 |

---

## Contagens por Capitulo

| Cap | Nome | FULL | SHORT | Total |
|-----|------|------|-------|-------|
| 01 | Transtornos do Neurodesenvolvimento | 9 | 4 | 13 |
| 02 | Espectro da Esquizofrenia e Outros Transtornos Psicoticos | 4 | 4 | 8 |
| 03 | Transtorno Bipolar e Transtornos Relacionados | 2 | 3 | 5 |
| 04 | Transtornos Depressivos | 4 | 2 | 6 |
| 05 | Transtornos de Ansiedade | 5 | 4 | 9 |
| 06 | Transtorno Obsessivo-Compulsivo e Transtornos Relacionados | 3 | 4 | 7 |
| 07 | Transtornos Relacionados a Trauma e Estressores | 3 | 2 | 5 |
| 08 | Transtornos Dissociativos | 3 | 1 | 4 |
| 09 | Transtornos de Sintomas Somaticos e Relacionados | 5 | 1 | 6 |
| 10 | Transtornos Alimentares | 4 | 2 | 6 |
| 11 | Transtornos da Eliminacao | 0 | 3 | 3 |
| 12 | Transtornos do Sono-Vigilia | 6 | 6 | 12 |
| 13 | Disfuncoes Sexuais | 7 | 1 | 8 |
| 14 | Disforia de Genero | 2 | 1 | 3 |
| 15 | Transtornos Disruptivos, do Controle de Impulsos e da Conduta | 3 | 2 | 5 |
| 16 | Transtornos Relacionados a Substancias e Transtornos Aditivos | 6 | 22 | 28 |
| 17 | Transtornos Neurocognitivos | 2 | 1 | 3 |
| 18 | Transtornos da Personalidade | 10 | 1 | 11 |
| 19 | Transtornos Parafilicos | 1 | 7 | 8 |
| 20 | Outros Transtornos Mentais | 0 | 0 | 0 |
| 21 | Transtornos do Movimento Induzidos por Medicamentos e Outros Efeitos Adversos | 0 | 10 | 10 |

| **TOTAL** | | **79** | **81** | **160** |

---

## Patches CRITICAL Aplicados (Rodada 2B)

| # | Capitulo | Transtorno | Campo |
|---|----------|-----------|-------|
| 1 | 01 | TDAH | estrutura_diagnostica: assimetricos -> simetricos |
| 2 | 01 | Tique Transitorio | duracao: >= 1 ano -> < 1 ano |
| 3 | 04 | TDM | gravidade.tipo: ordinal_simples -> episodio_atual |
| 4 | 15 | TOD | gravidade.tipo: ordinal_por_dominio -> pervasividade_contextual |

---

## Correcoes Capitulo 16 (Rodada 2D)

| Metrica | Antes | Depois |
|---------|-------|--------|
| Itens JSON | 10 | 28 |
| FULL | 6 | 6 |
| SHORT | 4 | 22 |
| Intoxicacoes representadas | 0 | 9 (proprias) |
| Abstinencias representadas | 0 | 9 (proprias) |

Decisao canônica: Intoxicacoes e abstinencias sao **itens proprios** no JSON.

---

## Correcoes de Supernormalizacao (Rodada 2C)

| Transtorno | De | Para |
|-----------|-----|------|
| Transtorno da Fala | temporal_topografico | qualitativo_descritivo |
| Transtorno do Movimento Estereotipado | temporal_topografico | qualitativo_descritivo |
| Transtorno do Desenvolvimento da Coordenacao | temporal_topografico | qualitativo_descritivo |

---

## Criterio de Aceitacao Final

| Criterio | Status |
|----------|--------|
| 4 patches CRITICAL aplicados (2B) | ✅ |
| Cap 16 reparseado com 28 itens (2D) | ✅ |
| final_corrected/ gerado (21 arquivos) | ✅ |
| final_json/ gerado (21 arquivos, 160 itens) | ✅ |
| Reconciliacao 160/160 MATCH | ✅ |
| minimal_all.json e excluded_all.json | ✅ |
| Nenhuma entrada registry perdida | ✅ |
| Estruturas supernormalizadas corrigidas | ✅ |
| blocked_patches.json reflete estado real | ✅ (0 bloqueados) |
| Nenhum source/*.original.md alterado | ✅ |
| Status = READY_FOR_DEV | ✅ |

---

*Gerado automaticamente — DSM Chapter Reduction Swarm Rodada 2D*
