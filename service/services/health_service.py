from datetime import datetime, timezone


def get_status() -> dict:
    return {
        "status": "up",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
