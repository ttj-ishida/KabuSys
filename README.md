# KabuSys

KabuSys は日本株の自動売買・データ基盤・バックテストを目的とした軽量なフレームワークです。  
DuckDB を中心に、データ取得（J-Quants）、ETL、特徴量生成、シグナル生成、バックテスト用シミュレーションまでを含みます。

主な設計方針：
- ルックアヘッドバイアスを防ぐ（target_date 時点のデータのみ使用）
- DB 操作は冪等性（idempotent）を重視（ON CONFLICT 等）
- 外部依存は最小限（標準ライブラリ + 必要な一部ライブラリ）
- DuckDB を用いたローカル一枚DB設計（Raw / Processed / Feature / Execution 層）

---

## 機能一覧

- データ取得・保存
  - J-Quants API クライアント（差分取得、ページネーション、トークン自動更新、レート制御）
  - RSS ニュース収集（XML 安全パース、SSRF/プライベートアドレスチェック、トラッキングパラメータ除去）
  - DuckDB への冪等保存（raw_prices, raw_financials, market_calendar, raw_news 等）

- ETL / Pipeline
  - 差分取得（最終取得日からの差分＋backfill）
  - 品質チェック（別モジュール quality と連携する想定）
  - データ正規化 / スキーマ初期化

- 研究（research）
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（スピアマン）計算、ファクター統計サマリ
  - Z スコア正規化ユーティリティ

- 特徴量エンジニアリング（strategy.feature_engineering）
  - research の raw factor を取り込みユニバースフィルタ適用、正規化、features テーブルへ保存

- シグナル生成（strategy.signal_generator）
  - features と ai_scores を統合して final_score を計算
  - Bear レジーム判定、BUY/SELL シグナル生成、signals テーブルへ保存

- バックテスト（backtest）
  - インメモリでのバックテスト用 DB コピー
  - PortfolioSimulator（擬似約定、スリッページ・手数料モデル）
  - バックテストループ（シグナル生成 → 約定 → マークトゥマーケット）
  - パフォーマンス指標計算（CAGR, Sharpe, Max Drawdown, Win rate, Payoff ratio）
  - CLI エントリポイント（python -m kabusys.backtest.run）

- スキーマ管理
  - DuckDB 用のスキーマ初期化（init_schema）およびテーブル定義一式

---

## セットアップ手順

前提：
- Python 3.10 以上（型注釈に X | Y 構文を使用）
- DuckDB を利用可能な環境

推奨手順（ローカル開発）：

1. リポジトリをクローンし、開発用にインストール
   ```bash
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate
   pip install -U pip
   pip install duckdb defusedxml
   pip install -e .
   ```
   ※ packaging 情報が無い場合は `pip install -e .` が失敗することがあります。その場合は必要な依存（上記）を手動でインストールしてください。

2. 必要な環境変数を設定（.env をプロジェクトルートに作成）
   - 必須（本番/データ取得等で必要）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - 任意 / デフォルトあり
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト "development"
     - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — デフォルト "INFO"
     - DUCKDB_PATH — デフォルト `data/kabusys.duckdb`
     - SQLITE_PATH — デフォルト `data/monitoring.db`
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動で .env を読み込む仕組みを無効化できます（テスト用途）

   例 (.env)
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token_here
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   ```

3. DuckDB スキーマ初期化
   Python コンソールやスクリプトから初期化します:
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   conn.close()
   ```

---

## 使い方（主要ユースケース）

1. バックテスト実行（CLI）
   DuckDB に必要なテーブル（prices_daily, features, ai_scores, market_regime, market_calendar 等）が事前に存在することが前提です。

   実行例：
   ```bash
   python -m kabusys.backtest.run \
     --start 2023-01-01 --end 2023-12-31 \
     --cash 10000000 \
     --slippage 0.001 \
     --commission 0.00055 \
     --max-position-pct 0.20 \
     --db data/kabusys.duckdb
   ```

   出力としてバックテストの主要指標（CAGR、Sharpe、MaxDD、WinRate、Total Trades）が表示されます。

2. 特徴量の作成（features テーブルへの書き込み）
   DuckDB 接続を使って日次で特徴量を計算し features に UPSERT します。
   ```python
   import duckdb
   from datetime import date
   from kabusys.strategy import build_features

   conn = duckdb.connect("data/kabusys.duckdb")
   n = build_features(conn, target_date=date(2024, 1, 31))
   print(f"upserted {n} features")
   conn.close()
   ```

3. シグナル生成
   features と ai_scores、positions を参照して signals に BUY/SELL を生成します。
   ```python
   import duckdb
   from datetime import date
   from kabusys.strategy import generate_signals

   conn = duckdb.connect("data/kabusys.duckdb")
   count = generate_signals(conn, target_date=date(2024, 1, 31))
   print(f"generated {count} signals")
   conn.close()
   ```

4. J-Quants からのデータ取得と保存
   - 日足取得・保存例：
   ```python
   import duckdb
   from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes, get_id_token

   conn = duckdb.connect("data/kabusys.duckdb")
   token = get_id_token()  # settings から refresh token を使用
   records = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))
   saved = save_daily_quotes(conn, records)
   conn.close()
   ```

5. RSS ニュース収集と記事保存
   ```python
   import duckdb
   from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

   conn = duckdb.connect("data/kabusys.duckdb")
   # known_codes を渡すと記事と銘柄の紐付け（news_symbols）も行います。
   results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203","6758"})
   print(results)
   conn.close()
   ```

6. ETL（Pipeline）: 差分取得等
   data.pipeline モジュールには差分取得・保存ロジックが含まれます（run_prices_etl 等）。具体的な呼び出しは pipeline モジュールの API を参照して実行してください。

---

## ディレクトリ構成（主要ファイル）

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
  - metrics.py
  - simulator.py
  - clock.py
  - run.py  (バックテスト CLI)
- execution/
  - __init__.py  (発注関連モジュールはここに追加する想定)
- monitoring/
  - (モニタリング関連モジュールを配置する想定)

主要なモジュール説明：
- kabusys.config: 環境変数の自動ロード・管理。settings オブジェクト経由で設定取得。
- kabusys.data.schema: DuckDB のスキーマ初期化、テーブル定義一式。
- kabusys.data.jquants_client: J-Quants API クライアント・保存ユーティリティ。
- kabusys.data.news_collector: RSS 収集と raw_news 保存、銘柄抽出。
- kabusys.research: ファクター計算・分析用ユーティリティ群。
- kabusys.strategy: 特徴量作成・シグナル生成。
- kabusys.backtest: バックテストエンジンとシミュレータ、評価指標。

---

## 環境変数一覧（主なもの）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu ステーション API のパスワード（execution 層で利用想定）
- SLACK_BOT_TOKEN (必須) — Slack 通知用トークン
- SLACK_CHANNEL_ID (必須) — Slack 送信先チャンネル
- DUCKDB_PATH — デフォルト data/kabusys.duckdb
- SQLITE_PATH — 監視用途の SQLite DB（default data/monitoring.db）
- KABUSYS_ENV — 開発環境フラグ（development | paper_trading | live）
- LOG_LEVEL — ログレベル

.env ファイルはプロジェクトルートの .git または pyproject.toml を起点に自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD を設定すると自動ロードを無効化）。

---

## 開発・運用上の注意

- DuckDB のスキーマは init_schema による初期化が必須です。既存DBに対しては init_schema を一度だけ実行してください。
- J-Quants の API 制限（120 req/min）や 401 リフレッシュ処理、429 等のリトライが組み込まれていますが、運用時は rate limit とコストに注意してください。
- NewsCollector は外部 HTTP を扱うため、SSRF 対策や gzip サイズ上限など安全対策を実装しています。外部ソースの扱いには注意してください。
- シグナル生成・執行部分は設計上分離されています。実際の発注は execution 層に実装して安全に行ってください（paper_trading/live のフラグ管理等）。
- バックテスト時のスリッページ・手数料モデルは simulator にて定義されていますが、実運用では実際の取引コストに合わせて調整してください。

---

必要に応じて README にサンプル .env.example、より詳細な ETL 実行手順や CI/CD、運用スケジュール（Cron や Airflow での定期実行）を追記できます。追加で記載したい項目（例：デプロイ手順、監視・アラート設定、テスト方法など）があれば教えてください。