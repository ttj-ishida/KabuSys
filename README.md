# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ（モジュール群）。  
データ取得・ETL、データ品質チェック、ニュース収集、マーケットカレンダー管理、監査ログ（発注→約定トレース）などを提供します。

---

## プロジェクト概要

KabuSys は J-Quants API 等から株価・財務・カレンダー・ニュースを取得して DuckDB に蓄積し、ETL・品質チェック・監査ログ機能を備えたデータ基盤／自動売買補助ライブラリです。設計上のポイントは以下の通りです。

- J-Quants API のレート制限遵守（120 req/min）とリトライ（指数バックオフ、401 時の自動トークンリフレッシュ）
- DuckDB を使った冪等的な保存（ON CONFLICT を利用）
- ニュース収集での SSRF/XML 攻撃防御、トラッキングパラメータ除去による記事ID冪等化
- 市場カレンダーを利用した営業日ロジック（next/prev/is_trading_day 等）
- ETL の差分取得・バックフィル・品質チェック（欠損・重複・スパイク・日付不整合）
- 監査ログ（signal → order_request → executions のトレーサビリティ）

---

## 主な機能一覧

- data.jquants_client
  - get_id_token, fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - DuckDB へ保存する save_* 関数（save_daily_quotes, save_financial_statements, save_market_calendar）
  - レートリミット／リトライ／look-ahead-bias 回避の fetched_at 記録
- data.news_collector
  - RSS フィード取得（gzip 対応）と記事の前処理
  - 記事の冪等保存（raw_news）と銘柄紐付け（news_symbols）
  - SSRF／XML Bomb 対策、受信サイズ制限
- data.schema
  - DuckDB 向けスキーマ定義（Raw / Processed / Feature / Execution / Audit 用テーブル）
  - init_schema(db_path) で初期化
- data.pipeline
  - run_daily_etl: カレンダー取得 → 株価差分取得 → 財務差分取得 → 品質チェック
  - run_prices_etl / run_financials_etl / run_calendar_etl
  - 差分更新と backfill による後出し訂正吸収
- data.calendar_management
  - calendar_update_job: 夜間カレンダー差分更新
  - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
- data.quality
  - check_missing_data, check_duplicates, check_spike, check_date_consistency, run_all_checks
  - QualityIssue 型で問題を収集（severity: error / warning）
- data.audit
  - 監査ログ用テーブル定義と初期化（signal_events, order_requests, executions）
  - init_audit_schema / init_audit_db

その他: strategy, execution, monitoring パッケージ用のエントリポイント（実装の拡張を想定）。

---

## 要件（依存関係）

- Python 3.10 以上（型アノテーションで | を使用）
- 必須パッケージ:
  - duckdb
  - defusedxml

（標準ライブラリのみで動く部分も多いですが、DuckDB を利用するため duckdb パッケージが必要です。）

インストール例（仮想環境推奨）:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
```

---

## 環境変数（設定）

kabusys.config.Settings を通じて環境変数で設定を取得します。自動でプロジェクトルートの `.env` → `.env.local` を読み込む機能があります（無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。

主な環境変数:

- JQUANTS_REFRESH_TOKEN (必須)  
  J-Quants のリフレッシュトークン（get_id_token に使う）
- KABU_API_PASSWORD (必須)  
  kabuステーション API パスワード
- KABU_API_BASE_URL (任意)  
  デフォルト: http://localhost:18080/kabusapi
- SLACK_BOT_TOKEN (必須)  
  Slack 通知用 Bot トークン（将来的な通知機能で使用）
- SLACK_CHANNEL_ID (必須)  
  Slack チャンネル ID
- DUCKDB_PATH (任意)  
  デフォルト: data/kabusys.duckdb
- SQLITE_PATH (任意)  
  デフォルト: data/monitoring.db
- KABUSYS_ENV (任意)  
  有効値: development, paper_trading, live（デフォルト development）
- LOG_LEVEL (任意)  
  DEBUG, INFO, WARNING, ERROR, CRITICAL（デフォルト INFO）

.env.example を用意してコピーし `.env` を作成してください。

---

## セットアップ手順

1. リポジトリをクローン、仮想環境作成・有効化
2. 必要パッケージをインストール
   - pip install duckdb defusedxml
3. プロジェクトルートに `.env`（や `.env.local`）を作成して環境変数を設定
4. DuckDB スキーマを初期化
   - デフォルトファイル: data/kabusys.duckdb（DUCKDB_PATH で変更可）
   - 例: init_schema("data/kabusys.duckdb")
5. 監査ログ用 DB を初期化（必要な場合）
   - init_audit_db("data/audit.duckdb") または init_audit_schema(conn)

---

## 使い方（サンプル）

以下は基本的な利用例です。スクリプトとして実行できます。

- スキーマ初期化（DuckDB）:
```python
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
```

- 監査ログ用 DB 初期化:
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/kabusys_audit.duckdb")
```

- 日次 ETL を実行（市場カレンダー取得 → 株価/財務取得 → 品質チェック）:
```python
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn)  # target_date を指定可能
print(result.to_dict())
```

- ニュース収集の実行（既知銘柄コードセットを渡して銘柄紐付け）:
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984"}  # 有効銘柄コードのセット
results = run_news_collection(conn, known_codes=known_codes)
print(results)  # {source_name: 新規保存数}
```

- J-Quants から日足を直接取得して保存:
```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
records = fetch_daily_quotes(code="7203", date_from=None, date_to=None)
saved = save_daily_quotes(conn, records)
print("saved:", saved)
```

- 品質チェック単体実行:
```python
from kabusys.data.quality import run_all_checks
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
issues = run_all_checks(conn)
for i in issues:
    print(i)
```

---

## 実運用時の注意点

- J-Quants API のレート制限（120 req/min）を守るため内部でスロットリングを行っています。多数銘柄の全件取得は時間がかかります。
- get_id_token は内部でリフレッシュを行います。401 を受けて一度だけ自動リフレッシュしてリトライする設計です。
- ニュース収集では外部から取得する RSS の扱いに注意（SSRF、XML 攻撃、巨大レスポンス対策を組み込んでいますが、ソースの信頼性は重要です）。
- DuckDB のファイルはバックアップと運用上の管理を行ってください（ファイルロック、バックアップ方針等）。
- KABUSYS_ENV を "live" にすると本番向け挙動（設定・監視）を有効にする想定です。paper_trading では仮想発注等との連携が前提になります（実装側の戦略・実行モジュールに依存）。
- 自動で .env を読み込む挙動を無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト時に便利）。

---

## ディレクトリ構成

主要ファイル・モジュール一覧（src/kabusys 以下）:

- __init__.py
  - パッケージ初期化。__version__ を公開。
- config.py
  - 環境変数読み込み・Settings（アプリ設定）
  - 自動 .env 読み込み（.env → .env.local）、必須変数チェック
- data/
  - __init__.py
  - jquants_client.py
    - J-Quants API クライアント、取得・保存関数（rate limiting, retry）
  - news_collector.py
    - RSS 取得・前処理・raw_news 保存・銘柄抽出
  - schema.py
    - DuckDB のスキーマ定義と init_schema / get_connection
  - pipeline.py
    - ETL パイプライン（run_daily_etl 等）
  - calendar_management.py
    - 市場カレンダー管理（更新ジョブ、営業日判定ヘルパ）
  - audit.py
    - 監査ログ（signal/order_request/executions）用スキーマと初期化
  - quality.py
    - データ品質チェック（欠損・重複・スパイク・日付不整合）
- strategy/
  - __init__.py（戦略関連のエントリ、実装は拡張想定）
- execution/
  - __init__.py（発注・ブローカー連携の実装を想定）
- monitoring/
  - __init__.py（監視・アラートの実装を想定）

---

## 開発・拡張のヒント

- strategy / execution / monitoring パッケージは拡張ポイントです。strategy 層は features / ai_scores テーブルを参照し、signal_queue にエンキューする形を想定できます。
- 監査ログは init_audit_schema を使って既存の DuckDB 接続に追加できます。監査は UTC タイムゾーンで保存されます（init で SET TimeZone='UTC' を実行）。
- 大量データを扱う箇所（ニュースのバルク INSERT、raw 保存など）はチャンク処理やトランザクション管理を行っているため、処理失敗時はロールバックが発生します。拡張時もトランザクション設計に注意してください。
- 単体テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 にして .env の自動読み込みを抑制し、テスト用の環境変数を注入してください。

---

何か特定の機能の使い方（例: ETL のスケジューリング、ニュースフィード追加、戦略の実装テンプレート等）について README を拡張したい場合は、用途に合わせた例や CLI スクリプト例を追加しますので要望を教えてください。