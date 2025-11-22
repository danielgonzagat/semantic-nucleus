# IAN-Ω e Pacotes de Idiomas

Este guia explica como o instinto alfabético-numérico (IAN-Ω) manipula idiomas, como medir impacto de performance e como manter gramáticas/morfologias uniformes e auditáveis.

## 1. Arquitetura geral

1. `nsr.ian.IANInstinct` carrega tabelas CHAR↔CODE, léxico inato e regras de diálogo.
2. `nsr.langpacks` define os pacotes estáticos (`LanguagePack`), cada um composto de:
   - `lexemes`: palavras/lemmas com semântica e POS.
   - `dialog_rules`: intents reconhecidas → plano de resposta determinístico.
   - `conjugations`: mapa lemma+traços → forma textual.
   - `syntactic_patterns`: sequências de semântica usadas para heurísticas de parser/intent.
3. `nsr.ian_bridge` converte as estruturas de fala/resposta em nós LIU auditáveis para o NSR.

## 2. Procedimento para adicionar novos idiomas

1. **Conjunto mínimo**:
   - Saudações (`GREETING_SIMPLE`).
   - Perguntas de estado (`QUESTION_HEALTH`, `QUESTION_HEALTH_VERBOSE`).
   - Intents de resposta (`ANSWER_HEALTH_*`), incluindo conjugação inata para o verbo equivalente a “estar/ser”.

   Exemplo mínimo de JSON:

   ```json
   {
     "code": "xx",
     "lexemes": [
       {"lemma": "SAUDACAO", "semantics": "GREETING_SIMPLE", "pos": "INTERJ", "forms": ["OLA"]},
       {"lemma": "TUDO", "semantics": "ALL_THINGS", "pos": "PRON_INDEF", "forms": ["TUDO"]}
     ],
     "dialog_rules": [
       {
         "trigger_role": "GREETING_SIMPLE_XX",
         "reply_role": "GREETING_SIMPLE_XX_REPLY",
         "reply_semantics": "GREETING_SIMPLE",
         "surface_tokens": ["ola"],
         "language": "xx"
       }
     ],
     "conjugations": [
       {"lemma": "estar", "tense": "pres", "person": 1, "number": "sing", "form": "estou"}
     ],
     "syntactic_patterns": [
       {"name": "GREETING_SIMPLE_XX", "sequence": ["GREETING_SIMPLE"]}
     ]
   }
   ```

2. **Atualizar `LANGUAGE_PACK_DATA`** em `nsr/langpacks.py`:
   - Preencher `lexemes`, `dialog_rules`, `conjugations`, `stopwords`, `syntactic_patterns`.
   - Utilize semânticas padrão (`GREETING_SIMPLE`, `ALL_THINGS`, `STATE_GOOD`, `YOU`, `QUESTION_HOW`, etc.) para garantir uniformidade.
3. **Recarregar e validar**:
   - `python3 - <<'PY' ... from nsr.langpacks import get_language_pack ... PY`.
   - Atualize `tests/nsr/test_langpacks.py` com asserts para o novo código.
4. **Treinar o instinto**:
   - Ajustar `DEFAULT_LANGUAGE_CODES` em `nsr/ian.py`.
   - Adicionar heurísticas específicas apenas quando necessário (ex.: marcador de pontuação, partículas típicas).
5. **Cobrir com testes runtime**:
   - `tests/nsr/test_ian.py` para o pipeline isolado (`respond`).
   - `tests/nsr/test_runtime.py` para validar preseed e `plan_language`.
6. **Validar o pacote**:
   - `python3 scripts/langpack_check.py --code it` para conferir idiomas embutidos.
   - `python3 scripts/langpack_check.py --file caminho.json --fail-on-warn` antes de importar pacotes externos.
7. **Gerar via DSL (opcional)**:
   - Descreva o idioma em formato compacto (JSON) e converta com `python3 scripts/langpack_dsl.py --input spec.json --output langpack.json`.
   - O formato DSL suporta `lexemes`, `dialog`, `conjugations`, `stopwords`, `patterns`, `idioms`, reduzindo redundância ao criar novos pacotes.

## 3. Conversão LIU (`ian_bridge`)

- `utterance_to_struct` grava `intent`, `semantics`, `language` e cada token (surface, normalized, codes, POS) num `STRUCT` LIU – esta é a representação da entrada entendida.
- `reply_plan_to_answer` materializa os `surface_tokens` do plano, resolve placeholders `:CONJ:...`, associa `plan_role`, `plan_semantics`, `plan_language` e uma lista de códigos numéricos para cada token gerado.
- `context_nodes_for_interaction` adiciona dois registros (`ian_utterance` e `ian_reply`) ao contexto do ISR, permitindo auditoria completa mesmo quando o loop Φ não roda.

## 4. Esquema unificado de gramática e morfologia

| Campo                       | Tipo                         | Uso                                                         |
|----------------------------|------------------------------|-------------------------------------------------------------|
| `LexemeSpec`               | lemma, semantics, pos, forms | Base de tokens; `forms` sempre em caixa alta.               |
| `DialogRuleSpec`           | trigger_role, reply_role, reply_semantics, surface_tokens, language | Define o plano textual determinístico usado em `IANInstinct.plan_reply`. |
| `ConjugationSpec`          | lemma, tense, person, number, form | Registra flexões para substituições `:CONJ:...`.           |
| `SyntacticPatternSpec`     | name, sequence               | Sequências semânticas usadas em `_matches_verbose_health_question`. |

Recomendações:
- Normalize sinônimos/variações no próprio `lexicon`.
- Utilize sufixos `_PT`, `_EN`, etc. nos `trigger_role`/`reply_role` para que heurísticas detectem idioma automaticamente.
- `surface_tokens` podem combinar literais e placeholders `:CONJ:lemma:tense:person:number`.

## 5. Performance e escalabilidade

O caminho determinístico precisa permanecer leve. Utilize:

```bash
python3 scripts/ian_bench.py --iterations 2000 --warmup 200 --long-length 2000 --long-runs 50
```

O benchmark mede latência média/mediana/p95 de `IANInstinct.reply`, uso máximo de memória (`tracemalloc`) e o custo de tokenizar textos longos. Inclua o relatório em PRs que modificarem `nsr/ian.py` ou `nsr/langpacks.py`; investigue regressões quando `p95 > 2ms` ou `peak_mem > 10MiB`.

## 6. Integração com o instinto matemático

- Intents que manipulam números devem gerar estruturas alinhadas com os operadores `code/EVAL_*`.
- Ao expandir léxicos, garanta que números em diferentes idiomas sejam mapeados para as mesmas entidades (`dois` → `2`, `two` → `2`).
- O novo `MathInstinct` (ver `docs/math_instinct.md`) compartilha o mesmo princípio do IAN: tabelas fixas, avaliação determinística e bridge dedicado para preseed do NSR.

## 7. Documentação e governança

- Atualize `README.md`, `docs/quickstart.md` e este guia sempre que um idioma ou script for adicionado.
- Registre decisões estruturais em `spec/C_NSR_Runtime/README.md` ou em LIPs.
- Documente exemplos de entrada/saída ao habilitar intents novas (ex.: agradecimentos, comandos, perguntas factuais).

## 8. Auditoria e segurança

- O IAN deve permanecer determinístico: evite estado global mutável.
- Revise heurísticas para evitar complexidade pior que linear em relação ao número de tokens.
- Valide arquivos JSON antes de carregá-los em produção (`scripts/langpack_check.py`).
- Considere rodar o benchmark e o validador em CI para bloquear regressões automaticamente.

## 9. Próximos passos sugeridos

1. Expandir a suíte de intents (negação, agradecimento, despedida) usando o mesmo esquema.
2. Adicionar um DSL declarativo (TOML/JSON) que possa ser compilado para `LanguagePack`.
3. Evoluir o `MathInstinct` para compartilhar a tabela CHAR↔CODE e suportar expressões mais ricas.
4. Planejar revisão de segurança específica para pacotes linguísticos (checklist de invariantes + benchmark obrigatório).

Este documento deve acompanhar qualquer PR que altere o IAN ou pacotes de idioma.
