# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリ群です。  
DuckDB をデータストアに用い、J‑Quants からマーケットデータを取得して ETL → 特徴量作成 → シグナル生成 → 実行（別モジュール想定）までのワークフローをサポートします。

主な設計方針:
- ルックアヘッドバイアス回避（計算は target_date 時点のデータのみ使用）
- DuckDB による冪等な保存（ON CONFLICT / トランザクション）
- ETL／収集処理は差分更新・バックフィル対応
- ネットワーク周りはレート制御、リトライ、SSRF/XML攻撃対策あり

## 機能一覧
- データ取得・保存
  - J‑Quants API クライアント（rate limiting、リトライ、トークン自動リフレッシュ）
  - raw_prices / raw_financials / market_calendar / raw_news などの保存関数
- ETL パイプライン
  - 日次 ETL（市場カレンダー、株価、財務データの差分取得と保存）
  - 個別 ETL ジョブ（prices / financials / calendar）
  - 品質チェック呼び出しフック（quality モジュール経由）
- カレンダー管理
  - 営業日判定、前後営業日の探索、カレンダーの夜間更新ジョブ
- ニュース収集
  - RSS フィード収集／前処理／記事ID生成／銘柄抽出／DB保存（SSRF対策・gzip上限など）
- リサーチ / ファクター計算
  - Momentum / Volatility / Value 等のファクター計算（prices_daily / raw_financials を参照）
  - 将来リターン計算、IC（Spearman）や統計サマリ関数
- 特徴量エンジニアリング
  - 生ファクターの統合、ユニバースフィルタ（最低株価・売買代金）、Z スコア正規化、features テーブルへの UPSERT
- シグナル生成
  - features と ai_scores を統合して final_score を算出
  - Bear レジームによる BUY 抑制、エグジット（SELL）判定、signals テーブルへ冪等書き込み
- スキーマ管理
  - DuckDB 用スキーマ初期化（init_schema）と接続取得ユーティリティ

## 必要条件 / 推奨環境
- Python 3.10+
- DuckDB（Python パッケージ: duckdb）
- defusedxml（RSS パースで安全化）
- 標準ライブラリの urllib 等を使用

実際の運用ではその他のライブラリ（ログ集約、Slack 通知、発注ライブラリ等）を追加する想定です。

## 環境変数（主なもの）
設定は .env / .env.local または OS 環境変数で行います。パッケージはプロジェクトルート（.git または pyproject.toml）を探して自動で .env を読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

必須:
- JQUANTS_REFRESH_TOKEN — J‑Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabu ステーション API のパスワード
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack 通知対象チャンネル ID

任意（デフォルト値あり）:
- KABUSYS_ENV — 環境 ("development" | "paper_trading" | "live")（デフォルト: development）
- LOG_LEVEL — ログレベル ("DEBUG" | "INFO" | ...)
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite ファイルパス（デフォルト: data/monitoring.db）

## セットアップ手順（例）
1. リポジトリをクローン:
   - git clone ... && cd repo

2. Python 仮想環境を作成・有効化:
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .\.venv\Scripts\activate)

3. 必要パッケージをインストール（例）:
   - pip install duckdb defusedxml

   （プロジェクトに requirements.txt / pyproject.toml があればそちらを利用）

4. 環境変数を用意:
   - プロジェクトルートに .env を作成する（.env.example を参考に）
   - 必須トークン類を設定（上記参照）

5. DuckDB スキーマ初期化:
   - Python スクリプトや REPL で以下を実行してデータベースを作成・テーブルを準備します。

   例:
   - python -c "from kabusys.data.schema import init_schema; init_schema('data/kabusys.duckdb')"

## 使い方（主要なワークフロー例）
以下はライブラリ API を使う最小例です。各関数は DuckDB の接続オブジェクト（duckdb.connect の戻り値）を受け取ります。

- DB を初期化して接続を取得:
  - from kabusys.data.schema import init_schema, get_connection
  - conn = init_schema('data/kabusys.duckdb')  # 初期化して接続
  - # 既存 DB に接続する場合: conn = get_connection('data/kabusys.duckdb')

- 日次 ETL を実行（J‑Quants トークンは環境変数経由で自動取得）:
  - from kabusys.data.pipeline import run_daily_etl
  - result = run_daily_etl(conn)  # 戻り値は ETLResult

- 特徴量を作成（target_date の features テーブル更新）:
  - from datetime import date
  - from kabusys.strategy import build_features
  - cnt = build_features(conn, date(2025, 1, 15))
  - print(f"features upserted: {cnt}")

- シグナル生成:
  - from kabusys.strategy import generate_signals
  - total = generate_signals(conn, date(2025, 1, 15))
  - print(f"signals generated: {total}")

- ニュース収集ジョブ（RSS）:
  - from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  - stats = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={'7203','6758'})
  - print(stats)

- カレンダー更新ジョブ:
  - from kabusys.data.calendar_management import calendar_update_job
  - saved = calendar_update_job(conn)
  - print(f"calendar saved: {saved}")

- J‑Quants からの直接フェッチ（テストや個別取得）:
  - from kabusys.data.jquants_client import fetch_daily_quotes, fetch_financial_statements
  - records = fetch_daily_quotes(code='7203', date_from=date(2024,1,1), date_to=date(2024,1,31))

注意:
- これらの処理は本 README 内の簡易例です。運用ではエラーハンドリング、ロギング、トークン管理、ジョブスケジューラ（cron/airflow 等）を組み合わせて使用してください。
- シグナルの実際の発注処理（execution 層）は本パッケージの別モジュールや外部サービスとして実装する必要があります。

## API の要点（抜粋）
- kabusys.config.settings — 環境変数を扱う設定オブジェクト
- kabusys.data.schema.init_schema(db_path) — DuckDB スキーマ作成
- kabusys.data.pipeline.run_daily_etl(conn, ...) — 日次 ETL のエントリポイント
- kabusys.data.jquants_client.* — fetch_*/save_* 系の取得・保存ユーティリティ
- kabusys.data.news_collector.run_news_collection(...) — RSS 収集と保存
- kabusys.research.* — factor 計算・解析ユーティリティ（calc_momentum, calc_value, calc_volatility, calc_forward_returns, calc_ic, factor_summary 等）
- kabusys.strategy.build_features(conn, target_date) — features テーブル構築
- kabusys.strategy.generate_signals(conn, target_date, threshold, weights) — signals 生成

## 推奨運用例（簡易）
- 毎朝（または取引日夜間）:
  - run_daily_etl を実行して prices / financials / calendar を更新し品質チェック
- ETL 後:
  - build_features を実行して特徴量を準備
  - generate_signals を実行して signals を更新
- 別ジョブ:
  - calendar_update_job を夜間に実行（カレンダー先読み）
  - run_news_collection を定期実行してニュースを収集・紐付け

ジョブは cron / systemd timer / Airflow などでスケジュールしてください。

## ディレクトリ構成（主要ファイル）
（src/kabusys 配下の主なモジュール）
- kabusys/
  - __init__.py
  - config.py — 環境変数読み込み・Settings
  - data/
    - __init__.py
    - jquants_client.py — J‑Quants API クライアント（fetch/save）
    - news_collector.py — RSS 収集・前処理・保存
    - schema.py — DuckDB スキーマ定義 & init_schema
    - stats.py — zscore_normalize 等の統計ユーティリティ
    - pipeline.py — ETL パイプライン（run_daily_etl など）
    - calendar_management.py — カレンダー管理・更新ジョブ
    - audit.py — 発注→約定トレーサビリティ用監査テーブル定義
    - features.py — features 用の公開インターフェース（再エクスポート）
  - research/
    - __init__.py
    - factor_research.py — Momentum/Volatility/Value の計算
    - feature_exploration.py — 将来リターン・IC・統計サマリ等
  - strategy/
    - __init__.py
    - feature_engineering.py — 生ファクター整形→features テーブル
    - signal_generator.py — final_score 計算と signals 生成
  - execution/ — 発注/実行層（空 or 実装予定）
  - monitoring/ — 監視用モジュール（実装ファイルが追加される想定）

## 開発者向けメモ・注意点
- 自動で .env を読み込みますが、CI やユニットテスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動読み込みを無効化可能です。
- DuckDB スキーマ定義は多数の制約・INDEX を含みます。初回 init_schema は時間がかかる場合があります。
- jquants_client のネットワークリクエストは rate limiting（120 req/min）とリトライを備えます。ローカルテスト時はモック化を検討してください。
- news_collector は外部 RSS を扱うため SSRF と XML 攻撃に対する防御策が組み込まれています。
- Strategy の重みや閾値は generate_signals の引数で上書き可能ですが、合計が 1.0 になるよう再スケールされます。

---

さらに詳しい設計仕様（StrategyModel.md / DataPlatform.md / DataSchema.md 等）や運用手順は、プロジェクトの設計文書を参照してください。README に記載の内容はコードベース上で主要な使い方と構造を簡潔にまとめたものです。質問やサンプル実行スクリプトが必要であれば教えてください。