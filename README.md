# KabuSys

KabuSys は日本株向けの自動売買プラットフォーム向けライブラリ群です。  
データ収集（J-Quants）、ETL、特徴量計算、シグナル生成、ニュース収集、監査ログなどの主要機能をモジュール化して提供します。設計上、発注 API や実際の売買処理（execution 層）には直接依存しないため、研究・バックテスト・ペーパートレード・本番運用へ柔軟に適用できます。

バージョン: 0.1.0

---

## 概要

主な目的:
- J-Quants API からの株価・財務・カレンダーの差分取得（レート制限・リトライ・トークン自動更新に対応）
- DuckDB を用いた冪等なデータ保存とスキーマ管理
- 研究で作成したファクターを正規化し戦略の特徴量（features）を生成
- features と AI スコアを統合して売買シグナルを生成
- RSS ベースのニュース収集と銘柄紐付け（SSRF対策・サイズ制限などの安全機能付き）
- 監査ログ（signal → order → execution のトレーサビリティ）設計

設計上の特徴:
- idempotent（ON CONFLICT / DO UPDATE 等）で再実行可能
- ルックアヘッドバイアス対策（target_date 時点のデータのみ使用）
- 外部依存（pandas 等）を極力抑え標準ライブラリ中心
- テスト容易性を考慮したトークン注入や自動環境変数ロードの無効化オプション

---

## 主な機能一覧

- data/jquants_client.py
  - J-Quants API クライアント（レートリミット、リトライ、トークン自動更新）
  - fetch/save: 日足（daily_quotes）、財務（statements）、カレンダー
- data/schema.py
  - DuckDB のスキーマ定義と初期化（Raw / Processed / Feature / Execution 層）
  - init_schema(db_path) / get_connection(db_path)
- data/pipeline.py
  - 日次 ETL（run_daily_etl）：カレンダー → 株価 → 財務 → 品質チェック
  - 差分取得・バックフィルを考慮
- data/news_collector.py
  - RSS 取得、テキスト前処理、記事保存、銘柄抽出・紐付け（SSRF対策・gzip/size制限）
- data/calendar_management.py
  - market_calendar 管理、営業日判定、next/prev_trading_day、calendar_update_job
- data/audit.py
  - signal/order/execution の監査ログ用スキーマ（トレース可能な設計）
- data/stats.py
  - zscore_normalize（クロスセクション Z スコア正規化）
- research/*
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（Spearman）計算、統計サマリ
- strategy/feature_engineering.py
  - research で作成した raw factor をマージ・フィルタ・正規化し features テーブルに UPSERT
- strategy/signal_generator.py
  - features + ai_scores を統合して final_score を計算、BUY/SELL シグナルを作成し signals テーブルへ書き込み
- config.py
  - 環境変数管理（.env 自動読み込み、必要変数の検査、設定プロパティの提供）

---

## 必要な環境変数

以下は Settings で参照される主な環境変数（README の時点で使用されているもの）:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL (任意) — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH (任意) — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH (任意) — SQLite 監視 DB（デフォルト: data/monitoring.db）
- KABUSYS_ENV (任意) — 開発環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL (任意) — ログレベル: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

自動で .env/.env.local をプロジェクトルートから読み込みます。自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## セットアップ手順（ローカル開発向け）

前提:
- Python 3.8+（typing 拡張や型注釈の利用）
- pip、virtualenv 等

1. リポジトリをクローンしてワークディレクトリへ移動
2. 仮想環境を作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - duckdb は必須。requests は未使用（urllib ベース）、defusedxml が必要。
   - 例:
     - pip install duckdb defusedxml
   - プロジェクトに requirements.txt があればそれを使用してください。
4. 環境変数を準備
   - プロジェクトルートに .env または .env.local を作成し、上記の必須値を定義
   - 例 (.env):
     JQUANTS_REFRESH_TOKEN=your_refresh_token
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C12345678
     KABU_API_PASSWORD=...
5. DuckDB スキーマを初期化
   - Python REPL またはスクリプトから:
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
   - ":memory:" を渡すとインメモリ DB が使えます（テスト用）。

---

## 使い方（代表的なワークフロー）

ここでは Python API を直接呼び出す例を示します。プロジェクトに CLI がない場合はこれをラッパー化して運用するとよいです。

- DuckDB の初期化
  - python -c "from kabusys.data.schema import init_schema; init_schema('data/kabusys.duckdb')"

- 日次 ETL 実行
  - Python 例:
    from datetime import date
    from kabusys.data.schema import get_connection, init_schema
    from kabusys.data.pipeline import run_daily_etl
    conn = init_schema('data/kabusys.duckdb')  # 初回のみ
    result = run_daily_etl(conn, target_date=date.today())
    print(result.to_dict())

- 特徴量（features）構築
  - from kabusys.strategy import build_features
    from kabusys.data.schema import get_connection
    from datetime import date
    conn = get_connection('data/kabusys.duckdb')
    count = build_features(conn, date(2026, 3, 20))
    print(f"features upserted: {count}")

- シグナル生成
  - from kabusys.strategy import generate_signals
    conn = get_connection('data/kabusys.duckdb')
    n = generate_signals(conn, date(2026, 3, 20))
    print(f"signals generated: {n}")

- ニュース収集ジョブ
  - from kabusys.data.news_collector import run_news_collection
    conn = get_connection('data/kabusys.duckdb')
    results = run_news_collection(conn, sources=None, known_codes={'7203','6758'})
    print(results)

- カレンダー更新ジョブ
  - from kabusys.data.calendar_management import calendar_update_job
    conn = get_connection('data/kabusys.duckdb')
    saved = calendar_update_job(conn)
    print(f"calendar saved: {saved}")

注意点:
- run_daily_etl などは内部で独立したステップごとに例外処理を行い、可能な限り処理を継続します。戻り値（ETLResult）を確認して品質問題やエラーの有無を検査してください。
- 環境変数が未設定の必須項目は Settings のプロパティ呼び出し時に ValueError を送出します。

---

## 設計上の安全策・運用上の注意

- J-Quants API はレート制限（120 req/min）に従うよう実装済み（_RateLimiter）。
- API リクエストはリトライと指数バックオフを備え、401 ではトークン自動更新を行います。
- ニュース収集は SSRF 対策、レスポンスサイズ制限（10MB）、Gzip 解凍後サイズチェック、defusedxml による XML 攻撃対策を実装しています。
- DB 操作はトランザクションで囲み、UPSERT / ON CONFLICT を使って冪等性を担保しています。
- 本リポジトリの strategy 層は発注 API を直接呼ばない設計です（signals テーブル生成まで）。実際の発注は execution 層で安全に実装してください。

---

## トラブルシューティング

- 環境変数がない / 読み込めない:
  - settings のプロパティが ValueError を投げます。.env ファイルをプロジェクトルートに置くか、環境変数をエクスポートしてください。
  - 自動 .env 読み込みを無効化している場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を確認。
- duckdb が import できない:
  - pip install duckdb を実行してください（環境によってはビルドが必要）。
- ネットワークエラー／API エラー:
  - jquants_client はリトライするが、継続的な 4xx-5xx が出る場合はトークンやパラメータを確認してください。
- RSS 取得で記事が取り込めない:
  - フィードのスキーム（http/https）やレスポンスサイズ、XML 構文エラーをログで確認してください。

---

## ディレクトリ構成（主要ファイル）

リポジトリ内の src/kabusys 配下を中心に記載します。

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数・設定管理（.env 自動読み込み、Settings クラス）
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（fetch/save, レート制限, リトライ）
    - news_collector.py
      - RSS 取得・前処理・raw_news 保存・銘柄抽出
    - schema.py
      - DuckDB スキーマ定義・init_schema / get_connection
    - pipeline.py
      - ETL パイプライン（run_daily_etl 等）
    - features.py
      - zscore_normalize の再エクスポート
    - calendar_management.py
      - market_calendar 管理・営業日ロジック・calendar_update_job
    - audit.py
      - 監査ログスキーマ（signal_events / order_requests / executions）
    - stats.py
      - zscore_normalize 等の統計ユーティリティ
  - research/
    - __init__.py
    - factor_research.py
      - momentum / volatility / value のファクター計算
    - feature_exploration.py
      - 将来リターン、IC、統計サマリ
  - strategy/
    - __init__.py
    - feature_engineering.py
      - features テーブル構築（normalization / filtering / UPSERT）
    - signal_generator.py
      - final_score 計算・BUY/SELL シグナル生成・signals 保存
  - execution/
    - __init__.py
    - （発注・注文処理はここに実装される想定 / 現状空）
  - monitoring/
    - （監視系モジュールを想定。今回のスナップショットでは詳細なし）

---

## 最後に

この README はコードベースの主要機能と利用方法の要点をまとめたものです。運用時はログ・監査出力・品質チェックの結果を必ず確認し、発注ロジックはサンドボックス環境やペーパートレードで十分に検証してから本番投入してください。必要であれば実運用向けの CLI やジョブラッパー（systemd / cron / Airflow 等）を追加してください。

不明点や追加ドキュメント（DataPlatform.md / StrategyModel.md 等参照箇所）の補完が必要であればお知らせください。