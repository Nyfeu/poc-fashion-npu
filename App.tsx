import { StatusBar } from 'expo-status-bar';
import { useState } from 'react';
import { ActivityIndicator, Image, Pressable, StyleSheet, Text, View } from 'react-native';

const SERVIDOR = 'http://192.168.68.94:5000';

type Amostra = {
  imagem_png: string;
  rotulo_real: string;
};

export default function App() {
  const [amostra, setAmostra] = useState<Amostra | null>(null);
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

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
        !('rotulo_real' in dados) ||
        typeof dados.rotulo_real !== 'string'
      ) {
        throw new Error('A resposta do servidor não contém a imagem e o rótulo esperados.');
      }

      setAmostra({ imagem_png: dados.imagem_png, rotulo_real: dados.rotulo_real });
    } catch (causa) {
      setErro(causa instanceof Error ? causa.message : 'Não foi possível sortear uma amostra.');
    } finally {
      setCarregando(false);
    }
  }

  return (
    <View style={styles.container}>
      {amostra ? (
        <>
          <Image source={{ uri: amostra.imagem_png }} style={styles.imagem} resizeMode="contain" />
          <Text style={styles.rotulo}>{amostra.rotulo_real}</Text>
        </>
      ) : (
        <Text style={styles.instrucao}>Toque em Sortear para ver uma peça de roupa.</Text>
      )}
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
      {erro ? <Text style={styles.erro}>{erro}</Text> : null}
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
    paddingTop: 48,
  },
  imagem: {
    width: '100%',
    height: 280,
  },
  rotulo: {
    marginTop: 16,
    fontSize: 24,
    fontWeight: '600',
  },
  instrucao: {
    marginTop: 120,
    marginBottom: 24,
    fontSize: 18,
    textAlign: 'center',
  },
  botao: {
    minWidth: 160,
    minHeight: 48,
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: 24,
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
    marginTop: 16,
    color: '#b42318',
    textAlign: 'center',
  },
});
