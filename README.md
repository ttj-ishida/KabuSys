KabuSys — 日本株自動売買基盤（README）
==================================

概要
----
KabuSys は日本株のデータ取得・ETL・品質検査・ニュース収集・監査ログなどを備えた自動売買プラットフォームのコアライブラリです。J-Quants API や RSS フィードからデータを収集して DuckDB に格納し、戦略・実行層に渡すための土台機能を提供します。

主な設計方針（抜粋）
- データ取得はレート制限・リトライ・自動トークンリフレッシュを備える
- データ保存は冪等（ON CONFLICT による上書き）で安全に行う
- ニュース収集は SSRF / XML Bomb 等の安全対策を組み込む
- データ品質チェックを行い問題を検出・報告する
- 監査ログ（シグナル→発注→約定のトレース）を専用スキーマで保持する

機能一覧
--------
- 環境変数 / .env 管理
  - プロジェクトルートの .env / .env.local を自動で読み込み（テスト等で無効化可能）
  - 必須設定に対する明示的エラー
- J-Quants API クライアント（kabusys.data.jquants_client）
  - 日次株価（OHLCV）、財務（四半期）、マーケットカレンダー取得
  - レートリミット（120 req/min）・リトライ・401時トークンリフレッシュ対応
  - DuckDB への冪等保存（raw_prices / raw_financials / market_calendar）
- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得、前処理、記事ID生成（正規化URLの SHA-256 の先頭 32 文字）
  - SSRF・サイズ上限・gzip 解凍・XML の安全パースなど多層の防御
  - raw_news / news_symbols へのバルク保存（トランザクション・チャンク処理）
  - 銘柄コード抽出（4桁数字）と既知銘柄リストによる紐付け
- DuckDB スキーマ管理（kabusys.data.schema）
  - Raw / Processed / Feature / Execution / Audit 層のテーブル定義と初期化
  - インデックス定義、init_schema()/get_connection()
- ETL パイプライン（kabusys.data.pipeline）
  - 日次 ETL（市場カレンダー→株価→財務→品質チェック）の統合実行
  - 差分更新 / バックフィル / 品質チェック（欠損・スパイク・重複・日付不整合）
- カレンダー管理（kabusys.data.calendar_management）
  - 営業日判定、次/前営業日の取得、期間内営業日列挙、夜間カレンダー更新ジョブ
  - market_calendar がない場合は曜日ベースのフォールバック
- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions の監査テーブルとインデックス
  - 全ての TIMESTAMP を UTC で保存する方針
- 品質チェック（kabusys.data.quality）
  - check_missing_data, check_spike, check_duplicates, check_date_consistency
  - QualityIssue オブジェクトで検出結果を返す

セットアップ手順
----------------
1. リポジトリをクローン（例）
   - git clone <repo-url>
   - 本リポジトリは src/ 配下にパッケージを置くレイアウトを想定しています。

2. Python 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - 必要な主な外部パッケージ:
     - duckdb
     - defusedxml
     - （その他プロジェクト固有の依存がある場合は pyproject.toml / requirements.txt を参照）
   - 例:
     - pip install duckdb defusedxml

4. 環境変数 (.env) を用意
   - プロジェクトルートの .env または .env.local に以下の必須設定を追加してください（例）:
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - SLACK_BOT_TOKEN=...
     - SLACK_CHANNEL_ID=...
   - 任意 / デフォルト:
     - KABUSYS_ENV=development | paper_trading | live  (デフォルト: development)
     - LOG_LEVEL=DEBUG | INFO | WARNING | ERROR | CRITICAL (デフォルト: INFO)
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
   - 自動 .env ロードを無効にする場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. データベース初期化
   - Python REPL またはスクリプトで DuckDB スキーマを初期化します。
     例:
     from kabusys.data import schema
     conn = schema.init_schema("data/kabusys.duckdb")

使い方（コード例）
-----------------
- 設定値の参照
  from kabusys.config import settings
  token = settings.jquants_refresh_token
  is_live = settings.is_live

- DuckDB スキーマ初期化
  from kabusys.data import schema
  conn = schema.init_schema("data/kabusys.duckdb")

- 日次 ETL を実行する
  from kabusys.data import pipeline
  result = pipeline.run_daily_etl(conn)
  print(result.to_dict())

- ニュース収集ジョブを走らせる
  from kabusys.data.news_collector import run_news_collection
  # known_codes に銘柄コード集合を渡すと記事と銘柄の紐付けを自動で行う
  counts = run_news_collection(conn, known_codes={"7203","6758"})
  print(counts)

- JPX カレンダー夜間更新ジョブ
  from kabusys.data.calendar_management import calendar_update_job
  saved = calendar_update_job(conn)
  print(f"saved: {saved}")

- J-Quants の ID トークン取得（内部で refresh token を使用）
  from kabusys.data.jquants_client import get_id_token
  id_token = get_id_token()  # settings.jquants_refresh_token を使用

運用時のポイント・注意事項
-------------------------
- J-Quants API のレート制限（120 req/min）を守るため内部でスロットリングしています。大量ページネーション時は時間がかかる点に注意してください。
- get_id_token は 401 応答時に自動でリフレッシュを試みます（1回のみ）。
- ニュース取得処理は外部 URL を扱うため SSRF・XML 注入対策を実装していますが、運用時は known RSS ソースの管理を厳格に行ってください。
- DuckDB のファイルパス（DUCKDB_PATH）は settings.duckdb_path で管理され、デフォルトは data/kabusys.duckdb です。
- テスト時に自動 .env ロードを避けたい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

ディレクトリ構成
----------------
（主要ファイルのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                       -- 環境変数・設定管理
    - data/
      - __init__.py
      - jquants_client.py             -- J-Quants API クライアント（取得・保存）
      - news_collector.py             -- RSS ニュース収集・保存・銘柄抽出
      - schema.py                     -- DuckDB スキーマ定義・初期化
      - pipeline.py                   -- ETL パイプライン（run_daily_etl 等）
      - calendar_management.py        -- 市場カレンダー関連ユーティリティ
      - audit.py                      -- 監査ログ（signal / order / execution）
      - quality.py                    -- データ品質チェック（QualityIssue）
    - strategy/
      - __init__.py                    -- 戦略層（拡張ポイント）
    - execution/
      - __init__.py                    -- 発注/実行層（拡張ポイント）
    - monitoring/
      - __init__.py                    -- 監視/メトリクス（拡張ポイント）

開発・拡張ガイド（簡易）
-----------------------
- 新しい ETL ジョブやデータ保存ロジックを追加するときは既存の設計原則（冪等性、fetched_at の記録、UTC タイムスタンプ）に従ってください。
- 戦略層（strategy）や発注層（execution）はパッケージ内に拡張ポイントがあり、監査ログ（audit）と連携することでトレースが可能です。
- テスト時は settings の注入や KABUSYS_DISABLE_AUTO_ENV_LOAD を使って環境依存を減らしてください。

よくある質問（FAQ）
------------------
Q: .env の自動ロードはどのように動作しますか？
A: config.py がプロジェクトルート（.git または pyproject.toml を基準）を探索し、.env → .env.local の順でロードします。OS 環境変数は保護され、.env.local は上書き可能です。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

Q: DuckDB のスキーマを初期化したい
A: from kabusys.data import schema; conn = schema.init_schema("data/kabusys.duckdb")

Q: ETL が失敗したら？
A: pipeline.run_daily_etl は個々のステップでエラーを捕捉して result.errors にメッセージを追加します。致命的なエラーは例外で上がりますのでログを確認してください。

ライセンス・貢献
----------------
（ここにプロジェクトのライセンス表記や貢献方法を記載してください。リポジトリに LICENSE ファイルがある場合は参照してください。）

補足
----
本 README はソース内のドキュメント文字列（docstring）や実装から要点を抽出して作成しています。各モジュールにはさらに詳細な設計メモや DataPlatform.md 等の参照ドキュメントを用意している想定です。具体的な運用スクリプト（cron / Airflow / GitHub Actions 等）や証券会社との発注連携は別途実装してください。

もし README に追加したい内容（例えばサンプル .env.example、CI 手順、より詳しい利用例）があれば教えてください。