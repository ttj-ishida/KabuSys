# KabuSys

日本株向けの自動売買・データ基盤ライブラリ群です。  
DuckDB を用いたデータ格納・ETL、ファクター計算、シグナル生成、バックテストシミュレータ、ニュース収集などを含みます。

---

## プロジェクト概要

KabuSys は以下のレイヤーで構成されるアルゴリズムトレーディング基盤です。

- Data Layer（取得・Raw / Processed データ）: J-Quants API から株価・財務・市場カレンダーを取得し、DuckDB に保存
- Feature Layer（研究・戦略）: ファクター計算（モメンタム・ボラティリティ・バリュー等）、Z スコア正規化、features テーブルへの保存
- Strategy 層: features と AI スコアを統合して最終スコアを算出し BUY/SELL シグナルを生成
- Execution / Backtest 層: シグナルの約定シミュレーション、ポートフォリオ評価、バックテスト実行
- News Collection: RSS フィードからニュースを収集し、銘柄紐付けを行う

設計上のポイント：
- ルックアヘッドバイアス回避（計算は target_date 時点のデータのみを使用）
- DuckDB を中心とした冪等な保存（ON CONFLICT / トランザクション）
- ネットワーク周りはレート制御・リトライ・トークン自動更新対応
- 外部依存を最小化（内部で標準ライブラリ、duckdb、defusedxml 等を使用）

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API クライアント（ページネーション、レートリミット、リトライ、トークンリフレッシュ）
  - pipeline: 差分 ETL（差分取得、保存、品質チェック）
  - schema: DuckDB スキーマ作成・初期化（raw / processed / feature / execution レイヤーのテーブル）
  - news_collector: RSS 取得・前処理・DB保存・銘柄抽出
  - stats: Z スコア正規化など統計ユーティリティ
- research/
  - factor_research: モメンタム・ボラティリティ・バリュー等のファクター計算
  - feature_exploration: 将来リターン・IC 計算・統計サマリ
- strategy/
  - feature_engineering: 生ファクターの正規化・ユニバースフィルタ・features テーブルへの書き込み
  - signal_generator: features と ai_scores を統合して売買シグナルを生成
- backtest/
  - engine: 日次ループのバックテスト実行（in-memory コピーを作成して安全に実行）
  - simulator: 約定・ポートフォリオ状態のシミュレーション（スリッページ・手数料モデル）
  - metrics: バックテスト評価指標（CAGR, Sharpe, MaxDD, win rate 等）
  - run: CLI エントリポイント（python -m kabusys.backtest.run）
- config: 環境変数管理（.env 自動ロード、必須キー取得のユーティリティ）

---

## 必要な依存・動作環境（例）

- Python 3.9+
- duckdb
- defusedxml
- （標準ライブラリ: urllib, datetime, logging 等）
- ネットワーク接続（J-Quants API、RSS フィード取得時）

pip での最低インストール例:
pip install duckdb defusedxml

（プロジェクトに pyproject.toml / requirements.txt があればそちらを利用してください）

---

## セットアップ手順

1. リポジトリを取得（例）
   git clone <repo-url>
   cd <repo>

2. Python 仮想環境の作成（任意）
   python -m venv .venv
   source .venv/bin/activate

3. 必要パッケージをインストール
   pip install -e .   # 開発インストール（setup があれば）
   pip install duckdb defusedxml

4. 環境変数の設定
   プロジェクトルートに .env または .env.local を置くと自動読み込みされます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると無効化可能）。

   例: .env (テンプレート)
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_api_password
   KABU_API_BASE_URL=http://localhost:18080/kabusapi   # 任意
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development
   LOG_LEVEL=INFO

   注意: Settings のプロパティは必須のものを読み出すと未設定時に例外を投げます（JQUANTS_REFRESH_TOKEN 等）。

5. DuckDB スキーマ初期化
   Python REPL やスクリプトで初期化します:

   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   conn.close()

---

## 使い方（主要ワークフロー例）

以下は主要な操作例です。実運用にあたってはログ/監査・スケジュール（cron/airflow等）や監視の仕組みを組み合わせてください。

1) データ取得（ETL）
- prices（株価）差分 ETL の実行例（簡易）:

  from datetime import date
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_prices_etl

  conn = init_schema("data/kabusys.duckdb")
  res = run_prices_etl(conn, target_date=date.today())
  print(res)
  conn.close()

- ニュース収集（RSS）例:

  from kabusys.data.schema import init_schema
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

  conn = init_schema("data/kabusys.duckdb")
  known_codes = {"7203", "6758", ...}  # 既知の銘柄コードセット
  result = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
  conn.close()
  print(result)

2) 特徴量作成（features）
- feature_engineering.build_features を呼び出して features テーブルを更新:

  from datetime import date
  import duckdb
  from kabusys.strategy import build_features

  conn = duckdb.connect("data/kabusys.duckdb")
  count = build_features(conn, target_date=date(2024, 1, 31))
  print(f"upserted features: {count}")
  conn.close()

3) シグナル生成
- signal_generator.generate_signals を呼び出して signals テーブルに書き込む:

  from datetime import date
  import duckdb
  from kabusys.strategy import generate_signals

  conn = duckdb.connect("data/kabusys.duckdb")
  total = generate_signals(conn, target_date=date(2024, 1, 31))
  print(f"signals generated: {total}")
  conn.close()

4) バックテスト（CLI）
- 提供されている CLI でバックテストを実行できます:

  python -m kabusys.backtest.run \
      --start 2023-01-01 --end 2024-12-31 \
      --cash 10000000 --db data/kabusys.duckdb

  オプション:
  --start / --end : 開始・終了日 (YYYY-MM-DD)
  --cash : 初期資金 (JPY)
  --slippage / --commission : スリッページ・手数料率
  --max-position-pct : 1銘柄あたりの最大保有割合

5) バックテスト API から呼び出す（プログラム的実行）
  from kabusys.data.schema import init_schema
  from kabusys.backtest.engine import run_backtest

  conn = init_schema("data/kabusys.duckdb")
  result = run_backtest(conn, start_date, end_date, initial_cash=10_000_000)
  print(result.metrics)
  conn.close()

---

## 設定と環境変数

主な環境変数（settings で参照されるもの）:

- JQUANTS_REFRESH_TOKEN (必須) : J-Quants API のリフレッシュトークン
- KABU_API_PASSWORD (必須) : kabu ステーション API パスワード
- KABU_API_BASE_URL (省略可) : kabu API ベース URL (デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須) : Slack 通知用 Bot Token
- SLACK_CHANNEL_ID (必須) : Slack チャネル ID
- DUCKDB_PATH (省略可) : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH (省略可) : 監視などに使う SQLite のパス（デフォルト: data/monitoring.db）
- KABUSYS_ENV (省略可) : 実行環境 (development / paper_trading / live)
- LOG_LEVEL (省略可) : ログレベル (DEBUG/INFO/WARNING/ERROR/CRITICAL)

自動 .env 読み込み:
- プロジェクトルート（.git または pyproject.toml を基準）にある .env / .env.local を起点に自動で環境変数を読み込みます。
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードは無効化されます（テスト時に便利）。

settings の必須キーが未設定の場合、ValueError が発生します。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py                    # 環境変数管理（.env 自動読み込み）
- data/
  - __init__.py
  - jquants_client.py          # J-Quants API クライアント + 保存ユーティリティ
  - news_collector.py          # RSS 取得・前処理・保存
  - pipeline.py                # ETL パイプライン（差分取得・保存・品質チェック）
  - schema.py                  # DuckDB スキーマ初期化
  - stats.py                   # 統計ユーティリティ（zscore_normalize）
- research/
  - __init__.py
  - factor_research.py         # モメンタム / ボラティリティ / バリュー計算
  - feature_exploration.py     # 将来リターン・IC・要約統計
- strategy/
  - __init__.py
  - feature_engineering.py     # ファクター正規化・ユニバースフィルタ
  - signal_generator.py        # final_score 計算・BUY/SELL 生成
- backtest/
  - __init__.py
  - engine.py                  # バックテストエンジン
  - simulator.py               # 約定・ポートフォリオシミュレーション
  - metrics.py                 # バックテストメトリクス
  - run.py                     # CLI 実行エントリポイント
  - clock.py                   # 将来用の模擬時計
- execution/                    # 発注・execution 層（空ディレクトリがある想定）
- monitoring/                   # 監視関連（SQLite など）

---

## 注意点・トラブルシュート

- 環境変数の未設定: settings の必須プロパティ（例: JQUANTS_REFRESH_TOKEN）が未設定だと ValueError になります。 .env を作成するか、環境に設定してください。
- DuckDB スキーマ: 初回は init_schema() でテーブルを作成してください。既存 DB に接続する場合は get_connection() を使用します（init_schema は不要）。
- J-Quants API: レート制限（120 req/min）・リトライ・401 トークン更新を実装していますが、API 側の制限に注意してください。
- News Collector: RSS パース時に不正な XML や大きすぎるレスポンスがあるとスキップします（安全対策のため）。
- テスト用に自動 .env ロードを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 貢献・拡張のヒント

- execution 層: 実際の発注（kabu API）との接続は execution パッケージに実装する想定です。現状はバックテスト・シミュレーション中心の実装が整っています。
- モジュールごとに単体テストを用意すると保守が容易になります（特に jquants_client の HTTP リトライ・news_collector の SSRF 防御ロジック等）。
- backfill / スケジューラ: ETL を定期実行する際はスケジューラ（Airflow / cron / systemd timer 等）で pipeline.run_* を呼び出すと良いでしょう。

---

必要があれば README に「コマンド例」や「.env.example ファイル」などを追記します。どの箇所をより詳細に書きたいか教えてください。