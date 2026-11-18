"""Aplicativo da bandeja: enquanto estiver aberto, o modo ligação fica ativo."""

import ctypes
import json
import os
import sys

import pystray
from PIL import Image, ImageDraw

from voice_code.claude_hooks import CLAUDE_SETTINGS_FILE, install_hooks
from voice_code.config import USER_ENV_FILE, ConfigError, load_settings, merge_environment
from voice_code.state import VoiceState

APP_NAME = "Voice Code"
MESSAGE_BOX_ICON_ERROR = 0x10


def show_error(message: str) -> None:
    """Exibe uma caixa de erro do Windows; o aplicativo não tem console."""
    ctypes.windll.user32.MessageBoxW(None, message, APP_NAME, MESSAGE_BOX_ICON_ERROR)


def hook_command_prefix() -> str:
    """Comando que os hooks do Claude Code usam para chamar este programa."""
    executable = sys.executable.replace("\\", "/")
    if getattr(sys, "frozen", False):
        return f'"{executable}"'
    # Execução pelo código-fonte, sem o executável empacotado.
    return f'"{executable}" -m voice_code'


def build_tray_image(size: int = 256) -> Image.Image:
    """Desenha um balão de fala verde com ondas de som em fundo transparente."""
    color = (30, 170, 90, 255)
    white = (255, 255, 255, 255)
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    def scaled(*values: float) -> tuple[int, ...]:
        """Converte coordenadas da grade base de 256 px para o tamanho pedido."""
        return tuple(round(value * size / 256) for value in values)

    draw.rounded_rectangle(scaled(16, 24, 240, 192), radius=scaled(48)[0], fill=color)
    draw.polygon(scaled(60, 180, 120, 180, 52, 240), fill=color)
    for left, top, right, bottom in ((104, 92, 120, 124), (128, 68, 144, 148), (152, 84, 168, 132), (80, 100, 96, 116)):
        draw.rounded_rectangle(scaled(left, top, right, bottom), radius=scaled(8)[0], fill=white)
    return image


def run_tray_app(state: VoiceState) -> int:
    """Ativa o modo ligação, registra os hooks e mantém o ícone até o usuário sair.

    Retorna o código de saída do processo.
    """
    if not state.acquire_app_lock():
        show_error("O Voice Code já está aberto. Procure o ícone na bandeja do sistema.")
        return 1

    try:
        load_settings(merge_environment(USER_ENV_FILE, os.environ))
        install_hooks(CLAUDE_SETTINGS_FILE, hook_command_prefix())
    except ConfigError as error:
        show_error(f"Configuração inválida em {USER_ENV_FILE}:\n\n{error}")
        state.release_app_lock()
        return 1
    except (OSError, json.JSONDecodeError) as error:
        show_error(f"Não foi possível configurar os hooks em {CLAUDE_SETTINGS_FILE}:\n\n{error}")
        state.release_app_lock()
        return 1

    def quit_app(icon: pystray.Icon) -> None:
        """Interrompe a fala, libera o bloqueio e fecha o ícone."""
        state.cancel_speech()
        state.release_app_lock()
        icon.stop()

    icon = pystray.Icon(
        "voice_code",
        build_tray_image(64),
        f"{APP_NAME} — modo ligação ativo",
        menu=pystray.Menu(
            pystray.MenuItem("Parar fala atual", lambda: state.cancel_speech()),
            pystray.MenuItem("Sair", quit_app),
        ),
    )
    icon.run()
    return 0
