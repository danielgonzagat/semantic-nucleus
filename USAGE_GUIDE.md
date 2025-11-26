# 🚀 Como Usar o Metanúcleo - IA Sem Pesos

## Início Rápido

### Instalação

```bash
# Clone o repositório
cd /home/runner/work/metanucleus/metanucleus

# Instale as dependências
pip install -e .[dev]

# Execute os testes para verificar
python -m pytest
```

### Uso Básico

```python
from nsr import run_text_full, SessionCtx

# Crie uma sessão (mantém memória entre execuções)
session = SessionCtx()

# Processe texto em linguagem natural
result = run_text_full('O carro tem rodas', session)
print(result.answer)  # "Rodas carro. Relações: carro has rodas."
print(result.quality) # 0.63
```

## Exemplos por Categoria

### 1. Linguagem Natural

```python
from nsr import run_text_full, SessionCtx

session = SessionCtx()

# Português
result = run_text_full('O cachorro late', session)
print(result.answer)

# Inglês (detecção automática)
result = run_text_full('The dog barks', session)
print(result.answer)

# Espanhol
result = run_text_full('El perro ladra', session)
print(result.answer)
```

### 2. Matemática Determinística

```python
from nsr import run_text_full, SessionCtx

session = SessionCtx()

# Operações básicas
result = run_text_full('5 + 3', session)
print(result.answer)  # "8"

result = run_text_full('10 * 2', session)
print(result.answer)  # "20"

result = run_text_full('100 - 25', session)
print(result.answer)  # "75"
```

### 3. Instintos Linguísticos (IAN)

```python
from nsr import run_text_full, SessionCtx

session = SessionCtx()

# Cumprimentos
result = run_text_full('olá', session)
print(result.answer)  # "oi"

result = run_text_full('hello', session)
print(result.answer)  # "hi"

# Perguntas de saúde
result = run_text_full('como você está?', session)
print(result.answer)  # "bem, obrigado"
```

### 4. Aprendizado Automático

```python
from nsr import run_text_full, SessionCtx

session = SessionCtx()

# O sistema aprende automaticamente a cada execução
for i in range(10):
    result = run_text_full(f'Exemplo {i}', session)
    
# Verifique o aprendizado
if session.weightless_learner:
    print(f"Episódios: {len(session.weightless_learner.episodes)}")
    print(f"Padrões: {len(session.weightless_learner.patterns)}")
    print(f"Regras: {len(session.weightless_learner.learned_rules)}")
```

### 5. Lógica Proposicional

```python
from nsr import run_text_full, SessionCtx

session = SessionCtx()

# Adicione fatos
result = run_text_full('Fact chuva', session)

# Adicione regras
result = run_text_full('Se chuva então nublado', session)

# Faça consultas
result = run_text_full('Query nublado', session)
print(result.answer)  # Sistema infere que está nublado
```

### 6. Análise de Código

```python
from nsr import run_text_full, SessionCtx

session = SessionCtx()

# Python
code = '''
def soma(a, b):
    return a + b
'''
result = run_text_full(code, session)
# Sistema analisa e extrai estrutura do código
```

## Recursos Avançados

### Configuração da Sessão

```python
from nsr import SessionCtx
from nsr.state import Config

# Configure parâmetros
config = Config(
    max_steps=64,           # Máximo de passos Φ
    min_quality=0.6,        # Qualidade mínima
    enable_contradiction_check=True,  # Verifica contradições
)

session = SessionCtx(config=config)
```

### Aprendizado Personalizado

```python
from nsr.weightless_learning import WeightlessLearner

# Configure o learner
learner = WeightlessLearner(
    min_pattern_support=3,    # Mínimo de episódios para padrão
    min_confidence=0.7,       # Confiança mínima
    auto_learn_interval=100,  # Aprende a cada 100 episódios
)

session = SessionCtx()
session.weightless_learner = learner
```

### Memória e Persistência

```python
from nsr import run_text_full, SessionCtx

session = SessionCtx()

# Execute múltiplas consultas (memória é mantida)
texts = [
    'O cachorro late',
    'O cachorro é amigável',
    'O gato mia',
]

for text in texts:
    result = run_text_full(text, session)
    print(f"{text} → {result.answer}")

# O sistema lembra das relações anteriores
```

## Análise Detalhada

### Inspecionando Resultados

```python
from nsr import run_text_full, SessionCtx

session = SessionCtx()
result = run_text_full('O elefante é grande', session)

# Resposta
print("Resposta:", result.answer)

# Qualidade (0-1)
print("Qualidade:", result.quality)

# Razão de parada
print("Halt Reason:", result.halt_reason)

# Traço de execução
print("Trace:", result.trace.steps)

# Meta-informações
if result.meta_summary:
    print("Rota:", result.meta_summary.get('meta_route'))
    print("Idioma:", result.meta_summary.get('language'))
```

### Estatísticas do Sistema

```python
from nsr import run_text_full, SessionCtx

session = SessionCtx()

# Execute algumas consultas
for i in range(20):
    run_text_full(f'Teste {i}', session)

# Estatísticas de aprendizado
if session.weightless_learner:
    learner = session.weightless_learner
    
    print(f"Total de episódios: {len(learner.episodes)}")
    print(f"Padrões extraídos: {len(learner.patterns)}")
    print(f"Regras aprendidas: {len(learner.learned_rules)}")
    
    # Busque episódios similares
    from liu import struct, entity
    query = struct(subject=entity("teste"))
    similar = learner.find_similar_episodes(query, k=5)
    print(f"Episódios similares: {len(similar)}")
```

## CLI (Linha de Comando)

### Executar Consultas

```bash
# Consulta simples
python -m nsr.cli "O carro tem rodas"

# Com formato específico
python -m nsr.cli "2+2" --format json

# Com estatísticas
python -m nsr.cli "teste" --include-stats

# Com relatório completo
python -m nsr.cli "teste" --include-report
```

### Chat Interativo

```bash
# Inicie um chat multi-turno
metanucleus-chat

# Comandos especiais no chat:
# /state - Mostra estado atual
# /debug - Informações de debug
# /sair - Encerra o chat
```

## Testes

### Executar Testes

```bash
# Todos os testes
python -m pytest

# Testes específicos
python -m pytest tests/nsr/test_weightless_learning.py

# Com verbose
python -m pytest -xvs

# Com cobertura
coverage run -m pytest && coverage report
```

## Troubleshooting

### Problema: Sistema não encontra episódios similares

**Solução:** Certifique-se de que há episódios suficientes com qualidade > 0.5

```python
# Verifique os episódios
if session.weightless_learner:
    print(len(session.weightless_learner.episodes))
```

### Problema: Qualidade baixa nas respostas

**Solução:** Ajuste os parâmetros do Config

```python
config = Config(min_quality=0.4)  # Reduz limite mínimo
session = SessionCtx(config=config)
```

### Problema: Memória crescendo muito

**Solução:** Configure limites de histórico

```python
config = Config(meta_history_limit=32)
session = SessionCtx(config=config)
```

## Performance

### Otimizações

```python
from nsr import SessionCtx
from nsr.weightless_learning import WeightlessLearner

# Configure para menos armazenamento
learner = WeightlessLearner(
    max_patterns=1000,         # Limite de padrões
    auto_learn_interval=1000,  # Aprende menos frequentemente
)

session = SessionCtx()
session.weightless_learner = learner
```

## Conclusão

O Metanúcleo é uma **IA completa sem pesos ou redes neurais**, oferecendo:

- ✅ Processamento de linguagem natural
- ✅ Raciocínio simbólico determinístico
- ✅ Aprendizado contínuo automático
- ✅ Auditabilidade completa
- ✅ Multi-idioma
- ✅ Sem caixa-preta

Para mais informações, consulte:
- `README.md` - Visão geral completa
- `IMPROVEMENTS.md` - Melhorias implementadas
- `docs/` - Documentação detalhada
