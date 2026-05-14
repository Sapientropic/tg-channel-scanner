"""Dashboard state payload assembly for the local Signal Desk facade."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any


DashboardSnapshotFn = Callable[[Any], dict]
ActiveActionsFn = Callable[[], list[dict]]
SourceAccessHealthLoadedFn = Callable[[], dict | None]
SourceAccessHealthDetailFn = Callable[[dict], str]
SourceAccessHealthIsFreshFn = Callable[[dict], bool]
SourceAccessActionSummaryFn = Callable[[dict], dict]


def _with_source_access_setup_check(
    snapshot: dict,
    health: dict | None,
    *,
    source_access_health_detail: SourceAccessHealthDetailFn,
    source_access_health_is_fresh: SourceAccessHealthIsFreshFn,
    source_access_action_summary: SourceAccessActionSummaryFn,
) -> dict:
    if not health:
        return snapshot
    setup = snapshot.get("setup_status") if isinstance(snapshot.get("setup_status"), dict) else {}
    checks = setup.get("checks") if isinstance(setup.get("checks"), list) else []
    if not checks:
        return snapshot
    detail = source_access_health_detail(health)
    if not source_access_health_is_fresh(health):
        detail = f"Last source access check is stale. {detail}"
    updated_checks: list[dict] = []
    for check in checks:
        if isinstance(check, dict) and check.get("check_id") == "source_access":
            updated_checks.append({**check, "detail": detail, "source_access": source_access_action_summary(health)})
        else:
            updated_checks.append(check)
    snapshot["setup_status"] = {**setup, "checks": updated_checks}
    return snapshot


def dashboard_state_payload(
    conn: Any,
    *,
    dashboard_snapshot: DashboardSnapshotFn,
    active_actions: ActiveActionsFn,
    source_access_health_loaded: SourceAccessHealthLoadedFn,
    source_access_health_detail: SourceAccessHealthDetailFn,
    source_access_health_is_fresh: SourceAccessHealthIsFreshFn,
    source_access_action_summary: SourceAccessActionSummaryFn,
) -> dict:
    snapshot = dashboard_snapshot(conn)
    snapshot["active_actions"] = active_actions()
    return _with_source_access_setup_check(
        snapshot,
        source_access_health_loaded(),
        source_access_health_detail=source_access_health_detail,
        source_access_health_is_fresh=source_access_health_is_fresh,
        source_access_action_summary=source_access_action_summary,
    )
