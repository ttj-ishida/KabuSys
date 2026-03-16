KabuSys
=======

日本株向けの自動売買プラットフォーム用ライブラリ。  
データ取得（J-Quants）、ETLパイプライン、DuckDBスキーマ定義、データ品質チェック、監査ログなど、マーケットデータ処理と発注トレーサビリティの基盤機能を提供します。

※本リポジトリはライブラリ実装の抜粋です。戦略やブローカー連携（kabuステーション等）については別モジュールで実装する想定です。

主な機能
--------
- J-Quants API クライアント（デイリー株価、財務データ、マーケットカレンダー取得）
  - APIレート制限（120 req/min）を守るレートリミッタ
  - 再試行（指数バックオフ、最大3回）および 401 の自動トークンリフレッシュ
  - 取得時刻（fetched_at）を UTC で記録（Look-ahead bias 防止）
- DuckDB スキーマ定義と初期化
  - Raw / Processed / Feature / Execution の多層スキーマ
  - インデックスや外部キーを含む冪等な DDL
- ETL パイプライン
  - 差分更新（最終取得日からの差分 + バックフィル）
  - 市場カレンダー先読み（lookahead）
  - 品質チェックの実行（欠損・重複・スパイク・日付不整合）
  - ETL 結果 (ETLResult) に品質問題やエラーを集約
- データ品質チェックモジュール
  - 欠損データ検出、スパイク（急騰・急落）検出、重複チェック、日付整合性チェック
  - 各チェックは QualityIssue のリストを返し、呼び出し側が重大度に応じて対応可能
- 監査ログ（audit）
  - シグナル → 発注要求 → 約定 のトレーサビリティ用テーブル群
  - 冪等キー（order_request_id / broker_execution_id 等）をサポート

セットアップ手順
----------------

前提
- Python 3.9+（typing の挙動や Path 型サポートを考慮）
- duckdb 等のライブラリが必要（requirements.txt を用意している場合はそちらを利用）

例: 開発環境の簡易セットアップ
1. リポジトリをクローン/配置
2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install duckdb
   - （他に必要なライブラリがあれば追加インストールしてください）
4. パッケージを開発モードでインストール（プロジェクトルートに pyproject.toml がある場合）
   - pip install -e .

環境変数（必須）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API 用パスワード（必須）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack 送信先チャンネル ID（必須）

オプション / デフォルト
- KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL （デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると .env の自動読み込みを無効化
- KABUSYS_DISABLE_AUTO_ENV_LOAD の説明: テスト等で自動ロードを抑制したい場合に使用
- KABUSYS は起点ファイルの親ディレクトリから .git もしくは pyproject.toml を探索し、.env / .env.local を自動読み込みします（OS 環境変数 > .env.local > .env の優先度）

データベースパス（デフォルト）
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db

使い方（基本例）
----------------

1) DuckDB スキーマ初期化
- 一度DBを作成しておく。":memory:" も指定可。

Python 例:
from kabusys.data.schema import init_schema
from kabusys.config import settings

# ファイルベースDBを初期化して接続を取得
conn = init_schema(settings.duckdb_path)

または任意パス:
conn = init_schema("data/kabusys.duckdb")

2) 日次 ETL の実行
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)
# ETLResult オブジェクトを確認
print(result.to_dict())

- run_daily_etl は以下を順に実行します:
  1. 市場カレンダー ETL（先読み）
  2. 株価日足 ETL（差分 + backfill）
  3. 財務データ ETL（差分 + backfill）
  4. 品質チェック（オプションで無効化可能）

ETLResult の主要フィールド:
- target_date: 実行対象日
- prices_fetched / prices_saved
- financials_fetched / financials_saved
- calendar_fetched / calendar_saved
- quality_issues: quality.QualityIssue のリスト
- errors: 実行中に発生したエラー文字列リスト
- has_errors / has_quality_errors: 簡易判定用プロパティ

3) J-Quants クライアントを直接利用（テストや特定用途向け）
from kabusys.data import jquants_client as jq
from kabusys.config import settings

id_token = jq.get_id_token(settings.jquants_refresh_token)
records = jq.fetch_daily_quotes(id_token=id_token, date_from=date(2023,1,1), date_to=date(2023,1,31))

DuckDB への保存（冪等）
from kabusys.data import jquants_client as jq
count_saved = jq.save_daily_quotes(conn, records)

4) 監査ログ（audit）初期化
from kabusys.data.audit import init_audit_schema, init_audit_db

# 既存の DuckDB 接続へ監査テーブルを追加
init_audit_schema(conn)

# または監査専用DBを作成
audit_conn = init_audit_db("data/audit.duckdb")

注意点 / 実装の要点
-------------------
- レート制限: J-Quants API は 120 req/min。内部で固定間隔スロットリングを行います。
- リトライ: HTTP 408/429/5xx 系は最大3回のリトライ（指数バックオフ）。429 の場合は Retry-After ヘッダを優先。
- 401 の取り扱い: ID トークン期限切れで 401 を受け取った場合、自動でリフレッシュして1回リトライします。
- 取得データのトレーサビリティ: save_* 関数は fetched_at や ON CONFLICT DO UPDATE を利用して冪等に保存します。
- 品質チェックは Fail-Fast ではなく全件収集を行い、呼び出し元が重大度に応じて処理継続/停止を判断します。
- .env の解析はシェル風の export KEY=val やクォート、インラインコメントの挙動を考慮した独自パーサを使っています。

ディレクトリ構成（抜粋）
-----------------------
src/kabusys/
- __init__.py               - パッケージ初期化（__version__ 等）
- config.py                 - 環境変数 / 設定管理（自動 .env ロード、Settings）
- data/
  - __init__.py
  - jquants_client.py       - J-Quants API クライアント（fetch_*/save_*）
  - schema.py               - DuckDB スキーマ定義 & init_schema / get_connection
  - pipeline.py             - ETL パイプライン（run_daily_etl 等）
  - audit.py                - 監査ログスキーマ（init_audit_schema / init_audit_db）
  - quality.py              - データ品質チェック（check_missing_data, check_spike, ...）
- strategy/
  - __init__.py             - 戦略関連のエントリ（拡張ポイント）
- execution/
  - __init__.py             - 発注/約定管理（拡張ポイント）
- monitoring/
  - __init__.py             - モニタリング関連（拡張ポイント）

よくある操作例（まとめ）
-----------------------
- スキーマ初期化:
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")

- ETL 実行:
  from kabusys.data.pipeline import run_daily_etl
  res = run_daily_etl(conn)
  if res.has_errors or res.has_quality_errors:
      # アラート、手動確認等の処理

- 監査ログ初期化:
  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn)

貢献
----
機能追加やバグ修正の PR は歓迎します。まず issue で相談してください。コードスタイル・テスト方針は別途 CONTRIBUTING.md を用意する予定です。

ライセンス
---------
プロジェクトに適したライセンスを設定してください（このドキュメントはライセンスに依存しません）。

補足
----
- 本 README はソースコード（src/kabusys/*.py）の実装に基づいて作成しています。運用時は各 API キーの管理や秘密情報の取り扱いに十分注意してください。
- 実際のブローカ API 連携（発注送信、約定受信、エラーハンドリング等）は execution/ 以下で実装してください。README の使用例は ETL とデータ基盤部分に焦点を当てています。

必要であれば、設定ファイル（.env.example）、簡易 CLI スクリプト、ユニットテスト例、CI ワークフロー用の説明も追加します。どれを優先して追加しますか？