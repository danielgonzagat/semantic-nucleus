"""
Universal Ontology v1.0 (categorias 1–110)
------------------------------------------

Esta tabela concentra o conhecimento simbólico base do Metanúcleo. Cada
categoria agrega conceitos com aliases, relações hierárquicas (ISA, PART_OF),
atributos e exemplos PT/EN. O builder converte essa descrição em domínios LIU
que podem ser registrados no MultiOntologyManager.
"""

from __future__ import annotations

from typing import Dict, Iterable, List, Sequence, Tuple

from liu import Node, entity, relation, text


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


BASE_CATEGORIES: List[Dict[str, object]] = [
    {
        "category": "existence",
        "concepts": [
            _concept("coisa", aliases=["objeto", "entidade"], examples_pt=["isso é uma coisa"], examples_en=["this is a thing"]),
            _concept("ser", aliases=["existir", "existência"], examples_pt=["um ser vivo"], examples_en=["a living being"]),
            _concept("evento", aliases=["ocorrência", "acontecimento"], examples_pt=["o evento aconteceu"], examples_en=["the event occurred"]),
            _concept("estado", aliases=["condição"], examples_pt=["estado atual"], examples_en=["current state"]),
            _concept("realidade", aliases=["mundo", "universo"], examples_pt=["na realidade..."], examples_en=["in reality..."]),
            _concept("identidade", aliases=["essência"], examples_pt=["identidade pessoal"], examples_en=["personal identity"]),
            _concept("propriedade", aliases=["característica", "atributo"], examples_pt=["cor é uma propriedade"], examples_en=["color is a property"]),
            _concept("tempo", aliases=["cronologia"], examples_pt=["o tempo passou"], examples_en=["time passed"]),
            _concept("espaço", aliases=["localização"], examples_pt=["o espaço físico"], examples_en=["physical space"]),
            _concept("mudança", aliases=["transformação"], examples_pt=["a mudança ocorreu"], examples_en=["the change occurred"]),
        ],
    },
    {
        "category": "people",
        "concepts": [
            _concept("pessoa", aliases=["indivíduo", "gente"], isa=["ser"], attributes=["idade", "nome", "gênero"], examples_pt=["a pessoa falou"], examples_en=["the person spoke"]),
            _concept("homem", aliases=["masculino"], isa=["pessoa"], examples_pt=["o homem saiu"], examples_en=["the man left"]),
            _concept("mulher", aliases=["feminino"], isa=["pessoa"], examples_pt=["a mulher chegou"], examples_en=["the woman arrived"]),
            _concept("criança", aliases=["menino", "menina"], isa=["pessoa"], examples_pt=["a criança correu"], examples_en=["the child ran"]),
            _concept("trabalhador", aliases=["funcionário"], isa=["pessoa"], examples_pt=["o trabalhador ajudou"], examples_en=["the worker helped"]),
            _concept("cliente", aliases=["consumidor"], isa=["pessoa"], examples_pt=["o cliente comprou"], examples_en=["the customer bought"]),
            _concept("amigo", aliases=["parceiro"], isa=["pessoa"], examples_pt=["o amigo ligou"], examples_en=["the friend called"]),
            _concept("professor", isa=["pessoa"], examples_pt=["o professor ensinou"], examples_en=["the teacher taught"]),
            _concept("aluno", aliases=["estudante"], isa=["pessoa"], examples_pt=["o aluno estudou"], examples_en=["the student studied"]),
        ],
    },
    {
        "category": "objects",
        "concepts": [
            _concept("carro", aliases=["automóvel"], isa=["veículo"], part_of=["estrada"], attributes=["cor", "velocidade"], examples_pt=["o carro andou"], examples_en=["the car moved"]),
            _concept("moto", aliases=["motocicleta"], isa=["veículo"], examples_pt=["a moto passou"], examples_en=["the motorcycle passed"]),
            _concept("casa", aliases=["lar"], isa=["construção"], part_of=["cidade"], attributes=["tamanho"], examples_pt=["a casa caiu"], examples_en=["the house fell"]),
            _concept("porta", isa=["objeto"], part_of=["casa"], attributes=["cor", "material"], examples_pt=["a porta abriu"], examples_en=["the door opened"]),
            _concept("janela", isa=["objeto"], part_of=["casa"], attributes=["vidro"], examples_pt=["a janela fechou"], examples_en=["the window closed"]),
            _concept("computador", aliases=["pc"], isa=["máquina"], attributes=["processador", "memória"], examples_pt=["o computador ligou"], examples_en=["the computer turned on"]),
            _concept("telefone", aliases=["celular", "smartphone"], isa=["dispositivo"], attributes=["bateria"], examples_pt=["o telefone tocou"], examples_en=["the phone rang"]),
        ],
    },
    {
        "category": "actions",
        "concepts": [
            _concept("andar", aliases=["caminhar"], isa=["movimento"], attributes=["velocidade"], examples_pt=["ele andou"], examples_en=["he walked"]),
            _concept("correr", aliases=["disparar"], isa=["movimento"], examples_pt=["ele correu"], examples_en=["he ran"]),
            _concept("pular", aliases=["saltou"], isa=["movimento"], examples_pt=["ele pulou"], examples_en=["he jumped"]),
            _concept("falar", aliases=["dizer"], isa=["comunicação"], examples_pt=["ela falou"], examples_en=["she spoke"]),
            _concept("ver", aliases=["olhar"], isa=["percepção"], examples_pt=["ele viu"], examples_en=["he saw"]),
            _concept("pegar", aliases=["agarrar"], isa=["ação"], examples_pt=["ele pegou o objeto"], examples_en=["he grabbed the object"]),
            _concept("bater", aliases=["colidir"], isa=["impacto"], examples_pt=["o carro bateu"], examples_en=["the car hit"]),
        ],
    },
    {
        "category": "places",
        "concepts": [
            _concept("cidade", isa=["local"], part_of=["estado"], attributes=["população"], examples_pt=["a cidade cresceu"], examples_en=["the city grew"]),
            _concept("rua", aliases=["avenida"], isa=["local"], part_of=["cidade"], examples_pt=["a rua estava vazia"], examples_en=["the street was empty"]),
            _concept("casa", aliases=["lar"], isa=["local"], part_of=["cidade"], examples_pt=["a casa é branca"], examples_en=["the house is white"]),
            _concept("escola", isa=["local"], part_of=["cidade"], examples_pt=["a escola abriu"], examples_en=["the school opened"]),
        ],
    },
    {
        "category": "time",
        "concepts": [
            _concept("hoje", isa=["tempo"], examples_pt=["hoje"], examples_en=["today"]),
            _concept("amanhã", isa=["tempo"], examples_pt=["amanhã"], examples_en=["tomorrow"]),
            _concept("ontem", isa=["tempo"], examples_pt=["ontem"], examples_en=["yesterday"]),
            _concept("agora", isa=["tempo"], examples_pt=["agora mesmo"], examples_en=["right now"]),
        ],
    },
    {
        "category": "affect",
        "concepts": [
            _concept("feliz", aliases=["contente"], isa=["estado"], examples_pt=["ele está feliz"], examples_en=["he is happy"]),
            _concept("triste", aliases=["abatido"], isa=["estado"], examples_pt=["ela está triste"], examples_en=["she is sad"]),
            _concept("raiva", aliases=["ira"], isa=["estado"], examples_pt=["ele sentiu raiva"], examples_en=["he felt anger"]),
        ],
    },
    {
        "category": "properties",
        "concepts": [
            _concept("cor", isa=["propriedade"], examples_pt=["a cor vermelha"], examples_en=["the red color"]),
            _concept("tamanho", isa=["propriedade"], examples_pt=["o tamanho grande"], examples_en=["the large size"]),
            _concept("forma", aliases=["formato"], isa=["propriedade"], examples_pt=["a forma redonda"], examples_en=["the round shape"]),
        ],
    },
    {
        "category": "physics",
        "concepts": [
            _concept("força", aliases=["pressão"], isa=["quantidade"], examples_pt=["força aplicada"], examples_en=["applied force"]),
            _concept("velocidade", isa=["quantidade"], examples_pt=["velocidade alta"], examples_en=["high speed"]),
            _concept("aceleração", isa=["quantidade"], examples_pt=["aceleração constante"], examples_en=["constant acceleration"]),
        ],
    },
    {
        "category": "mind",
        "concepts": [
            _concept("pensar", aliases=["raciocinar"], isa=["processo"], examples_pt=["ele pensou"], examples_en=["he thought"]),
            _concept("saber", aliases=["entender", "compreender"], isa=["processo"], examples_pt=["ele soube"], examples_en=["he knew"]),
            _concept("lembrar", aliases=["recordar"], isa=["processo"], examples_pt=["ele lembrou"], examples_en=["he remembered"]),
            _concept("dúvida", aliases=["incerteza"], isa=["estado"], examples_pt=["ele tinha dúvida"], examples_en=["he had doubt"]),
        ],
    },
]


CATALOG_EXTENSION: List[Dict[str, object]] = [
    {
        "category": "relations",
        "concepts": [
            _concept("parte_de", aliases=["componente_de"], isa=["relação"], examples_pt=["a roda é parte do carro"], examples_en=["the wheel is part of the car"]),
            _concept("causa", aliases=["provoca"], isa=["relação"], examples_pt=["o fogo causa calor"], examples_en=["fire causes heat"]),
            _concept("efeito", aliases=["resultado"], isa=["relação"], examples_pt=["dor é efeito da lesão"], examples_en=["pain is the effect of injury"]),
            _concept("igual", aliases=["mesmo", "equivalente"], isa=["relação"], examples_pt=["carro = automóvel"], examples_en=["car = automobile"]),
            _concept("diferente", aliases=["distinto"], isa=["relação"], examples_pt=["dia ≠ noite"], examples_en=["day ≠ night"]),
            _concept("maior_que", aliases=["superior_a"], isa=["quantitativo"], examples_pt=["10 é maior que 5"], examples_en=["10 is greater than 5"]),
            _concept("menor_que", aliases=["inferior_a"], isa=["quantitativo"], examples_pt=["3 é menor que 7"], examples_en=["3 is less than 7"]),
            _concept("pertence", aliases=["contido_em"], isa=["relação"], examples_pt=["o arquivo pertence à pasta"], examples_en=["the file belongs to the folder"]),
        ],
    },
    {
        "category": "quantities",
        "concepts": [
            _concept("número", aliases=["valor"], isa=["quantidade"], examples_pt=["o número 5"], examples_en=["number 5"]),
            _concept("conta", aliases=["soma"], isa=["operação"], examples_pt=["5 + 5"], examples_en=["5 + 5"]),
            _concept("zero", aliases=["0"], isa=["número"], examples_pt=["zero itens"], examples_en=["zero items"]),
            _concept("um", aliases=["1"], isa=["número"], examples_pt=["um item"], examples_en=["one item"]),
            _concept("dois", aliases=["2"], isa=["número"], examples_pt=["dois itens"], examples_en=["two items"]),
            _concept("dez", aliases=["10"], isa=["número"], examples_pt=["dez pessoas"], examples_en=["ten people"]),
            _concept("cento", aliases=["100"], isa=["número"], examples_pt=["cem reais"], examples_en=["one hundred"]),
            _concept("mil", aliases=["1000"], isa=["número"], examples_pt=["mil unidades"], examples_en=["one thousand"]),
            _concept("muito", aliases=["quantidade_grande"], isa=["quantidade"], examples_pt=["muito trabalho"], examples_en=["a lot of work"]),
            _concept("pouco", aliases=["escasso"], isa=["quantidade"], examples_pt=["pouco tempo"], examples_en=["little time"]),
        ],
    },
    {
        "category": "social_affect",
        "concepts": [
            _concept("agrado", aliases=["gostar"], isa=["estado"], examples_pt=["ele gostou"], examples_en=["he liked"]),
            _concept("desagrado", aliases=["não_gostar"], isa=["estado"], examples_pt=["ele não gostou"], examples_en=["he disliked"]),
            _concept("medo", aliases=["receio"], isa=["estado"], examples_pt=["ela sentiu medo"], examples_en=["she felt fear"]),
            _concept("coragem", aliases=["bravura"], isa=["traço"], examples_pt=["ele teve coragem"], examples_en=["he showed courage"]),
            _concept("empatia", isa=["traço"], examples_pt=["ele demonstrou empatia"], examples_en=["he showed empathy"]),
            _concept("confiança", isa=["estado"], examples_pt=["ela confiou"], examples_en=["she trusted"]),
        ],
    },
    {
        "category": "social_relations",
        "concepts": [
            _concept("familia", aliases=["parente"], isa=["grupo"], examples_pt=["minha família"], examples_en=["my family"]),
            _concept("amigo", aliases=["parceiro"], isa=["pessoa"], examples_pt=["meu amigo"], examples_en=["my friend"]),
            _concept("conhecido", aliases=["contato"], isa=["pessoa"], examples_pt=["um conhecido"], examples_en=["an acquaintance"]),
            _concept("colega", aliases=["companheiro"], isa=["pessoa"], examples_pt=["colega de trabalho"], examples_en=["work colleague"]),
            _concept("chefe", aliases=["superior"], isa=["pessoa"], examples_pt=["meu chefe"], examples_en=["my boss"]),
            _concept("parceiro_romantico", aliases=["namorado", "companheiro"], isa=["pessoa"], examples_pt=["parceiro romântico"], examples_en=["romantic partner"]),
        ],
    },
    {
        "category": "social_actions",
        "concepts": [
            _concept("ajudar", aliases=["auxiliar"], isa=["ação"], examples_pt=["ele ajudou"], examples_en=["he helped"]),
            _concept("pedir", aliases=["solicitar"], isa=["ação"], examples_pt=["ele pediu algo"], examples_en=["he asked for something"]),
            _concept("ordenar", aliases=["mandar"], isa=["ação"], examples_pt=["ele ordenou"], examples_en=["he ordered"]),
            _concept("elogiar", isa=["ação"], examples_pt=["ele elogiou"], examples_en=["he praised"]),
            _concept("criticar", aliases=["reclamar"], isa=["ação"], examples_pt=["ele criticou"], examples_en=["he criticized"]),
            _concept("cumprimentar", aliases=["saudar"], isa=["ação"], examples_pt=["ele cumprimentou"], examples_en=["he greeted"]),
        ],
    },
    {
        "category": "logic",
        "concepts": [
            _concept("e", aliases=["and"], isa=["operador"], examples_pt=["A e B"], examples_en=["A and B"]),
            _concept("ou", aliases=["or"], isa=["operador"], examples_pt=["A ou B"], examples_en=["A or B"]),
            _concept("não", aliases=["not"], isa=["operador"], examples_pt=["não A"], examples_en=["not A"]),
            _concept("se_entao", aliases=["implica"], isa=["operador"], examples_pt=["se A então B"], examples_en=["if A then B"]),
            _concept("equivalente", aliases=["se_e_somente_se"], isa=["operador"], examples_pt=["A ↔ B"], examples_en=["A iff B"]),
            _concept("verdadeiro", aliases=["true"], isa=["valor"], examples_pt=["verdadeiro"], examples_en=["true"]),
            _concept("falso", aliases=["false"], isa=["valor"], examples_pt=["falso"], examples_en=["false"]),
        ],
    },
    {
        "category": "computing",
        "concepts": [
            _concept("arquivo", aliases=["file"], isa=["objeto"], examples_pt=["o arquivo abriu"], examples_en=["the file opened"]),
            _concept("pasta", aliases=["diretorio"], isa=["local"], examples_pt=["a pasta contém arquivos"], examples_en=["the folder contains files"]),
            _concept("programa", aliases=["software"], isa=["objeto"], examples_pt=["o programa executou"], examples_en=["the program executed"]),
            _concept("codigo", aliases=["source"], isa=["objeto"], examples_pt=["o código compilou"], examples_en=["the code compiled"]),
            _concept("função", aliases=["método"], isa=["entidade"], examples_pt=["a função retornou"], examples_en=["the function returned"]),
            _concept("erro", aliases=["bug"], isa=["estado"], examples_pt=["um erro ocorreu"], examples_en=["an error occurred"]),
        ],
    },
    {
        "category": "abstracts",
        "concepts": [
            _concept("ideia", isa=["conceito"], examples_pt=["uma ideia surgiu"], examples_en=["an idea appeared"]),
            _concept("conceito", isa=["entidade"], examples_pt=["um conceito importante"], examples_en=["an important concept"]),
            _concept("significado", aliases=["sentido"], isa=["entidade"], examples_pt=["qual é o significado?"], examples_en=["what is the meaning?"]),
            _concept("metodo", aliases=["técnica"], isa=["entidade"], examples_pt=["um método novo"], examples_en=["a new method"]),
            _concept("processo", aliases=["fluxo"], isa=["entidade"], examples_pt=["o processo começou"], examples_en=["the process started"]),
        ],
    },
    {
        "category": "communication",
        "concepts": [
            _concept("pergunta", aliases=["questionamento"], isa=["ato"], examples_pt=["ela fez uma pergunta"], examples_en=["she asked a question"]),
            _concept("resposta", aliases=["retorno"], isa=["ato"], examples_pt=["ele deu uma resposta"], examples_en=["he gave an answer"]),
            _concept("afirmacao", aliases=["declaração"], isa=["ato"], examples_pt=["ela fez uma afirmação"], examples_en=["she made a statement"]),
            _concept("negacao", isa=["ato"], examples_pt=["uma negação"], examples_en=["a negation"]),
            _concept("explicacao", isa=["ato"], examples_pt=["uma explicação"], examples_en=["an explanation"]),
            _concept("comando", aliases=["ordem"], isa=["ato"], examples_pt=["um comando"], examples_en=["a command"]),
        ],
    },
    {
        "category": "intents",
        "concepts": [
            _concept("saudacao", aliases=["cumprimento"], isa=["intenção"], examples_pt=["oi", "olá"], examples_en=["hi", "hello"]),
            _concept("informacao", aliases=["pergunta_informacional"], isa=["intenção"], examples_pt=["o que é?"], examples_en=["what is?"]),
            _concept("acao", aliases=["pedido"], isa=["intenção"], examples_pt=["faça isso"], examples_en=["do this"]),
            _concept("explicacao", isa=["intenção"], examples_pt=["explique"], examples_en=["explain"]),
            _concept("opiniao", isa=["intenção"], examples_pt=["o que você acha?"], examples_en=["what do you think?"]),
            _concept("avaliacao", aliases=["julgamento"], isa=["intenção"], examples_pt=["isso é bom?"], examples_en=["is this good?"]),
        ],
    },
    {
        "category": "causality",
        "concepts": [
            _concept("causa_direta", aliases=["causa_imediata"], isa=["causa"], examples_pt=["fogo causa calor"], examples_en=["fire causes heat"]),
            _concept("causa_indireta", aliases=["causa_consequencial"], isa=["causa"], examples_pt=["chuva causa trânsito"], examples_en=["rain causes traffic"]),
            _concept("efeito_direto", aliases=["resultado_imediato"], isa=["efeito"], examples_pt=["o efeito imediato"], examples_en=["the direct effect"]),
            _concept("efeito_indireto", aliases=["efeito_consequencial"], isa=["efeito"], examples_pt=["efeito secundário"], examples_en=["secondary effect"]),
            _concept("condicao", aliases=["requisito"], isa=["relação"], examples_pt=["se X, então Y"], examples_en=["if X then Y"]),
            _concept("contrafactual", aliases=["contrario_ao_fato"], isa=["raciocinio"], examples_pt=["se não tivesse chovido..."], examples_en=["if it hadn't rained..."]),
            _concept("proposito", aliases=["finalidade"], isa=["relação"], examples_pt=["ele fez isso para ajudar"], examples_en=["he did it to help"]),
            _concept("justificativa", aliases=["motivo"], isa=["relação"], examples_pt=["ele fez isso porque..."], examples_en=["he did it because..."]),
        ],
    },
    {
        "category": "math",
        "concepts": [
            _concept("expressao", aliases=["ex"], isa=["objeto"], examples_pt=["2 + 2"], examples_en=["2 + 2"]),
            _concept("variavel", aliases=["x", "y", "z"], isa=["entidade"], examples_pt=["x é uma variável"], examples_en=["x is a variable"]),
            _concept("constante", isa=["entidade"], examples_pt=["constante pi"], examples_en=["constant pi"]),
            _concept("funcao", aliases=["f"], isa=["entidade"], examples_pt=["f(x) = x+1"], examples_en=["f(x)=x+1"]),
            _concept("dominio", isa=["entidade"], examples_pt=["domínio de f"], examples_en=["domain of f"]),
            _concept("intervalo", aliases=["range"], isa=["entidade"], examples_pt=["intervalo [0,1]"], examples_en=["interval [0,1]"]),
            _concept("soma", aliases=["+"], isa=["operação"], examples_pt=["a soma"], examples_en=["the sum"]),
            _concept("subtracao", aliases(["-"]), isa=["operação"], examples_pt(["subtração"]), examples_en(["subtraction"])),
            _concept("multiplicacao", aliases=["*"], isa=["operação"], examples_pt=["multiplicação"], examples_en=["multiplication"]),
            _concept("divisao", aliases=["/"], isa=["operação"], examples_pt=["divisão"], examples_en=["division"]),
            _concept("aplicacao_funcional", aliases=["aplicar"], isa=["operação"], examples_pt=["aplicar f a x"], examples_en=["apply f to x"]),
        ],
    },
