# KabuSys

日本株向けの自動売買およびデータプラットフォーム用ライブラリ（簡易版）。  
DuckDB をデータストアに用い、J-Quants API / RSS ニュース等からデータを取得して ETL を行い、特徴量の生成・シグナル算出・発注監査を支援するモジュール群を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は次の目的で設計されたモジュール群です。

- J-Quants API から株価・財務・市場カレンダーを取得して DuckDB に蓄積する ETL パイプライン
- RSS を用いたニュース収集・記事の前処理と銘柄紐付け
- 研究（research）向けのファクター計算・解析ユーティリティ（モメンタム・ボラティリティ・バリュー等）
- 特徴量の正規化・合成（feature engineering）と戦略シグナル生成（generate_signals）
- 発注／監査のためのスキーマ（audit）・実行層テーブル定義
- 設定管理（.env 自動読み込み、環境ごとのフラグ）

設計上の特徴として、ルックアヘッドバイアス回避の方針が徹底されており、
DB の指定日までのデータのみを用いて計算するよう実装されています。また、DuckDB への挿入は冪等（ON CONFLICT）を意識しています。

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API クライアント（レート制御、リトライ、ページネーション、トークン自動更新）
  - pipeline: ETL ジョブ（run_daily_etl / 個別ETL）
  - schema: DuckDB スキーマの初期化・接続ヘルパー
  - news_collector: RSS 収集、前処理、raw_news / news_symbols 保存
  - calendar_management: market_calendar の管理・営業日ロジック
  - stats / features: Z スコア正規化などの統計ユーティリティ
- research/
  - factor_research: momentum / volatility / value などのファクター計算
  - feature_exploration: 将来リターン計算・IC 計算・統計サマリー
- strategy/
  - feature_engineering.build_features: research からの生ファクターを合成して features テーブルに保存
  - signal_generator.generate_signals: features / ai_scores / positions を統合して BUY/SELL シグナルを生成し signals テーブルに保存
- config: 環境変数管理（.env 自動ロード、必須チェック、settings オブジェクト）
- audit: 発注／約定の監査テーブル定義（監査ログ用DDL）

---

## 前提条件

- Python 3.10+
- DuckDB
- defusedxml
- 標準ライブラリ以外の依存は上記が主要なものです。実際の運用ではさらに Slack SDK や kabu API クライアント等が必要になる可能性があります。

推奨インストール例（仮）:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
```

（パッケージ化されているなら `pip install -e .` などを使います）

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成して依存をインストール
   ```
   python -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   pip install duckdb defusedxml
   ```

3. 環境変数の設定
   - プロジェクトルートに `.env` と（必要なら）`.env.local` を置くと、自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 必要な主要設定（例）:
     ```
     # J-Quants
     JQUANTS_REFRESH_TOKEN=xxxxx

     # kabuステーション API（注文連携を行う場合）
     KABU_API_PASSWORD=your_kabu_password
     KABU_API_BASE_URL=http://localhost:18080/kabusapi

     # Slack 通知
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C0123456789

     # DB パス
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db

     # 環境
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

   - `.env` の自動ロードルール:
     - プロジェクトルートは __file__ の親階層から `.git` または `pyproject.toml` を探索して決定します。
     - 読み込み順: OS 環境 > .env.local > .env（.env.local は上書き）
     - テスト等で自動ロードを無効にする場合: `export KABUSYS_DISABLE_AUTO_ENV_LOAD=1`

4. DuckDB スキーマ初期化
   Python REPL やスクリプトから schema.init_schema を呼び出して DB を初期化します。
   例:
   ```python
   from kabusys.data import schema
   from kabusys.config import settings

   conn = schema.init_schema(settings.duckdb_path)
   ```
   これにより `features`, `prices_daily`, `raw_news`, `signals` 等のテーブルが作成されます。

---

## 使い方（代表的な操作サンプル）

- DuckDB 接続取得（初回は init_schema、既存 DB は get_connection）
  ```python
  from kabusys.data import schema
  conn = schema.init_schema("data/kabusys.duckdb")  # 初回
  # conn = schema.get_connection("data/kabusys.duckdb")  # 既存 DB に接続する場合
  ```

- 日次 ETL（J-Quants からデータを取得して保存、品質チェック付き）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn)  # target_date を指定可
  print(result.to_dict())
  ```

- 特徴量の構築（research のファクター結果を正規化して features テーブルへ保存）
  ```python
  from kabusys.strategy import build_features
  from datetime import date

  n = build_features(conn, date(2024, 1, 31))
  print("upserted features:", n)
  ```

- シグナル生成（features / ai_scores / positions を参照して signals を更新）
  ```python
  from kabusys.strategy import generate_signals
  from datetime import date

  total = generate_signals(conn, date(2024, 1, 31), threshold=0.6)
  print("signals written:", total)
  ```

- RSS ニュース収集と保存
  ```python
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  # known_codes は銘柄抽出に用いる有効な銘柄コードの集合
  res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203","6758"})
  print(res)
  ```

- カレンダー更新ジョブ
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  saved = calendar_update_job(conn)
  print("calendar saved:", saved)
  ```

- 研究用ユーティリティ（将来リターン・IC 等）
  ```python
  from kabusys.research import calc_forward_returns, calc_ic, factor_summary
  # calc_forward_returns(conn, date(2024,1,31))
  ```

---

## 環境変数一覧（主要なもの）

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabu API パスワード（発注連携時に必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: Slack 通知用（必須にしている箇所あり）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視用）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 実行環境（development / paper_trading / live）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 自動 .env ロードを無効化する場合は `1` を設定

注意: 設定値の取得は `kabusys.config.settings` を通じて行います。必須変数が未設定の場合は ValueError が発生します。

---

## ディレクトリ構成

主要ファイル／モジュールと役割（src/kabusys 以下）:

- __init__.py
- config.py
  - 環境変数自動読み込み、settings オブジェクト
- data/
  - jquants_client.py         -- J-Quants API クライアント（取得/保存ユーティリティ）
  - pipeline.py               -- ETL パイプライン（run_daily_etl など）
  - schema.py                 -- DuckDB スキーマ定義・初期化
  - stats.py                  -- zscore_normalize 等
  - features.py               -- features の公開インターフェース
  - news_collector.py         -- RSS 収集・前処理・DB 保存
  - calendar_management.py    -- market_calendar 管理（営業日ロジック）
  - audit.py                  -- 監査ログ／発注トレーサビリティ用スキーマ
  - execution/                -- 実行層（発注連携等、空ディレクトリあり）
- research/
  - factor_research.py        -- モメンタム/ボラティリティ/バリューファクター計算
  - feature_exploration.py    -- 将来リターン / IC / 統計サマリー
- strategy/
  - feature_engineering.py    -- features の構築（build_features）
  - signal_generator.py       -- シグナル生成（generate_signals）
- その他: execution/, monitoring/ モジュールが __all__ に準備されているが未実装/拡張対象

---

## 開発メモ / 設計上の注意

- ルックアヘッドバイアス回避: ほとんどの関数は target_date 時点までのデータのみを参照する設計です。
- 冪等性: DuckDB への保存処理は ON CONFLICT を利用して上書き/スキップし、複数回の処理で二重挿入が起きないようになっています。
- エラー処理: ETL の個別ステップは独立して例外処理され、1 ステップの失敗で全体停止しないことを意図しています（結果オブジェクトにエラー情報を追加）。
- 自動 .env 読み込みはプロジェクトルートを .git / pyproject.toml を基準に探索します。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して無効化できます。
- Python の型アノテーションや最近の構文を利用しているため Python 3.10 以降を想定しています。

---

## ライセンス / 貢献

本リポジトリに含まれるコードのライセンス／貢献ポリシーは本 README には含まれていません。実際の配布時には LICENSE を用意してください。

---

必要であれば、README に次の項目も追加できます:
- requirements.txt の具体的な依存一覧
- 実運用（kabuステーション / 証券会社 API）との連携手順
- 例外ケースの監視・アラート設定（Slack 通知の例）
- CI / テスト実行例

要望があれば追記します。