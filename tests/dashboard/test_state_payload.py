import unittest
from unittest.mock import patch

from scripts import dashboard_server, desk_state_payload


class DashboardStatePayloadTests(unittest.TestCase):
    def test_state_payload_owner_injects_active_actions_and_source_access_health(self):
        conn = object()
        health = {"schema_version": "desk_source_access_health_v1"}
        snapshot = {
            "setup_status": {
                "checks": [
                    {
                        "check_id": "source_access",
                        "label": "Source access",
                        "status": "blocked",
                        "detail": "old detail",
                    },
                    {"check_id": "profile", "detail": "unchanged"},
                ]
            }
        }

        payload = desk_state_payload.dashboard_state_payload(
            conn,
            dashboard_snapshot=lambda value: snapshot if value is conn else {},
            active_actions=lambda: [{"action_id": "sources_probe_access", "status": "running"}],
            source_access_health_loaded=lambda: health,
            source_access_health_detail=lambda value: f"detail from {value['schema_version']}",
            source_access_health_is_fresh=lambda value: True,
            source_access_action_summary=lambda value: {"schema_version": value["schema_version"], "quiet_count": 2},
        )

        self.assertEqual(payload["active_actions"][0]["action_id"], "sources_probe_access")
        source_access_check = payload["setup_status"]["checks"][0]
        self.assertEqual(source_access_check["detail"], "detail from desk_source_access_health_v1")
        self.assertEqual(source_access_check["source_access"]["quiet_count"], 2)
        self.assertEqual(payload["setup_status"]["checks"][1]["detail"], "unchanged")


    def test_dashboard_server_facade_keeps_state_payload_monkeypatch_surface(self):
        conn = object()
        health = {"schema_version": "desk_source_access_health_v1"}
        snapshot = {
            "setup_status": {
                "checks": [
                    {
                        "check_id": "source_access",
                        "label": "Source access",
                        "status": "blocked",
                        "detail": "old detail",
                    }
                ]
            }
        }

        with (
            patch.object(dashboard_server.monitor_state, "dashboard_snapshot", return_value=snapshot) as snapshot_mock,
            patch.object(dashboard_server, "desk_active_actions", return_value=[{"action_id": "patched"}]) as active_mock,
            patch.object(dashboard_server, "_source_access_health_loaded", return_value=health) as health_mock,
            patch.object(dashboard_server, "_source_access_health_detail", return_value="patched detail") as detail_mock,
            patch.object(dashboard_server, "_source_access_health_is_fresh", return_value=False) as fresh_mock,
            patch.object(
                dashboard_server,
                "_source_access_action_summary",
                return_value={"schema_version": "desk_source_access_health_v1", "inaccessible_count": 1},
            ) as summary_mock,
        ):
            payload = dashboard_server.dashboard_state_payload(conn)

        snapshot_mock.assert_called_once_with(conn)
        active_mock.assert_called_once_with()
        health_mock.assert_called_once_with()
        detail_mock.assert_called_once_with(health)
        fresh_mock.assert_called_once_with(health)
        summary_mock.assert_called_once_with(health)
        self.assertEqual(payload["active_actions"], [{"action_id": "patched"}])
        check = payload["setup_status"]["checks"][0]
        self.assertEqual(check["detail"], "Last source access check is stale. patched detail")
        self.assertEqual(check["source_access"]["inaccessible_count"], 1)


if __name__ == "__main__":
    unittest.main()
