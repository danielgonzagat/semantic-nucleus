# Manifesto do Núcleo Originário

## Princípios

1. **Significado como estado matemático** – Inteligência simbólica nasce de estruturas LIU/ISR, não de estatística ou pesos.
2. **Determinismo absoluto** – mesmo input ⇒ mesmo trace ⇒ mesmo hash. Paralelismo só com redução ordenada.
3. **CPU-first** – nenhuma dependência funcional de GPU ou aceleradores; otimizações são opcionais.
4. **Reatividade fechada** – `ISR_{n+1} = Φ(ISR_n, OP_n)` até convergir (`quality ≥ τ` e `answer ≠ NIL`).
5. **Sandbox total** – núcleos LIU/NSR/ΣVM não fazem IO; capacidades externas exigem política explícita.
6. **Auditabilidade** – cada passo produz `Trace` estruturado e snapshots SVMS reproduzíveis.
7. **Ética e governança abertas** – especificações públicas (este repositório), LIPs e CTS obrigatórios para releases.

## Normas técnicas

- **LIU**: S-expr/JSON canônicos, arenas imutáveis, tipagem estática (`liu.wf`).
- **NSR**: operadores Φ puros (NORMALIZE, ANSWER, INFER, MAP, REDUCE, REWRITE, EXPAND, COMPARE, EXTRACT, EXPLAIN, SUMMARIZE).
- **ΣVM**: bytecode SVMB com opcodes para construir nós LIU, operar sobre o ISR (relações/fila/quality) e despachar Φ de forma auditável (`HASH_STATE`, `TRAP`, snapshots).
- **Compiladores**: frontends multilíngue convergem para `code/*` relations, evitando execução dinâmica.
- **Testes**: suites mínimas para WF/determinismo/inferência/micro-ops/compilers; novas features só entram com casos de ouro.

## Segurança

- Sem side-effects em operadores; todos retornam novos estados.
- Cotas (passos, novos fatos, profundidade de unificação) configuráveis em `SessionCtx.Config`.
- Detecção de contradições habilitável (`Config.enable_contradiction_check` + `nsr.consistency.detect_contradictions`).
- snapshots `.svms` devem ser assinados quando usados em produção.

## Versionamento & ABI

- Código segue SemVer; ΣVM publica `VERSION = (major, minor)` em `svm.bytecode`.
- Mudanças incompatíveis na LIU exigem LIP + bump major.
- ABI ΣVM garante compatibilidade para pelo menos 2 versões minor anteriores.

## Governança

- **LIPs**: documento curto com motivação → mudança → análise de compatibilidade → atualização de testes.
- **Comitês sugeridos**: Core Spec WG, ABI/Bytecode WG, Segurança & Auditoria, Frontends.
- **Processo**: PR + LIP + prova de testes; merges exigem consenso aberto.

## Ética aplicada

- Transparência: qualquer decisão automatizada deve fornecer `Trace` e LIU de resposta para auditoria humana.
- Privacidade: snapshots devem omitir dados pessoais ou aplicar mascaramento determinístico.
- Neutralidade: sem heurísticas escondidas; todo conhecimento explícito fica em ontologias/rules controladas por humanos.

## Compasso de 10 anos

1. **Ano 0-1** – consolidar LIU/NSR/ΣVM, CTS v1.
2. **Ano 1-3** – ampliar operadores Φ, paralelismo determinístico, ferramentas de inspeção.
3. **Ano 3-5** – pacotes setoriais (finanças, jurídico), integração opcional com ML como capacidade externa.
4. **Ano 5-10** – especializações de hardware (micro-ops em FPGA/ASIC), provas formais de preservação/progresso.

Este manifesto deve acompanhar qualquer distribuição do Núcleo Originário.
