# MathInstinct — Instinto Matemático Determinístico

## 1. Objetivo

O `MathInstinct` fornece a mesma experiência determinística do IAN-Ω, mas focada em expressões matemáticas e comandos numéricos. Ele detecta expressões diretas (`"2 + 2"`) e frases como `"Quanto é 3 * 5?"` ou `"calculate 7/2"` e responde antes do loop Φ.

## 2. Componentes

1. `nsr.math_instinct.MathInstinct`
   - `analyze(text)` → `MathUtterance(expression, language, role, original)`.
   - `evaluate(text)` → `MathReply(text, value, language)` usando AST seguro (`+`, `-`, `*`, `/`, `^`, parênteses).
2. `nsr.math_bridge.maybe_route_math`
   - Constrói nós LIU (`math_utterance`, `math_reply`), injeta resposta e contexto no ISR, e retorna `MathHook`.
3. `nsr.runtime.run_text_full`
   - Tenta `maybe_route_math` antes do IAN. Quando houver match, o trace começa com `MATH[...]` e o loop Φ é encerrado ao atingir a qualidade mínima.

## 3. Uso rápido

```bash
PYTHONPATH=src python3 - <<'PY'
from nsr import run_text
print(run_text("2 + 2")[0])              # -> "4"
print(run_text("Quanto é 3 * 5?")[0])    # -> "15"
PY
```

Ou diretamente:

```python
from nsr.math_instinct import MathInstinct
instinct = MathInstinct()
print(instinct.evaluate("calculate 7/2").text)  # "3.5"
```

## 4. Extensão e segurança

- Palavras-chave suportadas por idioma estão em `LANGUAGE_KEYWORDS`; adicione novas entradas seguindo o padrão `"lingua": ("gatilho A", "gatilho B")`.
- Apenas operadores `+ - * / ^` e inteiros/decimais são aceitos. Qualquer outro nó AST dispara `ValueError`.
- Ao responder, `MathInstinct` mantém `value` (float) e `answer` (string normalizada) para facilitar auditoria.
- Toda resposta matemática passa a ser registrada no contexto LIU semelhante ao IAN, permitindo inspeção em `outcome.isr.context`.

## 5. Integração com IAN e NSR

- O `MathInstinct` usa o mesmo pipeline de preseed: se o input for matemático, não há passagem pelo parser LxU/NSR — o runtime recebe um ISR já respondido com qualidade ≥ `0.92`.
- Inputs mistos (texto + equação) ainda podem ser roteados para o NSR caso não satisfaçam os filtros do módulo matemático; nesse caso o IAN/LxU assumem o fluxo normal.
- Para consolidar alfabetização numérica e linguística no futuro, compartilhe a tabela CHAR↔CODE do IAN com o `MathInstinct` (ex.: para interpretar dígitos escritos por extenso).

## 6. Próximos passos

- Expandir o conjunto de operações (ex.: `%`, `//`, funções determinísticas) mediante validação formal.
- Adicionar templates de resposta específicos por idioma (ex.: `"Resultado: 42"` em PT/EN/ES/FR/IT).
- Conectar saídas matemáticas a operadores `code/EVAL_*` para manter consistência energética em loops Φ complexos.
