import json
import unittest
from datetime import datetime, timezone
from decimal import Decimal
from urllib.error import HTTPError
from unittest.mock import Mock, patch

from scripts.automation import crypto_premium as monitor


NOW = datetime(2026, 10, 24, 1, 0, tzinfo=timezone.utc)
NOW_MS = int(NOW.timestamp() * 1000)
CONFIG = {"threshold_pct": -1, "recovery_pct": -0.5}


def snapshot(domestic="99000", overseas="100", usd_krw="1000", usd_usdt="1"):
    return monitor.PremiumSnapshot(
        upbit_krw=Decimal(domestic),
        binance_usdt=Decimal(overseas),
        usd_krw=Decimal(usd_krw),
        usd_usdt=Decimal(usd_usdt),
        observed_at=NOW,
    )


class PremiumCalculationTests(unittest.TestCase):
    def test_exact_negative_one_percent(self):
        self.assertEqual(Decimal("-1"), snapshot().premium_pct)

    def test_usdt_is_converted_to_usd_instead_of_assumed_equal(self):
        quote = snapshot("100000", usd_usdt="1.01")
        self.assertAlmostEqual(Decimal("1"), quote.premium_pct)

    @patch("scripts.automation.crypto_premium.fetch_json")
    def test_collects_matching_fresh_public_quotes(self, fetch):
        fetch.side_effect = lambda url, label: {
            monitor.UPBIT_URL: [{"market": "KRW-BTC", "trade_price": 99000, "timestamp": NOW_MS}],
            monitor.BINANCE_URL: {"symbol": "BTCUSDT", "lastPrice": "100", "closeTime": NOW_MS},
            monitor.FX_URL: {"data": {"currency": "USD", "rates": {"KRW": "1000", "USDT": "1"}}},
        }[url]
        result = monitor.collect_snapshot(now=NOW)
        self.assertEqual(Decimal("-1"), result.premium_pct)

    @patch("scripts.automation.crypto_premium.fetch_json")
    def test_old_quotes_are_rejected(self, fetch):
        fetch.side_effect = lambda url, label: {
            monitor.UPBIT_URL: [{"market": "KRW-BTC", "trade_price": 99000, "timestamp": NOW_MS - 600000}],
            monitor.BINANCE_URL: {"symbol": "BTCUSDT", "lastPrice": "100", "closeTime": NOW_MS},
            monitor.FX_URL: {"data": {"currency": "USD", "rates": {"KRW": "1000", "USDT": "1"}}},
        }[url]
        with self.assertRaisesRegex(ValueError, "오래되었거나"):
            monitor.collect_snapshot(now=NOW)

    def test_invalid_numbers_are_rejected(self):
        for value in (None, "NaN", "Infinity", "0", "-1", "invalid"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                monitor.positive_decimal(value, "가격")

    def test_message_names_comparison_sources_and_fx_basis(self):
        message = monitor.build_message(snapshot(), Decimal("-1"))
        for text in ("BTC", "-1.00%", "업비트", "바이낸스", "기준환율", "수수료"):
            self.assertIn(text, message)


class PremiumNotificationTests(unittest.TestCase):
    def setUp(self):
        self.backend = Mock()
        self.backend.get.return_value = {"active": False}
        self.sender = Mock(return_value=True)

    def run_check(self, quote):
        return monitor.process_snapshot(quote, CONFIG, self.backend, self.sender)

    def test_alerts_at_threshold_and_marks_only_after_delivery(self):
        self.assertTrue(self.run_check(snapshot()))
        self.sender.assert_called_once()
        self.assertTrue(self.backend.put.call_args.args[0]["active"])

    def test_above_threshold_does_not_alert(self):
        self.assertFalse(self.run_check(snapshot("99001")))
        self.sender.assert_not_called()
        self.backend.put.assert_not_called()

    def test_persistent_discount_does_not_repeat_alert(self):
        self.backend.get.return_value = {"active": True}
        self.assertFalse(self.run_check(snapshot("98000")))
        self.sender.assert_not_called()
        self.backend.put.assert_not_called()

    def test_small_bounce_does_not_rearm_alert(self):
        self.backend.get.return_value = {"active": True}
        self.assertFalse(self.run_check(snapshot("99400")))
        self.backend.put.assert_not_called()

    def test_recovery_rearms_alert_for_next_discount(self):
        state = {"active": True}
        self.backend.get.side_effect = lambda: state.copy()
        self.backend.put.side_effect = lambda value: state.update(value)
        self.assertFalse(self.run_check(snapshot("99500")))
        self.assertFalse(state["active"])
        self.assertTrue(self.run_check(snapshot("99000")))
        self.sender.assert_called_once()

    def test_failed_delivery_does_not_mark_as_sent(self):
        self.sender.return_value = False
        with self.assertRaises(RuntimeError):
            self.run_check(snapshot())
        self.backend.put.assert_not_called()

    def test_state_failure_prevents_a_duplicate_alert(self):
        self.backend.get.side_effect = RuntimeError("KV unavailable")
        with self.assertRaises(RuntimeError):
            self.run_check(snapshot())
        self.sender.assert_not_called()

    def test_malformed_state_is_not_treated_as_a_new_alert(self):
        self.backend.get.return_value = {"active": "false"}
        with self.assertRaises(ValueError):
            self.run_check(snapshot())
        self.sender.assert_not_called()

    def test_recovery_must_be_above_trigger(self):
        with self.assertRaises(ValueError):
            monitor.process_snapshot(snapshot(), {"threshold_pct": -1, "recovery_pct": -2}, self.backend, self.sender)
        self.sender.assert_not_called()

    @patch("scripts.automation.crypto_premium.send_telegram")
    @patch("scripts.automation.crypto_premium.BridgeState")
    @patch("scripts.automation.crypto_premium.collect_snapshot", return_value=snapshot())
    @patch("scripts.automation.crypto_premium.load_config", return_value={"crypto_premium": CONFIG})
    def test_dry_run_does_not_touch_state_or_telegram(self, _config, _quote, backend, sender):
        monitor.main(["--dry-run"])
        backend.assert_not_called()
        sender.assert_not_called()


class PremiumTransportTests(unittest.TestCase):
    @patch.dict("os.environ", {
        "TELEGRAM_MEMORY_BRIDGE_URL": "https://bridge.example",
        "TELEGRAM_MEMORY_BRIDGE_TOKEN": "test-token",
    })
    @patch("scripts.automation.crypto_premium.request_json")
    def test_state_requests_identify_service_without_changing_authentication(self, request):
        def cloudflare_request(_url, **kwargs):
            headers = kwargs["headers"]
            if headers.get("User-Agent") != "RH96-premium-monitor/1.0":
                raise RuntimeError("403: error code: 1010")
            self.assertEqual("Bearer test-token", headers["Authorization"])
            self.assertEqual("application/json", headers["Accept"])
            return {"ok": True, "found": False}

        request.side_effect = cloudflare_request
        backend = monitor.BridgeState()
        self.assertEqual({"active": False}, backend.get())
        backend.put({"active": True})
        self.assertEqual(2, request.call_count)

    @patch.dict("os.environ", {
        "TELEGRAM_MEMORY_BRIDGE_URL": "https://bridge.example/",
        "TELEGRAM_MEMORY_BRIDGE_TOKEN": "test-token",
    })
    @patch("scripts.automation.crypto_premium.request_json")
    def test_new_namespace_starts_inactive_and_writes_to_existing_bridge(self, request):
        request.side_effect = [{"ok": True, "found": False}, {"ok": True}]
        backend = monitor.BridgeState()
        self.assertEqual({"active": False}, backend.get())
        backend.put({"active": True})
        self.assertEqual("https://bridge.example/state/get", request.call_args_list[0].args[0])
        self.assertEqual("https://bridge.example/state/put", request.call_args_list[1].args[0])
        payload = json.loads(request.call_args.kwargs["data"])
        self.assertEqual(monitor.STATE_KEY, payload["key"])
        self.assertNotIn("ttl_seconds", payload)

    @patch.dict("os.environ", {
        "TELEGRAM_MEMORY_BRIDGE_URL": "https://bridge.example",
        "TELEGRAM_MEMORY_BRIDGE_TOKEN": "test-token",
    })
    @patch("scripts.automation.crypto_premium.request_json", return_value={"ok": False, "error": "unauthorized"})
    def test_unauthorized_state_access_does_not_fall_back_to_empty_state(self, _request):
        with self.assertRaises(RuntimeError):
            monitor.BridgeState().get()

    @patch("scripts.automation.crypto_premium.time.sleep")
    @patch("scripts.automation.crypto_premium.request_json")
    def test_forbidden_public_api_is_not_retried(self, request, sleep):
        request.side_effect = HTTPError("https://example.com", 403, "Forbidden", {}, None)
        with self.assertRaises(HTTPError):
            monitor.fetch_json("https://example.com", "시세")
        self.assertEqual(1, request.call_count)
        sleep.assert_not_called()

    @patch("scripts.automation.crypto_premium.time.sleep")
    @patch("scripts.automation.crypto_premium.request_json")
    def test_temporary_public_api_failure_is_retried_once(self, request, sleep):
        request.side_effect = [HTTPError("https://example.com", 503, "Unavailable", {}, None), {"ok": True}]
        self.assertEqual({"ok": True}, monitor.fetch_json("https://example.com", "시세"))
        self.assertEqual(2, request.call_count)
        sleep.assert_called_once()


if __name__ == "__main__":
    unittest.main()
