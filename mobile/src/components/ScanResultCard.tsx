import { View, Text, StyleSheet } from "react-native";
import type { ScanResult } from "../services/api";

const STATUS_COLORS: Record<string, string> = {
  verified: "#16a34a",
  flagged: "#dc2626",
  prompt: "#ca8a04",
  error: "#6b7280",
};

interface Props {
  result: ScanResult;
}

export function ScanResultCard({ result }: Props) {
  const color = STATUS_COLORS[result.status] || STATUS_COLORS.error;

  return (
    <View style={[styles.card, { borderLeftColor: color }]}>
      <Text style={[styles.status, { color }]}>{result.status.toUpperCase()}</Text>
      <Text style={styles.message}>{result.message}</Text>
      <Text style={styles.confidence}>
        Confidence: {Math.round(result.confidence * 100)}%
      </Text>
      {result.last_verified && (
        <Text style={styles.verified}>
          Last verified: {result.last_verified}
        </Text>
      )}
      {result.cached && <Text style={styles.cached}>(Cached result)</Text>}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    borderLeftWidth: 4,
    padding: 16,
    margin: 16,
    backgroundColor: "#fff",
    borderRadius: 8,
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 2,
  },
  status: { fontSize: 18, fontWeight: "bold", marginBottom: 4 },
  message: { fontSize: 14, color: "#374151", marginBottom: 4 },
  confidence: { fontSize: 12, color: "#6b7280" },
  verified: { fontSize: 12, color: "#9ca3af", marginTop: 2 },
  cached: { fontSize: 12, color: "#ca8a04", marginTop: 2 },
});
