#!/usr/bin/env python3
"""Giselo Web Server — entry point."""
import argparse
import logging
import pathlib
import sys

PROJECT_ROOT = pathlib.Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))


def main():
    parser = argparse.ArgumentParser(description="Giselo Web Server")
    parser.add_argument("--host", default="0.0.0.0", help="Bind address (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8080, help="Port (default: 8080)")
    parser.add_argument("--config", default=str(PROJECT_ROOT / "config.yaml"))
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    try:
        import uvicorn
    except ImportError:
        print("ERROR: uvicorn no instalado. Ejecuta:")
        print("  pip install uvicorn fastapi")
        sys.exit(1)

    print(f"\n  Giselo Web arrancando en http://{args.host}:{args.port}")
    print(f"  Acceso local:    http://localhost:{args.port}")
    print(f"  Acceso VPN:      http://<tailscale-ip>:{args.port}\n")

    uvicorn.run(
        "crowia.server.app:app",
        host=args.host,
        port=args.port,
        reload=args.debug,
        log_level="debug" if args.debug else "info",
    )


if __name__ == "__main__":
    main()
