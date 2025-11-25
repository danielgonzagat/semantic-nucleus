"""
Corpus de treinamento para o classificador NCD do IAN.
Contém exemplos de intenções variadas para compressão semântica.
"""

IAN_NCD_CORPUS = {
    "GREETING": [
        "olá", "oi", "bom dia", "boa tarde", "boa noite", 
        "e aí", "como vai", "tudo bem", "saudações", "hello", 
        "hi", "hey", "greetings", "salut", "bonjour", "hola",
        "iniciar conversa", "começar papo", "oi amigo", "ola pessoal"
    ],
    "FAREWELL": [
        "tchau", "adeus", "até logo", "fui", "encerrar", 
        "sair", "fechar", "bye", "goodbye", "see you", 
        "exit", "quit", "adios", "au revoir", "terminar",
        "parar por hoje", "finalizar sessão", "kill process",
        "desligar", "shutdown", "encerrar atividade", "fechar tudo"
    ],
    "QUESTION_FACT": [
        "o que é", "quem é", "qual é", "onde fica", "quando foi",
        "me explique", "defina", "significado de", "what is",
        "who is", "explain", "definition of", "que es", "qu'est-ce que",
        "me diga sobre", "qual a sua função", "para que serve"
    ],
    "QUESTION_MATH": [
        "quanto é", "calcule", "some", "divida", "multiplique", 
        "subtraia", "raiz quadrada", "seno de", "1 + 1", "2 * 5",
        "calculate", "compute", "math", "plus", "minus", "times",
        "divided by", "equação", "resultado da conta", "valor de x"
    ],
    "COMMAND": [
        "faça", "crie", "gere", "execute", "escreva", "liste",
        "mostre", "do", "make", "create", "generate", "run",
        "execute", "show", "list", "imprima", "construa",
        "analise este código", "verifique isso"
    ],
    "IDENTITY": [
        "quem é você", "qual seu nome", "você é uma ia", "quem te criou",
        "apresente-se", "fale sobre você", "who are you", "your name",
        "are you ai", "quien eres", "qui etes vous", "teu criador",
        "voce é um robô"
    ]
}
