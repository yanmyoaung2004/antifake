import { useState, useEffect } from "react";
import { View, TouchableOpacity, Text, StyleSheet } from "react-native";
import * as Network from "expo-network";

import { ScanScreen } from "./src/screens/ScanScreen";
import { ResultScreen } from "./src/screens/ResultScreen";
import { HistoryScreen } from "./src/screens/HistoryScreen";
import { SettingsScreen } from "./src/screens/SettingsScreen";
import { OfflineBanner } from "./src/components/OfflineBanner";
import { flushQueue, getQueueLength } from "./src/services/offlineQueue";
import { pushToArray } from "./src/utils/storage";
import { STORAGE_KEYS } from "./src/utils/constants";
import type { ScanResult } from "./src/services/api";

type Screen = "scan" | "result" | "history" | "settings";

export default function App() {
  const [screen, setScreen] = useState<Screen>("scan");
  const [lastResult, setLastResult] = useState<ScanResult | null>(null);
  const [queueLength, setQueueLength] = useState(0);

  useEffect(() => {
    const checkNetwork = async () => {
      const state = await Network.getNetworkStateAsync();
      if (state.isConnected) {
        const results = await flushQueue();
        for (const r of results) {
          await pushToArray(STORAGE_KEYS.HISTORY, r);
        }
      }
      setQueueLength(await getQueueLength());
    };

    const interval = setInterval(checkNetwork, 30000);
    checkNetwork();
    return () => clearInterval(interval);
  }, []);

  const handleScanComplete = async (result: ScanResult) => {
    setLastResult(result);
    setScreen("result");
    await pushToArray(STORAGE_KEYS.HISTORY, result);
  };

  const renderScreen = () => {
    switch (screen) {
      case "result":
        return lastResult ? (
          <ResultScreen
            result={lastResult}
            onBack={() => setScreen("scan")}
          />
        ) : null;
      case "history":
        return <HistoryScreen />;
      case "settings":
        return <SettingsScreen />;
      default:
        return <ScanScreen onScanComplete={handleScanComplete} />;
    }
  };

  return (
    <View style={styles.container}>
      <OfflineBanner queueLength={queueLength} />
      <View style={styles.content}>{renderScreen()}</View>
      <View style={styles.tabBar}>
        {(["scan", "history", "settings"] as const).map((tab) => (
          <TouchableOpacity
            key={tab}
            style={[styles.tab, screen === tab && styles.activeTab]}
            onPress={() => setScreen(tab)}
          >
            <Text style={[styles.tabLabel, screen === tab && styles.activeLabel]}>
              {tab === "scan" ? "Scan" : tab === "history" ? "History" : "Settings"}
            </Text>
          </TouchableOpacity>
        ))}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#f9fafb" },
  content: { flex: 1 },
  tabBar: {
    flexDirection: "row",
    borderTopWidth: 1,
    borderTopColor: "#e5e7eb",
    backgroundColor: "#fff",
  },
  tab: {
    flex: 1,
    paddingVertical: 12,
    alignItems: "center",
  },
  activeTab: { borderTopWidth: 2, borderTopColor: "#2563eb" },
  tabLabel: { fontSize: 14, color: "#6b7280" },
  activeLabel: { color: "#2563eb", fontWeight: "600" },
});
