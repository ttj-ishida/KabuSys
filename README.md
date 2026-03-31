# KabuSys

日本株向けの自動売買・データ基盤ライブラリ群（ETL / データ品質 / ニュース収集 / AI スコアリング / 研究用ファクター計算 / 監査ログ等）

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株のデータパイプラインと自動売買基盤の共通機能を提供するライブラリ群です。主な目的は次のとおりです。

- J-Quants API からのデータ取得（株価、財務、マーケットカレンダー）
- DuckDB を用いた ETL / 永続化（冪等保存）
- データ品質チェック（欠損・スパイク・重複・日付整合性）
- RSS ベースのニュース収集と前処理（SSRF 保護・正規化）
- OpenAI（gpt-4o-mini）を用いたニュース NLP スコアリングおよび市場レジーム判定
- 研究用のファクター計算（モメンタム・バリュー・ボラティリティ等）
- 監査ログ（signal → order_request → execution のトレース可能なスキーマ）

設計上の方針として、ルックアヘッドバイアスを避けるため日付参照に現在時刻を直接使わない、外部 API 呼び出しはリトライとレート制御を入れる、DuckDB 側での冪等保存を徹底する、などが採用されています。

---

## 主な機能一覧

- data
  - jquants_client: J-Quants API クライアント（認証・ページネーション・レート制御・取得 → DuckDB 保存）
  - pipeline: 日次 ETL（calendar / prices / financials）を実行する run_daily_etl
  - quality: データ品質チェック（欠損 / スパイク / 重複 / 日付整合性）
  - news_collector: RSS 収集・前処理・raw_news への保存支援
  - calendar_management: 営業日判定 / next/prev_trading_day 等ユーティリティ
  - audit: 監査ログスキーマの初期化（signal_events, order_requests, executions）
  - stats: z-score 正規化ユーティリティ
- ai
  - news_nlp.score_news: ニュースを用いた銘柄別センチメント（ai_scores への書き込み）
  - regime_detector.score_regime: ETF(1321) の MA200 とニュースセンチメントを合成して市場レジーム判定
- research
  - factor_research: calc_momentum, calc_value, calc_volatility（ファクター計算）
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank（研究用解析）
- config
  - 環境変数 / .env 自動ロード（.env, .env.local）と Settings クラス

---

## セットアップ手順

前提: Python 3.9+（typing の一部機能や型注釈を使用）を想定。

1. リポジトリをクローンしてインストール（開発環境）:
   - git clone ...（省略）
   - pip install -e .    # パッケージ化されている場合

2. 必要なパッケージをインストール（例）:
   - pip install duckdb openai defusedxml

   実際の requirements はプロジェクトの packaging に依存するため、プロジェクトの setup/pyproject を参照してください。

3. 環境変数 / .env を用意:
   - プロジェクトルートに `.env` または `.env.local` を置くと自動ロードされます（OS 環境変数が優先、.env.local は .env を上書き）。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

4. 必須の環境変数（主なもの）
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - SLACK_BOT_TOKEN: Slack 通知を使う場合（必須とされるコード箇所あり）
   - SLACK_CHANNEL_ID: Slack 通知先チャンネル
   - KABU_API_PASSWORD: kabuステーション API を使う場合
   - OPENAI_API_KEY: OpenAI API を使う機能（news_nlp / regime_detector）を実行する場合
   - （オプション）
     - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視用 DB）
     - PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
     - KABUSYS_ENV: development / paper_trading / live
     - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL

   例 (.env):
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-xxxxxxxx
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456789
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（代表的な API とサンプル）

以下はライブラリ内部関数の利用例です。実際のアプリケーションではログ設定やエラー処理を追加してください。

- DuckDB 接続を作成して日次 ETL を実行する
  - 例（概要）:
    - from datetime import date
    - import duckdb
    - from kabusys.data.pipeline import run_daily_etl
    - conn = duckdb.connect("data/kabusys.duckdb")
    - result = run_daily_etl(conn, target_date=date(2026, 3, 20))
    - print(result.to_dict())

- OpenAI を使ったニューススコアリング（ai.news_nlp.score_news）
  - from kabusys.ai.news_nlp import score_news
  - conn = duckdb.connect(settings.duckdb_path)
  - n = score_news(conn, target_date=date(2026,3,20), api_key="sk-...")
  - print(f"scored {n} codes")

- レジーム判定（ai.regime_detector.score_regime）
  - from kabusys.ai.regime_detector import score_regime
  - conn = duckdb.connect(settings.duckdb_path)
  - score_regime(conn, target_date=date(2026,3,20), api_key="sk-...")

- 監査ログ DB 初期化
  - from kabusys.data.audit import init_audit_db
  - conn = init_audit_db("data/monitoring.duckdb")  # または ":memory:"
  - これで signal_events / order_requests / executions テーブルが作成されます

- ニュース RSS の取得（news_collector.fetch_rss）
  - from kabusys.data.news_collector import fetch_rss
  - articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
  - for a in articles: print(a["title"], a["datetime"])

- 研究用ファクター計算
  - from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  - records = calc_momentum(conn, target_date)
  - normalized = zscore_normalize(records, ["mom_1m", "mom_3m", "mom_6m"])

注: AI 系（news_nlp / regime_detector）は OpenAI の JSON Mode を利用します。API のレスポンスに依存するため、実行時に API キーとネットワーク接続が必要です。API エラーはフォールバック戦略（0.0 スコアなど）で処理される設計です。

---

## 自動環境読み込みの挙動

- 起動時にプロジェクトルート（.git または pyproject.toml が存在する親ディレクトリ）を探索し、存在すれば `.env` を読み込み、次に `.env.local` を上書きで読み込みます。
- OS 環境変数が優先され、.env の値は既に存在する OS 変数を上書きしません（ただし .env.local は強制上書き）。
- 自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用途など）。

---

## ディレクトリ構成（主なファイル）

（パッケージは src/kabusys 以下に配置されています）

- src/kabusys/
  - __init__.py
  - config.py                    # Settings / .env 自動ロード
  - ai/
    - __init__.py
    - news_nlp.py                # ニュースの NLP スコアリング（score_news）
    - regime_detector.py         # 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py          # J-Quants API クライアント（fetch/save 等）
    - pipeline.py                # ETL パイプライン（run_daily_etl 等）
    - quality.py                 # データ品質チェック
    - news_collector.py          # RSS 収集・前処理
    - calendar_management.py     # 市場カレンダー関連ユーティリティ
    - audit.py                   # 監査ログスキーマ初期化
    - etl.py                     # ETLResult エクスポート
    - stats.py                   # zscore_normalize 等
  - research/
    - __init__.py
    - factor_research.py         # calc_momentum, calc_value, calc_volatility
    - feature_exploration.py     # calc_forward_returns, calc_ic, factor_summary, rank
  - ai、data、research の他に strategy / execution / monitoring 等のサブパッケージが想定されています（パッケージ __all__ で公開設定）

---

## 注意点 / 運用上のヒント

- Look-ahead バイアス対策が各所で実装されています。バックテスト時は過去のスナップショットデータのみを用いる運用を徹底してください。
- J-Quants API はレート制限があります（120 req/min）。jquants_client は内部で待機処理を行いますが、並列化する場合は注意してください。
- OpenAI を利用する機能は外部 API に依存するため、失敗時のフォールバック（0.0 スコアの採用など）を理解した上で利用してください。
- DuckDB を永続化に利用する場合はバックアップ方針を定めてください。init_audit_db は親ディレクトリ自動作成や UTC タイムゾーン固定等の初期化処理を行います。
- news_collector は SSRF 対策（ホスト検査、リダイレクト検査）やレスポンスサイズ制限を組み込んでいますが、運用上のフィード先は信頼できるソースを推奨します。

---

以上が KabuSys の README（概要・セットアップ・使い方・構成）です。README をプロジェクトの実態（requirements / packaging / CI）に合わせて調整してください。必要であれば README の英語版や実行例スクリプト（CLI / Docker / systemd 用ユニット例）も追加します。どの形式が要りますか？