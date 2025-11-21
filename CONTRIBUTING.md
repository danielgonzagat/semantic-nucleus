# Contribuindo com o Núcleo Originário

Obrigada(o) por fortalecer o núcleo simbólico. Este guia descreve o fluxo mínimo para propor melhorias.

## Pré-requisitos

- Python 3.11+ instalado.
- `pip install -e .[dev]` para instalar dependências de desenvolvimento.
- `pre-commit install` para ativar os hooks locais.

## Fluxo de contribuição

1. Abra uma issue descrevendo bug/feature com contexto matemático.
2. Crie um branch: `git checkout -b feat/nome`.
3. Antes de commitar:
   - `pre-commit run --all-files`
   - `coverage run -m pytest && coverage report`
4. Abra o PR referenciando a issue e preencha o template.
5. Aguarde revisão (mínimo 2 aprovações para mudanças de protocolo).

## Padrões de código

- Determinismo acima de tudo: evite fontes de aleatoriedade sem seed fixa.
- Operadores Φ devem permanecer puros (use `isr.snapshot()` antes de mutar).
- Documentação (README/docs/spec) deve acompanhar qualquer feature pública.
- Ao tocar LIU/NSR/ΣVM, inclua testes CTS equivalentes.

## Assinatura DCO

Commits devem conter `Signed-off-by:` (pode usar `git commit -s`).

## Responsabilidades pós-merge

- Atualizar CHANGELOG.
- Criar LIP quando houver mudanças incompatíveis.
- Garantir que CI esteja verde.

Em dúvida? Abra uma discussão em `discussions/architecture`.
