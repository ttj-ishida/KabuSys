# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリセットです。  
ETL、ニュース収集・NLP、ファクター計算、監査ログ、J-Quants クライアント、マーケットカレンダー等を含みます。

---

## プロジェクト概要

KabuSys は日本株のデータ収集・品質管理・リサーチ・AI スコアリング・監査ログ・発注監視などを目的としたモジュール群です。  
主に以下の用途を想定しています。

- J-Quants API を用いた株価・財務・カレンダーの差分 ETL
- RSS ベースのニュース収集と LLM（OpenAI）による銘柄センチメント算出
- マーケットレジーム判定（ETF MA とマクロニュースを合成）
- ファクター計算（モメンタム/ボラティリティ/バリュー 等）と研究支援ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付整合性）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）用のスキーマ初期化

設計方針としては「ルックアヘッドバイアス排除」「冪等性」「フェイルセーフ（API失敗時は無害化）」を重視しています。

---

## 主な機能一覧

- ETL（data.pipeline.run_daily_etl）
  - 市場カレンダー・日足（raw_prices）・財務（raw_financials）を差分取得・保存
  - 品質チェックを実行して QualityIssue を返却
- J-Quants クライアント（data.jquants_client）
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar, fetch_listed_info
  - save_daily_quotes / save_financial_statements / save_market_calendar（DuckDB へ冪等保存）
- ニュース収集（data.news_collector）
  - RSS 取得、前処理、raw_news への保存、news_symbols と紐付け（ID 正規化・SSRF対策等）
- ニュース NLP（ai.news_nlp.score_news）
  - OpenAI を使って銘柄別のセンチメントスコアを生成して ai_scores テーブルへ保存
- レジーム判定（ai.regime_detector.score_regime）
  - ETF（1321）の 200 日 MA 乖離とマクロニュース LLM スコアを重み合成して市場レジームを判定・保存
- 研究支援（research.*）
  - calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, zscore_normalize 等
- カレンダー管理（data.calendar_management）
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job
- データ品質チェック（data.quality）
  - 欠損 / スパイク / 重複 / 日付不整合 の検出（QualityIssue 型で返却）
- 監査ログスキーマ（data.audit）
  - signal_events, order_requests, executions 等の DDL と初期化ユーティリティ（init_audit_schema / init_audit_db）

---

## 必要な環境変数

必須（アプリの多くの機能で必要）:
- JQUANTS_REFRESH_TOKEN — J-Quants 用リフレッシュトークン
- SLACK_BOT_TOKEN — Slack 通知を使う場合の Bot トークン
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID
- KABU_API_PASSWORD — kabu ステーション API（発注等）に必要なパスワード
- OPENAI_API_KEY — OpenAI を使う機能（ニュース NLP / レジーム判定）で必要

任意 (デフォルトあり):
- KABUSYS_ENV — 環境: one of ["development","paper_trading","live"]（デフォルト "development"）
- LOG_LEVEL — ログレベル（"DEBUG","INFO","WARNING","ERROR","CRITICAL"、デフォルト "INFO"）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 sqlite パス（デフォルト: data/monitoring.db）

自動 .env ロード:
- プロジェクトルート（.git または pyproject.toml の位置）から .env と .env.local を自動読み込みします。
- 読み込みは OS 環境変数 > .env.local > .env の順。
- 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

.env の記述ルールは一般的な KEY=VALUE 形式に対応し、シングル/ダブルクォートや export プレフィックスを扱います。

---

## セットアップ手順（開発向け）

前提: Python 3.10+（型アノテーションに Path | None などを使用）を推奨。

1. リポジトリを取得
   - git clone ...; cd <repo>

2. 仮想環境を作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   例（pip）:
   - pip install -e .              # setup.cfg / pyproject.toml がある場合
   - pip install duckdb openai defusedxml

   必要に応じて追加:
   - pip install requests  # （将来的な拡張用。現状は urllib を使用）

4. 環境変数設定
   - プロジェクトルートに .env を作成し、必須キーを設定してください。
     例 (.env):
       JQUANTS_REFRESH_TOKEN=xxxxx
       OPENAI_API_KEY=sk-...
       SLACK_BOT_TOKEN=xoxb-...
       SLACK_CHANNEL_ID=C01234567
       KABU_API_PASSWORD=secret
       KABUSYS_ENV=development
       DUCKDB_PATH=data/kabusys.duckdb

5. データベース初期化（監査ログを使う場合）
   - Python REPL から:
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")

---

## 使い方（簡単な例）

以下はライブラリ API を直接呼ぶ例です。実運用ではスクリプトやジョブランナーから呼び出します。

- 日次 ETL を実行する:
  python -c "import duckdb, datetime; from kabusys.data.pipeline import run_daily_etl; conn=duckdb.connect('data/kabusys.duckdb'); res=run_daily_etl(conn, target_date=datetime.date(2026,3,20)); print(res.to_dict())"

- ニュース NLP（OpenAI）で銘柄スコアを作る:
  from kabusys.ai.news_nlp import score_news
  import duckdb, datetime
  conn = duckdb.connect('data/kabusys.duckdb')
  score_news(conn, datetime.date(2026,3,20))  # OPENAI_API_KEY を環境にセットしておく

- 市場レジーム判定:
  from kabusys.ai.regime_detector import score_regime
  import duckdb, datetime
  conn = duckdb.connect('data/kabusys.duckdb')
  score_regime(conn, datetime.date(2026,3,20))  # OPENAI_API_KEY 必須

- J-Quants から日足を直接フェッチして保存:
  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
  import duckdb, datetime
  conn = duckdb.connect('data/kabusys.duckdb')
  records = fetch_daily_quotes(date_from=datetime.date(2026,3,1), date_to=datetime.date(2026,3,20))
  save_daily_quotes(conn, records)

- 監査ログスキーマの初期化（既存接続へ追加）:
  from kabusys.data.audit import init_audit_schema
  import duckdb
  conn = duckdb.connect('data/kabusys.duckdb')
  init_audit_schema(conn, transactional=True)

---

## 注意 / 設計上のポイント

- ルックアヘッドバイアス防止:
  - 多くの処理は date 引数を明示的に受け取り、内部で datetime.today() を使わない設計です。バックテスト等では必ず過去の date を渡してください。
- 冪等性:
  - ETL の保存関数は ON CONFLICT を用いて冪等に保存します。
- フェイルセーフ:
  - LLM/API 失敗時はゼロやスキップなどで継続し、致命的でない限り処理全体を止めない設計です。
- 自動 .env ロード:
  - プロジェクトルートを探して .env, .env.local を読み込みます。テストなどで無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成（要約）

- src/kabusys/
  - __init__.py
  - config.py                 : 環境変数 / .env 自動読み込み / Settings
  - ai/
    - __init__.py
    - news_nlp.py             : ニュースの LLM スコアリング（score_news）
    - regime_detector.py      : 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py       : J-Quants API クライアント & DuckDB 保存関数
    - pipeline.py             : ETL パイプライン（run_daily_etl 等）
    - etl.py                  : ETLResult の再エクスポート
    - news_collector.py       : RSS 取得・前処理
    - quality.py              : データ品質チェック（QualityIssue）
    - stats.py                : zscore_normalize 等の統計ユーティリティ
    - calendar_management.py  : 市場カレンダー管理（is_trading_day 等）
    - audit.py                : 監査ログテーブル DDL / 初期化
  - research/
    - __init__.py
    - factor_research.py      : calc_momentum / calc_value / calc_volatility
    - feature_exploration.py  : calc_forward_returns / calc_ic / factor_summary / rank
  - ai, research, data 配下に更に多数のユーティリティ関数とドキュメント的な docstring が含まれます。

---

## 推奨パッケージ（主要）

- duckdb
- openai
- defusedxml

必要に応じて他のパッケージ（requests 等）を導入することがありますが、現在のコードベースは標準ライブラリと上記で動作します。

---

## テスト・開発上のヒント

- OpenAI 呼び出しやネットワークを含む処理はテスト時にモックしやすいよう関数分割・注入設計がされています。例えば ai.news_nlp._call_openai_api を unittest.mock.patch で差し替えられます。
- 自動 .env ロードを無効化して環境依存を排除するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
- DuckDB の executemany に対する空パラメータの扱いなどに注意（コード内に互換性対策あり）。

---

README に書かれていない詳細実装や API の仕様は各モジュールの docstring を参照してください。質問や補足ドキュメントの追加希望があれば教えてください。