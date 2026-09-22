from datetime import datetime, timezone


def create_audit_event(
    action: str,
    user_id: int | None = None,
    entity_type: str | None = None,
    entity_id: int | None = None,
    details: dict | None = None,
):
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": action,
        "user_id": user_id,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "details": details or {},
    }