# KabuSys

KabuSys は日本株向けのデータパイプライン・リサーチ・AI/NLP・監査ログを備えた自動売買プラットフォームのライブラリコアです。J-Quants API や OpenAI を利用したニュースセンチメント解析、DuckDB を利用した ETL / データ品質チェック、監査ログ（発注→約定トレース）などの機能を提供します。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（主要 API の例）
- 環境変数 (.env) と自動読み込み
- ディレクトリ構成

---

プロジェクト概要
- 日本株を対象としたデータ取得（J-Quants）→保存（DuckDB）→品質チェック→ファクター計算→AI（ニュースセンチメント / レジーム判定）→監査ログ生成を行うための共通コンポーネント群。
- バックテスト／リサーチ用途と、本番（発注）での監査トレーサビリティを両立する設計方針です。
- Look-ahead バイアス対策、API リトライ、レート制御、冪等性（ON CONFLICT / UUID）などを意識して実装されています。

機能一覧
- データ収集 / ETL
  - J-Quants API クライアント（株価、財務、上場情報、マーケットカレンダー）
  - 差分取得・バックフィル対応の ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - DuckDB への冪等保存（save_*）
- データ品質
  - 欠損・重複・スパイク・日付不整合チェック（quality モジュール）
- ニュース収集 / NLP
  - RSS からのニュース収集（news_collector）
  - OpenAI を用いたニュース銘柄別センチメントスコアリング（news_nlp.score_news）
  - マクロニュースとETF MA200乖離を使った市場レジーム判定（ai.regime_detector.score_regime）
- 研究用ユーティリティ
  - モメンタム / バリュー / ボラティリティ等のファクター計算（research パッケージ）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー、Zスコア正規化
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions のスキーマ定義と初期化ユーティリティ（data.audit）
  - 監査用 DuckDB データベース初期化（init_audit_db）
- 設定管理
  - .env / 環境変数読み込み（config.Settings）
  - 自動 .env 読み込み（プロジェクトルートの .env / .env.local、無効化フラグあり）

---

セットアップ手順（ローカル開発向け）
1. リポジトリをクローン
   - git clone <repo-url>

2. Python バージョン
   - Python 3.10 以上（| 型注釈等を利用しているため 3.10+ を推奨）

3. 仮想環境作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

4. 依存パッケージをインストール
   - 必要な主なパッケージ:
     - duckdb
     - openai
     - defusedxml
   - 例:
     - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt / pyproject.toml があればそちらを使用してください:
     pip install -e . など）

5. 環境変数設定
   - プロジェクトルートに .env を作成する（例は後述）
   - 自動ロードはデフォルトで有効（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）

6. DB 用ディレクトリ作成（必要に応じて）
   - デフォルト DuckDB パス: data/kabusys.duckdb
   - 監査用 SQLite のデフォルト: data/monitoring.db
   - 例:
     - mkdir -p data

---

環境変数 (.env) と自動読み込み
- 自動読み込み:
  - プロジェクトルート（.git または pyproject.toml があるディレクトリ）を基準に .env を読み込みます。
  - 読み込み順: OS 環境変数 > .env.local (上書き) > .env
  - 無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードをスキップします。

- 主な必須環境変数（config.Settings で要求されるもの）
  - JQUANTS_REFRESH_TOKEN    : J-Quants リフレッシュトークン（get_id_token で使用）
  - KABU_API_PASSWORD        : kabuステーション API パスワード（発注周りで使用）
  - SLACK_BOT_TOKEN          : Slack Bot トークン（通知用）
  - SLACK_CHANNEL_ID        : Slack チャンネル ID
  - OPENAI_API_KEY           : OpenAI API キー（news_nlp / regime_detector で利用）
- DB パス関連（省略可、デフォルトあり）
  - DUCKDB_PATH              : デフォルト data/kabusys.duckdb
  - SQLITE_PATH              : デフォルト data/monitoring.db
- 実例 (.env)
  - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
  - OPENAI_API_KEY=sk-xxx
  - KABU_API_PASSWORD=your_kabu_password
  - SLACK_BOT_TOKEN=xoxb-xxx
  - SLACK_CHANNEL_ID=C01234567
  - DUCKDB_PATH=data/kabusys.duckdb

---

使い方（主要 API の例）
- DuckDB 接続の準備（例）
  - import duckdb
  - conn = duckdb.connect("data/kabusys.duckdb")

- ETL（日次パイプライン）
  - from datetime import date
    from kabusys.data.pipeline import run_daily_etl
    result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  - ETLResult オブジェクトが返り、fetched/saved/quality_issues などを確認できます。

- 単独ジョブ
  - run_prices_etl / run_financials_etl / run_calendar_etl を個別に呼ぶことも可能。

- ニュース NLP スコアリング
  - from kabusys.ai.news_nlp import score_news
    from datetime import date
    n = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  - OpenAI API キーを api_key 引数に渡すか、環境変数 OPENAI_API_KEY を利用。

- 市場レジーム判定
  - from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  - 内部で ETF 1321 の MA200 乖離とマクロニュースを統合します。

- 監査ログ初期化（監査用 DuckDB）
  - from kabusys.data.audit import init_audit_db
    audit_conn = init_audit_db("data/audit.duckdb")
  - または既存の DuckDB 接続に対して init_audit_schema(conn, transactional=True) を呼ぶ。

- J-Quants 直接利用（テストやカスタム取得）
  - from kabusys.data.jquants_client import fetch_daily_quotes, fetch_financial_statements
    records = fetch_daily_quotes(date_from=..., date_to=...)

- RSS フェッチ（ニュース収集）
  - from kabusys.data.news_collector import fetch_rss
    articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", "yahoo_finance")

注意点 / 設計上のポリシー
- ルックアヘッドバイアス対策:
  - モジュール内の多くの関数は datetime.today() / date.today() を直接参照しないよう設計されています。外部から target_date を渡す方式でバックテスト時のバイアスを防止します。
- フェイルセーフ:
  - 外部 API 失敗時はスコアを 0 にフォールバックしたり（AI モジュール）、個別処理の失敗を全体 ETL の継続に影響させない設計になっています（エラーは収集して呼び出し元に返す）。
- 冪等性:
  - DuckDB への保存はできるだけ ON CONFLICT DO UPDATE 等で冪等に行うようになっています。

---

ディレクトリ構成（抜粋）
- src/kabusys/
  - __init__.py
  - config.py                      -- 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                   -- ニュース NLP（score_news）
    - regime_detector.py            -- マーケットレジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py             -- J-Quants API クライアント（取得・保存）
    - pipeline.py                   -- ETL パイプライン(run_daily_etl 等)
    - etl.py                        -- ETL インターフェース再エクスポート
    - calendar_management.py        -- 市場カレンダー管理
    - news_collector.py             -- RSS 収集
    - stats.py                      -- 統計ユーティリティ（zscore_normalize）
    - quality.py                    -- データ品質チェック
    - audit.py                      -- 監査ログスキーマ / 初期化
  - research/
    - __init__.py
    - factor_research.py            -- Momentum / Value / Volatility 計算
    - feature_exploration.py        -- 将来リターン / IC / summary / rank
  - research/ ... (その他の研究ユーティリティ)
- data/                              -- デフォルトの DB 保存先（推奨）
- .env.example                       -- (プロジェクトにある場合は例を参照)

---

開発・テストについて
- 自動環境変数読み込みを無効にする:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると config が .env を自動ロードしません。テスト時に環境を差し替えたい場合に便利です。
- OpenAI 呼び出し・外部アクセスのモック:
  - news_nlp._call_openai_api や regime_detector._call_openai_api 等はテストで patch して差し替える設計になっています（ユニットテストが書きやすい）。

---

ライセンス / 貢献
- 本 README ではライセンス情報を記載していません。実際のリポジトリに LICENSE ファイルがある場合はそれに従ってください。
- 貢献／バグ報告は GitHub の Issue / Pull Request を通してください。

---

質問・補足
- README に追加したい具体的なコマンド例（pyproject.toml に基づくインストールや CI 設定等）があれば教えてください。必要に応じて README を拡張します。