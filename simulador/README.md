# Simulador da PoC: Fashion-MNIST na NPU

Funciona em dois modos: **emulação** (padrão, sem placa) ou **placa**
(`--placa`, com a FPGA de verdade). Veja "Ligando na placa de verdade".

Duas peças para ver como o app vai funcionar antes de escrevê-lo em React Native:

- `servidor/`: faz o papel do computador ligado à placa. Entrega peças
  aleatórias do conjunto de teste, roda a rede numa **emulação int8 da NPU**
  e devolve o resultado. O tempo de resposta imita o da placa (UART a
  921.600 bit/s + 1.506 ciclos a 100 MHz ≈ 9,1 ms).
- `app/app_celular.py`: uma janela com as proporções de um celular
  (390 × 844 pontos) e a mesma tela, a mesma lógica de estado e as mesmas
  chamadas de rede que o app Expo terá. Os comentários `RN:` no código dizem
  qual peça do React Native faz cada papel.

## Como rodar

Precisa de Python 3.10 ou mais novo.

```bash
pip install -r requirements.txt

# terminal 1
cd servidor
python servidor.py

# terminal 2
cd app
python app_celular.py
```

No app: **Sortear** busca uma peça, **Inferir** manda para a "placa", e o
resultado entra no topo da lista (verde se acertou, vermelho se errou), com o
placar de acertos acima.

| Comando | Para quê |
|---|---|
| `python servidor.py --atraso 1500` | Cada inferência 1,5 s mais lenta, para ver o "Inferindo..." |
| `python servidor.py --falha 0.3` | 30% das inferências respondem "a placa não respondeu" (503) |
| `python app_celular.py --escala 0.8` | Janela menor |
| `python app_celular.py --servidor http://192.168.0.10:5000` | Servidor em outra máquina |

Para ver a mensagem de "hospedeiro inacessível", feche o servidor com o app
aberto e toque em Sortear.

O modelo já vem treinado em `servidor/modelos/` (~87% de acerto em int8, no formato da placa).
Para treinar de novo (baixa os dados, só usa numpy, cerca de 30 s):

```bash
cd servidor
python treinar.py
```

## Contrato da API (o que o app Expo vai chamar)

No celular, use o IP do computador que o servidor mostra ao iniciar,
**nunca `localhost`** (no celular, `localhost` é o próprio celular).

**`GET /amostra/fashion`**
```json
{ "id": 1206, "pixels": [0, 0, 12, ...], "imagem_png": "data:image/png;base64,iVBOR...",
  "imagem_estilo": "data:image/png;base64,iVBOR...",
  "classe_real": 9, "rotulo_real": "Bota" }
```
`pixels` são 784 inteiros de 0 a 255, linha por linha (28 × 28): é o que vai
para a NPU. `imagem_png` é a mesma imagem já ampliada para 112 × 112, pronta
para mostrar no app com `<Image source={{ uri: imagem_png }} />`, sem precisar
desenhar 784 quadradinhos por item da lista. `imagem_estilo` é a mesma peça no
estilo da apresentação: 224 × 224 px, cada pixel um quadradinho azul sobre uma
grade escura.

**`POST /inferir/fashion`**, com corpo `{ "pixels": [...784...] }`
```json
{
  "classe": 9, "rotulo": "Bota", "confianca": 0.97,
  "probabilidades": [...10...], "rotulos": [...10...], "logits": [...10...],
  "ciclos": 1506, "tempo_npu_us": 15.06, "tempo_serial_ms": 8.62,
  "tempo_placa_ms": 9.13, "origem": "emulacao"
}
```

**`GET /status`**: confere se o servidor está no ar.

**Erros**

| Código | Quando | O que o app mostra |
|---|---|---|
| 400 | Imagem vazia, tamanho errado, valor fora de 0–255 | A mensagem do campo `erro` |
| 503 | A placa não respondeu (`--falha`) | "A placa não respondeu. Tente de novo." |
| sem resposta em 5 s | Servidor desligado, IP errado, sem Wi-Fi | "Hospedeiro inacessível..." |

`fetch` não tem opção de timeout: no app Expo, use `AbortController` com
`setTimeout`.

## Ligando na placa de verdade

O servidor tem dois modos, com **os mesmos pesos int8**:

| Modo | Comando | De onde vem a resposta |
|---|---|---|
| Emulação (padrão) | `python servidor.py` | A conta da NPU feita no computador |
| Placa | `python servidor.py --placa /dev/ttyUSB1` | A NPU na FPGA, pela UART |
| Placa, gravando o firmware antes | `python servidor.py --placa /dev/ttyUSB1 --gravar` | Idem, depois de gravar o `cnn_server` |

Com `--gravar`, o servidor primeiro grava o firmware `servidor/firmware/cnn_server.bin`
na placa, com o mesmo protocolo do `upload.py`: reset pelo debug controller
(RTS em baixo, `0xCAFEBABE`, boot em `0x00000000`, reset halt), espera o
`BOOT` do bootloader, manda `0xCAFEBABE` (resposta `!`), o tamanho e o programa
em blocos de 64 bytes, e espera o `>`. Para gravar outro arquivo:
`--gravar caminho/do/programa.bin`. O bitstream do SoC (o hardware) já precisa
estar na FPGA; o `--gravar` grava só o programa, e não usa o cartão microSD.

Em seguida (com ou sem `--gravar`), o servidor envia os pesos do Fashion-MNIST para a
NPU com o mesmo protocolo do `cnn_client.py` (comandos `0xAA`, `0xBB`, `0xCC`
e `0xDD`) e espera as confirmações `A`, `B`, `C` e `D`. Cada inferência usa
o comando `0xFF`. A FPGA precisa estar com o bitstream e o firmware
`cnn_server.c` carregados.

```bash
# o mais completo: grava, carrega os pesos e confere 200 imagens antes de servir
python servidor.py --placa /dev/ttyUSB1 --gravar --verificar 200
```

A verificação mostra a acurácia na placa e na emulação, quantas imagens deram
a mesma classe e quantas deram exatamente os mesmos logits.

Detalhes:
- **Porta:** no Linux, algo como `/dev/ttyUSB1` (o mesmo do `cnn_client.py`);
  no Windows, `COM4` e afins. Sem permissão no Linux: `sudo usermod -aG dialout $USER`
  e entre de novo na sessão.
- **Os LEDs e o display de 7 segmentos** mostram o número da classe prevista
  (0 = Camiseta, 1 = Calça, ..., 7 = Tênis, 9 = Bota), porque o firmware foi
  escrito para dígitos.
- **A placa guarda um modelo por vez:** depois de usar o servidor, a NPU fica
  com os pesos do Fashion-MNIST. Para voltar ao MNIST, rode o `cnn_client.py`.
- **Se a placa não responder em 2 s,** o servidor devolve 503 "a placa não
  respondeu", que o app já trata.
- Cada resposta no modo placa traz também `classe_emulacao` e
  `logits_emulacao`, e o `GET /status` conta quantas vezes placa e emulação
  discordaram.

### Testar o modo placa sem a FPGA (Linux)

`testes/firmware_falso.py` cria uma porta serial virtual que responde ao
mesmo protocolo do bootloader e do `cnn_server.c`, calculando a rede com laços
diretos (a porta virtual não tem RTS; o servidor avisa e segue):

```bash
python testes/firmware_falso.py          # mostra algo como /dev/pts/3
python servidor/servidor.py --placa /dev/pts/3 --gravar --verificar 40
```

Para simular a placa travando depois de 5 inferências:
`python testes/firmware_falso.py 5`.

### Como os pesos foram quantizados

`treinar.py` usa o mesmo esquema do `cnn_client.py`: entrada `pixel // 2`
(0 a 127), pesos em int8 com as escalas "seguras" que mantêm cada camada
abaixo de 120, e a NPU dividindo o acumulador por 256 (`>> 8`) na saída de
cada camada. A emulação faz exatamente essa conta. O arredondamento e a
saturação exatos do hardware não estão no firmware; a emulação desloca para
baixo e satura. Se o `--verificar` mostrar logits diferentes na placa, é
aí que está a diferença.

## Limites

- A emulação reproduz a conta do firmware, mas **não é** o emulador bit a bit
  do grupo. Use `--verificar` com a placa para conferir.
- O número de ciclos (1.506) é o medido na placa para essa arquitetura
  (conv 3×3/2 com 4 filtros + densa 676→10), que é a mesma do MNIST. No modo
  placa, o `tempo_placa_ms` é medido de verdade (ida e volta pela UART).
- As imagens vêm do conjunto de teste, então a acurácia que aparece no
  placar tende aos ~87% da rede. Fotos reais de roupas ficariam bem abaixo
  disso.
