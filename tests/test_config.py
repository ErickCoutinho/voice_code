import pytest

from voice_code.config import (
    DEFAULT_INTERRUPT_THRESHOLD,
    DEFAULT_TTS_RATE,
    DEFAULT_TTS_VOICE,
    ConfigError,
    load_settings,
    merge_environment,
)


def write_env_file(tmp_path, content):
    env_file = tmp_path / ".env"
    env_file.write_text(content, encoding="utf-8")
    return env_file


def test_env_file_values_are_used_when_environment_is_empty(tmp_path):
    env_file = write_env_file(tmp_path, "TTS_VOICE=pt-BR-FranciscaNeural\nVOICE_INTERRUPT_THRESHOLD=0.05\n")

    merged = merge_environment(env_file, {})

    assert merged == {"TTS_VOICE": "pt-BR-FranciscaNeural", "VOICE_INTERRUPT_THRESHOLD": "0.05"}


def test_environment_variable_takes_precedence_over_env_file(tmp_path):
    env_file = write_env_file(tmp_path, "TTS_VOICE=arquivo\n")

    merged = merge_environment(env_file, {"TTS_VOICE": "ambiente"})

    assert merged["TTS_VOICE"] == "ambiente"


def test_blank_environment_variable_does_not_hide_env_file_value(tmp_path):
    env_file = write_env_file(tmp_path, "TTS_VOICE=arquivo\n")

    merged = merge_environment(env_file, {"TTS_VOICE": ""})

    assert merged["TTS_VOICE"] == "arquivo"


def test_missing_env_file_uses_only_environment(tmp_path):
    merged = merge_environment(tmp_path / "inexistente.env", {"TTS_VOICE": "ambiente"})

    assert merged == {"TTS_VOICE": "ambiente"}


def test_unrelated_variables_are_ignored(tmp_path):
    env_file = write_env_file(tmp_path, "ANTHROPIC_API_KEY=segredo\n")

    merged = merge_environment(env_file, {"PATH": "/bin"})

    assert merged == {}


def test_defaults_are_used_when_settings_are_absent():
    settings = load_settings({})

    assert settings.tts_voice == DEFAULT_TTS_VOICE
    assert settings.interrupt_threshold == DEFAULT_INTERRUPT_THRESHOLD


def test_explicit_values_override_defaults():
    settings = load_settings({"TTS_VOICE": "pt-BR-FranciscaNeural", "VOICE_INTERRUPT_THRESHOLD": "0.05"})

    assert settings.tts_voice == "pt-BR-FranciscaNeural"
    assert settings.interrupt_threshold == 0.05


def test_default_rate_speeds_up_speech():
    assert load_settings({}).tts_rate == DEFAULT_TTS_RATE


def test_explicit_rate_is_accepted():
    assert load_settings({"TTS_RATE": "-10%"}).tts_rate == "-10%"


@pytest.mark.parametrize("raw_value", ["25%", "+25", "rápido"])
def test_invalid_rate_raises_clear_error(raw_value):
    with pytest.raises(ConfigError, match="TTS_RATE"):
        load_settings({"TTS_RATE": raw_value})


@pytest.mark.parametrize("raw_value", ["abc", "0", "-0.1", "1.5"])
def test_invalid_threshold_raises_clear_error(raw_value):
    with pytest.raises(ConfigError, match="VOICE_INTERRUPT_THRESHOLD"):
        load_settings({"VOICE_INTERRUPT_THRESHOLD": raw_value})
