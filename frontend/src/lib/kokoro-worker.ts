import { KokoroTTS } from "kokoro-js";

export type WorkerRequest = {
  type: "synthesize";
  id: number;
  text: string;
};

export type WorkerResponse =
  | { type: "device"; device: "webgpu" | "wasm" }
  | { type: "progress"; progress: number }
  | { type: "ready" }
  | { type: "error"; error: string }
  | { type: "result"; id: number; blob: Blob }
  | { type: "synthesize-error"; id: number; error: string };

const MODEL_ID = "onnx-community/Kokoro-82M-v1.0-ONNX";
const VOICE = "af_heart";

async function detectWebGPU(): Promise<boolean> {
  try {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const gpu = (navigator as any).gpu;
    if (!gpu) return false;
    const adapter = await gpu.requestAdapter();
    if (!adapter) return false;
    const device = await adapter.requestDevice();
    return Boolean(device);
  } catch {
    return false;
  }
}

async function init() {
  const device = (await detectWebGPU()) ? "webgpu" : "wasm";
  self.postMessage({ type: "device", device } satisfies WorkerResponse);

  const dtype = device === "wasm" ? "q8" : "fp32";

  let tts: KokoroTTS;
  try {
    tts = await KokoroTTS.from_pretrained(MODEL_ID, {
      dtype,
      device,
      progress_callback: (progress) => {
        if (progress.status === "progress") {
          self.postMessage({
            type: "progress",
            progress: Math.round(progress.progress),
          } satisfies WorkerResponse);
        }
      },
    });
  } catch (e) {
    const message = e instanceof Error ? e.message : "Unknown error";
    self.postMessage({
      type: "error",
      error: message,
    } satisfies WorkerResponse);
    return;
  }

  self.postMessage({ type: "ready" } satisfies WorkerResponse);

  self.addEventListener("message", async (e: MessageEvent<WorkerRequest>) => {
    const { type, id, text } = e.data;

    if (type === "synthesize") {
      try {
        const audio = await tts.generate(text, { voice: VOICE });
        const blob = audio.toBlob();
        self.postMessage({ type: "result", id, blob } satisfies WorkerResponse);
      } catch (err) {
        const message = err instanceof Error ? err.message : "Synthesis failed";
        self.postMessage({
          type: "synthesize-error",
          id,
          error: message,
        } satisfies WorkerResponse);
      }
    }
  });
}

init();
