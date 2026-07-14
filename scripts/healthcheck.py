"""Standalone health check - hits the running API's /health endpoint.
Used by docker-compose HEALTHCHECK and for manual smoke-testing."""

import sys
import requests

from app.config import settings


def main() -> int:
    url = f"http://localhost:{settings.api_port}/health"
    try:
        resp = requests.get(url, timeout=5)
        resp.raise_for_status()
        data = resp.json()
        print(data)
        return 0 if data.get("status") == "healthy" else 1
    except Exception as e:
        print(f"Health check failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
