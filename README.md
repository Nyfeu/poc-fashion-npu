# Fashion-MNIST na NPU — histórico de inferências com FlatList

Prova de conceito da disciplina **ECM963 — Desenvolvimento de Aplicativos
Híbridos** (Pesquisa aplicada com IA): um app em React Native + Expo que mostra
no celular o histórico de inferências de uma rede neural rodando na NPU do
nosso TCC.

O TCC é um processador RISC-V em FPGA (Nexys A7) com uma NPU, um circuito que
acelera redes neurais quantizadas em int8. Até então ela só tinha sido
demonstrada com o MNIST (dígitos). Esta PoC usa uma segunda rede, treinada no
**Fashion-MNIST** (peças de roupa), para mostrar que a mesma NPU serve para
mais de uma aplicação.

## Pergunta de pesquisa e resultado

> A **FlatList** do React Native é suficiente para mostrar esse histórico, na
> condição de os resultados chegarem um a um pela rede e a lista passar de 50
> itens, ou é preciso partir para a **FlashList**?

**A FlatList bastou.** Com 60 resultados, inclusive rolando enquanto novos
resultados chegavam, a lista rolou até o fim e voltou sem travar e sem espaços
em branco, no Expo Go em modo de desenvolvimento. Os detalhes estão em
[`PESQUISA.md`](PESQUISA.md).

## O que o app faz

- **Sortear:** busca uma peça aleatória do conjunto de teste e mostra a imagem
  com a classe real.
- **Inferir:** manda a peça para a NPU; o resultado entra no topo da lista,
  com a classe prevista, a confiança, a classe real e ✓ (acerto) ou ✗ (erro).
- **Rodar 20:** faz 20 rodadas seguidas, com um contador de progresso.
- **Placar:** "Acertos: X de Y", calculado a partir do histórico.
- **Erros tratados:** botões desabilitados quando não há o que fazer, limite de
  5 s por requisição, aviso de servidor inacessível e de placa sem resposta.
- **Vibração:** uma vez por inferência e uma vez ao fim do "Rodar 20".

## Como rodar

### 1. O servidor (o computador ligado à placa)

```bash
cd simulador
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cd servidor
python servidor.py                                   # emulação da NPU (sem placa)
python servidor.py --placa /dev/ttyUSB1 --gravar     # FPGA de verdade
```

Ao iniciar, o servidor mostra o endereço a usar no celular, como
`http://192.168.0.10:5000`. Os detalhes (modo placa, `--verificar`, testes sem
a FPGA) estão em [`simulador/README.md`](simulador/README.md).

### 2. O app

1. Coloque o endereço do servidor na constante `SERVIDOR`, no topo do
   `App.tsx`. Use o IP do computador, nunca `localhost`.
2. Com o celular e o computador na mesma rede Wi-Fi:

```bash
npm install
npx expo start
```

3. Abra o projeto no **Expo Go** (QR Code ou `exp://<ip>:8081`).

## Estrutura

```
App.tsx                      a tela da PoC (Sortear, Inferir, Rodar 20, lista)
components/ResultadoItem.tsx um item do histórico
PESQUISA.md                  diário de pesquisa: pergunta, alternativas, fontes, erros da IA
CRITERIOS.md                 critérios de aceitação, escritos antes de cada etapa
AGENTS.md                    contexto e regras para o agente de código
.github/copilot-instructions.md   como o Copilot deve responder
.vscode/mcp.json             servidor MCP do Expo
simulador/                   servidor da NPU (emulação e FPGA) e um simulador de tela em Tkinter
docs/                        apresentação
```

## Como foi construído

O app foi feito com o **GitHub Copilot em modo Agent**, conectado ao servidor
MCP do Expo, em etapas pequenas: para cada uma, os critérios foram escritos
antes em `CRITERIOS.md`, o diff foi lido antes de ser aceito, o resultado foi
testado no celular e cada etapa virou um commit.

| Etapa | O que entrou |
|---|---|
| 1 | Sortear e mostrar a peça |
| 2 | Inferir, FlatList e placar |
| 3 | Botões desabilitados e erros de rede |
| 4 | Rodar 20 e o teste com mais de 50 itens |
| 5 | Vibração |
| Exercício 9 | Área segura no Android |

Os erros que a IA cometeu, e como foram percebidos, estão na seção "Onde a IA
errou" do [`PESQUISA.md`](PESQUISA.md).

**Uso de IA fora do agente:** o servidor de apoio em `simulador/` (emulação da
NPU, gravação do firmware e comunicação com a FPGA) também foi gerado com IA,
e validado com uma placa simulada que segue o protocolo do firmware.

## Limites

- Na demonstração, a inferência é **emulada** no computador. O modo placa já
  existe no servidor, mas até agora só foi testado com uma placa simulada.
- A rede é pequena (uma convolução com 4 filtros e uma camada densa): acerta
  cerca de 87% no Fashion-MNIST.
- O histórico não é salvo: ao fechar o app, a lista começa vazia.
- No Android com navegação por botões, a barra do sistema fica clara; corrigir
  isso exige uma development build, fora do Expo Go.
