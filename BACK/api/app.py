"""
API do formulário de desligamento.

Serve o formulário (FRONT/index.html) e recebe as respostas, que vão para a
coleção "desligamento" no Firestore através de BACK/modules/module.py.

Rodar:
    python BACK/api/app.py
e abrir http://127.0.0.1:5000
"""

from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from flask import Flask, jsonify, request, send_from_directory  # noqa: E402

from BACK.modules.module import (  # noqa: E402
    COLECAO_DESLIGAMENTO,
    PERGUNTAS,
    SECOES,
    normalizar_respostas,
    send_data,
)

FRONT = RAIZ / "FRONT"

app = Flask(__name__, static_folder=str(FRONT), static_url_path="/estatico")


@app.get("/")
def formulario():
    return send_from_directory(FRONT, "index.html")


@app.get("/api/perguntas")
def listar_perguntas():
    """Questionário que o formulário usa para se montar."""

    return jsonify({"secoes": SECOES, "perguntas": PERGUNTAS})


@app.post("/api/desligamento")
def criar_desligamento():
    """Grava uma resposta nova na coleção "desligamento"."""

    payload = request.get_json(silent=True)
    if payload is None:
        return jsonify({"erros": ["Envie as respostas como JSON."]}), 400

    dados, erros = normalizar_respostas(payload)
    if erros:
        return jsonify({"erros": erros}), 400

    try:
        doc_id, carimbo = send_data(dados, colecao=COLECAO_DESLIGAMENTO)
    except Exception:
        app.logger.exception("Falha ao gravar resposta de desligamento")
        return (
            jsonify({"erros": ["Não foi possível salvar agora. Tente de novo em alguns instantes."]}),
            502,
        )

    return jsonify({"id": doc_id, "carimbo": carimbo, "colecao": COLECAO_DESLIGAMENTO}), 201


if __name__ == "__main__":
    app.run(debug=True)
