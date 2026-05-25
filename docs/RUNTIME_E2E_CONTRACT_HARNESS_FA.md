# Runtime E2E Contract Harness

## هدف

این مستند توضیح می‌دهد که **Runtime E2E Contract Harness** چیست، چرا لازم است، و چگونه مسیر کامل runtime را بدون inference واقعی تست می‌کند.

## چرا قبل از اتصال engine واقعی لازم است

PadYar-LipSync یک engine inference واقعی است که به GPU و مدل‌های ML نیاز دارد. اتصال مستقیم runtime به engine واقعی بدون تست‌های contract ممکن است باعث:

- خطاهای غیرمنتظره در production
- عدم تطابق فرمت request/response بین adapter و engine
- مشکلات timeout و fallback که در محیط تست قابل تشخیص نیستند

به همین دلیل، قبل از اتصال واقعی، contract بین runtime و engine را با **Mock Engine Service** تأیید می‌کنیم.

## مسیر تست

مسیر کامل E2E به این صورت است:

```
RuntimeConfig.from_env()
    → create_engine_adapter()
        → RemoteEngineAdapter
            → HTTP Request (in-process)
                → Mock Engine Service (/generate_frames, /health)
                    → HTTP Response
                        → base64 decode
                            → frame bytes (JPEG)
                                → FrameScheduler
                                    → خروجی queue / fallback
```

### مراحل تست:

1. **انتخاب adapter از environment**: `RuntimeConfig.from_env()` با `PADYAR_ENGINE_ADAPTER=remote` تنظیم می‌شود
2. **ساخت adapter توسط factory**: `create_engine_adapter()` یک `RemoteEngineAdapter` می‌سازد
3. **ارسال request به Mock Engine**: adapter درخواست JSON با فیلدهای `session_id`, `audio_chunk_b64`, `frame_count`, `format` ارسال می‌کند
4. **دریافت response**: Mock Engine لیست `frames_b64` برمی‌گرداند
5. **decode فریم‌ها**: adapter فریم‌های base64 را به bytes تبدیل می‌کند
6. **بررسی JPEG header**: هر فریم باید با `\xff\xd8` شروع شود
7. **scheduler output**: `FrameScheduler` فریم‌ها را در queue قرار می‌دهد یا fallback تولید می‌کند

## تفاوت Mock Engine با PadYar-LipSync واقعی

| ویژگی | Mock Engine | PadYar-LipSync واقعی |
|--------|------------|---------------------|
| Inference | ندارد | UNet + VAE + Whisper + TTS |
| GPU مورد نیاز | خیر | بله (CUDA) |
| فریم‌ها | JPEG ساختگی (deterministic) | فریم‌های واقعی lip-sync |
| Latency | قابل تنظیم (0ms پیش‌فرض) | واقعی (بسته به مدل) |
| Endpoint | `/generate_frames`, `/health` | همان endpoint‌ها |
| فرمت request/response | یکسان | یکسان |
| خطا | قابل شبیه‌سازی (fail_rate) | واقعی |

**نکته مهم**: Mock Engine دقیقاً همان HTTP protocol را پیاده‌سازی می‌کند که engine واقعی استفاده می‌کند. بنابراین، اگر contract در Mock Engine کار کند، با engine واقعی نیز باید کار کند.

## چرا runtime همچنان ML-free می‌ماند

Runtime هرگز مدل ML را load نمی‌کند. `RemoteEngineAdapter` فقط یک HTTP client است:

- از `urllib.request` استاندارد پایتون استفاده می‌کند
 هیچ وابستگی ML ندارد (torch, transformers, و غیره ممنوع هستند)
- تمام inference در engine خارجی انجام می‌شود
- runtime فقط فریم‌های آماده JPEG را دریافت و مدیریت می‌کند

تست‌های E2E این موضوع را نیز تأیید می‌کنند — هیچ import ممنوعی در مسیر تست وجود ندارد.

## محدودیت‌ها

1. **فریم‌ها واقعی نیستند**: JPEG ساختگی هستند، نه خروجی lip-sync واقعی
2. **Audio پردازش نمی‌شود**: Mock Engine audio chunk را نادیده می‌گیرد
3. **Network واقعی تست نمی‌شود**: تمام ارتباطات in-process است
4. **Latency واقعی اندازه‌گیری نمی‌شود**: فقط رفتار timeout و fallback تست می‌شود
5. **Session state در engine تست نمی‌شود**: Mock Engine state-less است

## تست‌ها

فایل تست: `tests/test_runtime_e2e_contract.py`

### بخش‌های تست:

| بخش | تعداد تست | توضیح |
|-----|-----------|--------|
| Config Selection | 4 | انتخاب adapter از env vars |
| Factory Creates Remote | 3 | ساخت RemoteEngineAdapter توسط factory |
| Adapter-Mock Contract | 6 | تطابق request/response بین adapter و mock |
| Mock Engine Contract | 3 | رفتار Mock Engine Service |
| Adapter Failure Handling | 5 | خطاهای کنترل‌شده adapter |
| Scheduler Fallback | 5 | رفتار fallback در خطای adapter |
| Runtime ML-Free | 3 | عدم وجود import ممنوع |
| Full E2E Path | 4 | مسیر کامل از env تا scheduler output |

**مجموع: 33 تست E2E contract**

## مرحله بعد پس از تأیید

پس از تأیید این harness، مراحل بعدی:

1. **تست با PadYar-LipSync واقعی**: اتصال `RemoteEngineAdapter` به engine واقعی و بررسی تطابق response
2. **بهبود error handling**: اضافه کردن retry logic و circuit breaker به adapter
3. **Streaming protocol**: طراحی protocol برای استریم فریم‌ها به‌جای batch response
4. **Performance tuning**: تنظیم timeout‌ها، queue sizes و backpressure بر اساس latency واقعی engine
