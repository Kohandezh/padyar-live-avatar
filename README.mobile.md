# Padyar Mobile

This folder contains the mobile SDK and mobile-related assets of the PadYar ecosystem.

## Role

This folder may contain:

- Android SDK
- iOS SDK
- Native C++ / NCNN on-device lip-sync engine
- Mobile demo apps
- Mobile assets and resources
- Historical mobile documentation

## Important Boundary

The runtime package remains:

src/padyar_live/

The runtime package must stay ML-free and adapter-only.

This mobile folder is included as part of the monorepo structure, but it must not be imported directly by the runtime layer.

## Related Layers

- src/padyar_live/ = realtime runtime and orchestration
- mobile/ = mobile SDK and on-device client layer
- external inference engines must be accessed through EngineAdapter

## Attribution

Powered by:
Mohammad Kohandezh — KSF Company
info@ksf.ir
