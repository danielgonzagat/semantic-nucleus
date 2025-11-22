# IAN-Ω e Pacotes de Idiomas

Este guia explica como o instinto alfabético-numérico (IAN-Ω) manipula idiomas, como medir impacto de performance e como manter gramáticas/morfologias uniformes e auditáveis.

## 1. Arquitetura geral

1. `nsr.ian.IANInstinct` carrega tabelas CHAR↔CODE, léxico inato e regras de diálogo.
2. `nsr.langpacks` define os pacotes estáticos (`LanguagePack`), cada um composto de:
   - `lexemes`: palavras/lemmas com semântica e POS.
   - `dialog_rules`: intents reconhecidas → plano de resposta determinístico.
   - `conjugations`: mapa lemma+traços → forma textual.
   - `syntactic_patterns`: sequências de semântica usadas para heurísticas de parser/intent.
3. `nsr.ian_bridge` traduz uma fala reconhecida para LIU (`struct`, `tokens`, `plan_language`) e injeta o preseed no NSR.

## 2. Procedimento para adicionar novos idiomas

1. **Conjunto mínimo**:
   - Saudações (`GREETING_SIMPLE`).
   - Perguntas de estado (`QUESTION_HEALTH`, `QUESTION_HEALTH_VERBOSE`).
   - Intents de resposta (`ANSWER_HEALTH_*`), incluindo conjugação inata para o verbo equivalente a “estar/ser”.
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

## 3. Esquema unificado de gramática e morfologia

| Campo                       | Tipo                         | Uso                                                         |
|----------------------------|------------------------------|-------------------------------------------------------------|
| `LexemeSpec`               | lemma, semantics, pos, forms | Base de tokens; `forms` sempre em caixa alta.               |
| `DialogRuleSpec`           | trigger_role, reply_role, reply_semantics, surface_tokens, language | Define o plano textual determinístico usado em `IANInstinct.plan_reply`. |
| `ConjugationSpec`          | lemma, tense, person, number, form | Registra flexões para substituições `:CONJ:...`.           |
| `SyntacticPatternSpec`     | name, sequence               | Sequências semânticas usadas em `_matches_verbose_health_question`. |

Recomendações:
- Utilize sempre os mesmos identificadores (`QUESTION_HEALTH_*`, `ANSWER_HEALTH_*`, `GREETING_SIMPLE_*`) para que regras genéricas do IAN consigam inferir idioma com `role` + sufixo.
- Conjugação: quando possível, normalize tempos/pessoas em `pres` + `{1,2,3}` × `{sing, plur}`.
- `surface_tokens` podem misturar strings literais e placeholders `:CONJ:lemma:tense:person:number`.

## 4. Performance e escalabilidade

O caminho determinístico precisa permanecer leve (sub-milisegundo por fala nas CPUs alvo). Para medir impacto:

```bash
python3 scripts/ian_bench.py --iterations 2000 --warmup 200
```

O benchmark:
- Percorre as frases de boot em PT/EN/ES/FR/IT.
- Mede latência por chamada (`IANInstinct.reply`) e picos de memória com `tracemalloc`.
- Emite média/mediana/p95 e throughput estimado.

Inclua o resultado no PR quando alterar `nsr/ian.py` ou `nsr/langpacks.py`. Se o p95 ultrapassar 2 ms ou o pico superar 10 MB, investigue regressões (geralmente lexicon excessivo ou heurísticas ineficientes).

## 5. Integração com o instinto matemático

O NSR já possui operadores `code/EVAL_PURE` e pipelines de raciocínio matemático dentro do runtime. Para manter coerência:

1. Garanta que intents linguísticas que descrevem estados numéricos sejam traduzidas para LIU que possa ser consumida pelos operadores matemáticos (ex.: `semantics=STATE_NUMBER`).
2. Ao adicionar novos idiomas, avalie como os tokens numéricos são representados (ex.: “dois”, “two”, “dos”) e adicione mapeamentos no lexicon para convergir em entidades numéricas.
3. Futuras extensões podem compartilhar a mesma tabela CHAR↔CODE para IAN e módulos matemáticos, evitando duplicidade de codificação.

## 6. Documentação e governança

- Sempre atualize `README.md` e `docs/quickstart.md` com o conjunto padrão de idiomas suportados.
- Registre decisões de gramática no `spec/C_NSR_Runtime/README.md` ou em LIPs dedicadas.
- Quando incluir idiomas novos, anexe exemplos de entrada/saída esperada e explique quais intents foram cobertas.

## 7. Auditoria e segurança

- O IAN deve permanecer determinístico: evite qualquer estado global mutável fora das tabelas.
- Recomendação de revisão periódica:
  - Procure loops de heurísticas que dependam do comprimento da entrada (risco de O(n²)).
  - Garanta que tabelas importadas via JSON sejam validadas antes de carregar (nos ambientes produtivos utilize `import_language_pack` com verificação manual).
  - Agende revisões formais de regras sempre que um idioma novo for habilitado.
- Para detectar regressões automaticamente, considere adicionar benchmarks a CI e monitorar diffs no `CONJUGATION_TABLE`.

## 8. Próximos passos sugeridos

1. Expandir a suíte de intents (negação, agradecimento, despedida) usando o mesmo esquema.
2. Adicionar um DSL leve para definir gramáticas (por exemplo, declarando `pattern -> reply` em TOML/JSON e convertendo para `LanguagePack`).
3. Criar uma camada equivalente para “instinto matemático”, reutilizando os princípios aqui descritos (tabelas fixas, operadores determinísticos, testes focados).
4. Planejar revisão de segurança específica para os pacotes linguísticos, com checklists de invariantes.

Este documento deve acompanhar qualquer PR que altere o IAN ou pacotes de idioma.
