import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "automation"))

import notify  # noqa: E402


class NotifyTests(unittest.TestCase):
    @patch("notify.time.sleep")
    @patch("notify._send_single_telegram", side_effect=[False, True])
    def test_send_telegram_retries_transient_failure(self, send_mock, sleep_mock) -> None:
        sent = notify.send_telegram(
            "테스트 메시지",
            fail_on_error=False,
            retry_count=1,
            retry_delay_seconds=0.1,
        )

        self.assertTrue(sent)
        self.assertEqual(2, send_mock.call_count)
        sleep_mock.assert_called_once_with(0.1)

    @patch("notify.time.sleep")
    @patch("notify._send_single_telegram", return_value=False)
    def test_send_telegram_raises_after_retries_when_required(self, send_mock, sleep_mock) -> None:
        with self.assertRaisesRegex(RuntimeError, "텔레그램 발송이 3회 모두 실패했습니다"):
            notify.send_telegram(
                "테스트 메시지",
                fail_on_error=True,
                retry_count=2,
                retry_delay_seconds=0.1,
            )

        self.assertEqual(3, send_mock.call_count)
        self.assertEqual(2, sleep_mock.call_count)


if __name__ == "__main__":
    unittest.main()
