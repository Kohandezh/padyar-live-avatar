# Padyar Live Avatar

**لایه‌ی Runtime و Orchestration بلادرنگ برای اکوسیستم آواتار هوشمند پادیار**

این مخزن مسئول پخش جریانی (WebSocket Streaming)، زمان‌بندی ناهمگام (Async Scheduling)، مدیریت چرخه‌ی حیات نشست‌ها، ردیابی تأخیر، بازیابی خطا، و هماهنگی موتورهای پردازشی است.

## این مخزن چه کار می‌کند

- پخش جریانی WebSocket (`/ws/live`) — فریم‌های باینری دوطرفه با keepalive
- صف فریم ناهمگام و زمان‌بندی chunk با کنترل فشار معکوس (backpressure)
- مدیریت چرخه‌ی حیات نشست‌ها (ایجاد، بروزرسانی، بستن، انقضای TTL، تشخیص بیکاری)
- اندازه‌گیری تأخیر (میانگین، p95، p99، نرخ fallback هر فریم)
- بازیابی خطا و ارائه فریم‌های جایگزین هنگام خرابی موتور
- API استاندارد برای مدیریت نشست‌ها و معیارها (`/health`, `/session`, `/metrics`)

## این مخزن چه کار نمی‌کند

این مخزن **مالک** مدل‌های هوش مصنوعی نیست و شامل UNet، VAE، Whisper، TTS یا وزن‌های مدل نمی‌شود.

تمام ارتباط با موتورهای پردازشی **فقط** از طریق رابط `EngineAdapter` انجام می‌شود. همه‌ی پردازش‌های هوش مصنوعی در موتور خارجی PadYar-LipSync اجرا می‌شود.

## معماری

```
┌──────────────────┐
│   اپلیکیشن       │
│   کاربر          │
└────────┬─────────┘
         │ WebSocket / REST
         ▼
┌──────────────────┐
│ padyar-live-     │  ← این مخزن
│ avatar           │
│                  │
│  FastAPI + WS    │
│  Scheduler       │
│  EngineAdapter   │  ← فقط فراخوانی خارجی
└────────┬─────────┘
         │ HTTP
         ▼
┌──────────────────┐
│ PadYar-LipSync   │  ← موتور پردازشی پایدار
│ (مخزن مجزا)     │
│  UNet, VAE,      │
│  Whisper, TTS    │
└──────────────────┘
```

| مخزن | نقش | وضعیت |
|------|-----|--------|
| **PadYar-LipSync** | موتور پردازشی پایدار (UNet، VAE، Whisper، TTS، پردازش چهره) | پایدار — آماده‌ی تولید |
| **padyar-live-avatar** | لایه‌ی هماهنگی بلادرنگ (پخش جریانی، زمان‌بندی، نشست‌ها، تأخیر) | در حال توسعه |
| **PadYarAvatar** | لایه‌ی شناخت آینده (حافظه، شخصیت، احساسات، عوامل هوشمند) | شروع نشده |

## اهمیت برای مسیر دانش‌بنیان

این مخزن با رعایت اصول مهندسی نرم‌افزار زیر، زیرساخت لازم برای کسب تأییدیه‌ی دانش‌بنیان را فراهم می‌کند:

- **تفکیک معماری:** جداسازی کامل لایه‌ی Runtime از لایه‌ی Inference — هر مخزن مسئولیت مشخصی دارد
- **تست‌پذیری:** ۵۴ تست خودکار که بدون نیاز به GPU اجرا می‌شوند — کل pipeline در کمتر از ۳ ثانیه تست می‌شود
- **کنترل وابستگی‌ها:** تست‌های خودکار که از ورود کتابخانه‌های غیرمجاز جلوگیری می‌کنند
- **CI خودکار:** GitHub Actions — lint، type-check، تست‌ها، و بررسی‌های معماری در هر push
- **مستندات امنیتی:** تحلیل سطح حمله و راه‌کارهای مقابله
- **قابلیت توسعه ماژولار:** هر موتور پردازشی جدید با پیاده‌سازی `EngineAdapter` قابل جایگزینی است بدون تغییر در کد Runtime

## وضعیت فعلی

```
ruff:   همه بررسی‌ها موفق
mypy:   بدون خطا در ۱۸ فایل
pytest: ۵۴ تست موفق در ۲.۷۷ ثانیه
```

## توسعه

### نصب

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pre-commit install
```

### اجرا

```bash
python -m padyar_live
# سرور روی http://0.0.0.0:8000 شروع می‌شود
```

### بررسی‌ها

```bash
ruff check src/ tests/                          # Lint
mypy src/padyar_live --ignore-missing-imports   # Type check
pytest tests/ -v                                # تست‌ها (۵۴ تست)
pytest tests/test_governance_*.py               # بررسی‌های معماری
```

## حاکمیت معماری

اجرای خودکار برای جلوگیری از نقض مرزها:

| تست | آنچه اعمال می‌کند |
|------|-------------------|
| `test_governance_imports` | عدم وارد کردن فریمورک‌های ML |
| `test_governance_deps` | عدم نصب پکیج‌های ML |
| `test_governance_architecture` | قرارداد Adapter، لایه‌بندی، عدم وابستگی دوری |

## مستندات

- `docs/ARCHITECTURE.md` — ساختار ماژول‌ها، جریان داده، استراتژی جایگزینی موتور
- `docs/BOUNDARIES.md` — مرزها، وابستگی‌های ممنوع، استراتژی بازگشت
- `docs/ADR/0001-runtime-engine-separation.md` — چرا Inference خارجی است
- `DEVELOPMENT.md` — نحوه افزودن endpoint، adapter، پیام WS
- `SECURITY.md` — سطح حمله و راه‌کارها
- `CONTRIBUTING.md` — قوانین مشارکت

## وابستگی‌ها

Runtime (حداقل):
- FastAPI, Uvicorn, Pydantic

توسعه:
- pytest, pytest-asyncio, httpx
- ruff, black, mypy, pre-commit

**ممنوع:** torch, transformers, diffusers, onnxruntime, whisper, mediapipe, ultralytics, celery, redis, kafka

---

Powered by: Mohammad Kohandezh — KSF Company
Contact: info@ksf.ir
