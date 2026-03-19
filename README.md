# KabuSys

KabuSys は日本株向けの自動売買プラットフォーム向けライブラリ群です。データ取得（J-Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、マーケットカレンダー管理、監査ログなどの機能を提供し、DuckDB をデータストアとして利用する設計になっています。

主な設計方針：
- ルックアヘッドバイアス防止（target_date 時点のデータのみ使用）
- 冪等性（DB への保存は ON CONFLICT で上書き等）
- テスト容易性（トークン注入、環境変数自動ロードの無効化など）
- 外部依存は最小限（標準ライブラリ中心、DuckDB・defusedxml 等を使用）

---

## 機能一覧

- データ取得
  - J-Quants API クライアント（株価日足、四半期財務、マーケットカレンダー）
  - レート制御・リトライ・トークン自動リフレッシュ対応
- データ保存・スキーマ
  - DuckDB スキーマ定義と初期化（raw / processed / feature / execution 層）
  - 冪等保存関数（raw_prices, raw_financials, market_calendar, raw_news 等）
- ETL パイプライン
  - run_daily_etl による日次差分 ETL（calendar → prices → financials → 品質チェック）
  - 差分再取得（backfill）・営業日補正対応
- 特徴量（Feature）
  - factor_research: momentum / volatility / value 等のファクター計算
  - feature_engineering: ファクター正規化（Zスコア）・ユニバースフィルタ・features テーブルへの保存
  - data.stats: zscore_normalize（再利用可能な統計ユーティリティ）
- シグナル生成
  - signal_generator: features + ai_scores を統合して final_score を計算、BUY/SELL シグナルを生成して signals テーブルへ保存
  - 売買ルール（閾値、重み、Bear レジーム判定、ストップロス等）を実装
- ニュース収集
  - RSS 収集（SSRF 対策、gzip 上限、XML セキュリティ、トラッキングパラメータ除去）
  - raw_news / news_symbols への冪等保存
  - 銘柄コード抽出（4桁コード）
- マーケットカレンダー管理
  - カレンダー更新ジョブ、営業日判定 API（next/prev/get_trading_days/is_trading_day/is_sq_day）
- 監査ログ（audit）
  - signal_events / order_requests / executions 等の監査用テーブル定義（トレーサビリティ）

---

## セットアップ手順

前提
- Python 3.9+（typing の一部構文を利用）
- DuckDB を利用（Python パッケージ duckdb）
- defusedxml（RSS XML パースのため）

1. リポジトリをクローン / コピー後、仮想環境を用意してアクティベートします。
   - 例:
     python -m venv .venv
     source .venv/bin/activate

2. 必要なパッケージをインストールします（最低限）:
   - pip install duckdb defusedxml

   （プロジェクトに requirements.txt/pyproject.toml がある場合はそちらに従ってください）

3. 環境変数を設定します。
   - プロジェクトルートに `.env`（または `.env.local`）を作成して次のキーを設定してください（必須は下記参照）。
   - 自動読み込みは kabusys.config モジュールがプロジェクトルート（.git または pyproject.toml）を検出して行います。テスト等で自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須の環境変数（少なくとも実行する機能に応じて設定してください）
- JQUANTS_REFRESH_TOKEN — J-Quants 用リフレッシュトークン（データ取得に必須）
- KABU_API_PASSWORD — kabu ステーション API のパスワード（execution 層使用時）
- SLACK_BOT_TOKEN — Slack 通知を使う場合
- SLACK_CHANNEL_ID — Slack のチャンネル ID

任意（デフォルト値あり）
- KABUSYS_ENV — 環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB 等（デフォルト: data/monitoring.db）

`.env` の例（簡易）
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

4. DuckDB スキーマの初期化
   - Python REPL やスクリプトで初期化します（デフォルトの DB パスを使う場合、上の DUCKDB_PATH を設定しておくと便利）。
   - 例:
     from kabusys.data.schema import init_schema, get_connection
     from kabusys.config import settings
     conn = init_schema(settings.duckdb_path)
     # またはメモリ DB
     # conn = init_schema(":memory:")

---

## 使い方（主要 API 例）

以下は典型的な運用フローのサンプルです。各関数はモジュール単体でも呼べます。

1) 日次 ETL 実行（市場カレンダー・株価・財務・品質チェック）
   from datetime import date
   from kabusys.data.schema import init_schema
   from kabusys.data.pipeline import run_daily_etl
   from kabusys.config import settings

   conn = init_schema(settings.duckdb_path)
   result = run_daily_etl(conn, target_date=date.today())
   print(result.to_dict())

2) 特徴量ビルド（features テーブルへの保存）
   from datetime import date
   from kabusys.data.schema import get_connection, init_schema
   from kabusys.strategy import build_features
   from kabusys.config import settings

   conn = init_schema(settings.duckdb_path)
   count = build_features(conn, target_date=date(2024, 1, 31))
   print(f"features upserted: {count}")

3) シグナル生成（signals テーブルへ保存）
   from datetime import date
   from kabusys.strategy import generate_signals
   from kabusys.data.schema import init_schema
   from kabusys.config import settings

   conn = init_schema(settings.duckdb_path)
   total_signals = generate_signals(conn, target_date=date(2024, 1, 31))
   print(f"signals written: {total_signals}")

   - 生成時に重みや閾値を引数で調整できます:
     generate_signals(conn, target_date, threshold=0.65, weights={"momentum":0.5, "value":0.2, ...})

4) ニュース収集ジョブ
   from kabusys.data.news_collector import run_news_collection
   from kabusys.data.schema import init_schema
   from kabusys.config import settings

   conn = init_schema(settings.duckdb_path)
   known_codes = {"7203", "6758", ...}  # 既知銘柄セットを渡すと紐付けを行う
   results = run_news_collection(conn, known_codes=known_codes)
   print(results)  # {source_name: saved_count, ...}

5) カレンダー更新ジョブ（夜間バッチ）
   from kabusys.data.calendar_management import calendar_update_job
   conn = init_schema(settings.duckdb_path)
   saved = calendar_update_job(conn)
   print("saved calendar rows:", saved)

注意:
- J-Quants API 呼び出しはレート制限およびリトライ・トークン自動更新を組み込んでいます。大量取得や自動化時は API 利用規約とレート制御に注意してください。
- signal_generator / feature_engineering は DuckDB 接続を受け取り、外部発注 API には依存しません（execution 層は別実装）。

---

## 実装上のポイント / 注意点

- 環境変数の自動ロード
  - kabusys.config はプロジェクトルート（.git または pyproject.toml）を起点に .env を自動読み込みします。読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
- DuckDB スキーマは init_schema() で一括作成され、冪等です（既存テーブルはスキップ）。
- ファクター正規化は zscore_normalize を利用し、std が極小の場合は正規化をスキップする安全策があります。
- ニュース収集では SSRF対策、gzip サイズ検査、defusedxml による XML セキュリティ、トラッキングパラメータ除去、ID は正規化 URL の SHA-256 で生成する等の対策を実装しています。
- signal_generator は AI スコア（ai_scores）や regime 判定を取り込みます。AI スコアが未登録でも中立補完されます。
- 多くの DB 書き込み処理はトランザクションで囲まれ、失敗時はロールバックして安全性を担保します。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py                        — 環境変数 / 設定管理
- data/
  - __init__.py
  - jquants_client.py              — J-Quants API クライアント + 保存関数
  - news_collector.py              — RSS ニュース収集と保存
  - schema.py                      — DuckDB スキーマ定義 / init_schema
  - stats.py                       — zscore_normalize 等統計ユーティリティ
  - pipeline.py                    — ETL パイプライン（run_daily_etl 等）
  - calendar_management.py         — カレンダー管理 / 更新ジョブ
  - audit.py                       — 監査ログ用スキーマ（signal_events 等）
  - features.py                    — zscore_normalize の再エクスポート
- research/
  - __init__.py
  - factor_research.py             — momentum / volatility / value ファクター計算
  - feature_exploration.py         — 将来リターン / IC / 統計サマリ
- strategy/
  - __init__.py
  - feature_engineering.py         — features の構築（正規化・フィルタ）
  - signal_generator.py            — final_score 計算と signals 生成
- execution/                        — 発注関連（パッケージ用空ディレクトリ。実装を追加可能）
- monitoring/                       — 監視用（実装を追加可能）

---

## ライセンス / 貢献

- 本リポジトリにはライセンス情報ファイル（LICENSE）が存在する前提です。利用前にライセンスを確認してください。
- バグ報告や機能追加提案は Issue を通じてお願いします。PR の際はテスト・ドキュメントを同梱してください。

---

README の記載は実装の抜粋に基づいて要点をまとめたものです。より詳細な仕様（StrategyModel.md / DataPlatform.md / Research ドキュメント等）がリポジトリに含まれている場合はそちらも参照してください。必要であれば README に利用例スクリプトや CLI 例（スケジューリング例、systemd / cron ジョブのテンプレート等）を追記します。どの追加情報が必要か教えてください。