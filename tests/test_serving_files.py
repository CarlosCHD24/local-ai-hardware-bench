import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]


class ServingFilesTests(unittest.TestCase):
    def test_service_uses_launcher_and_user_configuration(self):
        unit = (ROOT / "deploy/systemd/local-ai-server.service").read_text()
        self.assertIn("EnvironmentFile=-%h/.config/local-ai/server.env", unit)
        self.assertIn("ExecStart=%h/local-ai-hardware-bench/bin/local-ai-server", unit)
        self.assertIn("Restart=on-failure", unit)

    def test_launcher_requires_authentication_and_disables_web_ui(self):
        launcher = (ROOT / "bin/local-ai-server").read_text()
        self.assertIn('--api-key-file "${api_key_file}"', launcher)
        self.assertIn("--no-webui", launcher)
        self.assertIn("--flash-attn on", launcher)
        self.assertIn("--cache-type-k q8_0", launcher)
        self.assertIn("--cache-type-v q8_0", launcher)

    def test_example_binds_specific_lan_address(self):
        config = (
            ROOT / "deploy/server/desktop-rtx3060-12gb.env.example"
        ).read_text()
        self.assertIn("LOCAL_AI_SERVER_HOST=192.168.3.42", config)
        self.assertNotIn("LOCAL_AI_SERVER_HOST=0.0.0.0", config)


if __name__ == "__main__":
    unittest.main()
