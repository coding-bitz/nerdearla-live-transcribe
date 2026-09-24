import pathlib
import re
from app.config import ALLOWED_MODELS

PROHIBITED_PROVIDERS = [
    "whisper",
    "deepgram",
    "assemblyai",
    "openai",
    "anthropic",
]

ALLOWED_MODEL_SET = set(ALLOWED_MODELS.values())


def test_no_prohibited_providers_in_app() -> None:
    app_dir = pathlib.Path(__file__).resolve().parent.parent / "app"
    for py_file in app_dir.rglob("*.py"):
        content = py_file.read_text(encoding="utf-8").lower()
        for provider in PROHIBITED_PROVIDERS:
            assert provider not in content, f"Forbidden provider '{provider}' found in {py_file}"


def test_strictly_allowed_gemini_models_in_app() -> None:
    app_dir = pathlib.Path(__file__).resolve().parent.parent / "app"
    gemini_pattern = re.compile(r"gemini-[a-z0-9.-]+")

    for py_file in app_dir.rglob("*.py"):
        content = py_file.read_text(encoding="utf-8")
        matches = gemini_pattern.findall(content)
        for match in matches:
            assert (
                match in ALLOWED_MODEL_SET
            ), f"Unauthorized model '{match}' found in {py_file}. Whitelist: {ALLOWED_MODEL_SET}"


def test_no_demo_data_in_frontend_source() -> None:
    src_dir = pathlib.Path(__file__).resolve().parent.parent.parent / "frontend" / "src"
    if not src_dir.exists():
        return

    forbidden_patterns = [
        "sample transcript",
        "fake transcript",
        "demo data",
        "mock data",
    ]

    for file_path in src_dir.rglob("*"):
        if file_path.suffix in [".ts", ".tsx", ".js", ".jsx"]:
            content = file_path.read_text(encoding="utf-8").lower()
            for pattern in forbidden_patterns:
                assert pattern not in content, f"Forbidden pattern '{pattern}' found in {file_path}"
