import { useEffect, useState, useCallback } from "react";
import { View, FlatList, Button, Text, StyleSheet } from "react-native";

import { ScanResultCard } from "../components/ScanResultCard";
import { getItem, clearKey } from "../utils/storage";
import { STORAGE_KEYS } from "../utils/constants";
import type { ScanResult } from "../services/api";

export function HistoryScreen() {
  const [history, setHistory] = useState<ScanResult[]>([]);

  const loadHistory = useCallback(async () => {
    const data = await getItem<ScanResult[]>(STORAGE_KEYS.HISTORY);
    setHistory(data ?? []);
  }, []);

  useEffect(() => {
    loadHistory();
  }, [loadHistory]);

  const handleClear = async () => {
    await clearKey(STORAGE_KEYS.HISTORY);
    setHistory([]);
  };

  return (
    <View style={{ flex: 1, paddingTop: 48 }}>
      <View style={styles.header}>
        <Text style={styles.title}>Scan History</Text>
        <Button title="Clear" onPress={handleClear} />
      </View>
      <FlatList
        data={history}
        keyExtractor={(_, i) => i.toString()}
        renderItem={({ item }) => <ScanResultCard result={item} />}
        ListEmptyComponent={
          <Text style={styles.empty}>No scans yet.</Text>
        }
        onRefresh={loadHistory}
        refreshing={false}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  header: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    padding: 16,
  },
  title: { fontSize: 20, fontWeight: "bold" },
  empty: { textAlign: "center", color: "#9ca3af", marginTop: 48 },
});
