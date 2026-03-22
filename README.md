# KabuSys

日本株向けの自動売買 / 研究プラットフォーム（モジュール群）のリポジトリ。  
データ取得・ETL、特徴量生成、シグナル生成、バックテスト、ニュース収集、DuckDB スキーマ等を含む設計済みのライブラリ群です。

主な設計方針
- ルックアヘッドバイアスの排除（target_date 時点のデータのみを使用）
- DuckDB をデータストアに採用（オンディスク / インメモリどちらも可）
- 冪等性（ON CONFLICT / トランザクション）を重視
- 外部 API 呼び出しや I/O は明示的に行い、内部ロジックは純粋関数的に分離

---

## 機能一覧

- data
  - J-Quants API クライアント（fetch / save）: 株価日足、財務データ、マーケットカレンダー等の取得と DuckDB への保存（レートリミット・リトライ・トークン自動更新）
  - News RSS 収集器（RSS の正規化・前処理・SSRF / Gzip 制限・記事ID生成・DB 保存）
  - DuckDB スキーマ定義 / 初期化（init_schema）
  - ETL パイプライン（差分取得・バックフィル・品質チェック基盤）
  - 汎用統計ユーティリティ（Z スコア正規化等）
- research
  - ファクター計算（モメンタム、ボラティリティ、バリュー）
  - 将来リターン計算 / IC（スピアマン）計算 / ファクターサマリ
- strategy
  - feature_engineering: 生ファクターを正規化・フィルタして `features` テーブルへ書き込み
  - signal_generator: features / ai_scores / positions を統合して BUY/SELL シグナルを生成し `signals` テーブルへ書き込み
- backtest
  - PortfolioSimulator（擬似約定モデル、スリッページ / 手数料考慮）
  - バックテストエンジン（本番 DB からインメモリ DB へ必要データをコピーして日次ループでシミュレーション）
  - メトリクス計算（CAGR, Sharpe, MaxDrawdown, WinRate, PayoffRatio 等）
  - CLI エントリポイント（モジュール実行でバックテスト）
- execution / monitoring（発注 / モニタリング層のための基礎構造置き場）

---

## セットアップ手順

前提
- Python 3.10 以上（モダンな型ヒント（|）を使用）
- Git が使える環境（.env 自動検出に .git または pyproject.toml を使用）

1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージのインストール
   - 最小: duckdb, defusedxml
   - 例:
     pip install duckdb defusedxml

   - （任意）ローカル開発用にパッケージとしてインストール
     pip install -e .

4. 環境変数の準備
   - プロジェクトルートに `.env`（と必要なら `.env.local`）を置くと自動で読み込まれます。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
   - 必須環境変数（config.Settings により参照）
     - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD : kabuステーション API パスワード（execution 層で使用）
     - SLACK_BOT_TOKEN : Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID : 通知先チャンネル ID
   - 任意 / デフォルト
     - KABUSYS_ENV : development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL : DEBUG / INFO / ...（デフォルト: INFO）
     - DUCKDB_PATH : デフォルト data/kabusys.duckdb
     - SQLITE_PATH : デフォルト data/monitoring.db

   例 .env:
     JQUANTS_REFRESH_TOKEN=xxxx
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C12345678
     KABU_API_PASSWORD=your_password
     DUCKDB_PATH=data/kabusys.duckdb

5. DuckDB スキーマ初期化
   - Python REPL やスクリプトで:
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     conn.close()
   - これで必要テーブルが作成されます（冪等）。

---

## 使い方（主要ユースケース例）

1. DuckDB スキーマを初期化
   - Python:
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     conn.close()

2. J-Quants からデータを取得して保存（ETL）
   - 簡易例（株価差分 ETL）:
     from datetime import date
     import duckdb
     from kabusys.data.schema import init_schema
     from kabusys.data.pipeline import run_prices_etl

     conn = init_schema("data/kabusys.duckdb")
     # settings.jquants_refresh_token が設定されている前提
     fetched, saved = run_prices_etl(conn, target_date=date.today())
     conn.close()

   - News 収集:
     from kabusys.data.news_collector import run_news_collection
     conn = init_schema("data/kabusys.duckdb")
     known_codes = {"7203", "6758", ...}  # 任意
     results = run_news_collection(conn, known_codes=known_codes)
     conn.close()

   - 注意: pipeline 関数群は差分取得・backfill などのオプションを持つため、実運用では ETL スケジューラから呼ぶ前提です。

3. 特徴量生成（features テーブル作成）
   - Python:
     from datetime import date
     from kabusys.data.schema import init_schema
     from kabusys.strategy import build_features

     conn = init_schema("data/kabusys.duckdb")
     count = build_features(conn, target_date=date(2024, 1, 1))
     conn.close()

   - 目的: research の calc_* で計算した生ファクターを正規化・フィルタして features に保存します。

4. シグナル生成（signals テーブル作成）
   - Python:
     from datetime import date
     from kabusys.data.schema import init_schema
     from kabusys.strategy import generate_signals

     conn = init_schema("data/kabusys.duckdb")
     total = generate_signals(conn, target_date=date(2024, 1, 1))
     conn.close()

   - 生成された signals を execution 層に渡して実際の発注処理を行います（本リポジトリでは発注 API 呼び出しは別実装想定）。

5. バックテストの実行（CLI）
   - provided entrypoint:
     python -m kabusys.backtest.run \
       --start 2023-01-01 --end 2023-12-31 \
       --cash 10000000 --db data/kabusys.duckdb

   - あるいは Python から呼び出す:
     from datetime import date
     from kabusys.data.schema import init_schema
     from kabusys.backtest.engine import run_backtest

     conn = init_schema("data/kabusys.duckdb")
     result = run_backtest(conn, start_date=date(2023,1,1), end_date=date(2023,12,31))
     conn.close()
     # result.history, result.trades, result.metrics にアクセス可能

6. 開発・デバッグ
   - ログレベルは LOG_LEVEL 環境変数で制御（例: LOG_LEVEL=DEBUG）
   - テスト時に自動 .env ロードを抑止したい場合:
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## 主要モジュールの説明（簡易）

- kabusys.config
  - .env / .env.local 自動読み込み（プロジェクトルートの検出ロジックあり）
  - settings: 必須/任意の環境変数をプロパティとして提供

- kabusys.data.jquants_client
  - API レート制御、リトライ、401 トークン自動更新、ページネーション対応
  - fetch_* / save_* 関数でデータ取得から DuckDB 保存まで一貫

- kabusys.data.news_collector
  - RSS フィード収集、SSRF 対策、gzip / サイズ制限、記事正規化、ID 発行、DB 保存

- kabusys.data.schema
  - DuckDB スキーマ（raw / processed / feature / execution レイヤ）を定義する DDL を実行する init_schema

- kabusys.research
  - calc_momentum / calc_volatility / calc_value など、prices_daily/raw_financials を使ったファクター計算
  - calc_forward_returns, calc_ic, factor_summary など研究用ユーティリティ

- kabusys.strategy
  - build_features: 生ファクターをマージ → ユニバースフィルタ → 正規化 → features テーブルへ保存
  - generate_signals: features と ai_scores を統合し final_score を計算、BUY/SELL を signals に保存

- kabusys.backtest
  - run_backtest: 本番 DB からインメモリに必要テーブルをコピーして日次ループでシミュレーション
  - PortfolioSimulator: 約定ロジック（スリッページ / 手数料）と日次評価を提供
  - metrics: バックテスト評価指標を計算

---

## ディレクトリ構成

（抜粋。主要ファイルのみ列挙）

- src/
  - kabusys/
    - __init__.py
    - config.py
    - data/
      - __init__.py
      - jquants_client.py
      - news_collector.py
      - pipeline.py
      - schema.py
      - stats.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - strategy/
      - __init__.py
      - feature_engineering.py
      - signal_generator.py
    - backtest/
      - __init__.py
      - engine.py
      - simulator.py
      - metrics.py
      - run.py
      - clock.py
    - execution/
      - __init__.py
    - monitoring/
      - (実装場所)

---

## 注意事項 / 運用上のヒント

- DuckDB のファイルはバックアップを取ってください。init_schema は既存テーブルを上書きしませんが、ETL / 保存処理はデータを更新します。
- J-Quants のレート制限（120 req/min）や API トークンの管理に注意してください。トークンは settings.jquants_refresh_token によって自動で使用されます。
- news_collector は外部 URL を扱うため SSRF 対策やレスポンスサイズ制限を備えていますが、実運用では取得ソースの管理（ホワイトリスト）を行ってください。
- 本リポジトリは戦略のコアロジック（feature / signal / backtest）を提供しますが、実際の発注（kabuステーション等）との接続・運用は execution 層の拡張と慎重なテストが必要です。
- ローカル開発時に .env.local を利用して機密情報を分離すると便利です（.gitignore に追加推奨）。

---

もし README に追加したい内容（API リファレンス、CI/CD 手順、サンプルデータの作成方法、より詳細なコマンド例など）があれば教えてください。必要に応じて具体的な CLI スクリプト例やデプロイ手順も追記します。