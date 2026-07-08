"""
DAF OS Quest111 — Export Engine

Production Pipeline（`Prompt → Image Generation → AI Review → CEO確認`）で
CEOが確認した生成画像を、プラットフォーム提出用パッケージへまとめる。
本Questでは実際の申請（LINE Creators Marketへのアップロード等）は行わない
（パッケージ・ZIP・レポートを作るところまで）。

パイプライン：
  生成画像取得（services/image_generation_pipeline.py） → 画像構成チェック
  （Export Adapter） → 提出構成生成（Export Adapter） → ZIP作成 →
  Export Report作成

設計方針（将来の複数プラットフォーム対応）：
  Export Engine自体にはLINE専用ロジックを書かない。プラットフォームごとの
  必須ファイル・命名規則・検証ルールは"Export Adapter"（本ファイルの
  `LineExportAdapter`）に閉じ込め、将来
  `LINE → Discord → Telegram → WhatsApp`
  等へ拡張する場合も`_EXPORT_ADAPTERS`にAdapterを追加するだけで済む設計に
  している。Export Engine本体（`export_project()`等）はAdapterの
  インターフェース（`validate()` / `build_package()`）だけを呼ぶ。

保存先：
  outputs/exports/<project_id>/
    package/
      stickers/            （生成済みスタンプ画像をコピー）
      main.png
      tab.png
      metadata.json
    line_stickers.zip      （packageの中身をまとめたZIP。platformごとに
                             "<platform>_stickers.zip"）
    export_report.json

必要な関数：
- get_source_images(project_id):        Quest109の生成画像一覧を取得する
- check_export_readiness(project_id):   Export Adapterで画像構成チェックを
                                         行い、READY判定を返す（保存しない）
- build_export_package(project_id):     提出用package/（stickers/・
                                         main.png・tab.png・metadata.json）
                                         を作成する
- create_export_zip(project_id):        package/をZIP化する
- generate_export_report(project_id):   export_report.jsonを保存する
- export_project(project_id):           上記すべてを1回で行うエントリポイント
- load_export_report(project_id):       保存済みexport_report.jsonを読み込む

CLI:
  python services/export_engine.py <project_id> [platform]

生成画像未存在・画像構成不足・書き込み失敗のいずれでも例外を投げない
（READY=falseやerrors/warningsとして結果に含める）。既存のImage Generation
Pipeline（Quest109）・AI Review Engine（Quest110）には読み取り専用でのみ
アクセスし、変更を加えない。
"""

import json
import shutil
import sys
import zipfile
from datetime import datetime
from pathlib import Path

_REPO_ROOT = str(Path(__file__).parent.parent)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

_BASE_DIR = Path(__file__).parent.parent
_OUTPUTS_DIR = _BASE_DIR / "outputs"
_EXPORTS_DIR_NAME = "exports"

DEFAULT_PLATFORM = "line"
DEFAULT_ASSET_TYPE = "line_sticker"


# ──────────────────────────────────────────
# Export Adapter（プラットフォームごとの提出構成・検証ルール）
# ──────────────────────────────────────────

class BaseExportAdapter:
    """
    Export Adapterの共通インターフェース。Export Engine本体はこの
    インターフェースだけを呼び、プラットフォーム固有の判断（必須ファイル・
    サイズ・枚数上限等）はAdapter側に閉じ込める。
    """
    platform = "generic"
    zip_filename = "export.zip"

    def validate(self, image_dir: Path, image_files: list[str]) -> dict:
        """戻り値: {"errors": list[str], "warnings": list[str]}"""
        raise NotImplementedError

    def build_package(self, image_dir: Path, package_dir: Path, image_files: list[str]) -> dict:
        """
        package_dir配下に提出用ファイル一式を作成する。
        戻り値: {"image_count": int, "main_image": str | None, "tab_image": str | None}
        """
        raise NotImplementedError


class LineExportAdapter(BaseExportAdapter):
    """
    LINE Creators Market向けのExport Adapter（LINE固有ロジックはすべて
    このクラス内に閉じ込める）。
    """
    platform = "line"
    zip_filename = "line_stickers.zip"

    # LINE Creators Marketの一般的な要件（参考値。v1では最低限のチェックのみ）。
    MIN_STICKERS = 8
    MAX_STICKERS = 40
    MAIN_SIZE = (240, 240)
    TAB_SIZE = (96, 74)

    def validate(self, image_dir: Path, image_files: list[str]) -> dict:
        errors: list[str] = []
        warnings: list[str] = []

        if not image_files:
            errors.append("画像が存在しません（先に「⑤ 画像生成」を実行してください）")
            return {"errors": errors, "warnings": warnings}

        try:
            from PIL import Image
        except Exception as e:
            errors.append(f"Pillowが利用できません：{e}")
            return {"errors": errors, "warnings": warnings}

        sizes = set()
        for filename in image_files:
            path = image_dir / filename
            if not path.exists():
                errors.append(f"画像ファイルが見つかりません：{filename}")
                continue
            try:
                with Image.open(path) as img:
                    if img.format != "PNG":
                        errors.append(f"PNG形式ではありません：{filename}（format={img.format}）")
                        continue
                    sizes.add(img.size)
            except Exception as e:
                errors.append(f"画像を開けませんでした（{filename}）：{e}")

        if len(sizes) > 1:
            warnings.append(f"スタンプ画像のサイズが揃っていません（{sorted(sizes)}）")

        count = len(image_files)
        if count < self.MIN_STICKERS:
            warnings.append(
                f"画像枚数が{count}枚です（LINE Creators Marketの目安は{self.MIN_STICKERS}〜"
                f"{self.MAX_STICKERS}枚。Quest109時点は最大{3}枚生成のため今後拡張予定）"
            )
        elif count > self.MAX_STICKERS:
            errors.append(f"画像枚数が上限（{self.MAX_STICKERS}枚）を超えています（{count}枚）")

        # main.png / tab.pngは無ければbuild_package()側で自動生成するため、
        # ここではエラーにはせず、生成前の状態として警告に留める。
        if not (image_dir / "main.png").exists():
            warnings.append("main.pngが未生成です（Export時に自動生成します）")
        if not (image_dir / "tab.png").exists():
            warnings.append("tab.pngが未生成です（Export時に自動生成します）")

        return {"errors": errors, "warnings": warnings}

    def build_package(self, image_dir: Path, package_dir: Path, image_files: list[str]) -> dict:
        stickers_dir = package_dir / "stickers"
        stickers_dir.mkdir(parents=True, exist_ok=True)

        for filename in image_files:
            src = image_dir / filename
            if src.exists():
                shutil.copy2(src, stickers_dir / filename)

        main_path = image_dir / "main.png"
        tab_path = image_dir / "tab.png"

        # 既存のmain.png/tab.pngがあればそれを使い、無ければQuest98の
        # Image Generation Service（既存実装、変更なし）でその場生成する。
        try:
            if main_path.exists():
                shutil.copy2(main_path, package_dir / "main.png")
            else:
                from services.image_generation_service import render_icon_image
                render_icon_image(self.MAIN_SIZE).save(package_dir / "main.png")
        except Exception as e:
            print(f"[警告] main.pngの用意に失敗しました：{e}")

        try:
            if tab_path.exists():
                shutil.copy2(tab_path, package_dir / "tab.png")
            else:
                from services.image_generation_service import render_icon_image
                render_icon_image(self.TAB_SIZE).save(package_dir / "tab.png")
        except Exception as e:
            print(f"[警告] tab.pngの用意に失敗しました：{e}")

        return {
            "image_count": len(image_files),
            "main_image": "main.png" if (package_dir / "main.png").exists() else None,
            "tab_image": "tab.png" if (package_dir / "tab.png").exists() else None,
        }


# 将来 "discord" / "telegram" / "whatsapp" 等をここへ追加するだけで
# 拡張できる（Export Engine本体の変更は不要）。
_EXPORT_ADAPTERS: dict[str, BaseExportAdapter] = {
    "line": LineExportAdapter(),
}


def _get_adapter(platform: str) -> BaseExportAdapter:
    return _EXPORT_ADAPTERS.get(platform, _EXPORT_ADAPTERS[DEFAULT_PLATFORM])


def _exports_dir(project_id: str, outputs_dir: Path | None = None) -> Path:
    return (outputs_dir or _OUTPUTS_DIR) / _EXPORTS_DIR_NAME / project_id


def get_source_images(
    project_id: str,
    asset_type: str = DEFAULT_ASSET_TYPE,
    outputs_dir: Path | None = None,
) -> dict:
    """Quest109の生成画像一覧を取得する（読み取り専用、image_generation_pipeline.pyへ委譲）。"""
    try:
        from services.image_generation_pipeline import list_generated_images
        return list_generated_images(project_id, asset_type=asset_type, outputs_dir=outputs_dir)
    except Exception as e:
        print(f"[警告] 生成済み画像一覧の取得に失敗しました（{project_id}）：{e}")
        return {"exists": False, "project_id": project_id, "asset_type": asset_type,
                 "image_files": [], "metadata": None}


def check_export_readiness(
    project_id: str,
    asset_type: str = DEFAULT_ASSET_TYPE,
    platform: str = DEFAULT_PLATFORM,
    outputs_dir: Path | None = None,
) -> dict:
    """
    Export前チェック（画像存在・PNG形式・サイズ一致・画像枚数・main/tab.png
    存在）をAdapter経由で行い、READY判定を返す（保存はしない）。

    戻り値: {"ready": bool, "errors": list[str], "warnings": list[str],
             "image_count": int}
    例外を投げない。
    """
    try:
        adapter = _get_adapter(platform)
        images_info = get_source_images(project_id, asset_type=asset_type, outputs_dir=outputs_dir)
        image_dir = (outputs_dir or _OUTPUTS_DIR) / "generated_assets" / asset_type / project_id
        image_files = images_info.get("image_files") or []

        validation = adapter.validate(image_dir, image_files)
        errors = validation.get("errors") or []
        warnings = validation.get("warnings") or []

        return {"ready": len(errors) == 0, "errors": errors, "warnings": warnings, "image_count": len(image_files)}
    except Exception as e:
        print(f"[警告] Export前チェックに失敗しました（{project_id}）：{e}")
        return {"ready": False, "errors": [str(e)], "warnings": [], "image_count": 0}


def build_export_package(
    project_id: str,
    asset_type: str = DEFAULT_ASSET_TYPE,
    platform: str = DEFAULT_PLATFORM,
    outputs_dir: Path | None = None,
) -> dict:
    """
    outputs/exports/<project_id>/package/ に提出用ファイル一式
    （stickers/・main.png・tab.png・metadata.json）を作成する。

    戻り値: {"ok": bool, "package_dir": str | None, "metadata": dict | None, "error": str | None}
    例外を投げない。
    """
    try:
        adapter = _get_adapter(platform)
        images_info = get_source_images(project_id, asset_type=asset_type, outputs_dir=outputs_dir)
        image_files = images_info.get("image_files") or []
        if not image_files:
            return {"ok": False, "package_dir": None, "metadata": None,
                     "error": "生成済み画像が見つかりません（先に「⑤ 画像生成」を実行してください）"}

        image_dir = (outputs_dir or _OUTPUTS_DIR) / "generated_assets" / asset_type / project_id
        export_dir = _exports_dir(project_id, outputs_dir)
        package_dir = export_dir / "package"
        package_dir.mkdir(parents=True, exist_ok=True)

        build_result = adapter.build_package(image_dir, package_dir, image_files)

        validation = adapter.validate(image_dir, image_files)
        status = "ready" if not validation.get("errors") else "not_ready"

        metadata = {
            "project_id": project_id,
            "asset_type": asset_type,
            "image_count": build_result.get("image_count", len(image_files)),
            "main_image": build_result.get("main_image"),
            "tab_image": build_result.get("tab_image"),
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "status": status,
        }
        (package_dir / "metadata.json").write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
        )

        return {"ok": True, "package_dir": str(package_dir), "metadata": metadata, "error": None}
    except Exception as e:
        print(f"[警告] Export Packageの作成に失敗しました（{project_id}）：{e}")
        return {"ok": False, "package_dir": None, "metadata": None, "error": str(e)}


def create_export_zip(
    project_id: str,
    platform: str = DEFAULT_PLATFORM,
    outputs_dir: Path | None = None,
) -> dict:
    """
    package/ の中身をZIP化する（build_export_package()を先に呼んでおく
    必要がある）。

    戻り値: {"ok": bool, "zip_path": str | None, "zip_filename": str | None, "error": str | None}
    例外を投げない。
    """
    try:
        adapter = _get_adapter(platform)
        export_dir = _exports_dir(project_id, outputs_dir)
        package_dir = export_dir / "package"
        if not package_dir.exists():
            return {"ok": False, "zip_path": None, "zip_filename": None,
                     "error": "packageが未作成です（先にbuild_export_package()を実行してください）"}

        zip_path = export_dir / adapter.zip_filename
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for path in sorted(package_dir.rglob("*")):
                if path.is_file():
                    zf.write(path, arcname=str(path.relative_to(package_dir)))

        return {"ok": True, "zip_path": str(zip_path), "zip_filename": adapter.zip_filename, "error": None}
    except Exception as e:
        print(f"[警告] ZIPの作成に失敗しました（{project_id}）：{e}")
        return {"ok": False, "zip_path": None, "zip_filename": None, "error": str(e)}


def generate_export_report(
    project_id: str,
    readiness: dict,
    zip_filename: str | None,
    outputs_dir: Path | None = None,
) -> dict:
    """
    export_report.jsonを保存する。

    戻り値: {"ok": bool, "path": str | None, "report": dict | None, "error": str | None}
    例外を投げない。
    """
    try:
        export_dir = _exports_dir(project_id, outputs_dir)
        export_dir.mkdir(parents=True, exist_ok=True)

        report = {
            "ready": bool(readiness.get("ready")),
            "warnings": readiness.get("warnings") or [],
            "errors": readiness.get("errors") or [],
            "exported_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "zip_file": zip_filename,
        }
        path = export_dir / "export_report.json"
        path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return {"ok": True, "path": str(path), "report": report, "error": None}
    except Exception as e:
        print(f"[警告] export_report.jsonの保存に失敗しました（{project_id}）：{e}")
        return {"ok": False, "path": None, "report": None, "error": str(e)}


def export_project(
    project_id: str,
    asset_type: str = DEFAULT_ASSET_TYPE,
    platform: str = DEFAULT_PLATFORM,
    outputs_dir: Path | None = None,
) -> dict:
    """
    Quest111：生成画像取得 → 画像構成チェック → 提出構成生成 → ZIP作成 →
    Export Report作成、までを1回で行うエントリポイント
    （Dashboardの「⑦ Export」ボタンから呼ばれる）。

    生成画像が1件も無い場合はready=falseのレポートのみ返す（package/ZIPは
    作らない）。それ以外はerrors/warningsがあってもpackage・ZIP・レポート
    まで作成する（READYの可否をCEOが判断できるようにするため）。

    戻り値: {"ok": bool, "report": dict | None, "zip_path": str | None,
             "zip_filename": str | None, "package_dir": str | None, "error": str | None}
    例外を投げない。
    """
    try:
        readiness = check_export_readiness(project_id, asset_type=asset_type, platform=platform, outputs_dir=outputs_dir)

        if readiness.get("image_count", 0) == 0:
            report_result = generate_export_report(project_id, readiness, None, outputs_dir=outputs_dir)
            return {"ok": False, "report": report_result.get("report"), "zip_path": None,
                     "zip_filename": None, "package_dir": None,
                     "error": "生成済み画像が見つかりません（先に「⑤ 画像生成」を実行してください）"}

        package_result = build_export_package(project_id, asset_type=asset_type, platform=platform, outputs_dir=outputs_dir)
        if not package_result.get("ok"):
            report_result = generate_export_report(project_id, readiness, None, outputs_dir=outputs_dir)
            return {"ok": False, "report": report_result.get("report"), "zip_path": None,
                     "zip_filename": None, "package_dir": None, "error": package_result.get("error")}

        zip_result = create_export_zip(project_id, platform=platform, outputs_dir=outputs_dir)
        report_result = generate_export_report(
            project_id, readiness, zip_result.get("zip_filename"), outputs_dir=outputs_dir,
        )

        return {
            "ok": True, "report": report_result.get("report"),
            "zip_path": zip_result.get("zip_path"), "zip_filename": zip_result.get("zip_filename"),
            "package_dir": package_result.get("package_dir"), "error": None,
        }
    except Exception as e:
        print(f"[警告] Exportの実行に失敗しました（{project_id}）：{e}")
        return {"ok": False, "report": None, "zip_path": None, "zip_filename": None,
                 "package_dir": None, "error": str(e)}


def load_export_report(project_id: str, outputs_dir: Path | None = None) -> dict | None:
    """保存済みexport_report.jsonを読み込む。未存在・破損時はNoneを返す（例外を投げない）。"""
    try:
        path = _exports_dir(project_id, outputs_dir) / "export_report.json"
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[警告] export_report.jsonの読み込みに失敗しました（{project_id}）：{e}")
        return None


if __name__ == "__main__":
    # Quest111: 動作確認用のCLI導線。
    #   python services/export_engine.py <project_id> [platform]
    if len(sys.argv) > 1:
        project_id = sys.argv[1]
        platform = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_PLATFORM
        result = export_project(project_id, platform=platform)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("使い方: python services/export_engine.py <project_id> [platform]")
