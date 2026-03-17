# KabuSys — 日本株自動売買システム

簡潔な説明:
KabuSys は日本株の自動売買プラットフォーム向けに設計されたライブラリ群です。J-Quants API や RSS フィードからのデータ収集、DuckDB によるデータ管理、日次 ETL パイプライン、データ品質チェック、マーケットカレンダー管理、監査ログ（発注→約定のトレーサビリティ）など、量産運用を想定した各種機能を提供します。

主な設計方針:
- データの冪等性（ON CONFLICT / DO UPDATE / DO NOTHING）
- Look-ahead bias 回避のため取得時刻（UTC）を記録
- API レート制御、リトライ、トークン自動リフレッシュ
- SSRF / XML Bomb / メモリ DoS 等のセキュリティ対策
- DuckDB を利用した軽量で高速なローカルデータ管理

---

## 機能一覧

- 環境設定管理
  - .env ファイル（および OS 環境変数）から設定を自動ロード
  - 必須変数の取得と検証（例: JQUANTS_REFRESH_TOKEN 等）

- データ取得 / 保存（kabusys.data.jquants_client）
  - 株価日足（OHLCV）、財務（四半期 BS/PL）、JPX マーケットカレンダーの取得
  - API レート制御（120 req/min）、リトライ（指数バックオフ）、401 時のトークン自動更新
  - DuckDB への冪等保存関数（raw テーブル群への INSERT ... ON CONFLICT）

- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得（gzip サポート）、XML パース（defusedxml）、URL 正規化、トラッキングパラメータ除去
  - 記事ID は正規化 URL の SHA-256（先頭32文字）で生成して冪等性を担保
  - SSRF / プライベートアドレス対策、受信サイズ制限、DB へチャンク単位で挿入（INSERT ... RETURNING）

- DuckDB スキーマ管理（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層に分かれたテーブル定義と初期化
  - インデックス定義や外部キー依存を考慮した作成順序
  - init_schema / get_connection API

- ETL パイプライン（kabusys.data.pipeline）
  - 差分取得（最終取得日を利用）、バックフィル（後出し修正吸収）
  - 市場カレンダー、株価、財務の順に差分取得・保存
  - 品質チェックの実行（kabusys.data.quality）の組込み
  - run_daily_etl による一括実行と ETLResult による結果報告

- マーケットカレンダー管理（kabusys.data.calendar_management）
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day
  - 夜間の calendar_update_job（差分取得・保存・バックフィル・健全性チェック）

- 品質チェック（kabusys.data.quality）
  - 欠損データ、スパイク（前日比）、重複、日付不整合（未来日付・非営業日のデータ）
  - 各チェックは QualityIssue を返し、致命度（error/warning）を付与

- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions 等の監査テーブル初期化
  - 発注→約定までのトレーサビリティを UUID 連鎖で保証
  - UTC タイムスタンプ運用を前提

---

## 必要条件（動作環境）

- Python 3.10+（型注釈で一部 union 型等を利用）
- 主要依存パッケージ（例）
  - duckdb
  - defusedxml

（実際のプロジェクトでは pyproject.toml / requirements.txt を参照してください）

---

## セットアップ手順

1. リポジトリをクローン
   - git clone ... （リポジトリ URL）

2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Linux / macOS)
   - .venv\Scripts\activate     (Windows)

3. 依存パッケージをインストール
   - pip install -U pip
   - pip install duckdb defusedxml
   - （もしパッケージ化されている場合）pip install -e .

4. 環境変数の準備
   - プロジェクトルートに `.env` を作成するか OS 環境変数を設定します。
   - 自動ロードはデフォルトで有効（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化）。

   代表的な環境変数（必須）
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD: kabuステーション API のパスワード
   - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
   - SLACK_CHANNEL_ID: Slack 通知先チャンネル ID

   省略可 / デフォルト有り
   - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
   - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: SQLite ファイルパス（デフォルト: data/monitoring.db）

   例 .env:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
   KABU_API_PASSWORD=your_kabu_password_here
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C1234567890
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   ```

5. データベース初期化（DuckDB）
   - Python REPL やスクリプトから schema.init_schema を呼び出してテーブルを作成します。
   - 例:
     ```
     from kabusys.data.schema import init_schema
     from kabusys.config import settings

     conn = init_schema(settings.duckdb_path)
     ```

---

## 使い方（主要な API 例）

- DuckDB 接続の初期化:
  ```
  from kabusys.data.schema import init_schema
  from kabusys.config import settings

  conn = init_schema(settings.duckdb_path)
  ```

- 日次 ETL を実行:
  ```
  from kabusys.data.pipeline import run_daily_etl
  res = run_daily_etl(conn)  # 戻り値は ETLResult
  print(res.to_dict())
  ```

- ニュース収集ジョブ実行:
  ```
  from kabusys.data.news_collector import run_news_collection
  result = run_news_collection(conn, sources=None, known_codes=set(['7203','6758']))
  print(result)  # {source_name: 新規保存件数}
  ```

- カレンダー夜間更新ジョブ:
  ```
  from kabusys.data.calendar_management import calendar_update_job
  saved = calendar_update_job(conn)
  print('saved:', saved)
  ```

- マーケットカレンダーのユーティリティ:
  ```
  from kabusys.data.calendar_management import is_trading_day, next_trading_day
  import datetime
  d = datetime.date(2025, 1, 6)
  print(is_trading_day(conn, d))
  print(next_trading_day(conn, d))
  ```

- 監査テーブルの初期化（audit ログを別 DB で使う場合）:
  ```
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db('data/audit.duckdb')
  ```

- 品質チェック単体実行:
  ```
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn)
  for i in issues:
      print(i)
  ```

注: 多くの関数は外部 API（J-Quants）を呼ぶため、id_token を引数で注入できる設計になっています（テスト容易化）。設定に従って自動的にトークンを取得 / リフレッシュします。

---

## 推奨運用フロー（例）

1. 定期バッチ（夜間）:
   - calendar_update_job を実行して market_calendar を最新化
   - run_daily_etl を実行して株価 / 財務 / カレンダーを差分更新、品質チェックを実施
   - 必要に応じて Slack などで ETLResult を通知

2. リアルタイム / 当日運用:
   - ETL 後に features / ai_scores を生成（本コードベースには特徴量生成は含まれないため実装が必要）
   - signals を生成して signal_queue に登録、execution 層で発注管理
   - 監査ログ（order_requests / executions）へ逐次書き込み

---

## ディレクトリ構成

以下は本コードからの抜粋ベースの主要ファイル構成（src/kabusys）です:

- src/kabusys/
  - __init__.py
  - config.py                      # 環境変数 / 設定の読み込み
  - data/
    - __init__.py
    - jquants_client.py            # J-Quants API クライアント（取得 + DuckDB 保存）
    - news_collector.py            # RSS ニュース収集・前処理・保存
    - schema.py                    # DuckDB スキーマ定義・初期化
    - pipeline.py                  # ETL パイプライン（run_daily_etl 等）
    - calendar_management.py       # カレンダー更新・営業日ユーティリティ
    - audit.py                     # 監査ログテーブル初期化
    - quality.py                   # データ品質チェック
  - strategy/
    - __init__.py                  # 戦略関連（拡張ポイント）
  - execution/
    - __init__.py                  # 発注・実行層（拡張ポイント）
  - monitoring/
    - __init__.py                  # 監視・メトリクス（拡張ポイント）

注: strategy, execution, monitoring はプレースホルダとして用意されており、プロジェクト固有のロジックを実装する拡張ポイントです。

---

## 注意事項 / 補足

- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を基準に行われます。テストなどで自動読み込みを無効にしたい場合は、環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- J-Quants API のレート制御やリトライは実装済みですが、運用環境では API 利用ポリシーを遵守してください。
- DuckDB の型・制約はスキーマに厳密に定義されています。外部からの直接挿入やスキーマ変更には注意してください。
- news_collector は RSS の不正データ（XML Bomb 等）や SSRF を考慮した実装になっています。外部 URL の取り扱いは慎重に行ってください。

---

README の補足やサンプルスクリプト（ETL バッチ、ワーカー、監視通知など）の追加を希望される場合は、用途に合わせた具体的な例を作成します。必要であれば運用スケジュール（cron / Airflow / Prefect など）やデプロイ手順も追記できます。