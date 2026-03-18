# KabuSys

日本株向けの自動売買／データ基盤ライブラリ。  
DuckDB をデータレイヤに用い、J-Quants からのマーケットデータ取得、ETL パイプライン、データ品質チェック、特徴量計算、ニュース収集、監査ログなどのユーティリティを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下を目的としたモジュール群を含むパッケージです。

- J-Quants API からの株価・財務・カレンダー取得（レート制御・リトライ・トークン自動更新対応）
- DuckDB ベースのスキーマ定義と初期化
- 日次 ETL パイプライン（差分取得・バックフィル・品質チェック）
- ニュース（RSS）収集と記事 → 銘柄紐付け
- ファクター（モメンタム / バリュー / ボラティリティ等）計算および研究用ユーティリティ
- 監査ログ（シグナル→発注→約定のトレーサビリティ）
- 環境設定管理（.env 自動読み込み、必須環境変数チェック）

設計方針として、本ライブラリは本番口座への発注を直接行わず、データ取得・処理・特徴量生成・監査ログ等のインフラ／ユーティリティを提供します。

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API からのデータ取得（ページネーション・レート制御・リトライ・トークン管理）
  - schema: DuckDB スキーマ定義と init / get_connection
  - pipeline: 日次 ETL（prices / financials / market calendar）と ETLResult 出力
  - news_collector: RSS 収集、前処理、ID 生成、DuckDB への冪等保存、記事→銘柄紐付け
  - quality: データ品質チェック（欠損、スパイク、重複、日付不整合）
  - stats: z-score 正規化などの統計ユーティリティ
  - calendar_management: market_calendar の更新と営業日判定ユーティリティ
  - audit: 監査ログテーブル定義と初期化（signal / order_request / executions）
- research/
  - factor_research: Momentum / Volatility / Value 等のファクター計算
  - feature_exploration: 将来リターン計算、IC（Information Coefficient）、ファクター統計サマリ
- config: 環境変数管理（.env 自動読み込み、必須チェック、設定プロパティ）
- execution / strategy / monitoring: 将来の発注・戦略・監視用のプレースホルダ（パッケージ公開）

---

## 前提・必要条件

- Python 3.10 以上（PEP 604 の型注釈 (X | Y) を使用しているため）
- 必要なパッケージ（最低限）
  - duckdb
  - defusedxml

プロジェクトの実行に応じて他パッケージが必要になる可能性があります（例えばロギングや Slack 通知等を実装する場合）。

pip でインストール例:
```
pip install duckdb defusedxml
```

（実プロジェクトでは requirements.txt / poetry / pyproject.toml を用いて依存管理してください）

---

## セットアップ手順

1. リポジトリをクローンする／ソースを配置する

2. Python 環境の準備（推奨: 仮想環境）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   pip install --upgrade pip
   pip install duckdb defusedxml
   ```

3. 環境変数 (.env) を作成する  
   プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` を配置すると自動読み込みされます（起動時に自動でロード）。  
   自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   必須の環境変数（コード上で required とされるもの）:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD: kabu ステーション等に接続する際のパスワード（将来の実装用）
   - SLACK_BOT_TOKEN: Slack 通知用ボットトークン（将来の実装用）
   - SLACK_CHANNEL_ID: Slack 通知先チャネル ID

   任意・デフォルトがある設定:
   - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）

   例 (.env):
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token_here
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development
   DUCKDB_PATH=data/kabusys.duckdb
   LOG_LEVEL=INFO
   ```

4. DuckDB スキーマ初期化（Python から）
   ```python
   from kabusys.config import settings
   from kabusys.data import schema

   conn = schema.init_schema(settings.duckdb_path)
   ```

---

## 使い方（代表的な例）

以下はパッケージの代表的な利用例です。

- データベース初期化
  ```python
  from kabusys.config import settings
  from kabusys.data import schema

  conn = schema.init_schema(settings.duckdb_path)  # ファイルがなければ生成
  ```

- 日次 ETL 実行（J-Quants トークンは settings から自動取得）
  ```python
  from datetime import date
  import kabusys.data.pipeline as pipeline
  from kabusys.data.schema import init_schema
  from kabusys.config import settings

  conn = init_schema(settings.duckdb_path)
  result = pipeline.run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- J-Quants から株価を直接取得して保存
  ```python
  import duckdb
  from kabusys.data import jquants_client as jq
  from kabusys.config import settings

  conn = duckdb.connect(settings.duckdb_path)
  # 例: 2024-01-01 から 2024-03-31 の全銘柄
  records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,3,31))
  saved = jq.save_daily_quotes(conn, records)
  print("saved", saved)
  ```

- ニュース収集ジョブの実行
  ```python
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  from kabusys.data.schema import init_schema
  from kabusys.config import settings

  conn = init_schema(settings.duckdb_path)
  # known_codes: 銘柄抽出に使う有効コードセット（例: all codes from universe）
  known_codes = {"7203", "6758", "9984"}
  stats = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
  print(stats)
  ```

- 研究向けファクター計算（例: モメンタム）
  ```python
  import duckdb
  from datetime import date
  from kabusys.research import calc_momentum, calc_forward_returns, calc_ic

  conn = duckdb.connect("data/kabusys.duckdb")
  target = date(2024, 3, 1)
  factors = calc_momentum(conn, target)
  fwd = calc_forward_returns(conn, target, horizons=[1,5,21])
  ic = calc_ic(factors, fwd, factor_col="mom_1m", return_col="fwd_1d")
  print("IC:", ic)
  ```

---

## 設定・運用上の注意

- .env の読み込みはプロジェクトルート（.git または pyproject.toml があるディレクトリ）から行われます。CI / テスト等で自動読み込みを無効にしたい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- KABUSYS_ENV は "development", "paper_trading", "live" のいずれかでなければエラーになります。
- J-Quants API のレート制限（120 req/min）やリトライロジックは jquants_client 内で管理されています。
- DuckDB への保存は多くの場所で ON CONFLICT DO UPDATE / DO NOTHING を使用して冪等化を図っています。
- news_collector は SSRF や XML Bomb 対策（defusedxml、受信バイト上限、ホストチェック）を組み込んでいますが、運用環境でのネットワークポリシー設定も推奨します。
- 監査ログ（audit モジュール）はタイムゾーンを UTC に固定しており、削除を前提としない設計です。

---

## ディレクトリ構成

（主要ファイルのみ）

- src/kabusys/
  - __init__.py
  - config.py                      : 環境変数 / 設定管理（.env 自動読み込み）
  - data/
    - __init__.py
    - jquants_client.py             : J-Quants API クライアント（取得 & 保存）
    - news_collector.py             : RSS 収集・前処理・DB 保存・銘柄抽出
    - schema.py                     : DuckDB スキーマ定義・初期化
    - pipeline.py                   : ETL パイプライン（run_daily_etl など）
    - quality.py                    : データ品質チェック
    - stats.py                      : zscore_normalize 等の統計ユーティリティ
    - features.py                   : 公開インターフェース（zscore の再エクスポート）
    - calendar_management.py        : market_calendar の管理・営業日判定
    - audit.py                      : 監査ログ（signal/order_request/executions 等）
    - etl.py                        : ETLResult のエクスポート
  - research/
    - __init__.py
    - factor_research.py            : モメンタム / バリュー / ボラティリティ計算
    - feature_exploration.py        : 将来リターン・IC・サマリー等
  - strategy/                        : 戦略関連（パッケージ境界、実装は別途）
  - execution/                       : 発注・ブローカー連携（パッケージ境界）
  - monitoring/                      : 監視・アラート（パッケージ境界）

---

## 開発者向け備考

- 型注釈・Docstring が比較的充実しています。ユニットテストを追加して品質チェック・ETL の挙動を担保することを推奨します。
- DuckDB のバージョンによってサポートされる機能に差があるため、本ライブラリの一部注記（例: ON DELETE CASCADE の未対応）を確認してください。
- 必要に応じて jquants_client の HTTP ユーティリティや rate limiter を調整できます（テストでは _urlopen やトークン取得の仕組みをモックしてください）。

---

質問や使い方の具体的なサンプルが必要であれば、やりたい処理（例: 特定銘柄のバックフィル / ある日付範囲の IC を計算するスクリプト等）を教えてください。具体的なコード例を用意します。