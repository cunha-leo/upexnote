"""
Armazenamento seguro de chaves API - usa o Windows Credential Manager (via
biblioteca "keyring"), o mesmo cofre onde o Windows guarda passwords de
Wi-Fi/contas. As chaves nunca sao escritas em texto simples num ficheiro do
projeto - ficam encriptadas pelo Windows, associadas a esta conta de utilizador.
"""
import keyring

SERVICE_NAME = "UpexNote"

KNOWN_KEYS = ["ASSEMBLYAI_API_KEY", "OPENAI_API_KEY", "DEEPGRAM_API_KEY", "UPEXNOTE_PG_PASSWORD"]


def get_key(name: str) -> str:
    return keyring.get_password(SERVICE_NAME, name) or ""


def set_key(name: str, value: str) -> None:
    if value:
        keyring.set_password(SERVICE_NAME, name, value)
    else:
        clear_key(name)


def clear_key(name: str) -> None:
    try:
        keyring.delete_password(SERVICE_NAME, name)
    except keyring.errors.PasswordDeleteError:
        pass
