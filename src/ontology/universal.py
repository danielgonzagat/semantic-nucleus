"""
Universal Ontology v1.0 (categorias 1–110)
------------------------------------------

Representação simbólica determinística solicitada para o Metanúcleo. Os dados
abaixo descrevem 110 domínios universais, cada um com ao menos três conceitos
núcleo. O builder converte o catálogo em domínios LIU com relações auditáveis.
"""

from __future__ import annotations

from typing import Dict, List, Sequence, Tuple, Union

from liu import Node, entity, relation, text

ConceptSeed = Union[str, Dict[str, object]]


def _concept(
    name: str,
    *,
    aliases: Sequence[str] | None = None,
    isa: Sequence[str] | None = None,
    part_of: Sequence[str] | None = None,
    attributes: Sequence[str] | None = None,
    examples_pt: Sequence[str] | None = None,
    examples_en: Sequence[str] | None = None,
) -> Dict[str, object]:
    return {
        "name": name,
        "aliases": list(aliases or []),
        "isa": list(isa or []),
        "part_of": list(part_of or []),
        "attributes": list(attributes or []),
        "examples": {
            "pt": list(examples_pt or []),
            "en": list(examples_en or []),
        },
    }


def _concept_names(*names: str) -> List[str]:
    return list(names)


def _normalize_concept(seed: ConceptSeed) -> Dict[str, object]:
    if isinstance(seed, str):
        alias = seed.replace("_", " ")
        sample_pt = f"exemplo de {seed}"
        sample_en = f"example of {seed}"
        return _concept(seed, aliases=[alias], examples_pt=[sample_pt], examples_en=[sample_en])
    data = dict(seed)
    name = data.pop("name")
    return _concept(name, **data)


def _category(idx: int, label: str, concepts: Sequence[ConceptSeed]) -> Dict[str, object]:
    normalized = [_normalize_concept(concept) for concept in concepts]
    return {"category": f"{idx:03d}_{label}", "concepts": normalized}


CATEGORY_SEEDS: List[Dict[str, object]] = [
    {
        "idx": 1,
        "label": "existence",
        "concepts": [
            {
                "name": "coisa",
                "aliases": ["entidade", "objeto"],
                "examples_pt": ["isso é uma coisa"],
                "examples_en": ["this is a thing"],
            },
            {
                "name": "ser",
                "aliases": ["existente"],
                "isa": ["coisa"],
                "examples_pt": ["ser vivo"],
                "examples_en": ["living being"],
            },
            {
                "name": "evento",
                "aliases": ["acontecimento"],
                "examples_pt": ["o evento ocorreu"],
                "examples_en": ["the event happened"],
            },
        ],
    },
    {
        "idx": 2,
        "label": "people",
        "concepts": [
            {
                "name": "pessoa",
                "aliases": ["indivíduo"],
                "attributes": ["nome", "idade"],
                "examples_pt": ["a pessoa falou"],
                "examples_en": ["the person spoke"],
            },
            {"name": "trabalhador", "isa": ["pessoa"], "examples_pt": ["trabalhador motivado"], "examples_en": ["motivated worker"]},
            {"name": "criança", "isa": ["pessoa"], "examples_pt": ["criança curiosa"], "examples_en": ["curious child"]},
        ],
    },
    {
        "idx": 3,
        "label": "objects",
        "concepts": [
            {"name": "objeto", "aliases": ["item"], "examples_pt": ["objeto físico"], "examples_en": ["physical object"]},
            {"name": "dispositivo", "isa": ["objeto"], "examples_pt": ["dispositivo digital"], "examples_en": ["digital device"]},
            {"name": "ferramenta", "isa": ["objeto"], "examples_pt": ["ferramenta de precisão"], "examples_en": ["precision tool"]},
        ],
    },
    {
        "idx": 4,
        "label": "actions",
        "concepts": [
            {"name": "acao", "aliases": ["ato"], "attributes": ["agente", "alvo"], "examples_pt": ["ação precisa"], "examples_en": ["precise action"]},
            {"name": "movimento", "isa": ["acao"], "examples_pt": ["movimento contínuo"], "examples_en": ["continuous movement"]},
            {"name": "comunicar", "isa": ["acao"], "examples_pt": ["comunicar decisão"], "examples_en": ["communicate decision"]},
        ],
    },
    {
        "idx": 5,
        "label": "places",
        "concepts": [
            {"name": "lugar", "aliases": ["local"], "attributes": ["coordenada"], "examples_pt": ["lugar exato"], "examples_en": ["exact place"]},
            {"name": "cidade", "isa": ["lugar"], "examples_pt": ["cidade densa"], "examples_en": ["dense city"]},
            {"name": "ambiente_virtual", "isa": ["lugar"], "examples_pt": ["ambiente virtual imersivo"], "examples_en": ["immersive virtual environment"]},
        ],
    },
    {
        "idx": 6,
        "label": "time",
        "concepts": [
            {"name": "tempo", "aliases": ["cronologia"], "attributes": ["instante", "duracao"], "examples_pt": ["tempo passou"], "examples_en": ["time passed"]},
            {"name": "passado", "isa": ["tempo"], "examples_pt": ["passado recente"], "examples_en": ["recent past"]},
            {"name": "futuro", "isa": ["tempo"], "examples_pt": ["planejar futuro"], "examples_en": ["plan future"]},
        ],
    },
    {
        "idx": 7,
        "label": "affect",
        "concepts": [
            {"name": "emocao", "aliases": ["afeto"], "attributes": ["valencia", "intensidade"], "examples_pt": ["emoção intensa"], "examples_en": ["intense emotion"]},
            {"name": "alegria", "isa": ["emocao"], "examples_pt": ["alegria coletiva"], "examples_en": ["collective joy"]},
            {"name": "medo", "isa": ["emocao"], "examples_pt": ["medo súbito"], "examples_en": ["sudden fear"]},
        ],
    },
    {
        "idx": 8,
        "label": "properties",
        "concepts": [
            {"name": "propriedade", "aliases": ["atributo"], "examples_pt": ["propriedade mensurável"], "examples_en": ["measurable property"]},
            {"name": "cor", "isa": ["propriedade"], "examples_pt": ["cor azul"], "examples_en": ["blue color"]},
            {"name": "tamanho", "isa": ["propriedade"], "examples_pt": ["tamanho relativo"], "examples_en": ["relative size"]},
        ],
    },
    {
        "idx": 9,
        "label": "physics",
        "concepts": [
            {"name": "particula", "isa": ["objeto"], "examples_pt": ["partícula subatômica"], "examples_en": ["subatomic particle"]},
            {"name": "forca_fisica", "aliases": ["interacao"], "examples_pt": ["força gravitacional"], "examples_en": ["gravitational force"]},
            {"name": "energia", "examples_pt": ["energia potencial"], "examples_en": ["potential energy"]},
        ],
    },
    {
        "idx": 10,
        "label": "mind",
        "concepts": [
            {"name": "mente", "aliases": ["cognicao"], "attributes": ["estado"], "examples_pt": ["mente focada"], "examples_en": ["focused mind"]},
            {"name": "pensamento", "isa": ["processo_mental"], "examples_pt": ["pensamento analítico"], "examples_en": ["analytical thought"]},
            {"name": "memoria", "isa": ["processo_mental"], "examples_pt": ["memória episódica"], "examples_en": ["episodic memory"]},
        ],
    },
    # CATEGORIAS 11–40 (detalhes resumidos)
    {"idx": 11, "label": "relations", "concepts": _concept_names("relacao", "hierarquia", "similaridade")},
    {"idx": 12, "label": "quantities", "concepts": _concept_names("quantidade", "proporcao", "probabilidade")},
    {"idx": 13, "label": "social_affect", "concepts": _concept_names("empatia", "confianca", "respeito")},
    {"idx": 14, "label": "social_relations", "concepts": _concept_names("comunidade", "grupo", "rede_social")},
    {"idx": 15, "label": "social_actions", "concepts": _concept_names("cooperar", "negociar", "mediacao")},
    {"idx": 16, "label": "logic", "concepts": _concept_names("proposicao", "inferenca", "contradicao")},
    {"idx": 17, "label": "computing", "concepts": _concept_names("algoritmo", "dado", "estrutura_de_dados")},
    {"idx": 18, "label": "abstracts", "concepts": _concept_names("conceito", "categoria", "metafora")},
    {"idx": 19, "label": "communication", "concepts": _concept_names("mensagem", "canal", "protocolo")},
    {"idx": 20, "label": "intents", "concepts": _concept_names("objetivo", "intencao", "plano")},
    {"idx": 21, "label": "causality", "concepts": _concept_names("causa", "efeito", "feedback")},
    {"idx": 22, "label": "mathematics", "concepts": _concept_names("funcao", "teorema", "estrutura_algebrica")},
    {"idx": 23, "label": "extended_physics", "concepts": _concept_names("campo", "onda", "sistema_fisico")},
    {"idx": 24, "label": "natural_processes", "concepts": _concept_names("ecossistema", "ciclo", "evolucao")},
    {"idx": 25, "label": "society", "concepts": _concept_names("instituicao", "mercado", "cultura")},
    {"idx": 26, "label": "advanced_computing", "concepts": _concept_names("meta_linguagem", "bytecode", "pipeline")},
    {"idx": 27, "label": "textual", "concepts": _concept_names("documento", "frase", "paragrafo")},
    {"idx": 28, "label": "economy", "concepts": _concept_names("ativo", "transacao", "orcamento")},
    {"idx": 29, "label": "software_tech", "concepts": _concept_names("servico", "componente", "observabilidade")},
    {"idx": 30, "label": "metacognition", "concepts": _concept_names("auto_reflexao", "monitoramento", "meta_memoria")},
    {"idx": 31, "label": "narrative", "concepts": _concept_names("historia", "personagem", "conflito")},
    {"idx": 32, "label": "epistemology", "concepts": _concept_names("conhecimento", "justificacao", "crenca")},
    {"idx": 33, "label": "science", "concepts": _concept_names("metodo_cientifico", "experimento", "publicacao")},
    {"idx": 34, "label": "engineering", "concepts": _concept_names("projeto", "prototipo", "validacao")},
    {"idx": 35, "label": "metalanguage", "concepts": _concept_names("liu", "arena_imutavel", "serializacao")},
    {"idx": 36, "label": "meta_logic", "concepts": _concept_names("phi_operador", "regra_formal", "traco_auditavel")},
    {"idx": 37, "label": "cognitive_mind", "concepts": _concept_names("instinto_estrutural", "foco", "insight_formal")},
    {"idx": 38, "label": "meta_calculus", "concepts": _concept_names("meta_representacao", "meta_calculo", "meta_expressao")},
    {"idx": 39, "label": "modality", "concepts": _concept_names("necessidade", "possibilidade", "contingencia")},
    {"idx": 40, "label": "goal_models", "concepts": _concept_names("objetivo_superior", "submeta", "criterio_sucesso")},
    # CATEGORIAS 41–110
    {"idx": 41, "label": "ethics", "concepts": _concept_names("etica", "responsabilidade", "dilema_moral")},
    {"idx": 42, "label": "norms", "concepts": _concept_names("norma", "compliance", "sancao")},
    {"idx": 43, "label": "games", "concepts": _concept_names("jogo", "estrategia_ludica", "pontuacao")},
    {"idx": 44, "label": "complex_affect", "concepts": _concept_names("ambivalencia", "nostalgia", "orgulho")},
    {"idx": 45, "label": "motivation", "concepts": _concept_names("motivacao", "recompensa", "persistencia")},
    {"idx": 46, "label": "planning", "concepts": _concept_names("planejamento", "cronograma", "contingencia")},
    {"idx": 47, "label": "art", "concepts": _concept_names("arte", "linguagem_visual", "composicao")},
    {"idx": 48, "label": "social_phenomena", "concepts": _concept_names("tendencia", "movimento_social", "ritual")},
    {"idx": 49, "label": "meta_explanation", "concepts": _concept_names("meta_explicacao", "camada_contextual", "traco_explicativo")},
    {"idx": 50, "label": "self_reference", "concepts": _concept_names("auto_referencia", "metalinguagem_propria", "loop_reflexivo")},
    {"idx": 51, "label": "systems", "concepts": _concept_names("sistema", "subsistema", "interface")},
    {"idx": 52, "label": "processing", "concepts": _concept_names("processamento", "fluxo_de_dados", "buffer")},
    {"idx": 53, "label": "control", "concepts": _concept_names("controle", "sinal_de_erro", "atuador")},
    {"idx": 54, "label": "abstraction", "concepts": _concept_names("abstracao", "camada", "instanciacao")},
    {"idx": 55, "label": "internal_states", "concepts": _concept_names("estado_interno", "tensao_psicologica", "homeostase")},
    {"idx": 56, "label": "environment", "concepts": _concept_names("ambiente", "contexto", "ecologia_urbana")},
    {"idx": 57, "label": "interaction", "concepts": _concept_names("interacao", "turno", "feedback_social")},
    {"idx": 58, "label": "symbolic_autonomy", "concepts": _concept_names("autonomia_simbolica", "auto_execucao", "criterio_guardiao")},
    {"idx": 59, "label": "mental_models", "concepts": _concept_names("modelo_mental", "simulacao_interna", "hipotese")},
    {"idx": 60, "label": "tasks", "concepts": _concept_names("tarefa", "workflow", "checklist")},
    {"idx": 61, "label": "law", "concepts": _concept_names("lei", "processo_judicial", "precedente")},
    {"idx": 62, "label": "negotiation", "concepts": _concept_names("proposta", "concessao", "acordo")},
    {"idx": 63, "label": "project_management", "concepts": _concept_names("escopo", "entrega", "risco")},
    {"idx": 64, "label": "advanced_economy", "concepts": _concept_names("derivativo", "hedge", "indice_macro")},
    {"idx": 65, "label": "world_models", "concepts": _concept_names("modelo_mundo", "cenario", "simulacao_global")},
    {"idx": 66, "label": "conversation_states", "concepts": _concept_names("turno_dialogo", "contexto_discursivo", "intencao_implicita")},
    {"idx": 67, "label": "social_roles", "concepts": _concept_names("papel_social", "lider", "mediador")},
    {"idx": 68, "label": "structural_autonomy", "concepts": _concept_names("agente_autonomo", "limite_operacional", "autenticacao")},
    {"idx": 69, "label": "coordination", "concepts": _concept_names("sincronizacao", "protocolo_coordenacao", "janela_temporal")},
    {"idx": 70, "label": "consistency", "concepts": _concept_names("consistencia", "invariante", "prova_consistencia")},
    {"idx": 71, "label": "reasoning_chains", "concepts": _concept_names("cadeia_inferencia", "premissa", "conclusao_parcial")},
    {"idx": 72, "label": "deep_intention", "concepts": _concept_names("intencao_profunda", "motivo_raiz", "compromisso")},
    {"idx": 73, "label": "assumptions", "concepts": _concept_names("pressuposicao", "hipotese_base", "escopo_validade")},
    {"idx": 74, "label": "explanation", "concepts": _concept_names("explicacao", "justificativa", "contrafactual")},
    {"idx": 75, "label": "advanced_narrative", "concepts": _concept_names("meta_enredo", "linha_do_tempo_narrativa", "ponto_de_vista")},
    {"idx": 76, "label": "argumentation", "concepts": _concept_names("argumento", "contraargumento", "debate_formal")},
    {"idx": 77, "label": "strategy", "concepts": _concept_names("estrategia", "tatica", "manobra")},
    {"idx": 78, "label": "symbolic_self", "concepts": _concept_names("identidade_simbolica", "memoria_procedural", "auto_descricao_formal")},
    {"idx": 79, "label": "alignment", "concepts": _concept_names("alinhamento", "restricao_de_valor", "auditoria_moral")},
    {"idx": 80, "label": "decision", "concepts": _concept_names("decisao", "criterio", "arvore_decisao")},
    {"idx": 81, "label": "complex_systems", "concepts": _concept_names("sistema_complexo", "retroacao", "emergencia")},
    {"idx": 82, "label": "modeling", "concepts": _concept_names("modelagem", "parametrizacao", "ajuste")},
    {"idx": 83, "label": "space", "concepts": _concept_names("coordenada", "trajetoria", "orbita")},
    {"idx": 84, "label": "advanced_time", "concepts": _concept_names("linha_temporal", "janela_temporal", "latencia")},
    {"idx": 85, "label": "philosophy", "concepts": _concept_names("ontologia", "axiologia", "epistemologia")},
    {"idx": 86, "label": "instructions", "concepts": _concept_names("instrucao", "procedimento", "manual")},
    {"idx": 87, "label": "translation", "concepts": _concept_names("traducao", "equivalencia", "mapa_semantico")},
    {"idx": 88, "label": "structural_conflict", "concepts": _concept_names("conflito_estrutural", "tradeoff", "resolucao")},
    {"idx": 89, "label": "conceptual_abstraction", "concepts": _concept_names("macroconceito", "stack_semantico", "metafora_estrutural")},
    {"idx": 90, "label": "categorization", "concepts": _concept_names("classificacao", "taxonomia", "esquema")},
    {"idx": 91, "label": "complex_actions", "concepts": _concept_names("macro_acao", "sequencia_coreografada", "operacao_composta")},
    {"idx": 92, "label": "multiagent", "concepts": _concept_names("sistema_multiagente", "coordenacao_distribuida", "protocolo_social")},
    {"idx": 93, "label": "goal_driven", "concepts": _concept_names("plano_dirigido", "alocacao_recursos", "verificacao_objetivo")},
    {"idx": 94, "label": "logical_mechanisms", "concepts": _concept_names("mecanismo_logico", "gatilho", "constraint_logic")},
    {"idx": 95, "label": "meta_states", "concepts": _concept_names("estado_meta", "observador_meta", "contexto_meta")},
    {"idx": 96, "label": "technical_intelligence", "concepts": _concept_names("engenho_tecnico", "aprendizagem_simbolica", "diagnostico_tecnico")},
    {"idx": 97, "label": "computational_representation", "concepts": _concept_names("grafo", "tensor", "formato_ir")},
    {"idx": 98, "label": "linguistic_intelligence", "concepts": _concept_names("gramatica", "pragmatica", "ato_de_fala")},
    {"idx": 99, "label": "action_models", "concepts": _concept_names("modelo_de_acao", "pre_condicao", "efeito_planejado")},
    {"idx": 100, "label": "resilience", "concepts": _concept_names("resiliencia", "redundancia", "recuperacao")},
    {"idx": 101, "label": "biology_organization", "concepts": _concept_names("celula", "tecido", "orgao")},
    {"idx": 102, "label": "genetics", "concepts": _concept_names("gene", "mutacao", "heranca")},
    {"idx": 103, "label": "ecology", "concepts": _concept_names("cadeia_alimentar", "nicho", "servico_ecossistemico")},
    {"idx": 104, "label": "chemistry_basics", "concepts": _concept_names("atomo", "ligacao_quimica", "molecula")},
    {"idx": 105, "label": "chemical_reactions", "concepts": _concept_names("reacao", "catalisador", "equilibrio_quimico")},
    {"idx": 106, "label": "physics_mechanics", "concepts": _concept_names("massa", "forca", "momento")},
    {"idx": 107, "label": "physics_em", "concepts": _concept_names("campo_eletrico", "campo_magnetico", "onda_em")},
    {"idx": 108, "label": "thermodynamics", "concepts": _concept_names("temperatura", "entalpia", "entropia")},
    {"idx": 109, "label": "astronomy", "concepts": _concept_names("estrela", "galaxia", "orbita_planetaria")},
    {"idx": 110, "label": "geosciences", "concepts": _concept_names("rocha", "tectonica", "clima")},
]

UNIVERSAL_CATEGORIES: List[Dict[str, object]] = [
    _category(seed["idx"], seed["label"], seed["concepts"]) for seed in CATEGORY_SEEDS
]


def build_universal_domain_specs() -> Tuple[Dict[str, object], ...]:
    specs: List[Dict[str, object]] = []
    for category in UNIVERSAL_CATEGORIES:
        cat_name = category["category"]
        relations: List[Node] = []
        keywords: List[str] = []
        domain_entity = entity(cat_name)
        for concept in category["concepts"]:
            concept_name = concept["name"]
            concept_entity = entity(concept_name)
            aliases = concept.get("aliases", [])
            relations.append(relation("IN_CATEGORY", concept_entity, domain_entity))
            keywords.extend([concept_name, *aliases])

            for alias in aliases:
                relations.append(relation("ALIAS", concept_entity, entity(alias)))
            for isa_name in concept.get("isa", []):
                relations.append(relation("IS_A", concept_entity, entity(isa_name)))
            for parent in concept.get("part_of", []):
                relations.append(relation("PART_OF", concept_entity, entity(parent)))
            for attr in concept.get("attributes", []):
                relations.append(relation("HAS_ATTR", concept_entity, entity(attr)))
                keywords.append(attr)

            examples = concept.get("examples", {})
            for sample in examples.get("pt", []):
                relations.append(relation("EXAMPLE_PT", concept_entity, text(sample)))
            for sample in examples.get("en", []):
                relations.append(relation("EXAMPLE_EN", concept_entity, text(sample)))

        spec = {
            "name": f"universal::{cat_name}",
            "version": f"{cat_name}.v1",
            "relations": tuple(relations),
            "keywords": tuple(dict.fromkeys(keyword for keyword in keywords if keyword)),
            "dependencies": tuple(),
        }
        specs.append(spec)
    return tuple(specs)


__all__ = ["UNIVERSAL_CATEGORIES", "build_universal_domain_specs"]
