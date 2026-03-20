# KabuSys

日本株向け自動売買プラットフォームのコアライブラリ（ライブラリ部分）。  
このリポジトリはデータ取得（J-Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、DuckDB スキーマ管理など、アルゴリズム取引システムに必要な基盤処理を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買ワークフローを構成する共通ユーティリティ群をまとめた Python モジュール群です。主な役割は以下の通りです。

- J-Quants API からのデータ取得（株価・財務・マーケットカレンダー）
- DuckDB を使ったデータスキーマ定義・永続化（冪等保存）
- ETL（差分取得・品質チェック）
- 研究用ファクター計算（momentum/value/volatility 等）
- 特徴量（features）生成
- 戦略シグナル生成（BUY / SELL 判定）
- RSS ベースのニュース収集と銘柄紐付け
- マーケットカレンダー管理と営業日判定
- 設定管理（.env / 環境変数）

設計上の方針として「ルックアヘッドバイアスの防止」「冪等性」「外部依存の最小化」「テスト可能性」を重視しています。

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API クライアント（レート制御・リトライ・トークン自動更新・DuckDB 保存関数）
  - pipeline: 日次 ETL（差分取得・backfill・品質チェック）
  - schema: DuckDB のスキーマ初期化・接続ユーティリティ（init_schema, get_connection）
  - news_collector: RSS 収集・前処理・raw_news / news_symbols 保存
  - calendar_management: JPX カレンダー管理（営業日判定、next/prev_trading_day 等）
  - stats: 汎用統計ユーティリティ（zscore_normalize）
- research/
  - factor_research: momentum / value / volatility 等のファクター計算
  - feature_exploration: 将来リターン計算、IC（Spearman）計算、ファクターサマリ
- strategy/
  - feature_engineering: 生ファクターを正規化・フィルタして features テーブルへ保存
  - signal_generator: features と ai_scores を統合して final_score を算出、BUY/SELL シグナル作成
- config: .env / 環境変数の自動読み込みと Settings クラス（必須変数の検査）
- audit / execution / monitoring 等の監査・発注周りスキーマ（audit の DDL が含まれます）

主な公開 API（抜粋）:
- kabusys.data.schema.init_schema(db_path)
- kabusys.data.pipeline.run_daily_etl(conn, target_date=...)
- kabusys.research.calc_momentum / calc_volatility / calc_value
- kabusys.strategy.build_features(conn, target_date)
- kabusys.strategy.generate_signals(conn, target_date, threshold=...)
- kabusys.data.news_collector.run_news_collection(conn, sources, known_codes)

---

## セットアップ手順

前提:
- Python 3.9+（typing の | 記法を利用しているため 3.10 推奨）
- DuckDB（Python パッケージとしてインストール）
- ネットワークアクセス（J-Quants API / RSS フィード）

1. リポジトリをクローン／取得し、パッケージをインストール
   - 開発環境で editable install:
     pip install -e .

2. 依存パッケージ（例）
   - duckdb
   - defusedxml
   - （プロジェクトで必要な他パッケージを requirements.txt に記載している場合はそれに従う）

   例:
   pip install duckdb defusedxml

3. 環境変数設定 (.env)
   - プロジェクトルートに `.env` または `.env.local` を置くと自動読み込みされます（config モジュール参照）。
   - 自動読み込みを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   必須の環境変数:
   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD : kabuステーション API 用パスワード（発注周り）
   - SLACK_BOT_TOKEN : Slack 通知用 Bot トークン
   - SLACK_CHANNEL_ID : Slack 通知先チャンネル ID

   任意（デフォルトあり）:
   - KABUSYS_ENV : development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL : DEBUG / INFO / …（デフォルト: INFO）
   - DUCKDB_PATH : データベースファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH : 監視用 SQLite（デフォルト: data/monitoring.db）

   例 (.env):
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

4. DuckDB スキーマ初期化
   - Python REPL やスクリプトで以下を実行して DB を初期化します。

   例:
   from kabusys.data.schema import init_schema
   from kabusys.config import settings
   conn = init_schema(settings.duckdb_path)

   init_schema は parent ディレクトリを自動的に作成し、DDL を実行してテーブル群とインデックスを作成します（冪等）。

---

## 使い方（基本ワークフロー例）

1. DB 初期化（1回）

   from kabusys.data.schema import init_schema
   from kabusys.config import settings
   conn = init_schema(settings.duckdb_path)

2. 日次 ETL の実行（市場カレンダー、株価、財務の差分取得）:

   from kabusys.data.pipeline import run_daily_etl
   result = run_daily_etl(conn)
   print(result.to_dict())

   - run_daily_etl は target_date を省略すると今日の日付を使用します。
   - J-Quants トークンは config.settings.jquants_refresh_token（.env）から取得されます。必要に応じて id_token を直接渡せます。

3. 特徴量（features）構築:

   from kabusys.strategy import build_features
   from datetime import date
   n = build_features(conn, date.today())
   print(f"features upserted: {n}")

4. シグナル生成:

   from kabusys.strategy import generate_signals
   from datetime import date
   total_signals = generate_signals(conn, date.today(), threshold=0.6)
   print(f"signals written: {total_signals}")

5. ニュース収集（RSS）と銘柄紐付け:

   from kabusys.data.news_collector import run_news_collection
   known_codes = set(...)  # 有効な銘柄コードセット（例: prices_daily から抽出）
   results = run_news_collection(conn, sources=None, known_codes=known_codes)
   print(results)

6. マーケットカレンダー更新ジョブ（夜間バッチ）:

   from kabusys.data.calendar_management import calendar_update_job
   saved = calendar_update_job(conn)
   print(f"calendar saved: {saved}")

注意:
- 各処理は DuckDB のテーブル（features, ai_scores, positions, signals 等）に読み書きします。
- システムは「target_date 時点で利用可能なデータのみを使用する」ことを方針としており、ルックアヘッドバイアスを防ぎます。
- 各種関数は冪等に設計されています（DELETE→INSERT の日付単位置換、ON CONFLICT 等）。

---

## 環境変数（主なもの）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

任意 / デフォルト:
- KABUSYS_ENV (development | paper_trading | live) — default: development
- LOG_LEVEL (DEBUG | INFO | …) — default: INFO
- DUCKDB_PATH — default: data/kabusys.duckdb
- SQLITE_PATH — default: data/monitoring.db
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると .env 自動読み込みを無効化

設定は .env か環境変数で行ってください。.env の自動読み込みはプロジェクトルート（.git または pyproject.toml を基準）から行われます。

---

## ディレクトリ構成

以下は主要ファイル／モジュールの構成（抜粋）です:

src/kabusys/
- __init__.py
- config.py  — 環境変数 / Settings 管理（.env 自動読み込み）
- data/
  - __init__.py
  - schema.py             — DuckDB スキーマ定義・init_schema / get_connection
  - jquants_client.py     — J-Quants API クライアント + 保存関数
  - pipeline.py           — ETL パイプライン（run_daily_etl 等）
  - news_collector.py     — RSS 収集・保存・銘柄抽出
  - calendar_management.py— 市場カレンダーの管理とユーティリティ
  - features.py           — zscore_normalize re-export
  - stats.py              — 統計ユーティリティ（zscore_normalize）
  - audit.py              — 監査ログ用 DDL（signal_events / order_requests / executions 等）
  - pipeline.py
- research/
  - __init__.py
  - factor_research.py    — momentum/value/volatility の計算
  - feature_exploration.py— 将来リターン, IC, factor_summary, rank
- strategy/
  - __init__.py
  - feature_engineering.py— features テーブル作成ロジック
  - signal_generator.py   — final_score の算出と signals 生成
- execution/ (発注・execution 層の骨格)
- monitoring/ (監視・メトリクス用モジュール)
- その他ドキュメント（DataSchema.md 等を想定）

---

## 開発・貢献メモ

- テスト: 各モジュールは外部依存（HTTP / DB）を注入可能に設計し、ユニットテストでのモックが容易です（例: _urlopen の差し替え）。
- ロギング: 各モジュールは logging を利用しており、LOG_LEVEL 環境変数で制御します。
- 冪等性: DB への保存は ON CONFLICT / 日付単位の DELETE→INSERT 等で冪等化しています。
- セキュリティ: RSS パースは defusedxml を利用し SSRF / Gzip bomb / private host 対策を多数実装しています。

---

## よく使うコードスニペット（まとめ）

DB 初期化 + 日次 ETL + 特徴量・シグナル生成のシンプルな典型例:

from datetime import date
from kabusys.config import settings
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl
from kabusys.strategy import build_features, generate_signals

conn = init_schema(settings.duckdb_path)
etl_res = run_daily_etl(conn)
today = etl_res.target_date
build_features(conn, today)
generate_signals(conn, today)

---

もし README に含めたい追加の情報（例: CI 実行手順、Docker イメージ、詳しい環境変数一覧や .env.example のテンプレート、API 利用上の注意点など）があれば教えてください。必要に応じて README を拡張します。