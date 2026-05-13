import unittest

from .helpers import load_report_module


class ReportSourceTests(unittest.TestCase):
    def test_source_refs_keep_raw_messages_scoped_by_channel(self):
        report = load_report_module(self)
        messages = [
            {
                "id": 1,
                "channel": "channel_a",
                "date": "2026-05-06T08:00:00+00:00",
                "text": "Correct original text",
            },
            {
                "id": 1,
                "channel": "channel_b",
                "date": "2026-05-06T08:01:00+00:00",
                "text": "Wrong same-id text",
            },
        ]
        raw_jobs = [
            {
                "source_message_ids": [1],
                "source_message_refs": [{"channel": "channel_a", "id": 1}],
                "company": "Signal Co",
                "role": "Frontend Developer",
                "source": "channel_a",
                "rating": "high",
                "why": "Matches profile",
            }
        ]

        jobs, _ = report.deduplicate_jobs(raw_jobs, messages)
        html = report._render_job_card(jobs[0], 1, report.build_message_lookup(messages))

        self.assertEqual(jobs[0]["sources"], ["channel_a"])
        self.assertEqual(
            jobs[0]["source_message_refs"],
            [{"channel": "channel_a", "id": 1}],
        )
        self.assertIn("Correct original text", html)
        self.assertNotIn("Wrong same-id text", html)



if __name__ == "__main__":
    unittest.main()
