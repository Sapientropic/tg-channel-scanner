import hashlib
import hmac
import json
import sqlite3
import time
import unittest
from contextlib import contextmanager
from http import HTTPStatus
from urllib.parse import urlencode

from scripts import desk_miniapp, desk_miniapp_routes, monitor_state
from scripts import dashboard_server


def signed_init_data(bot_token: str, *, user_id: int = 123456, auth_date: int | None = None) -> str:
    payload = {
        "auth_date": str(auth_date or int(time.time())),
        "query_id": "AAE-test-query",
        "user": json.dumps({"id": user_id, "first_name": "Demo"}, separators=(",", ":")),
    }
    data_check_string = "\n".join(f"{key}={value}" for key, value in sorted(payload.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode("utf-8"), hashlib.sha256).digest()
    payload["hash"] = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()
    return urlencode(payload)


class MiniAppAuthTests(unittest.TestCase):
    def test_validate_init_data_accepts_current_telegram_signature(self):
        init_data = signed_init_data("12345:token")

        result = desk_miniapp.validate_telegram_init_data(
            init_data,
            bot_token="12345:token",
            now=int(time.time()),
        )

        self.assertEqual(result["schema_version"], "telegram_miniapp_auth_v1")
        self.assertEqual(result["user_id"], "123456")

    def test_validate_init_data_rejects_modified_payload(self):
        init_data = signed_init_data("12345:token").replace("Demo", "Tampered")

        with self.assertRaisesRegex(ValueError, "signature"):
            desk_miniapp.validate_telegram_init_data(init_data, bot_token="12345:token")

    def test_validate_init_data_rejects_stale_auth_date(self):
        init_data = signed_init_data("12345:token", auth_date=1)

        with self.assertRaisesRegex(ValueError, "expired"):
            desk_miniapp.validate_telegram_init_data(init_data, bot_token="12345:token", now=90000)

    def test_authorize_rejects_non_loopback_without_init_data(self):
        class FakeHandler:
            headers = {}
            client_address = ("203.0.113.10", 50000)
            db_path = "/tmp/tgcs.db"

        with self.assertRaisesRegex(ValueError, "init data"):
            desk_miniapp.authorize_miniapp_request(
                FakeHandler(),
                is_loopback_address_fn=lambda value: str(value).startswith("127."),
                token_loader=lambda: "12345:token",
                allowed_chat_ids_fn=lambda _db_path: {"123456"},
            )

    def test_authorize_rejects_forwarded_remote_without_init_data(self):
        class FakeHandler:
            headers = {"X-Forwarded-For": "203.0.113.10"}
            client_address = ("127.0.0.1", 50000)
            db_path = "/tmp/tgcs.db"

        with self.assertRaisesRegex(ValueError, "init data"):
            desk_miniapp.authorize_miniapp_request(
                FakeHandler(),
                is_loopback_address_fn=lambda value: str(value).startswith("127.") or str(value) == "localhost",
                token_loader=lambda: "12345:token",
                allowed_chat_ids_fn=lambda _db_path: {"123456"},
            )

    def test_authorize_rejects_loopback_preview_when_disabled_for_public_boundary(self):
        class FakeHandler:
            headers = {}
            client_address = ("127.0.0.1", 50000)
            db_path = "/tmp/tgcs.db"

        with self.assertRaisesRegex(ValueError, "init data"):
            desk_miniapp.authorize_miniapp_request(
                FakeHandler(),
                is_loopback_address_fn=lambda value: str(value).startswith("127."),
                token_loader=lambda: "12345:token",
                allowed_chat_ids_fn=lambda _db_path: {"123456"},
                allow_loopback_preview=False,
            )

    def test_dashboard_authorize_uses_public_boundary_preview_setting(self):
        class FakeHandler:
            headers = {}
            client_address = ("127.0.0.1", 50000)
            db_path = "/tmp/tgcs.db"
            miniapp_only = True
            miniapp_allow_loopback_preview = False

        with self.assertRaisesRegex(ValueError, "init data"):
            dashboard_server.authorize_miniapp_request(FakeHandler())

    def test_authorize_rejects_signed_init_data_not_in_allowlist(self):
        class FakeHandler:
            headers = {desk_miniapp.MINIAPP_INIT_DATA_HEADER: signed_init_data("12345:token", user_id=123456)}
            client_address = ("203.0.113.10", 50000)
            db_path = "/tmp/tgcs.db"

        with self.assertRaisesRegex(ValueError, "not authorized"):
            desk_miniapp.authorize_miniapp_request(
                FakeHandler(),
                is_loopback_address_fn=lambda _value: False,
                token_loader=lambda: "12345:token",
                allowed_chat_ids_fn=lambda _db_path: {"654321"},
            )

    def test_authorize_accepts_signed_init_data_for_saved_user_id(self):
        class FakeHandler:
            headers = {desk_miniapp.MINIAPP_INIT_DATA_HEADER: signed_init_data("12345:token", user_id=123456)}
            client_address = ("203.0.113.10", 50000)
            db_path = "/tmp/tgcs.db"

        result = desk_miniapp.authorize_miniapp_request(
            FakeHandler(),
            is_loopback_address_fn=lambda _value: False,
            token_loader=lambda: "12345:token",
            allowed_chat_ids_fn=lambda _db_path: {"123456"},
        )

        self.assertEqual(result["source"], "telegram")
        self.assertEqual(result["user_id"], "123456")

    def test_authorize_rejects_oversized_init_data_header(self):
        class FakeHandler:
            headers = {desk_miniapp.MINIAPP_INIT_DATA_HEADER: "x" * (desk_miniapp.MINIAPP_INIT_DATA_MAX_LENGTH + 1)}
            client_address = ("127.0.0.1", 50000)
            db_path = "/tmp/tgcs.db"

        with self.assertRaisesRegex(ValueError, "too large"):
            desk_miniapp.authorize_miniapp_request(
                FakeHandler(),
                is_loopback_address_fn=lambda value: str(value).startswith("127."),
                token_loader=lambda: "12345:token",
                allowed_chat_ids_fn=lambda _db_path: {"123456"},
            )


class MiniAppRouteTests(unittest.TestCase):
    def _connection_with_cards(self):
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        monitor_state.init_db(conn)
        cards = monitor_state.upsert_review_cards(
            conn,
            profile_id="jobs-fast",
            run_id="run-1",
            items=[
                {
                    "topic": "Frontend Mini App contract",
                    "rating": "high",
                    "decision_state": {"status": "new", "semantic_cluster": "miniapp-1"},
                    "why": "Paid React work with clear budget.",
                    "source_excerpt": "Original post: React Mini App contract with a clear weekly budget. https://example.com/raw-link",
                    "source_message_refs": [{"channel": "miniapps_jobs", "id": 42, "url": "https://t.me/miniapps_jobs/42"}],
                }
            ],
        )
        return conn, cards

    def test_state_route_returns_review_cards_for_loopback_preview(self):
        conn, cards = self._connection_with_cards()
        conn.execute(
            """
            INSERT INTO feedback_events(event_id, card_id, profile_id, action, note, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            ("feedback-miniapp-learning", cards[0]["card_id"], "jobs-fast", "keep", "", monitor_state.utc_now()),
        )
        conn.commit()

        class FakeHandler:
            status = None
            payload = None
            conn_closed = False
            headers = {}
            client_address = ("127.0.0.1", 50000)

            def _connect(self):
                return conn

            def _json(self, status, payload):
                self.status = status
                self.payload = payload

        @contextmanager
        def close_after_use(connection):
            try:
                yield connection
            finally:
                self.assertIs(connection, conn)

        handler = FakeHandler()
        handled = desk_miniapp_routes.handle_miniapp_get_route(
            handler,
            "/api/miniapp/state",
            authorize_request=lambda _handler: {"source": "loopback_preview"},
            close_after_use=close_after_use,
            miniapp_state=desk_miniapp.miniapp_state,
        )

        self.assertTrue(handled)
        self.assertEqual(handler.status, HTTPStatus.OK)
        self.assertEqual(handler.payload["miniapp"]["schema_version"], "miniapp_review_state_v1")
        self.assertEqual(handler.payload["miniapp"]["cards"][0]["card_id"], cards[0]["card_id"])
        self.assertEqual(
            handler.payload["miniapp"]["cards"][0]["item"]["source_excerpt"],
            "React Mini App contract with a clear weekly budget. [link]",
        )
        learning = handler.payload["miniapp"]["learning_summary"]
        self.assertEqual(learning["schema_version"], "miniapp_learning_summary_v1")
        self.assertEqual(learning["current_decision_count"], 1)
        self.assertEqual(learning["exportable_count"], 1)
        self.assertEqual(learning["pending_profile_diff_count"], 0)
        self.assertEqual(learning["next_action"]["label"], "Suggest profile improvements")
        self.assertNotIn("profiles", handler.payload["miniapp"])
        self.assertNotIn("recent_impacts", handler.payload["miniapp"]["learning_summary"])
        self.assertNotIn("last_export_path", handler.payload["miniapp"]["learning_summary"])
        self.assertNotIn("private", json.dumps(handler.payload, ensure_ascii=False).lower())

    def test_state_route_exposes_public_source_recommendations(self):
        conn, _cards = self._connection_with_cards()

        class FakeHandler:
            status = None
            payload = None
            headers = {}
            client_address = ("127.0.0.1", 50000)

            def _connect(self):
                return conn

            def _json(self, status, payload):
                self.status = status
                self.payload = payload

        @contextmanager
        def close_after_use(connection):
            yield connection

        recommendations = [
            {
                "schema_version": "miniapp_source_recommendation_v1",
                "source_id": "telegram:remote_jobs",
                "channel": "remote_jobs",
                "label": "Remote Jobs",
                "topic": "jobs",
                "reason": "remote work",
                "installed": False,
            }
        ]
        handler = FakeHandler()
        handled = desk_miniapp_routes.handle_miniapp_get_route(
            handler,
            "/api/miniapp/state",
            authorize_request=lambda _handler: {"source": "loopback_preview"},
            close_after_use=close_after_use,
            miniapp_state=lambda _conn, auth: {
                "schema_version": "miniapp_review_state_v1",
                "auth": auth,
                "cards": [],
                "source_recommendations": recommendations,
            },
        )

        self.assertTrue(handled)
        self.assertEqual(handler.status, HTTPStatus.OK)
        self.assertEqual(handler.payload["miniapp"]["source_recommendations"], recommendations)

    def test_public_source_recommendations_use_mobile_safe_metadata_only(self):
        recommendations = desk_miniapp.miniapp_source_recommendations(limit=2)

        self.assertGreaterEqual(len(recommendations), 1)
        self.assertEqual(recommendations[0]["schema_version"], "miniapp_source_recommendation_v1")
        self.assertIn("source_id", recommendations[0])
        self.assertIn("label", recommendations[0])
        serialized = json.dumps(recommendations, ensure_ascii=False)
        self.assertNotIn("direct_page_status", serialized)
        self.assertNotIn("source_of_recommendation", serialized)
        self.assertNotIn("https://t.me", serialized)

    def test_source_starter_route_imports_recommended_sources(self):
        class FakeHandler:
            status = None
            payload = None
            headers = {}
            client_address = ("127.0.0.1", 50000)

            def _json(self, status, payload):
                self.status = status
                self.payload = payload

        calls = []
        handler = FakeHandler()
        handled = desk_miniapp_routes.handle_miniapp_post_route(
            handler,
            "/api/miniapp/sources/starter",
            {"topic": "jobs"},
            authorize_request=lambda _handler: {"source": "loopback_preview"},
            close_after_use=lambda connection: connection,
            monitor_state_module=monitor_state,
            import_starter_sources=lambda body: calls.append(body) or {"schema_version": "desk_source_import_result_v1", "topic": "jobs"},
        )

        self.assertTrue(handled)
        self.assertEqual(calls, [{"topic": "jobs"}])
        self.assertEqual(handler.status, HTTPStatus.OK)
        self.assertEqual(handler.payload["result"]["schema_version"], "desk_source_import_result_v1")

    def test_source_starter_route_rejects_unexpected_fields(self):
        with self.assertRaisesRegex(ValueError, "Unexpected Mini App source field"):
            desk_miniapp_routes.handle_miniapp_post_route(
                object(),
                "/api/miniapp/sources/starter",
                {"topic": "jobs", "path": "../private"},
                authorize_request=lambda _handler: {"source": "loopback_preview"},
                close_after_use=lambda connection: connection,
                monitor_state_module=monitor_state,
                import_starter_sources=lambda body: body,
            )

    def test_state_route_hides_report_paths_for_signed_telegram_users(self):
        conn, cards = self._connection_with_cards()
        conn.execute("UPDATE review_cards SET report_path = ? WHERE card_id = ?", ("output/jobs-fast/report.html", cards[0]["card_id"]))
        conn.commit()

        class FakeHandler:
            status = None
            payload = None
            headers = {}
            client_address = ("203.0.113.10", 50000)

            def _connect(self):
                return conn

            def _json(self, status, payload):
                self.status = status
                self.payload = payload

        @contextmanager
        def close_after_use(connection):
            yield connection

        handler = FakeHandler()
        handled = desk_miniapp_routes.handle_miniapp_get_route(
            handler,
            "/api/miniapp/state",
            authorize_request=lambda _handler: {"source": "telegram", "user_id": "123456"},
            close_after_use=close_after_use,
            miniapp_state=desk_miniapp.miniapp_state,
        )

        self.assertTrue(handled)
        self.assertEqual(handler.payload["miniapp"]["cards"][0]["report_path"], "")

    def test_state_route_hides_report_paths_for_miniapp_only_loopback_preview(self):
        conn, cards = self._connection_with_cards()
        conn.execute("UPDATE review_cards SET report_path = ? WHERE card_id = ?", ("output/jobs-fast/report.html", cards[0]["card_id"]))
        conn.commit()

        class FakeHandler:
            status = None
            payload = None
            headers = {}
            client_address = ("127.0.0.1", 50000)

            def _connect(self):
                return conn

            def _json(self, status, payload):
                self.status = status
                self.payload = payload

        @contextmanager
        def close_after_use(connection):
            yield connection

        handler = FakeHandler()
        handled = desk_miniapp_routes.handle_miniapp_get_route(
            handler,
            "/api/miniapp/state",
            authorize_request=lambda _handler: {"source": "loopback_preview", "miniapp_only": True},
            close_after_use=close_after_use,
            miniapp_state=desk_miniapp.miniapp_state,
        )

        self.assertTrue(handled)
        self.assertEqual(handler.payload["miniapp"]["cards"][0]["report_path"], "")

    def test_action_route_allows_only_existing_review_actions(self):
        conn, cards = self._connection_with_cards()

        class FakeHandler:
            status = None
            payload = None
            headers = {"Content-Type": "application/json"}
            client_address = ("127.0.0.1", 50000)

            def _connect(self):
                return conn

            def _json(self, status, payload):
                self.status = status
                self.payload = payload

        @contextmanager
        def close_after_use(connection):
            yield connection

        handler = FakeHandler()
        handled = desk_miniapp_routes.handle_miniapp_post_route(
            handler,
            f"/api/miniapp/review-cards/{cards[0]['card_id']}/action",
            {"action": "keep", "note": ""},
            authorize_request=lambda _handler: {"source": "loopback_preview"},
            close_after_use=close_after_use,
            monitor_state_module=monitor_state,
        )

        self.assertTrue(handled)
        self.assertEqual(handler.status, HTTPStatus.OK)
        self.assertEqual(handler.payload["card"]["status"], "kept")

        with self.assertRaisesRegex(ValueError, "Unsupported"):
            desk_miniapp_routes.handle_miniapp_post_route(
                handler,
                f"/api/miniapp/review-cards/{cards[0]['card_id']}/action",
                {"action": "shell", "note": ""},
                authorize_request=lambda _handler: {"source": "loopback_preview"},
                close_after_use=close_after_use,
                monitor_state_module=monitor_state,
            )

    def test_miniapp_card_projects_only_mobile_needed_alert_fields(self):
        card = desk_miniapp.miniapp_card(
            {
                "card_id": "card-1",
                "profile_id": "jobs-fast",
                "title": "Safe mobile card",
                "rating": "high",
                "decision_status": "new",
                "source_refs": [],
                "item": {
                    "why": "Safe summary.",
                    "decision_state": {
                        "schema_version": "decision_state_v1",
                        "status": "new",
                        "seen_count": 2,
                        "signals": ["new"],
                        "semantic_cluster": "internal-cluster",
                        "explanations": {
                            "match_confidence": "high",
                            "token": "NESTED_TOKEN_SHOULD_NOT_RENDER",
                            "raw_text": "NESTED_RAW_SHOULD_NOT_RENDER",
                        },
                    },
                    "raw_text": "RAW_TELEGRAM_BODY_SHOULD_NOT_RENDER",
                },
                "status": "pending",
                "opportunity_status": "open",
                "first_run_id": "run-internal-1",
                "last_run_id": "run-internal-2",
                "alert_summary": {
                    "schema_version": "review_card_alert_summary_v1",
                    "alert_count": 2,
                    "latest_status": "sent",
                    "latest_run_id": "run-secret-ish",
                    "latest_target_id": "telegram-bot-default",
                    "latest_target_type": "telegram_bot",
                    "latest_delivery_mode": "live",
                    "latest_delivery_status": "sent",
                    "latest_delivery_ok": True,
                    "latest_alerted_at": "2026-05-17T00:00:00Z",
                },
                "report_path": "output/jobs-fast/not-a-report.json",
            }
        )

        self.assertEqual(
            card["item"],
            {"why": "Safe summary.", "decision_state": {"status": "new", "seen_count": 2, "signals": ["new"]}},
        )
        self.assertEqual(
            card["alert_summary"],
            {
                "schema_version": "review_card_alert_summary_v1",
                "alert_count": 2,
                "latest_status": "sent",
                "latest_delivery_mode": "live",
                "latest_delivery_status": "sent",
                "latest_delivery_ok": True,
                "latest_alerted_at": "2026-05-17T00:00:00Z",
            },
        )
        serialized = json.dumps(card, ensure_ascii=False)
        self.assertNotIn("latest_target_id", serialized)
        self.assertNotIn("latest_run_id", serialized)
        self.assertNotIn("first_run_id", serialized)
        self.assertNotIn("last_run_id", serialized)
        self.assertNotIn("semantic_cluster", serialized)
        self.assertNotIn("NESTED_TOKEN_SHOULD_NOT_RENDER", serialized)
        self.assertNotIn("NESTED_RAW_SHOULD_NOT_RENDER", serialized)
        self.assertNotIn("RAW_TELEGRAM_BODY_SHOULD_NOT_RENDER", serialized)
        self.assertEqual(card["report_path"], "")

    def test_action_route_returns_miniapp_projected_card_response(self):
        conn, cards = self._connection_with_cards()

        class FakeHandler:
            status = None
            payload = None
            headers = {"Content-Type": "application/json"}
            client_address = ("127.0.0.1", 50000)

            def _connect(self):
                return conn

            def _json(self, status, payload):
                self.status = status
                self.payload = payload

        @contextmanager
        def close_after_use(connection):
            yield connection

        handler = FakeHandler()
        handled = desk_miniapp_routes.handle_miniapp_post_route(
            handler,
            f"/api/miniapp/review-cards/{cards[0]['card_id']}/action",
            {"action": "applied", "note": ""},
            authorize_request=lambda _handler: {"source": "loopback_preview"},
            close_after_use=close_after_use,
            monitor_state_module=monitor_state,
        )

        self.assertTrue(handled)
        self.assertEqual(handler.status, HTTPStatus.OK)
        self.assertEqual(handler.payload["card"]["schema_version"], "review_card_v1")
        serialized = json.dumps(handler.payload["card"], ensure_ascii=False)
        self.assertNotIn("item_key", serialized)
        self.assertNotIn("created_at", serialized)
        self.assertNotIn("handled_at", serialized)

    def test_action_route_hides_report_paths_for_miniapp_only_loopback_preview(self):
        conn, cards = self._connection_with_cards()
        conn.execute("UPDATE review_cards SET report_path = ? WHERE card_id = ?", ("output/jobs-fast/report.html", cards[0]["card_id"]))
        conn.commit()

        class FakeHandler:
            status = None
            payload = None
            headers = {"Content-Type": "application/json"}
            client_address = ("127.0.0.1", 50000)

            def _connect(self):
                return conn

            def _json(self, status, payload):
                self.status = status
                self.payload = payload

        @contextmanager
        def close_after_use(connection):
            yield connection

        handler = FakeHandler()
        handled = desk_miniapp_routes.handle_miniapp_post_route(
            handler,
            f"/api/miniapp/review-cards/{cards[0]['card_id']}/action",
            {"action": "saved", "note": ""},
            authorize_request=lambda _handler: {"source": "loopback_preview", "miniapp_only": True},
            close_after_use=close_after_use,
            monitor_state_module=monitor_state,
        )

        self.assertTrue(handled)
        self.assertEqual(handler.payload["card"]["report_path"], "")

    def test_unknown_miniapp_post_path_returns_not_found_without_fallthrough(self):
        class FakeHandler:
            path = "/api/miniapp/unknown"
            headers = {"Content-Type": "application/json"}
            client_address = ("127.0.0.1", 50000)
            status = None
            payload = None
            read_count = 0

            def _read_json_body(self):
                self.read_count += 1
                return {}

            def _json(self, status, payload):
                self.status = status
                self.payload = payload

        handler = FakeHandler()
        dashboard_server.DashboardHandler.do_POST(handler)

        self.assertEqual(handler.status, HTTPStatus.NOT_FOUND)
        self.assertEqual(handler.payload["error"], "miniapp_not_found")
        self.assertEqual(handler.read_count, 0)

    def test_miniapp_only_mode_blocks_dashboard_state_and_artifacts(self):
        for path in ("/api/state", "/artifacts/output/jobs-fast/report.html", "/"):
            with self.subTest(path=path):
                self.assertFalse(dashboard_server.is_miniapp_only_get_path(path))
        for path in ("/miniapp", "/miniapp/", "/api/miniapp/state", "/assets/miniapp-demo.js", "/tgcs-signal-icon.png"):
            with self.subTest(path=path):
                self.assertTrue(dashboard_server.is_miniapp_only_get_path(path))

    def test_miniapp_only_static_asset_allowlist_uses_miniapp_html_references(self):
        with self.subTest("referenced miniapp assets allowed"):
            self.assertTrue(
                dashboard_server.is_miniapp_only_static_asset_path(
                    "/assets/miniapp-abc.js",
                    miniapp_asset_paths={"/assets/miniapp-abc.js", "/assets/inbox-shared.js"},
                )
            )
            self.assertTrue(
                dashboard_server.is_miniapp_only_static_asset_path(
                    "/assets/inbox-shared.js",
                    miniapp_asset_paths={"/assets/miniapp-abc.js", "/assets/inbox-shared.js"},
                )
            )
        with self.subTest("desktop assets blocked"):
            self.assertFalse(
                dashboard_server.is_miniapp_only_static_asset_path(
                    "/assets/main-dashboard.js",
                    miniapp_asset_paths={"/assets/miniapp-abc.js", "/assets/inbox-shared.js"},
                )
            )
        with self.subTest("icon stays allowed"):
            self.assertTrue(dashboard_server.is_miniapp_only_static_asset_path("/tgcs-signal-icon.png", miniapp_asset_paths=set()))
        with self.subTest("miniapp entry stays allowed"):
            self.assertTrue(dashboard_server.is_miniapp_only_static_asset_path("/miniapp", miniapp_asset_paths=set()))
            self.assertTrue(dashboard_server.is_miniapp_only_static_asset_path("/miniapp/", miniapp_asset_paths=set()))

    def test_dashboard_handler_requires_json_for_telegram_miniapp_posts(self):
        class FakeHandler:
            path = "/api/miniapp/review-cards/card-1/action"
            headers = {desk_miniapp.MINIAPP_INIT_DATA_HEADER: "query_id=abc&hash=bad"}
            status = None
            payload = None

            def _read_json_body(self):
                raise AssertionError("body should not be read before content type validation")

            def _json(self, status, payload):
                self.status = status
                self.payload = payload

        handler = FakeHandler()
        dashboard_server.DashboardHandler.do_POST(handler)

        self.assertEqual(handler.status, HTTPStatus.BAD_REQUEST)
        self.assertIn("application/json", handler.payload["error"])


if __name__ == "__main__":
    unittest.main()
