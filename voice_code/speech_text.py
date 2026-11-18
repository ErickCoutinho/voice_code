"""Conversão de respostas em markdown para texto adequado à leitura em voz alta."""

import re

FENCED_CODE_BLOCK = re.compile(r"```.*?(```|\Z)", re.DOTALL)
MARKDOWN_LINK = re.compile(r"\[([^\]]+)\]\([^)]*\)")
BARE_URL = re.compile(r"https?://\S+")
INLINE_CODE = re.compile(r"`([^`]*)`")
EMPHASIS_MARKERS = re.compile(r"(\*\*|__|\*|~~)")
HEADING_PREFIX = re.compile(r"^\s{0,3}#{1,6}\s+")
LIST_PREFIX = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+")
QUOTE_PREFIX = re.compile(r"^\s*>\s?")
TABLE_SEPARATOR = re.compile(r"^\s*\|?\s*:?-{3,}")
# Fim de frase: pontuação seguida de espaço. Não quebra "main.py" nem "3.5".
SENTENCE_END = re.compile(r"(?<=[.!?…])\s+")


def split_sentences(speech_text: str) -> list[str]:
    """Divide o texto em frases para que a primeira comece a tocar mais cedo."""
    sentences: list[str] = []
    for line in speech_text.splitlines():
        sentences.extend(part.strip() for part in SENTENCE_END.split(line) if part.strip())
    return sentences


def to_speech_text(markdown: str) -> str:
    """Remove código e marcações que não fazem sentido quando lidos em voz alta."""
    text = FENCED_CODE_BLOCK.sub(" ", markdown)
    text = MARKDOWN_LINK.sub(r"\1", text)
    text = BARE_URL.sub("", text)
    text = INLINE_CODE.sub(r"\1", text)
    text = EMPHASIS_MARKERS.sub("", text)

    spoken_lines = [_clean_line(line) for line in text.splitlines()]
    return "\n".join(line for line in spoken_lines if line)


def _clean_line(line: str) -> str:
    """Remove marcações de início de linha (títulos, citações, listas e tabelas)."""
    if TABLE_SEPARATOR.match(line):
        return ""
    line = HEADING_PREFIX.sub("", line)
    line = QUOTE_PREFIX.sub("", line)
    line = LIST_PREFIX.sub("", line)
    # Células de tabela são lidas em sequência, separadas por vírgula.
    if line.strip().startswith("|"):
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        line = ", ".join(cell for cell in cells if cell)
    return line.strip()
