import { CameraView as ExpoCamera, CameraType } from "expo-camera";
import { StyleSheet, View } from "react-native";

interface Props {
  onBarcodeScanned: (data: string) => void;
}

export function CameraView({ onBarcodeScanned }: Props) {
  return (
    <View style={styles.container}>
      <ExpoCamera
        style={styles.camera}
        facing="back"
        barcodeScannerSettings={{ barcodeTypes: ["qr"] }}
        onBarcodeScanned={({ data }) => onBarcodeScanned(data)}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  camera: { flex: 1 },
});
