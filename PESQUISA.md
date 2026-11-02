# Diário de pesquisa

## Contexto do TCC
Desenvolvemos um processador RISC-V em FPGA com uma NPU, um circuito que
acelera redes neurais. Até agora ela foi demonstrada só reconhecendo dígitos
(MNIST). Nesta prova de conceito, usamos uma segunda rede, que reconhece
peças de roupa (Fashion-MNIST), para mostrar que a mesma NPU serve para mais
de uma aplicação.

## Problema
Hoje cada resultado substitui o anterior na tela do computador. Quem
acompanha a demonstração não vê o histórico e não percebe onde a rede erra
com mais frequência (por exemplo, confundir camisa com camiseta).

## Pergunta de pesquisa
**Inicial:** Como mostrar no celular um histórico de resultados que cresce a
cada nova inferência, sem travar a rolagem com mais de 50 itens?

**Refinada (depois do mapa com as IAs e da documentação):** A FlatList do
React Native é suficiente para mostrar esse histórico, na condição de os
resultados chegarem um a um pela rede e a lista passar de 50 itens, ou é
preciso partir para a FlashList?

## O que as IAs disseram (mesmo pedido no Gemini e no ChatGPT)
- **Gemini:** recomendou a FlashList, uma biblioteca da Shopify.
- **ChatGPT:** recomendou a FlatList, que já vem no React Native, e disse que
  50 itens é pouco para ela.

**Onde discordaram e o que conferi na documentação:**
- Qual usar: a documentação não decide; depende de testar. Decidi testar a
  FlatList com mais de 50 itens no celular.
- O Gemini deu informações desatualizadas sobre a FlashList (descrevia a
  versão antiga) e atribuiu a ela uma configuração que, na verdade, é de
  outra biblioteca.
- Nenhuma das duas disse se as opções funcionam no Expo Go. Conferi: todas
  as que considerei funcionam.

## Alternativas consideradas
| Opção | Para que serve | Funciona no Expo Go? | Decisão |
|---|---|---|---|
| ScrollView | Listas pequenas | Sim | Não: desenha todos os itens de uma vez |
| FlatList | Listas longas | Sim | **Sim**: já vem no React Native e foi vista em aula |
| FlashList | Listas muito longas | Sim | Plano B, se a FlatList travar |

## Decisões de implementação
- **Imagem pronta do servidor:** cada peça chega em PNG, já ampliada, e é
  mostrada com um `Image` comum. Desenhar 784 quadradinhos por item deixaria
  a lista pesada por causa do desenho, e o teste deixaria de medir a FlatList.
- **Botão "Rodar 20":** sorteia e infere 20 peças em sequência. Serve para
  chegar a mais de 50 itens sem tocar 100 vezes na tela e para testar a lista
  enquanto os resultados chegam pela rede, que é a condição da pergunta.
- **Construção em etapas:** um pedido pequeno ao agente por vez, com o diff
  lido antes de aceitar, teste no celular e um commit por etapa.

## Fontes oficiais lidas
- FlatList: https://reactnative.dev/docs/flatlist
- ScrollView: https://reactnative.dev/docs/scrollview
- Como deixar a FlatList rápida: https://reactnative.dev/docs/optimizing-flatlist-configuration
- FlashList no Expo: https://docs.expo.dev/versions/latest/sdk/flash-list
- Mudanças da FlashList v2: https://shopify.github.io/flash-list/docs/v2-migration
- expo-image: https://docs.expo.dev/versions/latest/sdk/image
- expo-haptics: https://docs.expo.dev/versions/v58.0.0/sdk/haptics/

## Onde a IA errou
| O que pedi | O que veio | Como percebi | O que era o certo |
|---|---|---|---|
| Opções de lista (Gemini) | Disse que a FlashList precisa de tamanho fixo dos itens | Li a página de mudanças da versão 2 | Isso só valia na versão antiga |
| Opções de lista (Gemini) | Citou uma configuração (recyclingKey) como sendo da FlashList | Procurei na documentação | É do expo-image, outra biblioteca |
| Etapa 2 do app, sem mexer em pacotes (agente) | Mexeu no package.json duas vezes: o ESLint entrou (pelo `expo lint` que o AGENTS.md manda rodar) e depois ele tentou removê-lo | Lendo o diff antes de aceitar | Manter o ESLint e não mexer no package.json; recusei a remoção |
| Montar a tela do app (agente) | Omissão: a tela foi feita sem respeitar a área segura do Android, e a lista ficava atrás dos botões de navegação do sistema | Testando no celular, não na resposta do chat | Usar o SafeAreaView do react-native-safe-area-context; corrigido no exercício 9 |

## Resultado
Testei no celular ([modelo do seu celular], Android), pelo Expo Go em modo
de desenvolvimento, que é mais lento que o app final. Com 60 resultados na
lista, incluindo rolar enquanto novos resultados chegavam pelo "Rodar 20",
a FlatList rolou até o fim e voltou ao topo sem travar e sem espaços em
branco.

**Resposta à pergunta:** para o tamanho de uma demonstração, a FlatList é
suficiente; não foi preciso trocar pela FlashList.

**Observação do teste:** a lista ficava atrás dos botões de navegação do
Android. Não era um problema da FlatList, e sim da área segura da tela;
corrigido no exercício 9.

## Próximos passos no TCC
- Usar o app nas demonstrações e na banca, para mostrar a NPU com mais de
  uma rede.
