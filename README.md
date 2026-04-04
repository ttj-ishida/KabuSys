# KabuSys

KabuSys は日本株向けのデータプラットフォーム兼自動売買/リサーチ基盤です。J-Quants / RSS / OpenAI など外部データ・API を取り込み、ETL → 品質チェック → ファクター算出 → 戦略・発注（監査トレース）までのワークフローをサポートします。設計は「ルックアヘッドバイアスの排除」「冪等性」「フェイルセーフ性」を重視しています。

バージョン: 0.1.0

---

## 主な機能

- データ収集・ETL
  - J-Quants からの株価日足・財務・上場情報・市場カレンダー取得（ページネーション・レート制御・トークン自動リフレッシュ）
  - RSS ニュース収集（トラッキングパラメータ除去、SSRF 対策、前処理、冪等保存）
  - DuckDB への冪等保存（ON CONFLICT/アップサート）

- データ品質管理
  - 欠損・重複・スパイク（前日比）・日付不整合チェック（quality モジュール）
  - ETL 実行結果の集約（ETLResult）

- ニュースNLP / レジーム判定（AI）
  - ニュース記事を OpenAI（gpt-4o-mini）でセンチメント化し ai_scores に保存（news_nlp）
  - マクロセンチメント + ETF(1321)の 200 日 MA 乖離を合成して市場レジーム判定（regime_detector）
  - API 呼び出しはリトライ・バックオフ・フェイルセーフ化済み

- リサーチ用ファクター計算
  - Momentum / Volatility / Value 等のファクター算出（research モジュール）
  - 将来リターン計算、IC（スピアマン）計算、統計サマリー、Zスコア正規化（data.stats）

- 監査ログ（トレーサビリティ）
  - signal_events, order_requests, executions の監査テーブル定義と初期化ユーティリティ（audit モジュール）
  - order_request_id による冪等制御、UTC タイムスタンプ保存

- ユーティリティ
  - 市場カレンダー管理（is_trading_day / next_trading_day / prev_trading_day / get_trading_days）
  - 各種ユーティリティ・型安全なパーサ・トリム処理など

---

## 必要条件（想定）

- Python 3.10+
- 依存ライブラリ（主なもの）
  - duckdb
  - openai（OpenAI の v1 SDK を想定）
  - defusedxml
  - その他標準ライブラリ

（実際の requirements.txt はリポジトリに合わせて作成してください）

---

## インストール（開発環境向けの例）

1. 仮想環境を作成・有効化（例: venv）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

2. 必要パッケージをインストール（例）
   ```
   pip install duckdb openai defusedxml
   ```

3. パッケージを編集可能インストール（任意）
   ```
   pip install -e .
   ```

---

## 環境変数 / 設定

KabuSys は環境変数とプロジェクトルートの .env / .env.local を自動読み込みします（自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。

重要な環境変数（主なもの）:

- JQUANTS_REFRESH_TOKEN
  - J-Quants のリフレッシュトークン（必須、ETL・データ取得に使用）

- OPENAI_API_KEY
  - OpenAI API キー（news_nlp / regime_detector の呼び出しで使用）

- KABU_API_PASSWORD
  - kabuステーション API のパスワード（必要に応じて）

- KABUSYS_ENV
  - 環境。 "development" / "paper_trading" / "live" のいずれか（デフォルト: development）

- LOG_LEVEL
  - ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL。デフォルト: INFO）

- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PID_FILE_PATH / KILL_FLAG_PATH など監視関連設定

.env の読み込みルールのポイント:
- .env がプロジェクトルート（.git または pyproject.toml を探索）にあれば自動で読み込みます。
- 読み込み順: OS 環境変数 > .env.local > .env
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを抑止できます。

---

## セットアップ（DB 初期化など）

- 監査テーブルを初期化して専用 DuckDB を作る例:
  ```python
  from kabusys.data.audit import init_audit_db

  # ":memory:" でも可。ファイルパスを指定すると親ディレクトリを自動作成します。
  conn = init_audit_db("data/audit.duckdb")
  ```

- コードや関数に直接接続して ETL / 処理を実行する（例は Quickstart で示します）。

---

## Quickstart（主要ユースケースの使い方）

以下は Python スクリプト／REPL で直接呼び出す例です。いずれも settings（kabusys.config.settings）から環境を読み込みます。

- 日次 ETL を実行する
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  # DuckDB ファイルに接続（デフォルトパスは settings.duckdb_path を参照）
  conn = duckdb.connect("data/kabusys.duckdb")

  # ETL を実行（target_date を省略すると今日）
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュース NLP スコアを生成して ai_scores に保存する
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-xxxx")
  print("書き込み銘柄数:", written)
  ```

- 市場レジーム判定を実行する
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-xxxx")
  ```

- ファクター計算（リサーチ）
  ```python
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum, calc_volatility, calc_value

  conn = duckdb.connect("data/kabusys.duckdb")
  date0 = date(2026, 3, 20)
  mom = calc_momentum(conn, date0)
  vol = calc_volatility(conn, date0)
  val = calc_value(conn, date0)
  ```

- ETL 実行結果（ETLResult）を確認して品質問題を把握する

  run_daily_etl が返す ETLResult の .quality_issues に QualityIssue オブジェクトが含まれます。これをログ・アラートや運用判断に使用してください。

---

## 注意事項 / 設計上のポイント

- ルックアヘッドバイアス防止:
  - 多くのモジュールは date.today()/datetime.today() を直接参照せず、caller が target_date を渡す設計です。バックテスト用途ではバックテストループから直接呼ばないでください（ETL で事前にデータを用意することが推奨されます）。

- 冪等性:
  - API から取得したデータは保存時に ON CONFLICT（アップサート）で冪等に保存されます。

- フェイルセーフ:
  - OpenAI など外部 API 呼び出しはリトライ/バックオフや失敗時のデフォールト値（例: macro_sentiment=0.0）を用意しています。API の一時故障でパイプライン全体が停止しないようになっています。

- テスト容易性:
  - OpenAI 呼び出し・HTTP オープン関数などは内部でラップされており、unittest.mock.patch により差し替えてユニットテストが行いやすく設計されています。

---

## ディレクトリ構成（主要ファイル）

以下はこのリポジトリ内の主要モジュール構成（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                     - 環境変数 / 設定読み込みロジック
  - ai/
    - __init__.py
    - news_nlp.py                  - ニュースセンチメント分析（OpenAI）
    - regime_detector.py           - 市場レジーム判定（MA + マクロセンチメント合成）
  - data/
    - __init__.py
    - jquants_client.py            - J-Quants API クライアント（取得 + DuckDB 保存）
    - pipeline.py                  - ETL パイプライン（run_daily_etl など）
    - calendar_management.py       - 市場カレンダー管理（営業日判定等）
    - news_collector.py            - RSS ニュース収集
    - quality.py                   - データ品質チェック
    - stats.py                     - 汎用統計ユーティリティ（zscore_normalize 等）
    - etl.py                       - ETL インターフェース再エクスポート
    - audit.py                     - 監査ログスキーマ初期化（signal/order/execution）
  - research/
    - __init__.py
    - factor_research.py           - ファクター算出（momentum, value, volatility）
    - feature_exploration.py       - 将来リターン・IC・統計サマリー等
  - ai/__init__.py
  - research/__init__.py

（上記は本 README に含まれるファイル抜粋です。実際のソース全体は src/kabusys 以下を参照してください）

---

## 貢献 / 開発メモ

- コードは「DuckDB + 標準ライブラリ」を優先して書かれており、外部依存は最小限に抑えられています。必要な追加パッケージは requirements.txt を用意して管理してください。
- OpenAI 呼び出しや外部 HTTP のエントリはラップされているため、モック差し替えによるユニットテストが容易です（例: kabusys.ai.news_nlp._call_openai_api をモック）。
- 運用では .env / .env.local に API キー等を保存し、KABUSYS_DISABLE_AUTO_ENV_LOAD を適切に設定してテスト／CI を行ってください。

---

もし README に含めてほしい追加情報（例: CI 手順、具体的な SQL スキーマ、requirements.txt、実行スクリプトなど）があれば教えてください。必要に応じて追記します。