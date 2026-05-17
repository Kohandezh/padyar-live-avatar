# Boundaries

## What this repo does

- WebSocket streaming (bidirectional, binary frames)
- Async frame queue and chunk scheduling
- Session lifecycle management (create, touch, close, expire)
- Latency measurement (per-frame avg, p95, p99)
- Failover and fallback on engine failure
- REST API for session management and metrics

## What this repo does NOT do

- AI inference (UNet, VAE, Whisper, TTS, face detection)
- Model loading or management
- GPU abstraction or CUDA management
- Distributed coordination (message queues, service discovery)
- Persistent storage (databases, caches)
- Avatar personality, memory, or cognition
- Audio feature extraction

## Why ML code is forbidden here

1. **Single responsibility.** PadYar-LipSync is the canonical inference engine. It is production-stable. Duplicating inference logic here creates divergence, double maintenance, and version drift.

2. **Deployment independence.** The runtime can be scaled, restarted, or replaced without touching model code. The engine can be upgraded without touching orchestration.

3. **Testing.** The runtime is fully testable without GPUs, model weights, or ML frameworks. `FakeEngineAdapter` proves the entire streaming pipeline works in 2 seconds on any machine.

4. **Team boundary.** Engine work and runtime work can happen in parallel by different people without merge conflicts.

## Adapter-only inference access

All inference goes through `EngineAdapter`. There is no other path.

```
GOOD:  scheduler → engine.generate_frames()  → external service
BAD:   scheduler → torch.load() → model.forward() → local inference
```

The adapter boundary means:
- Runtime never imports `torch`, `transformers`, `diffusers`, `onnxruntime`, or any ML library.
- Runtime never loads a model file.
- Runtime never calls GPU APIs.
- Runtime only sends bytes over the network and receives bytes back.

## Forbidden dependencies

These will NOT be added in the current single-node phase:

| Dependency | Why forbidden |
|-----------|---------------|
| `torch` | ML framework — belongs in engine |
| `transformers` | HuggingFace — belongs in engine |
| `diffusers` | Stable Diffusion — belongs in engine |
| `onnxruntime` | ONNX inference — belongs in engine |
| `celery` | Task queue — premature distribution |
| `redis` | Cache/broker — premature distribution |
| `kafka-python` | Message bus — premature distribution |
| `ray` | Distributed compute — premature distribution |
| `kubernetes` | Orchestration — infrastructure concern |
| `sqlalchemy` | Database — no persistence needed yet |
| `mongoengine` | Database — no persistence needed yet |
| Any ML model library | Not this repo's job |

## Good vs Bad imports

```python
# GOOD — orchestration concerns
from padyar_live.adapters.engine import EngineAdapter
from padyar_live.scheduler.frame_scheduler import FrameScheduler
from padyar_live.runtime.session_manager import SessionManager
from padyar_live.runtime.latency import LatencyTracker
from fastapi import WebSocket
import asyncio

# BAD — ML/inference concerns
import torch                                          # FORBIDDEN
from transformers import WhisperModel                  # FORBIDDEN
from diffusers import AutoencoderKL                    # FORBIDDEN
from padyar_live.models.unet import PadyarUNet         # FORBIDDEN (wrong repo)
import onnxruntime as ort                              # FORBIDDEN
```

```python
# GOOD — calling engine through adapter
class LipSyncAdapter(EngineAdapter):
    async def generate_frames(self, session_id, audio, count):
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "http://lip-sync:7860/generate",
                content=audio,
                params={"session_id": session_id, "frame_count": count},
            )
            return [frame_bytes for frame_bytes in resp.json()["frames"]]

# BAD — implementing inference directly
class LocalEngine(EngineAdapter):
    def __init__(self):
        self.model = torch.load("unet.pth")          # FORBIDDEN

    async def generate_frames(self, session_id, audio, count):
        features = self.whisper.encode(audio)          # FORBIDDEN
        latent = self.vae.encode(frame)                # FORBIDDEN
        return self.unet.predict(latent, features)     # FORBIDDEN
```

## Rollback and replacement strategy

### Replacing the engine

1. Implement new `EngineAdapter` subclass
2. Pass to `create_app(engine=NewAdapter())`
3. Zero changes to runtime, scheduler, or WS code
4. If new engine breaks: swap back to old adapter — single line change

### Replacing the runtime (if needed)

1. PadYar-LipSync is not coupled to this runtime
2. Runtime only calls engine via HTTP — engine doesn't know about runtime
3. A new runtime can be written from scratch without touching engine

### Adding new dependencies

Before adding any dependency:
1. State what problem it solves
2. State why stdlib or existing deps can't solve it
3. Confirm it doesn't violate boundary rules
4. Get explicit approval

### Removing a module

1. Check all imports — ensure nothing else depends on it
2. Remove tests that test only that module
3. Remove in one commit — no dead code left behind

## Attribution

Powered by: Mohammad Kohandezh — KSF Company
Contact: info@ksf.ir
