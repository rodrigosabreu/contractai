"""Service exports, loaded on demand to avoid optional dependency side effects."""
from importlib import import_module

_EXPORTS = {
    **{name: "auth" for name in (
        "get_password_hash", "verify_password", "create_access_token",
        "create_refresh_token", "create_reset_token", "decode_token",
        "authenticate_user", "get_current_user_dependency", "is_token_revoked",
        "revoke_token", "revoke_all_user_tokens",
    )},
    **{name: "llm_client" for name in (
        "LLMMessage", "LLMResponse", "LLMProvider", "BaseLLMProvider",
        "OpenAIProvider", "NVIDIAProvider", "LLMClient", "get_llm_client",
        "close_llm_client",
    )},
    **{name: "pdf_parser" for name in ("extract_text_from_pdf", "extract_tables_from_pdf")},
    **{name: "vector_store" for name in ("VectorStore", "get_vector_store")},
    "AnalysisService": "analysis",
    **{name: "connectors" for name in (
        "GoogleDriveService", "get_google_drive_service", "OneDriveService", "get_onedrive_service",
    )},
}

__all__ = list(_EXPORTS)


def __getattr__(name: str):
    module = _EXPORTS.get(name)
    if module is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(import_module(f"{__name__}.{module}"), name)
    globals()[name] = value
    return value
