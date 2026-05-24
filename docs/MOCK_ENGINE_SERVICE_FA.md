# Mock Engine Service — مستند فنی

**Powered by:** Mohammad Kohandezh — KSF Company
**تماس:** info@ksf.ir

---

## هدف Mock Engine

Mock Engine یک سرور FastAPI سبک است که پروتکل HTTP مورد انتظار `RemoteEngineAdapter` را پیاده‌سازی می‌کند. این سرور برای تست محلی end-to-end استفاده می‌شود — بدون نیاز به GPU یا موتور استنتاج واقعی.

## چرا قبل از real engine لازم است

- تست کامل runtime بدون سرور PadYar-LipSync
- تأیید سازگاری پروتکل (contract testing)
- شبیه‌سازی تأخیر و خطا
- توسعه و دیباگ محلی سریع

## Protocol Compatibility

Mock Engine دقیقاً همان پروتکلی را پیاده‌سازی می‌کند که `RemoteEngineAdapter` انتظار دارد:

### GET /health

```json
{"status": "ok"}
```

### POST /generate_frames

**Request:**
```json
{
  "session_id": "...",
  "audio_chunk_b64": "...",
  "frame_count": 4,
  "format": "pcm_s16le_16000_mono"
}
```

**Response:**
```json
{
  "frames_b64": ["...", "..."],
  "frame_count": 4,
  "source": "mock_engine"
}
```

## How to Run

### شروع mock engine

```bash
python scripts/run_mock_engine.py
```

با تنظیمات پیش‌فرض: `127.0.0.1:9000`

### با تأخیر شبیه‌سازی شده

```bash
python scripts/run_mock_engine.py --latency-ms 100
```

### با نرخ خطای شبیه‌سازی شده

```bash
python scripts/run_mock_engine.py --fail-rate 0.3
```

### با تنظیمات کامل

```bash
python scripts/run_mock_engine.py --host 127.0.0.1 --port 9000 --latency-ms 50 --fail-rate 0.1
```

## اتصال runtime به mock engine

در یک terminal:

```bash
python scripts/run_mock_engine.py
```

در terminal دیگر:

```bash
PADYAR_ENGINE_ADAPTER=remote \
PADYAR_ENGINE_URL=http://127.0.0.1:9000 \
python -m padyar_live
```

runtime به mock engine وصل می‌شود و فریم‌های mock دریافت می‌کند.

## CLI Arguments

| Argument | پیش‌فرض | توضیح |
|---|---|---|
| `--host` | `127.0.0.1` | آدرس bind |
| `--port` | `9000` | پورت bind |
| `--latency-ms` | `0` | تأخیر شبیه‌سازی شده به میلی‌ثانیه |
| `--fail-rate` | `0.0` | نرخ خطای شبیه‌سازی شده (0.0 تا 1.0) |

## محدودیت‌ها

- فریم‌های تولید شده JPEG ساختگی هستند، نه تصاویر واقعی آواتار
- هیچ پردازش صوتی انجام نمی‌شود
- `session_id` برای state استفاده نمی‌شود (stateless)
- `format` بررسی نمی‌شود

## مراحل بعدی (پس از تأیید)

1. **تست با engine واقعی:** جایگزینی mock با PadYar-LipSync
2. **WebSocket bridge:** ارتقاء از HTTP به WebSocket
3. **Docker:** docker-compose با mock engine و runtime

---

*Powered by Mohammad Kohandezh — KSF Company*
*info@ksf.ir*
