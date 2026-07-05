import { useState, useCallback, useEffect } from "react";
import { View, Button, Alert } from "react-native";
import { Camera } from "expo-camera";

import { CameraView } from "../components/CameraView";
import { getCurrentLocation } from "../services/location";
import { postScan, ScanResult } from "../services/api";
import { enqueue } from "../services/offlineQueue";
import { ScanResultCard } from "../components/ScanResultCard";

interface Props {
  onScanComplete: (result: ScanResult) => void;
}

export function ScanScreen({ onScanComplete }: Props) {
  const [scanning, setScanning] = useState(false);
  const [result, setResult] = useState<ScanResult | null>(null);
  const [hasPermission, setHasPermission] = useState<boolean | null>(null);

  useEffect(() => {
    (async () => {
      const { status } = await Camera.requestCameraPermissionsAsync();
      setHasPermission(status === "granted");
    })();
  }, []);

  const handleBarcodeScanned = useCallback(
    async (data: string) => {
      if (!scanning) return;
      setScanning(false);

      try {
        const parts = data.split("|");
        const serial = parts[0] || data;
        const batchId = parts[1] || "BATCH-A";

        const coords = await getCurrentLocation();
        const payload = {
          serial,
          batch_id: batchId,
          lat: coords?.lat ?? 0,
          lng: coords?.lng ?? 0,
          timestamp: new Date().toISOString(),
          role: "consumer" as const,
        };

        try {
          const scanResult = await postScan(payload);
          setResult(scanResult);
          onScanComplete(scanResult);
        } catch {
          await enqueue(payload);
          Alert.alert(
            "Offline",
            "Scan saved offline. It will sync when connection is restored."
          );
        }
      } catch {
        Alert.alert("Error", "Could not complete scan.");
      }
    },
    [scanning, onScanComplete]
  );

  if (hasPermission === null) {
    return <View style={{ flex: 1 }} />;
  }

  if (!hasPermission) {
    return (
      <View style={{ flex: 1, justifyContent: "center", alignItems: "center" }}>
        <Button title="Grant Camera Permission" onPress={Camera.requestCameraPermissionsAsync} />
      </View>
    );
  }

  return (
    <View style={{ flex: 1 }}>
      {scanning ? (
        <CameraView onBarcodeScanned={handleBarcodeScanned} />
      ) : (
        <View style={{ flex: 1, justifyContent: "center", alignItems: "center", padding: 16 }}>
          <Button title="Start Scanning" onPress={() => setScanning(true)} />
          {result && <ScanResultCard result={result} />}
        </View>
      )}
    </View>
  );
}
