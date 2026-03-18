# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
J-Quants API から市場データを取得して DuckDB に格納し、ニュース収集・品質チェック・ETL パイプライン・監査ログなどを提供します。

## 特徴（概要）
- J-Quants API クライアント
  - 株価日足（OHLCV）、四半期財務データ、JPX マーケットカレンダーを取得
  - レート制限（120 req/min）や指数バックオフリトライ、401 時の自動トークンリフレッシュ対応
  - 取得時刻（fetched_at）を UTC で記録し Look-ahead bias を防止
  - DuckDB への保存は冪等（ON CONFLICT）で保証
- ニュース収集（RSS）
  - RSS から記事を収集し前処理（URL除去・空白正規化）して DuckDB に保存
  - SSRF, XML Bomb 対策（defusedxml、リダイレクト検査、応答サイズ制限）
  - 記事 ID は正規化 URL の SHA-256 ハッシュ（先頭 32 文字）
  - 銘柄コード抽出（4 桁コード候補、既知銘柄との照合）
- ETL パイプライン
  - 差分更新（最終取得日から必要分のみ取得、バックフィル日数指定可）
  - 市場カレンダー先読み、品質チェック（欠損・重複・スパイク・日付不整合）
  - 実行結果を ETLResult オブジェクトで返す
- データスキーマ（DuckDB）
  - Raw / Processed / Feature / Execution / Audit 層のテーブル定義を提供
  - 初期化関数でテーブルとインデックスを自動作成
- 監査ログ（audit）
  - シグナル→発注→約定まで追跡可能なテーブル群（UUID ベースの冪等キー）
  - タイムゾーンは UTC 固定

---

## 主な機能一覧
- kabusys.config.Settings: 環境変数管理（自動 .env ロード対応）
- kabusys.data.jquants_client:
  - get_id_token, fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes, save_financial_statements, save_market_calendar
- kabusys.data.news_collector:
  - fetch_rss, save_raw_news, save_news_symbols, run_news_collection
- kabusys.data.schema:
  - init_schema, get_connection
- kabusys.data.pipeline:
  - run_prices_etl, run_financials_etl, run_calendar_etl, run_daily_etl
- kabusys.data.calendar_management:
  - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, calendar_update_job
- kabusys.data.quality:
  - check_missing_data, check_duplicates, check_spike, check_date_consistency, run_all_checks
- kabusys.data.audit:
  - init_audit_db, init_audit_schema

---

## 必要な環境変数 (.env)
自動でプロジェクトルートの `.env` と `.env.local` を読み込みます（環境変数優先）。自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

最低限設定が必要なキー（例）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- SLACK_BOT_TOKEN — Slack Bot トークン（必須）
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID（必須）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視用）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境: development / paper_trading / live（デフォルト development）
- LOG_LEVEL — ログレベル: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）

例 (.env):
```env
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

前提:
- Python 3.9+（typing の一部記法が使われています）
- pip が利用できること

1. リポジトリをクローン / コピー
2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows では .venv\Scripts\activate)
3. 必要パッケージをインストール
   - duckdb, defusedxml 等が必要です。最低限:
     ```
     pip install duckdb defusedxml
     ```
   - 開発依存（テスト等）があれば適宜追加してください。
4. .env をプロジェクトルートに作成（上記参照）
5. DuckDB スキーマ初期化（後述の使用例参照）

---

## 使い方（主要な例）

以下はライブラリを直接使う例（Python スクリプト/REPL）。

1) DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema

# デフォルトのファイルパスを上書きする場合は settings.duckdb_path を参照
conn = init_schema("data/kabusys.duckdb")
# 以降 conn を使って ETL / ニュース保存 等を行う
```

2) 日次 ETL の実行（J-Quants から差分取得して保存・品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn)  # 引数で target_date や id_token を指定可能
print(result.to_dict())
```

3) ニュース収集ジョブ（RSS の収集と銘柄紐付け）
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
# known_codes は有効な銘柄コードセット（例: 読み込んだ prices テーブルなどから生成）
known_codes = {"7203", "6758", "9432"}
results = run_news_collection(conn, known_codes=known_codes)
print(results)  # {source_name: saved_count}
```

4) J-Quants から特定銘柄の株価を取得して保存
```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes, get_id_token
from kabusys.data.schema import init_schema
from datetime import date

conn = init_schema("data/kabusys.duckdb")
token = get_id_token()
records = fetch_daily_quotes(id_token=token, code="7203", date_from=date(2024, 1, 1), date_to=date(2024, 2, 1))
saved = save_daily_quotes(conn, records)
print(f"saved: {saved}")
```

5) 監査ログスキーマの初期化（audit 用 DB）
```python
from kabusys.data.audit import init_audit_db

conn_audit = init_audit_db("data/kabusys_audit.duckdb")
```

---

## 注意点 / 設計上のポイント
- 自動 .env ロード:
  - プロジェクトルートは .git または pyproject.toml を基準に検出します。
  - OS 環境変数が優先され、.env.local は上書き用途に使われます。
- J-Quants API:
  - レート制限（120 req/min）に合わせて内部で待機します。
  - リトライと ID トークンの自動リフレッシュに対応。
- ニュース収集:
  - RSS の XML パースに defusedxml を使って安全性を高めています。
  - URL の正規化・トラッキングパラメータ除去を行い冪等性を確保します。
- DuckDB:
  - init_schema は必要なテーブルとインデックスを冪等に作成します。
  - audit 初期化時は UTC タイムゾーン固定を設定します。
- 品質チェック:
  - ETL 後に run_all_checks を呼ぶことで欠損・重複・スパイク・日付不整合を検出します。
  - 重大度（error/warning）を返すため、呼び出し側で対応を判断してください。

---

## ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py — 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得・保存ロジック）
    - news_collector.py — RSS ニュース収集・保存・銘柄抽出
    - schema.py — DuckDB スキーマ定義と init_schema/get_connection
    - pipeline.py — ETL パイプライン（差分取得・保存・品質チェック）
    - calendar_management.py — 市場カレンダー操作（営業日判定等）
    - audit.py — 監査ログスキーマ（信頼性・追跡用）
    - quality.py — データ品質チェック
  - strategy/        — 戦略層（未実装のエントリポイントあり）
  - execution/       — 発注/実行層（未実装のエントリポイントあり）
  - monitoring/      — 監視用（未実装のエントリポイントあり）

---

## 開発・拡張のヒント
- strategy / execution / monitoring パッケージは骨組みがあり、戦略ロジックやブローカー接続を実装して統合できます。
- DuckDB 接続は軽量なのでテストでは ":memory:" を使うと便利です。
- run_daily_etl 等は id_token を引数で注入できるため、テスト時にモックトークンを渡して API 呼び出しを切り替えられます。
- news_collector._urlopen をモックしてネットワーク呼び出しをテスト可能です。

---

## ライセンス / 貢献
リポジトリに LICENSE があればそれに従ってください。貢献や issue、PR は歓迎します。README の記載や API 仕様を変更した場合はドキュメントの更新を忘れないでください。

---

何か追加したい情報（例: サンプル .env.example、ユニットテスト実行方法、CI 設定など）があれば教えてください。README に追記します。