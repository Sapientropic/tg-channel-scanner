import unittest
from contextlib import contextmanager
from http import HTTPStatus

from scripts import dashboard_server, desk_profile_post_routes, desk_profile_routes


class DashboardProfilePostRouteTests(unittest.TestCase):
    def test_profile_post_route_owner_handles_create_with_loopback_gate_and_closed_connection(self):
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
        body = {"brief": "Senior backend roles."}

        @contextmanager
        def close_after_use(conn):
            try:
                yield conn
            finally:
                conn.close()

        def create_profile(conn, payload):
            return {"conn": conn is handler.conn, "body": dict(payload)}

        handler = FakeHandler()
        handled = desk_profile_post_routes.handle_profile_post_route(
            handler,
            "/api/profiles/create",
            body,
            require_loopback_access=lambda value, feature: features.append((value, feature)),
            close_after_use=close_after_use,
            monitor_state_module=dashboard_server.monitor_state,
            profile_routes_module=desk_profile_routes,
            create_profile_from_brief=create_profile,
            profile_enabled_allowed_fields=dashboard_server.PROFILE_ENABLED_ALLOWED_FIELDS,
            profile_runtime_settings_allowed_fields=dashboard_server.PROFILE_RUNTIME_SETTINGS_ALLOWED_FIELDS,
            profile_draft_note_allowed_fields=dashboard_server.PROFILE_DRAFT_NOTE_ALLOWED_FIELDS,
            profile_draft_note_max_length=dashboard_server.PROFILE_DRAFT_NOTE_MAX_LENGTH,
            profile_matching_preferences_allowed_fields=dashboard_server.PROFILE_MATCHING_PREFERENCES_ALLOWED_FIELDS,
            profile_matching_preferences_max_length=dashboard_server.PROFILE_MATCHING_PREFERENCES_MAX_LENGTH,
        )

        self.assertTrue(handled)
        self.assertEqual(features, [(handler, "Profile creation")])
        self.assertTrue(handler.conn.closed)
        self.assertEqual(handler.status, HTTPStatus.OK)
        self.assertEqual(handler.payload, {"ok": True, "profile": {"conn": True, "body": body}})


    def test_profile_post_route_owner_rejects_request_shape_before_state_access(self):
        class FakeHandler:
            def _connect(self):
                raise AssertionError("invalid profile payload should be rejected before state access")

            def _json(self, status, payload):
                raise AssertionError("invalid profile payload should raise before JSON response")

        class FakeMonitorState:
            @staticmethod
            def require_profile_text_without_private_fragments(label, text):
                raise ValueError(f"{label} cannot include private fragments.")

        @contextmanager
        def close_after_use(conn):
            yield conn

        cases = [
            (
                "/api/profiles/jobs-fast/enabled",
                {"enabled": True, "unexpected": "field"},
                "Unsupported profile setting field",
            ),
            (
                "/api/profiles/jobs-fast/runtime-settings",
                {"unexpected": 10},
                "Unsupported profile setting field",
            ),
            (
                "/api/profiles/jobs-fast/draft-note",
                {"note": "abcd"},
                "3 characters or fewer",
            ),
            (
                "/api/profiles/jobs-fast/matching-preferences",
                {"preferences": "Authorization: Bearer sk-localSecret12345"},
                "cannot include private fragments",
            ),
        ]
        for path, body, error_fragment in cases:
            with self.subTest(path=path):
                with self.assertRaisesRegex(ValueError, error_fragment):
                    desk_profile_post_routes.handle_profile_post_route(
                        FakeHandler(),
                        path,
                        body,
                        require_loopback_access=lambda handler, feature: None,
                        close_after_use=close_after_use,
                        monitor_state_module=FakeMonitorState,
                        profile_routes_module=desk_profile_routes,
                        create_profile_from_brief=lambda conn, payload: {},
                        profile_enabled_allowed_fields={"enabled"},
                        profile_runtime_settings_allowed_fields={"scan_window_hours"},
                        profile_draft_note_allowed_fields={"note"},
                        profile_draft_note_max_length=3,
                        profile_matching_preferences_allowed_fields={"preferences"},
                        profile_matching_preferences_max_length=4000,
                    )


    def test_profile_post_route_owner_returns_false_for_non_profile_path(self):
        handled = desk_profile_post_routes.handle_profile_post_route(
            object(),
            "/api/feedback/export",
            {},
            require_loopback_access=lambda handler, feature: None,
            close_after_use=lambda conn: conn,
            monitor_state_module=dashboard_server.monitor_state,
            profile_routes_module=desk_profile_routes,
            create_profile_from_brief=lambda conn, payload: {},
            profile_enabled_allowed_fields=dashboard_server.PROFILE_ENABLED_ALLOWED_FIELDS,
            profile_runtime_settings_allowed_fields=dashboard_server.PROFILE_RUNTIME_SETTINGS_ALLOWED_FIELDS,
            profile_draft_note_allowed_fields=dashboard_server.PROFILE_DRAFT_NOTE_ALLOWED_FIELDS,
            profile_draft_note_max_length=dashboard_server.PROFILE_DRAFT_NOTE_MAX_LENGTH,
            profile_matching_preferences_allowed_fields=dashboard_server.PROFILE_MATCHING_PREFERENCES_ALLOWED_FIELDS,
            profile_matching_preferences_max_length=dashboard_server.PROFILE_MATCHING_PREFERENCES_MAX_LENGTH,
        )

        self.assertFalse(handled)


    def test_dashboard_handler_post_uses_facade_injected_profile_create_helper(self):
        class FakeConnection:
            closed = False

            def close(self):
                self.closed = True

        class FakeHandler:
            path = "/api/profiles/create"
            status = None
            payload = None
            conn = FakeConnection()
            body = {"brief": "Senior backend roles."}

            def _read_json_body(self):
                return self.body

            def _connect(self):
                return self.conn

            def _json(self, status, payload):
                self.status = status
                self.payload = payload

        result = {"schema_version": "patched_profile_create_result_v1"}
        with unittest.mock.patch.object(dashboard_server, "create_profile_from_brief", return_value=result) as create_mock:
            handler = FakeHandler()
            dashboard_server.DashboardHandler.do_POST(handler)

        create_mock.assert_called_once_with(handler.conn, {"brief": "Senior backend roles."})
        self.assertTrue(handler.conn.closed)
        self.assertEqual(handler.status, HTTPStatus.OK)
        self.assertEqual(handler.payload, {"ok": True, "profile": result})


    def test_dashboard_handler_post_handles_alert_mode_with_decoded_profile_id(self):
        class FakeConnection:
            closed = False

            def close(self):
                self.closed = True

        class FakeHandler:
            path = "/api/profiles/jobs%3Afast/alert-mode"
            status = None
            payload = None
            conn = FakeConnection()

            def _read_json_body(self):
                return {"mode": "interrupt"}

            def _connect(self):
                return self.conn

            def _json(self, status, payload):
                self.status = status
                self.payload = payload

        result = {"profile_id": "jobs:fast", "alert_mode": "interrupt"}
        with unittest.mock.patch.object(
            dashboard_server.monitor_state,
            "update_profile_alert_mode",
            return_value=result,
        ) as update_mock:
            handler = FakeHandler()
            dashboard_server.DashboardHandler.do_POST(handler)

        update_mock.assert_called_once_with(handler.conn, profile_id="jobs:fast", mode="interrupt")
        self.assertTrue(handler.conn.closed)
        self.assertEqual(handler.status, HTTPStatus.OK)
        self.assertEqual(handler.payload, {"ok": True, "profile": result})


if __name__ == "__main__":
    unittest.main()
