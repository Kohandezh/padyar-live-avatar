# RemoteEngineAdapter MVP — مستند فنی

**Powered by:** Mohammad Kohandezh — KSF Company
**تماس:** info@ksf.ir

---

## هدف RemoteEngineAdapter

`RemoteEngineAdapter` یک HTTP client است که runtime را به موتور استنتاج خارجی (PadYar-LipSync) وصل می‌کند. این adapter از طریق رابط `EngineAdapter` با runtime ارتباط دارد و هیچ کد ML در خود ندارد.

## چرا این adapter فقط client است

runtime نباید هیچ پردازش استنتاج انجام دهد. تمام کارهای سنگین (UNet، VAE، lip-sync) روی سرور مجزای engine اجرا می‌شود. `RemoteEngineAdapter` فقط:

1. درخواست HTTP می‌فرستد
2. پاسخ را دریافت و رمزگشایی می‌کند
3. خطاها را گزارش می‌دهد

هیچ مدل، هیچ GPU، هیچ فریمورک ML.

## چرا ML code وارد runtime نمی‌شود

- adapter فقط از `urllib` (کتابخانه استاندارد Python) استفاده می‌کند
- هیچ dependency جدید اضافه نشده
- تست‌های حاکمیت (`test_governance_imports`، `test_governance_deps`) همچنان پاس می‌شوند
- اگر کسی اشتباهاً `import torch` اضافه کند، CI مسدود می‌شود

## HTTP Protocol

### generate_frames

```
POST {base_url}/generate_frames
Content-Type: application/json
Authorization: Bearer <api_key>  (اگر تنظیم شده)
```

### Request Schema

```json
{
  "session_id": "uuid-v4",
  "audio_chunk_b64": "base64-encoded PCM bytes",
  "frame_count": 4,
  "format": "pcm_s16le_16000_mono"
}
```

| فیلد | نوع | توضیح |
|---|---|---|
| `session_id` | string | شناسه نشست — برای حفظ state در engine |
| `audio_chunk_b64` | string | صوت PCM (16kHz, 16-bit, mono) رمزگذاری شده با base64 |
| `frame_count` | integer | تعداد فریم درخواستی |
| `format` | string | فرمت صوتی — همیشه `pcm_s16le_16000_mono` |

### Response Schema

```json
{
  "frames_b64": ["base64-jpeg-1", "base64-jpeg-2", ...],
  "frame_count": 4,
  "source": "remote_engine"
}
```

| فیلد | نوع | توضیح |
|---|---|---|
| `frames_b64` | array of string | فریم‌های JPEG رمزگذاری شده با base64 |
| `frame_count` | integer | تعداد فریم بازگشتی — باید با درخواست مطابقت داشته باشد |
| `source` | string | منبع تولید فریم |

## Error Behavior

adapter در صورت بروز خطا، `RemoteEngineError` throw می‌کند:

| خطا | شرط |
|---|---|
| درخواست ناموفق | timeout، connection refused، DNS failure |
| JSON نامعتبر | پاسخ engine قابل parse نیست |
| عدم تطابق frame_count | تعداد فریم بازگشتی ≠ تعداد درخواستی |
| خطای رمزگشایی | base64 decode ناموفق |

**نکته مهم:** adapter خودش fallback نمی‌دهد. این مسئولیت scheduler است. وقتی adapter خطا می‌دهد، scheduler فریم جایگزین تولید می‌کند.

## Fallback Behavior

وقتی `RemoteEngineAdapter` خطا می‌دهد:

1. `FrameScheduler` خطا را catch می‌کند
2. آخرین فریم موفق یا فریم خنثی تولید می‌شود
3. نشست فعال می‌ماند
4. metrics ثبت می‌شود (fallback rate)
5. تلاش بعدی ممکن است موفق شود

این رفتار در scheduler پیاده‌سازی شده و نیازی به تغییر ندارد.

## Security Notes for API Key

- `api_key` در `RemoteEngineConfig` ذخیره می‌شود
- به‌صورت `Authorization: Bearer <key>` ارسال می‌شود
- اگر `api_key` برابر `None` باشد، header ارسال نمی‌شود
- **recommendation:** api_key از environment variable خوانده شود، نه hardcoded

```python
import os

config = RemoteEngineConfig(
    base_url=os.environ["ENGINE_URL"],
    api_key=os.environ.get("ENGINE_API_KEY"),
)
```

## تنظیمات RemoteEngineConfig

| فیلد | نوع | پیش‌فرض | توضیح |
|---|---|---|---|
| `base_url` | str | — | آدرس سرور engine (الزامی) |
| `timeout_seconds` | float | 5.0 | مهلت هر درخواست HTTP |
| `health_path` | str | `/health` | مسیر health check |
| `generate_path` | str | `/generate_frames` | مسیر تولید فریم |
| `api_key` | str or None | None | کلید API (اختیاری) |

## مراحل بعدی (پس از تأیید)

1. **تست یکپارچگی:** اتصال به engine واقعی در محیط توسعه
2. **WebSocket bridge:** ارتقاء از HTTP به WebSocket برای استریم پیوسته
3. **Reconnect logic:** اتصال مجدد خودکار پس از قطعی
4. **Metrics:** افزودن تأخیر adapter به metrics endpoint
5. **Docker:** پیکربندی استقرار runtime و engine

---

*Powered by Mohammad Kohandezh — KSF Company*
*info@ksf.ir*
