import { Image, StyleSheet, Text, View } from 'react-native';

export type Resultado = {
  id: number;
  imagem_estilo: string;
  rotulo_previsto: string;
  confianca: number;
  rotulo_real: string;
  acertou: boolean;
};

type Props = {
  resultado: Resultado;
};

export default function ResultadoItem({ resultado }: Props) {
  return (
    <View
      style={[
        styles.item,
        resultado.acertou ? styles.faixaAcerto : styles.faixaErro,
      ]}
    >
      <Image source={{ uri: resultado.imagem_estilo }} style={styles.imagem} resizeMode="contain" />
      <View style={styles.textos}>
        <Text style={styles.prevista}>
          Prevista: {resultado.rotulo_previsto} ({Math.round(resultado.confianca * 100)}%)
        </Text>
        <Text style={styles.real}>Real: {resultado.rotulo_real}</Text>
      </View>
      <Text
        accessibilityLabel={resultado.acertou ? 'Acertou' : 'Errou'}
        style={[styles.marcador, resultado.acertou ? styles.acerto : styles.erro]}
      >
        {resultado.acertou ? '✓' : '✗'}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  item: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    marginBottom: 10,
    padding: 12,
    backgroundColor: '#131D31',
    borderWidth: 1,
    borderColor: '#24324D',
    borderLeftWidth: 4,
    borderRadius: 12,
  },
  faixaAcerto: {
    borderLeftColor: '#7DD3FC',
  },
  faixaErro: {
    borderLeftColor: '#FDBA74',
  },
  imagem: {
    width: 72,
    height: 72,
  },
  textos: {
    flex: 1,
    gap: 4,
  },
  prevista: {
    fontSize: 15,
    fontWeight: '600',
    color: '#EEF2F8',
  },
  real: {
    fontSize: 14,
    color: '#A9B4C8',
  },
  marcador: {
    width: 28,
    fontSize: 24,
    fontWeight: '700',
    textAlign: 'center',
  },
  acerto: {
    color: '#7DD3FC',
  },
  erro: {
    color: '#FDBA74',
  },
});
