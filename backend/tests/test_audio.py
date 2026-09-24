import pytest
from app.audio import compute_audio_metrics, validate_pcm16_chunk
from app.errors import InvalidAudioFormatError


def test_validate_valid_pcm16_silence() -> None:
    # 160 samples (320 bytes) of PCM16 silence
    pcm_silence = b"\x00\x00" * 160
    validate_pcm16_chunk(pcm_silence)


def test_validate_empty_chunk_rejected() -> None:
    with pytest.raises(InvalidAudioFormatError, match="Empty audio chunk"):
        validate_pcm16_chunk(b"")


def test_validate_odd_length_chunk_rejected() -> None:
    with pytest.raises(InvalidAudioFormatError, match="must be a multiple of 2"):
        validate_pcm16_chunk(b"\x00\x00\x01")


def test_reject_webm_opus_container() -> None:
    webm_signature = b"\x1a\x45\xdf\xa3\x9f\x42\x86"
    with pytest.raises(InvalidAudioFormatError, match="containerized audio"):
        validate_pcm16_chunk(webm_signature)


def test_reject_ogg_container() -> None:
    ogg_signature = b"OggS\x00\x02\x00\x00"
    with pytest.raises(InvalidAudioFormatError, match="containerized audio"):
        validate_pcm16_chunk(ogg_signature)


def test_reject_riff_wav_container() -> None:
    wav_signature = b"RIFF\x24\x00\x00\x00WAVE"
    with pytest.raises(InvalidAudioFormatError, match="containerized audio"):
        validate_pcm16_chunk(wav_signature)


def test_compute_audio_metrics_silence() -> None:
    pcm_silence = b"\x00\x00" * 320
    metrics = compute_audio_metrics(pcm_silence)
    assert metrics["volume_rms"] == 0.0


def test_compute_audio_metrics_non_zero() -> None:
    # Construct 16-bit PCM samples with amplitude
    import struct

    samples = [10000, -10000] * 100
    pcm_data = struct.pack(f"<{len(samples)}h", *samples)
    metrics = compute_audio_metrics(pcm_data)
    assert 0.2 < metrics["volume_rms"] < 0.4
