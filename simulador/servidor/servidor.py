"""
Servidor que faz o papel do hospedeiro da placa: entrega peças do conjunto de
teste do Fashion-MNIST, recebe a imagem do celular, "envia para a NPU" (aqui,
a emulação int8) e devolve o resultado.

    python servidor.py                       # porta 5000, aceita conexões da rede
    python servidor.py --atraso 1500         # +1,5 s em cada inferência (testar a espera)
    python servidor.py --falha 0.3           # 30% das inferências "a placa não respondeu"

O celular precisa usar o IP do computador (mostrado ao iniciar), nunca localhost.
"""

from __future__ import annotations

import argparse
import base64
import random
import socket
import struct
import time
import zlib

import numpy as np
from flask import Flask, jsonify, request

from npu_emulada import CLASSES, PASTA_MODELOS, ModeloCNN

app = Flask(__name__)
MODELO = ModeloCNN()
AMOSTRAS = np.load(PASTA_MODELOS / "fashion_amostras.npz")
CONFIG = {"atraso_ms": 0, "falha": 0.0}


@app.after_request
def cors(resposta):
    # O Expo Go não precisa disso; o Expo Web (navegador) precisa.
    resposta.headers["Access-Control-Allow-Origin"] = "*"
    resposta.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return resposta


def png_data_uri(pixels: np.ndarray, ampliacao: int = 4) -> str:
    """Imagem 28x28 em tons de cinza -> PNG 112x112 em base64, pronto para o
    <Image source={{ uri }} /> do React Native. Ampliada aqui, pixel a pixel,
    para não ficar borrada no celular."""
    img = np.kron(pixels.reshape(28, 28).astype(np.uint8),
                  np.ones((ampliacao, ampliacao), np.uint8))
    altura, largura = img.shape
    bruto = b"".join(b"\x00" + linha.tobytes() for linha in img)

    def bloco(tipo: bytes, dados: bytes) -> bytes:
        return (struct.pack(">I", len(dados)) + tipo + dados
                + struct.pack(">I", zlib.crc32(tipo + dados) & 0xFFFFFFFF))

    png = (b"\x89PNG\r\n\x1a\n"
           + bloco(b"IHDR", struct.pack(">IIBBBBB", largura, altura, 8, 0, 0, 0, 0))
           + bloco(b"IDAT", zlib.compress(bruto, 9))
           + bloco(b"IEND", b""))
    return "data:image/png;base64," + base64.b64encode(png).decode()


def erro(mensagem: str, codigo: int):
    return jsonify(erro=mensagem), codigo


@app.get("/status")
def status():
    return jsonify(ok=True, origem="emulacao", atraso_ms=CONFIG["atraso_ms"],
                   falha=CONFIG["falha"])


@app.get("/amostra/fashion")
def amostra():
    i = random.randrange(len(AMOSTRAS["rotulos"]))
    classe = int(AMOSTRAS["rotulos"][i])
    img = AMOSTRAS["imagens"][i]
    return jsonify(id=i, pixels=img.reshape(-1).tolist(), imagem_png=png_data_uri(img),
                   classe_real=classe, rotulo_real=CLASSES[classe])


@app.post("/inferir/fashion")
def inferir():
    corpo = request.get_json(silent=True) or {}
    pixels = corpo.get("pixels")
    if not isinstance(pixels, list) or len(pixels) != 784:
        return erro("envie 'pixels' com exatamente 784 inteiros de 0 a 255", 400)
    try:
        arr = np.asarray(pixels, dtype=np.int64)
    except (TypeError, ValueError):
        return erro("os pixels precisam ser números inteiros", 400)
    if arr.min() < 0 or arr.max() > 255:
        return erro("os pixels precisam estar entre 0 e 255", 400)
    if arr.max() == 0:
        return erro("a imagem está vazia", 400)

    r = MODELO.inferir(arr.astype(np.uint8))    # <- troque aqui pela placa de verdade

    # espera o tempo que a placa levaria (UART + NPU) e, se configurado, falha
    time.sleep((r.tempo_placa_ms + CONFIG["atraso_ms"]) / 1000)
    if random.random() < CONFIG["falha"]:
        return erro("a placa não respondeu dentro do prazo", 503)

    return jsonify(
        classe=r.classe,
        rotulo=CLASSES[r.classe],
        confianca=r.probabilidades[r.classe],
        probabilidades=r.probabilidades,
        rotulos=CLASSES,
        logits=r.logits,
        ciclos=r.ciclos,
        tempo_npu_us=round(r.tempo_npu_us, 2),
        tempo_serial_ms=round(r.tempo_serial_ms, 2),
        tempo_placa_ms=round(r.tempo_placa_ms, 2),
        origem="emulacao",
    )


def ip_da_rede() -> str:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("10.255.255.255", 1))
            return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--porta", type=int, default=5000)
    ap.add_argument("--atraso", type=int, default=0, help="ms extras por inferência")
    ap.add_argument("--falha", type=float, default=0.0, help="probabilidade de 503 (0 a 1)")
    args = ap.parse_args()
    CONFIG.update(atraso_ms=args.atraso, falha=args.falha)
    print(f"\n  No celular, use: http://{ip_da_rede()}:{args.porta}")
    print(f"  Neste computador: http://localhost:{args.porta}\n")
    app.run(host="0.0.0.0", port=args.porta, threaded=True)
