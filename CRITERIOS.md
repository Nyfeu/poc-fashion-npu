# Critérios de aceitação

Escritos antes de pedir qualquer código ao agente. Cada um é conferido no
celular e ganha um commit quando passa.

## Responde à pergunta de pesquisa
- [ ] Com mais de 50 resultados na lista (tocando três vezes em "Rodar 20"),
      consigo rolar até o fim e voltar ao topo sem a rolagem travar e sem
      aparecerem espaços em branco no lugar dos itens.
- [ ] Enquanto o "Rodar 20" está adicionando resultados, a lista continua
      rolando normalmente.

## Ação principal
- [ ] Ao tocar em Sortear, a imagem da peça aparece no topo da tela com o
      nome da classe real.
- [ ] Ao tocar em Inferir, o resultado entra no topo da lista com a imagem,
      a classe prevista, a classe real e um ✓ verde (acerto) ou um ✗
      vermelho (erro).
- [ ] O placar "Acertos: X de Y" muda a cada novo resultado.
- [ ] Antes do primeiro resultado, a lista mostra "Nenhuma inferência ainda".
- [ ] O celular vibra uma vez quando chega o resultado de um Inferir, e uma
      vez só quando o "Rodar 20" termina (não vibra 20 vezes).

## Erro e entrada inválida
- [ ] O botão Inferir fica desabilitado antes do primeiro sorteio e depois
      que a peça já foi classificada.
- [ ] Com o servidor desligado, ao tocar em Sortear aparece "Servidor
      inacessível" em até 5 segundos, e os botões continuam respondendo.

## Fora do escopo
- O histórico não é salvo: ao fechar e abrir o app, a lista começa vazia.

**Verificado em:** ( ) aparelho físico ( ) emulador
**Resultado:** ( ) passou ( ) reprovou
