# duck_i18n.py — tiny two-language helper for the DuckAi CLI.
#
# English is the default UI language. Persian is enabled either with
# the --lang fa flag or the DUCKAI_LANG=fa environment variable.
#
# Any string that has no Persian translation is returned unchanged,
# so adding new messages never breaks the program.

import os

_lang = (os.environ.get("DUCKAI_LANG", "") or "en").strip().lower()
if _lang not in ("en", "fa"):
    _lang = "en"


def set_lang(lang: str | None) -> None:
    global _lang
    if lang:
        _lang = lang if lang in ("en", "fa") else "en"


def get_lang() -> str:
    return _lang


# Persian translations, keyed by the exact English message.
_FA = {}

# duck_voice.py — setup / dependency messages
_FA.update({
    "Voice packages are not installed: {pkgs}  ->  pip install {pkgs}":
        "پکیج‌های ویس نصب نیستند: {pkgs}  ←  pip install {pkgs}",
    "sounddevice (microphone)": "sounddevice (میکروفون)",
    "av/PyAV (Opus codec)": "av/PyAV (کدک Opus)",
    "aiortc (WebRTC)": "aiortc (WebRTC)",
    "numpy (audio math)": "numpy (پردازش صدا)",
    "PyAV is not installed  ->  pip install av": "PyAV نصب نیست ← pip install av",
    "sounddevice is not installed  ->  pip install sounddevice":
        "sounddevice نصب نیست ← pip install sounddevice",
    "numpy is not installed  ->  pip install numpy": "numpy نصب نیست ← pip install numpy",
    "aiortc is not installed  ->  pip install aiortc": "aiortc نصب نیست ← pip install aiortc",
    "Failed to open audio file ({path}): {e}": "بازکردن فایل صوتی ناموفق ({path}): {e}",
    "No audio stream found in '{path}'.": "در «{path}» استریم صوتی پیدا نشد.",
    "🎙 Recording… (Enter = stop, max {secs} s)":
        "🎙 در حال ضبط… (Enter = پایان، حداکثر {secs} ثانیه)",
    "Microphone access failed: {e}": "دسترسی به میکروفون ناموفق: {e}",
    "No audio captured — check your microphone.":
        "صدایی ضبط نشد — میکروفون را چک کنید.",
    "Recording was too short (< 0.2 s).": "ضبط خیلی کوتاه بود (<۰.۲ ثانیه).",
    "Dictation response could not be parsed: {t}":
        "پاسخ دیکته قابل خواندن نبود: {t}",
    "Dictation failed: {j}": "دیکته ناموفق: {j}",
    "Dictation failed after {n} attempts: {e}":
        "دیکته پس از {n} تلاش ناموفق بود: {e}",
    "✔ Recorded ({kb} KB) — transcribing…":
        "✔ ضبط شد ({kb} KB) — در حال تبدیل به متن…",
    "Starting voice session failed (HTTP {code}): {t}":
        "شروع جلسه صوتی ناموفق (HTTP {code}): {t}",
    "Fetching ice-servers failed (HTTP {code})":
        "دریافت ice-servers ناموفق (HTTP {code})",
    "Attempt {n} failed: {e}": "تلاش {n} ناموفق: {e}",
    "Live voice connection failed: {e}": "اتصال ویس زنده ناموفق: {e}",
    "POST session failed after 5 attempts":
        "POST session پس از ۵ تلاش ناموفق بود",
    "datachannel did not open within 30 s (ICE failed)":
        "datachannel در ۳۰ ثانیه باز نشد (ICE ناموفق)",
    "TURN: {n} server(s)": "TURN: {n} سرور",
    "Audio input from file: {path}": "ورودی صوتی از فایل: {path}",
    "Microphone enabled": "میکروفون فعال شد",
    "answer SDP applied — connecting ICE…":
        "answer SDP اعمال شد — در حال اتصال ICE…",
    "POST session attempt {n} failed: {e}":
        "POST session تلاش {n} ناموفق: {e}",
    # live_status_printer
    "  ✔ Connected — start talking (Enter = end)":
        "  ✔ اتصال برقرار شد — صحبت کنید (Enter = پایان)",
    "\n  (File finished — waiting for the answer…)":
        "\n  (پخش فایل تمام شد — در انتظار پاسخ…)",
    "\n  You: {val}": "\n  شما: {val}",
    "\n  🔍 Searching the web…": "\n  🔍 در حال جستجوی وب…",
    "\n  🔧 Tool: {val}": "\n  🔧 ابزار: {val}",
    "\n  (Response status: {val})": "\n  (وضعیت پاسخ: {val})",
    "\n  ✘ Voice session closed.": "\n  ✘ جلسه صوتی بسته شد.",
    "\n  [dc error] {val}": "\n  [dc خطا] {val}",
    "\n  (Session end reason: {val})": "\n  (دلیل پایان جلسه: {val})",
    "\n🎙 Live voice started (connecting…) — Enter = end":
        "\n🎙 گفتگوی زنده شروع شد (در حال اتصال…) — Enter = پایان",
    "  ⚠ Wear headphones so speaker audio does not feed the microphone.":
        "  ⚠ هندزفری بزنید تا صدای بلندگو وارد میکروفون نشود.",
    "Live voice summary:": "خلاصه گفتگوی زنده:",
    "You": "شما",
    "Assistant": "دستیار",
})

# duck_cli.py — image / file helpers
_FA.update({
    "Image file not found: {path}": "فایل تصویر پیدا نشد: {path}",
    "Image is too large and Pillow is not installed: {path}":
        "تصویر خیلی بزرگ است و Pillow نصب نیست: {path}",
    "Failed to open image ({path}): {e}": "بازکردن تصویر ناموفق ({path}): {e}",
    "Image is still too large after compression: {path}":
        "تصویر پس از فشرده‌سازی همچنان بزرگ است: {path}",
    "File not found: {path}": "فایل پیدا نشد: {path}",
    "'{name}' is not a text file. duck.ai only accepts images (WebP) and "
    "text; binary files cannot be sent.":
        "«{name}» فایل متنی نیست. duck.ai فقط تصویر (WebP) و متن را می‌پذیرد؛ "
        "فایل‌های باینری قابل ارسال نیستند.",
    "Failed to read file ({path}): {e}": "خواندن فایل ناموفق ({path}): {e}",
    "\n\nContent of file '{name}':\n```{lang}\n{content}\n```{trunc}\n":
        "\n\nمحتوای فایل «{name}»:\n```{lang}\n{content}\n```{trunc}\n",
    "\n\n[The file was long and got truncated to {max} characters]":
        "\n\n[… فایل طولانی بود و به {max} کاراکتر برش خورد]",
    "text": "text",
})

# duck_cli.py — DuckAI class / network
_FA.update({
    "jsa_jsdom.js not found — it must sit next to this script":
        "jsa_jsdom.js پیدا نشد — باید کنار همین اسکریپت باشد",
    "Node.js was not found on PATH. Install it from https://nodejs.org "
    "and then run:  npm install":
        "Node.js در PATH پیدا نشد. آن را از https://nodejs.org نصب کنید و "
        "بعد در همین پوشه اجرا کنید:  npm install",
    "The 'jsdom' package is missing. Run this in the project folder:  npm install":
        "پکیج «jsdom» نصب نیست. در پوشه پروژه اجرا کنید:  npm install",
    "Challenge execution failed: {e}": "اجرای چالش ناموفق: {e}",
    "Error inside challenge: {e}": "خطای داخل چالش: {e}",
    "No challenge received (HTTP {code}): {t}":
        "چالشی دریافت نشد (HTTP {code}): {t}",
    "Chat failed after {n} attempts: {e}":
        "چت پس از {n} تلاش ناموفق بود: {e}",
    "Server error ({status}): {t}": "خطای سرور ({status}): {t}",
    "No image in the response{extra}": "تصویری در پاسخ نبود{extra}",
    " (tool did not run?)": " (ابزار اجرا نشد؟)",
})

# duck_cli.py — terminal UI
_FA.update({
    "DuckDuckGo AI Chat — unofficial free client (no API key)":
        "DuckDuckGo AI Chat — کلاینت غیررسمی رایگان (بدون کلید API)",
    "See images ✔  Make images ✔  Read files ✔  Switch models ✔":
        "تصویر ببین ✔  تصویر بساز ✔  فایل بخوان ✔  مدل عوض کن ✔",
    "Language: {lang}  (change with --lang en|fa or DUCKAI_LANG=fa)":
        "زبان: {lang}  (با --lang en|fa یا DUCKAI_LANG=fa عوض کنید)",
    "\nPick a model:": "\nمدل را انتخاب کنید:",
    "  ← now": "  ← الان",
    "\nModel number (Enter = keep current): ":
        "\nشماره مدل (Enter = بدون تغییر): ",
    "Enter a valid number.": "شماره معتبر وارد کنید.",
    "\nCommands in chat:\n": "\nدستورها در گفتگو:\n",
    "  /img <path> [path2 ...]   Attach image(s) to the next message "
    "(auto-converted to WebP)":
        "  /img <مسیر> [مسیر2 ...]   اضافه‌کردن تصویر به پیام بعدی (خودکار به WebP تبدیل می‌شود)",
    "  /file <path> [path2 ...]  Attach text/code file(s) to the next message":
        "  /file <مسیر> [مسیر2 ...]  پیوست فایل متنی/کد به پیام بعدی",
    "  /draw <prompt>            Generate an image (e.g. /draw a starry sky)":
        "  /draw <توضیح>             ساخت تصویر (مثال: /draw یک آسمان پرستاره)",
    "  /model                    Switch model": "  /model                    تغییر مدل",
    "  /mic                      Record the microphone, transcribe and send":
        "  /mic                      ضبط صدای میکروفون، تبدیل به متن و ارسال",
    "  /live                     Live two-way voice chat (like a phone call — use headphones)":
        "  /live                     گفتگوی زنده صوتی (تماس دوطرفه — هندزفری بزن)",
    "  /clear                    Clear the chat memory": "  /clear                    پاک‌کردن حافظه گفتگو",
    "  /exit or empty Enter      Quit": "  /exit یا Enter خالی       پایان",
    "To send a normal message with an image/file: first run /img or /file, then type your text.":
        "پیام معمولی + تصویر/فایل در انتظار:  اول /img یا /file بزن، بعد متن را بنویس.",
    "\nChat started": "\nگفتگو شروع شد",
    "\nYou> ": "\nشما> ",
    "Current model: {model}": "مدل فعلی: {model}",
    "Chat memory cleared.": "حافظه گفتگو پاک شد.",
    "Give an image path: /img photo.jpg": "مسیر تصویر بده: /img عکس.jpg",
    "✔ {n} image(s) ready to send with your next message.":
        "✔ {n} تصویر آماده ارسال در پیام بعدی.",
    "Give a file path: /file main.py": "مسیر فایل بده: /file main.py",
    "✔ {n} file(s) ready to send with your next message.":
        "✔ {n} فایل آماده ارسال در پیام بعدی.",
    "\n🎨 Drawing…": "\n🎨 در حال کشیدن…",
    "✔ Image saved: {path}  ({w}×{h}, {kb} KB)":
        "✔ تصویر ذخیره شد: {path}  ({w}×{h}، {kb} KB)",
    "Unknown command. See /help.": "دستور ناشناخته. /help را ببین.",
    "[error] {e}": "[خطا] {e}",
    "\n🎨 Generating image: “{prompt}”": "\n🎨 در حال تولید تصویر: «{prompt}»",
    "✔ Saved: {path}  ({w}×{h}, {kb} KB)":
        "✔ ذخیره شد: {path}  ({w}×{h}، {kb} KB)",
    "one-off question (non-interactive)": "سؤال تک‌باره (غیرتعاملی)",
    "path(s) of one or more images (auto-converted to WebP)":
        "مسیر یک یا چند تصویر (خودکار به WebP تبدیل می‌شود)",
    "path(s) of one or more text/code files":
        "مسیر یک یا چند فایل متنی/کد",
    "generate an image from a text prompt (non-interactive)":
        "تولید تصویر از توضیح متنی (غیرتعاملی)",
    "folder for generated images (default: current folder)":
        "پوشه ذخیره تصاویر ساخته‌شده (پیش‌فرض: همین پوشه)",
    "luna | mini | nano | haiku | mistral | gpt-6-luna | ...":
        "luna | mini | nano | haiku | mistral | gpt-6-luna | ...",
    "http://host:port or socks5://host:port (socks needs: pip install 'requests[socks]')":
        "http://host:port یا socks5://host:port (برای socks: pip install 'requests[socks]')",
    "interactive continuous chat": "گفتگوی پیوسته تعاملی",
    "live two-way voice chat (WebRTC — like a phone call)":
        "گفتگوی زنده صوتی دوطرفه (WebRTC — مثل تماس تلفنی)",
    "record the microphone and transcribe to text (Enter = stop)":
        "ضبط از میکروفون و تبدیل به متن (Enter = پایان)",
    "transcribe an audio file (wav/mp3/m4a/webm/...) to text":
        "تبدیل فایل صوتی (wav/mp3/m4a/webm/...) به متن",
    "UI language: en or fa (default: DUCKAI_LANG env or en)":
        "زبان رابط: en یا fa (پیش‌فرض: متغیر DUCKAI_LANG یا en)",
    "show version and exit": "نمایش نسخه و خروج",
    "⚠ Pillow is not installed — install it to send images:  pip install pillow":
        "⚠ Pillow نصب نیست — برای ارسال تصویر نصبش کن: pip install pillow",
    "\nWhat do you want to do?": "\nچه کاری می‌خوای انجام بدی؟",
    "  1. Text chat (with memory, images and files)":
        "  1. گفتگوی متنی (با حافظه، تصویر و فایل)",
    "  2. One-off question": "  2. یک سؤال تک‌باره",
    "  3. Generate an image 🎨": "  3. تولید تصویر 🎨",
    "  4. Change model": "  4. تغییر مدل",
    "  5. Live voice chat 🎙 (like a phone call)":
        "  5. گفتگوی زنده صوتی 🎙 (مثل تماس تلفنی)",
    "  6. Voice to text (microphone or audio file)":
        "  6. ویس به متن (میکروفون یا فایل صوتی)",
    "  0. Exit": "  0. خروج",
    "\nYour choice: ": "\nانتخاب شما: ",
    "\nBye!\n": "\nخداحافظ!\n",
    "\nEnter your question (Enter to cancel):":
        "\nسؤال خود را وارد کنید (برای لغو Enter بزنید):",
    "Image path (optional, Enter = no image): ":
        "مسیر تصویر (اختیاری، Enter = بدون تصویر): ",
    "\n[…] Getting the answer…\n": "\n[…] در حال دریافت پاسخ…\n",
    "Cancelled.": "لغو شد.",
    "\nImage prompt: ": "\nتوضیح تصویر: ",
    "Audio file path (Enter = record from microphone): ":
        "مسیر فایل صوتی (Enter = ضبط از میکروفون): ",
    "\nText:\n{text}\n": "\nمتن:\n{text}\n",
    "Send it to chat? (y/n): ": "ارسال به چت؟ (y/n): ",
    "Enter a valid option.": "گزینه معتبر وارد کنید.",
    "\n\nProgram stopped.": "\n\nبرنامه متوقف شد.",
    "Version {v}": "نسخه {v}",
})


def _(s: str) -> str:
    """Translate an English message template; unknown strings pass through."""
    if _lang == "fa":
        return _FA.get(s, s)
    return s
