# Critérios de aceitação

Escreva o critério **antes** de acionar o agente. Depois de aplicar a
alteração, verifique no aplicativo rodando — não na resposta do chat — e
marque cada item.

Um critério bom fala do que se vê ou se mede, não da implementação. Ele não
diz `FlatList` nem `useState`; diz o que aparece na tela. E tem um jeito claro
de falhar: se nada nele pode reprovar, não é critério.

---

## Etapa 1 — sortear uma peça

- [x] Ao tocar em Sortear, a imagem da peça aparece no topo da tela com o
      nome da classe real.
- [x] A cada novo toque em Sortear, a imagem e o nome mudam.

**Verificado em:** (x) aparelho físico ( ) emulador
**Resultado:** (x) passou ( ) reprovou

---

## Etapa 2 — inferir e montar o histórico

- [x] Antes do primeiro resultado, a lista mostra "Nenhuma inferência ainda".
- [x] Ao tocar em Inferir, o resultado entra no topo da lista com a imagem,
      a classe prevista, a classe real e um ✓ verde (acerto) ou um ✗
      vermelho (erro).
- [x] O placar "Acertos: X de Y" muda a cada novo resultado.

**Verificado em:** (x) aparelho físico ( ) emulador
**Resultado:** (x) passou ( ) reprovou

---

## Etapa 3 — botões desabilitados e erros de rede

- [x] O botão Inferir fica desabilitado antes do primeiro sorteio e depois
      que a peça já foi classificada.
- [x] Com o servidor desligado, ao tocar em Sortear aparece "Servidor
      inacessível" e os botões continuam respondendo.
- [x] Com o servidor demorando mais de 5 segundos (`--atraso 7000`), aparece
      "Servidor inacessível" depois de 5 segundos.
- [x] Quando a placa não responde (`--falha 1`), aparece "A placa não
      respondeu. Tente de novo."

**Verificado em:** (x) aparelho físico ( ) emulador
**Resultado:** (x) passou ( ) reprovou

---

## Etapa 4 — Rodar 20 (responde à pergunta de pesquisa)

- [ ] Ao tocar em "Rodar 20", os resultados entram na lista um a um, o botão
      mostra o progresso e o placar atualiza a cada resultado.
- [ ] Enquanto o "Rodar 20" está adicionando resultados, a lista continua
      rolando normalmente.
- [ ] Com mais de 50 resultados na lista (três toques em "Rodar 20"), consigo
      rolar até o fim e voltar ao topo sem a rolagem travar e sem aparecerem
      espaços em branco no lugar dos itens.

**Verificado em:** ( ) aparelho físico ( ) emulador
**Resultado:** ( ) passou ( ) reprovou

Depois do teste, registre no `PESQUISA.md`, em "Resultado", o que você viu:
a FlatList bastou, ou foi preciso partir para a FlashList?

---

## Etapa 5 — retorno tátil

- [ ] O celular vibra uma vez quando chega o resultado de um Inferir.
- [ ] O celular vibra uma vez só quando o "Rodar 20" termina.
- [ ] Durante o "Rodar 20", o celular não vibra a cada resultado.

**Verificado em:** ( ) aparelho físico ( ) emulador
**Resultado:** ( ) passou ( ) reprovou

---

## Alteração pequena (exercício 9)

- [ ]
- [ ]

**Resultado:** ( ) passou ( ) reprovou

---

## Fora do escopo

- O histórico não é salvo: ao fechar e abrir o app, a lista começa vazia.

---

## Antes de aceitar cada diff

1. Quais arquivos mudaram? Algum que você não esperava?
2. Quantas linhas? Muito mais do que o pedido exige?
3. O pedido foi atendido sem ir além do que foi pedido?
4. Entrou alguma dependência nova? Com qual comando, em qual versão?
5. Você consegue explicar cada linha alterada?
6. O critério foi verificado no aplicativo rodando?