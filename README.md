# KabuSys

日本株向けの自動売買／データ基盤ライブラリ群です。  
データ ETL、ニュース収集・NLP スコアリング、ファクター計算（リサーチ）、市場レジーム判定、監査ログ（トレーサビリティ）など、自動売買システムに必要な基盤機能を提供します。

---

## 概要

KabuSys は以下の主要コンポーネントを含みます。

- J-Quants API クライアント（株価・財務・カレンダーの取得、レート制御・リトライ付き）
- ETL パイプライン（日次差分取得・保存・品質チェック）
- マーケットカレンダー管理（営業日判定、next/prev/trading day 等）
- ニュース収集（RSS -> raw_news、SSRF/サイズ対策付き）
- ニュース NLP（OpenAI を使った銘柄別センチメントスコア化）
- 市場レジーム判定（ETF 1321 の MA200 乖離 + マクロセンチメントの合成）
- リサーチ用ファクター計算（モメンタム、ボラティリティ、バリュー等）と統計ユーティリティ
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 監査ログ（signal → order_request → execution のトレーサビリティ用スキーマ初期化）

設計上の方針として、ルックアヘッドバイアス回避（内部で date.today()/datetime.today() を不用意に参照しない）、冪等性（DB 保存は ON CONFLICT / upsert）、フェイルセーフ（API 失敗はフォールバックして処理を継続）を重視しています。

---

## 機能一覧（抜粋）

- kabusys.config
  - .env 自動読み込み（プロジェクトルート検出）・環境変数ラッパー
  - 必須環境変数チェック（例: JQUANTS_REFRESH_TOKEN, OPENAI_API_KEY 等）
- kabusys.data.jquants_client
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar
  - get_id_token（リフレッシュトークンから ID トークン取得）
  - レート制御（120 req/min）・リトライ・401 リフレッシュ対応
- kabusys.data.pipeline
  - run_daily_etl: カレンダー→株価→財務→品質チェック を順に実行
  - 個別 ETL ジョブ（run_prices_etl, run_financials_etl, run_calendar_etl）
  - ETLResult 型（実行結果のサマリ）
- kabusys.data.news_collector
  - RSS 取得・記事正規化・ID 生成・SSRF 対策・保存用のデータ整形
- kabusys.ai.news_nlp
  - calc_news_window（対象ウィンドウ計算）
  - score_news：OpenAI による銘柄別センチメント取得 → ai_scores テーブルへ保存
- kabusys.ai.regime_detector
  - _calc_ma200_ratio（ETF 1321 の MA200 乖離）
  - _score_macro（マクロニュースを LLM に投げてスコア算出）
  - score_regime：MA と マクロを合成して market_regime に保存
- kabusys.research
  - calc_momentum / calc_volatility / calc_value
  - calc_forward_returns / calc_ic / factor_summary / rank
- kabusys.data.quality
  - 欠損 / 重複 / スパイク / 日付不整合 チェック
- kabusys.data.audit
  - 監査ログ DB スキーマ初期化（init_audit_schema / init_audit_db）

---

## 必要条件（推奨）

- Python 3.10+
  - 依存点: 型ヒントで `X | None` を使用しているため 3.10 以上を想定しています。
- 主な Python パッケージ（例）
  - duckdb
  - openai
  - defusedxml
  - その他: 標準ライブラリのみで多くを実装していますが、プロジェクトの packaging に従って必要パッケージを追加してください。

---

## セットアップ手順

1. リポジトリをクローン（例）
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境の作成（例）
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   ```

3. 必要パッケージのインストール（例）
   - 最低限:
     ```bash
     pip install duckdb openai defusedxml
     ```
   - パッケージ化されている場合:
     ```bash
     pip install -e .
     ```

4. 環境変数（.env）を用意
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（kabusys.config）。
   - 自動ロードを無効にする場合:
     ```bash
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 主要な環境変数例（必須）
     - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン
     - KABU_API_PASSWORD: kabuステーション API パスワード
     - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知用
     - OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で使用）
   - 例 (.env の最小例)
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=sk-...
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     KABU_API_PASSWORD=your_password
     LOG_LEVEL=INFO
     KABUSYS_ENV=development
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     ```

---

## 使い方（サンプル）

以下は Python REPL / スクリプトからの利用例です。

- 設定値参照
  ```python
  from kabusys.config import settings
  print(settings.duckdb_path)
  ```

- DuckDB 接続と日次 ETL 実行
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- News NLP スコア（OpenAI API キーは環境変数 OPENAI_API_KEY）
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news
  import duckdb

  conn = duckdb.connect(str(settings.duckdb_path))
  n_written = score_news(conn, date(2026, 3, 20))
  print("書き込み銘柄数:", n_written)
  ```

- 市場レジーム判定
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime
  import duckdb

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, date(2026, 3, 20))
  ```

- 監査ログ DB 初期化（監査用 DuckDB）
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit_duckdb.duckdb")
  # conn を用いて監査ログに書き込み可能
  ```

- RSS フェッチ（ニュース収集）
  ```python
  from kabusys.data.news_collector import fetch_rss
  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
  for a in articles[:5]:
      print(a["datetime"], a["title"])
  ```

注意点:
- OpenAI 呼び出しは API レートや課金が発生します。テスト時は関数内部の _call_openai_api をモックすることを推奨します（README 内の各モジュールで patch を想定）。
- ETL / 保存処理は DuckDB スキーマ（raw_prices / raw_financials / market_calendar 等）に依存します。スキーマ初期化が必要な場合はプロジェクトの schema 初期化処理に従ってください。

---

## 開発・テスト向けヒント

- テストで自動 .env 読み込みを無効化する:
  ```bash
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```
- OpenAI 呼び出しをテストで差し替える:
  - unittest.mock.patch で kabusys.ai.news_nlp._call_openai_api や kabusys.ai.regime_detector._call_openai_api をモックしてください。
- DuckDB はインメモリ ":memory:" を使用できます（init_audit_db 等は対応）。
- ログレベルは LOG_LEVEL 環境変数で制御（DEBUG / INFO / WARNING / ERROR / CRITICAL）。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py
- ai/
  - __init__.py
  - news_nlp.py
  - regime_detector.py
- data/
  - __init__.py
  - calendar_management.py
  - pipeline.py
  - etl.py
  - jquants_client.py
  - news_collector.py
  - quality.py
  - stats.py
  - audit.py
  - (etl の結果クラス等)
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- research と ai, data 間で利用するユーティリティや関数群が含まれます。

（上の一覧はこのコードベースに含まれる主要ファイルの抜粋です。パッケージ全体のファイルはリポジトリを参照してください。）

---

## 運用上の注意

- 本ライブラリは実取引（live）とペーパートレード（paper_trading）を区別する設定（KABUSYS_ENV）を持ちます。設定値は `development | paper_trading | live` のいずれかにしてください。
- 実際の発注／決済ロジックは本リポジトリの別モジュール（execution / strategy 等）で実装されることを想定しています。data/research/ai モジュールは主にデータ処理・解析・スコアリングを提供します。
- J-Quants / OpenAI / 証券 API の鍵・資格情報は適切に管理してください（.env ファイルの権限管理等）。
- DB 操作は多くが冪等性（ON CONFLICT）を取っていますが、バックアップ・監査は運用ポリシーに従って実施してください。

---

この README はコードベースの現状に基づいて作成しています。パッケージのビルド手順や追加のランタイム依存はリポジトリ内の packaging・CI 設定（pyproject.toml 等）がある場合はそちらを参照してください。必要であれば README に起動スクリプト例や SQL スキーマ生成手順なども追加できます。