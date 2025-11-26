"""
NSR-Learn: Aprendizado de Máquina Simbólico Sem Pesos Neurais.

Este módulo implementa uma arquitetura experimental de aprendizado que NÃO usa:
- Redes neurais
- Backpropagation  
- Matrizes de pesos contínuos
- Gradientes

CAPACIDADES IMPLEMENTADAS:

Nível 1 - Fundamentos:
├── Compressão MDL (Minimum Description Length)
├── Grafos de co-ocorrência discretos
├── Indução de regras simbólicas
└── Memória associativa discreta

Nível 2 - Raciocínio:
├── Analogia estrutural (Structure-Mapping)
├── Chain of Thought simbólico
├── Abstração hierárquica (Taxonomias)
└── Atenção simbólica multi-head

Nível 3 - Aprendizado Real:
├── Program Synthesis (aprender programas de exemplos)
├── World Model (simular consequências)
├── Raciocínio Causal (causa-efeito)
├── Meta-Learning (aprender a aprender)
├── Active Learning (decidir o que explorar)
└── Curriculum Learning (do simples ao complexo)

A hipótese fundamental: Inteligência = Compressão (Kolmogorov/Solomonoff)
Se conseguimos comprimir bem os dados, conseguimos "entendê-los".

Autor: NSR-Learn Team
Licença: MIT
"""

# === LEVEL 1: CORE COMPONENTS ===

from .compressor import MDLCompressor, CompressionResult
from .graph import CooccurrenceGraph, GraphNode, GraphEdge
from .inductor import RuleInductor, SymbolicRule, RuleSet, Condition
from .memory import AssociativeMemory, MemoryTrace, RetrievalResult
from .engine import LearningEngine, LearningConfig, LearningState

# === LEVEL 2: REASONING COMPONENTS ===

# Analogy
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

# Reasoning (Chain of Thought)
from .reasoning import (
    StepType,
    ReasoningStep,
    ReasoningChain,
    KnowledgeBase,
    ChainOfThoughtEngine,
    ReasoningIterator,
    create_example_kb,
)

# Abstraction
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

# Attention
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

# Generation
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

# Integrated Engine
from .advanced_engine import (
    ProcessingMode,
    AdvancedConfig,
    ProcessingResult,
    AdvancedLearningEngine,
    create_demo_engine,
)

# === LEVEL 3: REAL LEARNING COMPONENTS ===

# Program Synthesis
from .program_synthesis import (
    OpType,
    Expr,
    Evaluator,
    SynthesisExample,
    SynthesizedProgram,
    ProgramSynthesizer,
    PatternLearner,
    SequencePredictor,
)

# World Model
from .world_model import (
    Fluent,
    State,
    Action,
    TransitionRule,
    Plan,
    WorldModel,
    MentalSimulator,
    create_blocks_world,
)

# Causal Reasoning
from .causal import (
    CausalVariable,
    CausalLink,
    ConditionalProbability,
    CausalGraph,
    Intervention,
    CausalQuery,
    CausalReasoner,
    learn_causal_structure,
)

# Meta-Learning
from .meta_learning import (
    TaskType,
    Task,
    LearningStrategy,
    LearnedModel,
    MemoizationStrategy,
    PatternMatchingStrategy,
    RuleInductionStrategy,
    AnalogyStrategy,
    StrategyPerformance,
    MetaLearner,
)

# Active & Curriculum Learning
from .active_curriculum import (
    QueryStrategy,
    Query,
    LabeledExample,
    UncertaintyEstimator,
    DiversitySampler,
    ActiveLearner,
    DifficultyMetric,
    CurriculumExample,
    LearningStage,
    DifficultyEstimator,
    CurriculumLearner,
    AdaptiveLearner,
)

__version__ = "0.3.0"

__all__ = [
    # Version
    "__version__",
    
    # === LEVEL 1: CORE ===
    
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
    "Condition",
    
    # Memory
    "AssociativeMemory",
    "MemoryTrace",
    "RetrievalResult",
    
    # Engine (basic)
    "LearningEngine",
    "LearningConfig",
    "LearningState",
    
    # === LEVEL 2: REASONING ===
    
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
    
    # === LEVEL 3: REAL LEARNING ===
    
    # Program Synthesis
    "OpType",
    "Expr",
    "Evaluator",
    "SynthesisExample",
    "SynthesizedProgram",
    "ProgramSynthesizer",
    "PatternLearner",
    "SequencePredictor",
    
    # World Model
    "Fluent",
    "State",
    "Action",
    "TransitionRule",
    "Plan",
    "WorldModel",
    "MentalSimulator",
    "create_blocks_world",
    
    # Causal Reasoning
    "CausalVariable",
    "CausalLink",
    "ConditionalProbability",
    "CausalGraph",
    "Intervention",
    "CausalQuery",
    "CausalReasoner",
    "learn_causal_structure",
    
    # Meta-Learning
    "TaskType",
    "Task",
    "LearningStrategy",
    "LearnedModel",
    "MemoizationStrategy",
    "PatternMatchingStrategy",
    "RuleInductionStrategy",
    "AnalogyStrategy",
    "StrategyPerformance",
    "MetaLearner",
    
    # Active & Curriculum Learning
    "QueryStrategy",
    "Query",
    "LabeledExample",
    "UncertaintyEstimator",
    "DiversitySampler",
    "ActiveLearner",
    "DifficultyMetric",
    "CurriculumExample",
    "LearningStage",
    "DifficultyEstimator",
    "CurriculumLearner",
    "AdaptiveLearner",
]
