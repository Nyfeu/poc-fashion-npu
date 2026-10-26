"""
Emulação, só com inteiros, da inferência que a NPU faria na placa.

Não é o emulador bit a bit do grupo: é uma aproximação com o mesmo espírito
(int8 nas entradas e pesos, acumuladores int32, requantização por par (M, S)
com ReLU fundida), para o app ter algo realista do outro lado da rede.
Para usar a placa de verdade, troque a chamada a `inferir` em servidor.py
pela função do cnn_client do TCC (veja o README).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

PASTA_MODELOS = Path(__file__).parent / "modelos"

# --- Parâmetros da plataforma (dos artigos do TCC) -------------------------
FREQ_HZ = 100_000_000          # SoC a 100 MHz
BAUD = 921_600                 # UART a 921.600 bit/s
BITS_POR_BYTE = 10             # 8N1: start + 8 dados + stop
CICLOS_CNN_MEDIDOS = 1506      # conv 3x3/2 (4 filtros) + densa 676->10, medido na placa
SOBRECARGA_USB_MS = 0.5        # trânsito USB + firmware (artigo: ~0,5 ms)

CLASSES = ["Camiseta", "Calça", "Suéter", "Vestido", "Casaco",
           "Sandália", "Camisa", "Tênis", "Bolsa", "Bota"]


def par_m_s(escala_real: float, bits_m: int = 15) -> tuple[int, int]:
    """Converte uma escala real em (M, S) tal que escala ~= M / 2**S."""
    if escala_real <= 0:
        raise ValueError("escala precisa ser positiva")
    s = 0
    while escala_real * (1 << s) < (1 << (bits_m - 1)) and s < 62:
        s += 1
    return int(round(escala_real * (1 << s))), s


def requantizar(acc: np.ndarray, m: int, s: int, lo: int, hi: int) -> np.ndarray:
    """(acc * M) >> S com arredondamento, saturado em [lo, hi]."""
    acc = acc.astype(np.int64)
    arred = 1 << (s - 1) if s > 0 else 0
    return np.clip((acc * m + arred) >> s, lo, hi).astype(np.int32)


def im2col_3x3_passo2(img: np.ndarray) -> np.ndarray:
    """(N, 28, 28) -> (N, 169, 9): as janelas 3x3 da convolução com passo 2."""
    n = img.shape[0]
    saida = np.empty((n, 13, 13, 9), dtype=img.dtype)
    k = 0
    for dy in range(3):
        for dx in range(3):
            saida[:, :, :, k] = img[:, dy:dy + 25:2, dx:dx + 25:2]
            k += 1
    return saida.reshape(n, 169, 9)


@dataclass
class ResultadoNPU:
    classe: int
    logits: list[int]
    probabilidades: list[float]
    ciclos: int = CICLOS_CNN_MEDIDOS
    bytes_enviados: int = 784
    bytes_recebidos: int = 10

    @property
    def tempo_npu_us(self) -> float:
        return self.ciclos / FREQ_HZ * 1e6

    @property
    def tempo_serial_ms(self) -> float:
        return (self.bytes_enviados + self.bytes_recebidos) * BITS_POR_BYTE / BAUD * 1000

    @property
    def tempo_placa_ms(self) -> float:
        return self.tempo_serial_ms + SOBRECARGA_USB_MS + self.tempo_npu_us / 1000


class ModeloCNN:
    """conv 3x3/2 (4 filtros) + ReLU + densa 676 -> 10, tudo em inteiros."""

    def __init__(self, caminho: Path = PASTA_MODELOS / "fashion_int8.npz"):
        d = np.load(caminho)
        self.w1 = d["w1"].astype(np.int64)      # (9, 4)    int8
        self.b1 = d["b1"].astype(np.int64)      # (4,)      int32
        self.m1, self.s1 = int(d["m1"]), int(d["s1"])
        self.w2 = d["w2"].astype(np.int64)      # (676, 10) int8
        self.b2 = d["b2"].astype(np.int64)      # (10,)     int32
        self.m2, self.s2 = int(d["m2"]), int(d["s2"])
        self.escala_logit = float(d["escala_logit"])

    def inferir(self, pixels_u8: np.ndarray) -> ResultadoNPU:
        x = np.round(pixels_u8.reshape(1, 28, 28).astype(np.float64) * 127 / 255)
        janelas = im2col_3x3_passo2(x.astype(np.int64))           # 0..127, (1, 169, 9)
        acc1 = janelas[0] @ self.w1 + self.b1                      # (169, 4) int32
        a1 = requantizar(acc1, self.m1, self.s1, 0, 127)           # ReLU fundida
        acc2 = a1.reshape(-1).astype(np.int64) @ self.w2 + self.b2
        logits = requantizar(acc2, self.m2, self.s2, -128, 127)
        # O softmax não roda na NPU: o hospedeiro calcula só para mostrar a confiança.
        z = logits * self.escala_logit
        e = np.exp(z - z.max())
        probs = e / e.sum()
        return ResultadoNPU(classe=int(np.argmax(logits)), logits=logits.tolist(),
                            probabilidades=[round(float(p), 4) for p in probs])
