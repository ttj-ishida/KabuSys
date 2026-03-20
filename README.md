# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
データ取得（J-Quants）、DuckDB によるデータ格納、ファクター計算、特徴量生成、シグナル生成、ニュース収集、マーケットカレンダー管理、監査ログなどを含む一連の処理をモジュール化しています。

主な設計方針：
- ルックアヘッドバイアス防止（target_date ベースで処理）
- DuckDB を中心とした冪等的なデータ保存（ON CONFLICT / トランザクション）
- 外部 API 呼び出しは適切にレート制御・リトライ・トークンリフレッシュを実装
- research 層と production 層を分離（研究用ユーティリティも提供）

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 機能一覧
- 必要条件
- 環境変数
- セットアップ手順
- 使い方（例）
- ディレクトリ構成
- 開発・テストのヒント

---

## プロジェクト概要

KabuSys は日本株の自動売買システムの基礎となるライブラリ群です。主に以下を提供します。

- J-Quants API クライアント（データ取得・保存）
- DuckDB ベースのスキーマ定義と初期化
- ETL パイプライン（差分取得、保存、品質チェック）
- ファクター計算（モメンタム / ボラティリティ / バリュー 等）
- 特徴量エンジニアリング（正規化・フィルタ）
- シグナル生成（final_score 計算、BUY/SELL ロジック）
- ニュース収集（RSS、記事正規化、銘柄抽出、DB 保存）
- マーケットカレンダー管理（営業日判定、更新ジョブ）
- 監査ログ用スキーマ（signal → order → execution のトレース）

---

## 機能一覧

- data/jquants_client: J-Quants からの株価・財務・カレンダー取得、保存（冪等）
  - レートリミット制御、リトライ、トークン自動リフレッシュを実装
- data/schema: DuckDB スキーマ定義と init_schema() による初期化
- data/pipeline: 日次 ETL（run_daily_etl）・個別 ETL ジョブ（prices/financials/calendar）
- data/news_collector: RSS 取得・本文前処理・記事ID生成・raw_news 保存・銘柄抽出
- data/calendar_management: 営業日判定 / next/prev_trading_day 等のユーティリティ、calendar_update_job
- data/stats: zscore_normalize（クロスセクション Z スコア正規化）
- research/*: 研究用途のファクター計算・解析（forward returns, IC, factor summary 等）
- strategy/feature_engineering: 生ファクターの統合・ユニバースフィルタ・Z 正規化 → features テーブルへ
- strategy/signal_generator: features と ai_scores を統合して final_score を算出、BUY/SELL シグナルを signals テーブルへ
- execution / monitoring: （パッケージの公開 API に含まれる名前空間）

---

## 必要条件

- Python 3.10 以上（PEP 604 の型記法などを利用）
- 必要な Python パッケージ（最低限）:
  - duckdb
  - defusedxml

インストール例:
pip install duckdb defusedxml

実運用では追加の依存（Slack SDK 等）が必要になる場合があります。

---

## 環境変数

以下の環境変数／.env を参照します。プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` / `.env.local` を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すれば自動ロードを無効化できます）。

必須（Settings._require により未設定時は例外）:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- KABU_API_PASSWORD: kabuステーション API 用パスワード
- SLACK_BOT_TOKEN: Slack 通知用トークン
- SLACK_CHANNEL_ID: Slack チャンネル ID

任意（デフォルト値あり）:
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると自動 .env ロードを無効化
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視用DB）パス（デフォルト: data/monitoring.db）
- KABUS_API_BASE_URL: kabuAPI ベース URL（デフォルト: http://localhost:18080/kabusapi）

例 (.env):
JQUANTS_REFRESH_TOKEN=your_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

---

## セットアップ手順

1. リポジトリをクローン / ソースを用意
2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install --upgrade pip
   - pip install duckdb defusedxml
   - （必要に応じて他パッケージを追加）
4. 環境変数を設定（.env をプロジェクトルートに配置）
   - .env or .env.local を作成
5. DuckDB スキーマの初期化（初回のみ）
   - 下記「使い方」の例を参照

備考:
- 自動 .env ロードを無効化するテスト時は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 使い方（簡単な例）

以下は Python REPL / スクリプトからの利用例です。

1) DuckDB スキーマ初期化
from kabusys.config import settings
from kabusys.data.schema import init_schema

conn = init_schema(settings.duckdb_path)  # デフォルト: data/kabusys.duckdb

2) 日次 ETL 実行（株価 / 財務 / カレンダー を取得）
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn)  # target_date を指定可能
print(result.to_dict())

3) 特徴量ビルド（features テーブル作成）
from datetime import date
from kabusys.strategy import build_features
count = build_features(conn, date(2025, 1, 31))
print(f"features upserted: {count}")

4) シグナル生成（signals テーブル作成）
from kabusys.strategy import generate_signals
num_signals = generate_signals(conn, date(2025, 1, 31))
print(f"signals written: {num_signals}")

5) ニュース収集ジョブ
from kabusys.data.news_collector import run_news_collection
# known_codes を渡すと本文からの銘柄抽出・news_symbols テーブル更新を行う
results = run_news_collection(conn, known_codes={"7203", "6758"})
print(results)

6) カレンダーバッチ更新
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn)
print(f"calendar saved: {saved}")

注意:
- run_daily_etl などの各ジョブは内部で例外を捕捉しつつ進めますが、外部 API のエラーや DB トランザクション失敗は例外を投げる場合があります。ログ出力を参照してください。
- J-Quants API の認証トークンは settings.jquants_refresh_token により取得され、自動で ID トークンに変換・キャッシュされます。401 が返された場合は自動リフレッシュを試行します。

---

## ディレクトリ構成

パッケージは src/kabusys 以下に実装されています。主要なファイルと目的は以下の通り：

- src/kabusys/__init__.py
- src/kabusys/config.py
  - 環境変数読み込み、Settings クラス
- src/kabusys/data/
  - jquants_client.py      : J-Quants API クライアント（fetch / save）
  - news_collector.py     : RSS 取得・記事保存・銘柄抽出
  - schema.py             : DuckDB スキーマ定義・初期化 (init_schema)
  - pipeline.py           : ETL パイプライン（run_daily_etl など）
  - stats.py              : 統計ユーティリティ（zscore_normalize 等）
  - calendar_management.py: マーケットカレンダー管理
  - audit.py              : 監査ログ関連スキーマ（signal/events/order/execution）
  - features.py           : features 関連の公開インターフェース
- src/kabusys/research/
  - factor_research.py    : ファクター算出（momentum/value/volatility）
  - feature_exploration.py: 研究用解析ツール（forward returns, IC, summary）
- src/kabusys/strategy/
  - feature_engineering.py: 生ファクター統合・正規化 → features へ保存
  - signal_generator.py    : final_score 計算と signals テーブルへの書き込み
- src/kabusys/execution/ (空 __init__ など)
- src/kabusys/monitoring/ (監視関連モジュール - 実装が含まれる場合あり)

---

## 開発・テストのヒント

- 自動で .env を読み込む機能は config モジュールによって行われます。テスト中に環境を汚したくない場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB のインメモリテストは init_schema(":memory:") を使って行えます。
- news_collector.fetch_rss は外部ネットワーク依存部分（_urlopen）をモックしてテストしやすい設計になっています。
- jquants_client._RateLimiter により API 呼び出しがスロットリングされるため、実 API 呼び出しを多数行うテストは時間がかかります。id_token をモックしてユニットテストを行ってください。
- logging は設定された LOG_LEVEL を参照します。テスト実行時は DEBUG ログを有効にすると内部挙動の把握に便利です。

---

必要に応じて README にサンプル .env.example、運用手順（cron や Airflow でのジョブ実行方法）、監視・アラート設定、Slack 通知の使い方などを追記してください。開発中の仕様（StrategyModel.md / DataPlatform.md / DataSchema.md 等）に沿って拡張する前提で設計されています。