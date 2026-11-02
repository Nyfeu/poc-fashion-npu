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
const TEMPO_LIMITE_MS = 5000;

async function comTempoLimite<T>(operacao: (signal: AbortSignal) => Promise<T>): Promise<T> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), TEMPO_LIMITE_MS);

  try {
    return await operacao(controller.signal);
  } finally {
    clearTimeout(timeout);
  }
}

function mensagemDeErro(causa: unknown, fallback: string): string {
  if (
    causa instanceof TypeError ||
    (causa instanceof Error && causa.name === 'AbortError')
  ) {
    return 'Servidor inacessível. Confira se o servidor está rodando.';
  }

  return causa instanceof Error ? causa.message : fallback;
}

type Amostra = {
  pixels: number[];
  imagem_png: string;
  classe_real: number;
  rotulo_real: string;
};

type Predicao = {
  classe: number;
  rotulo: string;
  confianca: number;
};

async function buscarAmostra(): Promise<Amostra> {
  const dados = await comTempoLimite<unknown>(async (signal) => {
    const resposta = await fetch(`${SERVIDOR}/amostra/fashion`, { signal });
    if (resposta.status === 503) {
      throw new Error('A placa não respondeu. Tente de novo.');
    }
    if (!resposta.ok) {
      throw new Error(`O servidor respondeu com status ${resposta.status}.`);
    }
    return resposta.json();
  });

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

  return {
    imagem_png: dados.imagem_png,
    pixels: dados.pixels,
    classe_real: dados.classe_real,
    rotulo_real: dados.rotulo_real,
  };
}

async function solicitarInferencia(pixels: number[]): Promise<Predicao> {
  const dados = await comTempoLimite<unknown>(async (signal) => {
    const resposta = await fetch(`${SERVIDOR}/inferir/fashion`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ pixels }),
      signal,
    });
    if (resposta.status === 503) {
      throw new Error('A placa não respondeu. Tente de novo.');
    }
    if (!resposta.ok) {
      throw new Error(`O servidor respondeu com status ${resposta.status}.`);
    }
    return resposta.json();
  });

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

  return { classe: dados.classe, rotulo: dados.rotulo, confianca: dados.confianca };
}

export default function App() {
  const [amostra, setAmostra] = useState<Amostra | null>(null);
  const [requisicaoEmAndamento, setRequisicaoEmAndamento] = useState<
    'sorteio' | 'inferencia' | 'lote' | null
  >(null);
  const requisicaoAtiva = useRef(false);
  const [progressoLote, setProgressoLote] = useState(0);
  const [amostraInferida, setAmostraInferida] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [historico, setHistorico] = useState<Resultado[]>([]);
  const proximoId = useRef(0);

  async function sortearAmostra() {
    if (requisicaoAtiva.current) return;
    requisicaoAtiva.current = true;
    setRequisicaoEmAndamento('sorteio');
    setErro(null);

    try {
      setAmostra(await buscarAmostra());
      setAmostraInferida(false);
    } catch (causa) {
      setErro(mensagemDeErro(causa, 'Não foi possível sortear uma amostra.'));
    } finally {
      requisicaoAtiva.current = false;
      setRequisicaoEmAndamento(null);
    }
  }

  async function inferirAmostra() {
    if (!amostra || amostraInferida || requisicaoAtiva.current) {
      if (!amostra) {
        setErro('Sorteie uma amostra antes de inferir.');
      }
      return;
    }

    requisicaoAtiva.current = true;
    setRequisicaoEmAndamento('inferencia');
    setErro(null);

    try {
      const predicao = await solicitarInferencia(amostra.pixels);
      adicionarResultado(amostra, predicao);
      setAmostraInferida(true);
    } catch (causa) {
      setErro(mensagemDeErro(causa, 'Não foi possível inferir a amostra.'));
    } finally {
      requisicaoAtiva.current = false;
      setRequisicaoEmAndamento(null);
    }
  }

  function adicionarResultado(amostraAtual: Amostra, predicao: Predicao) {
    const resultado: Resultado = {
      id: proximoId.current,
      imagem_png: amostraAtual.imagem_png,
      rotulo_previsto: predicao.rotulo,
      confianca: predicao.confianca,
      rotulo_real: amostraAtual.rotulo_real,
      acertou: predicao.classe === amostraAtual.classe_real,
    };
    proximoId.current += 1;
    setHistorico((anterior) => [resultado, ...anterior]);
  }

  async function rodarVinte() {
    if (requisicaoAtiva.current) return;
    requisicaoAtiva.current = true;
    setRequisicaoEmAndamento('lote');
    setProgressoLote(0);
    setErro(null);

    try {
      for (let rodada = 1; rodada <= 20; rodada += 1) {
        setProgressoLote(rodada);
        const amostraAtual = await buscarAmostra();
        setAmostra(amostraAtual);
        setAmostraInferida(false);

        const predicao = await solicitarInferencia(amostraAtual.pixels);
        adicionarResultado(amostraAtual, predicao);
        setAmostraInferida(true);
      }
    } catch (causa) {
      setErro(mensagemDeErro(causa, 'Não foi possível concluir o lote.'));
    } finally {
      requisicaoAtiva.current = false;
      setRequisicaoEmAndamento(null);
      setProgressoLote(0);
    }
  }

  const acertos = historico.filter((resultado) => resultado.acertou).length;
  const inferirDesabilitado =
    amostra === null || amostraInferida || requisicaoEmAndamento !== null;

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
          disabled={requisicaoEmAndamento !== null}
          onPress={sortearAmostra}
          style={({ pressed }) => [
            styles.botao,
            requisicaoEmAndamento !== null && styles.botaoDesabilitado,
            pressed && styles.botaoPressionado,
          ]}
        >
          {requisicaoEmAndamento === 'sorteio' ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <Text
              style={[
                styles.textoBotao,
                requisicaoEmAndamento !== null && styles.textoBotaoDesabilitado,
              ]}
            >
              Sortear
            </Text>
          )}
        </Pressable>
        <Pressable
          accessibilityRole="button"
          disabled={inferirDesabilitado}
          onPress={inferirAmostra}
          style={({ pressed }) => [
            styles.botao,
            inferirDesabilitado && styles.botaoDesabilitado,
            pressed && styles.botaoPressionado,
          ]}
        >
          {requisicaoEmAndamento === 'inferencia' ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <Text
              style={[
                styles.textoBotao,
                inferirDesabilitado && styles.textoBotaoDesabilitado,
              ]}
            >
              Inferir
            </Text>
          )}
        </Pressable>
      </View>
      <Pressable
        accessibilityRole="button"
        disabled={requisicaoEmAndamento !== null}
        onPress={rodarVinte}
        style={({ pressed }) => [
          styles.botao,
          styles.botaoLote,
          requisicaoEmAndamento !== null && styles.botaoDesabilitado,
          pressed && styles.botaoPressionado,
        ]}
      >
        <Text
          style={[
            styles.textoBotao,
            requisicaoEmAndamento !== null && styles.textoBotaoDesabilitado,
          ]}
        >
          {requisicaoEmAndamento === 'lote' ? `Rodando ${progressoLote}/20` : 'Rodar 20'}
        </Text>
      </Pressable>
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
  botaoDesabilitado: {
    backgroundColor: '#a8b8dc',
  },
  botaoLote: {
    width: '100%',
  },
  botaoPressionado: {
    opacity: 0.8,
  },
  textoBotao: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
  textoBotaoDesabilitado: {
    color: '#f4f6fb',
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
