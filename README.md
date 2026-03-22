# KabuSys — 日本株自動売買システム

※この README はリポジトリ内のソースコードを元に作成しています。  
（実装内の docstring / コメントを要約・整理しています）

---

## プロジェクト概要

KabuSys は日本株向けのデータパイプライン・特徴量エンジニアリング、シグナル生成、バックテスト、およびニュース収集を統合した自動売買基盤です。  
主に以下の層で構成されています：

- Data Layer（J-Quants からのデータ取得、DuckDB に保存）
- Feature Layer（ファクター計算・正規化・features テーブル）
- Strategy Layer（シグナル計算・BUY / SELL 判定）
- Backtest（ポートフォリオシミュレータ、評価指標）
- News Collection（RSS 収集と銘柄紐付け）
- Execution（発注管理のための DB スキーマ等、将来的な実注文層）

設計方針の例：
- ルックアヘッドバイアスを防ぐため、常に target_date 時点までのデータのみを使用。
- DuckDB をメイン DB とし、ETL は冪等（ON CONFLICT / UPSERT）で実装。
- ネットワーク処理は慎重に（レート制限、リトライ、SSRF 対策等）。

---

## 主な機能一覧

- J-Quants API クライアント（取得・保存・トークンリフレッシュ・レート制御）
  - 日足（OHLCV）、財務データ、JPX カレンダーの取得
- ETL パイプライン（差分取得・品質チェック）
- DuckDB スキーマ初期化（init_schema）
- ファクター計算（momentum / volatility / value）
- クロスセクション Z スコア正規化
- 特徴量の構築（features テーブルへ UPSERT）
- シグナル生成（feature + AI スコア統合 → BUY / SELL）
  - Bear レジーム抑制、ストップロス等のエグジット条件
- バックテストエンジン（シミュレータ、スリッページ・手数料モデル）
  - 日次ループで signals → 約定 → ポートフォリオ評価
  - 主要メトリクス（CAGR, Sharpe, MaxDD, WinRate, PayoffRatio）
- ニュース収集（RSS 取得・前処理・記事保存・銘柄抽出）
  - URL 正規化、トラッキング除去、SSRF 対策、gzip 除去、XML 安全パーサ
- DuckDB ベースの Execution テーブル群（signals, orders, trades, positions 等）

---

## 動作要件（概略）

- Python 3.10+（typing などの利用を考慮）
- duckdb
- defusedxml（RSS パース用）
- ネットワーク接続（J-Quants API / RSS）

（実際の環境では pyproject.toml / requirements を参照してください）

---

## セットアップ手順

1. リポジトリをクローンしてワークディレクトリへ移動
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. Python 仮想環境の作成（例）
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

3. 必要パッケージのインストール
   - pip でプロジェクトを編集可能インストールする:
     ```bash
     pip install -e .
     ```
   - もし requirements.txt / pyproject がある場合はそちらを利用してください:
     ```bash
     pip install duckdb defusedxml
     ```

4. DuckDB スキーマ初期化（デフォルト DB パスは settings.duckdb_path）
   Python REPL またはスクリプトで：
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   conn.close()
   ```

5. 環境変数（.env）を用意する
   - プロジェクトルートに .env / .env.local を置くと自動で読み込まれます（必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須の環境変数（コード中で _require されているもの）:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD — kabuステーション API パスワード（実行層と連携する場合）
     - SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（通知を使う場合）
     - SLACK_CHANNEL_ID — Slack チャンネル ID
   - その他オプション:
     - KABUSYS_ENV (development | paper_trading | live), default=development
     - LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL), default=INFO
     - DUCKDB_PATH（settings.duckdb_path の上書き）
     - SQLITE_PATH（monitoring 用）

---

## 環境変数一覧（主要）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants 用リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu API のパスワード
- KABUSYS_ENV — 動作モード (development / paper_trading / live)
- LOG_LEVEL — ログレベル
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID — Slack 通知に使用
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — SQLite パス（監視用）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env 読み込みを無効化する場合に "1" を設定

---

## 使い方（代表的な例）

以下はライブラリ関数や CLI を使ったワークフローの例です。

1. DuckDB スキーマの初期化（再掲）
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   ```

2. J-Quants から日足を差分取得して保存（pipeline 例）
   - pipeline.run_prices_etl 等の関数が提供されています（詳細は pipeline モジュールを参照）。
   - 例（簡略）:
     ```python
     from kabusys.data.pipeline import run_prices_etl
     # conn は init_schema で初期化済みの connection
     fetched_count, saved_count = run_prices_etl(conn, target_date=date.today())
     ```

3. 特徴量構築（features テーブルへ日付単位で置換）
   ```python
   from datetime import date
   from kabusys.strategy import build_features

   count = build_features(conn, target_date=date(2024, 03, 01))
   print(f"upserted features: {count}")
   ```

4. シグナル生成
   ```python
   from kabusys.strategy import generate_signals
   from datetime import date

   total = generate_signals(conn, target_date=date(2024, 03, 01))
   print(f"signals written: {total}")
   ```

5. ニュース収集ジョブ（RSS）
   ```python
   from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

   known_codes = {"6758", "7203", "9432"}  # 例: 有効銘柄セット
   results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
   print(results)
   ```

6. バックテスト（Python API）
   ```python
   from datetime import date
   from kabusys.backtest.engine import run_backtest

   res = run_backtest(conn, start_date=date(2023,1,1), end_date=date(2023,12,31))
   print(res.metrics)
   ```

7. バックテスト CLI
   - モジュールとして実行可能：
     ```bash
     python -m kabusys.backtest.run \
       --start 2023-01-01 --end 2023-12-31 \
       --cash 10000000 --db data/kabusys.duckdb
     ```
   - 出力は CAGR / Sharpe / Max Drawdown / Win Rate / Payoff Ratio / Total Trades を表示します。

---

## よく使うモジュール（概要）

- kabusys.config — 環境変数 / 設定管理
- kabusys.data.jquants_client — J-Quants API クライアント / 保存ヘルパ
- kabusys.data.news_collector — RSS 取得 / raw_news 保存 / 銘柄抽出
- kabusys.data.schema — DuckDB スキーマ定義・初期化
- kabusys.data.pipeline — ETL の差分実行ロジック
- kabusys.research.* — 研究用ファクター計算・解析ユーティリティ
- kabusys.strategy.* — build_features / generate_signals（戦略ロジック）
- kabusys.backtest.* — バックテストエンジン・シミュレータ・メトリクス

---

## ディレクトリ構成（主要ファイル）

（リポジトリの src/kabusys 以下を抜粋）

- src/kabusys/
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
    - clock.py
    - run.py  (CLI entrypoint)
  - execution/ (発注層のプレースホルダ)
  - monitoring/ (監視用 DB など、実装はプロジェクトによる)

（各モジュールは README 内の「主な機能一覧」や docstring を参照してください）

---

## 開発・テストに関する注意点

- .env の自動ロードは config.py によりプロジェクトルート（.git または pyproject.toml）を基準に行われます。テスト時に自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB に対してスキーマ初期化を行うとテーブルが作成されます。バックテストでは init_schema(":memory:") を使ってインメモリ DB を作り、実 DB を汚染しないようにしています。
- ネットワーク呼び出し（J-Quants、RSS）にはレート制限・リトライ・SSRF 対策が組み込まれていますが、実運用では API 利用制限や認証トークン管理に注意してください。

---

## 参考・追加情報

- ソースコード中の docstring に詳細なアルゴリズム説明（StrategyModel, BacktestFramework, DataPlatform 参照箇所）があります。実装の細かな挙動や数値はコード中の定数・コメントを参照してください。
- 実運用でリアル注文を行う場合は execution 層（kabu API 連携）および監視・アラートを十分に整備してください。

---

もし README に加えて .env.example、起動スクリプト、または具体的な ETL バッチ例（cron/systemd ユニット）を追加したい場合は要望をください。必要に応じてサンプル .env や運用手順を追記します。