# KabuSys

日本株向けの自動売買／データプラットフォームライブラリ群です。  
データ取得（J-Quants）、ニュース収集・NLP（OpenAI）、研究用ファクター計算、ETL、監査ログなどを含むモジュール群を提供します。

## 主な特徴（概要）
- J-Quants API を用いた株価・財務・市場カレンダーの差分ETL（ページネーション・リトライ・レートリミット対応）
- RSS ベースのニュース収集（SSRF対策・トラッキング除去）と LLM を使った銘柄別センチメントスコアリング
- 市場レジーム判定（ETF 1321 の MA200 とマクロニュースの LLM センチメントを合成）
- 研究用ファクター計算（モメンタム、バリュー、ボラティリティ、将来リターン、IC、Zスコア正規化 等）
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 監査ログ（signal → order_request → executions のトレーサビリティ。DuckDBで管理）

---

## 機能一覧（モジュール）
- kabusys.config
  - .env / .env.local の自動読み込み（プロジェクトルート探索）と環境変数アクセスラッパー
  - 必須環境変数の検証、ランタイム設定（env, log_level 等）
- kabusys.data
  - jquants_client: J-Quants API クライアント（取得/保存関数、認証/リフレッシュ、レート制御）
  - pipeline: 日次 ETL 実装（run_daily_etl 等）、ETLResult の定義
  - news_collector: RSS フィード取得・パース・前処理・raw_news への保存（SSRF対策）
  - calendar_management: 市場カレンダー管理、営業日判定ユーティリティ
  - quality: データ品質チェック（欠損、スパイク、重複、日付不整合）
  - audit: 監査ログスキーマの初期化（init_audit_schema / init_audit_db）
  - stats: zscore_normalize など汎用統計ユーティリティ
- kabusys.ai
  - news_nlp.score_news: ニュースを LLM に送り銘柄ごとの ai_score を生成して ai_scores に保存
  - regime_detector.score_regime: ETF MA200 とマクロニュース LLM スコアを合成して market_regime を更新
- kabusys.research
  - factor_research: calc_momentum, calc_value, calc_volatility
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank

---

## セットアップ手順（開発／ローカル実行向け）
前提:
- Python 3.10 以上（型ヒントの union syntax 等を使用）
- DuckDB を使用（duckdb パッケージ）
- OpenAI SDK（openai パッケージ）
- defusedxml（RSS パースの安全化）など

1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  # macOS / Linux
   - .venv\Scripts\activate     # Windows

3. 依存関係をインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml

   ※ pyproject.toml / requirements.txt がある場合はそれに従ってください（本コードベースには依存リストが明示されていないため、上記を最低限の依存として挙げています）。

4. パッケージを編集インストール（任意）
   - pip install -e .

5. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml の存在するディレクトリ）に `.env` および（必要に応じて）`.env.local` を配置すると自動で読み込まれます（読み込み順: OS 環境 > .env.local > .env）。
   - 自動読み込みを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

必須の環境変数（最低限）
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（jquants_client.get_id_tokenで使用）
- KABU_API_PASSWORD — kabuステーション API パスワード（本リポジトリの外部モジュールで使用想定）
- SLACK_BOT_TOKEN — Slack 通知等で使用する Bot トークン
- SLACK_CHANNEL_ID — Slack チャンネル ID
- OPENAI_API_KEY — OpenAI API の API キー（news_nlp / regime_detector で使用）

オプション:
- KABUSYS_ENV: development / paper_trading / live（デフォルト development）
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL
- DUCKDB_PATH: デフォルト data/kabusys.duckdb
- SQLITE_PATH: デフォルト data/monitoring.db

---

## 使い方（簡単な実行例）
以下は基本的な Python からの呼び出し例です。実行前に必須環境変数を設定し、DuckDB の接続先ファイル/スキーマが準備されていることを前提とします。

- DuckDB 接続例
  - import duckdb
  - from kabusys.config import settings
  - conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL を実行する（デフォルトで当日をターゲット）
  - from kabusys.data.pipeline import run_daily_etl
  - result = run_daily_etl(conn)
  - print(result.to_dict())

- ニューススコアリング（ai_scores に書き込み）
  - from datetime import date
  - from kabusys.ai.news_nlp import score_news
  - count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key を省略すると OPENAI_API_KEY を使用
  - print(f"scored {count} codes")

- 市場レジーム判定
  - from kabusys.ai.regime_detector import score_regime
  - from datetime import date
  - score_regime(conn, target_date=date(2026, 3, 20))

- 監査ログ DB 初期化（監査用の DuckDB ファイルを作成）
  - from kabusys.data.audit import init_audit_db
  - aud_conn = init_audit_db("data/audit.duckdb")
  - # 以降 aud_conn を使って監査ログに書き込む

- カレンダー更新ジョブ（JPX カレンダー差分取得）
  - from kabusys.data.calendar_management import calendar_update_job
  - saved = calendar_update_job(conn)
  - print(f"saved {saved} calendar records")

注意点:
- 一部の保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）は対象テーブルの存在を前提とします。プロジェクトのスキーマ初期化手順（data schema）を別途用意しておく必要があります。
- news_collector の fetch_rss は SSRF や大容量応答に対する保護を施しており、URLスキームやプライベートIP、最大バイト数を検査します。

---

## ディレクトリ構成（主要ファイル）
（src/kabusys 配下の主要モジュールを抜粋）

- kabusys/
  - __init__.py  (パッケージ宣言、__version__)
  - config.py    (環境変数/.env 読み込み、Settings)
  - ai/
    - __init__.py
    - news_nlp.py       (ニュースセンチメント・ai_scores 書き込み)
    - regime_detector.py (市場レジーム判定、market_regime 書き込み)
  - data/
    - __init__.py
    - jquants_client.py (J-Quants API クライアント、保存関数)
    - pipeline.py       (ETL パイプライン, run_daily_etl, ETLResult)
    - etl.py            (ETLResult 再エクスポート)
    - news_collector.py (RSS 取得・前処理)
    - calendar_management.py (market_calendar 管理、営業日判定)
    - quality.py        (データ品質チェック)
    - stats.py          (zscore_normalize 等)
    - audit.py          (監査ログスキーマ初期化 / init_audit_db)
  - research/
    - __init__.py
    - factor_research.py     (calc_momentum, calc_value, calc_volatility)
    - feature_exploration.py (calc_forward_returns, calc_ic, factor_summary, rank)

---

## 運用上の注意 / トラブルシュート
- OpenAI / J-Quants の API レート制限と料金に注意してください。ライブラリはリトライと固定間隔のレート制限を実装していますが、実運用ではさらにジョブスケジューラ側でリトル制御を行ってください。
- 自動 .env 読み込みはプロジェクトルートを .git または pyproject.toml で探索します。CI やテストで自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB のスキーマ（テーブル定義）が必要です。監査ログ用のスキーマ初期化は data.audit.init_audit_db / init_audit_schema で行えますが、raw_prices / raw_financials / market_calendar 等のスキーマ作成は別途用意してください（ETL が前提とするスキーマが存在しないと INSERT が失敗します）。
- news_collector は外部ネットワークを扱うため、社内プロキシやファイアウォール環境では接続設定に注意してください。

---

もし README に追加したい情報（テーブルスキーマ、CI 実行手順、サンプル .env.example、テスト実行方法など）があれば教えてください。必要に応じてサンプル .env.example や初期スキーマのテンプレートも作成します。