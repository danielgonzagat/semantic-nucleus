# Especificação E — Manifesto & Governança

Este dossiê referencia `docs/manifesto.md` e define normas mínimas:

- **Determinismo completo**: toda liberação deve demonstrar hashes de estado idênticos para entradas idênticas.
- **Sem IO no núcleo**: qualquer acesso externo é capacidade opcional documentada e desligada por padrão.
- **Imutabilidade**: arenas de nós LIU e Estruturas ISR são tratadas como dados persistentes.
- **Reatividade**: evolução sempre `ISR_{n+1} = Φ(ISR_n, OP_n)` com loop auditável.
- **Inferência real**: regras `Rule(if_all→then)` + unificação `VAR:?X` obrigatórias em qualquer implementação.
- **Bytecode compatível**: `.svmb` usa opcodes de 1 byte + varint; snapshots `.svms` reconstroem estado.
- **Testes de conformidade**: suites em `/tests` são mandatórias antes de qualquer release.
- **Versionamento**: SemVer para código; ABI ΣVM mantém compatibilidade minor ≥2 versões.
- **Governança**: propostas via LIP (LIU Improvement Proposal) contendo motivação → design → compatibilidade.
