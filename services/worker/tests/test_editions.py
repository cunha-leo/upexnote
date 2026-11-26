import argparse
import io
import json
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch
from transcription import cli, db, edition

class EditionTests(unittest.TestCase):
    def test_personal_blocks_privileged_operations(self):
        for name, extra in [
            ("admin-data-sql", {}), ("api-admin-challenge", {}),
            ("support-admin-list", {}), ("account-elevate", {}),
            ("telemetry-overview", {}), ("tunnel-keep", {}),
            ("db-adopt-orphans", {}), ("account-login", {"mode":"vps"}),
            ("set-settings", {"storage_mode":"vps"}), ("db-check", {"stdin_password":True})
        ]:
            with self.subTest(name=name), patch.object(edition, "INTERNAL", False), redirect_stdout(io.StringIO()) as out:
                rc=cli._dispatch_edition(argparse.Namespace(command=name, **extra), {name:lambda _:self.fail("privileged handler reached")})
                self.assertEqual(rc, 1)
                self.assertEqual(json.loads(out.getvalue())["message"], "internal_only")
    def test_internal_dispatch_preserved(self):
        with patch.object(edition,"INTERNAL",True):
            self.assertEqual(cli._dispatch_edition(argparse.Namespace(command="admin-overview"),{"admin-overview":lambda _:42}),42)
    def test_personal_forces_sqlite(self):
        with patch.object(edition,"INTERNAL",False):
            self.assertEqual(db.storage_mode(),"local")
            self.assertIsNone(db.load_config())
            with self.assertRaises(PermissionError):
                db.set_mode_override("vps")
    def test_normal_dispatch_preserved(self):
        with patch.object(edition,"INTERNAL",False):
            self.assertEqual(cli._dispatch_edition(argparse.Namespace(command="engines"),{"engines":lambda _:42}),42)

if __name__ == "__main__":
    unittest.main()
