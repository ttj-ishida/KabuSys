# KabuSys

日本株向けの自動売買（研究・データ基盤・戦略実行）ライブラリ群です。  
KabuSys は以下の層を備えた設計になっています。

- Data Platform（J-Quants からのデータ取得 / DuckDB スキーマ / ETL パイプライン）
- Research（ファクター計算・特徴量探索）
- Strategy（特徴量の正規化・シグナル生成）
- Execution / Audit（発注・約定・ポジション管理向けスキーマと監査ログ）
- News Collector（RSS ベースのニュース収集・銘柄紐付け）

このリポジトリは、研究環境と本番（paper/live）環境の両方で再現可能な形でデータ取得 → 特徴量作成 → シグナル生成までを行えることを目的としています。

---

## 主な機能

- J-Quants API クライアント
  - 日足（OHLCV）、財務データ、JPX カレンダーのページネーション対応取得
  - レート制限対応（120 req/min）、リトライ、トークン自動リフレッシュ
  - DuckDB への冪等保存ユーティリティ（ON CONFLICT / upsert）

- DuckDB ベースのスキーマ定義・初期化
  - Raw / Processed / Feature / Execution 層を想定したテーブル群
  - インデックス、制約、トランザクションを考慮した初期化関数

- ETL パイプライン
  - 差分更新（最終取得日からの再取得・バックフィル）
  - 市場カレンダー先読み
  - 品質チェック（別モジュール）

- News Collector
  - RSS フィード取得（SSRF 軽減、gzip 対応、XML パース安全化）
  - 記事ID の正規化（URL 正規化 → SHA-256 部分）による冪等保存
  - 記事と銘柄コードの紐付け

- Research モジュール
  - Momentum / Volatility / Value 等のファクター計算
  - 将来リターン計算、IC（Spearman）や統計サマリ

- Strategy 層
  - 特徴量の Z スコア正規化・クリップ（build_features）
  - features + ai_scores を統合した final_score の計算、BUY/SELL シグナル生成（generate_signals）
  - Bear レジーム判定やエグジット（ストップロス等）のルールを含む

- Audit テーブル（監査・トレーサビリティ）設計
  - signal_events / order_requests / executions などの監査ログ用テーブル定義

---

## 要件（推奨）

- Python 3.10+
- 必須パッケージ（最低限）
  - duckdb
  - defusedxml

（セットアップ時に pip でインストールします。追加の依存が将来的にある場合は requirements ファイル等を参照してください）

---

## セットアップ手順

1. リポジトリをクローンして仮想環境を作成・有効化

   ```
   git clone <repo-url>
   cd <repo-root>
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```

2. 必要パッケージをインストール

   ```
   pip install duckdb defusedxml
   # 開発時: pip install -e .
   ```

   ※パッケージ化されている場合は `pip install -e .` でローカル editable install が可能です。

3. 環境変数（.env）を準備する

   パッケージの起動時にプロジェクトルート（.git または pyproject.toml を基準）にある `.env` / `.env.local` を自動で読み込みます（環境変数が既に設定されている場合は上書きされません）。自動読み込みを無効にしたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   主要な環境変数（Settings で必須/既定値が定義されています）:

   - JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD (必須) — kabu API のパスワード
   - KABU_API_BASE_URL (任意) — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
   - SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot Token
   - SLACK_CHANNEL_ID (必須) — Slack 通知先チャンネル ID
   - DUCKDB_PATH (任意) — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH (任意) — 監視用 SQLite（デフォルト: data/monitoring.db）
   - KABUSYS_ENV (任意) — 実行環境 ("development" | "paper_trading" | "live")（デフォルト: development）
   - LOG_LEVEL (任意) — ログレベル ("DEBUG","INFO","WARNING","ERROR","CRITICAL")（デフォルト: INFO）

   サンプル .env:

   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=DEBUG
   ```

4. DuckDB スキーマの初期化

   Python スクリプト / REPL でスキーマを作成します。

   ```python
   from kabusys.data import schema
   conn = schema.init_schema("data/kabusys.duckdb")
   conn.close()
   ```

   - ":memory:" を指定するとインメモリ DB で初期化できます（テスト用途）。

---

## 使い方（基本例）

以下はライブラリ API を直接呼ぶシンプルな例です。実運用ではロギングやエラーハンドリング、スケジューリングを付与してください。

- ETL（日次）を実行する

  ```python
  from kabusys.config import settings
  from kabusys.data import schema
  from kabusys.data.pipeline import run_daily_etl

  conn = schema.get_connection(settings.duckdb_path)
  result = run_daily_etl(conn)  # target_date を渡せば特定日向けに実行可能
  print(result.to_dict())
  conn.close()
  ```

- 特徴量（features）を作る

  ```python
  from datetime import date
  from kabusys.config import settings
  from kabusys.data import schema
  from kabusys.strategy import build_features

  conn = schema.get_connection(settings.duckdb_path)
  n = build_features(conn, target_date=date.today())
  print(f"features upserted: {n}")
  conn.close()
  ```

- シグナルを生成する

  ```python
  from datetime import date
  from kabusys.config import settings
  from kabusys.data import schema
  from kabusys.strategy import generate_signals

  conn = schema.get_connection(settings.duckdb_path)
  total = generate_signals(conn, target_date=date.today(), threshold=0.60)
  print(f"signals saved: {total}")
  conn.close()
  ```

- ニュース収集ジョブを走らせる

  ```python
  from kabusys.data import schema, news_collector
  from kabusys.config import settings

  conn = schema.get_connection(settings.duckdb_path)
  # known_codes を渡すと記事→銘柄紐付けが行われます
  known_codes = {"7203", "6758", "9432"}  # 例
  results = news_collector.run_news_collection(conn, known_codes=known_codes)
  print(results)
  conn.close()
  ```

- カレンダー更新ジョブ

  ```python
  from kabusys.data import schema, calendar_management

  conn = schema.get_connection("data/kabusys.duckdb")
  saved = calendar_management.calendar_update_job(conn)
  print(f"saved calendar entries: {saved}")
  conn.close()
  ```

---

## 自動環境読み込みについて

- パッケージの起動時に、プロジェクトルート（.git または pyproject.toml があるディレクトリ）から `.env` と `.env.local` を自動読み込みします（優先度: OS 環境変数 > .env.local > .env）。
- 自動読み込みが不要なテスト時などは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をセットしてください。

---

## ディレクトリ構成（主要ファイル）

（リポジトリが src-layout の場合を前提）

- src/
  - kabusys/
    - __init__.py
    - config.py
    - data/
      - __init__.py
      - jquants_client.py        — J-Quants API クライアント（取得・保存）
      - schema.py                — DuckDB スキーマ定義・初期化
      - pipeline.py              — ETL パイプライン（run_daily_etl 等）
      - stats.py                 — Z スコア等の統計ユーティリティ
      - news_collector.py        — RSS ニュース収集・保存
      - calendar_management.py   — 市場カレンダー管理・ジョブ
      - features.py              — feature ユーティリティ（再エクスポート）
      - audit.py                 — 監査ログ用 DDL
      - (その他)
    - research/
      - __init__.py
      - factor_research.py       — ファクター計算（momentum/volatility/value）
      - feature_exploration.py   — 将来リターン / IC / 統計サマリ
    - strategy/
      - __init__.py
      - feature_engineering.py   — features の構築（正規化・ユニバースフィルタ等）
      - signal_generator.py      — final_score 計算・シグナル生成
    - execution/
      - __init__.py
      - (発注/ブローカー連携ロジックはこの層へ実装想定)
    - monitoring/
      - (監視/メトリクス/アラート用の実装を想定)

上の構成は本 README に沿った機能分割が行われており、Data / Research / Strategy / Execution の責務が分離されています。

---

## 注意事項 / 補足

- Python バージョンは 3.10 以上を想定（`X | Y` 型注釈を使用）。
- DuckDB 接続はシンプルに `duckdb.connect(db_path)` で取得できます。スキーマ初期化には `init_schema()` を使うことを推奨します（初回のみ）。
- J-Quants クライアントはネットワーク/HTTP エラーや 401 などに対して自動リトライ／トークンリフレッシュを行いますが、API 利用上限や利用規約には注意してください。
- NewsCollector は SSRF 対策や XML パースの安全化（defusedxml）などを実装しています。外部フィードの取り扱いは厳重に行ってください。
- Strategy 層の設定（閾値・重みなど）は関数引数で上書きでき、デフォルトはコード内で定義されています。運用時はテストとバックテストを十分に行ってください。
- Execution 層（ブローカー接続）は本コードベースではスキーマ・監査ログを提供する設計で、実際のブローカー API ラッパーは別途実装することが想定されています。

---

必要であれば、README にサンプル .env.example や docker-compose / systemd ユニット例、CI 向けのテスト実行手順、より詳細な API リファレンス（各関数の使用例）を追加で作成します。どの情報を優先して追記しますか？