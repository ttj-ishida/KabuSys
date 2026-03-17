KabuSys
=======

概要
----
KabuSys は日本株の自動売買プラットフォーム向けに設計されたデータ基盤・ETL・監査ロジックを提供する Python パッケージです。J-Quants API や RSS フィードから市場データ・財務データ・ニュースを安全かつ冪等に収集・保存し、データ品質チェック・マーケットカレンダー管理・監査ログの初期化・ETL パイプライン実行などの基盤機能を備えます。これらは戦略層・実行層（kabuステーション等）に組み込んで利用できます。

主な特徴
--------
- J-Quants API クライアント
  - 日足（OHLCV）、財務（四半期 BS/PL）、JPX カレンダー取得
  - レート制限（120 req/min）とリトライ（指数バックオフ、401時のトークン自動リフレッシュ）対応
  - 取得時刻（fetched_at）を UTC で記録し Look-ahead bias を抑制
  - DuckDB への冪等保存（ON CONFLICT を利用）
- ニュース収集（RSS）
  - トラッキングパラメータ除去・URL 正規化・SSRF 対策・XML インジェクション対策（defusedxml）
  - 記事IDに正規化 URL の SHA-256 を利用（先頭32文字）で冪等性を保証
  - raw_news 保存、記事→銘柄の紐付け機能
- DuckDB スキーマ定義と初期化
  - Raw / Processed / Feature / Execution / Audit 層を含むスキーマ定義
  - テーブル・インデックス作成を冪等に実行
- ETL パイプライン
  - 差分更新（最終取得日からの差分取得 + バックフィル）
  - 市場カレンダーの先読み
  - 品質チェック（欠損・スパイク・重複・日付不整合検出）
  - ETL 実行結果を ETLResult オブジェクトで返却
- 監査ログ（audit）
  - signal → order_request → execution までトレーサビリティを保つ監査スキーマ
  - UUID ベースの冪等キー管理と UTC タイムスタンプ保存

動作要件
--------
- Python >= 3.10
- 必須パッケージ（例）
  - duckdb
  - defusedxml
- 標準ライブラリの urllib / json / logging 等を使用

セットアップ手順
----------------
1. リポジトリをクローン / ダウンロード
2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Linux/macOS) / .venv\Scripts\activate (Windows)
3. 依存パッケージをインストール
   - pip install duckdb defusedxml
   - （パッケージ配布がある場合）pip install -e .

環境変数
--------
KabuSys は .env または OS 環境変数から設定を読み込みます（パッケージ起動時に自動ロード）。自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

主要な環境変数（.env 例）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（省略時: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack チャネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（省略時: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視用）パス（省略時: data/monitoring.db）
- KABUSYS_ENV: 実行環境（development | paper_trading | live）
- LOG_LEVEL: ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）

例 (.env)
export JQUANTS_REFRESH_TOKEN=your_refresh_token
export KABU_API_PASSWORD=your_kabu_password
export SLACK_BOT_TOKEN=xoxb-...
export SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

使い方（基本的なワークフロー）
----------------------------

1) DuckDB スキーマ初期化
- Python REPL やスクリプトで実行:

from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")

- 監査ログスキーマを追加する場合:

from kabusys.data.audit import init_audit_schema
init_audit_schema(conn)

2) 日次 ETL の実行
- 日次 ETL（市場カレンダー、株価、財務、品質チェック）を実行:

from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import get_connection
conn = get_connection("data/kabusys.duckdb")
result = run_daily_etl(conn)  # target_date を指定することも可能
print(result.to_dict())

3) ニュース収集ジョブ
- RSS からニュースを取得して保存:

from kabusys.data.news_collector import run_news_collection
conn = get_connection("data/kabusys.duckdb")
# known_codes を渡すと本文中の銘柄コード抽出・紐付けも行う
results = run_news_collection(conn, known_codes={"7203","6758"})
print(results)

4) カレンダー更新バッチ
- 夜間に JPX カレンダーを差分更新するジョブ:

from kabusys.data.calendar_management import calendar_update_job
conn = get_connection("data/kabusys.duckdb")
saved = calendar_update_job(conn)

5) ユーティリティ・品質チェック
- 個別の品質チェックは quality モジュール経由で呼べます:

from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=None)
for i in issues:
    print(i)

注意事項
--------
- 環境変数の自動読み込みはプロジェクトルート（.git または pyproject.toml の存在）を基に行われます。テスト等で自動読み込みを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- J-Quants API のレート制限やレスポンスコード処理はクライアント側で制御していますが、API キーやトークンは安全に管理してください。
- DuckDB のパスに対して初回実行時に親ディレクトリが自動作成されます。

ディレクトリ構成（主なファイル）
-------------------------------
(src 配下を基準)

- src/kabusys/
  - __init__.py
  - config.py                 - 環境変数/設定管理（Settings）
  - data/
    - __init__.py
    - jquants_client.py       - J-Quants API クライアント & DuckDB 保存関数
    - news_collector.py       - RSS 取得・記事正規化・保存・銘柄抽出
    - schema.py               - DuckDB スキーマ定義・初期化
    - pipeline.py             - ETL パイプライン（差分取得・品質チェック等）
    - calendar_management.py  - 市場カレンダー管理・営業日判定
    - audit.py                - 監査ログ（signal/order_requests/executions）初期化
    - quality.py              - データ品質チェック
  - strategy/
    - __init__.py             - 戦略関連モジュール（拡張ポイント）
  - execution/
    - __init__.py             - 発注/実行関連モジュール（拡張ポイント）
  - monitoring/
    - __init__.py             - 監視・メトリクス関連（未実装/拡張ポイント）

拡張点
------
- strategy/ と execution/ はパッケージ空の初期化のみ含まれており、ここに戦略ロジック・オーダー作成・kabu ステーション連携などを実装できます。
- Slack 通知や監視のための機能はモニタリング層や外部ジョブから組み合わせて利用してください。

サンプルスクリプト例
-------------------
簡単な起動スクリプト例:

#!/usr/bin/env python3
from kabusys.data.schema import init_schema, get_connection
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn)
print(result.to_dict())

最後に
------
この README はコードベースから抽出した機能・想定利用方法をまとめたものです。実運用では環境ごとの設定管理、資格情報の安全な保管、バックアップや監視の仕組み（ログ集約・アラート等）を必ず組み込んでください。プロジェクトを拡張する際は、既存の冪等設計・UTC 時刻ルール・監査要件に沿うように実装してください。