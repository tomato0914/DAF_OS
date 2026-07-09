"""
DAF OS v1.4 — 会社メモリ見直しサービス
memory/*.md を読み込み、最近の会議結果（report.md）と比較して
見直し提案を outputs/memory_update_suggestions.md に出力する。
メモリファイル自体は書き換えない。CEO が確認後に手動更新する。
"""

import json
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path


_MEMORY_FILES = {
    "company_memory.md":  "会社の価値観",
    "ceo_preferences.md": "CEOの意思決定スタイル",
    "lessons_learned.md": "学びと教訓",
}

_OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
_MODEL = "openrouter/openai/gpt-4o-mini"


# ──────────────────────────────────────────
# ファイル読み込み
# ──────────────────────────────────────────

def _load_memories(memory_dir: Path) -> dict[str, str]:
    result = {}
    for filename, label in _MEMORY_FILES.items():
        path = memory_dir / filename
        if path.exists():
            result[label] = path.read_text(encoding="utf-8").strip()
    return result


def _load_report(outputs: Path) -> str:
    """
    Quest51: meeting_log.md（5人分の生発言＋各自が根拠にしたmemory）があれば優先する。
    無い場合は report.md（Orionの最終提案のみ）にフォールバックする（後方互換）。
    """
    meeting_log_path = outputs / "meeting_log.md"
    if meeting_log_path.exists():
        return meeting_log_path.read_text(encoding="utf-8").strip()

    path = outputs / "report.md"
    return path.read_text(encoding="utf-8").strip() if path.exists() else ""


# ──────────────────────────────────────────
# LLM 呼び出し（OpenRouter 直接）
# ──────────────────────────────────────────

def _call_llm(prompt: str, api_key: str) -> str:
    payload = {
        "model": "openai/gpt-4o-mini",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
        "max_tokens": 2000,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/tomato0914/DAF_OS",
        "X-Title": "DAF OS Memory Review",
    }
    req = urllib.request.Request(
        _OPENROUTER_URL,
        data=json.dumps(payload).encode(),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read())
            return data["choices"][0]["message"]["content"]
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"OpenRouter API エラー {e.code}: {e.read().decode()}") from e
    except Exception as e:
        raise RuntimeError(f"LLM 呼び出し失敗: {e}") from e


# ──────────────────────────────────────────
# プロンプト生成
# ──────────────────────────────────────────

def _build_prompt(memories: dict[str, str], report: str) -> str:
    mem_text = "\n\n".join(
        f"=== {label} ===\n{content}"
        for label, content in memories.items()
    )

    report_section = (
        f"=== 最近の会議レポート（meeting_log.md優先、無ければreport.md） ===\n{report[:3000]}"
        if report
        else "=== 最近の会議レポート ===\n（meeting_log.md / report.md が見つかりません。メモリの内部整合性のみ確認してください）"
    )

    return f"""あなたはDAFの会社メモリ管理アドバイザーです。
以下の【現在の会社メモリ】と【最近の会議レポート】を比較・分析し、
メモリの見直し提案を作成してください。

重要なルール：
- メモリファイルを直接書き換える提案はしない（CEOが手動で判断する）
- 具体的かつ実行可能な提案だけを出す
- 「なんとなく古そう」ではなく、会議レポートの具体的な内容と照らした根拠を示す

---

{mem_text}

---

{report_section}

---

以下のMarkdown形式で出力してください。セクション名は必ず守ってください：

# メモリ見直し提案

> 分析日時: （今日の日付を入れる）
> ステータス: 要確認 / CEO未承認

---

## 維持する項目

（会議レポートでも引き続き有効と確認できた価値観・方針を列挙。根拠も1行で添える）

---

## 見直し候補

（以下の形式で記載）

### [項目名]
- **現在の記述**：（既存の文章を引用）
- **気になる点**：（会議レポートと照らして何が変わったか）
- **修正案**：（具体的な書き換え案）

---

## 新しく追加した方がよい項目

（会議レポートから浮かび上がった、まだメモリに書かれていない重要な学び・価値観）

---

## CEOへのメモ

（全体を通じた所感と、承認の際に特に判断が必要な点を2〜3文で）
"""


# ──────────────────────────────────────────
# 公開関数
# ──────────────────────────────────────────

def generate_memory_suggestions(
    outputs: Path,
    memory_dir: Path,
    openrouter_api_key: str,
) -> Path | None:
    """
    メモリ見直し提案を生成して outputs/memory_update_suggestions.md に保存する。
    成功したら Path を返す。失敗したら None を返す（例外を外に伝播させない）。
    """
    memories = _load_memories(memory_dir)
    if not memories:
        print("[Memory Review] memory/*.md が見つかりません → スキップ")
        return None

    from services.ai_runtime_guard import require_ai_enabled
    if not require_ai_enabled("Memory Review"):
        return None

    report = _load_report(outputs)

    print("[Memory Review] 会社メモリの見直し提案を生成中...")
    if not report:
        print("  ℹ️  meeting_log.md / report.md なし — メモリの内部整合性のみ分析します")

    try:
        prompt = _build_prompt(memories, report)
        result = _call_llm(prompt, openrouter_api_key)
    except RuntimeError as e:
        print(f"  [警告] {e} → スキップ")
        return None

    # 生成日時を確定値に上書き（LLMが返す日付は信頼しない）
    import re as _re
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    result = _re.sub(
        r"(> 分析日時[:：]\s*).*",
        rf"\g<1>{now_str}",
        result,
    )

    # フッター追記
    footer = (
        "\n\n---\n\n"
        "> **⚠️ このファイルはAIによる提案です。**  \n"
        "> `memory/` フォルダのファイルを直接書き換えるまで変更は反映されません。  \n"
        "> CEOが確認・承認後に手動で更新してください。\n"
    )
    content = result.strip() + footer

    out_path = outputs / "memory_update_suggestions.md"
    out_path.write_text(content, encoding="utf-8")
    print(f"  ✓ {out_path}")
    return out_path


def try_generate_memory_suggestions(
    outputs: Path,
    memory_dir: Path,
    openrouter_api_key: str | None,
) -> Path | None:
    """
    APIキー未設定時は安全にスキップする。
    """
    if not openrouter_api_key:
        print("[Memory Review] OPENROUTER_API_KEY 未設定 → スキップ")
        return None
    return generate_memory_suggestions(outputs, memory_dir, openrouter_api_key)
