# KabuSys

日本株向けの自動売買 / 研究プラットフォーム用ライブラリ。  
市場データの取得・保存（J-Quants）、データ整形（ETL）、特徴量計算、シグナル生成、バックテスト、ニュース収集などを一貫して扱える設計になっています。

主な特徴
- DuckDB を用いたローカルDBスキーマ（冪等な INSERT / ON CONFLICT を活用）
- J-Quants API クライアント（レート制御・リトライ・トークン自動更新対応）
- 研究（research）モジュールでファクター計算・探索をサポート
- strategy 層で特徴量作成（feature_engineering）・シグナル生成（signal_generator）
- backtest フレームワーク（シミュレータ・メトリクス・日次ループ）
- ニュース収集（RSS）と記事→銘柄紐付け機能（SSRF対策・前処理付き）
- 環境変数/.env による設定管理（自動ロード機能あり）

---

## 機能一覧（主要モジュール）

- kabusys.config
  - .env / .env.local からの自動読み込み（プロジェクトルート検出）
  - 設定アクセス用 `settings`（J-Quants トークン、kabu API パスワード、Slack トークン等）

- kabusys.data
  - jquants_client: J-Quants API クライアント（fetch / save 系関数）
  - schema: DuckDB のスキーマ定義・初期化（init_schema）
  - pipeline: 差分 ETL / run_prices_etl などのパイプライン
  - news_collector: RSS 取得・前処理・raw_news への保存・銘柄抽出
  - stats: z-score 正規化など汎用統計ユーティリティ

- kabusys.research
  - factor_research: mom/volatility/value 等のファクター計算
  - feature_exploration: forward returns / IC / summary 等

- kabusys.strategy
  - feature_engineering.build_features(conn, target_date)
  - signal_generator.generate_signals(conn, target_date, ...)

- kabusys.backtest
  - engine.run_backtest(...)：バックテストの実行（DBコピー→日次ループ→評価）
  - simulator.PortfolioSimulator：擬似約定ロジック（スリッページ・手数料モデル）
  - metrics.calc_metrics：CAGR/Sharpe/MaxDD 等の算出
  - CLI エントリポイント：python -m kabusys.backtest.run

- kabusys.data.news_collector
  - fetch_rss, save_raw_news, run_news_collection（SSRF対策・gzip上限・トラッキング除去等）

---

## 必要条件 / 依存関係

- Python >= 3.10（| 型注釈などの構文を利用）
- 必須パッケージ（例）
  - duckdb
  - defusedxml

インストール例（仮想環境を推奨）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# 任意: 開発インストール（パッケージ化されている場合）
# pip install -e .
```

---

## 環境変数 / .env

自動で .env / .env.local をプロジェクトルートから読み込みます（ルート判定: .git または pyproject.toml）。  
自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時などに有用）。

必須（Settings で _require() されるもの）
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
- KABU_API_PASSWORD      : kabu ステーション API のパスワード
- SLACK_BOT_TOKEN        : Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID       : Slack チャネル ID

任意（デフォルトあり）
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — デフォルト: INFO
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db

.env の読み込みルール
- OS 環境変数 > .env.local > .env の順で優先
- export KEY=val 形式に対応、クォートやコメントの処理あり

---

## セットアップ手順（最小構成）

1. リポジトリをクローンして仮想環境を用意
   ```bash
   git clone <repo-url>
   cd <repo-dir>
   python -m venv .venv
   source .venv/bin/activate
   pip install duckdb defusedxml
   ```

2. 環境変数を設定（.env ファイル作成推奨）
   - 例: .env
     ```
     JQUANTS_REFRESH_TOKEN=xxxx
     KABU_API_PASSWORD=yyyy
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C12345678
     KABUSYS_ENV=development
     ```

3. DuckDB スキーマの初期化
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   conn.close()
   ```
   またはコマンドライン内の Python から実行して DB ファイルを作成します。

---

## 使い方（主要ユースケース）

以下はライブラリ関数を直接呼ぶ例（Python REPL / スクリプト）。

- DB 初期化（1度だけ）
  ```python
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")
  # ... 作業後
  conn.close()
  ```

- J-Quants から株価を取得して保存（jquants_client を直接利用）
  ```python
  from kabusys.data import jquants_client as jq
  from kabusys.data.schema import init_schema
  from datetime import date

  conn = init_schema("data/kabusys.duckdb")
  records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  saved = jq.save_daily_quotes(conn, records)
  conn.close()
  ```

- ETL：差分取得（pipeline の run_prices_etl 等）
  ```python
  from kabusys.data.pipeline import run_prices_etl
  from kabusys.data.schema import init_schema
  from datetime import date

  conn = init_schema("data/kabusys.duckdb")
  fetched, saved = run_prices_etl(conn, target_date=date.today())
  conn.close()
  ```

- 特徴量作成（feature_engineering）
  ```python
  from kabusys.strategy import build_features
  from kabusys.data.schema import init_schema
  from datetime import date

  conn = init_schema("data/kabusys.duckdb")
  n = build_features(conn, date(2024, 1, 31))
  print(f"features upserted: {n}")
  conn.close()
  ```

- シグナル生成
  ```python
  from kabusys.strategy import generate_signals
  from kabusys.data.schema import init_schema
  from datetime import date

  conn = init_schema("data/kabusys.duckdb")
  total = generate_signals(conn, date(2024, 1, 31), threshold=0.6)
  print(f"signals written: {total}")
  conn.close()
  ```

- バックテスト（CLI 推奨）
  ```bash
  python -m kabusys.backtest.run \
    --start 2023-01-01 --end 2023-12-31 \
    --cash 10000000 --db data/kabusys.duckdb
  ```
  または Python API:
  ```python
  from kabusys.backtest.engine import run_backtest
  from kabusys.data.schema import init_schema
  from datetime import date

  conn = init_schema("data/kabusys.duckdb")
  result = run_backtest(conn, start_date=date(2023,1,1), end_date=date(2023,12,31))
  print(result.metrics)
  conn.close()
  ```

- ニュース収集（RSS）
  ```python
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203","6758"})
  conn.close()
  ```

注意点
- 多くの関数は DuckDB の接続（DuckDBPyConnection）を受け取り、テーブルを参照/更新します。
- 保存処理は冪等性（ON CONFLICT）を考慮した実装になっています。
- 設定不足（必須環境変数未設定）は settings で ValueError を投げます。

---

## ディレクトリ構成（概要）

src/kabusys/
- __init__.py
- config.py — 環境変数 / .env の読み込み・Settings
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（fetch / save）
  - news_collector.py — RSS 取得・保存・銘柄抽出
  - schema.py — DuckDB スキーマ定義 & init_schema()
  - pipeline.py — ETL パイプライン（差分取得・バックフィル）
  - stats.py — zscore_normalize 等
- research/
  - __init__.py
  - factor_research.py — モメンタム / ボラティリティ / バリュー計算
  - feature_exploration.py — forward returns / IC / summary / rank
- strategy/
  - __init__.py
  - feature_engineering.py — features テーブル作成（正規化・フィルタ）
  - signal_generator.py — final_score 計算と signals 生成
- backtest/
  - __init__.py
  - engine.py — run_backtest（DBコピー→日次ループ）
  - simulator.py — PortfolioSimulator（擬似約定）
  - metrics.py — バックテスト評価指標
  - run.py — CLI 実行エントリポイント
  - clock.py — SimulatedClock（将来拡張用）
- execution/ (現時点ファイル無し / レイヤー用)
- monitoring/ (現時点ファイル無し / 監視用)

---

## 開発・運用上の注意

- DuckDB のバージョンによってはサポートする SQL 機能に差異があるため、テスト済みのバージョンを使用してください（プロジェクトに lock や CI があればそれに従ってください）。
- J-Quants API のレート制限（120 req/min）を Respect する実装になっていますが、大量のリクエストを行う際は注意してください。
- ニュース収集は外部 RSS を取得するため SSRF 対策やレスポンス上限が組み込まれていますが、運用時はフィードソースの信頼性・頻度を管理してください。
- 本リポジトリは金融資産に関わる計算を含むため、実運用時は充分な検証・監査・リスク管理を行ってください。

---

必要であれば、README にサンプル .env.example、より細かい API 仕様、DB スキーマのカラム説明、CI / テスト手順、Docker Compose によるローカル起動などを追加できます。どの情報を優先して追加しますか？