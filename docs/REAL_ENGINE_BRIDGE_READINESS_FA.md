# ممیزی آمادگی اتصال Engine واقعی

**Powered by:** Mohammad Kohandezh — KSF Company
**تماس:** info@ksf.ir

---

## وضعیت فعلی runtime

runtime فعلی (`src/padyar_live/`) قابلیت‌های زیر را دارد:

- `RuntimeConfig.from_env()` — بارگذاری تنظیمات از متغیرهای محیطی
- `create_engine_adapter()` — ساخت adapter بر اساس تنظیمات
- `RemoteEngineAdapter` — کلاینت HTTP استاندارد (urllib، بدون وابستگی اضافی)
- `FakeEngineAdapter` — adapter تستی بدون GPU
- `Mock Engine Service` — سرور FastAPI که پروتکل HTTP را شبیه‌سازی می‌کند
- `FrameScheduler` — صف async، backpressure، fallback
- 121 تست E2E که مسیر کامل را تأیید می‌کنند

## Contract فعلی RemoteEngineAdapter

`RemoteEngineAdapter` دو endpoint HTTP را فراخوانی می‌کند:

### POST /generate_frames

```json
{
  "session_id": "abc123",
  "audio_chunk_b64": "<base64-encoded PCM audio>",
  "frame_count": 4,
  "format": "pcm_s16le_16000_mono"
}
```

پاسخ:

```json
{
  "frames_b64": ["<base64 JPEG>", "<base64 JPEG>", ...],
  "frame_count": 4,
  "source": "remote_engine"
}
```

### GET /health

```json
{"status": "ok"}
```

## نیازمندی‌های engine واقعی

بر اساس بررسی `PadYar-LipSync-master/`، engine واقعی:

1. **مدل‌ها** — UNet، VAE، Whisper (tiny)، DWPose، FaceParsing، SFD face detector
2. **GPU** — استنتاج UNet + VAE نیاز به CUDA دارد
3. **Audio** — فایل WAV کامل (نه streaming)، 16kHz mono
4. **آواتار** — آماده‌سازی اولیه (face detection، VAE latents، masks)
5. **فریم خروجی** — NumPy RGB → blending → PNG/JPEG
6. **API** — فقط Gradio UI، بدون REST API
7. **وضعیت** — Stateful (Avatar class با کش دیسکی)

## فاصله mock engine با real engine

| ویژگی | Mock Engine | Real Engine |
|--------|------------|-------------|
| GPU | خیر | بله (CUDA) |
| مدل‌ها | ندارد | UNet + VAE + Whisper + DWPose + BiSeNet |
| Audio پردازش | نادیده می‌گیرد | Whisper feature extraction (50fps) |
| فریم خروجی | JPEG ساختگی | NumPy → blending → JPEG/PNG واقعی |
| Latency | 0ms | 100-500ms+ بسته به GPU |
| Avatar آماده‌سازی | ندارد | Face detection + VAE latents + masks |
| Session | Stateless | Stateful (Avatar class) |
| API | FastAPI `/generate_frames`, `/health` | فقط Gradio UI |

### فاصله‌های اصلی:

1. **Engine هیچ REST API ندارد** — فقط Gradio UI
2. **Audio باید فایل کامل باشد** — streaming chunk پشتیبانی نمی‌شود
3. **Avatar باید آماده شود** — face detection، VAE encoding، mask computation
4. **فریم خروجی NumPy است** — باید به JPEG تبدیل شود
5. **Interactive prompts** — `input()` در Avatar class برای سرور مناسب نیست
6. **مدل‌ها در startup بارگذاری می‌شوند** — نباید per-request لود شوند

## نقاطی که باید در PadYar-LipSync بررسی شود

### 1. اضافه‌کردن FastAPI endpoint
engine فعلی فقط Gradio دارد. باید endpoint‌های زیر اضافه شوند:
- `POST /generate_frames` — مطابق contract فعلی
- `GET /health` — بررسی سلامت و آماده‌بودن مدل‌ها

### 2. Streaming audio support
engine فعلی فایل کامل audio نیاز دارد. برای realtime:
- chunk های PCM باید جمع‌آوری و به فایل تبدیل شوند
- یا pipeline audio به‌روز شود تا chunked processing پشتیبانی کند

### 3. Avatar preparation API
آماده‌سازی آواتار باید از طریق API انجام شود:
- `POST /prepare_avatar` — دریافت تصویر و بازگرداندن avatar_id
- `DELETE /avatar/{id}` — پاکسازی منابع

### 4. حذف interactive prompts
`input()` در Avatar class باید حذف شود و با پارامتر‌های تابع جایگزین شود.

### 5. Session management
engine باید `session_id` را مدیریت کند:
- نگهداری state آواتار (pose، expression)
- پاکسازی منابع پس از بسته‌شدن session

### 6. JPEG encoding خروجی
فریم‌های NumPy باید به JPEG تبدیل و base64 encode شوند:
```python
_, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
frame_b64 = base64.b64encode(buffer).decode('ascii')
```

## چرا runtime نباید مستقیم engine را import کند

1. **جداسازی مسئولیت** — runtime فقط orchestration است، نه inference
2. **ML-free بودن** — اضافه‌کردن torch/transformers به runtime قوانین معماری را نقض می‌کند
3. **استقلال deployment** — engine روی GPU server، runtime روی هر machine
4. **تست‌پذیری** — با mock engine تست می‌شود بدون GPU
5. **scale** — engine و runtime مستقل از هم scale می‌شوند
6. **governance** — تست‌های governance فعلی ML imports را مسدود می‌کنند

## پیشنهاد معماری bridge

```
[padyar-live-avatar runtime]
    RemoteEngineAdapter (HTTP client)
        │
        │  HTTP POST /generate_frames
        │  HTTP GET  /health
        ▼
[padyar-engine-bridge]  ← جدید
    FastAPI server
        │
        ├─→ AudioProcessor (Whisper feature extraction)
        ├─→ UNet + VAE inference
        ├─→ Face blending
        └─→ Avatar management
        │
        ▼
[PadYar-LipSync models]
    UNet, VAE, Whisper, DWPose, BiSeNet
```

bridge یک FastAPI server مستقل است که:
- پروتکل HTTP فعلی `RemoteEngineAdapter` را پیاده‌سازی می‌کند
- مدل‌های ML را در startup بارگذاری می‌کند
- Avatar preparation را مدیریت می‌کند
- chunk های audio را جمع‌آوری و پردازش می‌کند
- فریم‌های JPEG برمی‌گرداند

**bridge در repo جداگانه یا در PadYar-LipSync repo قرار می‌گیرد — نه در runtime.**

---

*Powered by Mohammad Kohandezh — KSF Company*
*info@ksf.ir*
