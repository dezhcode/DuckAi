# 🦆 DuckAi — راهنمای فارسی

یک **کلاینت خط فرمان رایگان و غیررسمی برای DuckDuckGo AI Chat (duck.ai)** — بدون کلید API، بدون حساب کاربری، بدون اشتراک.

> ⚠️ **سلب مسئولیت:** این پروژه به DuckDuckGo هیچ وابستگی یا تأییدی ندارد و از یک اندپوینت خصوصی و مستندنشده استفاده می‌کند؛ ممکن است هر زمان از کار بیفتد. فقط برای استفاده شخصی و آموزشی باشد و قوانین DuckDuckGo را رعایت کنید. از سرویس سوءاستفاده نکنید.

*(راهنمای انگلیسی: [README.md](README.md))*

## ✨ امکانات

- 💬 **گفتگوی متنی** با پاسخ استریمی و حافظهٔ گفتگو
- 🖼️ **ارسال تصویر** (JPG / PNG / WebP / BMP… — خودکار به WebP تبدیل می‌شود) و پرسیدن سؤال درباره‌اش
- 📎 **پیوست فایل متنی/کد** (`.py`، `.js`، `.json`، `.md` و…) به پرامپت
- 🎨 **تولید تصویر** از توضیح متنی (خروجی JPEG)
- 🎙️ **دیکته** — ضبط میکروفون یا هر فایل صوتی و گرفتن متن
- 📞 **گفتگوی زنده صوتی** — تماس دوطرفهٔ واقعی WebRTC با هوش مصنوعی (مثل تماس تلفنی)
- 🔀 **تغییر مدل** — `gpt-6-luna`، `gpt-5.6-luna`، `gpt-5.4-mini`، `gpt-5.4-nano`، `claude-haiku-4-5`، `mistral-small-2603`
- 🌐 **پشتیبانی از پروکسی** (HTTP / SOCKS5)
- 🌍 **رابط دوزبانه** — انگلیسی (پیش‌فرض) و فارسی (`--lang fa`)

## 📦 نصب

### ۱. پیش‌نیازها

| پیش‌نیاز | توضیح |
|---|---|
| **Python نسخه ۳.۱۰ یا بالاتر** | از [python.org](https://www.python.org/downloads/) — در ویندوز حتماً تیک *Add python.exe to PATH* را بزنید |
| **Node.js نسخه ۱۸ یا بالاتر** | از [nodejs.org](https://nodejs.org/) — برای حل چالش duck.ai لازم است |

### ۲. گرفتن پروژه

```bash
git clone https://github.com/<YOUR-USERNAME>/DuckAi.git
cd DuckAi
```
*(یا فایل ZIP را دانلود و باز کنید)*

### ۳. نصب وابستگی‌ها

```bash
# پکیج‌های پایتون (اصلی)
pip install -r requirements.txt

# پکیج Node (jsdom — ضروری)
npm install
```

**اختیاری — فقط برای قابلیت‌های صوتی:**

```bash
pip install -r requirements-voice.txt
```

> اگر از پروکسی **SOCKS5** استفاده می‌کنید، این را هم بزنید: `pip install "requests[socks]"`

## 🚀 اجرا

### منوی تعاملی (ساده‌ترین راه)

```bash
python duck_cli.py
```

منویی شماره‌دار می‌بینید: گفتگوی متنی، سؤال تک‌باره، تولید تصویر، تغییر مدل، گفتگوی زندهٔ صوتی، ویس به متن.

### یک سؤال تک‌باره

```bash
python duck_cli.py --ask "DNS را در یک پاراگراف توضیح بده"
```

### گفتگوی پیوسته با حافظه

```bash
python duck_cli.py --chat
```

دستورهای داخل گفتگو:

| دستور | توضیح |
|---|---|
| `/img عکس.jpg` | پیوست‌کردن تصویر(ها) به پیام بعدی |
| `/file main.py` | پیوست‌کردن فایل متنی/کد به پیام بعدی |
| `/draw یک آسمان پرستاره` | تولید تصویر |
| `/model` | تغییر مدل |
| `/mic` | ضبط میکروفون ← تبدیل به متن ← ارسال |
| `/live` | گفتگوی زندهٔ صوتی دوطرفه (**حتماً هندزفری بزنید!**) |
| `/clear` | پاک‌کردن حافظهٔ گفتگو |
| `/exit` (یا Enter خالی) | خروج |

### فرستادن تصویر همراه سؤال

```bash
python duck_cli.py --ask "تو این عکس چیه؟" --image photo.jpg
```
چند تصویر: `--image a.jpg b.png`

### پرسیدن سؤال درباره یک فایل کد

```bash
python duck_cli.py --ask "این کد چه‌کار می‌کند؟" --file main.py
```
چند فایل: `--file main.py utils.py`

### تولید تصویر

```bash
python duck_cli.py --draw "یک گربه نارنجی بامزه روی طاقچه"
```
فایل JPEG در پوشهٔ فعلی ذخیره می‌شود (یا با `--out مسیر/پوشه` پوشهٔ دلخواه).

### صدا

```bash
# ضبط میکروفون و چاپ متن (Enter = پایان ضبط)
python duck_cli.py --listen

# تبدیل یک فایل صوتی موجود به متن (wav/mp3/m4a/webm/...)
python duck_cli.py --dictate recording.mp3

# تماس زندهٔ صوتی دوطرفه با هوش مصنوعی
python duck_cli.py --voice
```

### انتخاب مدل

```bash
python duck_cli.py --ask "سلام" --model mini      # gpt-5.4-mini
python duck_cli.py --ask "سلام" --model haiku     # claude-haiku-4-5
python duck_cli.py --ask "سلام" --model mistral   # mistral-small-2603
```

### پروکسی

```bash
python duck_cli.py --ask "سلام" --proxy http://127.0.0.1:8080
python duck_cli.py --ask "سلام" --proxy socks5://127.0.0.1:1080
```

### تغییر زبان رابط

```bash
python duck_cli.py --lang fa          # فقط برای همین اجرا
set DUCKAI_LANG=fa                    # ویندوز (دائمی: setx DUCKAI_LANG fa)
export DUCKAI_LANG=fa                 # لینوکس / مک
```

## 🔧 چطور کار می‌کند (فنی)

1. `GET https://duck.ai/` ← استخراج `data-version-tag` و `data-version-sha` ← ساخت `x-fe-version`
2. `GET /duckchat/v1/status` (با هدر `x-vqd-accept: 1`) ← برمی‌گرداند `x-vqd-hash-1`: یک چالش جاوااسکریپت کدشده با base64
3. چالش به‌صورت محلی با **Node.js + jsdom** حل می‌شود (`jsa_jsdom.js`) — بدون نیاز به مرورگر واقعی
4. جواب چالش در قالب نهایی `x-vqd-hash-1` بسته‌بندی می‌شود (`client_hashes` = base64ِ sha256)
5. `POST /duckchat/v1/chat` پاسخ را به‌صورت رویدادهای **SSE** استریم می‌کند

تولید تصویر با `metadata = {"toolChoice": {"GenerateImage": true}}` و خواندن رویدادهای `ui-component / generate-image` انجام می‌شود. ویس زنده از `GET /duckchat/v1/ice-servers` و `POST /duckchat/v1/session` استفاده می‌کند (WebRTC، صدای Opus، VAD سمت سرور، رویدادها روی datachannel به نام `duckai-voice-session`).

## 🐞 رفع اشکال

| مشکل | راه‌حل |
|---|---|
| `Node.js was not found on PATH` | Node.js را از [nodejs.org](https://nodejs.org) نصب کنید و ترمینال را دوباره باز کنید |
| `The 'jsdom' package is missing` | داخل **پوشهٔ پروژه** دستور `npm install` را اجرا کنید |
| `No challenge received (HTTP 403)` | احتمالاً IP شما محدود شده — صبر کنید یا از `--proxy` استفاده کنید |
| `Chat failed after 4 attempts` | duck.ai چیزی را عوض کرده یا پروکسی جلوی شما را می‌گیرد — بعداً دوباره امتحان کنید |
| متن فارسی به‌هم‌ریخته در ویندوز | اول `chcp 65001` را بزنید یا از Windows Terminal استفاده کنید |
| خطای میکروفون | پکیج‌های صوتی را نصب کنید: `pip install -r requirements-voice.txt` |
| ویس زنده صدای خودش را می‌شنود | هندزفری بزنید — اکوی بلندگو VAD سرور را گمراه می‌کند |
| هشدار Pillow | `pip install pillow` (برای تبدیل تصویر لازم است) |

## 📁 ساختار پروژه

```
DuckAi/
├── duck_cli.py        # CLI اصلی: چت، تصویر، فایل، تولید تصویر
├── duck_voice.py      # دیکته + جلسهٔ ویس زندهٔ WebRTC
├── duck_i18n.py       # متن‌های دوزبانهٔ رابط
├── jsa_jsdom.js       # اجراکنندهٔ Node برای حل چالش duck.ai
├── requirements.txt   # وابستگی‌های اصلی پایتون
├── requirements-voice.txt  # وابستگی‌های اختیاری صوتی
├── package.json       # وابستگی‌های Node (jsdom)
└── README.md / README.fa.md
```

## 📜 مجوز

MIT — فایل [LICENSE](LICENSE) را ببینید. استفاده با مسئولیت خودتان است؛ این ابزار غیررسمی است.
