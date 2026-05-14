import unittest
from contextlib import contextmanager
from http import HTTPStatus
from unittest.mock import patch

from scripts import dashboard_server, desk_get_routes


class DashboardGetRouteTests(unittest.TestCase):
    def test_get_route_owner_handles_state_with_loopback_gate_and_closed_connection(self):
        class FakeConnection:
            closed = False

            def close(self):
                self.closed = True

        class FakeHandler:
            status = None
            payload = None
            conn = FakeConnection()

            def _connect(self):
                return self.conn

            def _json(self, status, payload):
                self.status = status
                self.payload = payload

        features = []

        @contextmanager
        def close_after_use(conn):
            try:
                yield conn
            finally:
                conn.close()

        handler = FakeHandler()
        handled = desk_get_routes.handle_get_route(
            handler,
            "/api/state",
            require_loopback_access=lambda value, feature: features.append((value, feature)),
            close_after_use=close_after_use,
            desk_health=lambda **kwargs: {},
            desk_actions=lambda: {},
            telegram_status=lambda: {},
            desk_sources=lambda: {},
            desk_scheduler_status=lambda: {},
            desk_notification_token_status=lambda: {},
            desk_bot_gateway_status=lambda conn: {},
            desk_ai_settings_status=lambda: {},
            dashboard_state_payload=lambda conn: {"state": conn is handler.conn},
        )

        self.assertTrue(handled)
        self.assertEqual(features, [(handler, "Dashboard state")])
        self.assertTrue(handler.conn.closed)
        self.assertEqual(handler.status, HTTPStatus.OK)
        self.assertEqual(handler.payload, {"state": True})


    def test_get_route_owner_returns_false_for_static_fallback(self):
        handled = desk_get_routes.handle_get_route(
            object(),
            "/assets/app.js",
            require_loopback_access=lambda handler, feature: None,
            close_after_use=lambda conn: conn,
            desk_health=lambda **kwargs: {},
            desk_actions=lambda: {},
            telegram_status=lambda: {},
            desk_sources=lambda: {},
            desk_scheduler_status=lambda: {},
            desk_notification_token_status=lambda: {},
            desk_bot_gateway_status=lambda conn: {},
            desk_ai_settings_status=lambda: {},
            dashboard_state_payload=lambda conn: {},
        )

        self.assertFalse(handled)


    def test_dashboard_handler_get_uses_facade_injected_actions_helper(self):
        class FakeHandler:
            path = "/api/desk/actions"
            status = None
            payload = None

            def _json(self, status, payload):
                self.status = status
                self.payload = payload

            def _serve_static(self, path):
                raise AssertionError("API route should not fall through to static assets")

        with patch.object(
            dashboard_server,
            "desk_actions",
            return_value={"schema_version": "patched_actions_v1"},
        ) as actions_mock:
            handler = FakeHandler()
            dashboard_server.DashboardHandler.do_GET(handler)

        actions_mock.assert_called_once_with()
        self.assertEqual(handler.status, HTTPStatus.OK)
        self.assertEqual(handler.payload, {"schema_version": "patched_actions_v1"})


    def test_dashboard_handler_get_uses_facade_injected_status_helpers(self):
        class FakeHandler:
            status = None
            payload = None

            def __init__(self, path):
                self.path = path

            def _json(self, status, payload):
                self.status = status
                self.payload = payload

            def _serve_static(self, path):
                raise AssertionError("API route should not fall through to static assets")

        cases = [
            ("/api/desk/telegram-status", "telegram_status", "telegram"),
            ("/api/desk/sources", "desk_sources", "sources"),
            ("/api/desk/scheduler-status", "desk_scheduler_status", "scheduler"),
            ("/api/desk/notification-token/status", "desk_notification_token_status", "token"),
            ("/api/desk/ai-settings/status", "desk_ai_settings_status", "ai"),
        ]
        for path, helper_name, payload_key in cases:
            with self.subTest(path=path):
                result = {"schema_version": f"patched_{payload_key}_v1"}
                with patch.object(dashboard_server, helper_name, return_value=result) as helper_mock:
                    handler = FakeHandler(path)
                    dashboard_server.DashboardHandler.do_GET(handler)

                helper_mock.assert_called_once_with()
                self.assertEqual(handler.status, HTTPStatus.OK)
                self.assertEqual(handler.payload, {"ok": True, payload_key: result})


    def test_dashboard_handler_get_bot_gateway_status_uses_facade_and_closes_connection(self):
        class FakeConnection:
            closed = False

            def close(self):
                self.closed = True

        class FakeHandler:
            path = "/api/desk/bot-gateway-status"
            status = None
            payload = None
            conn = FakeConnection()

            def _connect(self):
                return self.conn

            def _json(self, status, payload):
                self.status = status
                self.payload = payload

            def _serve_static(self, path):
                raise AssertionError("API route should not fall through to static assets")

        result = {"schema_version": "patched_bot_gateway_v1"}
        with patch.object(dashboard_server, "desk_bot_gateway_status", return_value=result) as status_mock:
            handler = FakeHandler()
            dashboard_server.DashboardHandler.do_GET(handler)

        status_mock.assert_called_once_with(handler.conn)
        self.assertTrue(handler.conn.closed)
        self.assertEqual(handler.status, HTTPStatus.OK)
        self.assertEqual(handler.payload, {"ok": True, "bot_gateway": result})


    def test_dashboard_handler_get_artifact_route_uses_loopback_gate_and_handler_artifact_serving(self):
        class FakeHandler:
            path = "/artifacts/output/demo-report.html"
            served_artifact = None

            def _serve_artifact(self, path):
                self.served_artifact = path

            def _serve_static(self, path):
                raise AssertionError("Artifact route should not fall through to static assets")

            def _json(self, status, payload):
                raise AssertionError(f"Artifact route should not return JSON: {status} {payload}")

        with patch.object(dashboard_server.DashboardHandler, "_require_loopback_access") as gate_mock:
            handler = FakeHandler()
            dashboard_server.DashboardHandler.do_GET(handler)

        gate_mock.assert_called_once_with(handler, "Report artifacts")
        self.assertEqual(handler.served_artifact, "output/demo-report.html")


if __name__ == "__main__":
    unittest.main()
