# قرارداد پروتکل EngineAdapter — Padyar Live Avatar

**Powered by:** Mohammad Kohandezh — KSF Company
**تماس:** info@ksf.ir

---

## مقدمه

این سند پروتکل ارتباطی بین runtime (`src/padyar_live/`) و موتور استنتاج خارجی (PadYar-LipSync) را از طریق رابط `EngineAdapter` تعریف می‌کند.

هدف: هر موتوری که این پروتکل را پیاده‌سازی کند، بدون تغییر در runtime قابل اتصال باشد.

## متدهای رابط

### generate_frames

تولید فریم‌های تصویری آواتار بر اساس ورودی صوتی یا متنی.

```python
async def generate_frames(
    self,
    session_id: str,
    audio_chunk: bytes | None = None,
    text: str | None = None,
    config: FrameConfig | None = None,
) -> AsyncIterator[bytes]:
    ...
```

#### ورودی‌ها

| پارامتر | نوع | الزامی | توضیح |
|---|---|---|---|
| `session_id` | `str` | بله | شناسه نشست — برای پیگیری state در موتور |
| `audio_chunk` | `bytes` | خیر | قطعه صوتی PCM — 16bit، 16kHz، mono |
| `text` | `str` | خیر | متن ورودی (جایگزین audio) |
| `config` | `FrameConfig` | خیر | تنظیمات فریم (width، height، quality) |

**نکته:** حداقل یکی از `audio_chunk` یا `text` باید ارائه شود.

#### خروجی‌ها

`AsyncIterator[bytes]` — هر آیتم یک فریم JPEG کامل است.

### health_check

بررسی سلامت موتور استنتاج.

```python
async def health_check(self) -> bool:
    ...
```

#### رفتار

- `True`: موتور آماده دریافت درخواست
- `False`: موتور در دسترس نیست یا در حال بارگذاری

## Frame Payload

هر فریم خروجی:

| فیلد | مقدار |
|---|---|
| فرمت | JPEG |
| encoding | binary |
| رزولوشن پیش‌فرض | تنظیم‌شده توسط `FrameConfig` |
| حداکثر اندازه | تعریف‌شده توسط adapter |

مثال:

```
bytes: b'\xff\xd8\xff\xe0...' (JPEG header)
```

## Audio Chunk Payload

فرمت صوتی ورودی:

| فیلد | مقدار |
|---|---|
| فرمت | PCM raw |
| sample rate | 16000 Hz |
| bit depth | 16-bit |
| channels | 1 (mono) |
| endian | little-endian |
| حداکثر طول chunk | تنظیم‌شده توسط scheduler |

مثال محاسبه اندازه:
- 1 ثانیه صدا = 16000 samples × 2 bytes = 32000 bytes
- 100ms chunk = 3200 bytes

## Session ID

| ویژگی | مقدار |
|---|---|
| فرمت | UUID v4 |
| تولیدکننده | runtime (`SessionManager`) |
| ارسال‌شونده | به موتور از طریق `session_id` |
| طول عمر | تا زمان بسته‌شدن نشست یا انقضای TTL |
| یکتایی | هر نشست یک `session_id` یکتا دارد |

موتور باید `session_id` را برای:
- حفظ state آواتار (pose، expression)
- پیگیری lip-sync context
- پاکسازی منابع پس از بسته‌شدن

## Frame Count

| ویژگی | توضیح |
|---|---|
| خروجی هر chunk صوتی | تعداد متغیر فریم (وابسته به طول audio) |
| حداقل | 1 فریم (حتی برای audio کوتاه) |
| حداکثر | محدود توسط `RuntimeConfig.max_frames_per_chunk` |
| شمارش | توسط `FrameScheduler` انجام می‌شود |

## Error Format

خطاها از طریق استثناهای سفارشی گزارش می‌شوند:

```python
class EngineAdapterError(Exception):
    """خطای عمومی adapter"""
    pass

class EngineTimeoutError(EngineAdapterError):
    """موتور در مهلت تعیین‌شده پاسخ نداد"""
    pass

class EngineConnectionError(EngineAdapterError):
    """اتصال به موتور برقرار نشد یا قطع شد"""
    pass

class EngineLoadError(EngineAdapterError):
    """مدل در موتور بارگذاری نشد"""
    pass

class EngineSessionError(EngineAdapterError):
    """نشست در موتور نامعتبر یا منقضی شده"""
    pass
```

هر خطا شامل:
- `message` — توضیح فارسی یا فنی
- `session_id` — نشست مربوطه
- `retryable` — آیا تلاش مجدد ممکن است؟

## Timeout Behavior

| سناریو | مهلت | رفتار |
|---|---|---|
| اتصال اولیه | `connect_timeout` (پیش‌فرض: 5s) | `EngineConnectionError` |
| تولید تک فریم | `frame_timeout` (پیش‌فرض: 2s) | fallback frame |
| health_check | `health_timeout` (پیش‌فرض: 3s) | برگرداندن `False` |
| پایان نشست | `close_timeout` (پیش‌فرض: 5s) | قطع اجباری |

پس از `max_consecutive_timeouts` (پیش‌فرض: 3):
1. فعال‌شدن fallback mode
2. ثبت در metrics
3. تلاش periodical reconnect

## Fallback Behavior

وقتی موتور در دسترس نیست یا timeout می‌دهد:

1. **فریم جایگزین تولید شود** — آخرین فریم موفق، یا فریم خنثی (neutral frame)
2. **نشست همچنان فعال بماند** — کلاینت قطع نمی‌شود
3. **تلاش مجدد خودکار** — در پس‌زمینه، reconnect انجام می‌شود
4. **گزارش metrics** — نرخ fallback در `/metrics` گزارش می‌شود
5. **بازگشت شفاف** — پس از بازگشت موتور، بدون تداخل عملیات عادی از سر گرفته می‌شود

```python
# زمان‌بند fallback
fallback_rate = fallback_count / total_frame_requests
if fallback_rate > threshold:
    log_warning("engine fallback rate exceeded threshold")
```

## Health Check Protocol

### رفتار دوره‌ای

- فاصله: هر `health_check_interval` ثانیه (پیش‌فرض: 30s)
- اجرا در پس‌زمینه بدون تأثیر بر نشست‌های فعال

### پاسخ موتور

```python
# موتور سالم
health_check() -> True

# موتور در حال بارگذاری
health_check() -> False

# موتور غیرقابل دسترس
health_check() -> raises EngineConnectionError
```

### اقدامات بر اساس نتیجه

| نتیجه | اقدام |
|---|---|
| `True` | عادی |
| `False` | نشست‌های جدید به موتور ارسال نمی‌شوند، نشست‌های فعلی از fallback استفاده می‌کنند |
| Exception | موتور از rotation خارج می‌شود تا reconnect موفق |

## Versioning Strategy

### نسخه‌بندی پروتکل

```
PROTOCOL_VERSION = "1.0.0"
```

فرمت: `MAJOR.MINOR.PATCH` (Semantic Versioning)

- **MAJOR:** تغییر شکستن (breaking change) — adapter جدید نیاز است
- **MINOR:** قابلیت جدید — backward compatible
- **PATCH:** رفع خطا — backward compatible

### هندشیک نسخه

```python
adapter = RealEngineAdapter(
    engine_url="...",
    protocol_version="1.0.0",
)
```

اگر نسخه runtime و موتور ناسازگار باشند:
- `EngineAdapterError` با پیام نسخه‌بندی
- نشست‌ها ایجاد نمی‌شوند
- گزارش در metrics

## Compatibility Rules

1. **runtime نباید به جزئیات داخلی موتور وابسته باشد** — فقط از طریق `EngineAdapter`
2. **موتور باید پروتکل را رعایت کند** — ورودی/خروجی طبق این سند
3. **نسخه‌های MAJOR مختلف ناسازگارند** — هر دو طرف باید نسخه یکسان داشته باشند
4. **نسخه‌های MINOR سازگارند** — runtime نسخه پایین‌تر را هم می‌پذیرد
5. **fallback در هر نسخه‌ای فعال است** — حتی اگر موتور ناسازگار باشد

---

*Powered by Mohammad Kohandezh — KSF Company*
*info@ksf.ir*
