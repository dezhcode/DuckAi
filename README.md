# 🦆 DuckAi

A **free, unofficial command-line client for DuckDuckGo AI Chat (duck.ai)** — no API key, no account, no subscription.

> ⚠️ **Disclaimer:** This project is not affiliated with or endorsed by DuckDuckGo. It uses a private, undocumented endpoint and may stop working at any time. Use it for personal, educational purposes and respect DuckDuckGo's terms of service. Please do not abuse the service.

## ✨ Features

- 💬 **Text chat** with streaming answers and conversation memory
- 🖼️ **Send images** (JPG / PNG / WebP / BMP… — auto-converted to WebP) and ask about them
- 📎 **Attach text/code files** (`.py`, `.js`, `.json`, `.md`, …) to your prompts
- 🎨 **Generate images** from a text prompt (saved as JPEG)
- 🎙️ **Dictation** — record your microphone or any audio file and get the transcript
- 📞 **Live voice chat** — a real two-way WebRTC call with the AI (like a phone call)
- 🔀 **Model switching** — `gpt-6-luna`, `gpt-5.6-luna`, `gpt-5.4-mini`, `gpt-5.4-nano`, `claude-haiku-4-5`, `mistral-small-2603`
- 🌐 **Proxy support** (HTTP / SOCKS5)
- 🌍 **Bilingual UI** — English (default) and Persian (`--lang fa`)

## 📦 Installation

### 1. Prerequisites

| Requirement | Notes |
|---|---|
| **Python 3.10+** | [python.org](https://www.python.org/downloads/) — on Windows, tick *"Add python.exe to PATH"* |
| **Node.js 18+** | [nodejs.org](https://nodejs.org/) — required to solve the duck.ai challenge |

### 2. Get the project

```bash
git clone https://github.com/<YOUR-USERNAME>/DuckAi.git
cd DuckAi
```
*(or download and extract the ZIP)*

### 3. Install dependencies

```bash
# Python packages (core)
pip install -r requirements.txt

# Node package (jsdom — required)
npm install
```

**Optional — voice features only:**

```bash
pip install -r requirements-voice.txt
```

> If you use a **SOCKS5** proxy, also run: `pip install "requests[socks]"`

## 🚀 Usage

### Interactive menu (easiest)

```bash
python duck_cli.py
```

You get a numbered menu: text chat, one-off question, image generation, model switching, live voice, voice-to-text.

### One-off question

```bash
python duck_cli.py --ask "Explain what DNS is in one paragraph"
```

### Continuous chat with memory

```bash
python duck_cli.py --chat
```

In-chat commands:

| Command | Description |
|---|---|
| `/img photo.jpg` | Attach image(s) to your next message |
| `/file main.py` | Attach text/code file(s) to your next message |
| `/draw a starry sky` | Generate an image |
| `/model` | Switch model |
| `/mic` | Record the microphone → text → send |
| `/live` | Live two-way voice chat (**wear headphones!**) |
| `/clear` | Clear the chat memory |
| `/exit` (or empty Enter) | Quit |

### Send an image with a question

```bash
python duck_cli.py --ask "What is in this picture?" --image photo.jpg
```
Multiple images: `--image a.jpg b.png`

### Ask about a source file

```bash
python duck_cli.py --ask "What does this code do?" --file main.py
```
Multiple files: `--file main.py utils.py`

### Generate an image

```bash
python duck_cli.py --draw "a cute orange cat sitting on a windowsill"
```
The JPEG is saved in the current folder (or `--out some/folder`).

### Voice

```bash
# record the microphone, print the transcript (Enter = stop)
python duck_cli.py --listen

# transcribe an existing audio file (wav/mp3/m4a/webm/...)
python duck_cli.py --dictate recording.mp3

# live two-way voice call with the AI
python duck_cli.py --voice
```

### Pick a model

```bash
python duck_cli.py --ask "hi" --model mini     # gpt-5.4-mini
python duck_cli.py --ask "hi" --model haiku    # claude-haiku-4-5
python duck_cli.py --ask "hi" --model mistral  # mistral-small-2603
```

### Proxy

```bash
python duck_cli.py --ask "hi" --proxy http://127.0.0.1:8080
python duck_cli.py --ask "hi" --proxy socks5://127.0.0.1:1080
```

### Persian UI

```bash
python duck_cli.py --lang fa          # one run
set DUCKAI_LANG=fa                    # Windows (persistent: setx DUCKAI_LANG fa)
export DUCKAI_LANG=fa                 # Linux / macOS
```

## 🔧 How it works (technical)

1. `GET https://duck.ai/` → extracts `data-version-tag` / `data-version-sha` → builds `x-fe-version`
2. `GET /duckchat/v1/status` (header `x-vqd-accept: 1`) → returns `x-vqd-hash-1`: a base64-encoded JavaScript challenge
3. The challenge is solved locally with **Node.js + jsdom** (`jsa_jsdom.js`) — no real browser needed
4. The solution is packaged into the final `x-vqd-hash-1` proof (`client_hashes` = base64 of sha256)
5. `POST /duckchat/v1/chat` streams the answer back as **SSE** events

Image generation uses `metadata = {"toolChoice": {"GenerateImage": true}}` and reads `ui-component / generate-image` SSE events. Live voice uses `GET /duckchat/v1/ice-servers` + `POST /duckchat/v1/session` (WebRTC offer/answer, Opus audio, server-side VAD, events over a `duckai-voice-session` datachannel).

## 🐞 Troubleshooting

| Problem | Fix |
|---|---|
| `Node.js was not found on PATH` | Install Node.js from [nodejs.org](https://nodejs.org), reopen the terminal |
| `The 'jsdom' package is missing` | Run `npm install` **inside the project folder** |
| `No challenge received (HTTP 403)` | Your IP may be rate-limited/flagged — wait, or use `--proxy` |
| `Chat failed after 4 attempts` | duck.ai changed something, or a proxy is blocking you — try again later |
| Persian text looks broken on Windows | Run `chcp 65001` first, or use Windows Terminal |
| Microphone errors | Install the voice extras: `pip install -r requirements-voice.txt` |
| Live voice hears itself | Wear headphones — speaker echo confuses the server-side VAD |
| Pillow warning | `pip install pillow` (needed for image conversion) |

## 📁 Project layout

```
DuckAi/
├── duck_cli.py        # main CLI: chat, images, files, image generation
├── duck_voice.py      # dictation + live WebRTC voice session
├── duck_i18n.py       # English/Persian UI strings
├── jsa_jsdom.js       # Node runner that solves the duck.ai challenge
├── requirements.txt   # core Python deps
├── requirements-voice.txt  # optional voice deps
├── package.json       # Node deps (jsdom)
└── README.md / README.fa.md
```

## 📜 License

MIT — see [LICENSE](LICENSE). Use at your own risk; this is an unofficial tool.
