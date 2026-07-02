"""
DAF OS — 暗号化機能のセキュリティテスト（GitHub Issue #75 完了条件対応）

services/encryption_service.py の暗号化・復号・アクセス制御が正しく機能しているかを検証し、
結果を outputs/security_test_encryption.md に報告する。

実行方法:
    python scripts/security_check_encryption.py

安全設計：
- 外部APIを呼ばない
- テスト専用の使い捨て鍵のみを使用し、.env の実鍵は読み書きしない
- 鍵の値は結果レポートに一切出力しない
"""

import stat
import sys
import tempfile
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.encryption_service import (  # noqa: E402
    EncryptionKeyError,
    decrypt_file,
    decrypt_text,
    encrypt_file,
    encrypt_text,
    generate_key,
)


def _run_checks() -> list[dict]:
    results = []
    test_key = generate_key()
    other_key = generate_key()
    sample = "これは機密性の高いテストデータです。 / Sensitive test data 123!"

    # 1. ラウンドトリップ（暗号化→復号で元のデータに戻るか）
    try:
        ciphertext = encrypt_text(sample, key=test_key)
        decrypted = decrypt_text(ciphertext, key=test_key)
        ok = decrypted == sample
        results.append({
            "name": "ラウンドトリップ（暗号化→復号）",
            "passed": ok,
            "detail": "復号結果が元データと一致" if ok else "復号結果が元データと不一致",
        })
    except Exception as e:
        results.append({"name": "ラウンドトリップ（暗号化→復号）", "passed": False, "detail": str(e)})
        ciphertext = ""

    # 2. 平文がそのまま保存されていないか（暗号化されているか）
    try:
        ok = bool(ciphertext) and sample not in ciphertext
        results.append({
            "name": "平文の非露出（ciphertextに元データが含まれない）",
            "passed": ok,
            "detail": "暗号文に平文が含まれていない" if ok else "暗号文に平文が含まれている（重大な不具合）",
        })
    except Exception as e:
        results.append({"name": "平文の非露出", "passed": False, "detail": str(e)})

    # 3. 誤った鍵では復号できないこと（改ざん・鍵不一致耐性）
    try:
        try:
            decrypt_text(ciphertext, key=other_key)
            results.append({
                "name": "誤った鍵での復号拒否",
                "passed": False,
                "detail": "誤った鍵で復号できてしまった（重大な不具合）",
            })
        except EncryptionKeyError:
            results.append({
                "name": "誤った鍵での復号拒否",
                "passed": True,
                "detail": "想定どおり EncryptionKeyError が発生し復号を拒否した",
            })
    except Exception as e:
        results.append({"name": "誤った鍵での復号拒否", "passed": False, "detail": str(e)})

    # 4. 鍵未設定時に例外メッセージへ鍵の値が含まれないこと
    try:
        try:
            decrypt_text(ciphertext, key="")
            results.append({"name": "鍵未設定時のエラーハンドリング", "passed": False, "detail": "例外が発生しなかった"})
        except EncryptionKeyError as e:
            leaked = test_key in str(e) or other_key in str(e)
            results.append({
                "name": "鍵未設定時のエラーハンドリング（鍵の非露出）",
                "passed": not leaked,
                "detail": "エラーメッセージに鍵は含まれていない" if not leaked else "エラーメッセージに鍵が漏洩している（重大な不具合）",
            })
    except Exception as e:
        results.append({"name": "鍵未設定時のエラーハンドリング", "passed": False, "detail": str(e)})

    # 5. ファイル暗号化・復号のラウンドトリップ + アクセス制御（0o600）
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            src = tmp / "sample.txt"
            src.write_text(sample, encoding="utf-8")

            enc_path = encrypt_file(src, key=test_key)
            mode = stat.S_IMODE(enc_path.stat().st_mode)
            perm_ok = mode == 0o600

            dec_path = decrypt_file(enc_path, key=test_key)
            content_ok = dec_path.read_text(encoding="utf-8") == sample

            results.append({
                "name": "ファイル暗号化のアクセス制御（0o600）",
                "passed": perm_ok,
                "detail": f"権限: {oct(mode)}" + ("（正しく制限されている）" if perm_ok else "（想定と異なる）"),
            })
            results.append({
                "name": "ファイル暗号化のラウンドトリップ",
                "passed": content_ok,
                "detail": "復号後のファイル内容が元データと一致" if content_ok else "復号後の内容が一致しない",
            })
    except Exception as e:
        results.append({"name": "ファイル暗号化のアクセス制御・ラウンドトリップ", "passed": False, "detail": str(e)})

    return results


def _build_report(results: list[dict]) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    passed = sum(1 for r in results if r["passed"])
    total = len(results)

    lines = [
        "# セキュリティテスト結果 — データ暗号化（GitHub Issue #75）",
        "",
        f"> 実行日時: {now}",
        f"> 結果: {passed}/{total} 件成功",
        "",
        "対象: `services/encryption_service.py`（AES暗号化・アクセス制御）",
        "",
        "---",
        "",
        "| # | チェック項目 | 結果 | 詳細 |",
        "|---|-------------|------|------|",
    ]
    for i, r in enumerate(results, start=1):
        mark = "✅ 成功" if r["passed"] else "❌ 失敗"
        lines.append(f"| {i} | {r['name']} | {mark} | {r['detail']} |")

    lines += [
        "",
        "---",
        "",
        "## まとめ",
        "",
        f"- 実施したチェック: {total}件",
        f"- 成功: {passed}件",
        f"- 失敗: {total - passed}件",
        "",
        "> このテストは使い捨ての一時鍵のみを使用しており、`.env` の実際の鍵は読み書きしていません。",
    ]
    return "\n".join(lines)


def main() -> int:
    print("[セキュリティテスト] services/encryption_service.py を検証中...")
    results = _run_checks()
    report = _build_report(results)

    outputs_dir = Path(__file__).parent.parent / "outputs"
    outputs_dir.mkdir(exist_ok=True)
    report_path = outputs_dir / "security_test_encryption.md"
    report_path.write_text(report, encoding="utf-8")

    passed = sum(1 for r in results if r["passed"])
    total = len(results)
    print(f"[セキュリティテスト] {passed}/{total} 件成功 → {report_path}")

    for r in results:
        mark = "✅" if r["passed"] else "❌"
        print(f"  {mark} {r['name']}: {r['detail']}")

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
