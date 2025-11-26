# Implementação de Aprendizado Sem Pesos

## Status Atual

✅ **Implementado**:
- `WeightlessLearner`: Sistema base de aprendizado estrutural
- `PatternCompressor`: Compressão de padrões frequentes
- Integração com sistema de memória episódica existente

## Como Funciona

### 1. Armazenamento de Episódios

```python
from nsr.weightless_learning import WeightlessLearner, Episode
from nsr import run_text_full, SessionCtx

learner = WeightlessLearner()

# Após cada execução, armazena episódio
session = SessionCtx()
outcome = run_text_full("O carro tem rodas", session)

episode_fp = learner.add_episode(
    input_text="O carro tem rodas",
    input_struct=outcome.isr.relations[0],  # Simplificado
    output_text=outcome.answer,
    output_struct=outcome.isr.answer,
    relations=outcome.isr.relations,
    context=outcome.isr.context,
    quality=outcome.quality,
)
```

### 2. Extração de Padrões

```python
# Após acumular muitos episódios, extrai padrões
patterns = learner.extract_patterns(min_support=5)

for pattern in patterns:
    print(f"Padrão: {pattern.structure}")
    print(f"Frequência: {pattern.frequency}")
    print(f"Confiança: {pattern.confidence}")
```

### 3. Aprendizado de Regras

```python
# Aprende regras a partir de padrões
rules = learner.learn_rules_from_patterns()

# Regras podem ser adicionadas ao SessionCtx
session.kb_rules = tuple(rules)
```

### 4. Busca de Episódios Similares

```python
# Quando recebe nova entrada, busca episódios similares
from nsr.parser import build_struct
from nsr.lex import tokenize, DEFAULT_LEXICON

tokens = tokenize("A bicicleta tem pedais", DEFAULT_LEXICON)
query_struct = build_struct(tokens, language="pt")

similar = learner.find_similar_episodes(query_struct, k=5)

# Usa respostas similares como base
if similar:
    best_match = similar[0]
    # Adapta resposta do episódio similar
```

## Integração com Sistema Atual

### Modificar `runtime.py`

```python
# Em run_text_full, após processar:
from nsr.weightless_learning import WeightlessLearner

# Carrega learner (ou cria novo)
learner = get_or_create_learner(session)

# Armazena episódio
learner.add_episode(
    input_text=text,
    input_struct=meta.struct_node,
    output_text=outcome.answer,
    output_struct=outcome.isr.answer,
    relations=outcome.isr.relations,
    context=outcome.isr.context,
    quality=outcome.quality,
)

# Periodicamente, extrai padrões e aprende regras
if len(learner.episodes) % 100 == 0:
    patterns = learner.extract_patterns()
    new_rules = learner.learn_rules_from_patterns(patterns)
    # Adiciona regras ao session
    session.kb_rules = tuple(list(session.kb_rules) + new_rules)
```

## Comparação: Sem Pesos vs LLM

### Capacidades Esperadas

| Tarefa | LLM (com pesos) | Sistema Sem Pesos | Status |
|--------|----------------|-------------------|--------|
| **Compreensão básica** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ✅ Implementável |
| **Geração de texto** | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⚠️ Limitado |
| **Raciocínio lógico** | ⭐⭐⭐ | ⭐⭐⭐⭐ | ✅ Superior |
| **Memória explícita** | ⭐ | ⭐⭐⭐⭐⭐ | ✅ Superior |
| **Interpretabilidade** | ⭐ | ⭐⭐⭐⭐⭐ | ✅ Superior |
| **Aprendizado contínuo** | ⭐⭐ | ⭐⭐⭐⭐⭐ | ✅ Superior |
| **Escalabilidade** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⚠️ Requer otimização |

### Limitações do Sistema Sem Pesos

1. **Generalização Contínua**
   - LLMs: Interpolam suavemente entre conceitos
   - Sem Pesos: Discreto, precisa de regras explícitas
   - **Solução**: Hierarquias de abstração multi-nível

2. **Nuances de Linguagem**
   - LLMs: Capturam sutilezas implícitas
   - Sem Pesos: Precisa padrões explícitos
   - **Solução**: Padrões multi-nível + contexto rico

3. **Criatividade**
   - LLMs: Podem gerar texto criativo
   - Sem Pesos: Limitado a combinações de padrões
   - **Solução**: Sistema de recombinação de padrões

## Próximos Passos

### Fase 1: Escalabilidade (Atual)
- [x] Sistema base de aprendizado
- [x] Compressão de padrões
- [ ] Índices eficientes para busca
- [ ] Persistência de episódios

### Fase 2: Generalização Avançada
- [ ] Alinhamento estrutural multi-nível
- [ ] Hierarquias de abstração
- [ ] Sistema de variáveis inteligente

### Fase 3: Integração Completa
- [ ] Integração com `runtime.py`
- [ ] Aprendizado contínuo em background
- [ ] Sistema de avaliação de regras

### Fase 4: Otimizações
- [ ] Compressão agressiva de memória
- [ ] Cache inteligente
- [ ] Paralelização

## Conclusão

**É possível** criar um sistema de aprendizado poderoso sem pesos, mas:

✅ **Vantagens**:
- Totalmente interpretável
- Aprendizado contínuo sem retreinamento
- Memória explícita e auditável
- Controle determinístico

⚠️ **Desafios**:
- Requer memória massiva
- Busca pode ser lenta
- Generalização menos suave que LLMs

🎯 **Resultado Esperado**:
- **Não** alcançará exatamente o mesmo nível de LLMs em geração de texto
- **Pode** ser superior em raciocínio lógico e interpretabilidade
- **Será** complementar: melhor para tarefas que exigem controle e auditoria

O sistema atual já tem as bases. Falta escalar, otimizar e integrar completamente.
