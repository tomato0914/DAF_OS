"""
DAF OS — データ暗号化ユーティリティ（GitHub Issue #75: データ暗号化技術の実装）

DAF OSやその配下のプロダクトがローカルに保存する機密性の高いデータを、
AES暗号化（Fernet: AES-128-CBC + HMAC-SHA256 による認証付き暗号化）で
保護するための共通モジュール。

使い方：

    from services.encryption_service import encrypt_text, decrypt_text

    ciphertext = encrypt_text("秘密のデータ")
    plaintext = decrypt_text(ciphertext)

鍵は `.env` の `DAF_ENCRYPTION_KEY` から読み込む。未設定の場合は
`generate_key()` で新しい鍵を生成し、`.env` に追記して使う。

安全設計（アクセス制御）：
- 暗号鍵はコードにハードコードせず、環境変数からのみ読み込む
- 鍵の値をログ・例外メッセージ・標準出力に一切表示しない
- 暗号化したファイルは書き込み時に 0o600（所有者のみ読み書き可）に制限する
- 外部APIを呼ばない
"""

import os
import stat
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken


class EncryptionKeyError(Exception):
    """暗号鍵が未設定・不正、または復号に失敗した場合に送出する。"""


def generate_key() -> str:
    """
    新しい暗号鍵を生成する（初回セットアップ用）。
    生成した値は `.env` に `DAF_ENCRYPTION_KEY=<値>` として保存すること。
    """
    return Fernet.generate_key().decode("utf-8")


def is_configured() -> bool:
    """DAF_ENCRYPTION_KEY が設定されているかどうかのみを返す（鍵の値自体は返さない）。"""
    return bool(os.getenv("DAF_ENCRYPTION_KEY"))


def _load_key(key: str | None = None) -> bytes:
    """
    暗号鍵を取得する。明示的に渡されなければ環境変数 DAF_ENCRYPTION_KEY から読む。
    鍵が見つからない・不正な場合は例外を送出するが、鍵の値自体はメッセージに含めない。
    """
    raw_key = key if key is not None else os.getenv("DAF_ENCRYPTION_KEY")
    if not raw_key:
        raise EncryptionKeyError(
            "DAF_ENCRYPTION_KEY が設定されていません。"
            "generate_key() で鍵を生成し、.env に DAF_ENCRYPTION_KEY=<値> を追加してください。"
        )
    try:
        return raw_key.encode("utf-8")
    except Exception as e:
        raise EncryptionKeyError("DAF_ENCRYPTION_KEY の形式が不正です。") from e


def encrypt_text(plaintext: str, key: str | None = None) -> str:
    """平文をAES暗号化し、テキストとして保存可能な文字列を返す。"""
    fernet = Fernet(_load_key(key))
    return fernet.encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_text(ciphertext: str, key: str | None = None) -> str:
    """
    暗号化された文字列を復号する。
    鍵が誤っている・データが改ざんされている場合は EncryptionKeyError を送出する。
    """
    fernet = Fernet(_load_key(key))
    try:
        return fernet.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
    except InvalidToken as e:
        raise EncryptionKeyError(
            "復号に失敗しました。暗号鍵が誤っているか、データが破損・改ざんされている可能性があります。"
        ) from e


def _restrict_permissions(path: Path) -> None:
    """アクセス制御：ファイルを所有者のみ読み書き可能（0o600）に設定する。"""
    os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)


def encrypt_file(source_path: Path, dest_path: Path | None = None, key: str | None = None) -> Path:
    """
    ファイルの内容を暗号化して保存する。
    保存先ファイルはアクセス制御として 0o600（所有者のみ読み書き可）に設定する。
    """
    dest = dest_path or source_path.with_suffix(source_path.suffix + ".enc")
    plaintext = source_path.read_text(encoding="utf-8")
    ciphertext = encrypt_text(plaintext, key)
    dest.write_text(ciphertext, encoding="utf-8")
    _restrict_permissions(dest)
    return dest


def decrypt_file(source_path: Path, dest_path: Path | None = None, key: str | None = None) -> Path:
    """暗号化されたファイルを復号して保存する。復号後のファイルも 0o600 に制限する。"""
    dest = dest_path or (
        source_path.with_suffix("") if source_path.suffix == ".enc" else source_path.with_suffix(".dec")
    )
    ciphertext = source_path.read_text(encoding="utf-8")
    plaintext = decrypt_text(ciphertext, key)
    dest.write_text(plaintext, encoding="utf-8")
    _restrict_permissions(dest)
    return dest
