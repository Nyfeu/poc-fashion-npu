"""
Simulador de celular em Tkinter: mostra como ficaria o app Expo do
Fashion-MNIST, com as mesmas proporções (tela de 390 x 844 pontos, como um
iPhone comum) e a mesma lógica de estado e de rede do app em React Native.

    python app_celular.py                                  # servidor em localhost:5000
    python app_celular.py --servidor http://192.168.0.10:5000
    python app_celular.py --escala 0.8

Só usa a biblioteca padrão do Python. Os comentários "RN:" dizem qual peça
do React Native faz o mesmo papel em cada trecho.
"""

from __future__ import annotations

import argparse
import json
import queue
import threading
import time
import tkinter as tk
import urllib.error
import urllib.request

# --- Tema (RN: um objeto de cores usado no StyleSheet) --------------------
COR = {
    "fundo": "#F2F2F7", "cartao": "#FFFFFF", "texto": "#111827", "suave": "#6B7280",
    "primaria": "#2563EB", "primaria_off": "#A5B4FC", "secundaria": "#E5E7EB",
    "verde": "#16A34A", "vermelho": "#DC2626", "vermelho_claro": "#FEE2E2",
    "borda": "#E5E7EB",
}
LARGURA_PT, ALTURA_PT = 390, 844     # tamanho lógico da tela do celular
TIMEOUT_S = 5                        # RN: AbortController + setTimeout(5000)

ESCALA = 1.0


def px(pontos: float) -> int:
    """Converte pontos do celular em pixels da janela."""
    return max(1, int(round(pontos * ESCALA)))


def fonte(tamanho: int, peso: str = "normal"):
    return ("Helvetica", -px(tamanho), peso)


# --- Rede (RN: fetch) -----------------------------------------------------

class Api:
    """Faz as requisições numa thread e entrega o resultado na thread da tela,
    como o `await fetch(...)` faz no React Native: a tela não trava esperando."""

    def __init__(self, raiz: tk.Tk, base: str):
        self.raiz, self.base = raiz, base.rstrip("/")
        self.fila: queue.Queue = queue.Queue()
        self._ouvir()

    def _ouvir(self):
        while not self.fila.empty():
            callback, resultado = self.fila.get()
            callback(resultado)
        self.raiz.after(30, self._ouvir)

    def requisitar(self, metodo: str, caminho: str, corpo, ao_terminar):
        def trabalho():
            inicio = time.perf_counter()
            try:
                dados = json.dumps(corpo).encode() if corpo is not None else None
                req = urllib.request.Request(self.base + caminho, data=dados, method=metodo,
                                             headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=TIMEOUT_S) as r:
                    resp = {"ok": True, "dados": json.loads(r.read())}
            except urllib.error.HTTPError as e:   # o servidor respondeu com erro
                try:
                    msg = json.loads(e.read()).get("erro", "")
                except Exception:
                    msg = ""
                if e.code == 503:
                    msg = "A placa não respondeu. Tente de novo."
                resp = {"ok": False, "erro": msg or f"Erro {e.code} no servidor."}
            except Exception:                       # sem rede, servidor fora, timeout
                resp = {"ok": False,
                        "erro": "Hospedeiro inacessível. Confira se o servidor está "
                                "rodando e se o endereço está certo."}
            resp["ida_e_volta_ms"] = (time.perf_counter() - inicio) * 1000
            self.fila.put((ao_terminar, resp))

        threading.Thread(target=trabalho, daemon=True).start()


# --- Componentes (RN: Pressable, Image) -----------------------------------

class Botao(tk.Label):
    """RN: <Pressable disabled={...}>"""

    def __init__(self, pai, texto, ao_tocar, tipo="primaria"):
        super().__init__(pai, text=texto, font=fonte(16, "bold"), pady=px(12), cursor="hand2")
        self.ao_tocar, self.tipo, self.habilitado = ao_tocar, tipo, True
        self.bind("<Button-1>", lambda _e: self.habilitado and self.ao_tocar())
        self.definir(True)

    def definir(self, habilitado: bool, texto: str | None = None):
        self.habilitado = habilitado
        if texto:
            self.config(text=texto)
        if self.tipo == "primaria":
            self.config(bg=COR["primaria"] if habilitado else COR["primaria_off"], fg="white")
        else:
            self.config(bg=COR["secundaria"], fg=COR["texto"] if habilitado else COR["suave"])
        self.config(cursor="hand2" if habilitado else "arrow")


def imagem_28(pai, pixels: list[int], lado_pt: int) -> tk.PhotoImage:
    """784 pixels -> imagem ampliada. RN: uma grade 28x28 de <View>s, ou um <Image>
    gerado no servidor."""
    img = tk.PhotoImage(master=pai, width=28, height=28)
    linhas = []
    for y in range(28):
        linha = " ".join(f"#{v:02x}{v:02x}{v:02x}" for v in pixels[y * 28:(y + 1) * 28])
        linhas.append("{" + linha + "}")
    img.put(" ".join(linhas))
    return img.zoom(max(1, px(lado_pt) // 28))


# --- A tela ---------------------------------------------------------------

class TelaFashion(tk.Frame):
    """Sortear uma peça, inferir e acumular os resultados numa lista.

    RN, em resumo:
      const [amostra, setAmostra] = useState(null);
      const [jaInferida, setJaInferida] = useState(false);
      const [carregando, setCarregando] = useState(false);
      const [historico, setHistorico] = useState([]);
      const [erro, setErro] = useState(null);
      const acertos = historico.filter(h => h.acertou).length;   // estado derivado
      <FlatList data={historico} keyExtractor={h => h.chave}
                renderItem={...} ListEmptyComponent={...} />
    """

    def __init__(self, pai, api: Api):
        super().__init__(pai, bg=COR["fundo"])
        self.api = api
        self.estado = {"amostra": None, "ja_inferida": False, "carregando": False,
                       "historico": [], "erro": None}
        self.imagens: list = []

        tk.Label(self, text="Fashion-MNIST na NPU", font=fonte(24, "bold"), bg=COR["fundo"],
                 fg=COR["texto"], anchor="w").pack(fill="x", padx=px(20), pady=(px(12), 0))
        tk.Label(self, text="Sorteie uma peça do conjunto de teste e veja se a rede acerta.",
                 font=fonte(13), bg=COR["fundo"], fg=COR["suave"], anchor="w", justify="left",
                 wraplength=px(350)).pack(fill="x", padx=px(20), pady=(px(2), px(10)))

        # cartão da peça sorteada
        self.atual = tk.Frame(self, bg=COR["cartao"], highlightthickness=1,
                              highlightbackground=COR["borda"], height=px(138))
        self.atual.pack(fill="x", padx=px(20))
        self.atual.pack_propagate(False)

        # botões
        linha = tk.Frame(self, bg=COR["fundo"])
        linha.pack(fill="x", padx=px(20), pady=px(12))
        linha.columnconfigure(0, weight=1, uniform="b")
        linha.columnconfigure(1, weight=1, uniform="b")
        self.b_sortear = Botao(linha, "Sortear", self.sortear, "secundaria")
        self.b_sortear.grid(row=0, column=0, sticky="ew", padx=(0, px(6)))
        self.b_inferir = Botao(linha, "Inferir", self.inferir)
        self.b_inferir.grid(row=0, column=1, sticky="ew", padx=(px(6), 0))

        # placar e aviso de erro
        self.placar = tk.Label(self, font=fonte(15, "bold"), bg=COR["fundo"], fg=COR["texto"],
                               anchor="w")
        self.placar.pack(fill="x", padx=px(20))
        self.aviso = tk.Frame(self, bg=COR["fundo"])
        self.aviso.pack(fill="x", padx=px(20))

        # lista rolável (RN: FlatList)
        moldura = tk.Frame(self, bg=COR["fundo"])
        moldura.pack(fill="both", expand=True, padx=px(20), pady=(px(6), px(20)))
        self.rolagem = tk.Canvas(moldura, bg=COR["fundo"], highlightthickness=0)
        self.rolagem.pack(fill="both", expand=True)
        self.lista = tk.Frame(self.rolagem, bg=COR["fundo"])
        self.janela_lista = self.rolagem.create_window(0, 0, window=self.lista, anchor="nw")
        self.lista.bind("<Configure>", lambda _e: self.rolagem.configure(
            scrollregion=self.rolagem.bbox("all")))
        self.rolagem.bind("<Configure>", lambda e: self.rolagem.itemconfig(
            self.janela_lista, width=e.width))
        for ev in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            self.rolagem.bind_all(ev, self.rolar, add="+")
        self.render()

    def set_estado(self, **mudancas):
        """RN: os setters do useState. Mudou o estado, a tela se redesenha."""
        self.estado.update(mudancas)
        self.render()

    def rolar(self, e):
        passo = -1 if (getattr(e, "num", 0) == 4 or getattr(e, "delta", 0) > 0) else 1
        self.rolagem.yview_scroll(passo, "units")

    # --- ações ---

    def sortear(self):
        self.set_estado(carregando=True, erro=None)
        self.api.requisitar("GET", "/amostra/fashion", None, self.ao_sortear)

    def ao_sortear(self, r):
        if r["ok"]:
            self.set_estado(carregando=False, amostra=r["dados"], ja_inferida=False)
        else:
            self.set_estado(carregando=False, erro=r["erro"])

    def inferir(self):
        if self.estado["amostra"] is None:      # o botão já fica desabilitado; isto é só garantia
            return
        self.set_estado(carregando=True, erro=None)
        self.api.requisitar("POST", "/inferir/fashion",
                            {"pixels": self.estado["amostra"]["pixels"]}, self.ao_inferir)

    def ao_inferir(self, r):
        if not r["ok"]:
            return self.set_estado(carregando=False, erro=r["erro"])
        a, d = self.estado["amostra"], r["dados"]
        item = {"chave": f"{a['id']}-{len(self.estado['historico'])}",   # keyExtractor
                "pixels": a["pixels"], "real": a["rotulo_real"], "prevista": d["rotulo"],
                "confianca": d["confianca"], "acertou": d["classe"] == a["classe_real"],
                "ms": r["ida_e_volta_ms"]}
        # nunca altera a lista no lugar: cria uma nova (mesma regra do AGENTS.md)
        self.set_estado(carregando=False, ja_inferida=True,
                        historico=[item] + self.estado["historico"])

    # --- desenho a partir do estado ---

    def render(self):
        e = self.estado
        hist = e["historico"]
        acertos = sum(1 for h in hist if h["acertou"])        # estado derivado

        self.b_sortear.definir(not e["carregando"])
        self.b_inferir.definir(e["amostra"] is not None and not e["ja_inferida"]
                               and not e["carregando"],
                               "Inferindo..." if e["carregando"] and e["amostra"] else "Inferir")
        self.placar.config(text=f"Acertos: {acertos} de {len(hist)}"
                                + (f"  ({acertos / len(hist):.0%})" if hist else ""))

        for w in self.aviso.winfo_children():
            w.destroy()
        if e["erro"]:
            tk.Label(self.aviso, text="⚠  " + e["erro"], font=fonte(14),
                     bg=COR["vermelho_claro"], fg=COR["vermelho"], wraplength=px(320),
                     justify="left", anchor="w").pack(fill="x", pady=(px(6), 0), ipadx=px(12),
                                                      ipady=px(10))

        self.render_atual()
        self.render_lista()

    def render_atual(self):
        e = self.estado
        q = self.atual
        for w in q.winfo_children():
            w.destroy()
        a = e["amostra"]
        if not a:
            tk.Label(q, text="Toque em Sortear para escolher uma peça.", font=fonte(14),
                     bg=COR["cartao"], fg=COR["suave"]).pack(expand=True)
            return
        self._img_atual = imagem_28(self, a["pixels"], 112)
        tk.Label(q, image=self._img_atual, bd=0).pack(side="left", padx=px(12))
        info = tk.Frame(q, bg=COR["cartao"])
        info.pack(side="left", fill="y", pady=px(14))
        tk.Label(info, text=f"Amostra #{a['id']}", font=fonte(13), bg=COR["cartao"],
                 fg=COR["suave"]).pack(anchor="w")
        tk.Label(info, text=a["rotulo_real"], font=fonte(22, "bold"), bg=COR["cartao"],
                 fg=COR["texto"]).pack(anchor="w")
        tk.Label(info, text="classe real", font=fonte(12), bg=COR["cartao"],
                 fg=COR["suave"]).pack(anchor="w")
        if e["carregando"]:
            status = "enviando para a NPU..."
        elif e["ja_inferida"]:
            status = "já classificada: sorteie outra"
        else:
            status = "pronta para inferir"
        tk.Label(info, text=status, font=fonte(12), bg=COR["cartao"],
                 fg=COR["primaria"]).pack(anchor="w", pady=(px(10), 0))

    def render_lista(self):
        hist = self.estado["historico"]
        if getattr(self, "_tam_lista", None) == len(hist):
            return                                           # a lista não mudou
        self._tam_lista = len(hist)
        for w in self.lista.winfo_children():
            w.destroy()
        self.imagens.clear()
        if not hist:                                         # ListEmptyComponent
            tk.Label(self.lista, text="Nenhuma inferência ainda.", font=fonte(14),
                     bg=COR["fundo"], fg=COR["suave"]).pack(pady=px(24))
            return
        for h in hist:                                       # renderItem
            cor = COR["verde"] if h["acertou"] else COR["vermelho"]
            item = tk.Frame(self.lista, bg=COR["cartao"], highlightthickness=2,
                            highlightbackground=cor)
            item.pack(fill="x", pady=(0, px(6)))
            img = imagem_28(self, h["pixels"], 42)
            self.imagens.append(img)
            tk.Label(item, image=img, bd=0).pack(side="left", padx=px(8), pady=px(6))
            textos = tk.Frame(item, bg=COR["cartao"])
            textos.pack(side="left", fill="x", expand=True)
            tk.Label(textos, text=f"Prevista: {h['prevista']}  ·  {h['confianca']:.0%}",
                     font=fonte(14, "bold"), bg=COR["cartao"], fg=COR["texto"]).pack(anchor="w")
            tk.Label(textos, text=f"Real: {h['real']}  ·  {h['ms']:.0f} ms", font=fonte(13),
                     bg=COR["cartao"], fg=COR["suave"]).pack(anchor="w")
            tk.Label(item, text="✓" if h["acertou"] else "✗", font=fonte(22, "bold"),
                     bg=COR["cartao"], fg=cor).pack(side="right", padx=px(12))
        self.rolagem.yview_moveto(0)


# --- Moldura do celular ---------------------------------------------------

class Celular(tk.Tk):
    def __init__(self, servidor: str):
        super().__init__()
        self.title("Simulador do app — Fashion-MNIST na NPU")
        self.configure(bg=COR["fundo"])
        self.geometry(f"{px(LARGURA_PT)}x{px(ALTURA_PT)}")
        self.resizable(False, False)

        barra = tk.Frame(self, bg=COR["fundo"], height=px(44))   # barra de status do sistema
        barra.pack(fill="x")
        barra.pack_propagate(False)
        self.relogio = tk.Label(barra, font=fonte(15, "bold"), bg=COR["fundo"], fg=COR["texto"])
        self.relogio.pack(side="left", padx=px(26))
        tk.Label(barra, text=servidor.replace("http://", ""), font=fonte(11), bg=COR["fundo"],
                 fg=COR["suave"]).pack(side="right", padx=px(20))
        self._tique()

        self.tela = TelaFashion(self, Api(self, servidor))
        self.tela.pack(fill="both", expand=True)

    def _tique(self):
        self.relogio.config(text=time.strftime("%H:%M"))
        self.after(10_000, self._tique)


def main():
    global ESCALA
    ap = argparse.ArgumentParser(description="Simulador do app Fashion-MNIST na NPU")
    ap.add_argument("--servidor", default="http://localhost:5000")
    ap.add_argument("--escala", type=float, help="1.0 = 390x844 px (padrão: cabe na tela)")
    args = ap.parse_args()
    if args.escala:
        ESCALA = args.escala
    else:
        medidor = tk.Tk()
        medidor.withdraw()
        ESCALA = min(1.0, medidor.winfo_screenheight() * 0.88 / ALTURA_PT)
        medidor.destroy()
    Celular(args.servidor).mainloop()


if __name__ == "__main__":
    main()
