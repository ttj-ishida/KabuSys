KabuSys — 日本株自動売買プラットフォーム（README）
======================================

概要
----
KabuSys は日本株向けのデータプラットフォーム・リサーチ・自動売買支援ライブラリです。  
主に以下の目的を持ったモジュール群を提供します。

- 市場データの ETL（J-Quants との接続、DuckDB への保存）
- ニュース収集・NLP による銘柄センチメント算出（OpenAI）
- 市場レジーム判定（ETF MA とマクロニュースを統合）
- ファクター計算・特徴量探索（Research 用ユーティリティ）
- マーケットカレンダー管理、データ品質チェック
- 監査ログ（signal → order → execution のトレーサビリティ）用スキーマ初期化

設計方針（抜粋）
- ルックアヘッドバイアス対策（内部で date.today()／datetime.today() を直接参照しない設計）
- DuckDB をコア DB に使用、ETL は idempotent（重複防止）
- OpenAI / J-Quants API 呼び出しにはリトライ・バックオフ・レート制御を実装
- セキュリティ考慮（RSS の SSRF 対策、XML の defusedxml 利用 等）

主な機能一覧
--------------
- data
  - ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants API クライアント（fetch_*, save_*）
  - カレンダー管理（is_trading_day / next_trading_day / calendar_update_job）
  - ニュース収集（RSS fetch + raw_news 保存）
  - データ品質チェック（missing / duplicates / spike / date_consistency）
  - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - 汎用統計（zscore_normalize）
- ai
  - ニュース NLP（score_news: 銘柄ごとの ai_score 計算）
  - レジーム判定（score_regime: ETF 200MA とマクロセンチメントの合成）
- research
  - ファクター計算（calc_momentum / calc_value / calc_volatility）
  - 特徴量解析（calc_forward_returns / calc_ic / factor_summary / rank）
- config
  - 環境設定の自動読込（.env / .env.local の優先度・保護設定）
  - Settings オブジェクトによる型付きアクセス（settings.jquants_refresh_token 等）

動作環境・依存関係（例）
---------------------
- Python 3.10+
- ライブラリ（主なもの）
  - duckdb
  - openai
  - defusedxml
  - そのほか標準ライブラリ（urllib, json, datetime 等）

インストール（開発環境向け）
--------------------------
1. リポジトリをクローン
   - git clone ...

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml

4. （任意）パッケージとして開発インストール
   - pip install -e .

環境変数（.env）
----------------
プロジェクトは起動時に自動的に .env / .env.local をプロジェクトルート（.git または pyproject.toml を基準）から読み込みます。自動ロードを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

主に必要な環境変数（例）
- JQUANTS_REFRESH_TOKEN: J-Quants 用リフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime 実行時に参照）
- KABU_API_PASSWORD: kabu ステーション API パスワード（注文モジュール利用時）
- KABU_API_BASE_URL: kabu API エンドポイント（デフォルト http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: Slack 通知用
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- KABUSYS_ENV: development / paper_trading / live（デフォルト development）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL

簡単な .env の例
----------------
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

セットアップ手順（基本的な使い方）
--------------------------------

1) DuckDB 接続の準備
- Python から直接 DuckDB に接続できます（ファイル DB 推奨）。
  例:
    import duckdb
    from kabusys.config import settings

    conn = duckdb.connect(str(settings.duckdb_path))

2) 日次 ETL を実行する
- data.pipeline モジュールの run_daily_etl を使用します。
  例:
    from kabusys.data.pipeline import run_daily_etl
    from kabusys.config import settings
    import duckdb
    from datetime import date

    conn = duckdb.connect(str(settings.duckdb_path))
    result = run_daily_etl(conn, target_date=date(2026, 3, 20))
    print(result.to_dict())

3) 監査ログ DB を初期化する
- 監査ログ専用 DB を作成してスキーマを初期化できます。
  例:
    from kabusys.data.audit import init_audit_db
    conn_audit = init_audit_db("data/audit.duckdb")

4) ニュースセンチメント（AI）を実行する
- OpenAI API キーを設定して score_news を呼ぶと ai_scores テーブルに保存されます。
  例:
    from kabusys.ai.news_nlp import score_news
    import duckdb
    from datetime import date

    conn = duckdb.connect(str(settings.duckdb_path))
    n_written = score_news(conn, target_date=date(2026,3,20))
    print(f"wrote {n_written} scores")

- score_regime（市場レジーム）:
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date=date(2026,3,20))

注: OpenAI 呼び出しは API 使用料・レートに注意してください。API エラー時はフェイルセーフでゼロスコア等にフォールバックする設計です。

主要 API（抜粋・使用例）
------------------------
- 設定参照:
    from kabusys.config import settings
    settings.jquants_refresh_token
    settings.duckdb_path

- ETL:
    from kabusys.data.pipeline import run_daily_etl
    run_daily_etl(conn, target_date=...)

- ニュース NLP:
    from kabusys.ai.news_nlp import score_news
    score_news(conn, target_date=..., api_key=None)

- レジーム判定:
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date=..., api_key=None)

- リサーチ（ファクター計算）:
    from kabusys.research import calc_momentum, calc_value, calc_volatility
    calc_momentum(conn, target_date=...)

- 監査ログ初期化:
    from kabusys.data.audit import init_audit_db, init_audit_schema
    init_audit_db("data/audit.duckdb")

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py                        — 環境変数 / Settings 管理（.env 自動読込含む）
- ai/
  - __init__.py
  - news_nlp.py                    — ニュースのセンチメント算出（score_news）
  - regime_detector.py             — 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py              — J-Quants API クライアント（fetch/save）
  - pipeline.py                    — ETL パイプライン（run_daily_etl 等）
  - etl.py                         — ETL の公開インターフェース（ETLResult）
  - calendar_management.py         — 市場カレンダー管理
  - news_collector.py              — RSS ニュース収集（SSRF 対策等）
  - quality.py                     — データ品質チェック
  - stats.py                       — 統計ユーティリティ（zscore_normalize）
  - audit.py                       — 監査ログスキーマ定義・初期化
- research/
  - __init__.py
  - factor_research.py             — ファクター計算（momentum/value/volatility）
  - feature_exploration.py         — 将来リターン計算・IC・統計サマリー
- research/*（補助モジュール）
- その他: execution, strategy, monitoring（パッケージ公開設定に含まれるが本リポジトリ内の別実装対象）

運用上の注意
-------------
- API キーは必ず秘密に保管してください（.env を使用し git 管理下に置かないこと）。
- J-Quants のレート制限（120 req/min）に合わせた RateLimiter を備えていますが、大量取得時は API ポリシーを順守してください。
- OpenAI 呼び出しはコストがかかります。テスト時はモック化（unittest.mock.patch）して利用することを推奨します（コード内でもテストを想定した差替えポイントを用意しています）。
- DuckDB のバージョンや SQL の互換性に依存するため、本番導入前にローカルで十分テストしてください。

ライセンス・貢献
----------------
（ここにライセンス情報・貢献方法を記載してください。リポジトリに LICENSE があればその内容に従ってください。）

最後に
------
この README はコードベースの主要機能・使い方を簡潔に説明したものです。詳細な API 使用方法や設定項目の説明はコード内ドキュメント（docstring）を参照してください。追加でチュートリアルや具体的なデプロイ手順が必要であればお知らせください。