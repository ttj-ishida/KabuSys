# KabuSys

KabuSys は日本株向けの自動売買・データプラットフォームのコアライブラリです。  
主に以下の機能を提供します：データ取得（J-Quants）、ETL / ニュース収集、特徴量生成、シグナル生成、バックテスト、バックエンド用の DuckDB スキーマなど。

この README はリポジトリ内のコード（src/kabusys 以下）を元にした概要、セットアップ、使い方、ディレクトリ構成の説明です。

主な設計方針（抜粋）
- ルックアヘッドバイアス回避のため「target_date 時点で利用可能なデータのみ」を使う
- DuckDB をデータストアとして利用し、冪等な保存（ON CONFLICT 等）を行う
- ETL・HTTP 周りはリトライ・レート制御・セキュリティ対策（SSRF・XML 防御等）を組み込む
- バックテストは本番 DB を汚さないためにインメモリ接続へデータをコピーして実行する

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API クライアント（ページネーション、トークンリフレッシュ、リトライ、レートリミット）
  - news_collector: RSS からニュース取得・前処理・DB保存（SSRF 防御、gzip 対応、トラッキング除去）
  - schema: DuckDB のテーブル定義と初期化（raw / processed / feature / execution 層）
  - stats: 汎用的な統計ユーティリティ（Zスコア正規化など）
  - pipeline: ETL の差分更新ロジックと結果レポート（ETLResult）
- research/
  - factor_research: Momentum / Volatility / Value 等のファクター計算（prices_daily / raw_financials を参照）
  - feature_exploration: 将来リターン計算、IC（Spearman）計算、ファクターサマリ
- strategy/
  - feature_engineering: research の生ファクターを正規化・フィルタして features テーブルへ保存
  - signal_generator: features と ai_scores を統合して final_score を計算、BUY/SELL シグナルを生成し signals テーブルへ保存
- backtest/
  - engine: バックテスト全体フロー（DBコピー → 日次ループ → generate_signals 呼び出し → 約定シミュ）
  - simulator: ポートフォリオシミュレータ（スリッページ・手数料モデル・約定ログ）
  - metrics: バックテスト結果指標（CAGR, Sharpe, MaxDD, WinRate 等）
  - run: CLI エントリポイント（python -m kabusys.backtest.run）
- config.py
  - .env 自動読み込み（プロジェクトルートを検索）、環境変数経由で設定を取得する Settings（必須・任意を明示）
  - 自動 .env 読み込みを無効化する: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## 必要条件 / 推奨環境

- Python 3.10 以上（| 型表記を使用しているため）
- 主要依存ライブラリ（例、最低限）
  - duckdb
  - defusedxml

（実際の requirements はプロジェクトの packaging によります。上記はコードで直接参照されているライブラリです）

---

## 環境変数（主なもの）

必須 (Settings._require により未設定だとエラーになる)
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
- KABU_API_PASSWORD : kabuステーション API パスワード（execution 層で使用想定）
- SLACK_BOT_TOKEN : Slack 通知用トークン
- SLACK_CHANNEL_ID : Slack チャネル ID

任意 / デフォルトあり
- KABUSYS_ENV : development | paper_trading | live （デフォルト：development）
- LOG_LEVEL : DEBUG|INFO|... （デフォルト：INFO）
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト：data/kabusys.duckdb）
- SQLITE_PATH : SQLite（monitoring 用）パス（デフォルト：data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD : 1 にすると .env の自動ロードを無効化

.env の読み込み挙動
- プロジェクトルートを .git または pyproject.toml を基準に探索して .env / .env.local を読み込みます
- OS 環境変数が優先され、.env.local は .env を上書きします

---

## セットアップ手順（ローカル開発向け）

1. Python 仮想環境作成（例）
   - python -m venv .venv
   - source .venv/bin/activate（Windows: .venv\Scripts\activate）

2. 依存ライブラリのインストール
   - pip install duckdb defusedxml
   - その他プロジェクトで必要なパッケージがあれば追加でインストールしてください

3. プロジェクトルートに .env を用意
   - .env.example を参照して以下を設定（最低限必須のトークン等を設定）
     - JQUANTS_REFRESH_TOKEN=...
     - SLACK_BOT_TOKEN=...
     - SLACK_CHANNEL_ID=...
     - KABU_API_PASSWORD=...
   - テスト時に自動読み込みを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

4. DuckDB スキーマ初期化
   - Python から:
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
   - CLI でバックテストを実行するときはコード内で init_schema を呼んでいますが、事前に init_schema を実行して DB ファイルを作ると安全です。

---

## 使い方（主要ユースケース）

以下は代表的な操作例です。各関数はモジュール API として呼び出せます。

1) DuckDB スキーマ初期化
- Python:
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")

- in-memory（テスト用）:
  conn = init_schema(":memory:")

2) J-Quants からデータ取得→保存（ETL）
- 直接 jquants_client を使う例:
  from kabusys.data import jquants_client as jq
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")
  recs = jq.fetch_daily_quotes(date_from=..., date_to=..., id_token=None)
  jq.save_daily_quotes(conn, recs)

- pipeline を使う（差分取得、品質チェックの仕組みを利用）:
  from kabusys.data.pipeline import run_prices_etl
  result = run_prices_etl(conn, target_date=date.today())

3) ニュース収集
- RSS フェッチから保存:
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  conn = init_schema("data/kabusys.duckdb")
  known_codes = {"7203", "6758", ...}  # optional
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)

4) 特徴量生成（features テーブル）
- build_features を使って特定日分を生成して保存:
  from kabusys.strategy import build_features
  conn = init_schema("data/kabusys.duckdb")
  count = build_features(conn, target_date=date(2024, 1, 31))
  # 戻り値は upsert した銘柄数

5) シグナル生成（signals テーブル）
- generate_signals を呼んで date のシグナルを生成:
  from kabusys.strategy import generate_signals
  total = generate_signals(conn, target_date=date(2024,1,31), threshold=0.6)
  # 戻り値は書き込んだシグナル数（BUY + SELL）

6) バックテスト（CLI）
- コマンド例:
  python -m kabusys.backtest.run \
    --start 2023-01-01 --end 2023-12-31 \
    --cash 10000000 --db data/kabusys.duckdb

- またはプログラムから:
  from kabusys.backtest.engine import run_backtest
  result = run_backtest(conn, start_date, end_date)

7) バックテストの内部挙動
- run_backtest は本番 DB の必要テーブルを日付範囲でコピーしてインメモリ DuckDB を作り、
  日次で generate_signals を呼び、PortfolioSimulator で約定・評価を行います。
- 最終的に BacktestResult (history, trades, metrics) を返します。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py
- data/
  - __init__.py
  - jquants_client.py
  - news_collector.py
  - schema.py
  - stats.py
  - pipeline.py
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
  - clock.py
  - run.py
- execution/  (空の __init__ が含まれる、execution 層の拡張点)
- monitoring/  (モニタリング関連は将来的に実装想定)

（上記は README に記載された主要モジュール一覧です。詳細は各モジュールの docstring を参照してください）

---

## 補足・運用メモ

- 環境変数の自動ロードは config._find_project_root() でプロジェクトルートを探索して .env / .env.local を読み込みます。テストや CI では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを無効化できます。
- J-Quants API 呼び出しは内部でレート制御（120 req/min）とリトライ、401 時のリフレッシュを実装しています。ID トークンはモジュールレベルでキャッシュされます。
- news_collector は SSRF・XML bomb・gzip などのセキュリティ・堅牢性対策を盛り込んでいます。
- DuckDB スキーマは init_schema() で冪等に作成されます。":memory:" を使えばテスト用に軽量な in-memory DB が利用できます。
- signal_generator / feature_engineering / research の関数はルックアヘッドバイアス対策として target_date 時点のデータのみ参照することが設計方針として明示されています。

---

## 参照

- 各モジュールの先頭にある docstring（コード内コメント）を参照すると、設計仕様（StrategyModel.md / DataPlatform.md / BacktestFramework.md 等）に準拠した詳細が確認できます。
- 実運用にあたっては .env.example / デプロイ時のシークレット管理、DB バックアップ方針、モニタリング（Slack 通知等）の実装を合わせて検討してください。

---

README に記載の内容で不足や追記したい箇所（例: CI／テスト、具体的な依存バージョン、実行例スクリプト）などがあれば教えてください。必要に応じて README を更新します。