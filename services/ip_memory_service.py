"""
DAF OS Quest104 — IP Memory Engine

Quest101〜103はReference画像（1件単位）の登録・解析までを実装した。
Quest104では、Character単体ではなく「IP全体の知識」を蓄積・成長させる
基盤として IP Memory を導入する。

流れ（設計思想）：
  Reference（画像）→ Analysis（Quest103のAI解析）→ IP Memory（本質の蓄積）
  → Asset Generation（将来）

IP Memoryは1つのIPにつき以下7セクションを持つ構造とする。Quest104で
実装するのは DNA のみで、他は将来追加しやすいよう空のプレースホルダとして
キーだけ用意する（"Coming Soon"）：
  DNA / Character Bible / World Bible / Style Guide / Prompt History /
  Review History / Evolution History

DNAはReferenceの複製ではない。複数Referenceの共通点から「本質」を抽出した
ものであり、generate_dna_from_reference()はあくまで"提案"を返すのみで、
save_ip()/update_dna()を明示的に呼ぶまでip_memory.jsonへは反映されない
（Quest103のAI解析と同じ、CEOが確認・修正できる補助機能という方針）。

保存先：
  outputs/ip_memory/<ip_name>/ip_memory.json
Reference Library（outputs/reference_library/）とは物理的に分離する
（Referenceは"素材"、IP Memoryは"抽出された知識"という役割の違いを保つため）。

必要な関数：
- create_ip(ip_name):                  新規IPの空箱（DNA含む全セクション）を作成する
- load_ip(ip_name):                    ip_memory.jsonを読み込む
- save_ip(ip_name, ip_data):           ip_memory.json全体を保存する
- list_ips():                          登録済みIP一覧を返す（Dashboard向け）
- update_dna(ip_name, dna_updates):    DNAの一部フィールドだけを更新する
- generate_dna_from_reference(...):    Reference群からDNAの"提案"を生成する
                                        （保存はしない）

CLI:
  python services/ip_memory_service.py [ip_name]

ディレクトリ未存在・JSON破損・書き込み失敗のいずれでも例外を投げず、
DAF OS全体を止めない。
"""

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

_REPO_ROOT = str(Path(__file__).parent.parent)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

_BASE_DIR = Path(__file__).parent.parent
_OUTPUTS_DIR = _BASE_DIR / "outputs"
_IP_MEMORY_DIR_NAME = "ip_memory"

_DNA_GROUPS = {
    "identity": ("name", "species", "type"),
    "personality": ("personality", "values", "target_emotion"),
    "visual": ("color_palette", "line_style", "eye_style", "body_style"),
    "brand": ("positioning", "audience"),
    "rules": ("must_have", "must_not"),
}


def _empty_dna() -> dict:
    dna = {group: {key: "" for key in keys} for group, keys in _DNA_GROUPS.items()}
    dna["keywords"] = []
    return dna


def _empty_ip(ip_name: str) -> dict:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    return {
        "ip_name": ip_name,
        "dna": _empty_dna(),
        # Quest104ではDNA以外は空のプレースホルダ。将来Character Bible等を
        # ここへ実装する際も、ip_memory.jsonのスキーマ自体は変えずに済む。
        "character_bible": {},
        "world_bible": {},
        "style_guide": {},
        "prompt_history": [],
        "review_history": [],
        "evolution_history": [],
        "metadata": {"created_at": now, "updated_at": now, "version": 1},
    }


def _library_root(outputs_dir: Path | None = None) -> Path:
    return (outputs_dir or _OUTPUTS_DIR) / _IP_MEMORY_DIR_NAME


def _safe_ip_name(ip_name: str) -> str:
    """IP名をフォルダ名として安全な形（英数字・ハイフン・アンダースコア）に丸める。"""
    safe = re.sub(r"[^\w\-]", "_", (ip_name or "").strip()) or ""
    return safe


def _ip_dir(ip_name: str, outputs_dir: Path | None = None) -> Path | None:
    safe = _safe_ip_name(ip_name)
    if not safe:
        return None
    return _library_root(outputs_dir) / safe


def ip_dir_path(ip_name: str, outputs_dir: Path | None = None) -> Path | None:
    """
    Quest105：IPフォルダ（outputs/ip_memory/<safe_ip_name>/）のPathを返す。
    services/ip_bible_service.py がip_bible.mdの保存先を組み立てる際、
    IP名のサニタイズ（パストラバーサル対策）ロジックを二重実装しないよう
    公開する。IP名が空・不正な場合はNoneを返す。
    """
    return _ip_dir(ip_name, outputs_dir)


def create_ip(ip_name: str, outputs_dir: Path | None = None) -> dict:
    """
    新規IPの空箱（DNA＝全フィールド空文字/空配列、他セクションは空の
    プレースホルダ）を作成し、outputs/ip_memory/<ip_name>/ip_memory.json
    へ保存する。

    既に同名IPが存在する場合は上書きせず、既存データをそのまま返す
    （ok=Trueのまま。誤って空箱で潰さないための安全策）。

    戻り値: {"ok": bool, "path": str | None, "ip": dict | None,
             "already_exists": bool, "error": str | None}
    書き込み失敗時も例外を投げない。
    """
    try:
        safe_name = _safe_ip_name(ip_name)
        if not safe_name:
            return {"ok": False, "path": None, "ip": None, "already_exists": False,
                     "error": "IP名を入力してください"}

        ip_dir = _library_root(outputs_dir) / safe_name
        ip_dir.mkdir(parents=True, exist_ok=True)
        path = ip_dir / "ip_memory.json"

        if path.exists():
            existing = load_ip(safe_name, outputs_dir=outputs_dir)
            return {"ok": True, "path": str(path), "ip": existing, "already_exists": True, "error": None}

        ip_data = _empty_ip(safe_name)
        path.write_text(json.dumps(ip_data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return {"ok": True, "path": str(path), "ip": ip_data, "already_exists": False, "error": None}
    except Exception as e:
        print(f"[警告] IP Memoryの作成に失敗しました（{ip_name}）：{e}")
        return {"ok": False, "path": None, "ip": None, "already_exists": False, "error": str(e)}


def load_ip(ip_name: str, outputs_dir: Path | None = None) -> dict | None:
    """
    指定IPのip_memory.jsonを読み込む。未存在・破損の場合はNoneを返す
    （例外を投げない）。
    """
    try:
        ip_dir = _ip_dir(ip_name, outputs_dir)
        if ip_dir is None:
            return None
        path = ip_dir / "ip_memory.json"
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[警告] IP Memoryの読み込みに失敗しました（{ip_name}）：{e}")
        return None


def save_ip(ip_name: str, ip_data: dict, outputs_dir: Path | None = None) -> dict:
    """
    ip_memory.json全体を保存する（metadata.updated_atを更新し、versionを
    1つ増やす）。IPフォルダが無ければ作成する。

    戻り値: {"ok": bool, "path": str | None, "ip": dict | None, "error": str | None}
    例外を投げない。
    """
    try:
        safe_name = _safe_ip_name(ip_name)
        if not safe_name:
            return {"ok": False, "path": None, "ip": None, "error": "IP名を入力してください"}

        ip_dir = _library_root(outputs_dir) / safe_name
        ip_dir.mkdir(parents=True, exist_ok=True)
        path = ip_dir / "ip_memory.json"

        ip_data = dict(ip_data or {})
        ip_data["ip_name"] = safe_name
        metadata = dict(ip_data.get("metadata") or {})
        metadata["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
        metadata.setdefault("created_at", metadata["updated_at"])
        metadata["version"] = int(metadata.get("version") or 0) + 1
        ip_data["metadata"] = metadata

        path.write_text(json.dumps(ip_data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return {"ok": True, "path": str(path), "ip": ip_data, "error": None}
    except Exception as e:
        print(f"[警告] IP Memoryの保存に失敗しました（{ip_name}）：{e}")
        return {"ok": False, "path": None, "ip": None, "error": str(e)}


def list_ips(outputs_dir: Path | None = None) -> list[dict]:
    """
    登録済みIP一覧を返す（ip_name昇順）。ディレクトリ未存在・読み込み失敗
    のいずれでも例外を投げず、空リスト・スキップで対応する。

    戻り値: [{"ip_name": str, "created_at": str, "updated_at": str,
              "version": int, "dna_name": str}, ...]
    """
    try:
        root = _library_root(outputs_dir)
        if not root.exists():
            return []
        results = []
        for sub in sorted(root.iterdir()):
            if not sub.is_dir():
                continue
            ip = load_ip(sub.name, outputs_dir=outputs_dir)
            if not ip:
                continue
            metadata = ip.get("metadata") or {}
            dna = ip.get("dna") or {}
            identity = dna.get("identity") or {}
            results.append({
                "ip_name": ip.get("ip_name", sub.name),
                "created_at": metadata.get("created_at"),
                "updated_at": metadata.get("updated_at"),
                "version": metadata.get("version"),
                "dna_name": identity.get("name") or "",
            })
        return results
    except Exception as e:
        print(f"[警告] IP Memory一覧の取得に失敗しました：{e}")
        return []


def update_dna(ip_name: str, dna_updates: dict, outputs_dir: Path | None = None) -> dict:
    """
    既存IPのDNAだけを部分更新する（他セクション・metadata.created_at等は
    保持し、metadata.updated_at / versionのみsave_ip()経由で更新される）。
    IPが未作成の場合はcreate_ip()相当で新規作成してから更新する。

    dna_updatesは_DNA_GROUPSのgroup名（identity/personality/visual/brand/
    rules）をキーとするdict、または"keywords"（配列）を渡す。未知のgroup
    名は無視する。

    戻り値: save_ip()と同じ形式。例外を投げない。
    """
    try:
        safe_name = _safe_ip_name(ip_name)
        if not safe_name:
            return {"ok": False, "path": None, "ip": None, "error": "IP名を入力してください"}

        ip = load_ip(safe_name, outputs_dir=outputs_dir)
        if ip is None:
            created = create_ip(safe_name, outputs_dir=outputs_dir)
            if not created.get("ok"):
                return created
            ip = created["ip"]

        dna = dict(ip.get("dna") or _empty_dna())
        for group, keys in _DNA_GROUPS.items():
            if group not in (dna_updates or {}):
                continue
            group_updates = dna_updates[group] or {}
            current = dict(dna.get(group) or {key: "" for key in keys})
            for key in keys:
                if key in group_updates:
                    current[key] = group_updates[key]
            dna[group] = current

        if "keywords" in (dna_updates or {}):
            keywords = dna_updates["keywords"]
            if isinstance(keywords, str):
                keywords = [k.strip() for k in keywords.split(",") if k.strip()]
            dna["keywords"] = [str(k).strip() for k in (keywords or []) if str(k).strip()]

        ip["dna"] = dna
        return save_ip(safe_name, ip, outputs_dir=outputs_dir)
    except Exception as e:
        print(f"[警告] DNAの更新に失敗しました（{ip_name}）：{e}")
        return {"ok": False, "path": None, "ip": None, "error": str(e)}


# ──────────────────────────────────────────
# generate_dna_from_reference()：Reference → DNA（"提案"であり自動保存しない）
# ──────────────────────────────────────────

_DNA_SYNTHESIS_PROMPT = """あなたはVega、DAF OSのCreative Director（CDO）です。
以下は複数の参考画像（Reference）から集計したメタデータ（タグ・動物・配色・
雰囲気・メモ）です。これらは個々の画像の解析結果に過ぎません。

あなたの仕事は、これらの複製ではなく、複数Referenceに共通する「本質
（IPのDNA）」を抽出することです。1枚だけに現れる特徴は無視し、複数枚に
共通する傾向を優先してください。

参考メタデータ:
{reference_summary}

必ず次のキーだけを持つJSONオブジェクトで返してください（説明文やコード
ブロック記法は不要）：
{{
  "identity": {{"name": "", "species": "", "type": ""}},
  "personality": {{"personality": "", "values": "", "target_emotion": ""}},
  "visual": {{"color_palette": "", "line_style": "", "eye_style": "", "body_style": ""}},
  "brand": {{"positioning": "", "audience": ""}},
  "rules": {{"must_have": "", "must_not": ""}},
  "keywords": []
}}
"""


def _reference_metadata_summary_text(images: list[dict]) -> str:
    lines = []
    for img in images:
        parts = []
        if img.get("animal"):
            parts.append(f"animal={img['animal']}")
        if img.get("color"):
            parts.append(f"color={img['color']}")
        if img.get("mood"):
            parts.append(f"mood={img['mood']}")
        if img.get("tags"):
            parts.append(f"tags={', '.join(img['tags'])}")
        if img.get("memo"):
            parts.append(f"memo={img['memo']}")
        if parts:
            lines.append("- " + " / ".join(parts))
    return "\n".join(lines)


def _most_common(values: list[str], top_n: int = 3) -> list[str]:
    counts: dict[str, int] = {}
    for v in values:
        v = (v or "").strip()
        if not v:
            continue
        counts[v] = counts.get(v, 0) + 1
    return [v for v, _ in sorted(counts.items(), key=lambda kv: kv[1], reverse=True)[:top_n]]


def _fallback_dna_from_images(images: list[dict]) -> dict:
    """
    OPENROUTER_API_KEY未設定時のフォールバック。複数Referenceの中で
    最も頻出するタグ・動物・雰囲気を単純集計し、DNAの"叩き台"を作る
    （AI要約ではないため、あくまで簡易集計であることをkeywords/memo相当
    フィールドに残さない＝呼び出し側のUIで案内する）。
    """
    animals = _most_common([img.get("animal", "") for img in images], top_n=1)
    colors = _most_common([c for img in images for c in re.split(r"[,、]", img.get("color") or "") if c.strip()], top_n=3)
    moods = _most_common([m for img in images for m in re.split(r"[,、]", img.get("mood") or "") if m.strip()], top_n=3)
    all_tags = [t for img in images for t in (img.get("tags") or [])]
    top_tags = _most_common(all_tags, top_n=8)

    dna = _empty_dna()
    dna["identity"]["species"] = animals[0] if animals else ""
    dna["visual"]["color_palette"] = ", ".join(colors)
    dna["personality"]["target_emotion"] = ", ".join(moods)
    dna["keywords"] = top_tags
    return dna


def generate_dna_from_reference(
    ip_name: str,
    project_id: str | None = None,
    category: str | None = None,
    outputs_dir: Path | None = None,
) -> dict:
    """
    Quest104：登録済みReference（project_idまたはcategoryで絞り込み可能、
    未指定なら全件）の共通特徴からDNAの"提案"を生成する。ip_memory.jsonへの
    保存は行わない（呼び出し側がupdate_dna()/save_ip()を呼んで初めて反映）。

    OPENROUTER_API_KEY設定時は複数Referenceのタグ・動物・配色・雰囲気・
    メモをまとめてAIに渡し、共通する本質を要約させる（画像そのものは
    渡さない＝Quest103の解析結果というテキストメタデータのみを使う）。
    未設定・AI呼び出し失敗時は、頻出タグ・動物・配色・雰囲気の単純集計
    にフォールバックする。

    戻り値: {"ok": bool, "dna": dict | None, "reference_count": int,
             "error": str | None}
    例外を投げない。
    """
    try:
        from services.reference_analysis_service import list_reference_images

        images = list_reference_images(project_id=project_id, outputs_dir=outputs_dir)
        if category:
            images = [img for img in images if img.get("category") == category]

        if not images:
            return {"ok": False, "dna": None, "reference_count": 0,
                     "error": "対象のReferenceが見つかりません（project_id/categoryの指定を確認してください）"}

        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            dna = _fallback_dna_from_images(images)
            return {"ok": True, "dna": dna, "reference_count": len(images),
                     "error": None, "source": "fallback_aggregation"}

        try:
            import litellm

            summary_text = _reference_metadata_summary_text(images)
            prompt = _DNA_SYNTHESIS_PROMPT.format(reference_summary=summary_text or "（メタデータなし）")

            response = litellm.completion(
                model="openrouter/openai/gpt-4o-mini",
                api_key=api_key,
                api_base="https://openrouter.ai/api/v1",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.4,
                timeout=60,
            )
            content = response["choices"][0]["message"]["content"]
            dna = _parse_dna_json(content)
            return {"ok": True, "dna": dna, "reference_count": len(images), "error": None, "source": "ai"}
        except Exception as e:
            print(f"[警告] DNAのAI生成に失敗しました（{ip_name}）：{e}")
            dna = _fallback_dna_from_images(images)
            return {"ok": True, "dna": dna, "reference_count": len(images),
                     "error": f"AI生成に失敗したため簡易集計を使用：{e}", "source": "fallback_aggregation"}
    except Exception as e:
        print(f"[警告] DNA生成に失敗しました（{ip_name}）：{e}")
        return {"ok": False, "dna": None, "reference_count": 0, "error": str(e)}


def _parse_dna_json(raw_text: str) -> dict:
    """AI応答テキストからDNA用JSONを抽出し、欠けたキーは空値で補う。"""
    text = (raw_text or "").strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError("AI応答からJSONを抽出できませんでした")
    data = json.loads(text[start:end + 1])

    dna = _empty_dna()
    for group, keys in _DNA_GROUPS.items():
        group_data = data.get(group) or {}
        for key in keys:
            if key in group_data:
                dna[group][key] = str(group_data.get(key) or "").strip()

    keywords = data.get("keywords")
    if not isinstance(keywords, list):
        keywords = [k.strip() for k in str(keywords or "").split(",") if k.strip()]
    dna["keywords"] = [str(k).strip() for k in keywords if str(k).strip()]
    return dna


if __name__ == "__main__":
    # Quest104: 動作確認用のCLI導線。
    #   python services/ip_memory_service.py [ip_name]
    ip_name = sys.argv[1] if len(sys.argv) > 1 else None
    if ip_name:
        result = create_ip(ip_name)
        print(f"[IP Memory] {result}")
    else:
        ips = list_ips()
        print(f"[IP Memory] 登録済みIP数: {len(ips)}件")
        for ip in ips:
            print(f"  - {ip['ip_name']}（v{ip['version']}, updated_at={ip['updated_at']}）")
