# KabuSys

日本株向けの自動売買 / データプラットフォームのための Python ライブラリ群です。  
データ収集（J-Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、DuckDB スキーマ管理などを提供します。

---

## 概要

KabuSys は以下のレイヤーで構成される設計思想に基づいたプロジェクトです。

- Data（データ層）: J-Quants からの株価・財務・カレンダー・ニュース取得、DuckDB への永続化、品質チェック、カレンダー管理
- Research（研究層）: ファクター計算・特徴量探索・統計ユーティリティ
- Strategy（戦略層）: 特徴量の正規化・統合とシグナル生成（BUY / SELL）
- Execution（実行層）: 発注・約定・ポジション管理に関するスキーマ（実装用の土台）
- Config（設定）: .env / 環境変数からの設定読み込みとバリデーション

設計上のポイント:
- DuckDB を単一の分析 DB として使用（冪等な INSERT/UPsert を行う実装）
- ルックアヘッドバイアス防止（target_date 時点のデータのみ使用）
- 冪等性（ON CONFLICT / トランザクション）や堅牢なエラーハンドリングを重視

---

## 主な機能一覧

- J-Quants API クライアント（取得 / 保存 / レートリミット / リトライ / トークンリフレッシュ）
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar
- DuckDB スキーマ定義と初期化（init_schema）
- ETL パイプライン（差分取得 / backfill / 品質チェック）: run_daily_etl
- 研究用ファクター計算: calc_momentum, calc_volatility, calc_value
- 特徴量生成（正規化・ユニバースフィルタ）: build_features
- シグナル生成（final_score 計算、BUY/SELL 判定）: generate_signals
- ニュース収集（RSS → raw_news 保存、記事ID 正規化、銘柄推定）: fetch_rss / save_raw_news / run_news_collection
- マーケットカレンダー管理（営業日判定、next/prev_trading_day 等）
- 汎用統計ユーティリティ（Z スコア正規化、IC 計算、要約統計）

---

## 動作環境 / 前提

- Python 3.10 以上（コード内での型ヒントや union 演算子 `|` を利用）
- 必要パッケージ（代表例）
  - duckdb
  - defusedxml

プロジェクトの実際の依存は pyproject.toml / requirements.txt を参照してください（本リポジトリに含まれている場合）。

---

## セットアップ手順（ローカル開発用）

1. リポジトリをクローンする
   ```bash
   git clone <this-repo-url>
   cd <this-repo>
   ```

2. Python 仮想環境を作成・有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージをインストール
   - pyproject.toml / poetry を使っている場合:
     ```bash
     poetry install
     ```
   - pip を使う場合（最小例）:
     ```bash
     pip install duckdb defusedxml
     # または requirements.txt がある場合:
     # pip install -r requirements.txt
     ```

4. 環境変数 (.env) を作成する  
   ルートに `.env` または `.env.local` を置くことで自動ロードされます（自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。
   必須の環境変数（テンプレート）:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_api_password
   SLACK_BOT_TOKEN=your_slack_token
   SLACK_CHANNEL_ID=your_slack_channel_id
   # オプション
   KABUSYS_ENV=development    # development | paper_trading | live
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_DISABLE_AUTO_ENV_LOAD=   # 自動読み込みを無効にする場合は 1 を設定
   ```

---

## 使い方（簡単な例）

以下は Python スクリプトや REPL から利用する際の基本的な例です。

- DuckDB スキーマ初期化
  ```python
  from kabusys.data import schema

  conn = schema.init_schema("data/kabusys.duckdb")  # ":memory:" も可
  ```

- 日次 ETL 実行（J-Quants から差分取得して保存）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.data import schema

  conn = schema.get_connection("data/kabusys.duckdb")  # 事前に init_schema を推奨
  result = run_daily_etl(conn)  # target_date を省略すると今日になります
  print(result.to_dict())
  ```

- 研究用ファクター計算 / 特徴量作成 / シグナル生成
  ```python
  import duckdb
  from datetime import date
  from kabusys.strategy import build_features, generate_signals
  from kabusys.data import schema

  conn = schema.get_connection("data/kabusys.duckdb")
  target = date(2024, 1, 31)

  # features を構築（features テーブルに UPSERT）
  n = build_features(conn, target)
  print(f"features upserted: {n}")

  # シグナル生成（signals テーブルへ UPSERT）
  total = generate_signals(conn, target)
  print(f"signals generated: {total}")
  ```

- ニュース収集ジョブ（RSS 収集 → raw_news 保存 → 銘柄紐付け）
  ```python
  from kabusys.data import news_collector
  from kabusys.data import schema

  conn = schema.get_connection("data/kabusys.duckdb")
  # known_codes は有効な銘柄コードの集合（例: 全上場銘柄コード）
  results = news_collector.run_news_collection(conn, known_codes={"7203","6758"})
  print(results)
  ```

- J-Quants API を直接使う（トークン自動リフレッシュ / ページネーション対応）
  ```python
  from kabusys.data import jquants_client as jq

  # ID トークンは自動取得されます（settings.jquants_refresh_token を使用）
  quotes = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  ```

---

## 環境変数一覧（主要）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu API 用パスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack 通知先チャンネル ID
- DUCKDB_PATH — データベースファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL — ログレベル: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env 読み込みを無効化する場合は 1

設定は kabusys.config.settings 経由でアクセスできます（例: settings.jquants_refresh_token）。

---

## ディレクトリ構成（主要ファイル・モジュール）

以下は src/kabusys 配下の主要モジュールとその役割の抜粋です。

- kabusys/
  - __init__.py
  - config.py                         — 環境変数 / .env 読み込みと Settings
  - data/
    - __init__.py
    - jquants_client.py                — J-Quants API クライアント + 保存ユーティリティ
    - news_collector.py                — RSS 取得 / 正規化 / DB 保存 / 銘柄抽出
    - schema.py                        — DuckDB スキーマ定義と init_schema / get_connection
    - stats.py                         — zscore_normalize 等の統計ユーティリティ
    - features.py                      — 公開インターフェース（zscore_normalize）
    - pipeline.py                      — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py           — market_calendar 管理 / 営業日判定
    - audit.py                         — 監査ログ用スキーマ（signal_events 等）
    - execution/ (パッケージ)           — 実行層用の空パッケージ（拡張用）
  - research/
    - __init__.py
    - factor_research.py               — calc_momentum / calc_volatility / calc_value
    - feature_exploration.py           — calc_forward_returns / calc_ic / factor_summary / rank
  - strategy/
    - __init__.py
    - feature_engineering.py           — build_features（正規化・ユニバースフィルタ）
    - signal_generator.py              — generate_signals（final_score 計算・BUY/SELL 判定）
  - execution/                         — 発注実装を追加する場所（現状はパッケージ）

この README に記載の API 名（関数名 / クラス名）はソースコードの docstring に基づいています。詳細な仕様は各モジュールの docstring を参照してください。

---

## 開発 / テスト

- 単体テストや linters はプロジェクトに応じて追加してください（pytest, flake8, mypy など）。
- 環境依存コード（ネットワークや DB）を単体テストする場合は、jquants_client や news_collector のネットワーク呼び出しをモックしてください（コード中でもモック差し替えを想定した設計あり）。

---

## 注意事項 / 運用上のヒント

- KABUSYS_ENV を `live` に設定すると実運用向けフラグ（is_live）が有効化されます。発注や実アカウント操作を行うコードは環境に応じた安全チェックを実装してください。
- DuckDB のバックアップ / バージョン互換性に注意してください。移行時はスキーマ変更のためのマイグレーションを用意することを推奨します。
- ニュース収集時には SSRF 対策や XML BOM/圧縮上限など多くの安全対策を実装していますが、外部フィードを追加する際はソースの信頼性を確認してください。

---

もし README に追加したい事項（例: 実行可能な CLI、Docker / GitHub Actions 設定例、より詳細な環境変数のテンプレートなど）があれば教えてください。必要に応じてサンプル .env.example や運用手順も作成します。