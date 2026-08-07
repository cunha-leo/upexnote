"""
Armazenamento seguro de chaves API - usa o Windows Credential Manager (via
biblioteca "keyring"), o mesmo cofre onde o Windows guarda passwords de
Wi-Fi/contas. As chaves nunca sao escritas em texto simples num ficheiro do
projeto - ficam encriptadas pelo Windows, associadas a esta conta de utilizador.
"""
import keyring

SERVICE_NAME = "UpexNote"

KNOWN_KEYS = [
    "ASSEMBLYAI_API_KEY", "OPENAI_API_KEY", "DEEPGRAM_API_KEY",
    "DEEPSEEK_API_KEY", "GROK_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY",
    "UPEXNOTE_PG_PASSWORD", "UPEXNOTE_SUPPORT_CLIENT_SECRET",
]

# Categorizacao por finalidade (decisao de arquitetura 06/08/2026,
# FEATURE_VALIDATION_AND_ROADMAP.md, ADF-01): a tela de chaves deve mostrar
# pra que serve cada uma, nao so o fornecedor. Um fornecedor pode aparecer
# nas duas listas se suportar as duas funcoes (nenhum caso ainda hoje).
# Chaves fora deste dict (ex.: UPEXNOTE_PG_PASSWORD) nao sao motor de IA.
KEY_PURPOSES = {
    "ASSEMBLYAI_API_KEY": ["transcription"],
    "DEEPGRAM_API_KEY": ["transcription"],
    "OPENAI_API_KEY": ["transcription", "formatting"],
    "DEEPSEEK_API_KEY": ["formatting"],
    "GROK_API_KEY": ["formatting"],
    "ANTHROPIC_API_KEY": ["formatting"],
    "GEMINI_API_KEY": ["formatting"],
}


def key_purposes(name: str) -> list:
    return KEY_PURPOSES.get(name, [])


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
