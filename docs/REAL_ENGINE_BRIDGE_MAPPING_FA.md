# نگاشت پروتکل bridge با engine واقعی

**Powered by:** Mohammad Kohandezh — KSF Company
**تماس:** info@ksf.ir

---

## Request Schema Mapping

### Runtime → Bridge (RemoteEngineAdapter → HTTP)

runtime این request را ارسال می‌کند:

```json
{
  "session_id": "abc123",
  "audio_chunk_b64": "<base64 PCM s16le 16kHz mono>",
  "frame_count": 4,
  "format": "pcm_s16le_16000_mono"
}
```

### Bridge → Engine (داخلی)

bridge باید این تبدیل‌ها را انجام دهد:

| فیلد request | تبدیل در bridge | ورودی engine |
|---|---|---|
| `audio_chunk_b64` | base64 decode → PCM bytes → WAV tempfile | `audio_path` (فایل WAV) |
| `session_id` | lookup avatar state | `Avatar` object (pre-loaded) |
| `frame_count` | محاسبه Whisper features متناسب | `batch_size` در UNet inference |
| `format` | اعتبارسنجی، در حال حاضر فقط `pcm_s16le_16000_mono` | — |

### مشکل: Audio Streaming

engine فعلی فایل WAV کامل نیاز دارد. runtime chunk به chunk ارسال می‌کند.

**راه‌حل پیشنهادی:**

```
chunk 1 (PCM bytes) ─┐
chunk 2 (PCM bytes) ─┤→ buffer accumulation → WAV tempfile → Whisper → UNet
chunk 3 (PCM bytes) ─┤
chunk 4 (PCM bytes) ─┘
```

هر request شامل یک audio_chunk کامل برای یک batch فریم است. bridge:
1. PCM bytes را دریافت می‌کند
2. به WAV tempfile تبدیل می‌کند (header اضافه می‌کند)
3. Whisper feature extraction انجام می‌دهد
4. UNet inference اجرا می‌کند

**اندازه chunk:**
- 4 فریم در 25fps = 160ms audio
- 160ms × 16000 Hz × 2 bytes = 5120 bytes PCM
- بعد از base64: ~6827 bytes

## Response Schema Mapping

### Engine → Bridge (داخلی)

engine این خروجی تولید می‌کند:

| خروجی engine | توضیح |
|---|---|
| `numpy.ndarray` (B, H, W, 3) | batch فریم RGB (uint8) |
| رزولوشن face crop: 256×256 | پس از VAE decode |
| رزولوشن full frame: متغیر | پس از blending با تصویر اصلی |

### Bridge → Runtime (HTTP Response)

bridge باید این تبدیل را انجام دهد:

```python
# NumPy → JPEG → base64
frames_b64 = []
for frame in batch_frames:
    _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
    frames_b64.append(base64.b64encode(buffer).decode('ascii'))
```

```json
{
  "frames_b64": ["<base64 JPEG>", ...],
  "frame_count": 4,
  "source": "padyar-lipsync"
}
```

### نکات تبدیل:

| ویژگی | Engine خروجی | Bridge تبدیل |
|---|---|---|
| فرمت | NumPy RGB (H×W×3, uint8) | JPEG (cv2.imencode) |
| رنگ | RGB | BGR→RGB تبدیل برای cv2 |
| رزولوشن | full frame (متغیر) | JPEG bytes (کوچک‌شده با quality=90) |
| اندازه تقریبی | 256×256 face crop / full frame blended | ~10-50 KB per JPEG |
| Encoding | — | base64 |

## Audio Chunk Handling

### فرمت ورودی runtime

```
PCM signed 16-bit little-endian
16000 Hz sample rate
1 channel (mono)
```

### تبدیل به WAV

```python
import wave
import tempfile

def pcm_to_wav(pcm_bytes: bytes, sample_rate: int = 16000) -> str:
    """Convert raw PCM bytes to WAV tempfile path."""
    tmp = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
    with wave.open(tmp.name, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)       # 16-bit = 2 bytes
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_bytes)
    return tmp.name
```

### Whisper Processing

engine از `AudioProcessor` استفاده می‌کند:
1. `librosa.load(wav_path, sr=16000)` — بارگذاری audio
2. Split به 30-second segments
3. `AutoFeatureExtractor` → mel spectrogram
4. `WhisperModel.encoder` → hidden states (10 layers)
5. Output shape: `(50, 384)` per chunk — 50fps audio features

### نگاشت audio chunk → video frames

```
Audio FPS (Whisper): 50 fps
Video FPS: 25 fps (configurable)
Ratio: 50/25 = 2 whisper frames per video frame

For 4 video frames:
- Need 8 whisper feature frames
- Audio duration: 4 / 25 = 0.16 seconds
- PCM bytes: 0.16 × 16000 × 2 = 5120 bytes
```

engine از `audio_padding_length_left=2` و `audio_padding_length_right=2` استفاده می‌کند:
- هر video frame از 5 whisper frames (2 left + current + 2 right) استفاده می‌کند
- Total whisper features needed: `video_frames × (2+1+2) = 4 × 5 = 20`

## Frame Count Handling

### Runtime → Bridge

runtime `frame_count` را مشخص می‌کند (معمولاً `chunk_size` = 4).

### Bridge → Engine

bridge باید:
1. `frame_count` را به تعداد video frames متناسب تبدیل کند
2. Whisper features متناسب استخراج کند
3. UNet inference در batch اجرا کند

```python
# In bridge
video_frames = request.frame_count  # e.g., 4
whisper_frames = video_frames * 2    # 50fps / 25fps = 2

# Audio feature window
padding = 2  # audio_padding_length_left + right
total_whisper = whisper_frames + padding * 2

# UNet batch
batch_size = video_frames
latents = unet.forward(latent_batch, audio_features)
frames = vae.decode(latents)
```

## Avatar/Session Handling

### Runtime Side

runtime `session_id` تولید و ارسال می‌کند. اطلاعی از avatar state ندارد.

### Bridge Side

bridge باید avatar state را نگهداری کند:

```python
class AvatarRegistry:
    """In-memory avatar state cache."""

    def __init__(self):
        self._avatars: dict[str, Avatar] = {}

    def get_or_create(self, avatar_id: str, video_path: str) -> Avatar:
        if avatar_id not in self._avatars:
            self._avatars[avatar_id] = Avatar(
                avatar_id=avatar_id,
                video_path=video_path,
                preparation=True,
            )
        return self._avatars[avatar_id]

    def remove(self, avatar_id: str) -> None:
        if avatar_id in self._avatars:
            del self._avatars[avatar_id]
```

### Endpoints اضافی مورد نیاز

علاوه بر contract فعلی، bridge به endpoint‌های اضافی نیاز دارد:

```
POST /prepare_avatar
  Request:  {"avatar_id": "x", "video_path": "...", "bbox_shift": 5}
  Response: {"status": "prepared", "avatar_id": "x"}

DELETE /avatar/{avatar_id}
  Response: {"status": "removed"}
```

**نکته:** این endpoint‌ها خارج از contract فعلی `RemoteEngineAdapter` هستند. bridge باید آنها را مستقلاً پیاده‌سازی کند.

### Session → Avatar Binding

```
POST /session/{session_id}/bind_avatar
  Request:  {"avatar_id": "x"}
  Response: {"status": "bound"}
```

یا session به‌صورت پیش‌فرض به avatar_id متصل شود.

## Error Mapping

### Engine Errors → RemoteEngineError

| Engine Error | RemoteEngineError | HTTP Status |
|---|---|---|
| CUDA OOM | `RemoteEngineError("GPU out of memory")` | 500 |
| Model not loaded | `RemoteEngineError("model not ready")` | 503 |
| Invalid audio | `RemoteEngineError("audio decode failed")` | 400 |
| Face not detected | `RemoteEngineError("face detection failed")` | 422 |
| Avatar not found | `RemoteEngineError("avatar not prepared")` | 404 |
| Timeout | `RemoteEngineError("request failed: timeout")` | 504 |
| Whisper error | `RemoteEngineError("audio processing failed")` | 500 |

### Error Response Format

```json
{
  "detail": "GPU out of memory",
  "error": "RemoteEngineError: CUDA OOM during UNet inference",
  "session_id": "abc123"
}
```

## Timeout Mapping

| Operation | Engine Timeout | Runtime Config |
|---|---|---|
| Whisper feature extraction | ~50ms per chunk | `engine_timeout_seconds` (5s default) |
| UNet inference (batch=4) | ~200-500ms on RTX 3090 | `engine_timeout_seconds` |
| VAE decode (batch=4) | ~50-100ms | `engine_timeout_seconds` |
| Face blending | ~20ms per frame | `engine_timeout_seconds` |
| Total per request | ~300-700ms | `engine_timeout_seconds` (5s is safe) |

### Tuning پیشنهادی

```
engine_timeout_seconds: 5.0    →  adequate for initial testing
latency_target_ms: 500.0       →  realistic for GPU inference
chunk_size: 4                   →  good balance latency/throughput
fps: 25                         →  standard video fps
```

## Health Check Mapping

### Runtime Expectation

```python
GET /health → {"status": "ok"}
```

### Bridge Implementation

```python
@app.get("/health")
async def health():
    checks = {
        "models_loaded": unet is not None and vae is not None,
        "gpu_available": torch.cuda.is_available(),
        "gpu_memory_mb": torch.cuda.mem_get_info()[0] // 1024 // 1024
                          if torch.cuda.is_available() else 0,
    }
    if all(checks.values()):
        return {"status": "ok", "checks": checks}
    return {"status": "degraded", "checks": checks}
```

## File/Model Path Handling

### Model Paths (در PadYar-LipSync)

| Model | Path | اندازه تقریبی |
|---|---|---|
| UNet | `models/musetalkV15/unet.pth` | ~300 MB |
| VAE | `models/sd-vae/` (diffusers) | ~170 MB |
| Whisper | `models/whisper/` (HuggingFace tiny) | ~40 MB |
| DWPose | `models/dwpose/dw-ll_ucoco_384.pth` | ~200 MB |
| Face Parsing | `models/face-parse-bisent/79999_iter.pth` | ~50 MB |
| SyncNet | `models/syncnet/latentsync_syncnet.pt` | ~50 MB |

### Avatar Data Paths (پس از preparation)

| Artifact | Path | اندازه |
|---|---|---|
| Source frames | `full_imgs/*.png` | video-dependent |
| Face coords | `coords.pkl` | ~10 KB |
| VAE latents | `latents.pt` | ~50 MB per avatar |
| Face masks | `mask/*.png` | ~100 KB per frame |
| Mask coords | `mask_coords.pkl` | ~10 KB |
| Metadata | `avator_info.json` | ~1 KB |

## Expected Output Frame Format

### Engine Output

```
NumPy ndarray: shape (H, W, 3), dtype uint8, RGB order
Resolution: same as source video/image
Face crop: always 256×256 before blending
```

### Bridge Output (HTTP)

```
Base64-encoded JPEG
Quality: 90 (configurable)
Average size: 10-50 KB per frame (256×256 face)
Average size: 30-100 KB per frame (full frame blended)
```

### Performance Estimate

```
4 frames per request:
- UNet inference: ~300ms (batch=4, RTX 3090, fp16)
- VAE decode: ~80ms
- Blending: ~80ms (4 frames)
- JPEG encode + base64: ~20ms
- Total: ~480ms per request
```

---

*Powered by Mohammad Kohandezh — KSF Company*
*info@ksf.ir*
