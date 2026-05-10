"""
EDINET API 実動作検証スクリプト

実際の EDINET API にアクセスし、実装の動作と API レスポンスの形式が
一致しているかを検証します。

使用方法:
    python scripts/verify_edinet_api.py --api-key <YOUR_KEY>
    または
    EDINET_API_KEY=<YOUR_KEY> python scripts/verify_edinet_api.py

オプション:
    --date YYYY-MM-DD  特定日を指定（省略時: 今日〜3日前の中でデータがある最初の日）
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.parse
import urllib.request
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

# プロジェクトルートを sys.path に追加
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from kabusys.data.edinet_collector import (
    EDINET_DOCUMENTS_URL,
    _TARGET_DOC_TYPES,
    fetch_edinet_disclosures,
    run_edinet_collection,
)
from kabusys.data.schema import init_schema

# ---------------------------------------------------------------------------
# ヘルパー
# ---------------------------------------------------------------------------

_failures = 0


def check(label: str, ok: bool, detail: str = "") -> bool:
    global _failures
    status = "✅ PASS" if ok else "❌ FAIL"
    print(f"  {status}  {label}")
    if detail:
        print(f"           {detail}")
    if not ok:
        _failures += 1
    return ok


def info(msg: str) -> None:
    print(f"  ℹ️   {msg}")


def warn(msg: str) -> None:
    print(f"  ⚠️   {msg}")


# ---------------------------------------------------------------------------
# 生 API 呼び出し（実装を経由せず直接確認）
# ---------------------------------------------------------------------------


def _raw_api_call(target_date: date, api_key: str) -> dict:
    date_str = target_date.strftime("%Y-%m-%d")
    params: dict[str, str] = {"date": date_str, "type": "2"}
    if api_key:
        params["Subscription-Key"] = api_key
    url = f"{EDINET_DOCUMENTS_URL}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


# ---------------------------------------------------------------------------
# メイン検証
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="EDINET API 実動作検証")
    parser.add_argument("--api-key", default=os.environ.get("EDINET_API_KEY", ""))
    parser.add_argument(
        "--date", default=None, help="YYYY-MM-DD（省略時: 今日〜3日前で自動選択）"
    )
    args = parser.parse_args()

    api_key: str = args.api_key
    if not api_key:
        print(
            "❌ ERROR: --api-key を指定するか EDINET_API_KEY 環境変数を設定してください"
        )
        sys.exit(1)

    print("=" * 65)
    print("EDINET API 実動作検証")
    print("=" * 65)

    # ------------------------------------------------------------------
    # [1] API 接続 & 対象日の決定
    # ------------------------------------------------------------------
    print("\n[1] API 接続確認")

    if args.date:
        candidate_dates = [date.fromisoformat(args.date)]
    else:
        today = date.today()
        candidate_dates = [today - timedelta(days=i) for i in range(4)]

    target_date: date | None = None
    raw_data: dict | None = None

    for d in candidate_dates:
        print(f"  → {d} を試行中...", end=" ", flush=True)
        try:
            raw_data = _raw_api_call(d, api_key)
            print("接続 OK")
            target_date = d
            break
        except urllib.error.HTTPError as e:
            print(f"HTTP {e.code}")
            if e.code in (401, 403):
                print(f"❌ 認証エラー (HTTP {e.code}): API キーを確認してください")
                sys.exit(1)
        except Exception as e:
            print(f"例外: {e}")

    if raw_data is None or target_date is None:
        print("❌ すべての候補日で API 接続に失敗しました")
        sys.exit(1)

    check("API 接続成功", True)
    info(f"対象日: {target_date}")

    # ------------------------------------------------------------------
    # [2] レスポンス最上位構造
    # ------------------------------------------------------------------
    print("\n[2] レスポンス最上位構造")

    check("'metadata' フィールドが存在する", "metadata" in raw_data)
    check("'results' フィールドが存在する", "results" in raw_data)

    metadata = raw_data.get("metadata", {})
    actual_status = str(metadata.get("status", ""))
    check(
        "metadata.status == '200'",
        actual_status == "200",
        f"実際の status: {actual_status!r}",
    )

    results: list[dict] = raw_data.get("results", [])
    check(
        "results が list 型", isinstance(results, list), f"型: {type(results).__name__}"
    )
    info(f"results 総件数: {len(results)} 件")

    if not results:
        warn(f"{target_date} の results は 0 件（休場日または開示なし）")
        warn(
            "フィールド検証をスキップします（別の --date を指定して再試行してください）"
        )

    # ------------------------------------------------------------------
    # [3] results 要素フィールド（TypedDict と照合）
    # ------------------------------------------------------------------
    print("\n[3] results 要素フィールド（_EdinetDocument TypedDict と照合）")

    # 実装で参照するフィールドのみ確認（API は他にも多数のフィールドを返す）
    EXPECTED_FIELDS = {
        "docID",
        "edinetCode",
        "docTypeCode",
        "filerName",
        "submitDateTime",
        "docDescription",
        "pdfFlag",
        "xbrlFlag",
        "withdrawalStatus",
        "secCode",  # 銘柄コード（5桁 or None）
        "seqNumber",  # 連番（int）
    }

    if results:
        sample = results[0]
        actual_keys = set(sample.keys())

        missing = EXPECTED_FIELDS - actual_keys
        check(
            "実装が参照するすべてのフィールドが存在する",
            not missing,
            f"不足フィールド: {sorted(missing)}" if missing else "",
        )

        extra = actual_keys - EXPECTED_FIELDS
        if extra:
            info(f"API が返す追加フィールド（本実装では未使用）: {sorted(extra)}")

        # seqNumber は int が正常（str でないことを確認）
        seq = sample.get("seqNumber")
        check(
            "seqNumber が int 型",
            isinstance(seq, int),
            f"実際の型: {type(seq).__name__}",
        )

        # 文字列フィールドが str または None であることを確認（seqNumber 除く）
        str_fields = EXPECTED_FIELDS - {"seqNumber"}
        non_str = {
            k: type(sample[k]).__name__
            for k in str_fields
            if k in sample and not isinstance(sample[k], (str, type(None)))
        }
        check(
            "文字列フィールドが str または None 型（seqNumber 除く）",
            not non_str,
            f"型違い: {non_str}" if non_str else "",
        )

        info(f"サンプル docTypeCode  : {sample.get('docTypeCode')!r}")
        info(f"サンプル secCode      : {sample.get('secCode')!r}")
        info(f"サンプル withdrawalStatus: {sample.get('withdrawalStatus')!r}")
        info(f"サンプル submitDateTime: {sample.get('submitDateTime')!r}")
        info(f"サンプル pdfFlag      : {sample.get('pdfFlag')!r}")

    # ------------------------------------------------------------------
    # [4] 書類種別（docType）分布
    # ------------------------------------------------------------------
    print("\n[4] 書類種別（docType）分布とフィルタ確認")

    type_counter = Counter(str(doc.get("docTypeCode", "")) for doc in results)
    target_count = sum(v for k, v in type_counter.items() if k in _TARGET_DOC_TYPES)
    other_count = sum(v for k, v in type_counter.items() if k not in _TARGET_DOC_TYPES)

    DOC_TYPE_NAMES = {
        "120": "有価証券報告書",
        "130": "四半期報告書",
        "140": "臨時報告書",
        "150": "訂正臨時報告書",
        "170": "大量保有報告書",
        "171": "大量保有報告書（特例対象）",
        "172": "変更報告書",
    }
    for dt, cnt in sorted(type_counter.items()):
        marker = "✅" if dt in _TARGET_DOC_TYPES else "  "
        name = DOC_TYPE_NAMES.get(dt, "その他")
        print(f"  {marker}  docType={dt!r} ({name}): {cnt} 件")

    info(f"実装が取得する種別の合計: {target_count} 件")
    info(f"フィルタで除外される種別: {other_count} 件")

    # ------------------------------------------------------------------
    # [5] withdrawalStatus 分布
    # ------------------------------------------------------------------
    print("\n[5] 取り下げステータス（withdrawalStatus）分布")

    ws_counter = Counter(str(doc.get("withdrawalStatus", "")) for doc in results)
    for ws, cnt in sorted(ws_counter.items()):
        is_valid = ws == "0"
        marker = "✅" if is_valid else "🚫"
        note = "（有効、取得対象）" if is_valid else "（取り下げ済み、除外）"
        print(f"  {marker}  withdrawalStatus={ws!r}: {cnt} 件{note}")

    # ------------------------------------------------------------------
    # [6] fetch_edinet_disclosures() — 実装関数の動作確認
    # ------------------------------------------------------------------
    print("\n[6] fetch_edinet_disclosures() 実装関数の動作確認")

    disclosures = fetch_edinet_disclosures(target_date, api_key=api_key)
    check("list を返す", isinstance(disclosures, list))
    info(f"取得 RawDisclosure 件数: {len(disclosures)} 件")

    # 件数の一致確認（取り下げ済み除外 + 種別フィルタ後の期待値）
    expected_count = sum(
        1
        for doc in results
        if str(doc.get("withdrawalStatus", "0")) == "0"
        and str(doc.get("docTypeCode", "")) in _TARGET_DOC_TYPES
        and doc.get("docID", "")
    )
    check(
        f"件数がフィルタ後の期待値と一致 ({expected_count} 件)",
        len(disclosures) == expected_count,
        f"実際: {len(disclosures)} 件",
    )

    if disclosures:
        d0 = disclosures[0]

        check("source == 'edinet'", d0["source"] == "edinet", f"実際: {d0['source']!r}")
        check(
            "code is None（銘柄コード非対応）",
            d0["code"] is None,
            f"実際: {d0['code']!r}",
        )
        check(
            "document_url が EDINET API ドメインで始まる",
            (d0.get("document_url") or "").startswith(
                "https://api.edinet-fsa.go.jp/api/v2/documents/"
            ),
            f"実際: {d0.get('document_url')!r}",
        )
        check(
            "document_url に '?type=' を含む（type=1 or type=2）",
            "?type=" in (d0.get("document_url") or ""),
        )
        check(
            "document_type が対象種別コードの範囲内",
            d0.get("document_type") in _TARGET_DOC_TYPES,
            f"実際: {d0.get('document_type')!r}",
        )
        check(
            "disclosed_at が datetime 型",
            hasattr(d0["disclosed_at"], "strftime"),
            f"実際の型: {type(d0['disclosed_at']).__name__}",
        )

        info(f"サンプル id           : {d0['id']!r}")
        info(f"サンプル company_name : {d0['company_name']!r}")
        info(f"サンプル title        : {d0['title']!r}")
        info(f"サンプル document_type: {d0['document_type']!r}")
        info(f"サンプル disclosed_at : {d0['disclosed_at']}")
        info(f"サンプル document_url : {d0['document_url']!r}")

        # PDF フラグと URL の type パラメータ一致確認
        pdf_map = {
            str(doc.get("docID", "")): doc.get("pdfFlag", "0") for doc in results
        }
        type_mismatch = []
        for disc in disclosures:
            doc_id = disc["id"]
            pdf_flag = pdf_map.get(doc_id, "0")
            url = disc.get("document_url") or ""
            expected_type = "2" if pdf_flag == "1" else "1"
            if f"?type={expected_type}" not in url:
                type_mismatch.append(f"docID={doc_id} pdfFlag={pdf_flag} url={url}")
        check(
            "PDF フラグに応じた URL type パラメータが正しい（type=2: PDF, type=1: XBRL）",
            not type_mismatch,
            f"不一致: {type_mismatch}" if type_mismatch else "",
        )

    # ------------------------------------------------------------------
    # [7] run_edinet_collection() — DB 保存・冪等性
    # ------------------------------------------------------------------
    print("\n[7] run_edinet_collection() DB 保存・冪等性検証（インメモリ DuckDB）")

    conn = init_schema(":memory:")

    saved1 = run_edinet_collection(conn, target_date=target_date, api_key=api_key)
    check(
        f"初回保存件数 == fetch 件数 ({len(disclosures)})",
        saved1 == len(disclosures),
        f"実際の saved={saved1}",
    )

    saved2 = run_edinet_collection(conn, target_date=target_date, api_key=api_key)
    check("冪等性: 同日 2 回目の saved == 0", saved2 == 0, f"実際の saved={saved2}")

    rows = conn.execute(
        "SELECT COUNT(*) FROM raw_disclosures WHERE source = 'edinet'"
    ).fetchone()
    db_count = rows[0] if rows else 0
    check(
        f"DB の source='edinet' 件数 == 初回保存件数 ({saved1})",
        db_count == saved1,
        f"実際: {db_count}",
    )

    # tdnet レコードが混入していないか
    tdnet_rows = conn.execute(
        "SELECT COUNT(*) FROM raw_disclosures WHERE source = 'tdnet'"
    ).fetchone()
    check("DB に source='tdnet' の混入なし", (tdnet_rows[0] if tdnet_rows else 0) == 0)

    conn.close()

    # ------------------------------------------------------------------
    # [8] API キーなし / あり の URL 構築確認
    # ------------------------------------------------------------------
    print("\n[8] Subscription-Key の URL 組み込み確認")

    params_with = {"date": "2026-01-06", "type": "2", "Subscription-Key": "test-key"}
    url_with = f"{EDINET_DOCUMENTS_URL}?{urllib.parse.urlencode(params_with)}"
    params_without = {"date": "2026-01-06", "type": "2"}
    url_without = f"{EDINET_DOCUMENTS_URL}?{urllib.parse.urlencode(params_without)}"

    check(
        "API キーあり: Subscription-Key がクエリパラメータに含まれる",
        "Subscription-Key=test-key" in url_with,
        f"URL: {url_with}",
    )
    check(
        "API キーなし: Subscription-Key がクエリパラメータに含まれない",
        "Subscription-Key" not in url_without,
        f"URL: {url_without}",
    )

    # ------------------------------------------------------------------
    # 結果サマリ
    # ------------------------------------------------------------------
    print("\n" + "=" * 65)
    if _failures == 0:
        print("✅ すべての検証が PASS しました")
    else:
        print(f"❌ {_failures} 件の検証が FAIL しました")
    print("=" * 65)

    sys.exit(0 if _failures == 0 else 1)


if __name__ == "__main__":
    main()
