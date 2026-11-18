"""Registro dos hooks do voice-code nas configurações do Claude Code."""

import json
import os
import shutil
from pathlib import Path
from typing import Any

CLAUDE_SETTINGS_FILE = Path.home() / ".claude" / "settings.json"
BACKUP_SUFFIX = ".bak-voice-code"

STOP_ARGUMENT = "hook-stop"
PROMPT_ARGUMENT = "hook-prompt"
PROMPT_HOOK_TIMEOUT_SECONDS = 10


def install_hooks(settings_file: Path, command_prefix: str) -> bool:
    """Garante que os hooks apontem para o executável atual.

    Preserva as demais configurações e hooks. Retorna True quando o arquivo foi
    alterado; nesse caso, o conteúdo anterior fica salvo ao lado, com o sufixo
    .bak-voice-code.
    """
    original_text = settings_file.read_text(encoding="utf-8") if settings_file.exists() else ""
    settings: dict[str, Any] = json.loads(original_text) if original_text.strip() else {}
    hooks = settings.setdefault("hooks", {})

    desired_handlers = {
        "Stop": {"type": "command", "command": f"{command_prefix} {STOP_ARGUMENT}", "async": True},
        "UserPromptSubmit": {
            "type": "command",
            "command": f"{command_prefix} {PROMPT_ARGUMENT}",
            "timeout": PROMPT_HOOK_TIMEOUT_SECONDS,
        },
    }

    changed = False
    for event, desired_handler in desired_handlers.items():
        changed |= _replace_voice_code_handler(hooks.setdefault(event, []), desired_handler)

    if changed:
        _write_with_backup(settings_file, original_text, settings)
    return changed


def _replace_voice_code_handler(matcher_groups: list[dict[str, Any]], desired_handler: dict[str, Any]) -> bool:
    """Deixa no evento apenas o hook desejado do voice-code, mantendo os demais.

    Retorna True quando a lista de hooks do evento foi alterada.
    """
    argument = desired_handler["command"].rsplit(" ", 1)[-1]
    current_handlers = [
        handler
        for group in matcher_groups
        for handler in group.get("hooks", [])
        if _is_voice_code_handler(handler, argument)
    ]
    if current_handlers == [desired_handler]:
        return False

    for group in matcher_groups:
        group["hooks"] = [h for h in group.get("hooks", []) if not _is_voice_code_handler(h, argument)]
    matcher_groups[:] = [group for group in matcher_groups if group.get("hooks")]
    matcher_groups.append({"hooks": [desired_handler]})
    return True


def _is_voice_code_handler(handler: dict[str, Any], argument: str) -> bool:
    """Reconhece hooks do voice-code, inclusive de instalações em outros caminhos.

    Cobre VoiceCode.exe, voice-code.exe e python -m voice_code, para que uma
    instalação nova substitua a anterior.
    """
    command = str(handler.get("command", ""))
    return command.endswith(f" {argument}") and "voice" in command.lower()


def _write_with_backup(settings_file: Path, original_text: str, settings: dict[str, Any]) -> None:
    """Salva o conteúdo anterior como backup e grava as configurações de forma atômica."""
    settings_file.parent.mkdir(parents=True, exist_ok=True)
    if original_text:
        shutil.copyfile(settings_file, settings_file.with_name(settings_file.name + BACKUP_SUFFIX))
    temporary_file = settings_file.with_name(settings_file.name + ".tmp-voice-code")
    temporary_file.write_text(json.dumps(settings, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(temporary_file, settings_file)
