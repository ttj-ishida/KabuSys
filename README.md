# KabuSys

KabuSys は日本株向けのデータプラットフォームと自動売買（ストラテジ・シグナル生成）を統合したライブラリです。  
DuckDB をデータストアとして用い、J-Quants API からのデータ取得、ETL、特徴量生成、シグナル生成、ニュース収集、監査ログなどをモジュール化して提供します。

主な目的は「研究→本番」までのワークフローを再現できるように、ルックアヘッドバイアス対策・冪等性（idempotency）・監査性を重視した実装を行うことです。

対応 Python バージョン: 3.10 以上（型注釈で PEP 604 の `|` を使用）

---

## 機能一覧

- データ取得
  - J-Quants API クライアント（株価日足、財務データ、マーケットカレンダー）
  - レート制限・リトライ・トークン自動リフレッシュ対応
- ETL / データパイプライン
  - 差分更新（バックフィル対応）、品質チェックフレームワークとの連携
  - 日次 ETL エントリポイント（run_daily_etl）
- データスキーマ
  - DuckDB 上に Raw / Processed / Feature / Execution 層のスキーマ定義と初期化（init_schema）
- 特徴量計算（Research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算（prices_daily / raw_financials を参照）
  - クロスセクション Z スコア正規化ユーティリティ
- 戦略（Strategy）
  - 特徴量の合成・正規化（build_features）
  - 最終スコア計算と BUY/SELL シグナル生成（generate_signals）
  - Bear レジーム抑制やエグジット（ストップロス等）判定を実装
- ニュース収集
  - RSS フィード取得・前処理・raw_news 保存、銘柄コード抽出・紐付け
  - SSRF 対策、XML 攻撃対策、受信サイズ制限などセキュリティ設計
- 監査 / トレーサビリティ
  - シグナル→発注→約定までの監査テーブル定義（order_request の冪等キー等）
- ユーティリティ
  - マーケットカレンダー管理（営業日判定、next/prev trading day 等）
  - ロギングレベル設定など環境設定管理

---

## セットアップ手順

1. リポジトリをチェックアウト（任意）

   git clone <your-repo-url>
   cd <your-repo>

2. Python 仮想環境を作成・有効化（推奨）

   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows

3. 必要パッケージをインストール

   pip install duckdb defusedxml

   （プロジェクトで requirements.txt / pyproject.toml があればそちらを利用してください）

4. 環境変数の設定

   このプロジェクトは複数の必須環境変数を参照します。`.env` または OS 環境変数で設定してください。自動でプロジェクトルートの `.env` → `.env.local` を読み込みます（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能）。

   主要な環境変数（最低限これらは必須）:

   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
   - KABU_API_BASE_URL: kabuステーション API のベース URL（省略可、デフォルト: http://localhost:18080/kabusapi）
   - SLACK_BOT_TOKEN: 通知用 Slack Bot トークン（必須）
   - SLACK_CHANNEL_ID: 通知先チャネル ID（必須）
   - DUCKDB_PATH: DuckDB ファイルのパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite のパス（デフォルト: data/monitoring.db）
   - KABUSYS_ENV: 実行環境 (development|paper_trading|live)。デフォルト: development
   - LOG_LEVEL: ログレベル (DEBUG|INFO|WARNING|ERROR|CRITICAL)。デフォルト: INFO

   例 .env:

   ```
   JQUANTS_REFRESH_TOKEN=xxxx...
   KABU_API_PASSWORD=secret
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=DEBUG
   ```

5. スキーマ初期化（DuckDB の作成）

   Python REPL やスクリプトで:

   from kabusys.data.schema import init_schema
   from kabusys.config import settings
   conn = init_schema(settings.duckdb_path)

   これにより `data/` 配下に DuckDB ファイルが作成され、必要テーブルがすべて作られます。

---

## 使い方（主要なワークフロー例）

以下は基本的な利用例です。環境変数は事前に設定している前提です。

- スキーマ初期化

  from kabusys.data.schema import init_schema
  from kabusys.config import settings
  conn = init_schema(settings.duckdb_path)

- 日次 ETL を実行（市場カレンダー、株価、財務、品質チェック）

  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn)
  print(result.to_dict())

- 特徴量（features）を構築（戦略用）

  from kabusys.strategy import build_features
  from datetime import date
  count = build_features(conn, date(2024, 1, 31))
  print(f"features upserted: {count}")

- シグナル生成（signals テーブルに書き込む）

  from kabusys.strategy import generate_signals
  from datetime import date
  total = generate_signals(conn, date(2024, 1, 31))
  print(f"signals generated: {total}")

  生成時に重みや閾値を変更したい場合はオプション引数を指定できます。

- ニュース収集ジョブを実行

  from kabusys.data.news_collector import run_news_collection
  from kabusys.config import settings
  known_codes = {"7203", "6758", ...}  # 有効な銘柄コードリスト
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)

- カレンダー更新ジョブ（夜間バッチ想定）

  from kabusys.data.calendar_management import calendar_update_job
  saved = calendar_update_job(conn)
  print(f"saved calendar rows: {saved}")

注意:
- J-Quants クライアントは 120 req/min のレート制限に対応しています（内部でスロットリング）。大量の並列リクエストは避けてください。
- API 呼び出しは retry/backoff と 401 時の自動トークン更新を実装しています。
- ETL/保存は冪等性を意識して実装（ON CONFLICT や upsert を利用）。

---

## ディレクトリ構成（主要ファイル）

（パッケージルート: src/kabusys/）

- kabusys/
  - __init__.py
  - config.py
    - 環境変数管理（自動 .env ロード、必須チェック）
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（取得・保存関数を提供）
    - schema.py
      - DuckDB スキーマ定義と init_schema / get_connection
    - pipeline.py
      - ETL パイプライン（run_daily_etl 等）
    - stats.py
      - zscore_normalize 等の統計ユーティリティ
    - features.py
      - zscore_normalize の再エクスポート
    - news_collector.py
      - RSS 収集・保存・銘柄抽出
    - calendar_management.py
      - マーケットカレンダー管理（営業日判定、更新ジョブ）
    - audit.py
      - 監査ログ（signal_events / order_requests / executions 等）
    - (他: quality モジュール想定・外部参照)
  - research/
    - __init__.py
    - factor_research.py
      - momentum/volatility/value のファクター計算
    - feature_exploration.py
      - 将来リターン / IC / 統計サマリー等の研究向け分析ツール
  - strategy/
    - __init__.py
    - feature_engineering.py
      - build_features（raw factors を正規化して features に保存）
    - signal_generator.py
      - generate_signals（features + ai_scores から final_score を計算し signals を生成）
  - execution/
    - __init__.py
    - （発注/実行管理モジュールを配置想定）
  - monitoring/
    - （監視・アラート関連モジュールを配置想定）

各モジュールには docstring で設計方針や処理フローが明記されています。実際の運用では schema.init_schema → data.pipeline.run_daily_etl → strategy.build_features → strategy.generate_signals → execution 層（発注） の流れになります。

---

## 注意点 / 設計上の考慮

- ルックアヘッドバイアス防止:
  - 特徴量・シグナル生成は "target_date 時点でシステムが知り得るデータのみ" を使用するように設計されています。
  - 取得時刻 (fetched_at) を記録し、いつデータが得られたかをトレース可能にしています。
- 冪等性:
  - DB 保存は ON CONFLICT / upsert を活用して再実行可能にしています。
- セキュリティ:
  - news_collector は XML の脆弱性対策（defusedxml）、SSRF 対策、受信上限を実装しています。
- ロギング / モード:
  - KABUSYS_ENV による環境区分 (development / paper_trading / live) があり、運用上の挙動切替に利用できます。
- テスト:
  - モジュールは外部依存（HTTP / DB など）を引数注入可能に実装しており、ユニットテストが容易になるよう配慮されています（例: id_token を注入、_urlopen のモックなど）。

---

## よくある操作（CLI / スクリプト化のヒント）

- 定期実行（cron / Airflow）:
  - 夜間に calendar_update_job, run_daily_etl を実行し、その後 build_features → generate_signals を順次実行するワークフローを推奨します。
- 本番とテスト切替:
  - KABUSYS_ENV を `paper_trading` に設定して発注層をサンドボックス化する運用が可能です（発注層の実装による）。
- 環境変数の自動ロードを無効化したいテスト時:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動 .env 読み込みを抑制可能。

---

必要であれば README を実際のリポジトリに合わせて修正（依存関係や実行スクリプト、CI 設定、運用手順などの追加）します。追加したい項目があれば教えてください。