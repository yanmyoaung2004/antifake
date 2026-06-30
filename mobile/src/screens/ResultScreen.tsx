import { View, Button, TextInput, Alert } from "react-native";
import { useState } from "react";

import { ScanResultCard } from "../components/ScanResultCard";
import type { ScanResult } from "../services/api";

interface Props {
  result: ScanResult;
  onBack: () => void;
}

export function ResultScreen({ result, onBack }: Props) {
  const [reportText, setReportText] = useState("");

  const handleSubmitReport = () => {
    Alert.alert("Report Submitted", "Thank you. Our team will review this case.");
    onBack();
  };

  return (
    <View style={{ flex: 1, paddingTop: 48 }}>
      <ScanResultCard result={result} />

      {result.status === "prompt" && (
        <View style={{ padding: 16 }}>
          <TextInput
            style={{
              borderWidth: 1,
              borderColor: "#d1d5db",
              borderRadius: 8,
              padding: 12,
              minHeight: 80,
              marginBottom: 12,
            }}
            placeholder="Describe any concerns or upload a photo of the packaging..."
            multiline
            value={reportText}
            onChangeText={setReportText}
          />
          <Button title="Submit Report" onPress={handleSubmitReport} />
        </View>
      )}

      <View style={{ padding: 16 }}>
        <Button title="Scan Another" onPress={onBack} />
      </View>
    </View>
  );
}
