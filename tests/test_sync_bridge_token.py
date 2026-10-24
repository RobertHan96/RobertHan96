import unittest
from unittest.mock import patch

from scripts.automation import sync_bridge_token as sync


class BridgeTokenSyncTests(unittest.TestCase):
    def test_worker_name_is_taken_from_the_configured_bridge_url(self):
        self.assertEqual("rh96-telegram-memory-0326", sync.worker_name(
            "https://rh96-telegram-memory-0326.awdudtls.workers.dev/",
        ))

    def test_invalid_target_is_rejected(self):
        for url in ("http://a.b.workers.dev", "https://evil.example", "https://a.b.workers.dev.evil.example", "https://a.b.workers.dev/other"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                sync.worker_name(url)

    @patch.dict("os.environ", {
        "TELEGRAM_MEMORY_BRIDGE_URL": "https://target.account.workers.dev",
        "TELEGRAM_MEMORY_BRIDGE_TOKEN": "existing-bridge-token",
        "CLOUDFLARE_ACCOUNT_ID": "account-id",
        "CLOUDFLARE_API_TOKEN": "cloudflare-api-token",
    })
    @patch("scripts.automation.sync_bridge_token.api_json")
    @patch("scripts.automation.sync_bridge_token.bridge_authorized", return_value=True)
    def test_already_matching_token_does_not_change_worker(self, _check, api):
        sync.sync_token()
        api.assert_not_called()

    @patch.dict("os.environ", {
        "TELEGRAM_MEMORY_BRIDGE_URL": "https://target.account.workers.dev",
        "TELEGRAM_MEMORY_BRIDGE_TOKEN": "existing-bridge-token",
        "CLOUDFLARE_ACCOUNT_ID": "account-id",
        "CLOUDFLARE_API_TOKEN": "cloudflare-api-token",
    })
    @patch("scripts.automation.sync_bridge_token.api_json")
    @patch("scripts.automation.sync_bridge_token.bridge_authorized", side_effect=[False, True])
    def test_only_target_bridge_token_is_updated(self, check, api):
        api.side_effect = [
            {"success": True, "result": [{"name": "GITHUB_TOKEN"}]},
            {"success": True},
        ]
        sync.sync_token()
        self.assertEqual(2, api.call_count)
        self.assertEqual("GET", api.call_args_list[0].kwargs["method"])
        update = api.call_args_list[1]
        self.assertTrue(update.args[0].endswith("/workers/scripts/target/secrets"))
        self.assertEqual("PUT", update.kwargs["method"])
        self.assertEqual({
            "name": "TELEGRAM_MEMORY_BRIDGE_TOKEN",
            "text": "existing-bridge-token",
            "type": "secret_text",
        }, update.kwargs["payload"])
        self.assertEqual(2, check.call_count)


if __name__ == "__main__":
    unittest.main()
