# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
ETL、ニュース収集・AIセンチメント、ファクター計算、監査ログ、J-Quants クライアントなどを含むモジュール群を提供します。

バージョン: 0.1.0

## 概要

KabuSys は日本株アルゴリズム運用のための基盤ライブラリです。主な目的は次のとおりです。

- J-Quants からのデータ取得（株価日足、財務、マーケットカレンダー）
- DuckDB を使ったローカルデータストアと ETL パイプライン
- RSS ベースのニュース収集と OpenAI によるニュースセンチメント評価
- 市場レジーム判定（ETF + マクロニュースの合成）
- ファクター計算・研究ツール（モメンタム、バリュー、ボラティリティ、IC 等）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）テーブル初期化ユーティリティ
- 各種データ品質チェック、マーケットカレンダー管理

設計上の特徴：
- ルックアヘッドバイアス対策（target_date を明示し、 datetime.today() を参照しない設計）
- 冪等性（DB 保存は ON CONFLICT / DELETE→INSERT などで再実行可能）
- フェイルセーフ（API 失敗時はゼロフォールバックやスキップして継続）
- テスト容易性（外部呼び出しを注入またはモックしやすい設計）

## 機能一覧

- 環境設定管理（settings: .env、自動ロード機能）
  - 自動ロード順序: OS 環境 > .env.local > .env（プロジェクトルートを自動検出）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能
- J-Quants API クライアント（取得・保存・トークンリフレッシュ・レート制御）
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar
- ETL パイプライン（差分更新・バックフィル・品質チェック）
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - ETLResult 型による結果集約
- ニュース収集（RSS の安全取得、トラッキング除去、raw_news 保存）
- ニュース NLP（OpenAI を使った銘柄ごとのセンチメントスコアリング）
  - score_news(conn, target_date, api_key=None)
- 市場レジーム判定（ETF 1321 の MA とマクロニュースの LLM スコア合成）
  - score_regime(conn, target_date, api_key=None)
- 研究用ユーティリティ（ファクター計算、forward returns、IC、zscore 正規化）
  - calc_momentum / calc_value / calc_volatility / calc_forward_returns / calc_ic / factor_summary
- データ品質チェック（欠損・スパイク・重複・将来日付・非営業日データ）
  - run_all_checks 等
- 監査ログ初期化（監査用テーブル・インデックスを DuckDB に作成）
  - init_audit_schema / init_audit_db
- カレンダー管理（is_trading_day / next_trading_day / prev_trading_day / calendar_update_job）

## 動作要件

- Python 3.10 以上（タイプヒントに `|` を使用）
- 必須ライブラリ（例）:
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants / OpenAI / RSS）

実際のインストールで必要なパッケージはプロジェクトの requirements.txt に合わせてください。

## セットアップ手順

1. リポジトリをクローン / コピー

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml
   - （プロジェクトに requirements.txt があれば）pip install -r requirements.txt
   - または開発インストール:
     - pip install -e .

4. 環境変数設定
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env`（および任意で `.env.local`）を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 主要な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     - OPENAI_API_KEY=your_openai_api_key
     - KABU_API_PASSWORD=your_kabu_api_password
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - KABUSYS_ENV=development|paper_trading|live
     - LOG_LEVEL=INFO|DEBUG|...
   - `.env.example` を参考に作成してください（プロジェクトに存在する想定）。

5. データディレクトリの準備（必要なら）
   - settings.duckdb_path（デフォルト `data/kabusys.duckdb`）の親ディレクトリを作成するか、init 関数が自動作成します。

## 使い方（簡易）

以下は基本的な利用例です。実行は Python スクリプト/REPL で行えます。

- 設定の参照
  ```python
  from kabusys.config import settings
  print(settings.duckdb_path)  # Path オブジェクト
  print(settings.is_live)      # bool
  ```

- DuckDB に接続して日次 ETL を実行
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントスコア生成（OpenAI API キーが必要）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect(str(settings.duckdb_path))
  n = score_news(conn, target_date=date(2026, 3, 20))  # api_key を渡すことも可能
  print(f"scored {n} codes")
  ```

- 市場レジーム判定
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ DB 初期化
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")  # ディレクトリがなければ作成されます
  ```

注意点:
- AI 関連関数は OpenAI API キーを `api_key` 引数で明示的に渡すか、環境変数 `OPENAI_API_KEY` を設定してください。
- 多くの関数は target_date を必須にしており、コード内で現在時刻を直接参照しない設計です（バックテストでのルックアヘッド防止）。
- ETL / 保存処理は DuckDB のテーブル構造を前提としているため、必要なスキーマが存在する状態で動作させてください（スキーマ初期化コードは別途用意する想定）。

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN: J-Quants 用リフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（AI モジュールを使う場合必須）
- KABU_API_PASSWORD: kabu API パスワード
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視・モニタリング用 SQLite（デフォルト data/monitoring.db）
- KABUSYS_ENV: execution 環境 (development | paper_trading | live)
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動読み込みを無効化

.env の読み込みルール:
- プロジェクトルートを .git または pyproject.toml から自動検出
- 読み込み順: OS 環境 > .env.local > .env（.env.local は .env を上書き）
- 変数のパースはシェル風（export KEY=val, quotes, # コメント扱いの一部対応）

## テスト / モックについて

- OpenAI 呼び出し部分やネットワーク IO は unit test でモックしやすいように内部の呼び出し関数を切り出してあります（例: news_nlp._call_openai_api / regime_detector._call_openai_api を patch）。
- RSS 取得では `_urlopen` をモックして外部接続を防げます。
- J-Quants クライアントは get_id_token や _request を含むため id_token を注入してテストできます。

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                       -- 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                    -- ニュースセンチメント（AI）
    - regime_detector.py             -- 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py              -- J-Quants API クライアント & 保存処理
    - pipeline.py                    -- ETL パイプライン / run_daily_etl 等
    - etl.py                         -- ETL の公開型 ETLResult
    - news_collector.py              -- RSS ニュース収集
    - calendar_management.py         -- マーケットカレンダー管理
    - quality.py                     -- 品質チェック
    - stats.py                       -- 統計ユーティリティ（zscore_normalize）
    - audit.py                       -- 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py             -- モメンタム / ボラティリティ / バリュー
    - feature_exploration.py         -- forward returns / IC / summary
  - (その他)                          -- strategy / execution / monitoring 等プレースホルダ

各モジュールは DuckDB 接続（duckdb.DuckDBPyConnection）を受け取り SQL と Python を組み合わせて処理します。

## 運用上の注意

- J-Quants のレート制限（デフォルト 120 req/min）はクライアントで制御されています。大量バッチ処理を行う際はレートに注意してください。
- OpenAI 呼び出しはリトライ・バックオフが実装されていますが、API 利用料とレート制限に注意してください。
- データベースに保存されるタイムスタンプは UTC を想定しています（監査ログ等で明示）。
- 本リポジトリはバックテスト用のユーティリティ（研究モジュール）と運用用の ETL/監査を混在して提供します。実際の注文発注やライブ運用のロジック（kabu API 呼び出しなど）は別に注意深く実装・レビューしてください。

---

不明点や README に追加してほしい例（例: 具体的な .env.example、DuckDB スキーマの初期化スクリプト、CI/テスト手順など）があれば教えてください。必要に応じて追記します。