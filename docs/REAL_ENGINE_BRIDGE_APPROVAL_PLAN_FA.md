# طرح تأیید bridge اتصال engine واقعی

**Powered by:** Mohammad Kohandezh — KSF Company
**تماس:** info@ksf.ir

---

## گزینه‌های پیاده‌سازی

### گزینه ۱: Bridge داخل repo PadYar-LipSync

```
PadYar-LipSync/
├── lipsync/              ← کد موجود
├── bridge/               ← جدید
│   ├── app.py            FastAPI server
│   ├── audio.py          PCM → WAV → Whisper
│   ├── frames.py         NumPy → JPEG → base64
│   ├── avatar.py         AvatarRegistry
│   └── config.py         BridgeConfig
├── models/
└── requirements.txt
```

**مزایا:**
- دسترسی مستقیم به مدل‌ها و کد inference
- نیاز به deployment 하나
- نیاز به repo اضافی ندارد
- تست یکپارچه آسان‌تر

**معایب:**
- افزایش پیچیدگی repo PadYar-LipSync
- وابستگی bridge به جزئیات داخلی inference
- تغییرات inference ممکن است bridge را بشکند
- تست bridge نیاز به GPU دارد

### گزینه ۲: repo جداگانه `padyar-engine-bridge`

```
padyar-engine-bridge/      ← repo جدید
├── bridge/
│   ├── app.py
│   ├── audio.py
│   ├── frames.py
│   └── avatar.py
├── tests/
├── Dockerfile
└── pyproject.toml

Depends on:
  - PadYar-LipSync (pip install or git submodule)
  - FastAPI, torch, diffusers, transformers
```

**مزایا:**
- جداسازی کامل bridge از engine
- versioning مستقل
- جایگزینی engine بدون تغییر bridge
- CI/CD مستقل

**معایب:**
- repo اضافی برای مدیریت
- dependency management پیچیده‌تر
- نیاز به پیکربندی بیشتر
- alignment بین bridge و engine

### گزینه ۳: bridge موقت محلی برای تست

```
padyar-live-avatar/
├── src/padyar_live/
│   └── devtools/
│       ├── mock_engine.py      ← موجود
│       └── local_bridge.py     ← جدید (موقت)
└── tests/
```

**مزایا:**
- سریع‌ترین راه برای تست واقعی
- بدون repo اضافی
- با Mock Engine مقایسه مستقیم

**معایب:**
- نقض جداسازی runtime از ML (هرچند فقط در devtools)
- فقط برای development، نه production
- نیاز به GPU روی machine توسعه
- گزینه‌ی حذف ندارد

## توصیه

**گزینه ۱** برای MVP و production اولیه توصیه می‌شود:
- ساده‌ترین deployment
- کمترین moving parts
- سریع‌ترین مسیر تا اولین frame واقعی

**گزینه ۲** برای long-term:
- پس از stabilization، bridge به repo جداگانه منتقل شود
- وقتی API contract پایدار شد

**گزینه ۳** فقط برای آزمایش سریع:
- اگر GPU دسترس‌پذیر باشد و بخواهیم فوری تست کنیم
- نباید در production استفاده شود

## ریسک‌های امنیتی

### ۱. API Key / Authentication

- `RemoteEngineAdapter` از `Authorization: Bearer <key>` استفاده می‌کند
- bridge باید API key را اعتبارسنجی کند
- بدون authentication، هر کسی می‌تواند GPU را مصرف کند

**راه‌حل:**
```python
# In bridge
API_KEY = os.environ.get("PADYAR_ENGINE_API_KEY")

@app.middleware("http")
async def auth_middleware(request, call_next):
    if request.url.path == "/health":
        return await call_next(request)
    auth = request.headers.get("Authorization", "")
    if auth != f"Bearer {API_KEY}":
        return JSONResponse(status_code=401, content={"detail": "unauthorized"})
    return await call_next(request)
```

### ۲. Input Validation

- `audio_chunk_b64` باید محدود باشد (جلوگیری از ارسال چند GB)
- `frame_count` باید محدود باشد (max 20)
- `session_id` باید validate شود

**محدودیت‌های پیشنهادی:**
```
max_audio_chunk_bytes: 1 MB    (~5 seconds audio)
max_frame_count: 20
session_id_pattern: ^[a-zA-Z0-9_-]{1,64}$
```

### ۳. DoS Protection

- Rate limiting per session
- Queue depth limiting
- Request timeout enforcement

## ریسک‌های GPU/منابع

### ۱. GPU Memory

- UNet + VAE + Whisper ≈ 2-3 GB VRAM
- Avatar latents per avatar ≈ 50 MB
- 10 avatars ≈ 500 MB اضافی
- **حداقل VRAM لازم: 4 GB**
- **توصیه: 8+ GB**

### ۲. Concurrency

- UNet inference serial است (single GPU)
- Concurrent requests باید صف شوند
- Overload → CUDA OOM

**پیشنهاد:**
```python
# Semaphore to limit concurrent inference
INFERENCE_SEMAPHORE = asyncio.Semaphore(1)  # one at a time on single GPU
```

### ۳. Memory Leaks

- PyTorch CUDA cache ممکن است leak کند
- Avatar materials باید cleanup شوند
- torch.cuda.empty_cache() در صورت نیاز

**پیشنهاد:**
```python
@app.on_event("shutdown")
async def cleanup():
    for avatar_id in list(registry._avatars.keys()):
        registry.remove(avatar_id)
    torch.cuda.empty_cache()
```

## استراتژی Rollback

### سطح ۱: Runtime Fallback

runtime قبلاً fallback دارد:
```
Engine fails → FrameScheduler → fallback frames (b"") → client continues
```
اگر bridge از کار بیفتد، runtime بدون قطع‌شدن کلاینت‌ها کار می‌کند.

### سطح ۲: Adapter Switch

با تغییر متغیر محیطی:
```
PADYAR_ENGINE_ADAPTER=fake    → FakeEngineAdapter (no engine)
PADYAR_ENGINE_ADAPTER=remote  → RemoteEngineAdapter (bridge/engine)
```
بدون restart؟ بله، با reload config.

### سطح ۳: Mock Engine

```
python scripts/run_mock_engine.py --port 9000
```
Mock engine همیشه آماده است. فقط URL را تغییر دهید.

## دروازه‌های تأیید

### Gate ۱: Design Review (فعلی)

- [x] بررسی contract فعلی RemoteEngineAdapter
- [x] بررسی کد PadYar-LipSync
- [x] شناسایی فاصله‌ها
- [ ] تأیید architecture bridge
- [ ] انتخاب گزینه پیاده‌سازی

### Gate ۲: Bridge MVP

- [ ] FastAPI app با `/generate_frames` و `/health`
- [ ] PCM → WAV تبدیل
- [ ] UNet + VAE inference
- [ ] NumPy → JPEG → base64
- [ ] Avatar preparation endpoint
- [ ] Error handling صحیح
- [ ] Basic tests

### Gate ۳: Integration Testing

- [ ] Runtime ↔ Bridge E2E با GPU
- [ ] Latency measurement
- [ ] Fallback testing
- [ ] Concurrent sessions
- [ ] Avatar switching
- [ ] Error recovery
- [ ] Memory profiling

### Gate ۴: Production Readiness

- [ ] Authentication
- [ ] Rate limiting
- [ ] Monitoring/metrics
- [ ] Docker deployment
- [ ] GPU resource management
- [ ] Documentation
- [ ] Load testing

## آنچه باید قبل از کدنویسی تأیید شود

### از طرف مالک محصول:
1. **کدام گزینه؟** Bridge در PadYar-LipSync repo یا repo جداگانه؟
2. **GPU access؟** چه GPU‌ای در دسترس است؟
3. **Avatar selection؟** چند آواتار لازم است؟
4. **Quality vs Latency؟** اولویت کیفیت یا سرعت؟
5. **Resolution؟** فریم خروجی 256×256 face crop یا full frame؟

### از طرف فنی:
1. **نسخه PadYar-LipSync** — v1 یا v1.5؟ (v1.5 توصیه می‌شود)
2. **Float16** — آیا fp16 قابل استفاده است؟
3. **Audio chunk size** — چه مدت audio per request؟
4. **Avatar preparation** — چه زمانی انجام شود؟ (startup vs on-demand)
5. **Session TTL** — چه مدت avatar state نگهداری شود؟

---

*Powered by Mohammad Kohandezh — KSF Company*
*info@ksf.ir*
