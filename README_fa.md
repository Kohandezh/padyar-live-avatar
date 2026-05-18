# Padyar Live Avatar

**لایه‌ی Runtime و Orchestration بلادرنگ برای اکوسیستم آواتار هوشمند پادیار**

## ساختار Monorepo

| مسیر | نقش |
|---|---|
| `src/padyar_live/` | Runtime بلادرنگ — پخش WebSocket، زمان‌بندی، نشست‌ها، تأخیر، EngineAdapter |
| `tests/` | مجموعه تست Runtime (۵۴ تست، با حاکمیت معماری) |
| `mobile/padyar-android/` | SDK اندروید — آواتار ۲D آفلاین، lip-sync با NCNN |
| `mobile/padyar-ios/` | SDK iOS — آواتار ۲D آفلاین، رندر محلی |
| `PadYar-LipSync-master/` | مرجع تاریخی موتور پردازشی (اسنپ‌شات، توسط runtime وارد نمی‌شود) |
| `res/` | دارایی‌های محصول / آواتار |

## Runtime چه کار می‌کند

- پخش جریانی WebSocket (`/ws/live`) — فریم‌های باینری دوطرفه با keepalive
- صف فریم ناهمگام و زمان‌بندی chunk با کنترل backpressure
- مدیریت چرخه‌ی حیات نشست‌ها (ایجاد، بروزرسانی، بستن، انقضای TTL، تشخیص بیکاری)
- اندازه‌گیری تأخیر (میانگین، p95، p99، نرخ fallback)
- بازیابی خطا و ارائه فریم‌های جایگزین هنگام خرابی موتور
- API استاندارد برای مدیریت نشست‌ها و معیارها (`/health`, `/session`, `/metrics`)

## Runtime چه کار نمی‌کند

این مخزن **مالک** مدل‌های هوش مصنوعی نیست و شامل UNet، VAE، Whisper، TTS یا وزن‌های مدل نمی‌شود.

تمام ارتباط با موتورهای پردازشی **فقط** از طریق رابط `EngineAdapter` انجام می‌شود. همه‌ی پردازش‌های هوش مصنوعی در موتور خارجی PadYar-LipSync اجرا می‌شود.

## معماری

```
┌──────────────────┐
│   اپلیکیشن       │
│ (موبایل / وب)    │
└────────┬─────────┘
         │ WebSocket / REST
         ▼
┌──────────────────┐
│ padyar-live-     │  ← این مخزن (runtime)
│ avatar           │
│  FastAPI + WS    │
│  Scheduler       │
│  EngineAdapter   │  ← فقط فراخوانی خارجی
└────────┬─────────┘
         │ HTTP/gRPC
         ▼
┌──────────────────┐
│ PadYar-LipSync   │  ← موتور پردازشی (مخزن مجزا)
└──────────────────┘
```

| لایه | نقش | وضعیت |
|---|---|---|
| **PadYar-LipSync** | موتور پردازشی (UNet، VAE، Whisper، TTS) | پایدار — آماده‌ی تولید |
| **padyar-live-avatar** | لایه‌ی runtime (پخش جریانی، زمان‌بندی، نشست‌ها) | در حال توسعه |
| **PadYarAvatar** | لایه‌ی شناخت (حافظه، شخصیت، احساسات) | شروع نشده |

## اهمیت برای مسیر دانش‌بنیان

- **تفکیک معماری:** جداسازی کامل Runtime از Inference
- **تست‌پذیری:** ۵۴ تست خودکار بدون نیاز به GPU
- **کنترل وابستگی‌ها:** تست‌های خودکار برای جلوگیری از ورود کتابخانه‌های غیرمجاز
- **CI خودکار:** GitHub Actions — lint، type-check، تست، بررسی معماری
- **مستندات امنیتی:** تحلیل سطح حمله و راه‌کارها
- **قابلیت توسعه:** هر موتور جدید با پیاده‌سازی EngineAdapter قابل جایگزینی

## وضعیت فعلی

```
ruff:   همه بررسی‌ها موفق
mypy:   بدون خطا در ۱۸ فایل
pytest: ۵۴ تست موفق
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

| تست | آنچه اعمال می‌کند |
|---|---|
| `test_governance_imports` | عدم وارد کردن فریمورک‌های ML |
| `test_governance_deps` | عدم نصب پکیج‌های ML |
| `test_governance_architecture` | قرارداد Adapter، لایه‌بندی، عدم وابستگی دوری |

## وابستگی‌ها

Runtime (حداقل): FastAPI, Uvicorn, Pydantic

توسعه: pytest, pytest-asyncio, httpx, ruff, black, mypy, pre-commit

**ممنوع:** torch, transformers, diffusers, onnxruntime, whisper, mediapipe, ultralytics, celery, redis, kafka

---

Powered by Mohammad Kohandezh — KSF Company
Contact: info@ksf.ir
