"""
Treina, quantiza para int8 e salva a rede do Fashion-MNIST usada pelo servidor.
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

from npu_emulada import PASTA_MODELOS, im2col_3x3_passo2, par_m_s, requantizar

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

    # --- quantização int8 (escalas calibradas em 5.000 imagens de treino) ---
    s_x = 1 / 127
    _, plano, z2 = frente(p, im2col_3x3_passo2(paraf(xtr[:5000])))
    s_w1 = np.abs(p["w1"]).max() / 127
    s_a1 = np.percentile(plano, 99.99) / 127
    s_w2 = np.abs(p["w2"]).max() / 127
    s_l = np.percentile(np.abs(z2), 99.9) / 127
    q = {"w1": np.round(p["w1"] / s_w1).astype(np.int8),
         "b1": np.round(p["b1"] / (s_x * s_w1)).astype(np.int32),
         "w2": np.round(p["w2"] / s_w2).astype(np.int8),
         "b2": np.round(p["b2"] / (s_a1 * s_w2)).astype(np.int32)}
    q["m1"], q["s1"] = par_m_s(s_x * s_w1 / s_a1)
    q["m2"], q["s2"] = par_m_s(s_a1 * s_w2 / s_l)
    q["escala_logit"] = s_l

    # acurácia da versão inteira, com as mesmas contas do servidor
    xq = np.round(xte.astype(np.float64) * 127 / 255).astype(np.int64)
    acc1 = im2col_3x3_passo2(xq) @ q["w1"].astype(np.int64) + q["b1"]
    a1 = requantizar(acc1, q["m1"], q["s1"], 0, 127).reshape(len(xte), -1)
    logits = requantizar(a1.astype(np.int64) @ q["w2"].astype(np.int64) + q["b2"],
                         q["m2"], q["s2"], -128, 127)
    acc_q = (logits.argmax(1) == yte).mean()
    print(f"  acurácia int8: {acc_q:.2%}")

    PASTA_MODELOS.mkdir(exist_ok=True)
    np.savez(PASTA_MODELOS / "fashion_int8.npz", **q, acuracia_int8=acc_q)
    # amostras do conjunto de teste servidas por GET /amostra/fashion
    np.savez_compressed(PASTA_MODELOS / "fashion_amostras.npz",
                        imagens=xte[:2000], rotulos=yte[:2000])


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--epocas", type=int, default=15)
    args = ap.parse_args()
    print("Treinando Fashion-MNIST...")
    treinar(args.epocas, np.random.default_rng(42))
    print("Modelo salvo em", PASTA_MODELOS)
