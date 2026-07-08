import { useState, useRef } from "react";
import {
  View,
  Text,
  TouchableOpacity,
  Image,
  StyleSheet,
  ActivityIndicator,
} from "react-native";
import { CameraView, useCameraPermissions } from "expo-camera";
import axios from "axios";

const API_BASE = "http://10.0.2.2:8765";

type Screen = "start" | "scanning" | "result";

interface ScanResult {
  status: string;
  confidence: number;
  message: string;
  metrics?: Record<string, number>;
  overlay_base64?: string;
}

export default function App() {
  const [permission, requestPermission] = useCameraPermissions();
  const [screen, setScreen] = useState<Screen>("start");
  const [result, setResult] = useState<ScanResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [qrData, setQrData] = useState("");
  const cameraRef = useRef<any>(null);

  const handleBarcodeScanned = async ({ data }: { data: string }) => {
    setQrData(data);
    setLoading(true);

    try {
      const parts = data.split("|");
      const serial = parts[0] || data;
      const batchId = parts[1] || "BATCH-A";

      let imageBase64 = "";
      if (cameraRef.current) {
        const photo = await cameraRef.current.takePictureAsync({
          base64: true,
          quality: 0.5,
        });
        imageBase64 = photo.base64 || "";
      }

      const resp = await axios.post(`${API_BASE}/api/v1/verify`, {
        batch_id: batchId,
        serial,
        image_base64: imageBase64,
      });

      setResult(resp.data);
      setScreen("result");
    } catch (e: any) {
      setResult({
        status: "error",
        confidence: 0,
        message: e?.message || "Connection failed",
      });
      setScreen("result");
    } finally {
      setLoading(false);
    }
  };

  const handleStartScan = () => {
    setScreen("scanning");
    setResult(null);
    setQrData("");
  };

  if (!permission) {
    return <View style={styles.container} />;
  }

  if (!permission.granted) {
    return (
      <View style={styles.center}>
        <Text style={styles.title}>AntiFake</Text>
        <Text style={styles.subtitle}>Camera permission needed to scan medicine codes</Text>
        <TouchableOpacity style={styles.button} onPress={requestPermission}>
          <Text style={styles.buttonText}>Grant Permission</Text>
        </TouchableOpacity>
      </View>
    );
  }

  if (screen === "scanning") {
    return (
      <View style={styles.container}>
        <CameraView
          ref={cameraRef}
          style={StyleSheet.absoluteFill}
          facing="back"
          barcodeScannerSettings={{ barcodeTypes: ["qr"] }}
          onBarcodeScanned={handleBarcodeScanned}
        />
        {loading && (
          <View style={styles.overlay}>
            <ActivityIndicator size="large" color="#fff" />
            <Text style={styles.overlayText}>Analyzing...</Text>
          </View>
        )}
        <View style={styles.scanOverlay}>
          <Text style={styles.scanHint}>Point camera at the QR code</Text>
        </View>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      {result && (
        <View style={styles.resultContainer}>
          <Text style={styles.resultEmoji}>
            {result.status === "verified" ? "✅" : result.status === "counterfeit" ? "🚫" : "⚠️"}
          </Text>
          <Text
            style={[
              styles.resultStatus,
              {
                color:
                  result.status === "verified"
                    ? "#16a34a"
                    : result.status === "counterfeit"
                      ? "#dc2626"
                      : "#ca8a04",
              },
            ]}
          >
            {result.status === "verified"
              ? "AUTHENTIC"
              : result.status === "counterfeit"
                ? "COUNTERFEIT"
                : "ERROR"}
          </Text>
          <Text style={styles.resultMessage}>{result.message}</Text>
          <Text style={styles.resultConfidence}>
            Confidence: {Math.round(result.confidence * 100)}%
          </Text>

          {result.overlay_base64 && (
            <Image
              source={{
                uri: `data:image/png;base64,${result.overlay_base64}`,
              }}
              style={styles.overlayImage}
            />
          )}

          {result.metrics && (
            <View style={styles.metrics}>
              {Object.entries(result.metrics).map(([key, val]) => (
                <Text key={key} style={styles.metricText}>
                  {key}: {typeof val === "number" ? val.toFixed(3) : val}
                </Text>
              ))}
            </View>
          )}

          <TouchableOpacity style={styles.button} onPress={handleStartScan}>
            <Text style={styles.buttonText}>Scan Another</Text>
          </TouchableOpacity>
        </View>
      )}

      {!result && (
        <View style={styles.center}>
          <Text style={styles.title}>AntiFake</Text>
          <Text style={styles.subtitle}>
            Verify medicine authenticity with a single scan
          </Text>
          <TouchableOpacity style={styles.button} onPress={handleStartScan}>
            <Text style={styles.buttonText}>Start Scan</Text>
          </TouchableOpacity>
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#0f172a" },
  center: { flex: 1, justifyContent: "center", alignItems: "center", padding: 24 },
  title: { fontSize: 36, fontWeight: "bold", color: "#fff", marginBottom: 8 },
  subtitle: { fontSize: 16, color: "#94a3b8", textAlign: "center", marginBottom: 32 },
  button: {
    backgroundColor: "#3b82f6",
    paddingHorizontal: 32,
    paddingVertical: 14,
    borderRadius: 12,
  },
  buttonText: { color: "#fff", fontSize: 16, fontWeight: "600" },
  scanOverlay: {
    position: "absolute",
    bottom: 48,
    left: 0,
    right: 0,
    alignItems: "center",
  },
  scanHint: { color: "#fff", fontSize: 14, opacity: 0.8 },
  overlay: {
    ...StyleSheet.absoluteFill,
    backgroundColor: "rgba(0,0,0,0.6)",
    justifyContent: "center",
    alignItems: "center",
  },
  overlayText: { color: "#fff", fontSize: 18, marginTop: 12 },
  resultContainer: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    padding: 24,
  },
  resultEmoji: { fontSize: 64, marginBottom: 16 },
  resultStatus: { fontSize: 28, fontWeight: "bold", marginBottom: 8 },
  resultMessage: { fontSize: 16, color: "#94a3b8", textAlign: "center", marginBottom: 8 },
  resultConfidence: { fontSize: 14, color: "#64748b", marginBottom: 16 },
  overlayImage: { width: 200, height: 200, borderRadius: 8, marginBottom: 16 },
  metrics: {
    backgroundColor: "#1e293b",
    padding: 12,
    borderRadius: 8,
    marginBottom: 16,
    width: "100%",
  },
  metricText: { color: "#94a3b8", fontSize: 12, marginBottom: 4 },
});
