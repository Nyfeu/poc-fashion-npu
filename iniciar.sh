#!/usr/bin/env bash
# Sobe o servidor da NPU e o app (Expo) juntos. Ctrl+C encerra os dois.
#
#   ./iniciar.sh                                        # emulação da NPU
#   ./iniciar.sh --placa /dev/ttyUSB1                   # FPGA (firmware já gravado)
#   ./iniciar.sh --placa /dev/ttyUSB1 --gravar          # grava o cnn_server antes
#   ./iniciar.sh --placa /dev/ttyUSB1 --gravar --verificar 200
#
# Todas as opções são repassadas ao simulador/servidor/servidor.py.
# Variáveis opcionais: PORTA_SERVIDOR (padrão 5000), IP (força o IP anunciado).

set -euo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SIMULADOR="$RAIZ/simulador"
VENV="$SIMULADOR/.venv"
PORTA_SERVIDOR="${PORTA_SERVIDOR:-5000}"
LOG="$RAIZ/.servidor.log"

azul()     { printf '\033[96m%s\033[0m\n' "$*"; }
verde()    { printf '\033[92m%s\033[0m\n' "$*"; }
amarelo()  { printf '\033[93m%s\033[0m\n' "$*"; }
vermelho() { printf '\033[91m%s\033[0m\n' "$*" >&2; }

# --- Encerrar tudo ao sair (Ctrl+C, erro ou fim do Expo) --------------------
PID_SERVIDOR=""
encerrar() {
  if [[ -n "$PID_SERVIDOR" ]] && kill -0 "$PID_SERVIDOR" 2>/dev/null; then
    echo
    azul "Encerrando o servidor da NPU..."
    kill "$PID_SERVIDOR" 2>/dev/null || true
    wait "$PID_SERVIDOR" 2>/dev/null || true
  fi
}
trap encerrar EXIT INT TERM

# --- Pré-requisitos ---------------------------------------------------------
for cmd in python3 node npx curl; do
  if ! command -v "$cmd" >/dev/null; then
    vermelho "Falta o comando '$cmd'."
    [[ "$cmd" == curl ]] && vermelho "Instale com: sudo apt install curl"
    exit 1
  fi
done

# Porta serial: confere permissão antes de subir (erro comum no Linux)
args=("$@")
for ((i = 0; i < ${#args[@]}; i++)); do
  if [[ "${args[$i]}" == "--placa" && -n "${args[$((i + 1))]:-}" ]]; then
    serial="${args[$((i + 1))]}"
    if [[ ! -e "$serial" ]]; then
      vermelho "A porta $serial não existe. A placa está ligada no USB?"
      ls /dev/ttyUSB* /dev/ttyACM* 2>/dev/null | sed 's/^/  disponível: /' >&2 || true
      exit 1
    fi
    if [[ ! -w "$serial" ]]; then
      vermelho "Sem permissão para usar $serial."
      vermelho "Rode: sudo usermod -aG dialout \$USER   (e saia e entre de novo na sessão)"
      exit 1
    fi
  fi
done

# --- Python: ambiente virtual e dependências --------------------------------
if [[ ! -x "$VENV/bin/python" ]]; then
  azul "Criando o ambiente Python em simulador/.venv..."
  if ! python3 -m venv "$VENV" 2>/dev/null; then
    vermelho "Não consegui criar o ambiente virtual."
    vermelho "No Pop!_OS: sudo apt install python3-venv"
    exit 1
  fi
fi
if ! "$VENV/bin/python" -c "import numpy, flask, serial" 2>/dev/null; then
  azul "Instalando as dependências do servidor..."
  "$VENV/bin/pip" install -q -r "$SIMULADOR/requirements.txt"
fi

# --- App: dependências do Node ----------------------------------------------
if [[ ! -d "$RAIZ/node_modules" ]]; then
  azul "Instalando as dependências do app (npm install)..."
  (cd "$RAIZ" && npm install --silent)
fi

# --- IP do notebook na rede -------------------------------------------------
if [[ -z "${IP:-}" ]]; then
  IP="$(ip -4 route get 1.1.1.1 2>/dev/null | awk '{for (i = 1; i <= NF; i++) if ($i == "src") print $(i + 1)}' || true)"
  [[ -z "$IP" ]] && IP="$(hostname -I 2>/dev/null | awk '{print $1}' || true)"
fi
if [[ -z "$IP" ]]; then
  vermelho "Não encontrei o IP do notebook. Ele está conectado a uma rede?"
  exit 1
fi
export EXPO_PUBLIC_SERVIDOR="http://$IP:$PORTA_SERVIDOR"

# --- Servidor da NPU --------------------------------------------------------
if curl -s -o /dev/null --max-time 1 "http://localhost:$PORTA_SERVIDOR/status"; then
  vermelho "Já existe algo respondendo na porta $PORTA_SERVIDOR (outro servidor aberto?)."
  exit 1
fi

azul "Subindo o servidor da NPU ${*:+com: $*}"
(cd "$SIMULADOR/servidor" && exec "$VENV/bin/python" -u servidor.py --porta "$PORTA_SERVIDOR" "$@") \
  >"$LOG" 2>&1 &
PID_SERVIDOR=$!

# Espera responder. Com --gravar/--verificar, pode levar alguns segundos.
for _ in $(seq 1 120); do
  if ! kill -0 "$PID_SERVIDOR" 2>/dev/null; then
    vermelho "O servidor parou ao iniciar. Últimas linhas do log ($LOG):"
    tail -n 15 "$LOG" >&2
    PID_SERVIDOR=""
    exit 1
  fi
  if curl -s -o /dev/null --max-time 1 "http://localhost:$PORTA_SERVIDOR/status"; then
    break
  fi
  sleep 0.5
done
if ! curl -s -o /dev/null --max-time 1 "http://localhost:$PORTA_SERVIDOR/status"; then
  vermelho "O servidor não respondeu em 60 s. Veja o log: $LOG"
  exit 1
fi

# Mostra o que o servidor disse ao iniciar (gravação, verificação, modo)
grep -v -E "WARNING|Serving Flask|Debug mode|Running on|Press CTRL|\"GET |\"POST " "$LOG" | sed '/^\s*$/d' || true
verde "Servidor da NPU no ar: $EXPO_PUBLIC_SERVIDOR   (log: .servidor.log)"

# Firewall ativo bloquearia o celular
if systemctl is-active --quiet ufw 2>/dev/null; then
  amarelo "O firewall (ufw) está ativo. Se o celular não conectar:"
  amarelo "  sudo ufw allow $PORTA_SERVIDOR/tcp && sudo ufw allow 8081/tcp"
fi

# O app precisa ler o endereço da variável de ambiente
if ! grep -q "EXPO_PUBLIC_SERVIDOR" "$RAIZ/App.tsx" 2>/dev/null; then
  amarelo "Atenção: o App.tsx ainda tem o IP fixo e não lê EXPO_PUBLIC_SERVIDOR."
  amarelo "Ele vai usar o endereço que está no código, não $EXPO_PUBLIC_SERVIDOR."
fi

# --- Expo -------------------------------------------------------------------
echo
verde "No Expo Go, abra:  exp://$IP:8081"
if command -v qrencode >/dev/null; then
  qrencode -t ANSIUTF8 "exp://$IP:8081"
fi
azul "Subindo o Expo (Ctrl+C encerra o app e o servidor)..."
echo
cd "$RAIZ"
# --clear: o endereço do servidor entra no app na hora de montar o pacote;
# limpar o cache garante que um IP novo seja usado.
npx expo start --clear
