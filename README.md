# KabuSys

日本株向けの自動売買基盤ライブラリ。J-Quants / kabuステーション 等のデータソースからデータを収集・保存し、ETL・品質チェック・ニュース収集・監査ログなど自動売買システムに必要な基盤機能を提供します。

---

## プロジェクト概要

KabuSys は以下を目的とした Python モジュール群です。

- J-Quants API から株価（OHLCV）、財務データ、JPX マーケットカレンダーを取得・保存
- RSS フィードからニュース記事を収集・前処理し DuckDB に保存
- 日次 ETL パイプライン（差分取得、バックフィル、品質チェック）を実行
- マーケットカレンダーの営業日判定・更新ロジックを提供
- 監査ログ（signal → order → execution のトレーサビリティ）を DuckDB で管理
- 冪等性・レート制御・リトライ・セキュリティ（SSRF 対策等）を組み込んだ実装設計

設計上のポイント：
- J-Quants API に対してレート制限（120 req/min）と指数バックオフによるリトライを実装
- DuckDB への保存操作は冪等性（ON CONFLICT）を重視
- RSS 収集は URL 正規化・トラッキング除去・SSRF ブロック・XML インジェクション対策を実装
- 品質チェックは Fail-Fast せず問題を収集して報告

---

## 主な機能一覧

- jquants_client
  - get_id_token(), fetch_daily_quotes(), fetch_financial_statements(), fetch_market_calendar()
  - save_daily_quotes(), save_financial_statements(), save_market_calendar()
  - レートリミッタ、リトライ（401 のトークン自動リフレッシュ含む）、fetched_at の記録

- data.pipeline
  - run_prices_etl(), run_financials_etl(), run_calendar_etl(), run_daily_etl()
  - 差分取得、バックフィル、品質チェックを一括実行

- data.schema
  - init_schema(), get_connection()
  - Raw / Processed / Feature / Execution 層の DuckDB スキーマ定義と初期化

- data.news_collector
  - fetch_rss(), save_raw_news(), run_news_collection()
  - URL 正規化、トラッキングパラメータ除去、gzip サイズ検査、SSRF/プライベートホスト検査

- data.calendar_management
  - is_trading_day(), next_trading_day(), prev_trading_day(), get_trading_days(), calendar_update_job()

- data.quality
  - check_missing_data(), check_spike(), check_duplicates(), check_date_consistency(), run_all_checks()
  - 品質問題を QualityIssue オブジェクトで返却

- data.audit
  - init_audit_schema(), init_audit_db()
  - 監査用テーブル（signal_events, order_requests, executions）とインデックスの初期化

- config
  - Settings クラスで環境変数を集中管理。.env / .env.local の自動読み込み機構を備える（プロジェクトルート検出あり）

---

## セットアップ手順

前提：Python 3.9+（型ヒントでの Union 表記などを使っています）。プロジェクトルートに `pyproject.toml` や `.git` があることを想定します。

1. リポジトリをチェックアウト
   - 任意の方法でソースを取得します。

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - 必須（主要）依存例：
     - duckdb
     - defusedxml
   - 例:
     - pip install duckdb defusedxml

   ※ 実際のプロジェクトでは requirements.txt / pyproject.toml に依存を記載してください。

4. パッケージを開発モードでインストール（任意）
   - プロジェクトルートで:
     - python -m pip install -e .

5. 環境変数の設定
   - プロジェクトルートの `.env` または `.env.local` に設定を置けます。
   - 自動読み込みはデフォルトで有効（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須環境変数（コード上で required）:
     - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン
     - KABU_API_PASSWORD: kabuステーション API パスワード
     - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID: Slack 通知先チャンネルID
   - 任意:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト development）
     - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）
     - KABU_API_BASE_URL: kabu API ベース URL（デフォルト http://localhost:18080/kabusapi）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH: SQLite 監視 DB（デフォルト data/monitoring.db）

   例 .env（最低限の必須項目）:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（主要な API と実行例）

以下は典型的な操作例です。適宜ロギング設定などを行ってください。

- DuckDB スキーマ初期化
  ```python
  from kabusys.config import settings
  from kabusys.data.schema import init_schema

  # settings.duckdb_path は Settings.duckdb_path プロパティで取得可能
  conn = init_schema(settings.duckdb_path)
  ```

- 日次 ETL 実行（J-Quants からの差分取得・保存・品質チェック）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn)  # target_date を指定可能
  print(result.to_dict())
  ```

- マーケットカレンダー夜間更新ジョブ
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  saved = calendar_update_job(conn)
  print(f"saved: {saved}")
  ```

- ニュース収集の実行
  ```python
  from kabusys.data.news_collector import run_news_collection

  # known_codes は銘柄抽出に使用する有効コードセット（例: {'7203','6758'}）
  results = run_news_collection(conn, known_codes={'7203', '6758'})
  print(results)  # {source_name: 新規保存数}
  ```

- 監査ログスキーマ初期化（監査専用 DB を別途用意する場合）
  ```python
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.duckdb")
  ```

- J-Quants ID トークン取得（テスト用など）
  ```python
  from kabusys.data.jquants_client import get_id_token
  token = get_id_token()  # Settings.jquants_refresh_token を使用
  ```

注意点：
- run_daily_etl 等の関数は内部で例外をハンドリングして結果を返しますが、settings の必須環境変数が未設定だと ValueError が発生します。
- logging レベルや出力先はアプリ側で設定してください（settings.log_level を参考にすることで設定の一貫性が取れます）。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                        -- 環境変数・設定自動ロード
    - data/
      - __init__.py
      - jquants_client.py              -- J-Quants API クライアント（取得 + 保存）
      - news_collector.py              -- RSS ニュース収集・前処理・保存
      - schema.py                      -- DuckDB スキーマ定義・初期化
      - pipeline.py                    -- ETL パイプライン（差分更新 / 品質チェック）
      - calendar_management.py         -- カレンダー管理（営業日判定等）
      - audit.py                       -- 監査ログ用スキーマ初期化
      - quality.py                     -- データ品質チェック
    - strategy/
      - __init__.py                    -- 戦略関連（拡張ポイント）
    - execution/
      - __init__.py                    -- 発注/約定管理（拡張ポイント）
    - monitoring/
      - __init__.py                    -- 監視用モジュール（拡張ポイント）

---

## 実装上の注意 / トラブルシューティング

- .env の自動読み込み
  - プロジェクトルートは __file__ を起点に親ディレクトリで `.git` または `pyproject.toml` を探して決定します。見つからない場合、自動ロードはスキップされます。
  - 読み込み順: OS 環境変数 > .env.local > .env
  - 自動ロードを無効化する場合:
    - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

- 環境変数不足エラー
  - Settings の必須プロパティ（JQUANTS_REFRESH_TOKEN など）が未設定だとアクセス時に ValueError が発生します。実行前に .env 等で必須設定を入れてください。

- J-Quants API 呼び出し
  - レート制限（120 req/min）に従うため内部でスロットリングします。大量のページネーションで遅くなる点に注意してください。
  - 401 受信時は自動でリフレッシュし 1 回だけリトライします。
  - リトライ対象は 408/429/5xx 等の一部です（最大 3 回）。

- ニュース収集
  - XML パースに defusedxml を使用して XML ボム等の攻撃を防いでいます。
  - 最大受信サイズを制限（デフォルト 10MB）してメモリ DoS を防止。
  - リダイレクト先のプライベート IP（SSRF）を検出してブロックします。

- DuckDB 操作
  - init_schema() は冪等で、存在しない親ディレクトリは自動作成します。
  - save_* 関数は ON CONFLICT 句で重複を吸収するように設計されています。

---

## 開発・拡張ポイント

- strategy/ や execution/ ディレクトリは拡張ポイントです。戦略ロジックや注文実行ロジックはここに実装してください。
- 監査・実行まわりは data.audit と data.schema に土台があります。発注ブリッジ（kabu API 連携等）を実装し audit テーブルへ書き込むことでトレーサビリティを確保できます。
- 品質チェック（data.quality）は SQL ベースで拡張できます。新しいチェックを追加して run_all_checks に組み込んでください。

---

この README はコードベースに含まれるモジュール実装に基づいて作成しています。より具体的な運用手順（CI/CD、コンテナ化、運用監視、SLA等）は利用環境に合わせて追記してください。必要であればサンプルの .env.example、requirements.txt、簡単な CLI/Makefile の追加例も作成できます。必要なら指示してください。