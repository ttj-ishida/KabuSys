# KabuSys

日本株向けの自動データ基盤・研究・戦略ライブラリ群です。  
DuckDB をデータレイヤに用い、J-Quants API / RSS 等からデータを収集し、特徴量計算・品質チェック・ETL パイプラインを提供します。

---

## 概要

KabuSys は以下のレイヤーを想定したモジュール群を含みます。

- データ取得・保存（J-Quants クライアント、RSS ニュース収集）
- DuckDB スキーマ定義と初期化
- 日次 ETL パイプライン（差分取得、保存、品質チェック）
- 研究用ユーティリティ（ファクター計算、将来リターン・IC 計算、統計）
- マーケットカレンダー管理、監査ログスキーマ等

本リポジトリは実運用を想定した設計方針（冪等性、レート制限順守、Look-ahead バイアス対策、SSRF 対策など）をあらかじめ組み込んでいます。

---

## 主な機能一覧

- 環境設定読み込みとバリデーション（.env 自動ロード、必須 env チェック）
- J-Quants API クライアント
  - 日足（OHLCV）、財務データ、マーケットカレンダー取得
  - レート制限（120 req/min）管理、リトライ、トークン自動リフレッシュ
  - DuckDB への冪等保存ユーティリティ
- DuckDB スキーマ定義（Raw / Processed / Feature / Execution 層）
  - テーブル作成・インデックス作成・監査ログスキーマ
- ETL パイプライン
  - 差分取得（最終取得日から自動算出／バックフィル）
  - 日次 ETL 実行（カレンダー → 株価 → 財務 → 品質チェック）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース収集（RSS）
  - URL 正規化、トラッキング除去、SSRF 対策、gzip 限度チェック
  - raw_news / news_symbols への冪等保存
- 研究用ファクター計算
  - Momentum / Volatility / Value 等の計算関数（prices_daily / raw_financials を参照）
  - 将来リターン計算、IC（Spearman）計算、統計サマリー
  - Zスコア正規化ユーティリティ

---

## 要求事項（依存関係）

- Python 3.10+
- 必須パッケージ（例）
  - duckdb
  - defusedxml

（その他は標準ライブラリで実装されています。実行時に必要なライブラリが増える場合がありますので適宜 requirements.txt を用意してください。）

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境の作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate.bat  # Windows
   ```

3. 必要パッケージのインストール
   ```
   pip install duckdb defusedxml
   ```

4. 環境変数の設定
   - プロジェクトルート（リポジトリ直下）に `.env` または `.env.local` を配置すると自動で読み込まれます（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると自動読み込みを無効化）。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
     - SLACK_BOT_TOKEN: Slack 通知用トークン（使用時）
     - SLACK_CHANNEL_ID: Slack チャネル ID（使用時）
     - KABU_API_PASSWORD: kabuステーション API パスワード（使用時）
   - 任意:
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL: DEBUG/INFO/…（デフォルト: INFO）
     - DUCKDB_PATH / SQLITE_PATH: データベースパス（デフォルトは data/ 配下）

   例（.env）:
   ```
   JQUANTS_REFRESH_TOKEN=xxxx...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456
   KABU_API_PASSWORD=your_pw
   DUCKDB_PATH=data/kabusys.duckdb
   ```

5. DuckDB スキーマの初期化
   - Python REPL / スクリプトで:
     ```python
     from kabusys.data import schema
     conn = schema.init_schema("data/kabusys.duckdb")
     ```
   - これで必要なテーブル・インデックスが作成されます。

---

## 使い方（例）

以下は主要なユースケースの簡単なサンプルです。

- 日次 ETL の実行
  ```python
  from datetime import date
  import kabusys
  from kabusys.data import schema, pipeline

  conn = schema.init_schema("data/kabusys.duckdb")
  result = pipeline.run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- J-Quants から日足を取得して保存（手動）
  ```python
  from kabusys.data import jquants_client as jq
  import duckdb

  # id_token を明示的に渡すか、モジュールキャッシュを利用
  id_token = jq.get_id_token()
  records = jq.fetch_daily_quotes(id_token=id_token, date_from=date(2024,1,1), date_to=date(2024,1,31))

  conn = duckdb.connect("data/kabusys.duckdb")
  saved = jq.save_daily_quotes(conn, records)
  print("saved:", saved)
  ```

- ニュース収集ジョブの実行
  ```python
  from kabusys.data import news_collector
  from kabusys.data import schema
  conn = schema.get_connection("data/kabusys.duckdb")  # init_schema で事前作成しておく
  results = news_collector.run_news_collection(conn, sources=None, known_codes={"7203","6758"})
  print(results)
  ```

- 研究用ファクター計算
  ```python
  from datetime import date
  import duckdb
  from kabusys.research import calc_momentum, calc_volatility, calc_value, zscore_normalize

  conn = duckdb.connect("data/kabusys.duckdb")
  t = date(2024, 1, 31)
  mom = calc_momentum(conn, t)
  vol = calc_volatility(conn, t)
  val = calc_value(conn, t)

  # 例: mom の一部カラムを Z スコア正規化
  normalized = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m", "ma200_dev"])
  ```

- 将来リターン・IC 計算（feature exploration）
  ```python
  from kabusys.research.feature_exploration import calc_forward_returns, calc_ic
  # forward returns を計算して factor と IC を計算する流れは上の関数群を組み合わせて使います
  ```

- 設定値にアクセス
  ```python
  from kabusys.config import settings
  print(settings.jquants_refresh_token)
  print(settings.duckdb_path)
  ```

---

## 環境変数 / 設定の詳細

- 自動 .env ロード
  - パッケージ起点でプロジェクトルート（.git または pyproject.toml があるディレクトリ）を探索し、`.env` → `.env.local` の順で読み込みます。
  - 既存 OS 環境変数は上書きされません（`.env.local` は override=True で上書き可能だが OS 環境変数は保護されています）。
  - 無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

- Settings に定義される主なプロパティ
  - jquants_refresh_token: J-Quants リフレッシュトークン（必須）
  - kabu_api_password / kabu_api_base_url: kabu API 関連
  - slack_bot_token / slack_channel_id: Slack 通知関連（必須：利用時）
  - duckdb_path / sqlite_path: DB ファイルパス
  - KABUSYS_ENV: "development" / "paper_trading" / "live"
  - LOG_LEVEL: ログレベル（DEBUG, INFO, ...）

---

## ディレクトリ構成

主要ファイル・モジュール（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py         # J-Quants API クライアント・保存ユーティリティ
    - news_collector.py        # RSS ニュース収集・正規化・保存
    - schema.py                # DuckDB スキーマ定義・初期化
    - pipeline.py              # ETL パイプライン（run_daily_etl 等）
    - features.py              # 特徴量ユーティリティ（再エクスポート）
    - stats.py                 # 統計ユーティリティ（zscore_normalize）
    - calendar_management.py   # マーケットカレンダー管理・ジョブ
    - audit.py                 # 監査ログ（order/signals/executions）用スキーマ
    - etl.py                   # ETL インターフェース再エクスポート
    - quality.py               # データ品質チェック
  - research/
    - __init__.py
    - feature_exploration.py   # 将来リターン / IC / summary
    - factor_research.py       # Momentum / Volatility / Value 等の計算
  - strategy/
    - __init__.py
  - execution/
    - __init__.py
  - monitoring/
    - __init__.py

（上記以外にも多くの関数／ユーティリティが各ファイルに実装されています。README は主要な使用例と設計方針をまとめたものです。）

---

## 開発メモ / 設計上の注意点

- 多くの処理は DuckDB の SQL ウィンドウ関数を用いて効率化しており、prices_daily / raw_financials / market_calendar テーブルの前提があります。
- J-Quants クライアントはモジュールレベルで id_token をキャッシュします。トークンリフレッシュは自動処理されます。
- ニュース収集では SSRF 対策・XML 脆弱性対策（defusedxml）・レスポンスサイズ制限が組み込まれています。
- ETL は Fail-Fast せず、品質チェック結果を収集して呼び出し元で判断できる設計です。
- DuckDB のバージョンや SQL 機能差異により若干の互換性問題が生じる可能性があります（外部キー・ON DELETE の制約等は注意）。

---

## 貢献 / 問い合わせ

設計・実装に関する質問やバグ報告、機能追加提案は Issue を立ててください。README は随時更新します。

---

README は以上です。追加でサンプルの .env.example や requirements.txt、実行用 CLI スクリプト等が欲しい場合はお知らせください。