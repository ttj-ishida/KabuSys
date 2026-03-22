# KabuSys

KabuSys は日本株の自動売買基盤（データ収集・特徴量生成・シグナル生成・バックテスト・発注管理）を想定した Python パッケージです。DuckDB をデータ層に用い、J-Quants からのマーケットデータ取得や RSS ベースのニュース収集、戦略用の特徴量計算、シグナル生成、バックテスト機能を備えています。

主な設計方針：
- ルックアヘッドバイアスを避ける（target_date 時点のデータのみを使用）
- 冪等性（DB 書込みは ON CONFLICT / トランザクションで安全に）
- API レート制御・リトライ・トークン自動更新（J-Quants クライアント）
- ネットワーク安全対策（RSS 収集の SSRF 対策等）
- DuckDB 上に Raw / Processed / Feature / Execution 層を定義

---

## 機能一覧

- データ収集
  - J-Quants API クライアント（株価・財務・マーケットカレンダー）
    - レートリミット（120 req/min）対応、リトライ、ID トークン自動リフレッシュ
  - RSS ニュース収集（defusedxml による XML 安全処理、SSRF 対策、URL 正規化、銘柄抽出）
- ETL / パイプライン
  - 差分取得／バックフィル処理、品質チェック（品質判定は quality モジュールへ委譲）
- データスキーマ管理
  - DuckDB のスキーマ初期化（raw_prices, prices_daily, features, signals, positions ...）
- 研究（research）
  - ファクター計算（momentum / volatility / value）
  - 特徴量探索（forward returns / IC / summary）
  - Z スコア正規化ユーティリティ
- 戦略（strategy）
  - 特徴量構築（build_features）：raw ファクターの統合・ユニバースフィルタ・正規化・features テーブルへの upsert
  - シグナル生成（generate_signals）：features と ai_scores を統合して final_score を計算、BUY/SELL を signals テーブルに書き込み
- バックテスト（backtest）
  - ポートフォリオシミュレータ（擬似約定、スリッページ・手数料モデル）
  - 日次ループ実行（run_backtest）と結果メトリクス計算（CAGR, Sharpe, MaxDD, Win Rate, Payoff Ratio）
  - CLI エントリポイントがあり、期間指定で簡単にバックテスト可能
- ニュース・テキスト処理（news_collector）
  - RSS 取得 → raw_news へ登録 → 銘柄紐付け（news_symbols）

---

## セットアップ手順

前提
- Python 3.10 以上（型注釈に | 演算子を使用しているため）
- system に duckdb をインストール（pip で OK）

例（仮想環境を作る場合）:

1. 仮想環境を作成・有効化
   - python -m venv .venv
   - Windows: .venv\Scripts\activate
   - macOS/Linux: source .venv/bin/activate

2. 必要パッケージのインストール（最低限）
   - pip install duckdb defusedxml

   ※プロジェクトに requirements.txt がある場合はそれを使ってください。

3. DuckDB データベースの初期化（ファイル or :memory:）
   - Python REPL やスクリプト内で:
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")  # ディレクトリ自動作成
     conn.close()

4. 環境変数（.env）設定
   - プロジェクトルートに .env / .env.local を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必要な環境変数（主なもの）:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD: kabuステーション API 用パスワード（必須）
     - SLACK_BOT_TOKEN: Slack 通知用トークン（必須）
     - SLACK_CHANNEL_ID: Slack 通知先チャンネル（必須）
     - DUCKDB_PATH: デフォルト data/kabusys.duckdb（省略可）
     - SQLITE_PATH: デフォルト data/monitoring.db（省略可）
     - KABUSYS_ENV: development | paper_trading | live（デフォルト development）
     - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト INFO）

   - .env の書式は一般的な KEY=VAL、シングル/ダブルクォート・export プレフィックスにも対応します（config モジュール参照）。

---

## 使い方

以下は典型的なワークフロー例です。

1) スキーマ初期化（1 回）
- Python から:
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")
  conn.close()

2) データ取得 / ETL（株価・財務・カレンダー等）
- パイソンコードから差分 ETL を呼ぶ例:
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_prices_etl, run_news_collection

  conn = init_schema("data/kabusys.duckdb")
  # 株価取得（target_date は date オブジェクト）
  prices_fetched, prices_saved = run_prices_etl(conn, target_date)
  # ニュース取得（既知コード集合を渡すと自動で紐付け）
  results = run_news_collection(conn, known_codes={"7203","6758"})
  conn.close()

  ※run_prices_etl 等は id_token を注入可能（引数）でテストしやすく設計されています。

3) 特徴量構築 / シグナル生成
- 特徴量を構築:
  from kabusys.data.schema import init_schema
  from kabusys.strategy import build_features

  conn = init_schema("data/kabusys.duckdb")
  build_features(conn, target_date)
  conn.close()

- シグナル生成（features と ai_scores を参照して signals に追加）:
  from kabusys.strategy import generate_signals
  generate_signals(conn, target_date)

4) バックテスト
- CLI から:
  python -m kabusys.backtest.run --start 2023-01-01 --end 2023-12-31 --db data/kabusys.duckdb
- Python API から:
  from kabusys.data.schema import get_connection
  from kabusys.backtest.engine import run_backtest
  conn = get_connection("data/kabusys.duckdb")
  result = run_backtest(conn, start_date, end_date, initial_cash=10_000_000)
  conn.close()
  # result.metrics, result.history, result.trades を利用

5) ニュース収集ジョブ
- run_news_collection() を周期的に呼ぶことで raw_news / news_symbols を更新します。

注意点:
- generate_signals() / build_features() は target_date 時点の DB を参照して処理するため、ETL → features → generate_signals の順に行ってください。
- positions / signals テーブルはバックテストと本番で共有されるため、バックテスト時は run_backtest がインメモリ DB に必要データをコピーして実行します（本番 DB の signals を汚染しません）。

---

## 主要モジュール（抜粋）

- kabusys.config: 環境変数・設定管理（.env 自動読み込み、必須キーチェック、KABUSYS_ENV 等）
- kabusys.data
  - jquants_client.py: J-Quants API クライアント（レートリミット / リトライ / save_* 関数）
  - news_collector.py: RSS 取得・前処理・raw_news への保存・銘柄抽出
  - pipeline.py: ETL パイプラインの差分処理・ヘルパ群
  - schema.py: DuckDB スキーマ定義と init_schema()
  - stats.py: zscore_normalize 等の統計ユーティリティ
- kabusys.research: factor 計算・探索（calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic / factor_summary）
- kabusys.strategy:
  - feature_engineering.py: build_features
  - signal_generator.py: generate_signals
- kabusys.backtest:
  - engine.py: run_backtest（本番 DB からインメモリコピーしてバックテスト）
  - simulator.py: PortfolioSimulator（擬似約定・ポートフォリオ管理）
  - metrics.py: バックテストメトリクス計算
  - run.py: CLI エントリポイント

---

## ディレクトリ構成

主要ファイル・ディレクトリのツリー（抜粋）:

src/kabusys/
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
- execution/          (発注関連モジュールのためのパッケージ)
- monitoring/         (監視・監査ログ等のモジュール)

（上記はコードベースの主要コンポーネントを示しています。実際のリポジトリでは追加ファイルやドキュメントが存在する可能性があります。）

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants API のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用トークン
- SLACK_CHANNEL_ID (必須) — Slack 通知先チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — SQLite ファイルパス（デフォルト data/monitoring.db）
- KABUSYS_ENV — 環境 (development | paper_trading | live). デフォルト development
- LOG_LEVEL — ログレベル（DEBUG|INFO|...）。デフォルト INFO
- KABUSYS_DISABLE_AUTO_ENV_LOAD — "1" を設定すると .env 自動ロードを無効化

設定はプロジェクトルートの .env / .env.local に置くと自動で読み込まれます（config._find_project_root() により .git または pyproject.toml を起点に探索）。

---

## 開発上の注意 / 実運用での留意点

- API キーやトークンは必ず安全に管理し、リポジトリへコミットしないでください。
- 本番運用時は KABUSYS_ENV を適切に設定し、live モードでは特に発注ロジックのテストとフェイルセーフを用意してください。
- DuckDB のバックアップ・スナップショット運用を検討してください（破損・誤操作対策）。
- RSS 収集や API 呼び出しは外部ネットワークに依存するためリトライや監視を行ってください。
- このコードベースはモジュール単位での呼び出しを想定しているため、実運用ではジョブスケジューラ（cron / Airflow など）との連携を推奨します。

---

必要であれば README に実行例（具体的な Python スニペット）、.env.example のテンプレート、CI/CD 用の注意点、運用チェックリストなどを追記します。どの情報を追加したいか教えてください。