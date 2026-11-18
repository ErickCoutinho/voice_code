"""Ponto de entrada: sem argumentos abre o aplicativo da bandeja; com argumento, executa um hook."""

import asyncio
import json
import logging
import os
import sys

from voice_code.claude_hooks import PROMPT_ARGUMENT, STOP_ARGUMENT
from voice_code.config import STATE_DIR, USER_ENV_FILE, load_settings, merge_environment
from voice_code.speech_text import split_sentences, to_speech_text
from voice_code.state import VoiceState

LOG_FILE = STATE_DIR / "voice-code.log"

logger = logging.getLogger("voice_code")

CALL_MODE_INSTRUCTIONS = """
Modo ligação do voice-code ativo: a sua resposta final será lida em voz alta, como numa ligação.
- Responda em português do Brasil, de forma curta e conversacional, como numa conversa falada.
- Não coloque código, diffs, comandos, tabelas nem listas longas na resposta final. Ao alterar algo, \
diga em uma frase o que fez e cite o arquivo e a função afetados.
- A mensagem do usuário vem de transcrição de voz: interprete erros de transcrição pelo contexto \
(por exemplo, "Cloud Code" significa Claude Code).
- O usuário pode interromper a sua fala a qualquer momento; trate cada mensagem como continuação da conversa.
- Quando precisar de uma decisão, faça uma pergunta curta e direta.
""".strip()


def handle_stop_hook(state: VoiceState) -> None:
    """Hook Stop: lê em voz alta a resposta final do Claude."""
    if not state.is_app_running():
        return
    hook_input = json.loads(sys.stdin.buffer.read().decode("utf-8"))
    sentences = split_sentences(to_speech_text(hook_input.get("last_assistant_message") or ""))
    if not sentences:
        return

    # Importado aqui para que o hook de prompt, chamado a cada mensagem, não
    # pague o carregamento das bibliotecas de áudio.
    from voice_code.audio_output import speak_sentences

    settings = load_settings(merge_environment(USER_ENV_FILE, os.environ))
    token = state.claim_speech()
    asyncio.run(
        speak_sentences(
            sentences,
            voice=settings.tts_voice,
            rate=settings.tts_rate,
            interrupt_threshold=settings.interrupt_threshold,
            should_continue=lambda: state.is_current_speech(token),
        )
    )


def handle_prompt_hook(state: VoiceState) -> None:
    """Hook UserPromptSubmit: interrompe a fala e orienta o estilo da resposta."""
    state.cancel_speech()
    if state.is_app_running():
        # Texto impresso por este hook entra no contexto do Claude. A escrita em
        # bytes UTF-8 evita a codificação padrão do console no Windows.
        sys.stdout.buffer.write(f"{CALL_MODE_INSTRUCTIONS}\n".encode("utf-8"))
        sys.stdout.flush()


def main() -> int:
    """Abre o aplicativo da bandeja ou executa o hook indicado no primeiro argumento."""
    state = VoiceState(STATE_DIR)
    arguments = sys.argv[1:]

    if not arguments:
        from voice_code.tray_app import run_tray_app  # Carregado só no aplicativo da bandeja.

        return run_tray_app(state)

    _configure_file_logging()
    command = arguments[0]
    try:
        if command == PROMPT_ARGUMENT:
            handle_prompt_hook(state)
        elif command == STOP_ARGUMENT:
            handle_stop_hook(state)
        else:
            logger.error("Comando desconhecido: %s", command)
            return 2
    except Exception:
        # Os hooks não têm janela; o log é o único registro da falha.
        logger.exception("Falha ao executar o hook %s.", command)
        raise
    return 0


def _configure_file_logging() -> None:
    """Direciona os logs dos hooks para o arquivo voice-code.log."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        filename=LOG_FILE,
        encoding="utf-8",
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


if __name__ == "__main__":
    sys.exit(main())
