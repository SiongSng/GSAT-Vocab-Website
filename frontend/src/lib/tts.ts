import { EdgeTTS } from "edge-tts-universal/browser";

const VOICE = "en-US-EmmaMultilingualNeural";

const audioCache = new Map<string, string>();

export async function speakText(text: string): Promise<string> {
  const cached = audioCache.get(text);
  if (cached) return cached;

  const tts = new EdgeTTS(text, VOICE);
  const result = await tts.synthesize();
  const url = URL.createObjectURL(result.audio);

  audioCache.set(text, url);
  return url;
}

export function clearAudioCache(): void {
  for (const url of audioCache.values()) {
    URL.revokeObjectURL(url);
  }
  audioCache.clear();
}
