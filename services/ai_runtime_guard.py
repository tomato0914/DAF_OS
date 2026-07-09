"""
DAF OS Quest118 — AI Runtime Guard / APIコスト防止

Claude Codeでの実装・テスト・Dashboard確認中に、OpenRouter / OpenAI等の
AI APIが意図せず呼び出され、トークンを消費する事故を防ぐための一元的な
Guardを提供する。

DAF OSの方針はLean AI First：

  Python → Rule Engine → Template → AI → CEO

AIは「最後の専門家」であり、開発中・テスト中・UI確認中に勝手に使われては
ならない。本モジュールは新しいAI機能を追加するものではなく、既存のAI
呼び出し箇所（Reference AI Analysis・IP DNA生成・IP Bible生成・
Style Guide生成・AI Review Engine・Image Generation Pipeline・
Meeting Crew等）の直前に挿入する「関所」を提供するだけ。

制御方法（環境変数）：
  DAF_AI_ENABLED=true|false   （既定: false）
  DAF_RUNTIME_MODE=development|production|test  （既定: development）

判定ルール（優先順位）：
  1. DAF_RUNTIME_MODE が "production" 以外（development・test・未設定・
     不明な値も含む）の場合は、DAF_AI_ENABLEDの値に関わらず常にAI OFF。
  2. DAF_RUNTIME_MODE が "production" の場合のみ、DAF_AI_ENABLED=true で
     AI ONになる。DAF_AI_ENABLED=false（既定）ならAI OFFのまま。

  → AI ONになるのは "DAF_RUNTIME_MODE=production かつ DAF_AI_ENABLED=true"
    の組み合わせのときだけ。環境変数が一切未設定の場合は必ずAI OFF。

必要な関数：
- is_ai_enabled() -> bool:                  AI呼び出しが許可されているか
- get_runtime_mode() -> str:                 現在のDAF_RUNTIME_MODEを返す
- require_ai_enabled(feature_name) -> bool:  AI呼び出し直前に呼ぶ。OFFの場合は
                                              理由をログへ出し、Falseを返す
                                              （呼び出し側はFalseならfallbackへ
                                              切り替える）
- get_ai_status() -> dict:                   Dashboard/API向けの状態一式を返す

使い方（既存のAI呼び出し箇所での典型パターン）：
    from services.ai_runtime_guard import require_ai_enabled
    if not require_ai_enabled("AI Review Engine"):
        # fallback / rule-based結果を返す
        ...

本モジュール自体はAI APIを一切呼び出さない（判定のみ）。
"""

import os

DEFAULT_RUNTIME_MODE = "development"
PRODUCTION_MODE = "production"
DEVELOPMENT_MODE = "development"
TEST_MODE = "test"

_VALID_MODES = (DEVELOPMENT_MODE, PRODUCTION_MODE, TEST_MODE)

DEFAULT_PROVIDER = "openrouter"


def get_runtime_mode() -> str:
    """
    現在のDAF_RUNTIME_MODEを返す。未設定・空文字・不明な値の場合は
    "development"（最も安全な既定値）にフォールバックする。
    """
    raw = (os.getenv("DAF_RUNTIME_MODE") or "").strip().lower()
    if raw in _VALID_MODES:
        return raw
    return DEFAULT_RUNTIME_MODE


def _ai_enabled_flag() -> bool:
    """DAF_AI_ENABLED環境変数のtruthy判定。未設定時はFalse（AI禁止側）。"""
    raw = (os.getenv("DAF_AI_ENABLED") or "").strip().lower()
    return raw in ("1", "true", "yes", "on")


def is_ai_enabled() -> bool:
    """
    AI API呼び出しが許可されているかを判定する。
    DAF_RUNTIME_MODE=production かつ DAF_AI_ENABLED=true の場合のみTrue。
    環境変数が未設定の場合は必ずFalse（デフォルトAI OFF）。
    """
    return get_runtime_mode() == PRODUCTION_MODE and _ai_enabled_flag()


def _disabled_reason() -> str:
    mode = get_runtime_mode()
    if mode != PRODUCTION_MODE:
        return f"DAF_RUNTIME_MODE is '{mode}' (AI is only allowed when DAF_RUNTIME_MODE=production)"
    if not _ai_enabled_flag():
        return "DAF_AI_ENABLED is false"
    return "AI disabled"


def require_ai_enabled(feature_name: str) -> bool:
    """
    AI API呼び出しの直前に呼ぶGuard関数。AI OFFの場合は理由をログへ出し、
    Falseを返す（例外は投げない）。呼び出し側は戻り値がFalseの場合、
    必ずfallback（ルールベース・テンプレート・Pillow等）へ切り替えること。

    戻り値: bool（True=AI呼び出し可、False=fallbackへ切り替える）
    """
    enabled = is_ai_enabled()
    if not enabled:
        print(f"[AI Runtime Guard] {feature_name}: AI OFF（{_disabled_reason()}）→ fallbackへ切り替えます")
    return enabled


def get_ai_status() -> dict:
    """
    Dashboard・APIへ表示するためのAI Runtime状態一式を返す。

    戻り値: {"ai_enabled": bool, "runtime_mode": str, "reason": str,
             "provider": str, "api_calls_blocked": bool}
    """
    mode = get_runtime_mode()
    enabled = is_ai_enabled()
    reason = (
        "DAF_RUNTIME_MODE=production and DAF_AI_ENABLED=true"
        if enabled else _disabled_reason()
    )
    return {
        "ai_enabled": enabled,
        "runtime_mode": mode,
        "reason": reason,
        "provider": DEFAULT_PROVIDER,
        "api_calls_blocked": not enabled,
    }


if __name__ == "__main__":
    # 動作確認用のCLI導線。
    #   python services/ai_runtime_guard.py
    import json
    print(json.dumps(get_ai_status(), ensure_ascii=False, indent=2))
