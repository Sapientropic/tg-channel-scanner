import unittest
from http import HTTPStatus
from unittest.mock import patch

from scripts import dashboard_server, desk_source_routes


class DashboardSourceRouteTests(unittest.TestCase):
    def test_source_route_owner_handles_enabled_route_with_decoded_source_id(self):
        class FakeHandler:
            status = None
            payload = None

            def _json(self, status, payload):
                self.status = status
                self.payload = payload

        features = []
        body = {"enabled": False}

        handler = FakeHandler()
        handled = desk_source_routes.handle_source_post_route(
            handler,
            "/api/desk/sources/telegram%3Aremote_jobs/enabled",
            body,
            require_loopback_access=lambda value, feature: features.append((value, feature)),
            preview_desk_source_import=lambda payload: {},
            import_desk_sources=lambda payload: {},
            import_starter_sources=lambda payload: {},
            run_source_assistant=lambda payload: {},
            set_desk_source_enabled=lambda source_id, payload: {"source_id": source_id, "body": dict(payload)},
            set_desk_source_topics=lambda source_id, payload: {},
            remove_desk_source=lambda source_id, payload: {},
        )

        self.assertTrue(handled)
        self.assertEqual(features, [(handler, "Source library")])
        self.assertEqual(handler.status, HTTPStatus.OK)
        self.assertEqual(
            handler.payload,
            {"ok": True, "sources": {"source_id": "telegram:remote_jobs", "body": body}},
        )


    def test_source_route_owner_returns_false_for_non_source_path(self):
        handled = desk_source_routes.handle_source_post_route(
            object(),
            "/api/feedback/export",
            {},
            require_loopback_access=lambda handler, feature: None,
            preview_desk_source_import=lambda payload: {},
            import_desk_sources=lambda payload: {},
            import_starter_sources=lambda payload: {},
            run_source_assistant=lambda payload: {},
            set_desk_source_enabled=lambda source_id, payload: {},
            set_desk_source_topics=lambda source_id, payload: {},
            remove_desk_source=lambda source_id, payload: {},
        )

        self.assertFalse(handled)


    def test_dashboard_handler_post_uses_facade_injected_source_action_helpers(self):
        class FakeHandler:
            status = None
            payload = None

            def __init__(self, path, body):
                self.path = path
                self.body = body

            def _read_json_body(self):
                return self.body

            def _json(self, status, payload):
                self.status = status
                self.payload = payload

        cases = [
            ("/api/desk/sources/preview", "preview_desk_source_import", "result", ({"sources": []},)),
            ("/api/desk/sources/import", "import_desk_sources", "result", ({"sources": []},)),
            ("/api/desk/sources/starter", "import_starter_sources", "result", ({"topic": "jobs"},)),
            ("/api/desk/sources/assistant", "run_source_assistant", "result", ({"instruction": "add remote jobs"},)),
        ]
        for path, helper_name, payload_key, expected_args in cases:
            with self.subTest(path=path):
                result = {"schema_version": f"patched_{helper_name}_v1"}
                with patch.object(dashboard_server, helper_name, return_value=result) as helper_mock:
                    handler = FakeHandler(path, expected_args[0])
                    dashboard_server.DashboardHandler.do_POST(handler)

                helper_mock.assert_called_once_with(*expected_args)
                self.assertEqual(handler.status, HTTPStatus.OK)
                self.assertEqual(handler.payload, {"ok": True, payload_key: result})


    def test_dashboard_handler_post_uses_facade_injected_source_mutation_helpers(self):
        class FakeHandler:
            status = None
            payload = None

            def __init__(self, path, body):
                self.path = path
                self.body = body

            def _read_json_body(self):
                return self.body

            def _json(self, status, payload):
                self.status = status
                self.payload = payload

        cases = [
            ("/api/desk/sources/telegram%3Aremote_jobs/enabled", "set_desk_source_enabled", {"enabled": True}),
            ("/api/desk/sources/telegram%3Aremote_jobs/topics", "set_desk_source_topics", {"topics": ["ai"]}),
            ("/api/desk/sources/telegram%3Aremote_jobs/remove", "remove_desk_source", {"confirm": True}),
        ]
        for path, helper_name, body in cases:
            with self.subTest(path=path):
                result = {"schema_version": f"patched_{helper_name}_v1"}
                with patch.object(dashboard_server, helper_name, return_value=result) as helper_mock:
                    handler = FakeHandler(path, body)
                    dashboard_server.DashboardHandler.do_POST(handler)

                helper_mock.assert_called_once_with("telegram:remote_jobs", body)
                self.assertEqual(handler.status, HTTPStatus.OK)
                self.assertEqual(handler.payload, {"ok": True, "sources": result})


if __name__ == "__main__":
    unittest.main()
