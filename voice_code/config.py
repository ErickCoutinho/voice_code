"""Leitura e validação da configuração do usuário."""

import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from dotenv import dotenv_values

DEFAULT_TTS_VOICE = "pt-BR-AntonioNeural"
DEFAULT_TTS_RATE = "+25%"
DEFAULT_INTERRUPT_THRESHOLD = 0.02
TTS_RATE_PATTERN = re.compile(r"^[+-]\d{1,3}%$")

# Diretório fixo do usuário: os hooks rodam dentro de qualquer projeto, e o
# .env da pasta atual pertence ao projeto, não ao voice-code.
STATE_DIR = Path.home() / ".voice-code"
USER_ENV_FILE = STATE_DIR / ".env"

SETTING_NAMES = ("TTS_VOICE", "TTS_RATE", "VOICE_INTERRUPT_THRESHOLD")


class ConfigError(Exception):
    """Configuração ausente ou inválida."""


@dataclass(frozen=True)
class Settings:
    """Configuração validada da voz e da interrupção."""

    tts_voice: str
    tts_rate: str
    interrupt_threshold: float


def merge_environment(env_file: Path, environ: Mapping[str, str]) -> dict[str, str]:
    """Combina o arquivo .env do usuário com o ambiente do processo.

    Variáveis de ambiente não vazias têm prioridade sobre o arquivo. Apenas as
    variáveis do voice-code são lidas do arquivo.
    """
    file_values = dotenv_values(env_file)
    merged: dict[str, str] = {}
    for name in SETTING_NAMES:
        value = environ.get(name, "").strip() or (file_values.get(name) or "").strip()
        if value:
            merged[name] = value
    return merged


def load_settings(environ: Mapping[str, str]) -> Settings:
    """Monta a configuração, aplicando os padrões e validando os valores.

    Raises:
        ConfigError: quando algum valor informado é inválido.
    """
    return Settings(
        tts_voice=environ.get("TTS_VOICE", "").strip() or DEFAULT_TTS_VOICE,
        tts_rate=_parse_rate(environ.get("TTS_RATE", "")),
        interrupt_threshold=_parse_threshold(environ.get("VOICE_INTERRUPT_THRESHOLD", "")),
    )


def _parse_rate(raw_value: str) -> str:
    """Valida a velocidade da fala no formato exigido pelo edge-tts (ex.: +25%)."""
    rate = raw_value.strip() or DEFAULT_TTS_RATE
    if not TTS_RATE_PATTERN.match(rate):
        raise ConfigError(f"TTS_RATE deve ter o formato +25% ou -10%; recebido: {raw_value!r}.")
    return rate


def _parse_threshold(raw_value: str) -> float:
    """Valida o limite de volume do microfone, que deve estar entre 0 (exclusive) e 1."""
    if not raw_value.strip():
        return DEFAULT_INTERRUPT_THRESHOLD
    try:
        threshold = float(raw_value)
    except ValueError as error:
        raise ConfigError(
            f"VOICE_INTERRUPT_THRESHOLD deve ser um número entre 0 e 1; recebido: {raw_value!r}."
        ) from error
    if not 0 < threshold <= 1:
        raise ConfigError(
            f"VOICE_INTERRUPT_THRESHOLD deve ser maior que 0 e no máximo 1; recebido: {threshold}."
        )
    return threshold
