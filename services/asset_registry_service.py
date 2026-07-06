"""
DAF OS Quest89 — Asset Type Registry サービス

Execution Planner（Quest88）はAsset Typeごとの成果物・タスクをPythonコード内に
ハードコードしていた。line_sticker / youtube_short / ios_app などAsset Type
ごとに「必要な成果物」「制作手順」「レビュー項目」「公開時に必要なもの」が
異なるため、その知識をコードから切り離し、memory/asset_registry/*.json という
読み込み専用の定義書としてDAF OSに記憶させる。

Quest90（Asset Generator）はこのRegistryを参照して実際にデジタル資産を生成する
予定であり、このQuestではその基盤（定義書＋読み込み関数）を用意するところまで。

ディレクトリ構造:
  memory/asset_registry/line_sticker.json
  memory/asset_registry/youtube_short.json
  memory/asset_registry/blog.json
  memory/asset_registry/ebook.json
  memory/asset_registry/ios_app.json
  memory/asset_registry/saas.json
  memory/asset_registry/generic.json

各JSONの共通フォーマット:
  {
    "asset_type": str,
    "display_name": str,
    "deliverables": list[str],
    "tasks": list[str],
    "review_items": list[str],
    "publish_package": list[str]
  }

必要な関数：
- load_asset_registry(asset_type):     指定Asset TypeのRegistry（dict）を返す。
                                        存在しない場合はgeneric.jsonにフォールバックする
- list_asset_types():                  登録済みAsset Type名の一覧を返す
- get_asset_template(asset_type):      deliverables/tasks/review_items/
                                        publish_packageだけを抜き出したdictを返す
                                        （services/execution_planner_service.py が
                                        Quest88の既存ロジックの代わりに参照する）
- generate_asset_registry_summary():   AI会議へ注入する短いMarkdown要約を返す

CLI:
  python services/asset_registry_service.py

読み込み専用（Registry自体をこのサービスが書き換えることはない）。
ファイル未存在・JSON壊れ・ディレクトリ未存在のいずれでも例外を投げず、
安全に動作する（空のdict/リストにフォールバックする）。
"""

import json
import sys
from pathlib import Path

# `python services/asset_registry_service.py` のように直接実行された場合、
# リポジトリルートが sys.path に無く `services.*` を解決できないため追加する
# （services/execution_planner_service.py と同じ対策）。
_REPO_ROOT = str(Path(__file__).parent.parent)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

_BASE_DIR = Path(__file__).parent.parent
_MEMORY_DIR = _BASE_DIR / "memory"
_REGISTRY_DIR_NAME = "asset_registry"
_FALLBACK_ASSET_TYPE = "generic"

# Recommendationの並び順・list_asset_types()の既定順序として使う固定順序。
# Quest88（Execution Planner）の作成ファイル一覧と同じ並び。
_ASSET_TYPE_ORDER = [
    "line_sticker",
    "youtube_short",
    "blog",
    "ebook",
    "ios_app",
    "saas",
    "generic",
]

_EMPTY_TEMPLATE = {
    "deliverables": [],
    "tasks": [],
    "review_items": [],
    "publish_package": [],
}

_NO_DATA_SUMMARY = "## Asset Registry Summary\n\n現在、登録されているAsset Typeはありません。"


def _registry_dir(memory_dir: Path) -> Path:
    return memory_dir / _REGISTRY_DIR_NAME


def load_asset_registry(asset_type: str, memory_dir: Path | None = None) -> dict:
    """
    指定Asset TypeのRegistry定義（dict）を返す。該当するJSONが存在しない場合は
    generic.jsonにフォールバックする。generic.jsonも無い・JSON壊れ・
    ディレクトリ未存在のいずれの場合も例外を投げず、空のdictを返す。
    """
    try:
        base = memory_dir or _MEMORY_DIR
        registry_dir = _registry_dir(base)

        path = registry_dir / f"{asset_type}.json"
        if not path.exists():
            path = registry_dir / f"{_FALLBACK_ASSET_TYPE}.json"
        if not path.exists():
            return {}

        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[警告] Asset Registryの読み込みに失敗しました（{asset_type}）：{e}")
        return {}


def list_asset_types(memory_dir: Path | None = None) -> list[str]:
    """
    memory/asset_registry/ に登録されているAsset Type名の一覧を返す。
    _ASSET_TYPE_ORDERの並びを優先し、そこに無い（将来追加された）ファイルは
    アルファベット順で末尾に追加する。ディレクトリ未存在・読み込み失敗時は
    空リストを返す。
    """
    try:
        base = memory_dir or _MEMORY_DIR
        registry_dir = _registry_dir(base)
        if not registry_dir.exists():
            return []

        found = {p.stem for p in registry_dir.glob("*.json")}
        ordered = [t for t in _ASSET_TYPE_ORDER if t in found]
        extra = sorted(found - set(_ASSET_TYPE_ORDER))
        return ordered + extra
    except Exception as e:
        print(f"[警告] Asset Type一覧の取得に失敗しました：{e}")
        return []


def get_asset_template(asset_type: str, memory_dir: Path | None = None) -> dict:
    """
    load_asset_registry()の結果から、deliverables/tasks/review_items/
    publish_packageだけを抜き出したdictを返す。services/execution_planner_service.py
    がQuest88の既存ハードコードロジックの代わりに参照するための入口。
    Registryが取得できない場合はすべて空リストのdictを返す（例外を投げない）。
    """
    try:
        registry = load_asset_registry(asset_type, memory_dir=memory_dir)
        if not registry:
            return dict(_EMPTY_TEMPLATE)
        return {
            "deliverables": registry.get("deliverables", []),
            "tasks": registry.get("tasks", []),
            "review_items": registry.get("review_items", []),
            "publish_package": registry.get("publish_package", []),
        }
    except Exception as e:
        print(f"[警告] Asset Templateの取得に失敗しました（{asset_type}）：{e}")
        return dict(_EMPTY_TEMPLATE)


def generate_asset_registry_summary(memory_dir: Path | None = None) -> str:
    """
    登録済みのAsset Type一覧（genericを除く）をAI会議へ注入する短いMarkdown
    要約に整形する。genericはフォールバック専用であり「対応しているAsset Type」
    としては数えない。登録が無い場合は「現在、登録されているAsset Typeは
    ありません。」を返す。例外を投げない。
    """
    try:
        types = [t for t in list_asset_types(memory_dir=memory_dir) if t != _FALLBACK_ASSET_TYPE]
        if not types:
            return _NO_DATA_SUMMARY

        lines = ["## Asset Registry Summary", "", "### Supported Asset Types"]
        lines.extend(f"- {t}" for t in types)
        lines.append("")
        lines.append("### Recommendation")
        lines.append("Asset Generatorは")
        lines.append(f"{types[0]}から実装してください。")

        return "\n".join(lines).rstrip()
    except Exception as e:
        print(f"[警告] Asset Registry Summaryの生成に失敗しました：{e}")
        return _NO_DATA_SUMMARY


if __name__ == "__main__":
    # Quest89: CLI導線。Registry自体は静的定義なので生成処理はなく、内容確認用。
    #   python services/asset_registry_service.py
    print("[Asset Types]", list_asset_types())
    print()
    print(generate_asset_registry_summary())
