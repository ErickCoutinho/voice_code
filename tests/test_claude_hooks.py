import json

from voice_code.claude_hooks import BACKUP_SUFFIX, install_hooks

PREFIX = '"C:/Apps/VoiceCode.exe"'


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def voice_commands(settings, event):
    return [handler["command"] for group in settings["hooks"][event] for handler in group["hooks"]]


def test_creates_settings_file_with_both_hooks(tmp_path):
    settings_file = tmp_path / ".claude" / "settings.json"

    assert install_hooks(settings_file, PREFIX)

    settings = read_json(settings_file)
    assert voice_commands(settings, "Stop") == [f"{PREFIX} hook-stop"]
    assert voice_commands(settings, "UserPromptSubmit") == [f"{PREFIX} hook-prompt"]
    assert settings["hooks"]["Stop"][0]["hooks"][0]["async"] is True


def test_preserves_other_settings_and_hooks_and_creates_backup(tmp_path):
    settings_file = tmp_path / "settings.json"
    original = {
        "model": "opus",
        "hooks": {"Stop": [{"hooks": [{"type": "command", "command": "notify-send pronto"}]}]},
    }
    settings_file.write_text(json.dumps(original), encoding="utf-8")

    install_hooks(settings_file, PREFIX)

    settings = read_json(settings_file)
    assert settings["model"] == "opus"
    assert voice_commands(settings, "Stop") == ["notify-send pronto", f"{PREFIX} hook-stop"]
    assert read_json(tmp_path / f"settings.json{BACKUP_SUFFIX}") == original


def test_second_install_with_same_path_changes_nothing(tmp_path):
    settings_file = tmp_path / "settings.json"
    install_hooks(settings_file, PREFIX)
    content = settings_file.read_text(encoding="utf-8")

    assert not install_hooks(settings_file, PREFIX)
    assert settings_file.read_text(encoding="utf-8") == content


def test_replaces_hooks_from_previous_installation(tmp_path):
    settings_file = tmp_path / "settings.json"
    install_hooks(settings_file, '"C:/Users/eu/.local/bin/voice-code.exe"')

    assert install_hooks(settings_file, PREFIX)

    settings = read_json(settings_file)
    assert voice_commands(settings, "Stop") == [f"{PREFIX} hook-stop"]
    assert voice_commands(settings, "UserPromptSubmit") == [f"{PREFIX} hook-prompt"]
