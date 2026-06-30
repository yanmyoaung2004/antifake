import { View, Text, StyleSheet } from "react-native";

interface Props {
  queueLength: number;
}

export function OfflineBanner({ queueLength }: Props) {
  if (queueLength === 0) return null;

  return (
    <View style={styles.banner}>
      <Text style={styles.text}>
        ⚠ {queueLength} scan{queueLength > 1 ? "s" : ""} queued offline.
        Connect to sync.
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  banner: {
    backgroundColor: "#fef3c7",
    padding: 8,
    alignItems: "center",
  },
  text: { fontSize: 12, color: "#92400e" },
});
