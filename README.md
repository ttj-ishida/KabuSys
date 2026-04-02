# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集・NLP（OpenAI でのセンチメント評価）、市場レジーム判定、ファクター・リサーチ、監査ログ（約定トレーサビリティ）などを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下を目的とする内部ユーティリティ群です。

- J-Quants API からの差分 ETL（株価日足 / 財務 / 市場カレンダー）
- RSS ニュース収集と前処理（SSRF 対策、トラッキング除去）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント評価（銘柄別／マクロ）
- ETF を用いた市場レジーム判定（MA200 とマクロセンチメントの合成）
- ファクター計算・特徴量探索（モメンタム、バリュー、ボラティリティ、IC 等）
- データ品質チェック（欠損・スパイク・重複・日付整合性）
- 監査ログ（signal → order_request → execution のトレーサビリティ）
- DuckDB ベースのデータ保存（冪等性を考慮した保存関数）

設計方針として、バックテストでのルックアヘッドバイアス回避（内部で datetime.today()/date.today() を不用意に参照しない）や、API 呼び出し時のリトライ・フェイルセーフ処理、DB 書き込みの冪等性を重視しています。

---

## 主な機能一覧

- data/
  - ETL パイプライン（run_daily_etl 等）
  - J-Quants クライアント（fetch / save / 認証・レートリミット対応）
  - カレンダー管理（営業日判定、next/prev/get_trading_days）
  - ニュース収集（RSS → raw_news 保存、SSRF 対策）
  - データ品質チェック（missing / spike / duplicates / date consistency）
  - 監査ログ初期化・DB（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore 正規化）
- ai/
  - news_nlp.score_news: ニュースを銘柄ごとにまとめて OpenAI でスコア化し ai_scores に保存
  - regime_detector.score_regime: ETF(1321) の MA200 乖離とマクロセンチメントを合成して market_regime に保存
- research/
  - ファクター計算（momentum / value / volatility）
  - 将来リターン計算、IC（Spearman）計算、統計サマリー
- config:
  - .env 自動読み込み（プロジェクトルートの .env / .env.local、KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可）
  - settings オブジェクト経由の設定アクセス（パスやAPIトークン）

---

## 必要な環境変数

主に以下が必須またはよく使われます（デフォルト値があるものは任意）。

必須（実行する機能による）:
- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（ETL に必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（発注系がある場合）
- SLACK_BOT_TOKEN — Slack 通知を使う場合
- SLACK_CHANNEL_ID — Slack 通知先チャンネル
- OPENAI_API_KEY — OpenAI 呼び出し（news_nlp / regime_detector）を行う場合

任意（デフォルトあり）:
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- LOG_LEVEL (DEBUG|INFO|...) — デフォルト: INFO
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT

.env 自動読み込み:
- パッケージはプロジェクトルート（.git または pyproject.toml を探索）を検出すると、.env → .env.local の順で自動で読み込みます。
- 自動読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

例 (.env):
```
JQUANTS_REFRESH_TOKEN=xxxx...
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
```

---

## セットアップ手順（開発環境向け）

1. リポジトリをクローン / ソースを配置
2. Python 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml
   - （プロジェクト配布用に setup / pyproject があれば pip install -e . 等）
4. 環境変数を設定
   - 上の .env をプロジェクトルートに作成するか、環境変数を直接 export してください。
5. DuckDB 用ディレクトリを作成（必要に応じて）
   - mkdir -p data

推奨ライブラリ（使用する機能により追加）:
- duckdb
- openai (OpenAI Python SDK)
- defusedxml

---

## 使い方（簡単な例）

- DuckDB 接続準備
  - Python スクリプト等で duckdb.connect(settings.duckdb_path) を使って接続します。
  - 例:
    ```python
    import duckdb
    from kabusys.config import settings
    conn = duckdb.connect(str(settings.duckdb_path))
    ```

- 日次 ETL 実行（株価・財務・カレンダー取得 + 品質チェック）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  import duckdb
  from kabusys.config import settings
  from datetime import date

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースの AI スコア付け（OpenAI API キーは OPENAI_API_KEY 環境変数、または api_key 引数で渡す）
  ```python
  from kabusys.ai.news_nlp import score_news
  import duckdb
  from datetime import date
  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026,3,20))
  print(f"written: {n_written}")
  ```

- 市場レジーム判定（ma200 とマクロセンチメントの合成）
  ```python
  from kabusys.ai.regime_detector import score_regime
  import duckdb
  from datetime import date
  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026,3,20))
  ```

- 監査ログ DB の初期化（監査専用 DB を作る）
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # 初期化済 conn をそのまま利用可能
  ```

- 研究用ファクター計算例
  ```python
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  import duckdb
  from datetime import date
  conn = duckdb.connect("data/kabusys.duckdb")
  mom = calc_momentum(conn, date(2026,3,20))
  vol = calc_volatility(conn, date(2026,3,20))
  val = calc_value(conn, date(2026,3,20))
  ```

注意:
- OpenAI を使う機能は OPENAI_API_KEY が必要です（api_key を引数で与えることも可能）。
- J-Quants API を使う ETL は JQUANTS_REFRESH_TOKEN（.env 等で設定）を前提に動作します。
- 実行は DuckDB に必要なテーブルスキーマが揃っていることが前提です（ETL 初回実行で schema を作るなどのユーティリティがある場合はそれを使ってください）。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py — パッケージ定義（version, __all__）
- config.py — 環境変数 / .env 自動読み込み / settings オブジェクト
- ai/
  - __init__.py
  - news_nlp.py — ニュースの集約・OpenAI スコアリング・ai_scores 保存
  - regime_detector.py — ETF MA200 とマクロセンチメント合成による market_regime 書込み
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（取得・保存関数）
  - pipeline.py — ETL パイプライン（run_daily_etl 等）と ETLResult
  - etl.py — ETLResult の再エクスポート
  - news_collector.py — RSS 取得・前処理・raw_news 保存
  - calendar_management.py — market_calendar 管理・営業日判定
  - stats.py — zscore_normalize 等の汎用統計関数
  - quality.py — データ品質チェック（missing/spike/duplicates/date consistency）
  - audit.py — 監査ログ用 DDL/初期化ユーティリティ
- research/
  - __init__.py
  - factor_research.py — momentum/volatility/value の計算
  - feature_exploration.py — forward returns / IC / factor_summary / rank
- ai/regime_detector.py, ai/news_nlp.py など（OpenAI 呼び出しは SDK を使用）

---

## 注意事項 / 運用上のヒント

- .env の自動読み込みはプロジェクトルート検出に依存します。CI・テストで不要な場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して無効化してください。
- OpenAI 呼び出しではレスポンス検証・リトライロジックを入れていますが、API コストとレート制限には注意してください。
- J-Quants のレート制限（例: 120 req/min）や 401 の自動リフレッシュに対応した実装になっています。
- DuckDB の executemany は空リストを受け付けないバージョン互換のため、関数群は空チェックを行ってから executemany を呼び出します。
- 監査ログは削除しない前提で設計されており、order_request_id を冪等キーとして二重発注を防ぐ構成です。

---

必要であれば README に「利用例スクリプト」「.env.example の完全版」「テーブルスキーマ初期化手順」「Docker / systemd のデプロイ例」などを追記できます。どの情報を優先して追加しますか？