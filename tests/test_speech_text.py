from voice_code.speech_text import split_sentences, to_speech_text


def test_split_sentences_breaks_on_punctuation_and_lines():
    text = "Editei o main.py. Rodei os testes e passaram! Quer seguir?\nPróximo passo"

    assert split_sentences(text) == [
        "Editei o main.py.",
        "Rodei os testes e passaram!",
        "Quer seguir?",
        "Próximo passo",
    ]


def test_split_sentences_keeps_decimal_numbers_together():
    assert split_sentences("A versão 3.5 saiu.") == ["A versão 3.5 saiu."]


def test_fenced_code_blocks_are_removed():
    markdown = "Alterei a função.\n```python\ndef main():\n    pass\n```\nPronto."

    assert to_speech_text(markdown) == "Alterei a função.\nPronto."


def test_unclosed_code_block_is_removed_until_the_end():
    assert to_speech_text("Veja:\n```bash\nrm -rf build") == "Veja:"


def test_inline_code_keeps_its_content_without_backticks():
    assert to_speech_text("Editei `main.py` na função `run`.") == "Editei main.py na função run."


def test_markdown_formatting_is_removed():
    markdown = "## Resumo\n- **Corrigi** o *bug*\n1. Rodei os testes\n> Nota"

    assert to_speech_text(markdown) == "Resumo\nCorrigi o bug\nRodei os testes\nNota"


def test_links_keep_text_and_bare_urls_are_dropped():
    markdown = "Veja a [documentação](https://exemplo.com/doc) ou https://exemplo.com."

    assert to_speech_text(markdown) == "Veja a documentação ou"


def test_table_rows_are_read_as_comma_separated_cells():
    markdown = "| Arquivo | Status |\n|---|---|\n| main.py | ok |"

    assert to_speech_text(markdown) == "Arquivo, Status\nmain.py, ok"


def test_message_with_only_code_produces_empty_speech():
    assert to_speech_text("```\nx = 1\n```") == ""
