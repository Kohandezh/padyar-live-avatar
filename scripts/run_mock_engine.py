"""Run the PadYar mock engine service for local end-to-end testing."""

from __future__ import annotations

import argparse

import uvicorn

from padyar_live.devtools.mock_engine import create_mock_engine_app


def main() -> None:
    parser = argparse.ArgumentParser(description="PadYar Mock Engine Service")
    parser.add_argument("--host", default="127.0.0.1", help="Bind host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=9000, help="Bind port (default: 9000)")
    parser.add_argument("--latency-ms", type=float, default=0.0, help="Simulated latency per request in ms")
    parser.add_argument("--fail-rate", type=float, default=0.0, help="Simulated failure rate 0.0-1.0")
    args = parser.parse_args()

    app = create_mock_engine_app(
        latency_ms=args.latency_ms,
        fail_rate=args.fail_rate,
    )
    print(f"Mock engine starting on {args.host}:{args.port}")
    print(f"  latency_ms={args.latency_ms}, fail_rate={args.fail_rate}")
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
