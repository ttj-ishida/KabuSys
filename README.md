# KabuSys — 日本株自動売買基盤（README）

KabuSys は日本株のデータパイプライン、AIによるニュースセンチメント評価、ファクター計算、監査ログなどを含む自動売買/リサーチ基盤のライブラリ群です。本リポジトリは DuckDB ベースのローカルデータストアと J-Quants/API、OpenAI（LLM）などと連携してデータ収集、品質チェック、AI スコアリング、研究用ファクター計算および監査ログ管理を行います。

主な目的は「データ取得 → 品質検査 → 特徴量生成 → 戦略評価 → 監査/トレーサビリティ」を安全かつ再現可能に実行するためのモジュール提供です。

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（主要 API の例）
- ディレクトリ構成
- 環境変数（.env 例）
- 注意事項

---

## プロジェクト概要

KabuSys は次の領域をカバーします。

- J-Quants API からの差分 ETL（株価日足・財務・マーケットカレンダー）
- RSS ニュース収集と前処理（SSRF / gzip / トラッキング除去対策）
- OpenAI を用いたニュースセンチメント評価（銘柄ごと／マクロセンチメント）
- 市場レジーム判定（ETF の MA200 乖離 と マクロセンチメントの合成）
- 研究用ファクター計算（モメンタム、バリュー、ボラティリティ等）と統計ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order_request → execution のトレーサビリティ）用スキーマ初期化ユーティリティ

設計上の注力点：
- ルックアヘッドバイアス防止（内部で date.today()/datetime.today() を不用意に参照しない）
- 冪等処理（DB 保存は ON CONFLICT / INSERT ... DO UPDATE 等）
- フェイルセーフ：API 失敗時は例外で止めずフォールバックやスキップして継続する箇所がある
- セキュリティ対策：ニュース収集で SSRF を防止、defusedxml を使用など

---

## 機能一覧

主な機能（モジュール別）

- kabusys.config
  - .env の自動読み込み（プロジェクトルート検出）
  - settings オブジェクトで環境変数を型的に取得（JQUANTS_REFRESH_TOKEN, OPENAI_API_KEY など）
- kabusys.data.jquants_client
  - J-Quants API 呼び出し（認証トークン取得、ページネーション、レートリミット、リトライ）
  - fetch / save 関数（daily_quotes、financial_statements、market_calendar、listed_info）
- kabusys.data.pipeline
  - run_daily_etl：カレンダー取得 → 株価 ETL → 財務 ETL → 品質チェック を一括実行
  - run_prices_etl / run_financials_etl / run_calendar_etl：個別 ETL
  - ETLResult データクラス（品質問題・エラー集約）
- kabusys.data.quality
  - 欠損チェック、スパイク検出、重複チェック、日付不整合チェック
- kabusys.data.news_collector
  - RSS フィード収集、前処理、記事ID生成（URL 正規化 + SHA256）
  - SSRF 対策、gzip 上限、XML パース保護
- kabusys.ai.news_nlp
  - ニュースを銘柄ごとにまとめて OpenAI に送信し ai_scores に保存
  - バッチ処理、JSON Mode、リトライ・バリデーション
- kabusys.ai.regime_detector
  - ETF 1321 の MA200 乖離（70%）とマクロ LLM センチメント（30%）を合成して market_regime テーブルへ保存
- kabusys.research
  - calc_momentum / calc_volatility / calc_value: ファクター計算
  - calc_forward_returns / calc_ic / factor_summary / rank: 特徴量解析・IC 計算・統計ユーティリティ
- kabusys.data.audit
  - 監査ログテーブル初期化（signal_events, order_requests, executions）とインデックス
  - init_audit_db で DuckDB ファイルの作成とスキーマ適用

---

## セットアップ手順

前提
- Python 3.10+（typing の一部を使用）
- Git レポジトリのルートに pyproject.toml か .git があると自動で .env を読み込みます

1. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate（Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール
   (リポジトリに requirements.txt がない場合、最低限以下を入れてください)
   - pip install duckdb openai defusedxml

   実運用では他に requests 等を使う場合があります。pyproject/toml を参照してください。

3. パッケージのインストール（開発用）
   - pip install -e .

4. 環境変数を設定
   - プロジェクトルートに .env を置くと自動で読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）
   - 必須環境変数の例は下記「環境変数（.env 例）」を参照

5. DuckDB ファイル等の初期化
   - 監査 DB を初期化する場合:
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")

---

## 使い方（主要 API の例）

以下は最小限の Python 例です。実際にはログ設定や例外処理を追加してください。

- 環境設定の利用
  from kabusys.config import settings
  print(settings.duckdb_path)  # Path オブジェクト

- DuckDB 接続と日次 ETL 実行
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニュースセンチメント（銘柄ごとの AI スコア）実行
  from kabusys.ai.news_nlp import score_news
  import duckdb
  from datetime import date

  conn = duckdb.connect(str(settings.duckdb_path))
  # OPENAI_API_KEY を環境変数で設定していれば api_key=None で可
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"scored {n_written} codes")

- 市場レジーム判定
  from kabusys.ai.regime_detector import score_regime
  import duckdb
  from datetime import date

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))  # OpenAI キーは env または api_key 引数

- 監査 DB の初期化
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/monitoring_audit.duckdb")
  # これで signal_events / order_requests / executions テーブルが作成されます

- 研究用ファクター計算
  from kabusys.research import calc_momentum, calc_volatility, calc_value
  import duckdb
  from datetime import date

  conn = duckdb.connect(str(settings.duckdb_path))
  mom = calc_momentum(conn, date(2026, 3, 20))
  vol = calc_volatility(conn, date(2026, 3, 20))
  val = calc_value(conn, date(2026, 3, 20))

注意点:
- OpenAI API を呼ぶ処理（score_news / score_regime）は API コールに伴う料金とレート制限に注意してください。各関数は api_key を明示的に渡すことも可能です。
- ETL / スコアリング系は DuckDB テーブル（raw_prices, raw_financials, raw_news, news_symbols, ai_scores, market_regime など）が期待されます。schema 初期化ロジックは別途提供されている想定です。

---

## ディレクトリ構成

主要ファイル・ディレクトリ（src/kabusys 配下）:

- kabusys/
  - __init__.py
  - config.py               — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py           — ニュース NLP スコアリング（銘柄別）
    - regime_detector.py    — 市場レジーム判定（MA200 + マクロセンチメント）
  - data/
    - __init__.py
    - jquants_client.py     — J-Quants API クライアント（fetch / save）
    - pipeline.py           — ETL パイプライン（run_daily_etl 等）
    - quality.py            — データ品質チェック
    - news_collector.py     — RSS 収集と前処理
    - calendar_management.py— マーケットカレンダー管理（is_trading_day 等）
    - audit.py              — 監査ログスキーマ初期化
    - etl.py                — ETLResult の再エクスポート
    - stats.py              — 統計ユーティリティ（zscore_normalize）
  - research/
    - __init__.py
    - factor_research.py    — Momentum/Value/Volatility 等の計算
    - feature_exploration.py— 将来リターン / IC / 統計サマリー
  - ai/、data/、research/ 以下に更に機能分割されたモジュールが存在

この README では主要モジュールを抜粋して記載しています。ソース全体は src/kabusys 以下を参照してください。

---

## 環境変数（.env の例）

プロジェクトルートに .env を置くと自動で読み込みます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。

例（.env）:
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_api_password_here
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO

必須（ライブラリ内の _require で要求されるもの）:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

OpenAI キーは score_news / score_regime 等で必要（env に置くか、関数に api_key を渡す）。

設定管理のポイント:
- 読み込み順: OS 環境変数 > .env.local > .env（プロジェクトルートを自動検出）
- 開発時に自動ロードを抑止する場合: export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## 注意事項 / ベストプラクティス

- DuckDB のテーブルスキーマ（raw_prices, raw_financials, raw_news, market_calendar, ai_scores, market_regime など）は別途定義されている想定です。ETL 実行前にスキーマを作成してください。
- OpenAI や J-Quants API のキーは必ず安全に管理してください（CI/CD のシークレット管理など）。
- ニュースの自動収集は外部サイトへのアクセスを伴うため、フェイルセーフやレート制限、SSRF 対策を考慮して運用してください。
- ETL・AI 呼び出しはネットワークリトライや指数バックオフを組み込んでいますが、実環境では追加の監視・アラートを推奨します。
- 本ライブラリはルックアヘッドバイアス対策が意識されていますが、バックテスト等で使用する際は取得タイミング（fetched_at）やデータの再現性に注意してください。

---

さらに詳しい仕様や API の詳細はソースコードの docstring を参照してください。必要であれば、README に追加したい使用例や CI / デプロイ手順、schema の SQL を作成して追記します。