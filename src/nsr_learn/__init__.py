"""
NSR-Learn: Aprendizado de Máquina Simbólico Sem Pesos Neurais.

Este módulo implementa uma arquitetura experimental de aprendizado que NÃO usa:
- Redes neurais
- Backpropagation  
- Matrizes de pesos contínuos
- Gradientes

Em vez disso, usa:
- Compressão MDL (Minimum Description Length)
- Grafos de co-ocorrência discretos
- Indução de regras simbólicas
- Memória associativa discreta
- Raciocínio por analogia estrutural
- Cadeia de raciocínio simbólica (Chain of Thought)
- Abstração hierárquica
- Atenção simbólica multi-head
- Geração de texto via composição

A hipótese fundamental: Inteligência = Compressão (Kolmogorov/Solomonoff)
Se conseguimos comprimir bem os dados, conseguimos "entendê-los".

Arquitetura:
                    ┌─────────────────────────────────────┐
                    │     Advanced Learning Engine        │
                    │  (Orquestra todos os componentes)   │
                    └──────────────────┬──────────────────┘
                                       │
         ┌─────────┬─────────┬─────────┼─────────┬─────────┬─────────┐
         ▼         ▼         ▼         ▼         ▼         ▼         ▼
    ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐
    │ MDL     │ │Co-occur │ │ Rule    │ │Assoc.  │ │Analogy │ │Chain of│
    │Compress │ │ Graph   │ │Inductor │ │Memory  │ │Engine  │ │Thought │
    └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘
         │           │           │           │           │           │
         └───────────┴───────────┴─────┬─────┴───────────┴───────────┘
                                       │
         ┌─────────┬─────────┬─────────┼─────────┬─────────┐
         ▼         ▼         ▼         ▼         ▼         ▼
    ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐
    │Taxonomy │ │Pattern  │ │Concept  │ │Symbolic │ │Text    │
    │         │ │Abstract │ │Composer │ │Attention│ │Generate│
    └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘

Autor: NSR-Learn Team
Licença: MIT
"""

# Core components (original)
from .compressor import MDLCompressor, CompressionResult
from .graph import CooccurrenceGraph, GraphNode, GraphEdge
from .inductor import RuleInductor, SymbolicRule, RuleSet
from .memory import AssociativeMemory, MemoryTrace, RetrievalResult
from .engine import LearningEngine, LearningConfig, LearningState

# Advanced: Analogy
from .analogy import (
    Relation,
    Structure, 
    StructuralMapping,
    Analogy,
    AnalogyEngine,
    SOLAR_SYSTEM,
    ATOM,
    TEACHER_STUDENT,
    DOCTOR_PATIENT,
)

# Advanced: Reasoning (Chain of Thought)
from .reasoning import (
    StepType,
    ReasoningStep,
    ReasoningChain,
    KnowledgeBase,
    ChainOfThoughtEngine,
    ReasoningIterator,
    create_example_kb,
)

# Advanced: Abstraction
from .abstraction import (
    RelationType,
    Concept,
    HierarchicalRelation,
    ConceptNode,
    Taxonomy,
    PatternAbstractor,
    ConceptComposer,
    create_default_taxonomy,
)

# Advanced: Attention
from .attention import (
    AttentionFactor,
    AttentionScore,
    AttentionContext,
    SalienceComputer,
    RelevanceComputer,
    SurpriseComputer,
    SymbolicAttention,
    AttentionHead,
    MultiHeadSymbolicAttention,
)

# Advanced: Generation
from .generator import (
    FragmentType,
    TextFragment,
    TextPlan,
    Template,
    MarkovComposer,
    FragmentLibrary,
    TextGenerator,
    DialogueGenerator,
    create_default_generator,
)

# Advanced: Integrated Engine
from .advanced_engine import (
    ProcessingMode,
    AdvancedConfig,
    ProcessingResult,
    AdvancedLearningEngine,
    create_demo_engine,
)

__version__ = "0.2.0"

__all__ = [
    # Version
    "__version__",
    
    # === CORE COMPONENTS ===
    
    # Compressor
    "MDLCompressor",
    "CompressionResult",
    
    # Graph
    "CooccurrenceGraph", 
    "GraphNode",
    "GraphEdge",
    
    # Inductor
    "RuleInductor",
    "SymbolicRule",
    "RuleSet",
    
    # Memory
    "AssociativeMemory",
    "MemoryTrace",
    "RetrievalResult",
    
    # Engine (basic)
    "LearningEngine",
    "LearningConfig",
    "LearningState",
    
    # === ADVANCED COMPONENTS ===
    
    # Analogy
    "Relation",
    "Structure",
    "StructuralMapping",
    "Analogy",
    "AnalogyEngine",
    "SOLAR_SYSTEM",
    "ATOM",
    "TEACHER_STUDENT",
    "DOCTOR_PATIENT",
    
    # Reasoning
    "StepType",
    "ReasoningStep",
    "ReasoningChain",
    "KnowledgeBase",
    "ChainOfThoughtEngine",
    "ReasoningIterator",
    "create_example_kb",
    
    # Abstraction
    "RelationType",
    "Concept",
    "HierarchicalRelation",
    "ConceptNode",
    "Taxonomy",
    "PatternAbstractor",
    "ConceptComposer",
    "create_default_taxonomy",
    
    # Attention
    "AttentionFactor",
    "AttentionScore",
    "AttentionContext",
    "SalienceComputer",
    "RelevanceComputer",
    "SurpriseComputer",
    "SymbolicAttention",
    "AttentionHead",
    "MultiHeadSymbolicAttention",
    
    # Generation
    "FragmentType",
    "TextFragment",
    "TextPlan",
    "Template",
    "MarkovComposer",
    "FragmentLibrary",
    "TextGenerator",
    "DialogueGenerator",
    "create_default_generator",
    
    # Advanced Engine
    "ProcessingMode",
    "AdvancedConfig",
    "ProcessingResult",
    "AdvancedLearningEngine",
    "create_demo_engine",
]
