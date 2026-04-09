# KabuSys

日本株向けの自動売買 / データプラットフォーム用 Python パッケージ群です。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集・NLP（OpenAI）によるセンチメント評価、リサーチ用ファクター計算、監査ログ（発注〜約定のトレーサビリティ）などを含みます。

---

## 特徴（機能一覧）

- データ取得（J-Quants）
  - 株価日足（OHLCV）、財務データ、JPX カレンダーの差分取得・ページネーション対応
  - レートリミット管理、トークン自動リフレッシュ、リトライ（指数バックオフ）
  - DuckDB への冪等保存（ON CONFLICT 相当）

- ETL パイプライン
  - 日次 ETL（市場カレンダー → 株価 → 財務 → 品質チェック）
  - 品質チェック（欠損、重複、スパイク、日付不整合）を報告

- ニュース収集
  - RSS 取得、URL 正規化、SSRF 防御、前処理、raw_news / news_symbols への冪等登録

- ニュース NLP（OpenAI）
  - ニュースを銘柄ごとにまとめて gpt-4o-mini（JSON Mode）へ送信し ai_scores に保存
  - バッチ処理、リトライ、レスポンスバリデーション、スコアの ±1.0 クリップ

- 市場レジーム判定（Regime Detector）
  - ETF (1321) の 200 日 MA 乖離（70%）とマクロニュース LLM センチメント（30%）を合成して
    market_regime テーブルへ冪等書き込み（bull / neutral / bear）

- リサーチ用ツール
  - Momentum / Volatility / Value 等のファクター計算
  - 将来リターン、IC（Spearman rank）、ファクター統計サマリー、Z スコア正規化

- 監査ログ（Audit）
  - signal_events, order_requests, executions を含む監査スキーマを DuckDB に初期化・管理
  - 発注フローの完全なトレーサビリティ（UUID ベース）

- 設定管理
  - 環境変数（.env / .env.local の自動ロード、プロジェクトルート検出）
  - 実行環境区分（development / paper_trading / live）やログレベル、DB パス等を管理

---

## セットアップ手順

必要条件
- Python 3.9+（型注釈により 3.9+ を想定）
- ネットワークアクセス（J-Quants / OpenAI / RSS）

推奨インストール例:

1. リポジトリをクローン（またはパッケージソースを用意）
2. 仮想環境作成・有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```
3. 依存パッケージのインストール（例）
   ```bash
   pip install duckdb openai defusedxml
   # またはパッケージが pyproject.toml を提供している場合:
   pip install -e .
   ```
   ※ 実際の依存一覧は pyproject.toml / requirements に従ってください。

4. 環境変数 / .env の準備  
   プロジェクトルート（.git または pyproject.toml を含むディレクトリ）に `.env` と `.env.local` を配置できます。
   自動読み込み挙動:
   - OS 環境変数 > .env.local > .env の優先順位で読み込み（デフォルト）
   - テスト等で自動ロード無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定

   主要な環境変数（例）
   - JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
   - OPENAI_API_KEY (必須 for NLP) — OpenAI API キー（score_news / score_regime 実行時）
   - KABU_API_PASSWORD — kabuステーション API 用パスワード
   - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
   - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
   - PAPER_FILL_MODE — paper_trading の挙動 ("instant" | "partial" | "never" | "reject")
   - KABUSYS_ENV — 実行環境 ("development", "paper_trading", "live")
   - LOG_LEVEL — ログレベル ("DEBUG","INFO",...)

   例 .env:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
   OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. 監査DBの初期化（オプション）
   ```python
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")
   ```

---

## 使い方（簡単な利用例）

以下は代表的な API 呼び出し例です。DuckDB 接続に対して各関数を呼び出します。

- 日次 ETL 実行（run_daily_etl）
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントスコア（score_news）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数 OPENAI_API_KEY を使う
  print("書き込み銘柄数:", n_written)
  ```

- 市場レジーム判定（score_regime）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- リサーチ関数（例: モメンタム）
  ```python
  import duckdb
  from datetime import date
  from kabusys.research.factor_research import calc_momentum

  conn = duckdb.connect("data/kabusys.duckdb")
  records = calc_momentum(conn, target_date=date(2026,3,20))
  ```

- 監査スキーマの初期化
  ```python
  import duckdb
  from kabusys.data.audit import init_audit_schema

  conn = duckdb.connect("data/kabusys.duckdb")
  init_audit_schema(conn, transactional=True)
  ```

注意:
- OpenAI を使う関数は API キーが必要です（引数で明示的に渡すか環境変数 OPENAI_API_KEY を利用）。
- ETL / ニュース収集 / NLP は外部 API を呼ぶためネットワーク・課金に注意してください。
- 本ライブラリの設計方針として、ルックアヘッドバイアスを避けるために date.today()/datetime.today() を内部で直接使わないよう配慮されています（API 呼び出し時に明示的に target_date を渡すことを推奨）。

---

## 主要モジュール（簡易ディレクトリ構成）

ソースは `src/kabusys` 配下にあります。主要ファイルを抜粋すると:

- kabusys/
  - __init__.py
  - config.py  — 環境変数 / 自動 .env ロード / Settings
  - ai/
    - __init__.py
    - news_nlp.py       — ニュースセンチメント取得（score_news）
    - regime_detector.py — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py   — J-Quants API クライアント & DuckDB 保存関数
    - pipeline.py        — ETL パイプライン（run_daily_etl 等）
    - etl.py             — ETLResult の再エクスポート
    - news_collector.py  — RSS 取得・前処理・raw_news 保存
    - quality.py         — データ品質チェック
    - stats.py           — zscore_normalize 等の統計ユーティリティ
    - calendar_management.py — 市場カレンダー管理（is_trading_day 等）
    - audit.py           — 監査ログスキーマ初期化 / init_audit_db
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py

（上記は主要ファイルの抜粋です。プロジェクトの完全な構成はソースツリーを参照してください。）

---

## 設定と動作の注意点

- .env 自動読み込み
  - `kabusys.config` はプロジェクトルート（.git または pyproject.toml があるディレクトリ）を基準に `.env` と `.env.local` を自動読み込みします。
  - 読み込み順: OS 環境変数 > .env.local > .env
  - 自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用途など）。
  - .env のパースはクォート・コメント行・export 形式を考慮した実装です。

- 環境（KABUSYS_ENV）
  - 有効値: `development`, `paper_trading`, `live`
  - `paper_trading` 時は Paper Trading の挙動（PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH 等）に注意してください。

- OpenAI 呼び出し・リトライ
  - news_nlp / regime_detector は OpenAI API 呼び出しに対して指数バックオフ・リトライ・レスポンスバリデーションを行います。API 失敗時はフェイルセーフとしてスコアに 0 を採用したり、処理をスキップしたりする設計です。

- DuckDB について
  - デフォルトの DB パスは `data/kabusys.duckdb`（Settings.duckdb_path で変更可）。
  - ETL 等の実行前にスキーマを用意する必要がある場合は、適切なスキーマ初期化処理を実行してください（プロジェクトに別途 schema 初期化コードがある想定）。

---

## 開発・テスト時のヒント

- テスト時に外部 API 呼び出しを避けるには、OpenAI クライアントや jquants_client の HTTP 呼び出し箇所をモックしてください。news_nlp / regime_detector は内部の _call_openai_api をパッチすることを想定して設計されています。
- `.env.local` を CI 固有の設定で使用し、ローカル `.env` を .gitignore に含めることで秘密情報の管理を行ってください。
- DuckDB は軽量なのでテストでは `:memory:` を使うことで高速に DB 初期化できます。

---

必要であれば、README に含める具体的な .env.example、CI 用の設定例、またはコマンドライン実行スクリプト（例: daily_etl.py）テンプレートの追加も作成します。どの情報を詳しく載せたいか教えてください。