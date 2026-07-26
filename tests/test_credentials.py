import pytest

from speechkit.credentials import CredentialStore, CredentialStoreError


def test_store_reads_saves_and_removes_only_the_sarvam_entry(monkeypatch):
    calls = []
    monkeypatch.setattr("speechkit.credentials.keyring.get_password", lambda service, account: calls.append(("get", service, account)) or "stored")
    monkeypatch.setattr("speechkit.credentials.keyring.set_password", lambda service, account, value: calls.append(("set", service, account, value)))
    monkeypatch.setattr("speechkit.credentials.keyring.delete_password", lambda service, account: calls.append(("delete", service, account)))
    store = CredentialStore()

    assert store.get() == "stored"
    store.save("new-key")
    store.remove()

    assert calls == [
        ("get", "speechkit", "sarvam"),
        ("set", "speechkit", "sarvam", "new-key"),
        ("delete", "speechkit", "sarvam"),
    ]


def test_store_translates_keychain_failures(monkeypatch):
    monkeypatch.setattr("speechkit.credentials.keyring.get_password", lambda *_: (_ for _ in ()).throw(RuntimeError("backend unavailable")))

    with pytest.raises(CredentialStoreError):
        CredentialStore().get()
