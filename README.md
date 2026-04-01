KabuSys
=======

日本株向けのデータパイプライン／リサーチ／自動売買補助ライブラリ群です。  
DuckDB をデータ層に使い、J-Quants や RSS、OpenAI を組み合わせて以下のような機能を提供します。

要点
- データ取得（J-Quants）→ DuckDB に保存（ETL）
- ニュースの収集・前処理・LLM によるセンチメント付与（news_nlp）
- マクロニュース + ETF MA に基づく市場レジーム判定（regime_detector）
- ファクター計算・特徴量探索（research パッケージ）
- データ品質チェック・カレンダー管理・監査ログ（data パッケージ）
- 環境変数ベースの設定管理（config）

主な機能一覧
- ETL（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
- J-Quants API クライアント（fetch / save の高耐久実装、認証・リトライ・レート制御）
- RSS ニュース収集（SSRF対策、URL正規化、トラッキング除去）
- OpenAI を使ったニュースセンチメント解析（バッチ処理、JSON Mode、リトライ）
- 市場レジーム判定（ETF 1321 の MA200 とマクロセンチメントの重み和）
- ファクター計算（モメンタム / ボラティリティ / バリュー 等）
- データ品質チェック（欠損・重複・スパイク・日付整合性）
- 監査ログスキーマの初期化・監査テーブル（signal_events / order_requests / executions）
- 汎用統計ユーティリティ（zscore 正規化など）

セットアップ手順（開発用）
- 前提
  - Python 3.10+（型アノテーションに | を利用）
  - DuckDB（Python パッケージ duckdb）
  - OpenAI Python SDK（openai）
  - defusedxml（RSS パースの安全化）
  - その他依存ライブラリ（標準 lib 以外がある場合は requirements.txt に記載してください）

例（venv を使う）
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. パッケージインストール（例）
   - pip install duckdb openai defusedxml

   （プロジェクトルートに setup.py/pyproject.toml があれば）
   - pip install -e .

3. 環境変数の設定
   - プロジェクトルートに .env / .env.local を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると無効化できます）。
   - 主要な環境変数（最低限必要なもの）
     - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
     - OPENAI_API_KEY : OpenAI API キー（news_nlp / regime_detector 用）
     - KABU_API_PASSWORD : kabu ステーション API のパスワード（必要に応じて）
     - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID : Slack 通知用
     - DUCKDB_PATH / SQLITE_PATH : データベースファイルパス（省略時デフォルト有り）
     - KABUSYS_ENV : development / paper_trading / live
     - LOG_LEVEL : DEBUG / INFO / WARNING / ERROR / CRITICAL

   .env 例行（参考）
   - JQUANTS_REFRESH_TOKEN=xxxx
   - OPENAI_API_KEY=sk-xxxx
   - KABU_API_PASSWORD=...
   - SLACK_BOT_TOKEN=xoxb-...
   - SLACK_CHANNEL_ID=C01234567
   - DUCKDB_PATH=data/kabusys.duckdb
   - SQLITE_PATH=data/monitoring.db
   - KABUSYS_ENV=development
   - LOG_LEVEL=INFO

使い方（代表的な例）
- DuckDB 接続を用意する
  - import duckdb
  - conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL を実行する（市場カレンダー・株価・財務・品質チェックを一括で実行）
  - from kabusys.data.pipeline import run_daily_etl
  - from kabusys.config import settings
  - conn = duckdb.connect(str(settings.duckdb_path))
  - result = run_daily_etl(conn)  # target_date を指定することも可
  - print(result.to_dict())

- ニュースのスコア付与（指定日分）
  - from datetime import date
  - from kabusys.ai.news_nlp import score_news
  - conn = duckdb.connect(str(settings.duckdb_path))
  - count = score_news(conn, target_date=date(2026,3,20))  # OPENAI_API_KEY を env にセット済みなら api_key は不要

- 市場レジームのスコア（regime_detector）
  - from kabusys.ai.regime_detector import score_regime
  - from datetime import date
  - conn = duckdb.connect(str(settings.duckdb_path))
  - score_regime(conn, target_date=date(2026,3,20))  # OPENAI_API_KEY が必要

- 監査ログ DB の初期化（監査専用 DB）
  - from kabusys.data.audit import init_audit_db
  - conn_audit = init_audit_db("data/audit.duckdb")
  - # これにより信号・発注・約定のためのテーブルとインデックスが作成されます

設定（config モジュールのポイント）
- 自動 .env ロード
  - プロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を基準に .env と .env.local を自動的に読み込みます。
  - 読み込み順: OS 環境変数 > .env.local > .env
  - テスト等で自動ロードを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- Settings API
  - from kabusys.config import settings
  - settings.jquants_refresh_token, settings.duckdb_path, settings.env などのプロパティでアクセス可能
  - KABUSYS_ENV は "development" / "paper_trading" / "live" のいずれかに制限

注意点・設計上の考慮
- Look-ahead バイアス対策
  - 多くの関数は date.today() 等を直接参照せず、target_date を明示的に受け取る設計です（バックテスト時のバイアス防止）。
- OpenAI 呼び出し
  - gpt-4o-mini を想定し JSON Mode を利用する設計。API エラーはリトライして、最悪の場合はフェイルセーフ（0.0等のデフォルト）で継続します。
- J-Quants API
  - レートリミット（120 req/min）を固定間隔で守る実装。401 時はトークン自動リフレッシュを行います。
- セキュリティ
  - RSS 収集部は SSRF 回避、XML インジェクション対策（defusedxml）、レスポンスサイズ制限などを実装。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数と設定管理
  - ai/
    - __init__.py
    - news_nlp.py            — ニュースの集約・OpenAI スコアリング
    - regime_detector.py     — 市場レジーム判定（ETF MA200 + マクロセンチメント）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（fetch / save）
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - etl.py                 — ETLResult の再エクスポート
    - news_collector.py      — RSS 収集・前処理
    - calendar_management.py — 市場カレンダー管理（is_trading_day 等）
    - quality.py             — データ品質チェック
    - stats.py               — 統計ユーティリティ（zscore_normalize）
    - audit.py               — 監査ログスキーマ初期化 / init_audit_db
  - research/
    - __init__.py
    - factor_research.py     — モメンタム / バリュー / ボラティリティ計算
    - feature_exploration.py — 将来リターン / IC / 統計サマリー / rank 等
  - ai/、research/、data/ の各モジュールはさらに多くのヘルパー・内部関数を含みます。

開発上のヒント
- テスト時は OpenAI 呼び出しやネットワーク呼び出しをモックすることを想定した設計（内部の _call_openai_api や _urlopen を差し替え可能）。
- DuckDB の executemany は空リストを受け付けないバージョンがあるため、呼び出し前に空チェックを行っています。実運用では DuckDB のバージョン依存に注意してください。
- audit.init_audit_schema は transactional フラグを提供します。既にトランザクション中の接続へ呼ぶと問題が起きるため transactional=False をデフォルトにしています。

ライセンス・貢献
- （このリポジトリのライセンス情報をここに記載してください）

お問い合わせ
- 実装や設計に関する質問があれば、コードの該当モジュール（例: kabusys.data.jquants_client）を参照してください。README に含める追加の使い方やサンプルが必要であれば教えてください。

以上。必要であれば各機能の具体的なコード例（ETL 実行フロー、OpenAI プロンプトの例、J-Quants の取得例など）を追加します。