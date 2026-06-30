import * as Location from "expo-location";

export interface Coords {
  lat: number;
  lng: number;
}

export async function requestLocationPermission(): Promise<boolean> {
  const { status } = await Location.requestForegroundPermissionsAsync();
  return status === "granted";
}

export async function getCurrentLocation(): Promise<Coords | null> {
  const hasPermission = await requestLocationPermission();
  if (!hasPermission) return null;

  const loc = await Location.getCurrentPositionAsync({
    accuracy: Location.Accuracy.High,
  });
  return {
    lat: loc.coords.latitude,
    lng: loc.coords.longitude,
  };
}
