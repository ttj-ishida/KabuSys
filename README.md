# KabuSys

バージョン: 0.1.0

KabuSys は日本株向けの自動売買・データ基盤ライブラリです。J-Quants などから市場データ・財務データ・ニュースを取得し、DuckDB に蓄積・加工して戦略用の特徴量や売買シグナルを生成するためのモジュール群を提供します。研究（research）→ データ（data）→ 戦略（strategy）→ 発注（execution）というレイヤード設計を念頭に置いて実装されています。

主な用途:
- J-Quants API を用いた株価・財務・カレンダーの差分取得（ETL）
- ニュース（RSS）収集と記事 → 銘柄紐付け
- ファクター計算（モメンタム / ボラティリティ / バリュー 等）
- 特徴量正規化・合成（features テーブル生成）
- シグナル生成（features + ai_scores → signals）
- DuckDB スキーマ初期化 / 管理

## 機能一覧

- 環境変数管理（.env の自動読み込み、必須変数チェック）
- J-Quants API クライアント
  - レート制限管理、リトライ、トークン自動リフレッシュ
  - データ取得（株価日足、財務、マーケットカレンダー）
  - DuckDB への冪等保存（ON CONFLICT を利用）
- ETLパイプライン（差分更新・バックフィル・品質チェック呼び出し）
- DuckDB スキーマ定義と初期化（raw / processed / feature / execution 層）
- ファクター計算（momentum / volatility / value）
- 特徴量生成（Zスコア正規化、ユニバースフィルタ）
- シグナル生成（重み付け合成、Bear レジーム抑制、エグジット判定）
- RSS ニュース収集（SSRF 対策、XML 安全パース、トラッキング除去、銘柄抽出）
- マーケットカレンダー管理（営業日判定 / next/prev_trading_day 等）
- 監査ログ（signal → order → execution のトレーサビリティ用 DDL：audit）

## 動作環境 / 前提

- Python 3.10 以上（型記法で | を使用しているため）
- DuckDB（Python パッケージ経由で使用）
- defusedxml（RSS の安全パースで利用）
- （任意）J-Quants API の利用には J-Quants のリフレッシュトークンが必要

依存パッケージ例（最低限）:
- duckdb
- defusedxml

実際のパッケージ化・依存リストはプロジェクトの setup / pyproject.toml を参照してください。

## セットアップ手順

1. リポジトリをクローンし、仮想環境を作成（任意）

   ```bash
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate
   ```

2. 必要パッケージをインストール

   - 開発中であれば editable install:

     ```bash
     python -m pip install -e .
     ```

   - または最低限の依存を個別にインストール:

     ```bash
     python -m pip install duckdb defusedxml
     ```

3. 環境変数設定

   プロジェクトルートに `.env` または `.env.local` を配置すると、自動的にロードされます（優先度: OS 環境変数 > .env.local > .env）。自動ロードを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   必須の環境変数（少なくともこれらを設定する必要があります）:

   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD: kabuステーション API のパスワード（execution 層利用時）
   - SLACK_BOT_TOKEN: Slack 通知用トークン（必要に応じて）
   - SLACK_CHANNEL_ID: 通知先チャンネル ID
   - その他（任意／デフォルトあり）
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL: DEBUG/INFO/...（デフォルト: INFO）
     - KABU_API_BASE_URL: kabu API のベース（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）

   環境変数は `kabusys.config.settings` で参照できます。

4. DuckDB スキーマ初期化

   Python REPL やスクリプトからスキーマを初期化します:

   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")  # ":memory:" でメモリ DB も可
   ```

   この関数は必要なテーブルとインデックスをすべて作成します（冪等）。

## 使い方（代表的な例）

ここではライブラリ関数を直接使う簡単な例を示します。実運用ではタスクスケジューラ（cron / Airflow 等）から呼ぶことを想定しています。

- 日次 ETL を実行する

  ```python
  from datetime import date
  import duckdb
  from kabusys.data.schema import get_connection, init_schema
  from kabusys.data.pipeline import run_daily_etl

  # DB 初期化済み / 既存 DB に接続
  conn = init_schema("data/kabusys.duckdb")

  # 今日分の ETL を実行
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- 特徴量（features）の構築

  build_features は DuckDB コネクションと日付を受け取り、features テーブルへ書き込みます。

  ```python
  from datetime import date
  from kabusys.strategy import build_features
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  count = build_features(conn, target_date=date(2026, 1, 15))
  print(f"upserted features: {count}")
  ```

- シグナル生成

  ```python
  from datetime import date
  from kabusys.strategy import generate_signals
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  total_signals = generate_signals(conn, target_date=date(2026, 1, 15))
  print(f"signals written: {total_signals}")
  ```

- ニュース収集（RSS）ジョブ

  ```python
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  # known_codes は銘柄抽出に利用する有効なコード集合（例: 全上場銘柄のコードセット）
  results = run_news_collection(conn, sources=None, known_codes={"7203","6758"})
  print(results)  # ソースごとの新規保存件数
  ```

- マーケットカレンダー更新ジョブ（夜間バッチ想定）

  ```python
  from kabusys.data.calendar_management import calendar_update_job
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  saved = calendar_update_job(conn)
  print(f"calendar saved: {saved}")
  ```

- 設定値参照

  ```python
  from kabusys.config import settings
  print(settings.duckdb_path)
  print(settings.is_live)
  ```

## 環境変数（主要）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須 for execution)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須 for Slack通知)
- SLACK_CHANNEL_ID (必須 for Slack通知)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — デフォルト: INFO
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動的な .env ロードを停止します（テスト用途など）

.env ファイルは shell の export 形式やシンプルな KEY=VALUE 形式、引用符・エスケープにも対応しています。

## ディレクトリ構成（主なファイル）

src/kabusys/
- __init__.py (パッケージ定義、バージョン)
- config.py (環境変数・設定管理)
- data/
  - __init__.py
  - jquants_client.py (J-Quants API クライアント + 保存ロジック)
  - news_collector.py (RSS 収集・前処理・DB保存)
  - schema.py (DuckDB スキーマ定義・初期化)
  - stats.py (zscore_normalize 等の統計ユーティリティ)
  - pipeline.py (ETL パイプラインの実装)
  - calendar_management.py (市場カレンダー管理)
  - audit.py (監査ログ DDL と初期化用)
  - features.py (公開インターフェース)
- research/
  - __init__.py
  - factor_research.py (momentum/volatility/value の計算)
  - feature_exploration.py (forward_returns, IC, summary 等)
- strategy/
  - __init__.py
  - feature_engineering.py (features 作成ワークフロー)
  - signal_generator.py (シグナル生成ロジック)
- execution/ (発注/実行関連の実装（空の __init__ を含む））
- monitoring/ (監視・メトリクス用の DB/ロジック格納想定)

（上記は主要モジュールの抜粋です。詳細は各ファイルのドキュメント文字列を参照してください。）

## 設計上の注意事項 / ポリシー

- ルックアヘッドバイアス防止: 特徴量・シグナル生成では target_date 時点で「システムが知り得る」情報のみを使うよう設計されています（fetched_at の記録等）。
- 冪等性: DB への保存は ON CONFLICT を使い冪等性を確保しています。ETL は部分失敗しても再実行可能なよう設計されています。
- セキュリティ: RSS 取得では SSRF 対策・XML の安全パース・受信サイズ制限を実装しています。J-Quants ではレート制御とリトライ／トークン自動更新を行います。
- 本コードベースは戦略仕様（StrategyModel.md 等）やデータ仕様（DataPlatform.md / DataSchema.md）に基づく実装を想定しています。実運用する場合はリスク管理・発注フロー・接続先の証券会社 API 実装が必要です。

## 開発 / テスト

- 自動環境ロードをテストで抑制するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB のインメモリモード（":memory:"）を利用して単体テストを実行できます。
- 依存関係はプロジェクトの pyproject.toml / setup.cfg / requirements.txt（存在する場合）を参照してください。

---

問題や不明点があれば、どの機能（ETL / features / signals / news など）について追加の利用例や詳しい説明が必要かを教えてください。README を具体的な運用手順（cron の例、Airflow DAG、Slack 通知の組み込み方法など）に合わせて拡張できます。