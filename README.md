# KabuSys

日本株向けのデータプラットフォームと研究・自動売買補助ライブラリ群です。  
DuckDB をローカル DB として利用し、J-Quants / RSS / OpenAI（LLM）など外部データを取り込んで、データ ETL、品質チェック、ニュース NLP、ファクター計算、レジーム判定、監査ログなどを提供します。

主な設計方針：
- ルックアヘッドバイアスを防ぐ（内部で datetime.today()/date.today() を不用意に参照しない）
- ETL / データ保存は冪等（ON CONFLICT など）で実行
- 外部 API 呼び出しはリトライやレート制限、フェイルセーフを実装
- DuckDB と標準ライブラリのみで主要処理を実装（追加依存は最小限）

---

## 機能一覧

- 環境設定読み込み / 管理（.env, .env.local、環境変数） — `kabusys.config`
  - 自動 .env ロード（プロジェクトルート検出、無効化フラグあり）
  - 必須項目チェック（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN 等）
- J-Quants API クライアント（取得・保存・認証・レート制御・リトライ） — `kabusys.data.jquants_client`
  - 株価日足、財務データ、JPX カレンダー、上場銘柄一覧 等
  - DuckDB へ冪等保存（raw_prices, raw_financials, market_calendar 等）
- ETL パイプライン（差分取得、バックフィル、品質チェック） — `kabusys.data.pipeline`
  - 日次 ETL 実行（run_daily_etl）
  - 個別ジョブ: run_prices_etl / run_financials_etl / run_calendar_etl
- データ品質チェック — `kabusys.data.quality`
  - 欠損、主キー重複、スパイク（急騰・急落）、日付不整合 など
- マーケットカレンダー管理（営業日判定、next/prev_trading_day 等） — `kabusys.data.calendar_management`
- ニュース収集（RSS）と前処理（SSRF 対策、URL 正規化、トラッキング除去） — `kabusys.data.news_collector`
- ニュース NLP（OpenAI を用いた銘柄ごとのセンチメント） — `kabusys.ai.news_nlp`
  - 指定タイムウィンドウ内の記事を銘柄単位に集約し、バッチで LLM 呼び出し
  - レスポンス検証とスコアクリップ、部分成功時の安全な DB 書き換え
- 市場レジーム判定（ETF の MA とマクロニュース LLM 評価の合成） — `kabusys.ai.regime_detector`
- 研究用ファクター計算・探索（モメンタム、バリュー、ボラティリティ、IC、forward returns 等） — `kabusys.research`
- 監査ログ（signal/order/execution のトレーサビリティ）初期化ユーティリティ — `kabusys.data.audit`
  - DuckDB ベースの監査テーブルとインデックスの初期化（init_audit_schema / init_audit_db）
- 汎用統計ユーティリティ（Zスコア正規化） — `kabusys.data.stats`

---

## 必要条件（推奨）

- Python 3.10+
- DuckDB（Python パッケージ: duckdb）
- OpenAI Python SDK（openai）※ニュース NLP / レジーム判定で必要
- defusedxml（RSS パースの安全対策）
- （その他）標準ライブラリのみで多くの処理を実装していますが、外部 API 呼び出し用の urllib 等を使用します

例: 必要パッケージ（最低限）
- duckdb
- openai
- defusedxml

---

## セットアップ手順

1. リポジトリをクローン / コピー

2. Python 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb openai defusedxml

   （パッケージ一覧が別途 requirements.txt にある場合はそれを利用してください）

4. 環境変数 / .env を用意
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` を置くと自動読み込みされます（.env.local を上書き）。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
   - 最低限必要な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     - KABU_API_PASSWORD=your_kabu_api_password
     - SLACK_BOT_TOKEN=xoxb-...
     - SLACK_CHANNEL_ID=C01234567
     - OPENAI_API_KEY=sk-...
   - 省略可能な設定:
     - KABUSYS_ENV=development|paper_trading|live  (デフォルト: development)
     - LOG_LEVEL=INFO|DEBUG|...
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db

5. （初回）データディレクトリの作成
   - mkdir -p data

---

## 使い方（基本例）

以下は Python スクリプト / REPL から直接利用する例です。import 先はパッケージ名 `kabusys` 下のモジュールです。

- DuckDB 接続を作成して日次 ETL を実行する
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  # target_date を指定しない場合は今日が使われます（内部で営業日補正あり）
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- OpenAI を使ってニューススコアを算出（ai_scores へ書き込む）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  # api_key を明示的に渡すか、環境変数 OPENAI_API_KEY をセットしておく
  n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
  print("written:", n_written)
  ```

- レジーム判定を実行（market_regime テーブルへ書き込み）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
  ```

- 監査ログ用の専用 DB を初期化する
  ```python
  from kabusys.data.audit import init_audit_db

  conn = init_audit_db("data/audit.duckdb")
  # これで監査テーブル（signal_events, order_requests, executions） とインデックスが作成されます
  ```

- 研究用ファクター計算
  ```python
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

  conn = duckdb.connect("data/kabusys.duckdb")
  mom = calc_momentum(conn, date(2026, 3, 20))
  val = calc_value(conn, date(2026, 3, 20))
  vol = calc_volatility(conn, date(2026, 3, 20))
  ```

- データ品質チェックを実行
  ```python
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=None)
  for i in issues:
      print(i)
  ```

注意点:
- LLM を用いる機能（news_nlp, regime_detector）は OpenAI API キーが必要です。api_key 引数で渡すか環境変数 `OPENAI_API_KEY` を設定してください。
- J-Quants API を利用する機能は `JQUANTS_REFRESH_TOKEN` が必須です。
- config.Settings は `.env` の自動ロードを行います。テスト等で自動ロードを抑止する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB に対する複数スレッド／プロセスからの同時アクセスは DB ファイル形式によって注意が必要です。運用時は適宜接続運用ポリシーを検討してください。

---

## 主要 API（抜粋）

- kabusys.config.settings: 設定オブジェクト（プロパティで必要な環境変数を取得）
  - jquants_refresh_token, kabu_api_password, slack_bot_token, slack_channel_id, duckdb_path, sqlite_path, env, log_level, is_live/is_paper/is_dev

- kabusys.data.jquants_client
  - fetch_daily_quotes, save_daily_quotes
  - fetch_financial_statements, save_financial_statements
  - fetch_market_calendar, save_market_calendar
  - get_id_token

- kabusys.data.pipeline
  - run_daily_etl(conn, target_date, id_token=None, run_quality_checks=True, ...)

- kabusys.data.quality
  - run_all_checks(conn, target_date=None, reference_date=None, spike_threshold=0.5)

- kabusys.ai.news_nlp
  - score_news(conn, target_date, api_key=None) -> 書き込んだ銘柄数

- kabusys.ai.regime_detector
  - score_regime(conn, target_date, api_key=None) -> 1（成功）

- kabusys.data.audit
  - init_audit_schema(conn, transactional=False)
  - init_audit_db(db_path) -> DuckDB 接続

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / .env 読み込み・設定
  - ai/
    - __init__.py
    - news_nlp.py            — ニュースセンチメント（OpenAI）
    - regime_detector.py     — 市場レジーム判定（MA + マクロセンチメント）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得/保存）
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - quality.py             — データ品質チェック
    - calendar_management.py — マーケットカレンダー管理（営業日判定等）
    - news_collector.py      — RSS 収集・前処理
    - stats.py               — 統計ユーティリティ（Zスコア）
    - audit.py               — 監査ログ初期化（テーブル定義）
    - etl.py                 — ETLResult エクスポート
  - research/
    - __init__.py
    - factor_research.py     — Momentum / Value / Volatility 等
    - feature_exploration.py — forward returns, IC, rank, summary
  - ai/, data/, research/ の各種ユーティリティと公開 API

---

## 開発者向け補足

- 自動 .env ロードはプロジェクトルート（.git または pyproject.toml）を基に行います。配布パッケージでも .env がない場合は自動ロードはスキップされます。
- OpenAI 呼び出しはレスポンス検証・リトライ・バックオフが実装されていますが、テスト時は各モジュールの _call_openai_api をモックして外部依存を外すことができます（ドキュメント中にその旨の注記あり）。
- DuckDB の executemany には空リストを渡せない制約があるため、モジュール内で空リストチェックを行っています（互換性対策）。
- ニュース収集では SSRF 対策、受信サイズ制限、gzip 解凍後のサイズチェックなど安全対策を多数実装しています。

---

## よくある質問

Q: .env を自動で読み込ませたくない場合は？  
A: 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

Q: KABUSYS_ENV に設定可能な値は？  
A: `development`, `paper_trading`, `live` のいずれかです。大文字小文字は無視されます。

Q: OpenAI のモデルはどれを使っていますか？  
A: コード中では gpt-4o-mini を指定しています（news_nlp/regime_detector）。

---

必要に応じて README のサンプルスクリプトや環境変数テンプレート（.env.example）を追加で作成できます。特定の実行例（ETL の cron 化、監査 DB 運用、Slack 通知連携 等）を README に追記したい場合は、どのシナリオを優先したいか教えてください。