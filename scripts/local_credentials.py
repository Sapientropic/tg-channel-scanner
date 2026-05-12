"""Local-only Signal Desk secret storage adapters.

Environment variables remain the primary configuration path. This module only
wraps OS user secret stores for desktop convenience, and it must fail closed
when the platform has no usable local store.
"""

from __future__ import annotations

import ctypes
import importlib
import os
import sys
from ctypes import wintypes
from dataclasses import dataclass
from datetime import UTC, datetime


BACKEND_WINDOWS = "windows_credential_manager"
BACKEND_KEYRING = "keyring"
BACKEND_UNSUPPORTED = "unsupported"
KEYRING_USERNAME = "Signal Desk"
CRED_TYPE_GENERIC = 1
# Generic credentials are scoped to the current Windows user by Credential
# Manager. This persist mode keeps the secret across that user's logon sessions
# on the same machine, which is the intended Windows alpha boundary.
CRED_PERSIST_LOCAL_MACHINE = 2
ERROR_NOT_FOUND = 1168


class CredentialStoreError(RuntimeError):
    """Raised when the platform credential store cannot complete an operation."""


@dataclass(frozen=True)
class StoredSecret:
    secret: str
    updated_at: str | None = None


def _load_keyring():
    try:
        return importlib.import_module("keyring")
    except Exception:
        return None


def _usable_keyring_module():
    keyring = _load_keyring()
    if keyring is None:
        return None
    try:
        active_backend = keyring.get_keyring()
        priority = float(getattr(active_backend, "priority", 0) or 0)
    except Exception:
        return None
    backend_type = f"{type(active_backend).__module__}.{type(active_backend).__name__}".lower()
    if priority <= 0 or "null" in backend_type or "fail" in backend_type:
        return None
    return keyring


def backend() -> str:
    if os.name == "nt":
        return BACKEND_WINDOWS
    if _usable_keyring_module() is not None:
        return BACKEND_KEYRING
    return BACKEND_UNSUPPORTED


def store_label() -> str:
    selected = backend()
    if selected == BACKEND_WINDOWS:
        return "Windows Credential Manager"
    if selected == BACKEND_KEYRING:
        if sys.platform == "darwin":
            return "macOS Keychain"
        if sys.platform.startswith("linux"):
            return "Linux Secret Service/KWallet"
        return "system keyring"
    return "environment variables only"


def is_supported() -> bool:
    return backend() != BACKEND_UNSUPPORTED


class _FILETIME(ctypes.Structure):
    _fields_ = [
        ("dwLowDateTime", wintypes.DWORD),
        ("dwHighDateTime", wintypes.DWORD),
    ]


class _CREDENTIALW(ctypes.Structure):
    _fields_ = [
        ("Flags", wintypes.DWORD),
        ("Type", wintypes.DWORD),
        ("TargetName", wintypes.LPWSTR),
        ("Comment", wintypes.LPWSTR),
        ("LastWritten", _FILETIME),
        ("CredentialBlobSize", wintypes.DWORD),
        ("CredentialBlob", ctypes.POINTER(ctypes.c_ubyte)),
        ("Persist", wintypes.DWORD),
        ("AttributeCount", wintypes.DWORD),
        ("Attributes", ctypes.c_void_p),
        ("TargetAlias", wintypes.LPWSTR),
        ("UserName", wintypes.LPWSTR),
    ]


def _advapi32():
    if os.name != "nt":
        raise CredentialStoreError("Windows Credential Manager is not available on this platform.")
    library = ctypes.WinDLL("Advapi32.dll", use_last_error=True)
    library.CredWriteW.argtypes = [ctypes.POINTER(_CREDENTIALW), wintypes.DWORD]
    library.CredWriteW.restype = wintypes.BOOL
    library.CredReadW.argtypes = [
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        ctypes.POINTER(ctypes.POINTER(_CREDENTIALW)),
    ]
    library.CredReadW.restype = wintypes.BOOL
    library.CredDeleteW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD]
    library.CredDeleteW.restype = wintypes.BOOL
    library.CredFree.argtypes = [ctypes.c_void_p]
    library.CredFree.restype = None
    return library


def _keyring_or_error():
    keyring = _usable_keyring_module()
    if keyring is None:
        raise CredentialStoreError("No usable local keyring backend is available on this platform.")
    return keyring


def _last_error_message(prefix: str) -> CredentialStoreError:
    code = ctypes.get_last_error()
    return CredentialStoreError(f"{prefix} failed with Windows error {code}.")


def _filetime_to_iso(value: _FILETIME) -> str | None:
    raw = (int(value.dwHighDateTime) << 32) + int(value.dwLowDateTime)
    if raw <= 0:
        return None
    # Windows FILETIME counts 100ns intervals since 1601-01-01 UTC.
    unix_seconds = (raw - 116444736000000000) / 10_000_000
    return datetime.fromtimestamp(unix_seconds, tz=UTC).isoformat().replace("+00:00", "Z")


def _read_windows_secret(target_name: str) -> StoredSecret | None:
    library = _advapi32()
    credential = ctypes.POINTER(_CREDENTIALW)()
    ok = library.CredReadW(target_name, CRED_TYPE_GENERIC, 0, ctypes.byref(credential))
    if not ok:
        if ctypes.get_last_error() == ERROR_NOT_FOUND:
            return None
        raise _last_error_message("CredReadW")
    try:
        item = credential.contents
        if item.CredentialBlobSize <= 0:
            secret = ""
        else:
            blob = ctypes.string_at(item.CredentialBlob, item.CredentialBlobSize)
            secret = blob.decode("utf-16-le")
        return StoredSecret(secret=secret, updated_at=_filetime_to_iso(item.LastWritten))
    finally:
        library.CredFree(credential)


def read_secret(target_name: str) -> StoredSecret | None:
    selected = backend()
    if selected == BACKEND_WINDOWS:
        return _read_windows_secret(target_name)
    if selected == BACKEND_KEYRING:
        keyring = _keyring_or_error()
        try:
            secret = keyring.get_password(target_name, KEYRING_USERNAME)
        except Exception as exc:
            raise CredentialStoreError(f"keyring read failed: {exc}") from exc
        if not secret:
            return None
        return StoredSecret(secret=str(secret), updated_at=None)
    raise CredentialStoreError("Local secure storage is not available on this platform.")


def _write_windows_secret(target_name: str, secret: str, *, username: str = "Signal Desk") -> None:
    clean = str(secret or "").strip()
    if not clean:
        raise ValueError("Secret cannot be empty.")
    blob = clean.encode("utf-16-le")
    if len(blob) > 2048:
        raise ValueError("Secret is too long for local secure storage.")
    library = _advapi32()
    blob_buffer = ctypes.create_string_buffer(blob)
    credential = _CREDENTIALW()
    credential.Type = CRED_TYPE_GENERIC
    credential.TargetName = target_name
    credential.CredentialBlobSize = len(blob)
    credential.CredentialBlob = ctypes.cast(blob_buffer, ctypes.POINTER(ctypes.c_ubyte))
    credential.Persist = CRED_PERSIST_LOCAL_MACHINE
    credential.UserName = username
    if not library.CredWriteW(ctypes.byref(credential), 0):
        raise _last_error_message("CredWriteW")


def write_secret(target_name: str, secret: str, *, username: str = "Signal Desk") -> None:
    clean = str(secret or "").strip()
    if not clean:
        raise ValueError("Secret cannot be empty.")
    selected = backend()
    if selected == BACKEND_WINDOWS:
        _write_windows_secret(target_name, clean, username=username)
        return
    if selected == BACKEND_KEYRING:
        keyring = _keyring_or_error()
        try:
            keyring.set_password(target_name, KEYRING_USERNAME, clean)
        except Exception as exc:
            raise CredentialStoreError(f"keyring write failed: {exc}") from exc
        return
    raise CredentialStoreError("Local secure storage is not available on this platform.")


def _delete_windows_secret(target_name: str) -> None:
    library = _advapi32()
    ok = library.CredDeleteW(target_name, CRED_TYPE_GENERIC, 0)
    if ok or ctypes.get_last_error() == ERROR_NOT_FOUND:
        return
    raise _last_error_message("CredDeleteW")


def delete_secret(target_name: str) -> None:
    selected = backend()
    if selected == BACKEND_WINDOWS:
        _delete_windows_secret(target_name)
        return
    if selected == BACKEND_KEYRING:
        keyring = _keyring_or_error()
        try:
            keyring.delete_password(target_name, KEYRING_USERNAME)
        except Exception as exc:
            password_delete_error = getattr(getattr(keyring, "errors", object()), "PasswordDeleteError", ())
            if password_delete_error and isinstance(exc, password_delete_error):
                return
            raise CredentialStoreError(f"keyring delete failed: {exc}") from exc
        return
    raise CredentialStoreError("Local secure storage is not available on this platform.")
