"""
Treina, quantiza para int8 no formato da placa e salva a rede do Fashion-MNIST
usada pelo servidor (emulação e placa usam os mesmos pesos).
Só precisa de numpy (não usa PyTorch):

    python treinar.py            # baixa os dados e treina (~30 s)

O modelo já vem treinado na pasta modelos/; rode isto só se quiser treinar
de novo ou mudar alguma coisa.
"""

from __future__ import annotations

import argparse
import gzip
import time
import urllib.request
from pathlib import Path

import numpy as np

from npu_emulada import PASTA_MODELOS, ModeloNPU, im2col_3x3_passo2, preparar_entrada

PASTA_DADOS = Path(__file__).parent / "dados"
FONTE = "https://raw.githubusercontent.com/zalandoresearch/fashion-mnist/master/data/fashion/"
ARQUIVOS = ["train-images-idx3-ubyte", "train-labels-idx1-ubyte",
            "t10k-images-idx3-ubyte", "t10k-labels-idx1-ubyte"]


def carregar():
    PASTA_DADOS.mkdir(exist_ok=True)
    saida = []
    for arq in ARQUIVOS:
        destino = PASTA_DADOS / f"{arq}.gz"
        if not destino.exists():
            print(f"  baixando {arq}.gz")
            urllib.request.urlretrieve(FONTE + f"{arq}.gz", destino)
        with gzip.open(destino, "rb") as f:
            dados = f.read()
        ndim = dados[3]
        dims = [int.from_bytes(dados[4 + 4 * i:8 + 4 * i], "big") for i in range(ndim)]
        saida.append(np.frombuffer(dados, np.uint8, offset=4 + 4 * ndim).reshape(dims))
    return saida


class Adam:
    def __init__(self, params, lr=3e-3, b1=0.9, b2=0.999, eps=1e-8):
        self.p, self.lr, self.b1, self.b2, self.eps = params, lr, b1, b2, eps
        self.m = {k: np.zeros_like(v) for k, v in params.items()}
        self.v = {k: np.zeros_like(v) for k, v in params.items()}
        self.t = 0

    def passo(self, grads):
        self.t += 1
        for k, g in grads.items():
            self.m[k] = self.b1 * self.m[k] + (1 - self.b1) * g
            self.v[k] = self.b2 * self.v[k] + (1 - self.b2) * g * g
            mh = self.m[k] / (1 - self.b1 ** self.t)
            vh = self.v[k] / (1 - self.b2 ** self.t)
            self.p[k] -= self.lr * mh / (np.sqrt(vh) + self.eps)


def frente(p, janelas):
    z1 = janelas @ p["w1"] + p["b1"]                 # (N, 169, 4)
    plano = np.maximum(z1, 0).reshape(len(janelas), -1)
    return z1, plano, plano @ p["w2"] + p["b2"]


def treinar(epocas: int, rng):
    xtr, ytr, xte, yte = carregar()
    paraf = lambda x: np.round(x.astype(np.float32) * 127 / 255) / 127   # entrada da placa
    p = {"w1": rng.normal(0, np.sqrt(2 / 9), (9, 4)).astype(np.float32),
         "b1": np.zeros(4, np.float32),
         "w2": rng.normal(0, np.sqrt(1 / 676), (676, 10)).astype(np.float32),
         "b2": np.zeros(10, np.float32)}
    opt = Adam(p)
    for ep in range(epocas):
        t0 = time.time()
        ordem = rng.permutation(len(xtr))
        for i in range(0, len(ordem), 128):
            idx = ordem[i:i + 128]
            janelas = im2col_3x3_passo2(paraf(xtr[idx]))
            z1, plano, z2 = frente(p, janelas)
            # entropia cruzada
            z2 = z2 - z2.max(1, keepdims=True)
            prob = np.exp(z2)
            prob /= prob.sum(1, keepdims=True)
            prob[np.arange(len(idx)), ytr[idx]] -= 1
            dz2 = prob / len(idx)
            dplano = (dz2 @ p["w2"].T).reshape(z1.shape) * (z1 > 0)
            opt.passo({"w2": plano.T @ dz2, "b2": dz2.sum(0),
                       "w1": np.einsum("npk,npf->kf", janelas, dplano),
                       "b1": dplano.sum((0, 1))})
        opt.lr *= 0.8
        acc = (frente(p, im2col_3x3_passo2(paraf(xte)))[2].argmax(1) == yte).mean()
        print(f"  época {ep + 1}/{epocas}: acurácia float {acc:.2%} ({time.time() - t0:.0f} s)")

    # --- quantização int8 no formato da placa (mesmo esquema do cnn_client.py) ---
    # Calibração: maiores saídas da conv (após ReLU) e dos logits em todo o treino,
    # para nenhuma imagem passar de 120 depois do >> 8 (a placa trabalha até 127).
    max_y1 = max_y2 = 0.0
    for i in range(0, len(xtr), 5000):
        _, plano, z2 = frente(p, im2col_3x3_passo2(paraf(xtr[i:i + 5000])))
        max_y1, max_y2 = max(max_y1, float(plano.max())), max(max_y2, float(np.abs(z2).max()))
    w_conv_f = p["w1"].T                     # (4, 9): filtro x (dy*3+dx), como no PyTorch
    w_fc_f = p["w2"].T                       # (10, 676): entrada em channels-last, como na placa

    s_w1 = min(127.0 / np.abs(w_conv_f).max(), (120.0 * 256.0) / (max_y1 * 127.0))
    w_conv = np.round(w_conv_f * s_w1).astype(np.int8)
    b_conv = np.round(p["b1"] * 127.0 * s_w1).astype(np.int32)
    s_y1 = (127.0 * s_w1) / 256.0
    s_w2 = min(127.0 / np.abs(w_fc_f).max(), (120.0 * 256.0) / (max_y2 * s_y1))
    w_fc = np.round(w_fc_f * s_w2).astype(np.int8)
    b_fc = np.round(p["b2"] * s_y1 * s_w2).astype(np.int32)
    escala_logit = 256.0 / (s_y1 * s_w2)     # logit real ~= logit_int8 * escala_logit

    PASTA_MODELOS.mkdir(exist_ok=True)
    caminho = PASTA_MODELOS / "fashion_int8.npz"
    np.savez(caminho, w_conv=w_conv, b_conv=b_conv, w_fc=w_fc, b_fc=b_fc,
             escala_logit=escala_logit)

    # acurácia da emulação inteira, com as mesmas contas que o servidor usa
    logits = ModeloNPU(caminho).logits_emulados(preparar_entrada(xte))
    acc_q = (logits.argmax(1) == yte).mean()
    print(f"  acurácia int8 (emulação da placa): {acc_q:.2%}")
    print(f"  maior saída da conv no teste: {acc_logits_conv(w_conv, b_conv, xte).max()} "
          f"(a placa satura em 127)")
    np.savez(caminho, w_conv=w_conv, b_conv=b_conv, w_fc=w_fc, b_fc=b_fc,
             escala_logit=escala_logit, acuracia_int8=acc_q)
    # amostras do conjunto de teste servidas por GET /amostra/fashion
    np.savez_compressed(PASTA_MODELOS / "fashion_amostras.npz",
                        imagens=xte[:2000], rotulos=yte[:2000])


def acc_logits_conv(w_conv, b_conv, imagens):
    """Saída da conv já deslocada (>> 8), para conferir se cabe em 127."""
    x = preparar_entrada(imagens).reshape(-1, 28, 28).astype(np.int64)
    acc = im2col_3x3_passo2(x) @ w_conv.astype(np.int64).T + b_conv
    return acc >> 8


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--epocas", type=int, default=15)
    args = ap.parse_args()
    print("Treinando Fashion-MNIST...")
    treinar(args.epocas, np.random.default_rng(42))
    print("Modelo salvo em", PASTA_MODELOS)
