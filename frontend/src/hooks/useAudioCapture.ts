import { useCallback, useRef, useState } from "react";
import { resampleAndEncodePCM16, uint8ArrayToBase64, WORKLET_CODE } from "../audio/pcm16";

export interface AudioCaptureState {
  isRecording: boolean;
  error: string | null;
  volume: number;
}

export function useAudioCapture() {
  const [isRecording, setIsRecording] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [volume, setVolume] = useState(0);

  const audioContextRef = useRef<AudioContext | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const workletNodeRef = useRef<AudioWorkletNode | null>(null);

  const stopCapture = useCallback(() => {
    if (workletNodeRef.current) {
      workletNodeRef.current.disconnect();
      workletNodeRef.current = null;
    }

    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach((track) => track.stop());
      mediaStreamRef.current = null;
    }

    if (audioContextRef.current) {
      audioContextRef.current.close().catch(() => {});
      audioContextRef.current = null;
    }

    setIsRecording(false);
    setVolume(0);
  }, []);

  const startCapture = useCallback(
    async (onChunk: (pcmBytes: Uint8Array, base64Data: string) => void) => {
      setError(null);

      // Verify browser capability for AudioWorklet and MediaDevices
      if (!navigator.mediaDevices?.getUserMedia) {
        const msg = "Microphone access is not supported in this browser";
        setError(msg);
        throw new Error(msg);
      }

      if (typeof window.AudioContext === "undefined" && typeof (window as any).webkitAudioContext === "undefined") {
        const msg = "Web Audio API is not supported in this browser";
        setError(msg);
        throw new Error(msg);
      }

      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          audio: {
            channelCount: 1,
            sampleRate: { ideal: 16000 },
            echoCancellation: true,
            noiseSuppression: true,
            autoGainControl: true,
          },
        });

        mediaStreamRef.current = stream;

        const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
        const audioCtx = new AudioCtx();
        audioContextRef.current = audioCtx;

        if (audioCtx.state === "suspended") {
          await audioCtx.resume();
        }

        // Register AudioWorklet processor module via inline blob
        const blob = new Blob([WORKLET_CODE], { type: "application/javascript" });
        const workletUrl = URL.createObjectURL(blob);

        try {
          await audioCtx.audioWorklet.addModule(workletUrl);
        } finally {
          URL.revokeObjectURL(workletUrl);
        }

        const sourceNode = audioCtx.createMediaStreamSource(stream);
        const workletNode = new AudioWorkletNode(audioCtx, "pcm-recorder-worklet");
        workletNodeRef.current = workletNode;

        const sourceSampleRate = audioCtx.sampleRate;

        // Buffer for ~100ms audio chunks (1600 samples at 16kHz)
        let sampleAccumulator: number[] = [];
        const SAMPLES_PER_CHUNK = 1600;

        workletNode.port.onmessage = (event: MessageEvent<Float32Array>) => {
          const rawSamples = event.data;
          if (!rawSamples || rawSamples.length === 0) return;

          // Compute instantaneous RMS volume for UI visualization
          let sumSquares = 0;
          for (let i = 0; i < rawSamples.length; i++) {
            sumSquares += rawSamples[i] * rawSamples[i];
            sampleAccumulator.push(rawSamples[i]);
          }
          const rms = Math.sqrt(sumSquares / rawSamples.length);
          setVolume(Math.min(1, rms * 3));

          // When accumulated samples reach chunk size, resample and encode
          if (sampleAccumulator.length >= SAMPLES_PER_CHUNK) {
            const floatArray = new Float32Array(sampleAccumulator);
            sampleAccumulator = [];

            const pcmBytes = resampleAndEncodePCM16(floatArray, sourceSampleRate, 16000);
            const b64 = uint8ArrayToBase64(pcmBytes);
            onChunk(pcmBytes, b64);
          }
        };

        sourceNode.connect(workletNode);
        setIsRecording(true);
      } catch (err: any) {
        stopCapture();
        const msg = err.message || "Failed to start microphone capture";
        setError(msg);
        throw err;
      }
    },
    [stopCapture]
  );

  return {
    isRecording,
    error,
    volume,
    startCapture,
    stopCapture,
  };
}
