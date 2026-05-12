import types
import unittest
from unittest.mock import patch

from scripts import local_credentials


class FakeKeyringModule:
    def __init__(self, *, priority: float = 1.0):
        self.store: dict[tuple[str, str], str] = {}
        self._backend = types.SimpleNamespace(priority=priority)

        class PasswordDeleteError(Exception):
            pass

        self.errors = types.SimpleNamespace(PasswordDeleteError=PasswordDeleteError)

    def get_keyring(self):
        return self._backend

    def get_password(self, service_name: str, username: str):
        return self.store.get((service_name, username))

    def set_password(self, service_name: str, username: str, password: str):
        self.store[(service_name, username)] = password

    def delete_password(self, service_name: str, username: str):
        self.store.pop((service_name, username), None)


class LocalCredentialsTests(unittest.TestCase):
    def test_keyring_backend_reads_writes_and_deletes_posix_secrets(self):
        keyring = FakeKeyringModule()
        with patch.object(local_credentials.os, "name", "posix"):
            with patch.object(local_credentials, "_load_keyring", return_value=keyring, create=True):
                self.assertTrue(local_credentials.is_supported())
                self.assertEqual(local_credentials.backend(), "keyring")
                self.assertNotEqual(local_credentials.store_label(), "environment variables only")

                local_credentials.write_secret("tgcs.test", " stored-secret ")
                stored = local_credentials.read_secret("tgcs.test")
                local_credentials.delete_secret("tgcs.test")

        self.assertIsNotNone(stored)
        self.assertEqual(stored.secret, "stored-secret")
        self.assertIsNone(keyring.store.get(("tgcs.test", "Signal Desk")))

    def test_null_keyring_backend_is_treated_as_unsupported(self):
        keyring = FakeKeyringModule(priority=0)
        with patch.object(local_credentials.os, "name", "posix"):
            with patch.object(local_credentials, "_load_keyring", return_value=keyring, create=True):
                self.assertFalse(local_credentials.is_supported())
                self.assertEqual(local_credentials.backend(), "unsupported")
                with self.assertRaises(local_credentials.CredentialStoreError):
                    local_credentials.read_secret("tgcs.test")


if __name__ == "__main__":
    unittest.main()
