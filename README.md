# KabuSys

KabuSys は日本株向けの自動売買プラットフォーム向けに設計された Python モジュール群です。  
データ取得（J-Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、マーケットカレンダー管理、監査ログ/実行レイヤのスキーマ等を含む、研究→運用までを想定したスタックを提供します。

主な設計方針：
- ルックアヘッドバイアスを避ける（各処理は target_date 時点のデータのみを使用）
- DuckDB を単一の分析 DB として採用し、冪等な保存を重視（ON CONFLICT / トランザクション）
- 外部 API 呼び出しは明示的に分離し、再利用可能なクライアント（jquants_client）として提供
- セキュリティ考慮（RSS の SSRF 対策、XML パーサーの安全化 等）
- 本番/ペーパー/開発の環境フラグ対応（KABUSYS_ENV）

---

## 機能一覧

- データ取得
  - J-Quants API クライアント（株価日足、財務、マーケットカレンダー）
  - レート制限・リトライ・トークン自動リフレッシュ対応
- ETL パイプライン
  - 差分取得（バックフィル対応）、保存、品質チェックの実行（run_daily_etl 等）
- スキーマ管理
  - DuckDB のスキーマ初期化 / 接続ユーティリティ（init_schema / get_connection）
  - Raw / Processed / Feature / Execution の多層スキーマ
- 特徴量（feature）計算
  - momentum / volatility / value の計算（research モジュール）
  - Z スコア正規化、ユニバースフィルタ適用、features テーブルへの保存
- シグナル生成
  - features と ai_scores を統合して final_score を計算、BUY/SELL シグナルを生成・保存
  - Bear レジーム抑制・ストップロス等のエグジットロジック搭載
- ニュース収集
  - RSS フィード取得・前処理（URL 除去/正規化）・raw_news 保存・銘柄抽出
  - SSRF/サイズ制限/XML インジェクション対策
- マーケットカレンダー管理
  - JPX カレンダー差分取得、営業日判定・次/前営業日の取得等
- 監査ログ（audit）
  - signal → order_request → execution のトレーサビリティテーブル群（監査用）

---

## セットアップ手順

前提
- Python 3.10+（型ヒントに union 型などを使用）
- DuckDB（Python パッケージ）
- ネットワークから J-Quants 等へアクセスできること

1. ソースのインストール（プロジェクトルートで）
   - 開発インストール例:
     - pip install -e .
   - 依存パッケージ（例）:
     - pip install duckdb defusedxml

2. 環境変数 / .env の設定
   - プロジェクトルートに `.env`（または `.env.local`）を置くと自動で読み込まれます（自動ロードはデフォルト有効）。
   - 自動ロードを無効化する場合:
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を環境変数に設定
   - 必須環境変数（最低限）:
     - JQUANTS_REFRESH_TOKEN=: J-Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD=: kabuステーション API のパスワード（発注連携が必要な場合）
     - SLACK_BOT_TOKEN=: Slack 通知用 Bot トークン（必要に応じて）
     - SLACK_CHANNEL_ID=: 通知先チャンネル ID（必要に応じて）
   - 任意 / デフォルト値あり:
     - KABUSYS_ENV=: development / paper_trading / live（デフォルト development）
     - KABU_API_BASE_URL=: kabu API の base URL（デフォルト http://localhost:18080/kabusapi）
     - DUCKDB_PATH=: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH=: 監視 DB（デフォルト data/monitoring.db）
     - LOG_LEVEL=: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）
   - サンプル .env 内容例:
     - JQUANTS_REFRESH_TOKEN=xxxx
     - KABU_API_PASSWORD=secret
     - SLACK_BOT_TOKEN=xoxb-...
     - SLACK_CHANNEL_ID=C01234567
     - DUCKDB_PATH=data/kabusys.duckdb
     - KABUSYS_ENV=development

3. DuckDB スキーマ初期化
   - Python REPL / スクリプトで実行:
     - from kabusys.data.schema import init_schema
     - conn = init_schema("data/kabusys.duckdb")
   - ":memory:" を指定するとインメモリ DB になります（テスト用）。

---

## 使い方（代表的な例）

以下は最小構成のサンプルコード例。実運用ではログ設定・例外処理等を追加してください。

- DuckDB 接続 & スキーマ初期化
  - from kabusys.data.schema import init_schema, get_connection
  - conn = init_schema("data/kabusys.duckdb")

- 日次 ETL 実行（市場カレンダー・株価・財務データの差分取得）
  - from kabusys.data.pipeline import run_daily_etl
  - result = run_daily_etl(conn)  # デフォルトは今日を対象日とする
  - print(result.to_dict())

- 特徴量構築（target_date 分を features テーブルに UPSERT）
  - from kabusys.strategy import build_features
  - from datetime import date
  - n = build_features(conn, date(2024, 1, 31))
  - print(f"features upserted: {n}")

- シグナル生成（features/ai_scores/positions を参照して signals を作成）
  - from kabusys.strategy import generate_signals
  - from datetime import date
  - total = generate_signals(conn, date(2024, 1, 31), threshold=0.60)
  - print(f"signals written: {total}")

- ニュース収集ジョブ（RSS 収集・raw_news 登録・銘柄紐付け）
  - from kabusys.data.news_collector import run_news_collection
  - known_codes = {"7203", "6758", "2914", ...}  # 事前に有効銘柄セットを用意
  - results = run_news_collection(conn, known_codes=known_codes)
  - print(results)

- カレンダー更新ジョブ（夜間バッチ）
  - from kabusys.data.calendar_management import calendar_update_job
  - saved = calendar_update_job(conn)
  - print(f"calendar saved: {saved}")

- J-Quants API 直接利用（テスト・デバッグ）
  - from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
  - token = get_id_token()  # settings.jquants_refresh_token を使用して取得
  - quotes = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))

---

## 主要モジュールと API の説明（抜粋）

- kabusys.config
  - settings オブジェクトで環境変数を参照。必須キー未設定時は ValueError を送出。
  - 自動でプロジェクトルートの .env/.env.local を読み込む（必要に応じて無効化可）。

- kabusys.data.jquants_client
  - J-Quants との通信、ページネーション対応、保存ユーティリティ（save_daily_quotes 等）。

- kabusys.data.schema
  - init_schema(db_path) で DuckDB の全テーブルを作成（冪等）。
  - get_connection(db_path) で既存 DB へ接続（初回は init_schema を推奨）。

- kabusys.data.pipeline
  - run_daily_etl(conn, ...) : 日次 ETL の統合エントリポイント。品質チェックを含む。

- kabusys.research / kabusys.strategy
  - calc_momentum / calc_volatility / calc_value: ファクター計算
  - build_features: ファクターの正規化・ユニバースフィルタ・features への保存
  - generate_signals: features と ai_scores を統合して signals を作成

- kabusys.data.news_collector
  - fetch_rss / save_raw_news / run_news_collection: RSS 取得→DB 保存→銘柄紐付け

- kabusys.data.calendar_management
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days
  - calendar_update_job: JPX カレンダー更新ジョブ

---

## ディレクトリ構成（主要ファイル）

以下は `src/kabusys` 配下の主要モジュールの抜粋です。

- kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py
    - news_collector.py
    - schema.py
    - stats.py
    - pipeline.py
    - features.py
    - calendar_management.py
    - audit.py
    - pipeline.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - strategy/
    - __init__.py
    - feature_engineering.py
    - signal_generator.py
  - execution/  (発注層は拡張ポイント)
    - __init__.py
  - monitoring/  (監視関連: sqlite 等を想定)
    - (モジュールを追加予定)

※ 実際のリポジトリではさらにドキュメント（DataPlatform.md, StrategyModel.md 等）や CLI スクリプトが存在する想定です。

---

## ロギング / 環境モード

- KABUSYS_ENV は以下の値を受け付けます:
  - development, paper_trading, live
- LOG_LEVEL は標準的なログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）
- settings.is_live / is_paper / is_dev で挙動分岐が可能

---

## セキュリティ / 運用上の注意

- .env やシークレットは Git 管理に含めないこと。
- J-Quants トークンはリフレッシュトークンが必要。トークン管理は慎重に行ってください。
- RSS 取得は外部 URL を開くため SSRF 対策やサイズ制限を組み込んでいますが、運用時はソースの管理と検証を行ってください。
- 実際に発注を行う execution 層は外部のブローカー API と統合する必要があります（kabuステーション等）。設定ミスで実売買を発生させないよう注意してください（paper_trading モードの利用推奨）。

---

## 貢献 / 拡張ポイント

- execution 層（ブローカー連携）の実装（kabu API、証券会社 SDK）
- ai_scores を生成するモデルの統合（学習/推論パイプライン）
- 監視ダッシュボード・アラート（SQLite / Prometheus 統合など）
- 単体テスト・CI ワークフローの追加

---

不明点や README に追加したい具体的な利用シナリオ（例: cron での日次実行、Kubernetes ジョブ化、Slack 通知のサンプル等）があれば教えてください。必要に応じて README を拡張します。