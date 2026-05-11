"""Bootstrap runner: orchestrates J-Quants Bulk API download and ingestion."""

from __future__ import annotations

import argparse
import logging
import shutil
import sys
import urllib.error
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

import duckdb

from kabusys.data.bootstrap.bulk_client import (
    BulkApiError,
    download_file,
    get_presigned_url,
    list_files,
)
from kabusys.data.bootstrap.loaders import (
    load_calendar,
    load_financials,
    load_master,
    load_prices,
    load_topix,
)

logger = logging.getLogger(__name__)

ENDPOINTS = [
    "/equities/bars/daily",
    "/equities/master",
    "/fins/summary",
    "/markets/calendar",
    "/indices/bars/daily/topix",
]

_LOADER_MAP = {
    "/equities/bars/daily": load_prices,
    "/equities/master": load_master,
    "/fins/summary": load_financials,
    "/markets/calendar": load_calendar,
    "/indices/bars/daily/topix": load_topix,
}


@dataclass
class BootstrapResult:
    total_files: int = 0
    loaded_files: int = 0
    skipped_files: int = 0
    failed_files: int = 0
    rows_by_endpoint: dict[str, int] = field(default_factory=dict)


def _endpoint_to_dir(endpoint: str, raw_dir: Path) -> Path:
    """'/equities/bars/daily' → raw_dir/equities/bars/daily/"""
    return raw_dir / endpoint.lstrip("/")


def _safe_errmsg(exc: Exception) -> str:
    """presigned URL がログ/DBに漏れないよう URLを含む可能性のある例外を整形する。

    __cause__ チェーンを辿って urllib 例外を探し、見つかればその安全なメッセージを返す。
    - HTTPError: status + reason のみ（URL を除外）
    - URLError: reason のみ（OS レベルのエラー詳細）
    - その他: str(exc) をそのまま使用（自前コードの例外は URL を含まない）
    """
    cause: BaseException | None = exc
    while cause is not None:
        if isinstance(cause, urllib.error.HTTPError):
            return f"HTTP {cause.code} {cause.reason}"
        if isinstance(cause, urllib.error.URLError):
            return f"URLError: {cause.reason}"
        cause = cause.__cause__ or cause.__context__
    return str(exc)


def _safe_filename(file_key: str) -> str | None:
    """file_key の末尾セグメントを検証してファイル名として返す。'.'/'..' は拒否。

    S3キーは常に '/' 区切りなので PurePosixPath で正規化する。
    """
    name = PurePosixPath(file_key).name
    if not name or name in (".", ".."):
        return None
    return name


def _reset_bootstrap(conn: duckdb.DuckDBPyConnection, raw_dir: Path) -> None:
    """bootstrap_load_history をクリアし、ダウンロード済みファイルを全て削除する。"""
    conn.execute("DELETE FROM bootstrap_load_history")
    if raw_dir.exists():
        shutil.rmtree(raw_dir)
        logger.info("raw_dir 削除: %s", raw_dir)
    logger.info("bootstrap を初期化しました")


def _loaded_keys(conn: duckdb.DuckDBPyConnection) -> set[str]:
    rows = conn.execute(
        "SELECT file_key FROM bootstrap_load_history WHERE status = 'loaded'"
    ).fetchall()
    return {r[0] for r in rows}


def _record(
    conn: duckdb.DuckDBPyConnection,
    file_key: str,
    endpoint: str,
    file_name: str,
    status: str,
    row_count: int | None = None,
    error_msg: str | None = None,
) -> None:
    conn.execute(
        "INSERT INTO bootstrap_load_history "
        "(file_key, endpoint, file_name, status, row_count, error_msg, loaded_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?) "
        "ON CONFLICT (file_key) DO UPDATE SET "
        "status=EXCLUDED.status, row_count=EXCLUDED.row_count, "
        "error_msg=EXCLUDED.error_msg, loaded_at=EXCLUDED.loaded_at",
        [
            file_key,
            endpoint,
            file_name,
            status,
            row_count,
            error_msg,
            datetime.now(timezone.utc),
        ],
    )


def run_bootstrap(
    conn: duckdb.DuckDBPyConnection,
    api_key: str,
    raw_dir: Path = Path("data/bootstrap/raw"),
    dry_run: bool = False,
    endpoints: list[str] | None = None,
) -> BootstrapResult:
    """全エンドポイントを順次処理する。1ファイル失敗でも継続。"""
    target_endpoints = endpoints if endpoints is not None else ENDPOINTS
    result = BootstrapResult()
    loaded_keys = _loaded_keys(conn)

    for endpoint in target_endpoints:
        loader = _LOADER_MAP.get(endpoint)
        if loader is None:
            logger.warning("未知のエンドポイントをスキップ: %s", endpoint)
            continue
        ep_dir = _endpoint_to_dir(endpoint, raw_dir)
        rows_ep = 0

        print(f"[{endpoint}] ファイル一覧を取得中...", flush=True)
        try:
            files = list_files(endpoint, api_key)
        except BulkApiError as exc:
            logger.error("list_files 失敗 (%s): %s", endpoint, exc)
            print(f"[{endpoint}] 失敗: {exc}", flush=True)
            continue

        logger.info("%s: %d ファイル検出", endpoint, len(files))
        print(f"[{endpoint}] {len(files)} ファイル検出", flush=True)

        for idx, f in enumerate(files, 1):
            file_key = f.get("Key", "")
            if not file_key:
                logger.warning("file_key が空のエントリをスキップ: %s", f)
                continue
            file_name = _safe_filename(file_key)
            if file_name is None:
                logger.warning("不正な file_key をスキップ: %s", file_key)
                continue
            result.total_files += 1

            if file_key in loaded_keys:
                logger.debug("スキップ（ロード済み）: %s", file_key)
                result.skipped_files += 1
                continue

            if dry_run:
                continue

            dest = ep_dir / file_name
            if not dest.exists():
                print(f"  [{idx}/{len(files)}] ダウンロード: {file_name}", flush=True)
                try:
                    presigned = get_presigned_url(file_key, api_key)
                    download_file(presigned, dest)
                except Exception as exc:
                    logger.error("ダウンロード失敗 (%s): %s", file_key, exc)
                    _record(
                        conn,
                        file_key,
                        endpoint,
                        file_name,
                        "failed",
                        error_msg=_safe_errmsg(exc),
                    )
                    result.failed_files += 1
                    continue

            print(f"  [{idx}/{len(files)}] ロード中: {file_name}", flush=True)
            try:
                n = loader(conn, dest)
                rows_ep += n
                _record(conn, file_key, endpoint, file_name, "loaded", row_count=n)
                result.loaded_files += 1
                logger.info("ロード完了 (%s): %d 件", file_name, n)
                print(f"  [{idx}/{len(files)}] 完了: {file_name} ({n:,} 件)", flush=True)
            except Exception as exc:
                logger.error("ロード失敗 (%s): %s", file_key, exc)
                _record(
                    conn,
                    file_key,
                    endpoint,
                    file_name,
                    "failed",
                    error_msg=_safe_errmsg(exc),
                )
                result.failed_files += 1

        result.rows_by_endpoint[endpoint] = rows_ep

    return result


def _print_summary(result: BootstrapResult, endpoints: list[str]) -> None:
    print("\nBootstrap 完了サマリー")
    for ep in endpoints:
        rows = result.rows_by_endpoint.get(ep, 0)
        print(f"  {ep:<40}: {rows:>10,} 件")
    print(f"  ロード済み: {result.loaded_files} ファイル")
    print(f"  スキップ  : {result.skipped_files} ファイル")
    print(f"  失敗      : {result.failed_files} ファイル")


def main(argv: list[str] | None = None) -> int:
    import logging as _logging

    from kabusys.config import Settings
    from kabusys.data.schema import init_schema

    parser = argparse.ArgumentParser(
        description="J-Quants Bootstrap: 初回一括データ投入"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="ダウンロードせず件数確認のみ"
    )
    parser.add_argument("--endpoint", metavar="EP", help="特定エンドポイントのみ処理")
    parser.add_argument(
        "--raw-dir", default="data/bootstrap/raw", help="ローカルキャッシュディレクトリ"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="DEBUG レベルのログを出力"
    )
    parser.add_argument(
        "--fresh",
        action="store_true",
        help="履歴とキャッシュを削除して最初から実行（初期化モード）",
    )
    parser.add_argument(
        "--yes", "-y", action="store_true", help="--fresh の確認プロンプトをスキップ"
    )
    args = parser.parse_args(argv)

    _logging.basicConfig(
        level=_logging.DEBUG if args.verbose else _logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    settings = Settings()
    api_key = settings.jquants_bulk_api_key
    raw_dir = Path(args.raw_dir)
    endpoints = [args.endpoint] if args.endpoint else ENDPOINTS

    conn = init_schema(settings.duckdb_path)
    try:
        if args.fresh:
            if not args.yes:
                print(
                    f"警告: bootstrap_load_history を全削除し {raw_dir} 以下のファイルを全て削除します。",
                    flush=True,
                )
                answer = input("続行しますか？ [y/N]: ")
                if answer.strip().lower() != "y":
                    print("キャンセルしました。")
                    return 0
            _reset_bootstrap(conn, raw_dir)
            print("初期化完了。最初から実行します。\n", flush=True)
        else:
            print("続きから実行します（ロード済みファイルはスキップ）。\n", flush=True)

        result = run_bootstrap(
            conn=conn,
            api_key=api_key,
            raw_dir=raw_dir,
            dry_run=args.dry_run,
            endpoints=endpoints,
        )
        _print_summary(result, endpoints)
        return 1 if result.failed_files else 0
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
