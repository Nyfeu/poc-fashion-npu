import { StatusBar } from 'expo-status-bar';
import { useRef, useState } from 'react';
import {
  ActivityIndicator,
  FlatList,
  Image,
  Pressable,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import ResultadoItem, { type Resultado } from './components/ResultadoItem';

const SERVIDOR = 'http://192.168.68.94:5000';

type Amostra = {
  pixels: number[];
  imagem_png: string;
  classe_real: number;
  rotulo_real: string;
};

export default function App() {
  const [amostra, setAmostra] = useState<Amostra | null>(null);
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [historico, setHistorico] = useState<Resultado[]>([]);
  const proximoId = useRef(0);

  async function sortearAmostra() {
    setCarregando(true);
    setErro(null);

    try {
      const resposta = await fetch(`${SERVIDOR}/amostra/fashion`);
      if (!resposta.ok) {
        throw new Error(`O servidor respondeu com status ${resposta.status}.`);
      }

      const dados: unknown = await resposta.json();
      if (
        typeof dados !== 'object' ||
        dados === null ||
        !('imagem_png' in dados) ||
        typeof dados.imagem_png !== 'string' ||
        !('pixels' in dados) ||
        !Array.isArray(dados.pixels) ||
        !dados.pixels.every((pixel) => typeof pixel === 'number') ||
        !('classe_real' in dados) ||
        typeof dados.classe_real !== 'number' ||
        !('rotulo_real' in dados) ||
        typeof dados.rotulo_real !== 'string'
      ) {
        throw new Error('A resposta do servidor não contém os dados esperados da amostra.');
      }

      setAmostra({
        imagem_png: dados.imagem_png,
        pixels: dados.pixels,
        classe_real: dados.classe_real,
        rotulo_real: dados.rotulo_real,
      });
    } catch (causa) {
      setErro(causa instanceof Error ? causa.message : 'Não foi possível sortear uma amostra.');
    } finally {
      setCarregando(false);
    }
  }

  async function inferirAmostra() {
    if (!amostra) {
      setErro('Sorteie uma amostra antes de inferir.');
      return;
    }

    setErro(null);

    try {
      const resposta = await fetch(`${SERVIDOR}/inferir/fashion`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pixels: amostra.pixels }),
      });
      if (!resposta.ok) {
        throw new Error(`O servidor respondeu com status ${resposta.status}.`);
      }

      const dados: unknown = await resposta.json();
      if (
        typeof dados !== 'object' ||
        dados === null ||
        !('classe' in dados) ||
        typeof dados.classe !== 'number' ||
        !('rotulo' in dados) ||
        typeof dados.rotulo !== 'string' ||
        !('confianca' in dados) ||
        typeof dados.confianca !== 'number'
      ) {
        throw new Error('A resposta do servidor não contém os dados esperados da inferência.');
      }

      const resultado: Resultado = {
        id: proximoId.current,
        imagem_png: amostra.imagem_png,
        rotulo_previsto: dados.rotulo,
        confianca: dados.confianca,
        rotulo_real: amostra.rotulo_real,
        acertou: dados.classe === amostra.classe_real,
      };
      proximoId.current += 1;
      setHistorico((anterior) => [resultado, ...anterior]);
    } catch (causa) {
      setErro(causa instanceof Error ? causa.message : 'Não foi possível inferir a amostra.');
    }
  }

  const acertos = historico.filter((resultado) => resultado.acertou).length;

  return (
    <View style={styles.container}>
      {amostra ? (
        <>
          <Image source={{ uri: amostra.imagem_png }} style={styles.imagemTopo} resizeMode="contain" />
          <Text style={styles.rotulo}>{amostra.rotulo_real}</Text>
        </>
      ) : (
        <Text style={styles.instrucao}>Toque em Sortear para ver uma peça de roupa.</Text>
      )}
      <View style={styles.botoes}>
        <Pressable
          accessibilityRole="button"
          disabled={carregando}
          onPress={sortearAmostra}
          style={({ pressed }) => [styles.botao, pressed && styles.botaoPressionado]}
        >
          {carregando ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <Text style={styles.textoBotao}>Sortear</Text>
          )}
        </Pressable>
        <Pressable
          accessibilityRole="button"
          onPress={inferirAmostra}
          style={({ pressed }) => [styles.botao, pressed && styles.botaoPressionado]}
        >
          <Text style={styles.textoBotao}>Inferir</Text>
        </Pressable>
      </View>
      {erro ? <Text style={styles.erro}>{erro}</Text> : null}
      <Text style={styles.placar}>Acertos: {acertos} de {historico.length}</Text>
      <FlatList
        data={historico}
        keyExtractor={(item) => String(item.id)}
        renderItem={({ item }) => <ResultadoItem resultado={item} />}
        ListEmptyComponent={<Text style={styles.listaVazia}>Nenhuma inferência ainda</Text>}
        style={styles.lista}
        contentContainerStyle={historico.length === 0 ? styles.listaVaziaContainer : undefined}
      />
      <StatusBar style="auto" />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#fff',
    alignItems: 'center',
    paddingHorizontal: 24,
    paddingTop: 32,
  },
  imagemTopo: {
    width: 112,
    height: 112,
  },
  rotulo: {
    marginTop: 8,
    fontSize: 20,
    fontWeight: '600',
  },
  instrucao: {
    height: 112,
    textAlignVertical: 'center',
    fontSize: 16,
    textAlign: 'center',
  },
  botoes: {
    flexDirection: 'row',
    gap: 12,
  },
  botao: {
    minWidth: 130,
    minHeight: 48,
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: 12,
    paddingHorizontal: 24,
    borderRadius: 8,
    backgroundColor: '#2457c5',
  },
  botaoPressionado: {
    opacity: 0.8,
  },
  textoBotao: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
  erro: {
    marginTop: 8,
    color: '#b42318',
    textAlign: 'center',
  },
  placar: {
    alignSelf: 'flex-start',
    marginTop: 20,
    marginBottom: 8,
    fontSize: 18,
    fontWeight: '600',
  },
  lista: {
    width: '100%',
  },
  listaVaziaContainer: {
    flexGrow: 1,
  },
  listaVazia: {
    paddingTop: 24,
    color: '#666',
    textAlign: 'center',
  },
});
