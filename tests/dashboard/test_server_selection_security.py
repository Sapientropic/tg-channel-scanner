import unittest
import json
from http import HTTPStatus
from unittest.mock import patch

from scripts import dashboard_server, desk_server_selection


class DashboardServerSelectionSecurityTests(unittest.TestCase):
    def test_server_selection_helpers_stay_available_from_dashboard_facade(self):
        self.assertIs(dashboard_server.DashboardServerSelection, desk_server_selection.DashboardServerSelection)
        self.assertEqual(dashboard_server.DESK_HEALTH_SCHEMA_VERSION, desk_server_selection.DESK_HEALTH_SCHEMA_VERSION)
        self.assertEqual(dashboard_server.DESK_APP_ID, desk_server_selection.DESK_APP_ID)


    def test_dashboard_host_warning_only_warns_for_non_loopback_hosts(self):
        self.assertIsNone(dashboard_server.dashboard_host_warning("127.0.0.1"))
        self.assertIsNone(dashboard_server.dashboard_host_warning("localhost"))
        self.assertIsNone(dashboard_server.dashboard_host_warning("::1"))

        warning = dashboard_server.dashboard_host_warning("0.0.0.0")

        self.assertIsNotNone(warning)
        self.assertIn("report artifacts", (warning or "").lower())


    def test_loopback_address_detection_handles_common_local_forms(self):
        self.assertTrue(dashboard_server.is_loopback_address("127.0.0.1"))
        self.assertTrue(dashboard_server.is_loopback_address("::1"))
        self.assertTrue(dashboard_server.is_loopback_address("localhost"))
        self.assertTrue(dashboard_server.is_loopback_address("::ffff:127.0.0.1"))
        self.assertFalse(dashboard_server.is_loopback_address("192.168.1.10"))


    def test_select_dashboard_server_reuses_existing_compatible_instance(self):
        with patch.object(
            dashboard_server,
            "fetch_compatible_desk_health",
            return_value={
                "schema_version": "desk_health_v1",
                "app": "tgcs-signal-desk",
                "url": "https://example.com/not-local",
            },
        ):
            with patch.object(dashboard_server, "ThreadingHTTPServer") as server_mock:
                selection = dashboard_server.select_dashboard_server(
                    host="127.0.0.1",
                    port=8765,
                    auto_port=True,
                    handler_cls=dashboard_server.BaseHTTPRequestHandler,
                )

        server_mock.assert_not_called()
        self.assertTrue(selection.reused_existing)
        self.assertEqual(selection.url, "http://127.0.0.1:8765")


    def test_fetch_compatible_desk_health_rejects_remote_payload_url(self):
        class FakeSocket:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self):
                return json.dumps(
                    {
                        "schema_version": "desk_health_v1",
                        "app": "tgcs-signal-desk",
                        "url": "https://example.com/not-local",
                    }
                ).encode("utf-8")

        with patch.object(dashboard_server.socket, "create_connection", return_value=FakeSocket()):
            with patch.object(dashboard_server, "urlopen", return_value=FakeResponse()):
                health = dashboard_server.fetch_compatible_desk_health("127.0.0.1", 8765)

        self.assertIsNone(health)


    def test_select_dashboard_server_auto_port_skips_incompatible_occupied_port(self):
        calls = []

        def fake_server(address, handler_cls):
            calls.append(address[1])
            if address[1] == 8765:
                raise OSError("port in use")
            return object()

        with patch.object(dashboard_server, "fetch_compatible_desk_health", return_value=None):
            with patch.object(dashboard_server, "is_tcp_port_listening", return_value=False):
                with patch.object(dashboard_server, "ThreadingHTTPServer", side_effect=fake_server):
                    selection = dashboard_server.select_dashboard_server(
                        host="127.0.0.1",
                        port=8765,
                        auto_port=True,
                        handler_cls=dashboard_server.BaseHTTPRequestHandler,
                    )

        self.assertEqual(calls, [8765, 8766])
        self.assertFalse(selection.reused_existing)
        self.assertEqual(selection.port, 8766)


    def test_select_dashboard_server_auto_port_does_not_bind_incompatible_listener(self):
        calls = []

        def fake_server(address, handler_cls):
            calls.append(address[1])
            return object()

        with patch.object(dashboard_server, "fetch_compatible_desk_health", return_value=None):
            with patch.object(dashboard_server, "is_tcp_port_listening", side_effect=[True, False]):
                with patch.object(dashboard_server, "ThreadingHTTPServer", side_effect=fake_server):
                    selection = dashboard_server.select_dashboard_server(
                        host="127.0.0.1",
                        port=8765,
                        auto_port=True,
                        handler_cls=dashboard_server.BaseHTTPRequestHandler,
                    )

        self.assertEqual(calls, [8766])
        self.assertFalse(selection.reused_existing)
        self.assertEqual(selection.port, 8766)


    def test_select_dashboard_server_explicit_port_stays_strict(self):
        with patch.object(dashboard_server, "fetch_compatible_desk_health") as health_mock:
            with patch.object(dashboard_server, "ThreadingHTTPServer", side_effect=OSError("port in use")):
                with self.assertRaises(OSError):
                    dashboard_server.select_dashboard_server(
                        host="127.0.0.1",
                        port=8765,
                        auto_port=False,
                        handler_cls=dashboard_server.BaseHTTPRequestHandler,
                    )

        health_mock.assert_not_called()


    def test_select_dashboard_server_explicit_port_rejects_incompatible_listener_before_bind(self):
        with patch.object(dashboard_server, "is_tcp_port_listening", return_value=True):
            with patch.object(dashboard_server, "ThreadingHTTPServer") as server_mock:
                with self.assertRaises(OSError):
                    dashboard_server.select_dashboard_server(
                        host="127.0.0.1",
                        port=8765,
                        auto_port=False,
                        handler_cls=dashboard_server.BaseHTTPRequestHandler,
                    )

        server_mock.assert_not_called()


    def test_sensitive_desk_setup_endpoint_requires_loopback_client(self):
        class FakeHandler:
            path = "/api/desk/telegram-status"
            client_address = ("192.168.1.10", 51000)
            status = None
            payload = None

            def _json(self, status, payload):
                self.status = status
                self.payload = payload

        handler = FakeHandler()
        dashboard_server.DashboardHandler.do_GET(handler)

        self.assertEqual(handler.status, HTTPStatus.BAD_REQUEST)
        self.assertIn("localhost", handler.payload["error"])


    def test_state_and_artifact_get_endpoints_require_loopback_client(self):
        class FakeHandler:
            client_address = ("192.168.1.10", 51000)
            status = None
            payload = None
            connected = False
            served_artifact = False

            def __init__(self, path):
                self.path = path

            def _connect(self):
                self.connected = True
                raise AssertionError("state connection should be gated before use")

            def _serve_artifact(self, encoded_path):
                self.served_artifact = True
                raise AssertionError("artifact serving should be gated before use")

            def _serve_static(self, path):
                raise AssertionError("sensitive routes should not fall back to static")

            def _json(self, status, payload):
                self.status = status
                self.payload = payload

        for path in ["/api/state", "/artifacts/output/runs/run-1/report.html"]:
            with self.subTest(path=path):
                handler = FakeHandler(path)
                dashboard_server.DashboardHandler.do_GET(handler)

                self.assertEqual(handler.status, HTTPStatus.BAD_REQUEST)
                self.assertIn("localhost", handler.payload["error"])
                self.assertFalse(handler.connected)
                self.assertFalse(handler.served_artifact)



if __name__ == "__main__":
    unittest.main()
