"""Estado compartilhado entre o aplicativo da bandeja e os processos dos hooks."""

import msvcrt
import os
import uuid
from pathlib import Path

APP_LOCK_FILE_NAME = "app.lock"
CURRENT_SPEECH_FILE_NAME = "current_speech"


class VoiceState:
    """Indica se o aplicativo está aberto e qual fala está ativa.

    O aplicativo mantém um bloqueio de arquivo enquanto roda. O sistema
    operacional libera o bloqueio quando o processo termina, inclusive em caso de
    falha, então o modo ligação nunca fica ligado com o aplicativo fechado.

    Cada fala registra um token próprio e só continua tocando enquanto esse token
    for o atual. Uma nova fala ou um cancelamento substitui o token.
    """

    def __init__(self, state_dir: Path) -> None:
        self._state_dir = state_dir
        self._lock_file = state_dir / APP_LOCK_FILE_NAME
        self._current_speech_file = state_dir / CURRENT_SPEECH_FILE_NAME
        self._held_lock_descriptor: int | None = None

    def acquire_app_lock(self) -> bool:
        """Retorna False quando outra instância do aplicativo já está aberta."""
        descriptor = self._open_lock_file()
        try:
            msvcrt.locking(descriptor, msvcrt.LK_NBLCK, 1)
        except OSError:
            os.close(descriptor)
            return False
        self._held_lock_descriptor = descriptor
        return True

    def release_app_lock(self) -> None:
        """Libera o bloqueio mantido por esta instância, se houver."""
        if self._held_lock_descriptor is None:
            return
        os.lseek(self._held_lock_descriptor, 0, os.SEEK_SET)
        msvcrt.locking(self._held_lock_descriptor, msvcrt.LK_UNLCK, 1)
        os.close(self._held_lock_descriptor)
        self._held_lock_descriptor = None

    def is_app_running(self) -> bool:
        """Indica se o aplicativo da bandeja está aberto, sem tomar o bloqueio."""
        if not self._lock_file.exists():
            return False
        descriptor = self._open_lock_file()
        try:
            msvcrt.locking(descriptor, msvcrt.LK_NBLCK, 1)
        except OSError:
            return True
        else:
            os.lseek(descriptor, 0, os.SEEK_SET)
            msvcrt.locking(descriptor, msvcrt.LK_UNLCK, 1)
            return False
        finally:
            os.close(descriptor)

    def claim_speech(self) -> str:
        """Registra uma nova fala como a atual, interrompendo a anterior, e retorna o seu token."""
        token = uuid.uuid4().hex
        self._write_current_speech(token)
        return token

    def is_current_speech(self, token: str) -> bool:
        """Indica se a fala do token ainda pode continuar tocando."""
        try:
            return self._current_speech_file.read_text(encoding="utf-8") == token
        except FileNotFoundError:
            return False

    def cancel_speech(self) -> None:
        """Interrompe a fala atual, se houver."""
        if self._current_speech_file.exists():
            self._write_current_speech("")

    def _open_lock_file(self) -> int:
        """Abre (ou cria) o arquivo de bloqueio e retorna o descritor."""
        self._state_dir.mkdir(parents=True, exist_ok=True)
        return os.open(self._lock_file, os.O_RDWR | os.O_CREAT)

    def _write_current_speech(self, token: str) -> None:
        """Grava o token da fala atual; vazio significa nenhuma fala."""
        self._state_dir.mkdir(parents=True, exist_ok=True)
        # Escrita atômica: outro processo nunca lê o arquivo pela metade.
        temporary_file = self._current_speech_file.with_name(f"{CURRENT_SPEECH_FILE_NAME}.{uuid.uuid4().hex}.tmp")
        temporary_file.write_text(token, encoding="utf-8")
        os.replace(temporary_file, self._current_speech_file)
