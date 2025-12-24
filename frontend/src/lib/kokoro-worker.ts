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
    if (!device) return false;

    // Additional check: verify WebGPU can actually create a basic buffer
    // Some devices report WebGPU support but fail during actual inference
    try {
      const testBuffer = device.createBuffer({
        size: 16,
        usage: 0x80 | 0x08, // GPUBufferUsage.STORAGE | GPUBufferUsage.COPY_DST
      });
      testBuffer.destroy();
    } catch {
      console.warn(
        "[Kokoro] WebGPU device exists but buffer creation failed, falling back to WASM",
      );
      return false;
    }

    return true;
  } catch {
    return false;
  }
}

async function init() {
  console.log("[Kokoro Worker] Starting initialization...");
  const device = (await detectWebGPU()) ? "webgpu" : "wasm";
  console.log("[Kokoro Worker] Selected device:", device);
  self.postMessage({ type: "device", device } satisfies WorkerResponse);

  const dtype = device === "wasm" ? "q8" : "fp32";
  console.log("[Kokoro Worker] Using dtype:", dtype);

  let tts: KokoroTTS;
  try {
    console.log("[Kokoro Worker] Loading model...");
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
    console.log("[Kokoro Worker] Model loaded successfully");
  } catch (e) {
    const message = e instanceof Error ? e.message : "Unknown error";
    console.error("[Kokoro Worker] Model loading failed:", message, e);
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
      console.log("[Kokoro Worker] Synthesize request:", id, text);
      try {
        const startTime = performance.now();

        // Kokoro uses different style vectors based on token sequence length.
        // Short texts (single words) map to style vectors with fewer training
        // samples, causing unstable prosody. Adding punctuation produces more
        // phoneme tokens, and slowing speed compensates for duration prediction.
        const isShortText = text.trim().split(/\s+/).length <= 2;
        const processedText =
          isShortText && !/[.!?]$/.test(text.trim()) ? `${text.trim()}.` : text;
        const speed = isShortText ? 0.85 : 1.0;

        const audio = await tts.generate(processedText, {
          voice: VOICE,
          speed,
        });
        const elapsed = performance.now() - startTime;
        console.log(
          "[Kokoro Worker] Synthesis completed in",
          elapsed.toFixed(0),
          "ms",
        );
        const blob = audio.toBlob();
        self.postMessage({ type: "result", id, blob } satisfies WorkerResponse);
      } catch (err) {
        const message = err instanceof Error ? err.message : "Synthesis failed";
        console.error("[Kokoro Worker] Synthesis error:", message, err);
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
