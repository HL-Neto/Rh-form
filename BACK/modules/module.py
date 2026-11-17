"""
Acesso ao Firestore e gravação das respostas do formulário de desligamento.

PERGUNTAS é a fonte única de verdade do questionário: o formulário é montado a
partir de /api/perguntas, que devolve essa mesma lista. Assim o front-end e a
validação do back-end nunca ficam fora de sincronia.

Os nomes dos campos são exatamente os nomes das colunas já existentes na
coleção "desligamento" (inclusive os erros de digitação do formulário antigo),
para que os documentos novos continuem consultáveis junto com os antigos. O
texto que a pessoa lê na tela fica em "label", que é corrigido e reescrito.
"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

import firebase_admin
from dotenv import load_dotenv
from firebase_admin import credentials, firestore

RAIZ = Path(__file__).resolve().parents[2]

load_dotenv(RAIZ / ".env")

COLECAO_DESLIGAMENTO = "desligamento"
CAMPO_CARIMBO = "Carimbo de data/hora"
LIMITE_TEXTO = 5000

SECOES = [
    {
        "id": "pessoa",
        "titulo": "Sobre você",
        "descricao": "Só para o RH saber de quem é a resposta.",
    },
    {
        "id": "saida",
        "titulo": "A saída",
        "descricao": "O que levou ao desligamento.",
    },
    {
        "id": "notas",
        "titulo": "Suas notas",
        "descricao": "1 é o pior cenário, 5 o melhor.",
    },
    {
        "id": "gestao",
        "titulo": "Liderança e gestão",
        "descricao": "Como foi ser conduzido no dia a dia.",
    },
    {
        "id": "cultura",
        "titulo": "Ambiente e cultura",
        "descricao": "Como era conviver e trabalhar junto.",
    },
    {
        "id": "fica",
        "titulo": "O que fica",
        "descricao": "O que valeu a pena nesse tempo.",
    },
    {
        "id": "muda",
        "titulo": "O que precisa mudar",
        "descricao": "Aqui é onde sua resposta vira decisão.",
    },
    {
        "id": "final",
        "titulo": "Para finalizar",
        "descricao": "Espaço aberto, sem pergunta guiando.",
    },
]

PERGUNTAS = [
    # --- Sobre você --------------------------------------------------------
    {
        "campo": "Nome Completo:",
        "label": "Nome completo",
        "secao": "pessoa",
        "tipo": "texto",
        "obrigatorio": True,
    },
    {
        "campo": "Qual se cargo?",
        "label": "Qual era seu cargo?",
        "secao": "pessoa",
        "tipo": "texto",
        "obrigatorio": True,
    },
    {
        "campo": "Qual seu departamento?",
        "label": "Qual era seu departamento?",
        "secao": "pessoa",
        "tipo": "texto",
        "obrigatorio": True,
        "sugestoes": [
            "Administração (Geral)",
            "Comercial / Vendas",
            "Pós-venda / Oficina",
            "Peças",
            "Financeiro",
            "Recursos Humanos",
            "Marketing",
            "Logística",
            "TI",
        ],
    },
    {
        "campo": "Tempo de empresa?",
        "label": "Quanto tempo você ficou na empresa?",
        "secao": "pessoa",
        "tipo": "select",
        "obrigatorio": True,
        "opcoes": [
            "Menos de 6 meses.",
            "6 meses a 1 ano.",
            "1 a 3 anos.",
            "3 a 5 anos.",
            "Mais de 5 anos.",
        ],
    },
    {
        "campo": "Tipo de desligamento?",
        "label": "Tipo de desligamento",
        "secao": "pessoa",
        "tipo": "select",
        "obrigatorio": True,
        "opcoes": [
            "Pedido de demissão.",
            "Desligamento pela empresa.",
            "Fim de contrato ou experiência.",
            "Acordo entre as partes.",
        ],
    },
    # --- A saída -----------------------------------------------------------
    {
        "campo": "Qual o motivo da saída?",
        "label": "Qual o motivo da saída?",
        "secao": "saida",
        "tipo": "longo",
        "obrigatorio": True,
    },
    {
        "campo": "O que podera ter evitado sua saída?",
        "label": "O que poderia ter evitado sua saída?",
        "secao": "saida",
        "tipo": "longo",
        "obrigatorio": False,
    },
    {
        "campo": "Deixe seu comentário:",
        "label": "Quer comentar algo sobre esse motivo?",
        "secao": "saida",
        "tipo": "longo",
        "obrigatorio": False,
    },
    # --- Suas notas --------------------------------------------------------
    {
        "campo": "Avalie De 1 a 5 sua liderança.",
        "label": "Liderança",
        "secao": "notas",
        "tipo": "nota",
        "obrigatorio": True,
    },
    {
        "campo": "Avalie de 1 a 5 Condições de trabalho.",
        "label": "Condições de trabalho",
        "secao": "notas",
        "tipo": "nota",
        "obrigatorio": True,
        "ajuda": "Estrutura, equipamento, segurança e carga de trabalho.",
    },
    {
        "campo": "Avalie de 1 a 5 Reconhecimento",
        "label": "Reconhecimento",
        "secao": "notas",
        "tipo": "nota",
        "obrigatorio": True,
    },
    {
        "campo": "Avalie de 1 a 5 Segurança Psicológica",
        "label": "Segurança psicológica",
        "secao": "notas",
        "tipo": "nota",
        "obrigatorio": True,
        "ajuda": "Poder falar, errar e discordar sem medo de retaliação.",
    },
    {
        "campo": "De 1 a 5 como você avaliaria sua experiência geral na empresa?",
        "label": "Experiência geral na empresa",
        "secao": "notas",
        "tipo": "nota",
        "obrigatorio": True,
    },
    # --- Liderança e gestão ------------------------------------------------
    {
        "campo": "Como você avalia o suporte e feedback recebido do seu gestor direto (Supervisor)?",
        "label": "Suporte e feedback do gestor direto (supervisor)",
        "secao": "gestao",
        "tipo": "select",
        "obrigatorio": False,
        "opcoes": [
            "Muito bom",
            "Bom",
            "Regular",
            "Ruim",
            "Muito ruim",
            "Não recebi feedback",
        ],
    },
    {
        "campo": "Como você avalia o suporte e feedback recebido do seu gestor indireto (Gerência)?",
        "label": "Suporte e feedback do gestor indireto (gerência)",
        "secao": "gestao",
        "tipo": "select",
        "obrigatorio": False,
        "opcoes": [
            "Muito bom",
            "Bom",
            "Regular",
            "Ruim",
            "Muito ruim",
            "Não recebi feedback",
        ],
    },
    {
        "campo": "Havia clareza de expectativas e metas no seu cargo?",
        "label": "Havia clareza de expectativas e metas no seu cargo?",
        "secao": "gestao",
        "tipo": "select",
        "obrigatorio": False,
        "opcoes": [
            "Sempre",
            "Na maior parte do tempo",
            "Raramente",
            "Nunca",
        ],
    },
    {
        "campo": "Você recebeu reconhecimento adequado pelo seu trabalho?",
        "label": "Você recebeu reconhecimento adequado pelo seu trabalho?",
        "secao": "gestao",
        "tipo": "select",
        "obrigatorio": False,
        "opcoes": ["Sim", "Em parte", "Não"],
    },
    {
        "campo": "Sentia que havia oportunidades de crescimento e desenvolvimento?",
        "label": "Sentia que havia oportunidades de crescimento e desenvolvimento?",
        "secao": "gestao",
        "tipo": "select",
        "obrigatorio": False,
        "opcoes": ["Sim", "Em parte", "Não"],
    },
    # --- Ambiente e cultura ------------------------------------------------
    {
        "campo": "O ambiente de trabalho era colaborativo e respeitoso?",
        "label": "O ambiente de trabalho era colaborativo e respeitoso?",
        "secao": "cultura",
        "tipo": "select",
        "obrigatorio": False,
        "opcoes": [
            "Sempre",
            "Na maior parte do tempo",
            "Raramente",
            "Nunca",
        ],
    },
    {
        "campo": "Como era a comunicação entre equipes e departamentos?",
        "label": "Como era a comunicação entre equipes e departamentos?",
        "secao": "cultura",
        "tipo": "longo",
        "obrigatorio": False,
    },
    {
        "campo": "Como você descreveria a cultura da empresa?",
        "label": "Como você descreveria a cultura da empresa?",
        "secao": "cultura",
        "tipo": "longo",
        "obrigatorio": False,
    },
    {
        "campo": "Você vivenciou alguma situação de assédio?",
        "label": "Você vivenciou alguma situação de assédio?",
        "secao": "cultura",
        "tipo": "select",
        "obrigatorio": False,
        "opcoes": ["Não", "Sim"],
        "ajuda": "Se sim, use o campo aberto no fim do formulário para contar o que aconteceu.",
    },
    # --- O que fica --------------------------------------------------------
    {
        "campo": "O que mais você valorizou durante seu tempo aqui?",
        "label": "O que mais você valorizou durante seu tempo aqui?",
        "secao": "fica",
        "tipo": "longo",
        "obrigatorio": False,
    },
    {
        "campo": "O que você vai sentir mais falta?",
        "label": "Do que você vai sentir mais falta?",
        "secao": "fica",
        "tipo": "longo",
        "obrigatorio": False,
    },
    {
        "campo": "O que você não vai sentir falta?",
        "label": "E do que você não vai sentir falta?",
        "secao": "fica",
        "tipo": "longo",
        "obrigatorio": False,
    },
    # --- O que precisa mudar -----------------------------------------------
    {
        "campo": "O que a motomar deveria melhorar?",
        "label": "O que a Motomar deveria melhorar?",
        "secao": "muda",
        "tipo": "longo",
        "obrigatorio": False,
    },
    {
        "campo": "Se fosse possível mudar algo na empresa, o que seria?",
        "label": "Se você pudesse mudar uma coisa na empresa, qual seria?",
        "secao": "muda",
        "tipo": "longo",
        "obrigatorio": False,
    },
    {
        "campo": "Você consideraria voltar a trabalhar aqui no futuro, caso houvesse oportunidade?",
        "label": "Você consideraria voltar a trabalhar aqui no futuro?",
        "secao": "muda",
        "tipo": "select",
        "obrigatorio": False,
        "opcoes": ["Sim", "Talvez", "Não"],
    },
    # --- Para finalizar ----------------------------------------------------
    {
        "campo": "Há algo mais que gostaria de compartilhar e não foi mencionado?",
        "label": "Há algo mais que você queira contar e que não foi perguntado?",
        "secao": "final",
        "tipo": "longo",
        "obrigatorio": False,
    },
]

# Campos que existem na coleção por causa de versões antigas do formulário e
# que não são mais perguntados. Vão vazios em todo documento novo, para que a
# coleção inteira mantenha o mesmo formato.
CAMPOS_HERDADOS = (
    "Deixe seu comentário: 2",
    "O que mais você valorizou durante seu tempo aqui? 2",
)


class RespostaInvalida(ValueError):
    """Respostas recusadas antes de chegar no banco."""

    def __init__(self, erros):
        super().__init__("; ".join(erros))
        self.erros = list(erros)


def get_fb():
    """Cliente do Firestore. Inicializa o app do Firebase apenas uma vez."""

    try:
        firebase_admin.get_app()
    except ValueError:
        cred_path = (os.getenv("FIREBASE_CREDENTIALS_PATH") or "").strip().strip('"').strip("'")
        if not cred_path:
            raise RuntimeError("FIREBASE_CREDENTIALS_PATH não está definido no .env.")
        caminho = Path(cred_path)
        if not caminho.is_absolute():
            caminho = RAIZ / caminho
        if not caminho.exists():
            raise RuntimeError(f"Credencial do Firebase não encontrada em {caminho}")
        firebase_admin.initialize_app(credentials.Certificate(str(caminho)))

    return firestore.client()


def perguntas_por_campo():
    """Índice campo -> definição da pergunta."""

    return {pergunta["campo"]: pergunta for pergunta in PERGUNTAS}


def _validar_nota(bruto, pergunta):
    if bruto is None or bruto == "":
        if pergunta["obrigatorio"]:
            return None, f'"{pergunta["label"]}": escolha uma nota de 1 a 5.'
        return None, None
    try:
        nota = int(str(bruto).strip())
    except (TypeError, ValueError):
        return None, f'"{pergunta["label"]}": a nota precisa ser um número de 1 a 5.'
    if not 1 <= nota <= 5:
        return None, f'"{pergunta["label"]}": a nota precisa estar entre 1 e 5.'
    return nota, None


def _validar_texto(bruto, pergunta):
    texto = "" if bruto is None else str(bruto).strip()
    if not texto:
        if pergunta["obrigatorio"]:
            return None, f'"{pergunta["label"]}": campo obrigatório.'
        return "", None
    if len(texto) > LIMITE_TEXTO:
        return None, f'"{pergunta["label"]}": use no máximo {LIMITE_TEXTO} caracteres.'
    if pergunta["tipo"] == "select" and texto not in pergunta.get("opcoes", []):
        return None, f'"{pergunta["label"]}": escolha uma das opções da lista.'
    return texto, None


def normalizar_respostas(payload):
    """Converte o JSON do formulário no documento que vai para o Firestore.

    Devolve (dados, erros). Campos desconhecidos são ignorados, campos
    opcionais em branco entram como string vazia e as notas entram como
    inteiro, do mesmo jeito que os documentos antigos da coleção.
    """

    if not isinstance(payload, dict):
        return {}, ["Envie um objeto JSON com as respostas."]

    dados = {}
    erros = []

    for pergunta in PERGUNTAS:
        bruto = payload.get(pergunta["campo"])
        if pergunta["tipo"] == "nota":
            valor, erro = _validar_nota(bruto, pergunta)
        else:
            valor, erro = _validar_texto(bruto, pergunta)
        if erro:
            erros.append(erro)
        elif valor is not None:
            dados[pergunta["campo"]] = valor

    for campo in CAMPOS_HERDADOS:
        dados[campo] = ""

    return dados, erros


def send_data(dados, colecao=COLECAO_DESLIGAMENTO, db=None):
    """Grava um documento NOVO na coleção e devolve (id, carimbo).

    Usa add(), que gera um id automático, então cada envio do formulário cria
    um documento próprio e nunca sobrescreve um envio anterior.
    """

    db = db or get_fb()

    documento = dict(dados)
    carimbo = documento.get(CAMPO_CARIMBO) or datetime.now().isoformat()
    documento[CAMPO_CARIMBO] = carimbo

    _, referencia = db.collection(colecao).add(documento)
    return referencia.id, carimbo


def registrar_desligamento(payload):
    """Valida o JSON do formulário e grava na coleção "desligamento"."""

    dados, erros = normalizar_respostas(payload)
    if erros:
        raise RespostaInvalida(erros)
    return send_data(dados)
