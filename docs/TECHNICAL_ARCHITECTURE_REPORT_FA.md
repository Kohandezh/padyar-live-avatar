# گزارش معماری فنی — Padyar Live Avatar

**Powered by:** Mohammad Kohandezh — KSF Company
**تماس:** info@ksf.ir

---

## ساختار مخزن

```
padyar-live-avatar/
├── src/padyar_live/              runtime بلادرنگ (تحت حاکمیت)
├── tests/                        تست‌های runtime (54 تست)
├── mobile/padyar-android/        SDK اندروید (مرجع)
├── mobile/padyar-ios/            SDK iOS (مرجع)
├── PadYar-LipSync-master/        اسنپشات تاریخی موتور استنتاج
├── res/                          دارایی‌های آواتار
├── docs/                         مستندات معماری و حاکمیت
├── pyproject.toml                پیکربندی بسته
├── CLAUDE.md                     مرجع حقیقت برای جلسات AI
├── README.md                     مستند عمومی (انگلیسی)
├── README_fa.md                  مستند عمومی (فارسی)
├── CONTRIBUTING.md               قوانین مشارکت
├── DEVELOPMENT.md                راهنمای توسعه
└── SECURITY.md                   سیاست امنیتی
```

## Runtime — src/padyar_live/

runtime هسته بلادرنگ سیستم است و تحت حاکمیت خودکار قرار دارد.

### ساختار ماژول‌ها

```
src/padyar_live/
├── api/
│   ├── app.py            کارخانه اپلیکیشن FastAPI، lifespan، خطای سراسری
│   ├── routes.py         نقاط پایانی REST (/health, /session, /metrics)
│   ├── ws.py             هندلر WebSocket (ping/pong، کدهای بسته‌شدن، خطا)
│   ├── ws_handlers.py    SchedulerFactory (یک زمان‌بند برای هر نشست)
│   └── metrics.py        MetricsCollector (تجمیع از زمان‌بندهای فعال)
├── adapters/
│   └── engine.py         EngineAdapter ABC + FakeEngineAdapter
├── runtime/
│   ├── config.py         RuntimeConfig (host, port, timeouts, queue sizes)
│   ├── session_manager.py مدیریت نشست: CRUD، TTL، تشخیص بیکاری، پاکسازی
│   └── latency.py        LatencyTracker (avg, p95, p99, نرخ fallback)
├── scheduler/
│   └── frame_scheduler.py صف ناهمگام، chunking، فشار معکوس، fallback
└── models/
    └── schemas.py        مدل‌های Pydantic برای تمام ورودی/خروجی‌ها
```

### WebSocket

- نقطه پایانی: `/ws/live`
- ارتباط دوطرفه با فریم‌های باینری
- پشتیبانی از ping/pong
- کدهای بسته‌شدن استاندارد و فریم‌های خطا
- یک زمان‌بند مجزا برای هر نشست

### مدیریت نشست (Session Lifecycle)

- ایجاد، به‌روزرسانی (touch)، بسته‌شدن، حذف
- TTL خودکار با انقضای نشست
- تشخیص بیکاری (idle detection)
- پاکسازی خودکار نشست‌های منقضی

### زمان‌بند فریم (Frame Scheduler)

- صف ناهمگام با مدیریت فشار معکوس (backpressure)
- زمان‌بندی chunk برای استریم
- ردیابی تأخیر هر فریم
- بازیابی خودکار در صورت خطا یا قطع موتور (fallback)

### ردیابی تأخیر (Latency Tracking)

- میانگین تأخیر هر فریم
- صدک 95 و صدک 99
- نرخ fallback
- تجمیع برای گزارش‌دهی

### رابط موتور (EngineAdapter)

```python
class EngineAdapter(ABC):
    @abstractmethod
    async def generate_frames(self, ...) -> AsyncIterator[bytes]: ...

    @abstractmethod
    async def health_check(self) -> bool: ...
```

- `generate_frames()` — تولید فریم‌های تصویری (JPEG)
- `health_check()` — بررسی سلامت موتور استنتاج
- `FakeEngineAdapter` — پیاده‌سازی تستی بدون نیاز به GPU

### نقاط پایانی REST

| متد | مسیر | عملکرد |
|---|---|---|
| GET | `/health` | بررسی سلامت سرویس |
| POST | `/session` | ایجاد نشست جدید |
| GET | `/session` | فهرست نشست‌ها |
| GET | `/session/{id}` | دریافت نشست |
| DELETE | `/session/{id}` | بستن نشست |
| GET | `/metrics` | گزارش تأخیر و آمار |

## SDK موبایل — mobile/

### mobile/padyar-android/

- SDK اندروید با Gradle
- پیاده‌سازی بومی C++/NCNN برای lip-sync آفلاین
- استریم PCM صوتی
- JNI bridge بین Java و C++
- کتابخانه بومی: `libgjpadyar.so`
- `applicationId`: `ai.guiji.padyar.test` (demo app)
- **وضعیت:** مرجع، build متوقف

### mobile/padyar-ios/

- SDK iOS با Xcode و CocoaPods
- رندرینگ Metal
- lip-sync آفلاین روی دستگاه
- targets: `GJLocalDigitalDemo` (demo), `GJLocalDigitalSDK` (framework)
- **وضعیت:** مرجع، build متوقف

## اسنپشات تاریخی موتور — PadYar-LipSync-master/

- اسنپشات تاریخی از موتور استنتاج Python PadYar-LipSync
- شامل: MuseTalk v1 و v1.5، Jupyter notebooks، realtime_inference.py، web UI
- **فقط مرجع.** وارد نشده، اجرا نشده، و نگهداری نمی‌شود
- موتور فعال PadYar-LipSync در مخزن مجزا قرار دارد

## دارایی‌ها — res/

- تصاویر پرتره آواتار
- ویدیوهای پیش‌رندر شده در رزولوشن‌های 270p و 540p

## واردات ممنوع (Forbidden Imports)

runtime نباید هیچ‌یک از موارد زیر را وارد کند:

```
torch, tensorflow, onnxruntime, diffusers, transformers,
whisper, mediapipe, ultralytics
celery, redis, kafka-python, ray, kubernetes
sqlalchemy, mongoengine
```

### وابستگی‌های مجاز

- runtime: FastAPI, Uvicorn, Pydantic
- development: pytest, pytest-asyncio, httpx, ruff, black, mypy, pre-commit

### اعمال خودکار

تست‌های `test_governance_imports` و `test_governance_deps` هرگونه نقض را شناسایی می‌کنند.

## تست‌های حاکمیت (Governance Tests)

| فایل تست | عملکرد |
|---|---|
| `test_governance_imports` | عدم وجود واردات ML در هر فایل src/ |
| `test_governance_deps` | عدم وجود بسته‌های ML در venv |
| `test_governance_architecture` | قرارداد adapter، لایه‌بندی، عدم وابستگی دایره‌ای |
| `test_adapter_contract` | قرارداد ABC موتور |
| `test_engine` | FakeEngineAdapter فریم‌های JPEG معتبر برمی‌گرداند |
| `test_latency` | LatencyTracker avg/p95/p99/fallback |
| `test_rest` | تمام نقاط پایانی REST |
| `test_scheduler` | زمان‌بندی، فشار معکوس، fallback |
| `test_session` | CRUD نشست، TTL، بیکاری، پاکسازی |
| `test_ws_integration` | چرخه کامل WebSocket |

## امنیت و جداسازی مسئولیت‌ها

1. **عدم دسترسی مستقیم runtime به موبایل:** هیچ فایلی در `src/padyar_live/` از `mobile/` وارد نمی‌کند
2. **عدم دسترسی مستقیم runtime به موتور:** هیچ فایلی در `src/padyar_live/` از `PadYar-LipSync-master/` وارد نمی‌کند
3. **عدم وجود ML در runtime:** هیچ فریمورک یادگیری ماشین در کد یا وابستگی‌ها
4. **حاکمیت خودکار:** هر نقض بالادست توسط CI شناسایی می‌شود
5. **بازیابی خودکار:** fallback در صورت خطای موتور، بدون قطع خدمات

---

*Powered by Mohammad Kohandezh — KSF Company*
*info@ksf.ir*
