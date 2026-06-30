import AsyncStorage from "@react-native-async-storage/async-storage";

export async function getItem<T>(key: string): Promise<T | null> {
  const raw = await AsyncStorage.getItem(key);
  return raw ? (JSON.parse(raw) as T) : null;
}

export async function setItem<T>(key: string, value: T): Promise<void> {
  await AsyncStorage.setItem(key, JSON.stringify(value));
}

export async function pushToArray<T>(key: string, value: T): Promise<void> {
  const existing = (await getItem<T[]>(key)) || [];
  existing.push(value);
  await setItem(key, existing);
}

export async function clearKey(key: string): Promise<void> {
  await AsyncStorage.removeItem(key);
}
