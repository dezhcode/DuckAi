#!/usr/bin/env python3
# duck_cli.py — free unofficial client for DuckDuckGo AI Chat (duck.ai)
#
# Protocol (reverse-engineered from a real HAR capture):
#   1) GET  https://duck.ai/            -> data-version-tag + data-version-sha  => x-fe-version
#   2) GET  /duckchat/v1/status (x-vqd-accept: 1)  -> x-vqd-hash-1 = base64(JS challenge)
#   3)  Solve the challenge with Node + jsdom  ->  {server_hashes, client_hashes, signals, meta}
#   4)  final x-vqd-hash-1 = base64(JSON with client_hashes = base64(sha256(raw)))
#   5) POST /duckchat/v1/chat  -> SSE response stream
#
# Features:
#   * Image input: {"type":"image","mimeType":"image/webp","image":"data:image/webp;base64,..."}
#     (the server only accepts WebP — JPEG/PNG/etc. are converted automatically with Pillow)
#   * Image generation: metadata={"toolChoice":{"GenerateImage":true}} -> SSE events with
#     role=ui-component, name=generate-image and data.b64Image (JPEG)
#   * Text/code files are inlined into the prompt as fenced code blocks
#   * Model switching: menu, --model argument, or the /model command mid-chat
#   * Voice: dictation (voice -> text) and live two-way voice via WebRTC (see duck_voice.py)
#   * UI language: English (default) or Persian — --lang fa or DUCKAI_LANG=fa
#
# Requirements:
#   Python 3.10+   pip install -r requirements.txt
#   Node.js on PATH +  npm install   (installs jsdom, in this folder)
#
# Free models (duck.ai frontend config, Nov 2026): gpt-6-luna (default),
#         gpt-5.4-mini, claude-haiku-5-5, mistral-small-2603,
#         tinfoil/gpt-oss-120b, tinfoil/gemma4-31b
# Legacy (auto-upgraded by duck.ai): gpt-5.6-luna, gpt-5.4-nano, claude-haiku-4-5
#
# Usage:
#   python duck_cli.py                                     -> interactive menu
#   python duck_cli.py --ask "Hello, how are you?"
#   python duck_cli.py --ask "What is this?" --image photo.jpg
#   python duck_cli.py --ask "What does this code do?" --file main.py
#   python duck_cli.py --draw "a cute orange cat"          -> generate an image (saved as JPEG)
#   python duck_cli.py --ask "hi" --model mini             -> gpt-5.4-mini
#   python duck_cli.py --chat                              -> continuous chat with memory
#   Inside chat:  /img pic.jpg   /file code.py   /draw a starry sky   /model   /exit
#   Voice:  /mic (record + transcribe)   /live (live voice call)   --voice   --listen   --dictate FILE

import argparse
import base64
import hashlib
import io
import json
import mimetypes
import os
import re
import subprocess
import sys
import tempfile
import threading
import time
import uuid

if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from duck_i18n import _, get_lang, set_lang

import requests

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

__version__ = "2.2.0"

HERE = os.path.dirname(os.path.abspath(__file__))
_BASE = "https://duck.ai"

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36")

# Chat models. The free set mirrors duck.ai's own frontend config (checked Nov 2026):
# these six models list the Free tier in their availableTo array:
#   gpt-6-luna, gpt-5.4-mini, claude-haiku-5-5, mistral-small-2603,
#   tinfoil/gpt-oss-120b, tinfoil/gemma4-31b
# Legacy ids (gpt-5.6-luna, gpt-5.4-nano, claude-haiku-4-5) are still accepted —
# duck.ai upgrades them to their replacement model.
MODELS = {
    # ── current free models ──
    "luna": "gpt-6-luna",           # free-tier default model
    "gpt-6-luna": "gpt-6-luna",
    "mini": "gpt-5.4-mini",
    "gpt-5.4-mini": "gpt-5.4-mini",
    "haiku": "claude-haiku-5-5",
    "claude-haiku-5-5": "claude-haiku-5-5",
    "mistral": "mistral-small-2603",
    "mistral-small-2603": "mistral-small-2603",
    "oss": "tinfoil/gpt-oss-120b",  # open-source 120B
    "gemma": "tinfoil/gemma4-31b",  # open-source Gemma 4 31B
    # ── legacy ids (still work, auto-upgraded by duck.ai) ──
    "gpt-5.6-luna": "gpt-5.6-luna",          # -> upgraded to gpt-6-luna
    "gpt-5.4-nano": "gpt-5.4-nano",          # -> upgraded to gpt-6-luna
    "claude-haiku-4-5": "claude-haiku-4-5",  # -> upgraded to claude-haiku-5-5
}

_LEGACY_MODELS = {"gpt-5.6-luna", "gpt-5.4-nano", "claude-haiku-4-5"}

# Some models reject reasoningEffort "none" (HTTP 400 ERR_BAD_REQUEST).
# Per-model defaults; every other model uses "none".
REASONING_EFFORT = {
    "tinfoil/gpt-oss-120b": "low",
}

# Image limits (mirroring duck.ai browser behavior)
IMG_MAX_DIM = 1568            # largest side
IMG_WEBP_QUALITY = 85
IMG_MAX_PAYLOAD = 3_500_000   # data-url size cap to avoid HTTP 400

_TEXT_EXTS = {
    ".txt", ".md", ".markdown", ".rst", ".log", ".csv", ".tsv", ".json",
    ".jsonl", ".xml", ".yaml", ".yml", ".ini", ".cfg", ".conf", ".toml",
    ".env", ".py", ".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx", ".java",
    ".c", ".h", ".cpp", ".hpp", ".cc", ".cs", ".go", ".rs", ".rb", ".php",
    ".swift", ".kt", ".kts", ".sh", ".bash", ".zsh", ".ps1", ".bat", ".cmd",
    ".sql", ".html", ".htm", ".css", ".scss", ".less", ".vue", ".svelte",
    ".dart", ".lua", ".pl", ".r", ".m", ".asm", ".gradle", ".cmake",
    ".dockerfile", ".gitignore", ".properties", ".prisma", ".graphql",
}

_SOLVE_LOCK = threading.Lock()


def b64(data: bytes) -> str:
    return base64.b64encode(data).decode()


def sha256_b64(text: str) -> str:
    return b64(hashlib.sha256(text.encode()).digest())


def b64_json(obj) -> str:
    return b64(json.dumps(obj, separators=(",", ":")).encode())


class DuckAIError(RuntimeError):
    def __init__(self, message: str, status: int | None = None):
        super().__init__(message)
        self.status = status


# ─────────────────────────── image / file helpers ───────────────────────────

def image_to_data_url(path: str) -> dict:
    """Convert any image to a WebP data-url (the only format the server accepts)."""
    if not os.path.isfile(path):
        raise DuckAIError(_("Image file not found: {path}").format(path=path))
    if not HAS_PIL:
        # Without Pillow only raw WebP files can be sent as-is
        with open(path, "rb") as fh:
            raw = fh.read()
        if len(raw) > IMG_MAX_PAYLOAD:
            raise DuckAIError(_("Image is too large and Pillow is not installed: {path}")
                              .format(path=path))
        return {
            "type": "image",
            "mimeType": "image/webp",
            "image": "data:image/webp;base64," + b64(raw),
        }
    try:
        im = Image.open(path)
        im.load()
    except Exception as e:
        raise DuckAIError(_("Failed to open image ({path}): {e}").format(path=path, e=e))
    if im.mode in ("RGBA", "P", "LA"):
        im = im.convert("RGBA")
        # white background for transparency
        bg = Image.new("RGB", im.size, (255, 255, 255))
        bg.paste(im, mask=im.split()[-1])
        im = bg
    elif im.mode != "RGB":
        im = im.convert("RGB")
    # downscale if too large
    w, h = im.size
    scale = max(w, h) / IMG_MAX_DIM
    if scale > 1:
        im = im.resize((int(w / scale), int(h / scale)),
                       Image.LANCZOS if hasattr(Image, "LANCZOS") else Image.BICUBIC)
    buf = io.BytesIO()
    im.save(buf, "WEBP", quality=IMG_WEBP_QUALITY)
    data = buf.getvalue()
    # if still too big, step the quality down
    q = IMG_WEBP_QUALITY
    while len(data) > IMG_MAX_PAYLOAD and q > 30:
        q -= 15
        buf = io.BytesIO()
        im.save(buf, "WEBP", quality=q)
        data = buf.getvalue()
    if len(data) > IMG_MAX_PAYLOAD:
        raise DuckAIError(_("Image is still too large after compression: {path}")
                          .format(path=path))
    return {
        "type": "image",
        "mimeType": "image/webp",
        "image": "data:image/webp;base64," + b64(data),
    }


def images_to_parts(paths: list[str]) -> list[dict]:
    return [image_to_data_url(p) for p in paths]


def file_to_prompt_chunk(path: str, max_chars: int = 60_000) -> str:
    """Inline a text/code file into the prompt as a fenced code block."""
    if not os.path.isfile(path):
        raise DuckAIError(_("File not found: {path}").format(path=path))
    ext = os.path.splitext(path)[1].lower().lstrip(".")
    mime_guess = mimetypes.guess_type(path)[0] or ""
    if not (ext in _TEXT_EXTS or mime_guess.startswith("text/") or ext == ""):
        raise DuckAIError(
            _("'{name}' is not a text file. duck.ai only accepts images (WebP) and "
              "text; binary files cannot be sent.").format(name=os.path.basename(path)))
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            content = fh.read()
    except OSError as e:
        raise DuckAIError(_("Failed to read file ({path}): {e}").format(path=path, e=e))
    trunc = ""
    if len(content) > max_chars:
        content = content[:max_chars]
        trunc = _("\n\n[The file was long and got truncated to {max} characters]").format(
            max=max_chars)
    name = os.path.basename(path)
    lang = ext if ext else "text"
    return _("\n\nContent of file '{name}':\n```{lang}\n{content}\n```{trunc}\n").format(
        name=name, lang=lang, content=content, trunc=trunc)


# ─────────────────────────────── client ───────────────────────────────

class DuckAI:
    def __init__(self, ua: str = UA, timeout: int = 60, proxy: str | None = None):
        self.ua = ua
        self.timeout = timeout
        self.s = requests.Session()
        self.s.headers.update({"User-Agent": ua, "Accept-Language": "en-US,en;q=0.9"})
        if proxy:
            self.s.proxies = {"http": proxy, "https": proxy}
        self.fe_version = ""
        self.jsa = ""  # last proof (reused for later requests of the same conversation)

    # ────────── handshake ──────────

    def bootstrap(self):
        r = self.s.get(_BASE + "/", timeout=self.timeout)
        r.raise_for_status()
        tag = re.search(r'data-version-tag="([^"]*)"', r.text)
        sha = re.search(r'data-version-sha="([^"]*)"', r.text)
        self.fe_version = "{t}-{s}".format(t=tag.group(1) if tag else "dev",
                                           s=sha.group(1) if sha else "hash")
        return self

    def fetch_challenge(self) -> str:
        r = self.s.get(
            _BASE + "/duckchat/v1/status",
            headers={"x-vqd-accept": "1", "Cache-Control": "no-store",
                     "x-fe-version": self.fe_version,
                     "Origin": _BASE, "Referer": _BASE + "/"},
            timeout=self.timeout,
        )
        raw = r.headers.get("x-vqd-hash-1")
        if not raw:
            raise DuckAIError(_("No challenge received (HTTP {code}): {t}")
                              .format(code=r.status_code, t=r.text[:200]),
                              status=r.status_code)
        return base64.b64decode(raw + "=" * (-len(raw) % 4)).decode("utf-8", "replace")

    def solve(self, js_source: str) -> dict:
        """Run the challenge with Node + jsdom."""
        runner = os.path.join(HERE, "jsa_jsdom.js")
        if not os.path.isfile(runner):
            raise DuckAIError(_("jsa_jsdom.js not found — it must sit next to this script"))
        # write the challenge to the system temp dir so this also works when the
        # project folder itself is read-only
        fd, path = tempfile.mkstemp(suffix=".js")
        os.close(fd)
        try:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(js_source)
            with _SOLVE_LOCK:
                try:
                    out = subprocess.run(
                        ["node", runner, path, self.ua],
                        capture_output=True, text=True, timeout=90,
                        cwd=HERE,
                    )
                except FileNotFoundError:
                    raise DuckAIError(
                        _("Node.js was not found on PATH. Install it from "
                          "https://nodejs.org and then run:  npm install"))
        finally:
            try:
                os.remove(path)
            except OSError:
                pass
        if out.returncode != 0 or not out.stdout.strip():
            if "Cannot find module" in out.stderr and "jsdom" in out.stderr:
                raise DuckAIError(_("The 'jsdom' package is missing. Run this in the "
                                    "project folder:  npm install"))
            raise DuckAIError(_("Challenge execution failed: {e}").format(e=out.stderr[:400]))
        try:
            result = json.loads(out.stdout)
        except json.JSONDecodeError as e:
            raise DuckAIError(_("Challenge execution failed: {e}").format(e=e))
        if "__error" in result:
            raise DuckAIError(_("Error inside challenge: {e}").format(e=result["__error"][:400]))
        return result

    def build_proof(self, solved: dict) -> str:
        proof = dict(solved)
        proof["client_hashes"] = [sha256_b64(x) for x in solved["client_hashes"]]
        meta = dict(solved.get("meta") or {})
        meta.update({
            "origin": _BASE,
            "stack": ("Error\nat l (https://duck.ai/dist/duckai-dist/entry.duckai.js:2:2129171)\n"
                      "at async https://duck.ai/dist/duckai-dist/entry.duckai.js:2:1859809"),
            "duration": "58",
        })
        proof["meta"] = meta
        return b64_json(proof)

    def rehandshake(self):
        """Fetch a fresh challenge (fixes transient 418 responses)."""
        self.bootstrap()
        self.jsa = self.build_proof(self.solve(self.fetch_challenge()))

    # ────────── chat ──────────

    def chat(self, prompt: str, model: str = "gpt-6-luna", tools: bool = True,
             history: list | None = None, images: list[dict] | None = None,
             draw: bool = False, prompt_extra: str = ""):
        content = [{"type": "text", "text": prompt + prompt_extra}]
        if images:
            content.extend(images)  # same order as the browser: text first, then images
        msgs = (history or []) + [{"role": "user", "content": content}]
        body = {
            "model": model,
            "messages": msgs,
            "canUseTools": tools,
            "reasoningEffort": REASONING_EFFORT.get(model, "none"),
            "canUseApproxLocation": None,
            "canDelegateImageGeneration": None,
            "canShowGreeting": False,
        }
        if draw:
            # what the browser does for "draw / make an image"
            body["metadata"] = {"toolChoice": {"GenerateImage": True}}
        headers = {
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
            "Origin": _BASE,
            "Referer": _BASE + "/",
            "x-fe-version": self.fe_version,
            "x-fe-signals": b64_json({
                "start": int(time.time() * 1000),
                "events": [{"name": "action", "delta": 1200, "trusted": True}],
                "end": 1500,
            }),
            "X-Vqd-Hash-1": self.jsa,
        }
        return self.s.post(_BASE + "/duckchat/v1/chat", headers=headers,
                           data=json.dumps(body), stream=True, timeout=self.timeout)

    # ────────── raw event stream ──────────

    def stream_events(self, prompt: str, model: str = "gpt-6-luna", retries: int = 4,
                      history: list | None = None, images: list[dict] | None = None,
                      draw: bool = False, prompt_extra: str = ""):
        """Generator of SSE events; each item is one of:
             ("message", str)         — a chunk of the answer text
             ("image", dict)          — final image {b64, width, height, format}
             ("image_partial", dict)  — progressive preview
             ("image_title", str)     — image-generation step title
             ("tool", dict)           — tool call (GenerateImage/WebSearch/...)
           Errors raise DuckAIError."""
        r = None
        last = ""
        status = None
        for attempt in range(retries):
            if attempt:
                self.rehandshake()
            else:
                if not self.fe_version or not self.jsa:
                    self.rehandshake()
            r = self.chat(prompt, model, history=history, images=images,
                          draw=draw, prompt_extra=prompt_extra)
            if r.status_code == 200:
                break
            status = r.status_code
            last = "HTTP {c}: {t}".format(c=r.status_code, t=r.text[:200])
            # 418 = DDG anti-abuse score; a fresh challenge usually fixes it
            time.sleep(2 + attempt * 2)
        else:
            raise DuckAIError(_("Chat failed after {n} attempts: {e}")
                              .format(n=retries, e=last), status=status)

        for raw in r.iter_lines():
            if not raw:
                continue
            line = raw.decode("utf-8", "replace") if isinstance(raw, bytes) else raw
            if not line.startswith("data: "):
                continue
            payload = line[6:]
            if payload.startswith("["):  # [PING] / [DONE] / [CHAT_TITLE:...]
                continue
            try:
                ev = json.loads(payload)
            except json.JSONDecodeError:
                continue
            if ev.get("action") == "error":
                raise DuckAIError(
                    _("Server error ({status}): {t}")
                    .format(status=ev.get("status"), t=ev.get("type", "?")))
            role = ev.get("role", "")
            name = ev.get("name", "")
            # answer text
            msg = ev.get("message")
            if isinstance(msg, str) and msg:
                yield ("message", msg)
                continue
            # image-generation events
            if role == "ui-component" and name == "generate-image":
                data = ev.get("data") or {}
                dtype = data.get("type")
                if dtype == "image-title":
                    yield ("image_title", data.get("title", ""))
                    continue
                if dtype == "image-partial" or data.get("status") == "partial":
                    yield ("image_partial", data)
                    continue
                if data.get("status") == "success" and data.get("b64Image"):
                    yield ("image", {
                        "b64": data["b64Image"],
                        "width": data.get("width"),
                        "height": data.get("height"),
                        "format": data.get("format", "jpeg"),
                    })
                    continue
            # tool calls
            if role == "tool-invocation":
                yield ("tool", {
                    "toolName": ev.get("toolName"),
                    "state": ev.get("state"),
                    "toolArguments": ev.get("toolArguments"),
                })
                continue

    def stream(self, prompt: str, model: str = "gpt-6-luna", retries: int = 4,
               history: list | None = None, images: list[dict] | None = None,
               prompt_extra: str = ""):
        for kind, val in self.stream_events(prompt, model=model, retries=retries,
                                            history=history, images=images,
                                            prompt_extra=prompt_extra):
            if kind == "message":
                yield val

    def ask(self, prompt: str, model: str = "gpt-6-luna", on_delta=None,
            retries: int = 4, history: list | None = None,
            images: list[dict] | None = None, files: list[str] | None = None) -> str:
        prompt_extra = ""
        for f in (files or []):
            prompt_extra += file_to_prompt_chunk(f)
        parts = []
        for delta in self.stream(prompt, model=model, retries=retries, history=history,
                                 images=images, prompt_extra=prompt_extra):
            parts.append(delta)
            if on_delta:
                on_delta(delta)
        return "".join(parts)

    # ────────── image generation ──────────

    def generate_image(self, prompt: str, model: str = "gpt-6-luna",
                       out_dir: str | None = None, on_progress=None,
                       retries: int = 4, history: list | None = None):
        """Generate an image and save it as JPEG. Returns: (path, companion text, info)"""
        out_dir = out_dir or HERE
        os.makedirs(out_dir, exist_ok=True)
        img = None
        text_parts = []
        tool_seen = False
        for kind, val in self.stream_events(prompt, model=model, retries=retries,
                                            history=history, draw=True):
            if kind == "message":
                text_parts.append(val)
                if on_progress:
                    on_progress("text", val)
            elif kind == "image_title":
                if on_progress:
                    on_progress("title", val)
            elif kind == "image_partial":
                tool_seen = True
                if on_progress:
                    on_progress("partial", None)
            elif kind == "tool":
                tool_seen = True
                if on_progress:
                    on_progress("tool", val.get("toolName"))
            elif kind == "image":
                img = val
        if not img:
            raise DuckAIError(_("No image in the response{extra}")
                              .format(extra=_(" (tool did not run?)") if not tool_seen else ""))
        raw = base64.b64decode(img["b64"])
        ext = "jpg" if img.get("format", "jpeg").lower().startswith("jp") \
            else (img.get("format") or "jpg").lower()
        fname = "duckai_{ts}_{uid}.{ext}".format(
            ts=time.strftime("%Y%m%d_%H%M%S"), uid=uuid.uuid4().hex[:6], ext=ext)
        path = os.path.join(out_dir, fname)
        with open(path, "wb") as fh:
            fh.write(raw)
        return path, "".join(text_parts), img

    # continuous chat: keeps history in duck.ai's message format
    def chat_turn(self, prompt: str, model: str, history: list,
                  images: list[dict] | None = None,
                  files: list[str] | None = None) -> str:
        prompt_extra = ""
        for f in (files or []):
            prompt_extra += file_to_prompt_chunk(f)
        answer = self._ask_with_extra(prompt, model, history, images, prompt_extra)
        content = [{"type": "text", "text": prompt}]
        if images:
            content.extend(images)
        if prompt_extra:
            content[0]["text"] = prompt + prompt_extra
        history.append({"role": "user", "content": content})
        history.append({"role": "assistant", "content": answer})
        return answer

    def _ask_with_extra(self, prompt, model, history, images, prompt_extra):
        parts = []
        for delta in self.stream(prompt, model=model, history=history,
                                 images=images, prompt_extra=prompt_extra):
            parts.append(delta)
        return "".join(parts)


# ───────────────────────────── terminal UI ─────────────────────────────

def print_header():
    print("\n" + "=" * 58)
    print("   " + _("DuckDuckGo AI Chat — unofficial free client (no API key)"))
    print("   " + _("See images ✔  Make images ✔  Read files ✔  Switch models ✔"))
    lang_name = "English" if get_lang() == "en" else "Persian (فارسی)"
    print("   " + _("Language: {lang}  (change with --lang en|fa or DUCKAI_LANG=fa)")
          .format(lang=lang_name))
    print("=" * 58)


def model_table() -> list:
    return list(MODELS)


def choose_model(current: str | None = None) -> str:
    print(_("\nPick a model:"))
    keys = model_table()
    for i, k in enumerate(keys, 1):
        mark = ""
        if current and MODELS[k] == current:
            mark = _("  ← now")
        if k in _LEGACY_MODELS:
            mark += "  (legacy)"
        print("  {i}. {k:12} -> {m}{mark}".format(i=i, k=k, m=MODELS[k], mark=mark))
    while True:
        c = input(_("\nModel number (Enter = keep current): ")).strip()
        if not c:
            return current or MODELS[keys[0]]
        if c.isdigit() and 1 <= int(c) <= len(keys):
            return MODELS[keys[int(c) - 1]]
        print(_("Enter a valid number."))


def resolve_model(name: str | None, default: str = "gpt-6-luna") -> str:
    return MODELS.get(name or "", name or default)


# ─────────────────── chat loop with / commands ───────────────────

HELP = _("\nCommands in chat:\n") + "\n".join([
    _("  /img <path> [path2 ...]   Attach image(s) to the next message "
      "(auto-converted to WebP)"),
    _("  /file <path> [path2 ...]  Attach text/code file(s) to the next message"),
    _("  /draw <prompt>            Generate an image (e.g. /draw a starry sky)"),
    _("  /model                    Switch model"),
    _("  /mic                      Record the microphone, transcribe and send"),
    _("  /live                     Live two-way voice chat (like a phone call — use headphones)"),
    _("  /clear                    Clear the chat memory"),
    _("  /exit or empty Enter      Quit"),
    _("To send a normal message with an image/file: first run /img or /file, then type your text."),
])


def chat_loop(client: DuckAI, model: str, out_dir: str | None = None):
    print(_("\nChat started") + HELP + "-" * 55)
    history = []
    pending_images: list[dict] = []
    pending_files: list[str] = []
    while True:
        try:
            prompt = input(_("\nYou> ")).strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not prompt:
            break

        # ── voice commands ──
        if prompt == "/live":
            try:
                import duck_voice as dv
                dv.run_live(client, model)
            except Exception as e:
                print(_("[error] {e}").format(e=e))
            continue
        if prompt == "/mic":
            try:
                import duck_voice as dv
                dv.ensure_voice_deps()
                prompt = dv.record_and_transcribe(client, model)
                if not prompt:
                    continue
                print("-" * 55)
            except Exception as e:
                print(_("[error] {e}").format(e=e))
                continue
        # ── commands ──
        if prompt.startswith("/"):
            parts = prompt.split(maxsplit=1)
            cmd = parts[0].lower()
            arg = parts[1].strip() if len(parts) > 1 else ""
            if cmd == "/exit":
                break
            if cmd == "/model":
                model = choose_model(model)
                print(_("Current model: {model}").format(model=model))
                continue
            if cmd == "/clear":
                history.clear()
                print(_("Chat memory cleared."))
                continue
            if cmd == "/help":
                print(HELP)
                continue
            if cmd == "/img":
                if not arg:
                    print(_("Give an image path: /img photo.jpg"))
                    continue
                try:
                    added = arg.replace('"', " ").split()
                    for p in added:
                        pending_images.append(image_to_data_url(p))
                    print(_("✔ {n} image(s) ready to send with your next message.")
                          .format(n=len(added)))
                except Exception as e:
                    print(_("[error] {e}").format(e=e))
                continue
            if cmd == "/file":
                if not arg:
                    print(_("Give a file path: /file main.py"))
                    continue
                added = arg.replace('"', " ").split()
                pending_files.extend(added)
                print(_("✔ {n} file(s) ready to send with your next message.")
                      .format(n=len(added)))
                continue
            if cmd == "/draw":
                if not arg:
                    print(_("Give a prompt: /draw a cute orange cat"))
                    continue
                print("\n🎨 " + _("Drawing…"), flush=True)
                try:
                    def prog(kind, val):
                        if kind == "title":
                            print("   🖌 " + val, flush=True)
                        elif kind == "partial":
                            pass  # progressive previews are silenced

                    path, text, info = client.generate_image(
                        arg, model=model, out_dir=out_dir, on_progress=prog,
                        history=history)
                    size_kb = os.path.getsize(path) // 1024
                    print(_("✔ Image saved: {path}  ({w}×{h}, {kb} KB)")
                          .format(path=path, w=info.get("width"),
                                  h=info.get("height"), kb=size_kb))
                    if text:
                        print(text)
                    # keep it in history like the browser (for edits / follow-ups)
                    history.append({"role": "user",
                                    "content": [{"type": "text", "text": arg}]})
                    history.append({"role": "assistant", "content": "", "parts": [
                        {"type": "generated-image", "result": info["b64"],
                         "width": info.get("width"), "height": info.get("height"),
                         "format": info.get("format", "jpeg")},
                        {"type": "text", "text": text or ""},
                    ]})
                except Exception as e:
                    print(_("[error] {e}").format(e=e))
                continue
            print(_("Unknown command. See /help."))
            continue

        # ── normal message (+ pending attachments) ──
        print("\n…", end="", flush=True)
        try:
            prompt_extra = ""
            for f in pending_files:
                prompt_extra += file_to_prompt_chunk(f)
            parts = []
            for delta in client.stream(prompt, model=model, history=history,
                                       images=pending_images or None,
                                       prompt_extra=prompt_extra):
                parts.append(delta)
                print(delta, end="", flush=True)
            answer = "".join(parts)
            content = [{"type": "text", "text": prompt + prompt_extra}]
            content.extend(pending_images)
            history.append({"role": "user", "content": content})
            history.append({"role": "assistant", "content": answer})
            print("\n")
        except Exception as e:
            print("\n" + _("[error] {e}").format(e=e))
        finally:
            pending_images.clear()
            pending_files.clear()
    print("-" * 55)


def draw_once(client: DuckAI, prompt: str, model: str, out_dir: str | None):
    print(_("\n🎨 Generating image: “{prompt}”").format(prompt=prompt))
    try:
        def prog(kind, val):
            if kind == "title":
                print("   🖌 " + val, flush=True)

        path, text, info = client.generate_image(prompt, model=model,
                                                 out_dir=out_dir, on_progress=prog)
        size_kb = os.path.getsize(path) // 1024
        print(_("✔ Saved: {path}  ({w}×{h}, {kb} KB)")
              .format(path=path, w=info.get("width"), h=info.get("height"), kb=size_kb))
        if text:
            print(text)
    except Exception as e:
        print(_("[error] {e}").format(e=e))
        sys.exit(2)


def main():
    parser = argparse.ArgumentParser(
        prog="duck_cli",
        description="DuckDuckGo AI Chat CLI (free, unofficial)")
    parser.add_argument("--ask", help=_("one-off question (non-interactive)"))
    parser.add_argument("--image", nargs="+", default=[],
                        help=_("path(s) of one or more images (auto-converted to WebP)"))
    parser.add_argument("--file", nargs="+", default=[],
                        help=_("path(s) of one or more text/code files"))
    parser.add_argument("--draw", help=_("generate an image from a text prompt (non-interactive)"))
    parser.add_argument("--out", help=_("folder for generated images (default: current folder)"))
    parser.add_argument("--model", default=None,
                        help=_("luna | mini | haiku | mistral | oss | gemma "
                               "| gpt-6-luna | ..."))
    parser.add_argument("--proxy",
                        help=_("http://host:port or socks5://host:port (socks needs: "
                               "pip install 'requests[socks]')"))
    parser.add_argument("--chat", action="store_true", help=_("interactive continuous chat"))
    parser.add_argument("--voice", action="store_true",
                        help=_("live two-way voice chat (WebRTC — like a phone call)"))
    parser.add_argument("--listen", action="store_true",
                        help=_("record the microphone and transcribe to text (Enter = stop)"))
    parser.add_argument("--dictate", metavar="FILE",
                        help=_("transcribe an audio file (wav/mp3/m4a/webm/...) to text"))
    parser.add_argument("--lang", choices=("en", "fa"), default=None,
                        help=_("UI language: en or fa (default: DUCKAI_LANG env or en)"))
    parser.add_argument("--version", action="version",
                        version="%(prog)s " + __version__,
                        help=_("show version and exit"))
    args = parser.parse_args()

    if args.lang:
        set_lang(args.lang)

    model = resolve_model(args.model)
    out_dir = args.out

    if args.draw:
        draw_once(DuckAI(proxy=args.proxy), args.draw, model, out_dir)
        return

    if args.dictate:
        import duck_voice as dv
        try:
            print(dv.transcribe_file(DuckAI(proxy=args.proxy), args.dictate, model))
        except Exception as e:
            print(_("[error] {e}").format(e=e))
            sys.exit(2)
        return

    if args.listen:
        import duck_voice as dv
        try:
            print(dv.record_and_transcribe(DuckAI(proxy=args.proxy), model))
        except Exception as e:
            print(_("[error] {e}").format(e=e))
            sys.exit(2)
        return

    if args.voice:
        print_header()
        import duck_voice as dv
        dv.run_live(DuckAI(proxy=args.proxy), model)
        return

    if args.ask:
        client = DuckAI(proxy=args.proxy)
        try:
            imgs = images_to_parts(args.image) if args.image else None
            answer = client.ask(args.ask, model=model,
                                on_delta=lambda d: print(d, end="", flush=True),
                                images=imgs, files=args.file or None)
            print()
        except Exception as e:
            print(_("[error] {e}").format(e=e))
            sys.exit(2)
        return

    if args.chat:
        print_header()
        print(_("Current model: {model}").format(model=model))
        if not HAS_PIL:
            print(_("⚠ Pillow is not installed — install it to send images:  "
                    "pip install pillow"))
        chat_loop(DuckAI(proxy=args.proxy), model, out_dir=out_dir)
        return

    print_header()
    if not HAS_PIL:
        print(_("⚠ Pillow is not installed — install it to send images:  "
                "pip install pillow"))
    while True:
        print(_("\nWhat do you want to do?"))
        print(_("  1. Text chat (with memory, images and files)"))
        print(_("  2. One-off question"))
        print(_("  3. Generate an image 🎨"))
        print(_("  4. Change model"))
        print(_("  5. Live voice chat 🎙 (like a phone call)"))
        print(_("  6. Voice to text (microphone or audio file)"))
        print(_("  0. Exit"))
        choice = input(_("\nYour choice: ")).strip()
        if choice == "0":
            print(_("\nBye!\n"))
            break
        elif choice == "1":
            chat_loop(DuckAI(proxy=args.proxy), model, out_dir=out_dir)
        elif choice == "2":
            print(_("\nEnter your question (Enter to cancel):"))
            prompt = input("> ").strip()
            if not prompt:
                print(_("Cancelled."))
                continue
            img_p = input(_("Image path (optional, Enter = no image): ")).strip()
            try:
                imgs = images_to_parts([img_p]) if img_p else None
                print(_("\n[…] Getting the answer…\n") + "-" * 55)
                DuckAI(proxy=args.proxy).ask(
                    prompt, model=model,
                    on_delta=lambda d: print(d, end="", flush=True),
                    images=imgs)
                print("\n")
            except Exception as e:
                print(_("[error] {e}").format(e=e))
            print("-" * 55)
        elif choice == "3":
            prompt = input(_("\nImage prompt: ")).strip()
            if not prompt:
                print(_("Cancelled."))
                continue
            draw_once(DuckAI(proxy=args.proxy), prompt, model, out_dir)
            print("-" * 55)
        elif choice == "4":
            model = choose_model(model)
            print(_("Current model: {model}").format(model=model))
        elif choice == "5":
            try:
                import duck_voice as dv
                dv.run_live(DuckAI(proxy=args.proxy), model)
            except Exception as e:
                print(_("[error] {e}").format(e=e))
            print("-" * 55)
        elif choice == "6":
            try:
                import duck_voice as dv
                src_ = input(_("Audio file path (Enter = record from microphone): ")
                             ).strip().strip('"')
                c2 = DuckAI(proxy=args.proxy)
                if src_:
                    text = dv.transcribe_file(c2, src_, model)
                else:
                    text = dv.record_and_transcribe(c2, model)
                print(_("\nText:\n{text}\n").format(text=text))
                if input(_("Send it to chat? (y/n): ")).strip().lower() == "y":
                    print(_("\n[…] Getting the answer…"))
                    c2.ask(text, model=model,
                           on_delta=lambda d: print(d, end="", flush=True))
                    print()
            except Exception as e:
                print(_("[error] {e}").format(e=e))
            print("-" * 55)
        else:
            print(_("Enter a valid option."))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(_("\n\nProgram stopped."))
