KabuSys — 日本株向けデータパイプライン・リサーチ・自動売買基盤
================================================================

概要
----
KabuSys は日本株のデータ収集（J-Quants）、データ品質チェック、ファクター計算、ニュースの NLP スコアリング（OpenAI）、市場レジーム判定、監査ログ（発注→約定のトレース）などを備えた自動売買／リサーチ基盤のライブラリ群です。モジュール単位で ETL、品質チェック、リサーチ用ユーティリティ、AI スコアリング、監査ログ初期化などを提供します。

主な特徴
--------
- J-Quants API 経由の差分 ETL（株価・財務・カレンダー）と冪等保存
- DuckDB を使った高速な分析／ストレージ（データテーブル保存・更新用ユーティリティ）
- ニュース収集（RSS）・前処理・SSRF 対策・トラッキングパラメータ除去
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント（ai_scores）と市場レジーム判定
- 研究用ファクター・特徴量モジュール（モメンタム / バリュー / ボラティリティ / 将来リターン / IC / 統計サマリー 等）
- データ品質チェック（欠損、重複、スパイク、日付不整合）
- 監査ログ（signal / order_request / executions）用のスキーマ作成・初期化ユーティリティ
- 環境変数による設定管理（.env 自動読み込み機能あり）

必要な環境
---------
- Python 3.10+
- 必要な Python パッケージ（最低）:
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API、OpenAI、RSS フィード）

インストール（例）
-----------------
1. 仮想環境を作る（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb openai defusedxml

3. パッケージを編集モードでインストール（開発）
   - pip install -e .

環境変数（.env）
----------------
KabuSys は起動時にプロジェクトルート（.git または pyproject.toml）を探索して .env / .env.local を自動読み込みします（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると無効化可能）。主に利用される環境変数:

必須（多くの機能で必要）
- JQUANTS_REFRESH_TOKEN  : J-Quants API 用リフレッシュトークン
- OPENAI_API_KEY         : OpenAI API キー（score_news / regime 判定で使用）
- KABU_API_PASSWORD      : kabuステーション API のパスワード（発注連携用）
- SLACK_BOT_TOKEN        : Slack 通知（ボット）トークン（通知実装がある場合）
- SLACK_CHANNEL_ID       : 通知先 Slack チャンネル ID

任意
- KABU_API_BASE_URL      : kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH            : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH            : 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV            : 環境 ("development" | "paper_trading" | "live")（デフォルト: development）
- LOG_LEVEL              : ログレベル ("DEBUG" | "INFO" | ...)

簡易 .env.example
-----------------
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=your_openai_api_key
KABU_API_PASSWORD=your_kabu_api_password
SLACK_BOT_TOKEN=your_slack_bot_token
SLACK_CHANNEL_ID=your_slack_channel_id
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

セットアップ手順（実践）
---------------------
1. 環境変数を設定（.env を作成）
2. DuckDB 用ディレクトリを作る:
   - mkdir -p data
3. 必要パッケージをインストール（上記参照）
4. 監査ログ DB を初期化（監査スキーマのみを使う場合）:
   - from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
   この関数は監査ログ用テーブル群とインデックスを作成します。
5. ETL の実行前に J-Quants ID トークンが必要（get_id_token は内部で解決します）。ETL を実行するときは settings.jquants_refresh_token を .env に設定しておくと自動で取得されます。

使い方：主要 API / 例
--------------------

- 日次 ETL の実行（株価・財務・カレンダー取得、品質チェック）
  - 例:
    from datetime import date
    import duckdb
    from kabusys.config import settings
    from kabusys.data.pipeline import run_daily_etl

    conn = duckdb.connect(str(settings.duckdb_path))
    result = run_daily_etl(conn, target_date=date(2026, 3, 20))
    print(result.to_dict())

  - run_daily_etl は ETLResult を返し、取得数・保存数・品質問題・エラー情報を含みます。

- ニュースセンチメントのスコアリング（OpenAI 必須）
  - 例:
    import duckdb
    from datetime import date
    from kabusys.ai.news_nlp import score_news
    from kabusys.config import settings

    conn = duckdb.connect(str(settings.duckdb_path))
    n = score_news(conn, target_date=date(2026,3,20))
    print(f"scored {n} codes")

  - 引数 api_key を渡すと環境変数を使わずに OpenAI キーを指定できます。

- 市場レジーム判定
  - 例:
    from kabusys.ai.regime_detector import score_regime
    result = score_regime(conn, target_date=date(2026,3,20))

- 監査ログの初期化（専用 DB を作る）
  - 例:
    from kabusys.data.audit import init_audit_db
    conn = init_audit_db("data/kabusys_audit.duckdb")
    # conn を利用して以降の監査ログの書き込みが可能になる

- RSS 取得（ニュースコレクタ）
  - 例:
    from kabusys.data.news_collector import fetch_rss
    articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")

注意点・設計方針（抜粋）
---------------------
- ルックアヘッドバイアス回避:
  - すべての関数は内部で datetime.today() / date.today() を不用意に参照せず、呼び出し側が target_date を明示することでバックテスト時のリークを防止するよう設計されています。
- 冪等性:
  - J-Quants からのデータ保存は ON CONFLICT DO UPDATE を使って冪等に保存します（save_* 関数群）。
- フェイルセーフ:
  - AI API 呼び出しや外部 API で失敗した場合、致命的に停止させずフォールバック（スコア=0.0 等）して継続する設計が多く採用されています。
- セキュリティ:
  - RSS 取得は SSRF 対策（プライベートアドレス拒否、リダイレクト検査）や XML の安全パーサ（defusedxml）を用いています。

ディレクトリ構成（抜粋）
-----------------------
プロジェクトの主要ファイルを抜粋して示します（src/kabusys 配下）:

- kabusys/
  - __init__.py                — パッケージ定義・公開モジュール一覧
  - config.py                  — 環境変数 / 設定管理（.env 自動読み込み）
  - ai/
    - __init__.py
    - news_nlp.py              — ニュース NLP（score_news）
    - regime_detector.py       — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - calendar_management.py   — 市場カレンダー管理（is_trading_day 等）
    - etl.py                   — ETL 公開インターフェース（ETLResult 再エクスポート）
    - pipeline.py              — 日次 ETL パイプライン（run_daily_etl 他）
    - stats.py                 — 汎用統計ユーティリティ（zscore_normalize 等）
    - quality.py               — データ品質チェック（欠損・スパイク・重複・日付不整合）
    - audit.py                 — 監査ログスキーマ初期化・audit DB 初期化
    - jquants_client.py        — J-Quants API クライアント（取得・保存関数）
    - news_collector.py        — RSS 収集・前処理・保存補助
  - research/
    - __init__.py
    - factor_research.py       — モメンタム／ボラティリティ／バリュー計算
    - feature_exploration.py   — 将来リターン／IC／統計サマリー等

（各モジュールには docstring で設計方針・処理フローが記載されています）

開発に関する補足
----------------
- テスト:
  - モジュール内の外部 API 呼び出しは差し替え（モック）しやすいように設計されています（例: news_nlp._call_openai_api を patch してテスト可能）。
- ロギング:
  - 各モジュールは標準の logging モジュールを利用。LOG_LEVEL を環境変数で制御できます。
- マイグレーション / スキーマ:
  - 監査ログ用スキーマは data.audit.init_audit_schema / init_audit_db で初期化できます。主要な分析テーブル（raw_prices, raw_financials, market_calendar, ai_scores, ai_scores 等）は ETL の対象であり、実行前にスキーマを準備する必要があります（スキーマ定義は別ドキュメントにある想定です）。

サポート / ドキュメント
---------------------
- 各モジュールの docstring に処理フロー・設計ノートが詳細に記載されています。まずは該当モジュールの docstring を参照してください。
- 実運用では KABUSYS_ENV（paper_trading / live）や Slack 通知・Error ハンドリングの追加を推奨します。

ライセンス
---------
（ここにプロジェクトのライセンス情報を記載してください）

---

この README はリポジトリ内のコードから主要機能・利用方法をまとめたものです。必要であれば、実際のスキーマ SQL・data dictionary・運用手順（cron / Airflow / systemd など）を別途追記します。追加したい項目（例: マイグレーション用 SQL、運用フロー、CI 用設定）があれば教えてください。