# KabuSys

日本株向けの自動売買システム用ライブラリ集です。データ取得（J-Quants）、ETL、特徴量作成、シグナル生成、ニュース収集、マーケットカレンダー管理、監査ログなど、運用に必要な主要コンポーネントを含んでいます。

バージョン: 0.1.0

---

## 概要

このリポジトリは、マーケットデータの取得と管理、ファクター計算、特徴量作成、戦略シグナル生成、ニュース収集、そして発注／監査のための各種ユーティリティを提供します。DuckDB を DB 層として使い、J-Quants API からデータを取得して冪等に保存します。研究（research）コードと運用（strategy / data）コードは明確に分離されています。

設計上のポイント：
- ルックアヘッドバイアスを避ける設計（target_date 時点のデータしか参照しない）
- DuckDB によるローカル永続化（スキーマは冪等に作成）
- J-Quants API 呼び出しに対するレート制御・リトライ・トークン自動更新
- ニュース収集での SSRF 対策や XML を安全に扱う実装
- 冪等（ON CONFLICT）な DB 書き込み

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API クライアント（ページネーション、レート制御、リトライ、トークン取得）
  - schema: DuckDB スキーマ定義・初期化（raw / processed / feature / execution 層）
  - pipeline: 日次 ETL（prices / financials / calendar）の差分取得と保存
  - news_collector: RSS からニュース収集、URL 正規化、記事保存、銘柄抽出
  - calendar_management: JPX カレンダー管理（営業日判定、next/prev_trading_day 等）
  - stats: Zスコア正規化などの統計ユーティリティ
  - features: データ層で再利用されるエイリアス（zscore_normalize）
  - audit: 発注〜約定の監査ログ用テーブル定義
- research/
  - factor_research: Momentum / Volatility / Value 等のファクター計算
  - feature_exploration: 将来リターン計算、IC（Spearman）計算、統計サマリー等
- strategy/
  - feature_engineering: research の生ファクターを正規化・合成して features テーブルへ保存
  - signal_generator: features / ai_scores / positions を統合し最終スコアを計算、BUY/SELL シグナル生成して signals テーブルへ保存
- config: 環境変数・設定管理（.env 自動ロード、必須変数検査）
- execution/, monitoring/: 実運用の発注実行層・監視層のための名前空間（将来拡張）

---

## 動作環境・依存関係

- Python 3.10 以上（型注釈で `X | Y` を使用しているため）
- 必要パッケージ（代表例）:
  - duckdb
  - defusedxml
- そのほか標準ライブラリに依存する実装が中心です。実環境では pip 等で追加の依存を管理してください。

例:
pip install duckdb defusedxml

（プロジェクトに requirements.txt / pyproject.toml があればそちらを使ってください）

---

## セットアップ手順

1. リポジトリをクローン／チェックアウト

2. 仮想環境を作成して有効化（推奨）

   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .\.venv\Scripts\activate   # Windows (PowerShell)

3. 必要パッケージをインストール

   pip install -U pip
   pip install duckdb defusedxml

   （プロジェクトを editable インストールしたい場合）
   pip install -e .

4. 環境変数の準備

   ルート（プロジェクトルート）に `.env` または `.env.local` を作成すると、`kabusys.config` モジュールが自動で読み込みます（ただしテスト等で無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。

   主要な環境変数（必須）:
   - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabu ステーション API のパスワード（必須）
   - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
   - SLACK_CHANNEL_ID: Slack チャンネル ID（必須）

   任意・デフォルト付き:
   - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
   - KABU_API_BASE_URL: kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH: 監視等で使用する SQLite のパス（デフォルト data/monitoring.db）

   例 (.env):
   JQUANTS_REFRESH_TOKEN= your_refresh_token_here
   KABU_API_PASSWORD= your_password
   SLACK_BOT_TOKEN= xoxb-...
   SLACK_CHANNEL_ID= C01234567
   DUCKDB_PATH= data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO

5. DuckDB スキーマ初期化

   以下のようにして DB を初期化します（ファイルは settings.duckdb_path を利用する例）。

   from kabusys.config import settings
   from kabusys.data.schema import init_schema

   conn = init_schema(settings.duckdb_path)  # ファイルがなければ親ディレクトリも作成します

---

## 使い方（主要な例）

- 日次 ETL（株価 / 財務 / カレンダー）を実行する

  from datetime import date
  import duckdb
  from kabusys.config import settings
  from kabusys.data.schema import init_schema, get_connection
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema(settings.duckdb_path)
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())

- 特徴量の構築（strategy.feature_engineering.build_features）

  from datetime import date
  from kabusys.config import settings
  from kabusys.data.schema import init_schema
  from kabusys.strategy import build_features

  conn = init_schema(settings.duckdb_path)
  n = build_features(conn, target_date=date.today())
  print(f"built features for {n} codes")

- シグナル生成（strategy.signal_generator.generate_signals）

  from datetime import date
  from kabusys.config import settings
  from kabusys.data.schema import init_schema
  from kabusys.strategy import generate_signals

  conn = init_schema(settings.duckdb_path)
  total = generate_signals(conn, target_date=date.today())
  print(f"signals generated: {total}")

- ニュース収集（RSS）

  from kabusys.config import settings
  from kabusys.data.schema import init_schema
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

  conn = init_schema(settings.duckdb_path)
  known_codes = {"7203", "6758", ...}  # 運用上の有効銘柄コード一覧
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
  print(results)

- カレンダー更新ジョブ

  from kabusys.data.schema import init_schema
  from kabusys.data.calendar_management import calendar_update_job
  from kabusys.config import settings

  conn = init_schema(settings.duckdb_path)
  saved = calendar_update_job(conn)
  print(f"calendar saved: {saved}")

- research ユーティリティ（研究用途）

  from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic

  # conn は DuckDB 接続、target_date は date 型
  mom = calc_momentum(conn, target_date)
  fwd = calc_forward_returns(conn, target_date, horizons=[1,5,21])
  ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_5d")

---

## 環境変数詳細（主要）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (任意, デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- DUCKDB_PATH (任意, デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (任意, デフォルト: data/monitoring.db)
- KABUSYS_ENV (任意, 値: development|paper_trading|live, デフォルト: development)
- LOG_LEVEL (任意, 値: DEBUG|INFO|WARNING|ERROR|CRITICAL, デフォルト: INFO)
- KABUSYS_DISABLE_AUTO_ENV_LOAD (任意, 値: 1 を設定すると .env 自動読み込みを無効化)

config.Settings クラスからこれらを参照できます（例: settings.jquants_refresh_token）。

---

## ディレクトリ構成

src/kabusys/
- __init__.py
- config.py
- data/
  - __init__.py
  - jquants_client.py       # J-Quants API クライアント + 保存ロジック
  - news_collector.py       # RSS 取得・記事解析・DB 保存
  - schema.py               # DuckDB スキーマ定義と init_schema/get_connection
  - pipeline.py             # ETL パイプライン（run_daily_etl 等）
  - stats.py                # zscore_normalize 等の統計ユーティリティ
  - features.py             # data 層の公開インターフェース（再エクスポート）
  - calendar_management.py  # マーケットカレンダー管理
  - audit.py                # 監査ログ用スキーマ定義
  - (その他)
- research/
  - __init__.py
  - factor_research.py      # Momentum / Volatility / Value ファクター計算
  - feature_exploration.py  # 将来リターン, IC, 統計サマリー
- strategy/
  - __init__.py
  - feature_engineering.py  # features テーブルの構築
  - signal_generator.py     # final_score 計算と signals 書き込み
- execution/                 # 発注実装層（名前空間）
- monitoring/                # 監視・アラート用コード（名前空間）

---

## 注意点 / 補足

- DuckDB スキーマは init_schema() により冪等的に作成されます。既存 DB に対しては処理を上書きしません。
- J-Quants API のリクエストはレート制御とリトライが入っているため、長時間かかる場合があります（特に全銘柄の取得など）。
- ニュース取得は外部 HTTP を行うため、ネットワーク・SSRF 対策（ホワイトリスト・プライベート IP ブロック等）に配慮しています。news_collector は defusedxml を利用して XML の安全なパースを行います。
- strategy 層は execution 層（実際の発注）へ依存しない設計です。生成した signals テーブルを execution 層の実装が消費する想定です。
- 環境変数は .env / .env.local によりプロジェクトルートから自動読み込みされます（config._find_project_root により __file__ を起点にプロジェクトルートを特定）。自動読み込みを抑止したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Research の関数群は本番資産へアクセスしない想定で、DuckDB の prices_daily / raw_financials などのみを参照します。

---

もし README に追加したい具体的な使用例（cron ジョブ構成、Dockerfile、systemd ユニット、CI 設定、.env.example など）があれば、必要に応じて追記します。