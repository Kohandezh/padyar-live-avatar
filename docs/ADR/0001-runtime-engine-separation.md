# ADR 0001: Runtime-Engine Separation

## Status

Accepted

## Context

The PadYar ecosystem needs to stream AI-generated avatar frames in realtime to mobile and web clients. There is an existing stable inference engine (PadYar-LipSync) that handles UNet, VAE, Whisper, TTS, and face processing.

The question: should the realtime streaming orchestration live in the same repo as the inference engine, or in a separate repo?

## Decision

Separate repos. `padyar-live-avatar` handles only orchestration. `PadYar-LipSync` handles only inference. They communicate over the network through an adapter interface.

## Rationale

### 1. Independent scaling

Inference is GPU-bound. Orchestration is I/O-bound. They scale differently. A single GPU server might serve 5-10 concurrent sessions. The runtime might handle 100+ WebSocket connections with near-zero CPU. Colocating them forces scaling both together.

### 2. Independent deployment

The engine is stable — it shouldn't change often. The runtime is new — it will change frequently during development. Separate repos mean runtime deployments never risk breaking inference.

### 3. Testing without GPUs

The entire runtime pipeline can be tested on any machine in under 2 seconds using `FakeEngineAdapter`. No GPU, no model downloads, no CUDA. This makes CI fast and development accessible.

### 4. Future engine replacement

If a better inference engine comes along (faster UNet, different architecture, cloud API), we implement a new adapter. The runtime doesn't change. This protects the streaming infrastructure from engine churn.

### 5. Team parallelism

Engine work (model optimization, quantization, accuracy) and runtime work (streaming, scheduling, latency) require different expertise. Separate repos let people work without stepping on each other.

## Consequences

### Positive

- Runtime is testable without GPU
- Engine can be upgraded independently
- Clear code ownership boundaries
- Faster CI (no model downloads)
- Runtime can be rewritten without touching stable engine

### Negative

- Network latency between runtime and engine (mitigated: both on same machine or LAN)
- Two repos to deploy (mitigated: simple docker-compose)
- Adapter interface must stay stable (enforced: only 2 methods in ABC)

## Implementation

The adapter boundary is defined by `EngineAdapter`:

```python
class EngineAdapter(ABC):
    async def generate_frames(self, session_id: str, audio_chunk: bytes, frame_count: int) -> list[bytes]
    async def health_check(self) -> bool
```

Two methods. That's the entire contract. Any engine implementing this plugs in.

## Future considerations

- When PadYarAvatar repo is built, it will call this runtime, not the engine directly
- The three-layer stack will be: Avatar (cognition) → Runtime (streaming) → Engine (inference)
- Each layer only knows about the layer directly below it
