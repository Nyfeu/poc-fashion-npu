# Simulador da PoC: Fashion-MNIST na NPU

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

O modelo já vem treinado em `servidor/modelos/` (~87% de acerto em int8).
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

Em `servidor.py`, a linha marcada com `<- troque aqui pela placa de verdade`
chama a emulação. Troque-a pela função do `cnn_client` do TCC que envia a
imagem pela UART e lê os logits (com os pesos do Fashion-MNIST carregados na
placa), e mude `origem` para `"placa"`. O app não muda nada.

## Limites

- A emulação segue a mesma ideia da NPU (int8, acumulador int32,
  requantização por par (M, S), ReLU fundida), mas **não é** o emulador bit a
  bit do grupo. O número de ciclos é o medido na placa para essa arquitetura
  (conv 3×3/2 com 4 filtros + densa 676→10), que é a mesma do MNIST.
- As imagens vêm do conjunto de teste, então a acurácia que aparece no
  placar tende aos ~87% da rede. Fotos reais de roupas ficariam bem abaixo
  disso.
