This is an Expo/React Native mobile application. Prioritize mobile-first patterns, performance, and cross-platform compatibility.

## Expo has changed — do not trust your training data

Expo ships breaking changes every SDK release. APIs you remember are likely renamed, moved, or removed. Before writing any code that touches an Expo, EAS, or React Native API:

1. Read the major version of the `expo` package in `package.json`.
2. Fetch the matching versioned docs: `https://docs.expo.dev/versions/v<major>.0.0/`
3. For anything else, fetch https://docs.expo.dev/llms.txt — an index of all Expo docs with corrections to common LLM misconceptions. Follow its links to the specific page you need; never answer from memory.

## Commands

Use `bunx` instead of `npx` if the project uses bun (`bun.lock` present).

```bash
npx expo install <package>  # ALWAYS use instead of npm/yarn/pnpm/bun add — resolves SDK-compatible versions
npx expo start              # start the dev server
npx expo lint               # lint
npx tsc --noEmit            # typecheck
npx expo-doctor             # diagnose dependency and config issues
npx expo install --fix      # fix incompatible package versions
```

Run lint and typecheck before declaring any task done.

## Navigation & Routing

- Use **Expo Router** for all navigation. Routes live in `src/app/` — every file there is a screen, `_layout.tsx` files define navigators. Keep non-route code (components, hooks, utils) outside `src/app/`.
- Import `Link`, `router`, and `useLocalSearchParams` from `expo-router`.
- Docs: https://docs.expo.dev/router/introduction.md

## Building with EAS

Use EAS to build, sign, and submit the app in the cloud (`eas build`, `eas submit`) and to ship over-the-air updates (`eas update`) — no local Xcode or Android Studio required. Run EAS CLI as `bunx eas-cli <command>` in Bun projects, or `npx eas-cli@latest <command>` otherwise; substitute that for bare `eas` in docs examples.
Docs: https://docs.expo.dev/eas/index.md

## Rules

- If `ios/` and `android/` directories do not exist, they are generated (Continuous Native Generation). Never create or edit them by hand — configure native behavior in `app.json` and config plugins.
- Expo Go only includes its bundled native modules. After adding a library with native code, the app needs a development build: `npx expo run:ios|android` locally, or `eas build --profile development`.
- Prefer recommended Expo modules over third-party libraries, and check your available skills before adding dependencies. Docs: https://docs.expo.dev/versions/latest/index.md

## Convenções deste projeto

- Não altere arquivos fora do escopo pedido. Explique cada alteração.
- Componentes ficam em `components/`, um arquivo por componente.
- Estado nunca é modificado no lugar: sempre gere um novo valor.
- Valores que podem ser calculados a partir do estado não viram estado.
- Antes de usar um pacote, confirme na documentação se ele funciona no Expo Go.

## Contexto desta prova de conceito

- TCC: processador RISC-V em FPGA com uma NPU que executa redes neurais; esta
  PoC usa uma segunda rede (Fashion-MNIST) para mostrar que a NPU serve para
  mais de uma aplicação.
- Problema: na tela do computador, cada resultado substitui o anterior; quem
  acompanha a demonstração não vê o histórico nem os padrões de erro.
- Tecnologia investigada: FlatList do React Native.
- Uma tela só, em `App.tsx`: botão Sortear mostra uma peça de roupa; botão
  Inferir classifica e coloca o resultado no topo de uma lista (imagem,
  classe prevista, classe real, acerto ou erro); placar "Acertos: X de Y";
  botão "Rodar 20" sorteia e infere 20 peças em sequência.
- Vibração com expo-haptics: uma vez a cada Inferir manual e uma vez só ao
  fim do "Rodar 20".
- Servidor já existe e roda no computador. O endereço fica numa constante no
  topo do App.tsx (IP do computador na rede, nunca localhost).
    - GET /amostra/fashion → { id, pixels (784 números de 0 a 255),
    imagem_png (imagem pronta em data URI, para o componente Image),
    classe_real, rotulo_real }
  - POST /inferir/fashion com { pixels } → { classe, rotulo, confianca, ... }
- Não usar Expo Router: esta PoC tem uma tela só, em `App.tsx`. Ignore a
  seção "Navigation & Routing" acima e não crie a pasta `src/app/`.
- Fora de escopo: login, salvar o histórico, design final e tudo que não
  demonstre a pergunta.