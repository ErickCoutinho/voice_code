# voice-code

Modo ligação para o [Claude Code](https://code.claude.com/docs) no Windows: as respostas
do Claude são lidas em voz alta e a fala para quando você começa a falar, como numa
ligação.

O `voice-code` não transcreve a sua voz. A entrada por voz fica com qualquer ferramenta
de ditado (por exemplo, o ditado nativo do Claude Code, ativado com `/voice`). O
`voice-code` cuida apenas da saída falada, por meio de
[hooks](https://code.claude.com/docs/en/hooks) do Claude Code.

## Uso

1. Abra o `VoiceCode.exe`. Um balão verde aparece na bandeja do sistema.
2. Use o Claude Code normalmente. Enquanto o programa estiver aberto, as respostas são
   lidas em voz alta.
3. Para encerrar, clique com o botão direito no ícone da bandeja e escolha **Sair**.

No menu da bandeja, **Parar fala atual** interrompe a leitura em andamento.

## Como funciona

Ao abrir, o programa registra dois hooks em `~/.claude/settings.json`, apontando para o
próprio executável. As demais configurações são preservadas, e o conteúdo anterior fica
salvo em `~/.claude/settings.json.bak-voice-code`.

| Hook do Claude Code | Efeito |
|---------------------|--------|
| `UserPromptSubmit`  | Interrompe a fala em andamento. Com o programa aberto, instrui o Claude a responder de forma curta e conversacional, sem código na resposta final. |
| `Stop`              | Com o programa aberto, lê a resposta final em voz alta, frase por frase, sem blocos de código nem marcações de markdown. Roda em segundo plano. |

Com o programa fechado, os hooks não fazem nada. O programa mantém um bloqueio de
arquivo enquanto roda, que o Windows libera quando ele termina, inclusive em caso de
falha.

Durante a leitura, o microfone é monitorado. Cerca de 300 ms de voz contínua acima do
limite configurado interrompem a fala. Essa detecção é por volume: funciona bem com
headset; com alto-falantes, o próprio áudio da fala pode interrompê-la.

Para remover o `voice-code`, feche o programa, apague a pasta dele e remova de
`~/.claude/settings.json` os hooks que terminam em `hook-stop` e `hook-prompt`.

## Configuração

O arquivo `C:\Users\<usuário>\.voice-code\.env` é opcional. Use o `.env.example` como
modelo. Variáveis de ambiente não vazias têm prioridade sobre o arquivo.

| Variável                    | Padrão                | Descrição |
|-----------------------------|-----------------------|-----------|
| `TTS_VOICE`                 | `pt-BR-AntonioNeural` | Voz do edge-tts. |
| `TTS_RATE`                  | `+25%`                | Velocidade da fala, no formato `+25%` ou `-10%`. |
| `VOICE_INTERRUPT_THRESHOLD` | `0.02`                | Volume do microfone (RMS, entre 0 e 1) que interrompe a fala. Aumente se a fala parar sozinha; diminua se não parar quando você fala. |

Falhas da leitura em voz alta são registradas em
`C:\Users\<usuário>\.voice-code\voice-code.log`.

## Requisitos

- Windows
- Claude Code
- Microfone e saída de áudio (headset recomendado)
- Conexão com a internet (síntese de voz do edge-tts)

## Desenvolvimento

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[test,build]"
pytest
```

Para gerar o executável em `dist\VoiceCode\`:

```powershell
pyinstaller --noconfirm --onedir --windowed --name VoiceCode --icon assets/voice_code.ico --paths . --collect-data edge_tts voice_code/__main__.py
```

O formato em pasta (`--onedir`) é intencional: os hooks iniciam o executável a cada
mensagem, e o formato de arquivo único (`--onefile`) leva alguns segundos para
descompactar a cada execução.
