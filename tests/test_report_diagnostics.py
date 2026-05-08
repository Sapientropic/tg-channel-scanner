import unittest


class ReportDiagnosticsTests(unittest.TestCase):
    def test_empty_scan_explains_no_messages(self):
        from scripts import report_diagnostics

        diagnostics = report_diagnostics.build_diagnostics(
            messages=[],
            raw_items=[],
            meta={"total_messages_collected": 0, "channel_count": 2},
            ocr_enabled=False,
            llm_available=True,
        )

        codes = [item["code"] for item in diagnostics]
        self.assertIn("no_messages_fetched", codes)
        self.assertIn("Check the channel list", diagnostics[0]["next_step"])

    def test_all_filtered_out_explains_profile_or_llm_filter(self):
        from scripts import report_diagnostics

        diagnostics = report_diagnostics.build_diagnostics(
            messages=[{"id": 1, "text": "not relevant"}],
            raw_items=[],
            meta={"total_messages_collected": 1, "channel_count": 1},
            ocr_enabled=False,
            llm_available=True,
        )

        codes = [item["code"] for item in diagnostics]
        self.assertIn("all_filtered_out", codes)

    def test_scan_incomplete_failures_and_disabled_ocr_are_reported(self):
        from scripts import report_diagnostics

        diagnostics = report_diagnostics.build_diagnostics(
            messages=[{"id": 1, "text": "", "media_group": "photo"}],
            raw_items=[],
            meta={
                "total_messages_collected": 1,
                "incomplete_channels": ["jobs"],
                "failed_channels": ["broken"],
                "ocr_enabled": False,
            },
            ocr_enabled=False,
            llm_available=True,
        )

        codes = {item["code"] for item in diagnostics}
        self.assertIn("scan_incomplete", codes)
        self.assertIn("channel_failures", codes)
        self.assertIn("ocr_disabled_media_present", codes)

    def test_llm_unavailable_is_a_diagnostic(self):
        from scripts import report_diagnostics

        diagnostics = report_diagnostics.build_diagnostics(
            messages=[{"id": 1, "text": "job"}],
            raw_items=[],
            meta={"total_messages_collected": 1},
            ocr_enabled=False,
            llm_available=False,
        )

        self.assertIn("llm_unavailable", [item["code"] for item in diagnostics])


if __name__ == "__main__":
    unittest.main()
