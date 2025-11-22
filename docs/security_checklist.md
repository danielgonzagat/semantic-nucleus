# Checklist de Segurança Linguística e Matemática

Use esta lista antes de promover um novo pacote de idioma, heurística do IAN ou operador matemático.

## 1. Linguagem

- [ ] Todas as formas (`forms`) estão em maiúsculas e presentes na tabela CHAR↔CODE.
- [ ] Cada `DialogRule` contém `surface_tokens` renderizáveis sem caracteres fora do charset.
- [ ] Tokens `:CONJ:` apontam para conjugação existente (`lemma`, `tense`, `person`, `number`).
- [ ] Sufixos de `trigger_role` e `reply_role` seguem o padrão `_PT`, `_EN`, etc.
- [ ] Novas heurísticas do IAN não iteram quadraticamente sobre tokens (verificar `O(n)`).
- [ ] Scripts (`langpack_check.py --fail-on-warn`) executados para todos os idiomas afetados.
- [ ] `pytest tests/nsr/test_ian.py -k <idioma>` cobre cenários positivos e negativos.

## 2. Matemática

- [ ] Operadores permitidos foram revisados (sem `eval` livre).
- [ ] Chamadas AST (`Call`) aceitam apenas funções whitelisted (`abs`, `sqrt`, …).
- [ ] Inputs não numéricos falham de forma controlada.
- [ ] Benchmarks (`scripts/ian_bench.py` + `scripts/math_*` quando aplicável) rodaram e ficaram dentro dos thresholds.

## 3. Integração NSR

- [ ] `maybe_route_text` e `maybe_route_math` adicionam contexto LIU auditável.
- [ ] `trace.steps[0]` reflete o roteamento correto (`IAN[...]` ou `MATH[...]`).
- [ ] Qualidade inicial (`isr.quality`) é >= `SessionCtx.config.min_quality` quando skipar loop Φ.

## 4. CI / Automação

- [ ] `scripts/langpack_check.py --fail-on-warn` adicionado ao workflow.
- [ ] `scripts/ian_bench.py --max-p95-ms ... --max-peak-mib ...` também no workflow.
- [ ] Novos scripts possuem instruções no README ou em `docs/*`.

## 5. Revisão Manual

- [ ] Diferenças em `LANGUAGE_PACK_DATA` revisadas por pelo menos uma pessoa além da autora.
- [ ] `docs/ian_langpacks.md` e/ou `docs/math_instinct.md` atualizados com o que mudou.
- [ ] Foi registrada uma entrada no CHANGELOG (quando aplicável).

Somente quando todos os itens relevantes estiverem completos, o pacote/heurística deve ser promovido para ambientes superiores.
