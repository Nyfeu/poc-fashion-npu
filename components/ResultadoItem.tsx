import { Image, StyleSheet, Text, View } from 'react-native';

export type Resultado = {
  id: number;
  imagem_png: string;
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
    <View style={styles.item}>
      <Image source={{ uri: resultado.imagem_png }} style={styles.imagem} resizeMode="contain" />
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
    paddingVertical: 10,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: '#ddd',
  },
  imagem: {
    width: 64,
    height: 64,
  },
  textos: {
    flex: 1,
    gap: 4,
  },
  prevista: {
    fontSize: 15,
    fontWeight: '600',
  },
  real: {
    fontSize: 14,
    color: '#555',
  },
  marcador: {
    width: 28,
    fontSize: 24,
    fontWeight: '700',
    textAlign: 'center',
  },
  acerto: {
    color: '#16803c',
  },
  erro: {
    color: '#c62828',
  },
});
