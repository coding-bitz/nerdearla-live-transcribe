import math
import struct
from typing import Dict
from app.errors import InvalidAudioFormatError

# Known compressed container signatures that must be rejected
CONTAINER_SIGNATURES = [
    b"\x1a\x45\xdf\xa3",  # EBML / WebM / Matroska
    b"OggS",              # Ogg container (Opus / Vorbis)
    b"RIFF",              # WAV / AVI container
    b"fLaC",              # FLAC
    b"ID3",               # MP3 ID3 header
    b"\xff\xfb",          # MP3 sync frame
    b"\xff\xf3",          # MP3 sync frame
    b"\xff\xf2",          # MP3 sync frame
]


def validate_pcm16_chunk(data: bytes) -> None:
    """Validates that incoming bytes represent raw mono 16-bit PCM at 16 kHz."""
    if not data or len(data) == 0:
        raise InvalidAudioFormatError("Empty audio chunk received")

    # Reject known containerized audio streams (e.g. WebM/Opus)
    for sig in CONTAINER_SIGNATURES:
        if data.startswith(sig):
            raise InvalidAudioFormatError("Expected mono PCM16 at 16 kHz, received containerized audio")

    # 16-bit PCM requires an even number of bytes (2 bytes per sample)
    if len(data) % 2 != 0:
        raise InvalidAudioFormatError("Invalid PCM16 data: byte length must be a multiple of 2")


def compute_audio_metrics(pcm_bytes: bytes) -> Dict[str, float]:
    """Computes measured RMS volume from verified mono PCM16 audio bytes."""
    sample_count = len(pcm_bytes) // 2
    if sample_count == 0:
        return {"volume_rms": 0.0}

    samples = struct.unpack(f"<{sample_count}h", pcm_bytes)
    sum_squares = sum(s * s for s in samples)
    rms = math.sqrt(sum_squares / sample_count)

    # Normalize relative to max signed 16-bit integer (32768)
    normalized_rms = min(1.0, rms / 32768.0)
    return {
        "volume_rms": round(normalized_rms, 4),
    }
