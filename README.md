# KabuSys

日本株向けの自動売買プラットフォーム（ライブラリ）です。  
J-Quants / kabuステーション 等の外部APIから市場データを取得し、DuckDB に格納・加工、戦略/発注/監査/モニタリング用のスキーマを提供します。

主な設計方針：
- データの取得はレート制限・リトライ・トークン自動更新を内包
- データの取得時点（fetched_at）をUTCで記録し Look-ahead bias を防止
- DuckDB に対する操作は冪等（ON CONFLICT / CREATE IF NOT EXISTS）で安全に実行
- 監査ログは発注から約定までのフローを UUID 連鎖で完全トレース可能に保持
- データ品質チェック（欠損・スパイク・重複・日付不整合）をサポート

---

## 機能一覧

- 環境変数/設定管理（.env 自動ロードと Settings オブジェクト）
- J-Quants API クライアント
  - OHLCV（日足）取得（ページネーション対応）
  - 財務データ（四半期 BS/PL）取得
  - JPX マーケットカレンダー取得
  - レート制限（120 req/min）管理、リトライ、401 時のトークン自動リフレッシュ
  - DuckDB への保存関数（raw_prices / raw_financials / market_calendar）
- DuckDB スキーマ定義・初期化（Raw / Processed / Feature / Execution 層）
- 監査ログスキーマ（signal_events / order_requests / executions）と初期化
- データ品質チェック（欠損、スパイク、重複、日付不整合）と集約実行
- モジュール化された package 構成（data / strategy / execution / monitoring）

---

## 前提条件

- Python 3.10+
- 必要パッケージ（例）
  - duckdb
- ネットワークアクセス（J-Quants API 等）
- 環境変数または .env に API トークン等を設定

（パッケージのインストールはプロジェクトの実際の requirements.txt に従ってください）

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン／チェックアウト
2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 必要なパッケージをインストール
   - pip install duckdb
   - （プロジェクトに requirements.txt があれば）pip install -r requirements.txt
4. 環境変数を用意
   - プロジェクトルートに `.env` または `.env.local` を作成するか、OS の環境変数を設定します。
   - 自動ロードはデフォルトで有効。自動ロードを無効にしたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 環境変数（主なキー）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID

任意 / 既定値あり:
- KABUSYS_ENV — 実行環境（development / paper_trading / live）デフォルト: development
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）デフォルト: INFO
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）

注意:
- settings オブジェクトはこれらをラップして提供します（kabusys.config.settings）。
- 必須値が未設定の場合、Settings の各プロパティが ValueError を送出します。

---

## 使い方（サンプル）

ここでは主要な操作例を示します。実際はアプリケーション側でこれらを組み合わせて ETL / 戦略 / 発注ワークフローを構築します。

1) DuckDB スキーマの初期化
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

# ファイル DB を初期化（親ディレクトリが自動作成されます）
conn = init_schema(settings.duckdb_path)

# インメモリ DB の場合
# conn = init_schema(":memory:")
```

2) J-Quants から日足を取得して保存
```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes, get_id_token
from kabusys.config import settings

# 取得（内部でトークンのキャッシュ・自動リフレッシュ・レート制限・リトライを行う）
records = fetch_daily_quotes(code="7203", date_from=None, date_to=None)

# 保存（conn は init_schema で得た DuckDB 接続）
n = save_daily_quotes(conn, records)
print(f"保存件数: {n}")
```

3) 財務データ・マーケットカレンダーの取得/保存
```python
from kabusys.data.jquants_client import fetch_financial_statements, save_financial_statements, fetch_market_calendar, save_market_calendar

fin = fetch_financial_statements(code="7203")
save_financial_statements(conn, fin)

cal = fetch_market_calendar()
save_market_calendar(conn, cal)
```

4) 監査ログスキーマの初期化（既存の conn に追加）
```python
from kabusys.data.audit import init_audit_schema

init_audit_schema(conn)  # conn は init_schema で作成した接続
```

5) データ品質チェックの実行
```python
from kabusys.data.quality import run_all_checks

issues = run_all_checks(conn, target_date=None)
for issue in issues:
    print(issue.check_name, issue.table, issue.severity, issue.detail)
    for row in issue.rows:
        print("  ", row)
```

---

## 自動環境変数ロードの挙動

- パッケージ import 時点でプロジェクトルート（.git または pyproject.toml のある親ディレクトリ）を探索し、`.env` → `.env.local` の順で読み込みます。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env
  - .env.local は存在すれば `.env` の設定を上書きします（ただし OS 環境変数は保護されます）。
- 自動ロードを無効化する場合:
  - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト等で有用）。

パーシングの注意:
- export KEY=val 形式に対応
- 値にクォート／エスケープをサポート
- 行末の # はインラインコメントとして条件付きで扱う（クォート内は無視）

---

## 実装上の重要な点

- J-Quants クライアント:
  - レート制限: 120 req/min（モジュール内 RateLimiter）
  - 再試行: 最大 3 回、408/429/5xx の場合は指数バックオフ。429 の場合は Retry-After ヘッダを尊重。
  - 401 (Unauthorized) を受け取った場合は、1 回だけリフレッシュして再試行（無限再帰回避あり）。
  - ページネーション対応（pagination_key を追跡）
  - 取得時刻は fetched_at に UTC ISO8601（Z）で記録
- DuckDB スキーマ:
  - Raw / Processed / Feature / Execution 層を定義
  - ON CONFLICT DO UPDATE による冪等性
  - 各種インデックス・DDL は init_schema() で作成
- 監査ログ:
  - UTC タイムゾーンを前提（init_audit_schema は SET TimeZone='UTC' を実行）
  - order_request_id を冪等キーとして扱い二重発注を防止
- データ品質チェック:
  - 各チェックは QualityIssue オブジェクトのリストを返す（Fail-Fast ではなく問題を収集）
  - SQL ベースで効率的に判定（パラメータバインド使用）

---

## 開発・テストのヒント

- settings はプロパティで必須チェックを行います。ユニットテスト時は環境変数をモンキーパッチするか、`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を使って自動読み込みを停止してください。
- DuckDB の初期化は軽量なので、テストでは `":memory:"` を利用すると高速で副作用が少ないです。
- J-Quants 実際 API を使わないテストでは、get_id_token / _request をモックしてください。
- audit テーブルは削除しない前提です。テスト用 DB を別ファイルに分けることを推奨します。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                — 環境変数・設定管理（自動 .env ロード）
    - data/
      - __init__.py
      - jquants_client.py      — J-Quants API クライアント（取得・保存ロジック）
      - schema.py              — DuckDB スキーマ定義・初期化
      - audit.py               — 監査ログスキーマ・初期化
      - quality.py             — データ品質チェック
      - other modules...       — （将来的なデータ関連モジュール）
    - strategy/
      - __init__.py            — 戦略層（未実装／拡張ポイント）
    - execution/
      - __init__.py            — 発注・ブローカーラッパー（未実装／拡張ポイント）
    - monitoring/
      - __init__.py            — モニタリング関連（未実装／拡張ポイント）

---

この README はコードベースの現状（データ取得・スキーマ定義・監査・品質チェック）をまとめたものです。戦略や実際の発注ロジック、Slack 通知等はこの基盤に機能を追加して構築してください。質問や README に追記したい点があれば教えてください。