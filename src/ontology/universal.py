"""
Universal Ontology v1.0 (Parte 1).

Representa categorias determinísticas com conceitos, aliases, relações e exemplos
prontos para alimentar o MultiOntologyManager.
"""

from __future__ import annotations

from typing import Dict, Iterable, List, Sequence, Tuple

from liu import Node, entity, relation, text


UNIVERSAL_ONTOLOGY_V1_PART1: List[Dict[str, object]] = [
    {
        "category": "existence",
        "concepts": [
            {
                "name": "coisa",
                "aliases": ["objeto", "entidade"],
                "isa": [],
                "part_of": [],
                "attributes": [],
                "examples": {
                    "pt": ["isso é uma coisa"],
                    "en": ["this is a thing"],
                },
            },
            {
                "name": "ser",
                "aliases": ["existir", "existência"],
                "isa": [],
                "part_of": [],
                "attributes": [],
                "examples": {
                    "pt": ["um ser vivo"],
                    "en": ["a living being"],
                },
            },
            {
                "name": "evento",
                "aliases": ["ocorrência", "acontecimento"],
                "isa": [],
                "part_of": [],
                "attributes": [],
                "examples": {
                    "pt": ["o evento aconteceu"],
                    "en": ["the event occurred"],
                },
            },
            {
                "name": "estado",
                "aliases": ["condição"],
                "isa": [],
                "part_of": [],
                "attributes": [],
                "examples": {
                    "pt": ["estado atual"],
                    "en": ["current state"],
                },
            },
            {
                "name": "realidade",
                "aliases": ["mundo", "universo"],
                "isa": [],
                "part_of": [],
                "attributes": [],
                "examples": {
                    "pt": ["na realidade..."],
                    "en": ["in reality..."],
                },
            },
            {
                "name": "identidade",
                "aliases": ["essência"],
                "isa": [],
                "part_of": [],
                "attributes": [],
                "examples": {
                    "pt": ["identidade pessoal"],
                    "en": ["personal identity"],
                },
            },
            {
                "name": "propriedade",
                "aliases": ["característica", "atributo"],
                "isa": [],
                "part_of": [],
                "attributes": [],
                "examples": {
                    "pt": ["cor é uma propriedade"],
                    "en": ["color is a property"],
                },
            },
            {
                "name": "tempo",
                "aliases": ["cronologia"],
                "isa": [],
                "part_of": [],
                "attributes": [],
                "examples": {
                    "pt": ["o tempo passou"],
                    "en": ["time passed"],
                },
            },
            {
                "name": "espaço",
                "aliases": ["localização"],
                "isa": [],
                "part_of": [],
                "attributes": [],
                "examples": {
                    "pt": ["o espaço físico"],
                    "en": ["physical space"],
                },
            },
            {
                "name": "mudança",
                "aliases": ["transformação"],
                "isa": [],
                "part_of": [],
                "attributes": [],
                "examples": {
                    "pt": ["a mudança ocorreu"],
                    "en": ["the change occurred"],
                },
            },
        ],
    },
    {
        "category": "people",
        "concepts": [
            {
                "name": "pessoa",
                "aliases": ["indivíduo", "gente"],
                "isa": ["ser"],
                "part_of": [],
                "attributes": ["idade", "nome", "gênero"],
                "examples": {
                    "pt": ["a pessoa falou"],
                    "en": ["the person spoke"],
                },
            },
            {
                "name": "homem",
                "aliases": ["masculino"],
                "isa": ["pessoa"],
                "part_of": [],
                "attributes": [],
                "examples": {
                    "pt": ["o homem saiu"],
                    "en": ["the man left"],
                },
            },
            {
                "name": "mulher",
                "aliases": ["feminino"],
                "isa": ["pessoa"],
                "part_of": [],
                "attributes": [],
                "examples": {
                    "pt": ["a mulher chegou"],
                    "en": ["the woman arrived"],
                },
            },
            {
                "name": "criança",
                "aliases": ["menino", "menina"],
                "isa": ["pessoa"],
                "part_of": [],
                "attributes": [],
                "examples": {
                    "pt": ["a criança correu"],
                    "en": ["the child ran"],
                },
            },
            {
                "name": "trabalhador",
                "aliases": ["funcionário"],
                "isa": ["pessoa"],
                "part_of": [],
                "attributes": [],
                "examples": {
                    "pt": ["o trabalhador ajudou"],
                    "en": ["the worker helped"],
                },
            },
            {
                "name": "cliente",
                "aliases": ["consumidor"],
                "isa": ["pessoa"],
                "part_of": [],
                "attributes": [],
                "examples": {
                    "pt": ["o cliente comprou"],
                    "en": ["the customer bought"],
                },
            },
            {
                "name": "amigo",
                "aliases": ["parceiro"],
                "isa": ["pessoa"],
                "part_of": [],
                "attributes": [],
                "examples": {
                    "pt": ["o amigo ligou"],
                    "en": ["the friend called"],
                },
            },
            {
                "name": "professor",
                "aliases": [],
                "isa": ["pessoa"],
                "part_of": [],
                "attributes": [],
                "examples": {
                    "pt": ["o professor ensinou"],
                    "en": ["the teacher taught"],
                },
            },
            {
                "name": "aluno",
                "aliases": ["estudante"],
                "isa": ["pessoa"],
                "part_of": [],
                "attributes": [],
                "examples": {
                    "pt": ["o aluno estudou"],
                    "en": ["the student studied"],
                },
            },
        ],
    },
    {
        "category": "objects",
        "concepts": [
            {
                "name": "carro",
                "aliases": ["automóvel"],
                "isa": ["veículo"],
                "part_of": ["estrada"],
                "attributes": ["cor", "velocidade"],
                "examples": {
                    "pt": ["o carro andou"],
                    "en": ["the car moved"],
                },
            },
            {
                "name": "moto",
                "aliases": ["motocicleta"],
                "isa": ["veículo"],
                "part_of": [],
                "attributes": [],
                "examples": {
                    "pt": ["a moto passou"],
                    "en": ["the motorcycle passed"],
                },
            },
            {
                "name": "casa",
                "aliases": ["lar"],
                "isa": ["construção"],
                "part_of": ["cidade"],
                "attributes": ["tamanho"],
                "examples": {
                    "pt": ["a casa caiu"],
                    "en": ["the house fell"],
                },
            },
            {
                "name": "porta",
                "aliases": [],
                "isa": ["objeto"],
                "part_of": ["casa"],
                "attributes": ["cor", "material"],
                "examples": {
                    "pt": ["a porta abriu"],
                    "en": ["the door opened"],
                },
            },
            {
                "name": "janela",
                "aliases": [],
                "isa": ["objeto"],
                "part_of": ["casa"],
                "attributes": ["vidro"],
                "examples": {
                    "pt": ["a janela fechou"],
                    "en": ["the window closed"],
                },
            },
            {
                "name": "computador",
                "aliases": ["pc"],
                "isa": ["máquina"],
                "part_of": [],
                "attributes": ["processador", "memória"],
                "examples": {
                    "pt": ["o computador ligou"],
                    "en": ["the computer turned on"],
                },
            },
            {
                "name": "telefone",
                "aliases": ["celular", "smartphone"],
                "isa": ["dispositivo"],
                "part_of": [],
                "attributes": ["bateria"],
                "examples": {
                    "pt": ["o telefone tocou"],
                    "en": ["the phone rang"],
                },
            },
        ],
    },
    {
        "category": "actions",
        "concepts": [
            {
                "name": "andar",
                "aliases": ["caminhar"],
                "isa": ["movimento"],
                "part_of": [],
                "attributes": ["velocidade"],
                "examples": {
                    "pt": ["ele andou"],
                    "en": ["he walked"],
                },
            },
            {
                "name": "correr",
                "aliases": ["disparar"],
                "isa": ["movimento"],
                "part_of": [],
                "attributes": [],
                "examples": {
                    "pt": ["ele correu"],
                    "en": ["he ran"],
                },
            },
            {
                "name": "pular",
                "aliases": ["saltou"],
                "isa": ["movimento"],
                "part_of": [],
                "attributes": [],
                "examples": {
                    "pt": ["ele pulou"],
                    "en": ["he jumped"],
                },
            },
            {
                "name": "falar",
                "aliases": ["dizer"],
                "isa": ["comunicação"],
                "part_of": [],
                "attributes": [],
                "examples": {
                    "pt": ["ela falou"],
                    "en": ["she spoke"],
                },
            },
            {
                "name": "ver",
                "aliases": ["olhar"],
                "isa": ["percepção"],
                "part_of": [],
                "attributes": [],
                "examples": {
                    "pt": ["ele viu"],
                    "en": ["he saw"],
                },
            },
            {
                "name": "pegar",
                "aliases": ["agarrar"],
                "isa": ["ação"],
                "part_of": [],
                "attributes": [],
                "examples": {
                    "pt": ["ele pegou o objeto"],
                    "en": ["he grabbed the object"],
                },
            },
            {
                "name": "bater",
                "aliases": ["colidir"],
                "isa": ["impacto"],
                "part_of": [],
                "attributes": [],
                "examples": {
                    "pt": ["o carro bateu"],
                    "en": ["the car hit"],
                },
            },
        ],
    },
    {
        "category": "places",
        "concepts": [
            {
                "name": "cidade",
                "aliases": [],
                "isa": ["local"],
                "part_of": ["estado"],
                "attributes": ["população"],
                "examples": {
                    "pt": ["a cidade cresceu"],
                    "en": ["the city grew"],
                },
            },
            {
                "name": "rua",
                "aliases": ["avenida"],
                "isa": ["local"],
                "part_of": ["cidade"],
                "attributes": [],
                "examples": {
                    "pt": ["a rua estava vazia"],
                    "en": ["the street was empty"],
                },
            },
            {
                "name": "casa",
                "aliases": ["lar"],
                "isa": ["local"],
                "part_of": ["cidade"],
                "attributes": [],
                "examples": {
                    "pt": ["a casa é branca"],
                    "en": ["the house is white"],
                },
            },
            {
                "name": "escola",
                "aliases": [],
                "isa": ["local"],
                "part_of": ["cidade"],
                "attributes": [],
                "examples": {
                    "pt": ["a escola abriu"],
                    "en": ["the school opened"],
                },
            },
        ],
    },
    {
        "category": "time",
        "concepts": [
            {
                "name": "hoje",
                "aliases": [],
                "isa": ["tempo"],
                "part_of": [],
                "attributes": [],
                "examples": {
                    "pt": ["hoje"],
                    "en": ["today"],
                },
            },
            {
                "name": "amanhã",
                "aliases": [],
                "isa": ["tempo"],
                "part_of": [],
                "attributes": [],
                "examples": {
                    "pt": ["amanhã"],
                    "en": ["tomorrow"],
                },
            },
            {
                "name": "ontem",
                "aliases": [],
                "isa": ["tempo"],
                "part_of": [],
                "attributes": [],
                "examples": {
                    "pt": ["ontem"],
                    "en": ["yesterday"],
                },
            },
            {
                "name": "agora",
                "aliases": [],
                "isa": ["tempo"],
                "part_of": [],
                "attributes": [],
                "examples": {
                    "pt": ["agora mesmo"],
                    "en": ["right now"],
                },
            },
        ],
    },
    {
        "category": "affect",
        "concepts": [
            {
                "name": "feliz",
                "aliases": ["contente"],
                "isa": ["estado"],
                "part_of": [],
                "attributes": [],
                "examples": {
                    "pt": ["ele está feliz"],
                    "en": ["he is happy"],
                },
            },
            {
                "name": "triste",
                "aliases": ["abatido"],
                "isa": ["estado"],
                "part_of": [],
                "attributes": [],
                "examples": {
                    "pt": ["ela está triste"],
                    "en": ["she is sad"],
                },
            },
            {
                "name": "raiva",
                "aliases": ["ira"],
                "isa": ["estado"],
                "part_of": [],
                "attributes": [],
                "examples": {
                    "pt": ["ele sentiu raiva"],
                    "en": ["he felt anger"],
                },
            },
        ],
    },
    {
        "category": "properties",
        "concepts": [
            {
                "name": "cor",
                "aliases": [],
                "isa": ["propriedade"],
                "part_of": [],
                "attributes": [],
                "examples": {
                    "pt": ["a cor vermelha"],
                    "en": ["the red color"],
                },
            },
            {
                "name": "tamanho",
                "aliases": [],
                "isa": ["propriedade"],
                "part_of": [],
                "attributes": [],
                "examples": {
                    "pt": ["o tamanho grande"],
                    "en": ["the large size"],
                },
            },
            {
                "name": "forma",
                "aliases": ["formato"],
                "isa": ["propriedade"],
                "part_of": [],
                "attributes": [],
                "examples": {
                    "pt": ["a forma redonda"],
                    "en": ["the round shape"],
                },
            },
        ],
    },
    {
        "category": "physics",
        "concepts": [
            {
                "name": "força",
                "aliases": ["pressão"],
                "isa": ["quantidade"],
                "part_of": [],
                "attributes": [],
                "examples": {
                    "pt": ["força aplicada"],
                    "en": ["applied force"],
                },
            },
            {
                "name": "velocidade",
                "aliases": [],
                "isa": ["quantidade"],
                "part_of": [],
                "attributes": [],
                "examples": {
                    "pt": ["velocidade alta"],
                    "en": ["high speed"],
                },
            },
            {
                "name": "aceleração",
                "aliases": [],
                "isa": ["quantidade"],
                "part_of": [],
                "attributes": [],
                "examples": {
                    "pt": ["aceleração constante"],
                    "en": ["constant acceleration"],
                },
            },
        ],
    },
    {
        "category": "mind",
        "concepts": [
            {
                "name": "pensar",
                "aliases": ["raciocinar"],
                "isa": ["processo"],
                "part_of": [],
                "attributes": [],
                "examples": {
                    "pt": ["ele pensou"],
                    "en": ["he thought"],
                },
            },
            {
                "name": "saber",
                "aliases": ["entender", "compreender"],
                "isa": ["processo"],
                "part_of": [],
                "attributes": [],
                "examples": {
                    "pt": ["ele soube"],
                    "en": ["he knew"],
                },
            },
            {
                "name": "lembrar",
                "aliases": ["recordar"],
                "isa": ["processo"],
                "part_of": [],
                "attributes": [],
                "examples": {
                    "pt": ["ele lembrou"],
                    "en": ["he remembered"],
                },
            },
            {
                "name": "dúvida",
                "aliases": ["incerteza"],
                "isa": ["estado"],
                "part_of": [],
                "attributes": [],
                "examples": {
                    "pt": ["ele tinha dúvida"],
                    "en": ["he had doubt"],
                },
            },
        ],
    },
]


def build_universal_domain_specs(
    dataset: Sequence[Dict[str, object]] | None = None,
) -> Tuple[Dict[str, object], ...]:
    """
    Produz especificações (name/version/relations/keywords) prontas para domínios.
    """

    source = dataset or UNIVERSAL_ONTOLOGY_V1_PART1
    specs: List[Dict[str, object]] = []
    for entry in source:
        category = str(entry["category"])
        relations: List[Node] = []
        keywords: set[str] = set()
        concepts = entry.get("concepts", [])
        for concept in concepts:
            concept = dict(concept)
            name = concept["name"]
            aliases = _as_list(concept.get("aliases", []))
            isa_list = _as_list(concept.get("isa", []))
            part_of_list = _as_list(concept.get("part_of", []))
            attributes = _as_list(concept.get("attributes", []))
            relations.append(
                relation("IN_CATEGORY", entity(name), entity(f"category::{category}"))
            )
            keywords.add(name)
            keywords.update(aliases)
            for alias in aliases:
                relations.append(relation("HAS_ALIAS", entity(name), entity(alias)))
            for parent in isa_list:
                relations.append(relation("IS_A", entity(name), entity(parent)))
            for parent in part_of_list:
                relations.append(relation("PART_OF", entity(name), entity(parent)))
                relations.append(relation("HAS_PART", entity(parent), entity(name)))
            for attr in attributes:
                relations.append(relation("HAS_ATTRIBUTE", entity(name), entity(attr)))
            examples = concept.get("examples", {}) or {}
            for sentence in _as_list(examples.get("pt", [])):
                relations.append(
                    relation("EXAMPLE_PT", entity(name), text(sentence))
                )
            for sentence in _as_list(examples.get("en", [])):
                relations.append(
                    relation("EXAMPLE_EN", entity(name), text(sentence))
                )
        specs.append(
            {
                "name": f"universal::{category}",
                "version": "universal.v1p1",
                "relations": tuple(relations),
                "keywords": tuple(sorted(keywords)),
            }
        )
    return tuple(specs)


def _as_list(values: Iterable[str] | None) -> List[str]:
    if not values:
        return []
    return [str(value) for value in values if str(value).strip()]


__all__ = [
    "UNIVERSAL_ONTOLOGY_V1_PART1",
    "build_universal_domain_specs",
]
