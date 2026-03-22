# KabuSys

KabuSys は日本株のデータ取得・特徴量生成・シグナル生成・バックテスト・ニュース収集を一貫して行う自動売買／リサーチ向けライブラリです。DuckDB をデータストアとして利用し、J-Quants API や RSS フィードからデータを取得して ETL → 特徴量化 → シグナル生成 → バックテストというワークフローを提供します。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 機能一覧
- 要件
- セットアップ手順
- 環境変数
- 使い方（主要ユースケース）
- ディレクトリ構成（主要ファイル説明）
- ライセンス・貢献

---

## プロジェクト概要

KabuSys は以下を目的とした内部／研究用ライブラリです。

- J-Quants からの株価・財務・カレンダー取得（差分取得、リトライ、レート制御）
- RSS ベースのニュース収集と記事→銘柄の紐付け
- DuckDB によるスキーマ管理（Raw / Processed / Feature / Execution 層）
- 研究用のファクター計算（モメンタム・バリュー・ボラティリティ等）
- 特徴量の正規化（Zスコア）と features テーブルへの保存
- features と AI スコアを統合してシグナル（BUY/SELL）を生成
- バックテストフレームワーク（シミュレータ／評価指標）
- ニュース収集ジョブのエンドツーエンド処理

設計方針として、ルックアヘッドバイアスの回避、冪等性（idempotency）、エラーハンドリング（リトライ/トランザクション）を重視しています。

---

## 機能一覧

主な機能（モジュール別）

- kabusys.config
  - 環境変数読み込み（.env / .env.local 自動読み込み）と設定アクセス
- kabusys.data.jquants_client
  - J-Quants API クライアント（レート制御、リトライ、トークン自動更新）
  - 保存用の idempotent な save_* 関数（raw_prices, raw_financials, market_calendar 等）
- kabusys.data.news_collector
  - RSS フィード取得（SSRF防止・gzip制御・XMLパース安全化）
  - raw_news / news_symbols への冪等保存
- kabusys.data.schema
  - DuckDB のスキーマ定義と初期化（Raw / Processed / Feature / Execution 層）
- kabusys.research
  - ファクター計算（calc_momentum, calc_volatility, calc_value）
  - 解析ユーティリティ（calc_forward_returns, calc_ic, factor_summary）
- kabusys.strategy
  - build_features: 生ファクターの正規化と features 保存
  - generate_signals: features と ai_scores を統合して BUY/SELL 生成
- kabusys.backtest
  - run_backtest: インメモリ DB を用いた日次バックテストループ
  - PortfolioSimulator: 約定・スリッページ・手数料モデルを含む擬似約定
  - metrics: CAGR, Sharpe, MaxDD, WinRate, PayoffRatio などを計算

---

## 要件

必須ランタイム / ライブラリ（主要なもの）

- Python 3.10 以上（型ヒントに union 型等を使用）
- duckdb
- defusedxml

その他は標準ライブラリで実装されています。プロジェクト配布時に pyproject.toml / requirements.txt がある場合はそれに従ってください。

---

## セットアップ手順

1. リポジトリをクローン（例）
   - git clone <リポジトリURL>
2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install --upgrade pip
   - pip install duckdb defusedxml
   - （プロジェクトに pyproject.toml や requirements.txt がある場合）
     - pip install -r requirements.txt
     - または pip install -e .
4. データベース初期化（DuckDB スキーマ）
   - Python REPL / スクリプトで以下を実行:
     from kabusys.data.schema import init_schema
     init_schema("data/kabusys.duckdb")
   - デフォルトのパスは .env や環境変数で設定できます（デフォルト: data/kabusys.duckdb）
5. 環境変数設定
   - プロジェクトルートに .env または .env.local を置くと自動で読み込まれます（詳しくは次節）
   - 自動ロードを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します

---

## 環境変数

config.Settings により読み込まれる主要変数:

必須:
- JQUANTS_REFRESH_TOKEN
  - J-Quants のリフレッシュトークン（fetch・token 取得に使用）
- KABU_API_PASSWORD
  - kabuステーション等の API パスワード（execution 層で使用）
- SLACK_BOT_TOKEN
  - Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID
  - Slack 通知先チャンネル ID

任意 / デフォルトあり:
- KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- KABUSYS_ENV (development | paper_trading | live) (default: development)
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) (default: INFO)

.env ファイルの自動読み込み順:
- OS 環境変数 > .env.local > .env
- プロジェクトルートは .git または pyproject.toml の存在で判定

注意:
- 必須環境変数が未設定の場合、settings.<property> 呼び出し時に ValueError が発生します。

---

## 使い方

ここでは主要なユースケースの実行例を示します。

1) DuckDB スキーマ初期化（1回だけ）
- コマンドライン / Python:
  python -c "from kabusys.data.schema import init_schema; init_schema('data/kabusys.duckdb')"

2) J-Quants からデータ取得 → 保存（ETL）
- ETL パイプラインの個別関数を使えます（例: run_prices_etl）
- 例（Python スクリプト）:
  from datetime import date
  import duckdb
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_prices_etl

  conn = init_schema('data/kabusys.duckdb')
  # target_date を指定して差分取得を実行
  fetched, saved = run_prices_etl(conn, target_date=date.today())
  conn.close()

  ※ ETLResult 構造体や run_news_collection なども利用可能です。

3) 特徴量の構築（build_features）
- features を生成して features テーブルへ保存:
  from datetime import date
  import duckdb
  from kabusys.strategy import build_features
  from kabusys.data.schema import init_schema

  conn = init_schema('data/kabusys.duckdb')
  n = build_features(conn, target_date=date(2024, 1, 31))
  conn.close()

4) シグナル生成（generate_signals）
- features & ai_scores をもとに signals テーブルへ書き込み:
  from datetime import date
  import duckdb
  from kabusys.strategy import generate_signals
  from kabusys.data.schema import init_schema

  conn = init_schema('data/kabusys.duckdb')
  total = generate_signals(conn, target_date=date(2024, 1, 31))
  conn.close()

5) バックテスト（CLI）
- パッケージに含まれるエントリポイントを使ってバックテストを実行できます。
  例:
    python -m kabusys.backtest.run \
      --start 2023-01-01 --end 2023-12-31 \
      --cash 10000000 --db data/kabusys.duckdb

- このコマンドは指定した DB（事前に prices_daily, features, ai_scores, market_regime, market_calendar が入力済みであることが前提）からデータを読み取り、インメモリ DB を構築して日次シミュレーションを行います。実行後は CAGR / Sharpe / MaxDD / Trades 等を出力します。

6) ニュース収集ジョブ
- RSS から記事を取得して保存 → 銘柄紐付け:
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  from kabusys.data.schema import init_schema

  conn = init_schema('data/kabusys.duckdb')
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={'7203','6758'})
  conn.close()

---

## 注意点 / 実運用での留意

- J-Quants API の認証トークンとレート制御（120 req/min）に従う必要があります。クライアントは自動でリトライ・トークン更新を行いますが、API 利用規約に従ってください。
- ETL は差分取得を想定しています。初回ロードはデータ量が大きくなるため注意。
- features / signals / positions 等のテーブルはバックテストで直接編集されるため、本番 DB をバックテストで上書きしないよう、run_backtest は本番 DB からインメモリにコピーして動作します。
- news_collector は外部ネットワークへアクセスするため SSRF 等の防御を行っていますが、実行環境のネットワークポリシーに注意してください。

---

## ディレクトリ構成（主要ファイル）

以下はソースの主要モジュール一覧と簡単な説明（プロジェクトルート: src/kabusys）:

- __init__.py
  - パッケージ初期化、export されたサブパッケージ指定
- config.py
  - 環境設定読み込み（.env 自動読み込み）、Settings クラス
- data/
  - jquants_client.py — J-Quants API クライアント（取得・保存関数）
  - news_collector.py — RSS 取得 → raw_news / news_symbols 保存
  - schema.py — DuckDB スキーマ定義と init_schema()
  - stats.py — zscore_normalize 等の統計ユーティリティ
  - pipeline.py — ETL 管理（差分取得、品質チェックフック等）
- research/
  - factor_research.py — モメンタム / バリュー / ボラティリティの計算
  - feature_exploration.py — forward returns / IC / summary 等の解析用関数
- strategy/
  - feature_engineering.py — ファクター正規化・features への書き込み
  - signal_generator.py — features と ai_scores を統合して signals を生成
- backtest/
  - engine.py — run_backtest（インメモリ構築・日次ループ）
  - simulator.py — PortfolioSimulator（擬似約定・history/trade 記録）
  - metrics.py — バックテスト評価指標
  - run.py — CLI エントリポイント
  - clock.py — SimulatedClock（将来拡張用）
- execution/ (暫定)
  - 発注・execution 層関連（実装の拡張を想定）

---

## 貢献・報告

バグ報告や機能提案は Issues を通じてお願いします。PR の際はテスト・型チェック・既存のコーディングスタイルに合わせてください。

---

## ライセンス

本リポジトリにライセンスファイルが含まれている場合はそれに従ってください。内部利用向けのテンプレート実装であり、実運用では監査・テスト・法的確認を行ってください。

---

必要ならば、README に追加してほしい使用例（具体的なスクリプト、CI/CD の流れ、運用手順等）を教えてください。