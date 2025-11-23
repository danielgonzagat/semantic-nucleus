# Política de Revisão e Aprovação

Esta política complementa o arquivo [`CODEOWNERS`](../.github/CODEOWNERS) e define quantos revisores são exigidos para cada área crítica.

## Matriz de Responsabilidade

| Área                             | Path principal                    | Revisores mínimos | Observações                                       |
|----------------------------------|-----------------------------------|-------------------|---------------------------------------------------|
| NSR / Meta-LER / LC-Ω           | `src/nsr/`, `tests/nsr/`          | 2 (nsr-core)      | Pelo menos um revisor deve ter contexto de LC-Ω.  |
| ΣVM / bytecode / snapshots      | `src/svm/`, `tests/cts/`          | 2 (svm-core + qa) | Mudanças em opcode/bytecode exigem CTS verde.     |
| Documentação pública e governança| `docs/`, `README.md`              | 1 (docs)          | Alterações normativas devem citar a fonte.        |
| Scripts/infra/CI                | `.github/`, `scripts/`            | 1 (core-team)     | Releases requerem sinal verde do core-team.       |

## Processo

1. Abra o PR com referência às issues/roadmap relevantes.
2. Certifique-se de que o CI (`Tests` + `Release` se aplicável) esteja verde.
3. Solicite revisões aos times listados no `CODEOWNERS`. O GitHub exigirá as aprovações mínimas automaticamente.
4. Para alterações críticas (protocolos LIU/ΣVM/meta_summary), inclua:
   - item no `CHANGELOG.md`,
   - nota em [`docs/cts_policy.md`](./cts_policy.md),
   - breve justificativa na descrição do PR.
5. Após as aprovações, o autor ou um mantenedor aplica o merge utilizando squash ou rebase conforme convenção da equipe.

## Exceções

- Hotfixes de segurança podem seguir um caminho acelerado (1 aprovação do core-team + validação de segurança). O PR deve mencionar o motivo e incluir link para o relatório confidencial.
- Dependabot Bots: PRs automatizados devem receber pelo menos 1 aprovação humana antes do merge.

Siga esta política para manter o Metanúcleo auditável e com revisão cruzada das áreas críticas. Dúvidas podem ser registradas via issue com a etiqueta `governanca`.
