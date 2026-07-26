from __future__ import annotations

import keyring

from .exceptions import CredentialStoreError


class CredentialStore:
    service_name = "speechkit"
    account_name = "sarvam"

    def get(self) -> str | None:
        try:
            return keyring.get_password(self.service_name, self.account_name)
        except Exception as error:
            raise CredentialStoreError("Credential store is unavailable.") from error

    def save(self, api_key: str) -> None:
        try:
            keyring.set_password(self.service_name, self.account_name, api_key)
        except Exception as error:
            raise CredentialStoreError("Credential store is unavailable.") from error

    def remove(self) -> None:
        try:
            keyring.delete_password(self.service_name, self.account_name)
        except keyring.errors.PasswordDeleteError:
            return
        except Exception as error:
            raise CredentialStoreError("Credential store is unavailable.") from error
