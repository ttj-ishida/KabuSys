# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ。  
DuckDB をデータ層に、J-Quants や RSS / OpenAI を活用してデータ取得、品質チェック、ニュース NLP、戦略研究、監査ログ（トレーサビリティ）を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は次の要件を満たすことを目標としたモジュール群です。

- J-Quants API から株価・財務・マーケットカレンダーを差分取得して DuckDB に保存する ETL。
- RSS ベースのニュース収集とニュースを LLM（OpenAI）でスコアリングする機能。
- 市場レジーム判定（ETF 1321 の MA とマクロニュースの LLM センチメントを合成）。
- 研究用ファクター計算・特徴量探索ユーティリティ（モメンタム、ボラティリティ、バリューなど）。
- データ品質チェック（欠損・スパイク・重複・日付不整合）。
- 監査ログ（signal → order_request → execution のトレーサビリティ）用テーブル定義と初期化。
- 環境変数 / .env の自動読み込み（プロジェクトルート検出に基づく）。

設計方針として、バックテストのルックアヘッドバイアスを避けるために datetime.now()/today() を直接参照しない実装や、API 呼び出し時のフォールバック・リトライ・フェイルセーフを重視しています。

---

## 主な機能一覧

- data/
  - ETL（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（fetch / save 各種）
  - カレンダー管理（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, calendar_update_job）
  - ニュース収集（fetch_rss, 前処理・SSRF 対策）
  - データ品質チェック（check_missing_data, check_spike, check_duplicates, check_date_consistency, run_all_checks）
  - 監査ログ初期化（init_audit_schema, init_audit_db）
  - 統計ユーティリティ（zscore_normalize）
- ai/
  - news_nlp.score_news: ニュースを LLM で銘柄別にスコアリングし ai_scores テーブルへ書き込み
  - regime_detector.score_regime: ETF 1321 の MA200 乖離とマクロニュース LLM を合成して market_regime へ書込
- research/
  - factor_research.calc_momentum / calc_volatility / calc_value
  - feature_exploration.calc_forward_returns / calc_ic / factor_summary / rank
- config.py
  - .env 自動読み込み（.git または pyproject.toml があるプロジェクトルートを探索）
  - settings オブジェクト経由で設定アクセス（JQUANTS_REFRESH_TOKEN 等）
  - 自動ロード無効化環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD

---

## 前提（Prerequisites）

- Python 3.10+
- パッケージ（pip インストール推奨）:
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリ以外の追加が必要になった場合は setup.py/pyproject.toml を参照）

---

## セットアップ手順

1. リポジトリをクローンして開発環境を準備

   ```bash
   git clone <repo-url>
   cd <repo-dir>
   python -m venv .venv
   source .venv/bin/activate
   pip install -U pip
   pip install duckdb openai defusedxml
   # 開発インストール (パッケージ化されている場合)
   pip install -e .
   ```

2. 環境変数の準備

   プロジェクトルートに `.env` を置くと自動的に読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると無効化可）。最低限必要な値:

   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime 実行時に必要）
   - KABU_API_PASSWORD: kabuステーション API パスワード（注文周りで使用する場合）
   - 任意で:
     - KABUSYS_ENV (development | paper_trading | live)
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視DB, default: data/monitoring.db）
     - LOG_LEVEL（DEBUG/INFO/...）

   サンプル `.env`（プロジェクトルート）:

   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-xxxx...
   KABU_API_PASSWORD=your_kabu_password
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   ```

3. データディレクトリを作成（必要に応じて）

   ```bash
   mkdir -p data
   ```

---

## 初期化・よく使う操作（使い方）

以下は Python からの利用例です。DuckDB コネクションは kabusys の関数に渡して利用します。

- DuckDB に接続

  ```python
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  ```

- 監査ログ（audit）用 DB 初期化（専用 DB を使う場合）

  ```python
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit.duckdb")  # ファイル: data/audit.duckdb
  ```

- 日次 ETL を実行（市場カレンダー・株価・財務・品質チェック）

  ```python
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  # conn: duckdb connection
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニューススコアを生成（AI スコアリング）

  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  n = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-xxxx")
  print(f"scored {n} codes")
  ```

  api_key を引数で渡さない場合は環境変数 OPENAI_API_KEY を参照します。

- 市場レジームスコアを算出

  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026,3,20), api_key=None)  # OPENAI_API_KEY を使用
  ```

- カレンダーの夜間更新ジョブ

  ```python
  from kabusys.data.calendar_management import calendar_update_job
  calendar_update_job(conn)
  ```

- 研究用ファクター計算

  ```python
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  from datetime import date

  mom = calc_momentum(conn, date(2026,3,20))
  vol = calc_volatility(conn, date(2026,3,20))
  val = calc_value(conn, date(2026,3,20))
  ```

- データ品質チェックの実行

  ```python
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=date(2026,3,20))
  for i in issues:
      print(i)
  ```

- .env 自動読み込みを抑止する（テスト等）

  ```bash
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```

---

## よくある運用メモ

- OpenAI 呼び出しはリトライ・フォールバックロジックを持ちますが、API キーが無いと明示的に ValueError が投げられます。実行前に OPENAI_API_KEY を設定してください。
- J-Quants の API はレート制限（120 req/min）を想定しておりモジュール側でスロットリングとリトライを行います。長期的にはバッチスケジューラでの夜間実行が想定されます。
- ETL は差分更新・バックフィル（既存最終日から数日前を再取得）を行い、後出し修正を吸収します。
- DuckDB へ保存する際は冪等（ON CONFLICT DO UPDATE / DO NOTHING）で実装されています。
- ニュース収集は SSRF 対策（リダイレクト検査、プライベート IP ブロック）や XML の安全なパース（defusedxml）を実装しています。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py
    - ai/
      - __init__.py
      - news_nlp.py
      - regime_detector.py
    - data/
      - __init__.py
      - jquants_client.py
      - pipeline.py
      - etl.py (re-export)
      - calendar_management.py
      - news_collector.py
      - quality.py
      - stats.py
      - audit.py
      - (その他: schema や補助モジュール想定)
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - monitoring/ (監視用モジュール群想定)
    - strategy/ (戦略実装用モジュール想定)
    - execution/ (発注・ブローカー連携想定)

各モジュールはドメインごとに分割され、DuckDB 接続を受け取る設計になっています（副作用を極力排除）。

---

## 開発・テストのヒント

- 環境変数の自動ロードはプロジェクトルート（.git または pyproject.toml があるディレクトリ）を探索して .env / .env.local を読み込みます。ユニットテストでは KABUSYS_DISABLE_AUTO_ENV_LOAD を有効にして制御することを推奨します。
- OpenAI 呼び出しやネットワーク I/O 部分はモックしやすいように内部呼び出し関数（_call_openai_api, _urlopen 等）を分離しています。ユニットテストではこれらを patch して利用してください。
- DuckDB は軽量でメモリ内 DB も可能（":memory:"）。テストではメモリ DB を使うと高速です。

---

## ライセンス / 貢献

この README はコードベースの概要と使い方に焦点を当てています。実際のリポジトリに LICENSE や CONTRIBUTING ガイドがあればそちらを参照してください。

---

何か追記してほしい箇所（例: 実行スクリプトのサンプル、CI の設定、具体的な依存バージョンなど）があれば教えてください。