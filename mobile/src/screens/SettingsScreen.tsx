import { View, Text, StyleSheet } from "react-native";

export function SettingsScreen() {
  return (
    <View style={styles.container}>
      <Text style={styles.title}>Settings</Text>
      <Text style={styles.text}>AntiFake v0.1.0</Text>
      <Text style={styles.text}>Powered by spatial-temporal anomaly detection</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, paddingTop: 48, padding: 16 },
  title: { fontSize: 20, fontWeight: "bold", marginBottom: 16 },
  text: { fontSize: 14, color: "#6b7280", marginBottom: 8 },
});
