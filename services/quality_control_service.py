"""
DAF OS Quest106 — Quality Control Engine（Factory品質管理）

DAFはLean AI Firstを採用する：
  Python → Rule Engine → Template → AI → CEO
の優先順位で、まず一番安価で決定的な層から実装する。Quest106で実装するのは
先頭の「Python（Rule Engine）」部分のみ。AI Review（Vision API・LLM判定等）
ではなく、Pythonの決定的なルールだけで生成物（Digital Asset）の品質を
機械的にチェックする。OpenRouter等の外部AI APIは一切呼ばない。

チェック対象と主なチェック項目：
  画像    : PNG / Transparency / Size / Resolution / Aspect Ratio / File Size
  Metadata: JSON存在・必須キー（version/timestamp相当） ※既存パイプラインの
            metadata.md（Markdown）にも後方互換で対応し、その場合はWARNING
            （必須キー検証はできないが、存在自体は評価する）
  IP      : IP Memory存在（Quest104 ip_memory.json）／IP Bible存在（Quest105
            ip_bible.md）
  Reference: 登録済みReference（Quest101〜102）の有無

判定：
  各チェックに重みを割り当て、PASS=満点／WARNING=半分／FAIL=0点で
  加重平均したスコア（0〜100）を返す。"passed"はスコアが閾値（既定70点）
  以上で、かつ致命的チェック（PNGとして開けるか）がFAILしていないことで
  判定する（Metadata/IP/Referenceは現時点では参考情報であり、v1の
  line_stickerパイプライン等は未接続でも単独では不合格にしない）。

必要な関数：
- validate_image(image_path):          画像1件のチェック結果一覧を返す
- validate_metadata(metadata_path):     メタデータのチェック結果一覧を返す
- validate_ip(ip_name):                 IP Memory / IP Bibleのチェック結果一覧を返す
- validate_reference(project_id):       Referenceのチェック結果一覧を返す
- validate_asset(asset_dir, ...):       Assetフォルダ内の代表画像・メタデータを
                                         自動検出してチェックする
- generate_quality_report(asset_dir, ip_name=None, project_id=None):
                                         上記すべてを統合し、
                                         {"passed", "score", "checks"} を返す

CLI:
  python services/quality_control_service.py <asset_dir> [ip_name] [project_id]

ファイル未存在・画像破損・JSON破損のいずれでも例外を投げない
（当該チェックはFAIL/WARNINGとして結果に含める）。既存のReference
Library・IP Memoryへは一切書き込まない（read-onlyでのみ参照する）。
"""

import json
import sys
from pathlib import Path

_REPO_ROOT = str(Path(__file__).parent.parent)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

_BASE_DIR = Path(__file__).parent.parent
_OUTPUTS_DIR = _BASE_DIR / "outputs"

PASS, WARNING, FAIL = "PASS", "WARNING", "FAIL"

# 各チェックの重み（合計100）。加重平均でscoreを算出する。
_CHECK_WEIGHTS = {
    "PNG": 15,
    "Transparency": 10,
    "Size": 10,
    "Resolution": 5,
    "Aspect Ratio": 5,
    "File Size": 10,
    "Metadata": 20,
    "IP Memory": 10,
    "IP Bible": 5,
    "Reference": 10,
}
_STATUS_SCORE = {PASS: 1.0, WARNING: 0.5, FAIL: 0.0}
_PASS_SCORE_THRESHOLD = 70
# このチェックがFAILした場合のみ、スコアに関わらず不合格とする
# （画像として開けない＝そもそもAssetとして成立していないため）。
_BLOCKING_CHECKS = {"PNG"}

_MAX_DIMENSION = 4096
_MIN_ASPECT_RATIO = 0.1
_MAX_ASPECT_RATIO = 10.0
_FILE_SIZE_WARN_BYTES = 1_000_000   # 1MB（LINEスタンプ等の一般的な上限目安）
_FILE_SIZE_FAIL_BYTES = 5_000_000   # 5MB


def _check(name: str, status: str, detail: str = "") -> dict:
    return {"name": name, "status": status, "detail": detail}


def validate_image(image_path: str | Path) -> list[dict]:
    """
    1枚の画像ファイルをチェックする（PNG形式・背景透過・サイズ・解像度・
    縦横比・ファイルサイズ）。ファイル未存在・破損画像でも例外を投げず、
    該当チェックをFAILとして返す。

    戻り値: [{"name": str, "status": "PASS"|"WARNING"|"FAIL", "detail": str}, ...]
    """
    path = Path(image_path)
    checks = []

    if not path.exists() or not path.is_file():
        checks.append(_check("PNG", FAIL, "画像ファイルが見つかりません"))
        for name in ("Transparency", "Size", "Resolution", "Aspect Ratio", "File Size"):
            checks.append(_check(name, FAIL, "画像が存在しないため判定できません"))
        return checks

    if path.suffix.lower() != ".png":
        checks.append(_check("PNG", FAIL, f"拡張子がPNGではありません（{path.suffix}）"))
    else:
        try:
            from PIL import Image
            with Image.open(path) as img:
                if img.format != "PNG":
                    checks.append(_check("PNG", FAIL, f"PNG形式として開けませんでした（format={img.format}）"))
                else:
                    checks.append(_check("PNG", PASS, "PNG形式として正しく読み込めました"))
        except Exception as e:
            checks.append(_check("PNG", FAIL, f"画像を開けませんでした：{e}"))
            for name in ("Transparency", "Size", "Resolution", "Aspect Ratio", "File Size"):
                checks.append(_check(name, FAIL, "画像を開けなかったため判定できません"))
            return checks

    try:
        from PIL import Image
        with Image.open(path) as img:
            # Transparency
            if img.mode in ("RGBA", "LA"):
                alpha = img.getchannel("A")
                lo, hi = alpha.getextrema()
                if lo < 255:
                    checks.append(_check("Transparency", PASS, f"透明ピクセルを検出しました（alpha min={lo}）"))
                else:
                    checks.append(_check("Transparency", WARNING, "アルファチャンネルはありますが透明ピクセルがありません"))
            else:
                checks.append(_check("Transparency", FAIL, f"アルファチャンネルがありません（mode={img.mode}）"))

            # Size（寸法）
            w, h = img.size
            if 1 <= w <= _MAX_DIMENSION and 1 <= h <= _MAX_DIMENSION:
                checks.append(_check("Size", PASS, f"{w}x{h}px"))
            else:
                checks.append(_check("Size", FAIL, f"サイズが範囲外です（{w}x{h}px）"))

            # Resolution（DPI。Pillow Rendererは通常DPIを設定しないためWARNING扱い）
            dpi = img.info.get("dpi")
            if not dpi:
                checks.append(_check("Resolution", WARNING, "DPI情報が設定されていません"))
            elif dpi[0] >= 72:
                checks.append(_check("Resolution", PASS, f"{dpi[0]} dpi"))
            else:
                checks.append(_check("Resolution", WARNING, f"解像度が低めです（{dpi[0]} dpi）"))

            # Aspect Ratio
            ratio = w / h if h else 0
            if _MIN_ASPECT_RATIO <= ratio <= _MAX_ASPECT_RATIO:
                checks.append(_check("Aspect Ratio", PASS, f"{ratio:.2f}"))
            else:
                checks.append(_check("Aspect Ratio", FAIL, f"縦横比が極端です（{ratio:.2f}）"))
    except Exception as e:
        for name in ("Transparency", "Size", "Resolution", "Aspect Ratio"):
            checks.append(_check(name, FAIL, f"判定中にエラーが発生しました：{e}"))

    # File Size
    try:
        size_bytes = path.stat().st_size
        if size_bytes <= _FILE_SIZE_WARN_BYTES:
            checks.append(_check("File Size", PASS, f"{size_bytes:,} bytes"))
        elif size_bytes <= _FILE_SIZE_FAIL_BYTES:
            checks.append(_check("File Size", WARNING, f"ファイルサイズがやや大きめです（{size_bytes:,} bytes）"))
        else:
            checks.append(_check("File Size", FAIL, f"ファイルサイズが大きすぎます（{size_bytes:,} bytes）"))
    except Exception as e:
        checks.append(_check("File Size", FAIL, f"ファイルサイズを取得できませんでした：{e}"))

    return checks


def _find_json_value(data: dict, key_candidates: tuple[str, ...]):
    """トップレベル、または"metadata"キー配下（ip_memory.json等の形式）を探す。"""
    for key in key_candidates:
        if key in data:
            return data[key]
    nested = data.get("metadata")
    if isinstance(nested, dict):
        for key in key_candidates:
            if key in nested:
                return nested[key]
    return None


def validate_metadata(metadata_path: str | Path | None) -> list[dict]:
    """
    メタデータファイルをチェックする（JSON存在・必須キー・version・
    timestamp）。既存パイプライン（LINEスタンプ等）が使うMarkdown形式の
    metadata.mdにも後方互換で対応し、その場合は"存在するがJSONではない"
    としてWARNINGを返す（必須キー検証はできないため）。

    戻り値: [{"name": "Metadata", "status": ..., "detail": ...}]
    """
    if metadata_path is None:
        return [_check("Metadata", FAIL, "メタデータファイルが指定されていません")]

    path = Path(metadata_path)
    if not path.exists():
        return [_check("Metadata", FAIL, "メタデータファイルが見つかりません")]

    if path.suffix.lower() != ".json":
        return [_check("Metadata", WARNING,
                        f"JSON形式ではありません（{path.suffix}）。既存のMarkdownメタデータとして"
                        "存在は確認できましたが、version/timestampは検証できません")]

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        return [_check("Metadata", FAIL, f"JSONの読み込みに失敗しました：{e}")]

    if not isinstance(data, dict):
        return [_check("Metadata", FAIL, "JSONのトップレベルがオブジェクトではありません")]

    version = _find_json_value(data, ("version",))
    timestamp = _find_json_value(data, ("timestamp", "created_at", "updated_at"))

    missing = []
    if version is None:
        missing.append("version")
    if timestamp is None:
        missing.append("timestamp")

    if missing:
        return [_check("Metadata", WARNING, f"必須キーが不足しています：{', '.join(missing)}")]
    return [_check("Metadata", PASS, "JSON・必須キー（version/timestamp）ともに確認できました")]


def validate_ip(ip_name: str | None, outputs_dir: Path | None = None) -> list[dict]:
    """
    IP Memory（Quest104）・IP Bible（Quest105）の存在を確認する
    （read-onlyでの参照のみ、書き込みは一切行わない）。

    戻り値: [{"name": "IP Memory", ...}, {"name": "IP Bible", ...}]
    """
    if not ip_name:
        return [
            _check("IP Memory", WARNING, "IP名が指定されていません（このAssetはIPと未紐づけ）"),
            _check("IP Bible", WARNING, "IP名が指定されていません"),
        ]

    try:
        from services.ip_memory_service import load_ip
        from services.ip_bible_service import load_ip_bible

        ip = load_ip(ip_name, outputs_dir=outputs_dir)
        if ip is None:
            return [
                _check("IP Memory", FAIL, f"ip_memory.jsonが見つかりません（IP: {ip_name}）"),
                _check("IP Bible", WARNING, "IP Memoryが無いためIP Bibleも未確認です"),
            ]

        ip_memory_check = _check("IP Memory", PASS, f"IP Memoryを確認しました（IP: {ip_name}）")

        bible = load_ip_bible(ip_name, outputs_dir=outputs_dir)
        if bible:
            ip_bible_check = _check("IP Bible", PASS, "IP Bible（ip_bible.md）を確認しました")
        else:
            ip_bible_check = _check("IP Bible", WARNING, "IP Bibleはまだ生成・保存されていません")

        return [ip_memory_check, ip_bible_check]
    except Exception as e:
        return [
            _check("IP Memory", FAIL, f"IP Memoryの確認中にエラーが発生しました：{e}"),
            _check("IP Bible", FAIL, f"IP Bibleの確認中にエラーが発生しました：{e}"),
        ]


def validate_reference(project_id: str | None, outputs_dir: Path | None = None) -> list[dict]:
    """
    登録済みReference（Quest101〜102、`outputs/reference_library/`）の有無を
    確認する（read-onlyでの参照のみ）。

    戻り値: [{"name": "Reference", ...}]
    """
    if not project_id:
        return [_check("Reference", WARNING, "project_idが指定されていません（Referenceとの紐づけを確認できません）")]

    try:
        from services.reference_analysis_service import list_reference_images
        images = list_reference_images(project_id=project_id, outputs_dir=outputs_dir)
        if images:
            return [_check("Reference", PASS, f"登録済みReference {len(images)}件を確認しました")]
        return [_check("Reference", WARNING, f"Project {project_id} に紐づくReferenceが登録されていません")]
    except Exception as e:
        return [_check("Reference", FAIL, f"Referenceの確認中にエラーが発生しました：{e}")]


def _find_representative_image(asset_dir: Path, image_filename: str | None) -> Path | None:
    if image_filename:
        candidate = asset_dir / image_filename
        return candidate if candidate.exists() else None
    for preferred in ("main.png", "tab.png"):
        candidate = asset_dir / preferred
        if candidate.exists():
            return candidate
    pngs = sorted(asset_dir.glob("*.png"))
    return pngs[0] if pngs else None


def _find_metadata_file(asset_dir: Path, metadata_filename: str | None) -> Path | None:
    if metadata_filename:
        candidate = asset_dir / metadata_filename
        return candidate if candidate.exists() else None
    for preferred in ("metadata.json", "metadata.md"):
        candidate = asset_dir / preferred
        if candidate.exists():
            return candidate
    return None


def validate_asset(
    asset_dir: str | Path,
    image_filename: str | None = None,
    metadata_filename: str | None = None,
) -> list[dict]:
    """
    Assetフォルダ（`outputs/generated_assets/<asset_type>/` 等）内の代表画像
    （既定: main.png → tab.png → 最初に見つかったpng）とメタデータ
    （既定: metadata.json → metadata.md）を自動検出し、validate_image() /
    validate_metadata() を実行する。IP・Referenceのチェックは含まない
    （generate_quality_report()側で別途付加する）。

    戻り値: 画像チェック + メタデータチェックを結合したリスト。
    """
    asset_dir = Path(asset_dir)
    image_path = _find_representative_image(asset_dir, image_filename)
    metadata_path = _find_metadata_file(asset_dir, metadata_filename)

    checks = []
    if image_path is None:
        checks.extend(validate_image(asset_dir / (image_filename or "main.png")))
    else:
        checks.extend(validate_image(image_path))

    checks.extend(validate_metadata(metadata_path))
    return checks


def generate_quality_report(
    asset_dir: str | Path,
    ip_name: str | None = None,
    project_id: str | None = None,
    image_filename: str | None = None,
    metadata_filename: str | None = None,
    outputs_dir: Path | None = None,
) -> dict:
    """
    Quest106：Assetフォルダ・IP Memory・Referenceの全チェックを実行し、
    Quality Report（{"passed", "score", "checks"}）を組み立てる。

    Pythonの決定的なルールのみで判定する（AI・OpenRouterは一切呼ばない）。
    各チェックの重み付き加重平均でscore（0〜100）を算出し、score≧70かつ
    "PNG"チェックがFAILしていない場合にpassed=Trueとする。

    戻り値: {"passed": bool, "score": int, "checks": [{"name","status","detail"}, ...]}
    例外を投げない（想定外のエラーは1件のFAILチェックとして結果に含める）。
    """
    try:
        checks = []
        checks.extend(validate_asset(asset_dir, image_filename=image_filename, metadata_filename=metadata_filename))
        checks.extend(validate_ip(ip_name, outputs_dir=outputs_dir))
        checks.extend(validate_reference(project_id, outputs_dir=outputs_dir))

        total_weight = 0.0
        earned = 0.0
        blocking_failed = False
        for c in checks:
            weight = _CHECK_WEIGHTS.get(c["name"], 0)
            total_weight += weight
            earned += weight * _STATUS_SCORE.get(c["status"], 0.0)
            if c["name"] in _BLOCKING_CHECKS and c["status"] == FAIL:
                blocking_failed = True

        score = round((earned / total_weight) * 100) if total_weight else 0
        passed = (score >= _PASS_SCORE_THRESHOLD) and not blocking_failed

        return {"passed": passed, "score": score, "checks": checks}
    except Exception as e:
        print(f"[警告] Quality Reportの生成に失敗しました（{asset_dir}）：{e}")
        return {"passed": False, "score": 0, "checks": [_check("Quality Check", FAIL, f"実行中にエラーが発生しました：{e}")]}


if __name__ == "__main__":
    # Quest106: 動作確認用のCLI導線。
    #   python services/quality_control_service.py <asset_dir> [ip_name] [project_id]
    if len(sys.argv) < 2:
        print("使い方: python services/quality_control_service.py <asset_dir> [ip_name] [project_id]")
    else:
        asset_dir = sys.argv[1]
        ip_name = sys.argv[2] if len(sys.argv) > 2 else None
        project_id = sys.argv[3] if len(sys.argv) > 3 else None
        report = generate_quality_report(asset_dir, ip_name=ip_name, project_id=project_id)
        print(json.dumps(report, ensure_ascii=False, indent=2))
