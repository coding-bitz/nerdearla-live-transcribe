/**
 * Converts Float32 audio samples from any sample rate into mono 16-bit linear PCM at 16,000 Hz.
 */
export function resampleAndEncodePCM16(
  inputSamples: Float32Array,
  sourceSampleRate: number,
  targetSampleRate: number = 16000
): Uint8Array {
  if (inputSamples.length === 0) {
    return new Uint8Array(0);
  }

  // Linear interpolation resampling
  let resampled: Float32Array;
  if (sourceSampleRate === targetSampleRate) {
    resampled = inputSamples;
  } else {
    const ratio = sourceSampleRate / targetSampleRate;
    const outputLength = Math.round(inputSamples.length / ratio);
    resampled = new Float32Array(outputLength);

    for (let i = 0; i < outputLength; i++) {
      const position = i * ratio;
      const index = Math.floor(position);
      const fraction = position - index;

      const s0 = inputSamples[index] ?? 0;
      const s1 = inputSamples[index + 1] ?? s0;
      resampled[i] = s0 + fraction * (s1 - s0);
    }
  }

  // Convert Float32 [-1.0, 1.0] to signed 16-bit little-endian PCM
  const buffer = new ArrayBuffer(resampled.length * 2);
  const view = new DataView(buffer);

  for (let i = 0; i < resampled.length; i++) {
    const s = Math.max(-1, Math.min(1, resampled[i]));
    const intSample = s < 0 ? Math.round(s * 0x8000) : Math.round(s * 0x7fff);
    view.setInt16(i * 2, intSample, true); // true for little-endian
  }

  return new Uint8Array(buffer);
}

/**
 * Encodes a Uint8Array into a standard Base64 string for WebSocket transmission.
 */
export function uint8ArrayToBase64(bytes: Uint8Array): string {
  let binary = "";
  const len = bytes.byteLength;
  for (let i = 0; i < len; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  return btoa(binary);
}

/**
 * Inline AudioWorklet processor code string.
 */
export const WORKLET_CODE = `
class PCMRecorderProcessor extends AudioWorkletProcessor {
  process(inputs, outputs, parameters) {
    const input = inputs[0];
    if (input && input.length > 0) {
      const channelData = input[0];
      if (channelData && channelData.length > 0) {
        // Send Float32 chunk copy to main thread
        this.port.postMessage(channelData);
      }
    }
    return true;
  }
}
registerProcessor('pcm-recorder-worklet', PCMRecorderProcessor);
`;
