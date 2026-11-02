"""FPGA falsa: abre um pty e responde ao protocolo do bootloader (upload.py) e
do firmware cnn_server.c. A rede é calculada com laços diretos (sem im2col),
como referência independente.

    python testes/firmware_falso.py              # imprime a porta, ex. /dev/pts/3
    python testes/firmware_falso.py 5            # "trava" depois de 5 inferências
"""
import hashlib, os, pty, struct, sys, threading, time
import numpy as np

def ler(fd, n):
    buf = b""
    while len(buf) < n:
        buf += os.read(fd, n - len(buf))
    return buf

def desempacotar(palavras, saidas, entradas):
    blocos = len(palavras) // entradas
    w = np.zeros((blocos * 4, entradas), np.int64)
    for j in range(blocos):
        for k in range(entradas):
            p = int(palavras[j * entradas + k])
            for c in range(4):
                b = (p >> (8 * c)) & 0xFF
                w[4 * j + c, k] = b - 256 if b > 127 else b
    return w[:saidas]

def rede(x, wc, bc, wf, bf):
    img = np.frombuffer(x, np.int8).astype(np.int64).reshape(28, 28)
    y = np.zeros(676, np.int64)
    for oy in range(13):
        for ox in range(13):
            for f in range(4):
                acc = int(bc[f])
                for dy in range(3):
                    for dx in range(3):
                        acc += int(img[2 * oy + dy, 2 * ox + dx]) * int(wc[f, dy * 3 + dx])
                y[(oy * 13 + ox) * 4 + f] = min(max(acc >> 8, 0), 127)     # channels-last
    out = bytearray()
    for n in range(10):
        acc = int(bf[n]) + int(np.dot(y, wf[n]))
        out += struct.pack(">b", min(max(acc >> 8, -128), 127))
    return bytes(out)

def bootloader(fd):
    """Depois do reset pelo debug controller: anuncia BOOT, recebe o programa."""
    time.sleep(0.15)                       # o hospedeiro limpa o buffer antes de soltar o SoC
    os.write(fd, b"\r\nBOOT\r\n")
    assert ler(fd, 4) == b"\xCA\xFE\xBA\xBE", "bootloader: palavra mágica errada"
    os.write(fd, b"!")
    tamanho = struct.unpack("<I", ler(fd, 4))[0] & 0x7FFFFFFF
    programa = ler(fd, tamanho)
    print(f"[fpga falsa] programa recebido: {tamanho} bytes, sha256 "
          f"{hashlib.sha256(programa).hexdigest()[:16]}", flush=True)
    os.write(fd, b"....\r\n>")


def firmware(fd, silenciar_apos=None):
    wc = bc = wf = bf = None
    inferencias = 0
    while True:
        cmd = ler(fd, 1)[0]
        if cmd == 0xCA:                    # debug controller: CA FE BA BE, 09 + endereço, 08
            assert ler(fd, 3) == b"\xFE\xBA\xBE"
            assert ler(fd, 5)[0] == 0x09 and ler(fd, 1)[0] == 0x08
            print("[fpga falsa] reset pelo debug controller", flush=True)
            bootloader(fd)
            wc = bc = wf = bf = None       # o firmware novo começa sem pesos
            continue
        if cmd == 0xAA:
            wc = desempacotar(struct.unpack(">9I", ler(fd, 36)), 4, 9); os.write(fd, b"A")
        elif cmd == 0xBB:
            bc = struct.unpack(">4i", ler(fd, 16)); os.write(fd, b"B")
        elif cmd == 0xCC:
            wf = desempacotar(struct.unpack(">2028I", ler(fd, 8112)), 10, 676); os.write(fd, b"C")
        elif cmd == 0xDD:
            bf = struct.unpack(">12i", ler(fd, 48))[:10]; os.write(fd, b"D")
        elif cmd == 0xFF:
            x = ler(fd, 784)
            inferencias += 1
            if silenciar_apos is not None and inferencias > silenciar_apos:
                continue                     # simula a placa travada: não responde
            os.write(fd, rede(x, wc, bc, wf, bf))

if __name__ == "__main__":
    mestre, escravo = pty.openpty()
    import tty; tty.setraw(escravo)
    print(os.ttyname(escravo), flush=True)
    firmware(mestre, int(sys.argv[1]) if len(sys.argv) > 1 else None)
