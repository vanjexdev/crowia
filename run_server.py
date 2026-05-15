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
    parser.add_argument("--ssl-cert", help="Path to TLS certificate (.crt)")
    parser.add_argument("--ssl-key", help="Path to TLS private key (.key)")
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

    https = args.ssl_cert and args.ssl_key
    proto = "https" if https else "http"
    print(f"\n  Giselo Web arrancando en {proto}://{args.host}:{args.port}")
    print(f"  Acceso local:    {proto}://localhost:{args.port}")
    print(f"  Acceso VPN:      {proto}://<tailscale-hostname>:{args.port}\n")

    uvicorn_kwargs = dict(
        host=args.host,
        port=args.port,
        reload=args.debug,
        log_level="debug" if args.debug else "info",
    )
    if https:
        uvicorn_kwargs["ssl_certfile"] = args.ssl_cert
        uvicorn_kwargs["ssl_keyfile"] = args.ssl_key

    uvicorn.run("crowia.server.app:app", **uvicorn_kwargs)


if __name__ == "__main__":
    main()
