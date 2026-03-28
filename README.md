KabuSys
=======

日本株向けの自動売買／データプラットフォーム用ライブラリ群です。データ収集（J-Quants）、ニュース収集・NLP評価（OpenAI）、ETL パイプライン、研究用ファクター計算、監査ログ（約定トレーサビリティ）などを含みます。

プロジェクト概要
--------------
- 目的: 日本株のデータプラットフォームと自動売買フローの基盤機能を提供する。
- 主な設計方針:
  - ルックアヘッドバイアス対策（内部で date.today() を直接参照しない等）
  - DuckDB を中心としたローカルデータ管理（ETL は差分更新・冪等保存）
  - 外部 API（J-Quants / OpenAI）呼び出しはリトライ・レート制御を実装
  - 監査ログ（signal → order_request → executions）で完全なトレーサビリティを保証

機能一覧
--------
- データ取得・保存（kabusys.data.jquants_client）
  - 株価日足（OHLCV）、財務情報、JPX マーケットカレンダー、上場銘柄一覧
  - レートリミット管理、リトライ、ID トークン自動リフレッシュ、DuckDB への冪等保存
- ETL パイプライン（kabusys.data.pipeline）
  - 日次 ETL(run_daily_etl): カレンダー、株価、財務の差分取得と品質チェック
  - 個別ジョブ: run_prices_etl / run_financials_etl / run_calendar_etl
  - ETLResult による集約レポート
- データ品質チェック（kabusys.data.quality）
  - 欠損、スパイク、重複、日付不整合などのチェックをまとめて実行
- マーケットカレンダー管理（kabusys.data.calendar_management）
  - 営業日判定、前後営業日の取得、カレンダー更新ジョブ
- ニュース収集（kabusys.data.news_collector）
  - RSS から記事取得、URL 正規化、SSRF 対策、raw_news / news_symbols への保存前処理
- AI（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp.score_news）: 銘柄ごとのセンチメントを OpenAI で算出し ai_scores に保存
  - マーケットレジーム判定（kabusys.ai.regime_detector.score_regime）: ETF（1321）の MA + マクロニュースで市場レジームを算出
  - OpenAI 呼び出しは JSON Mode / レスポンスバリデーション / 再試行対応
- 研究用ユーティリティ（kabusys.research）
  - ファクター計算 (momentum/value/volatility), forward returns, IC 計算, z-score 正規化
- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions の DDL と初期化ユーティリティ
  - init_audit_db / init_audit_schema を提供

セットアップ手順
--------------
1. リポジトリをクローンしてインストール（例: editable）
   - pip を用いる場合:
     - pip install -e .
   - 開発環境: Python 3.9+ を想定（コードの typing に準拠）

2. 必要な主な依存ライブラリ（pyproject.toml / setup にも依存）:
   - duckdb
   - openai
   - defusedxml
   - その他標準ライブラリ以外のパッケージ（requests ではなく urllib を使用している箇所が多い）

3. 環境変数 / .env
   - プロジェクトルートに .env/.env.local を置くと自動で読み込まれます（kabusys.config）。
     - 自動ロードを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
   - 必須と思われる環境変数（用途に応じて設定）:
     - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須：jquants_client.get_id_token 等で使用）
     - OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で使用）
     - KABU_API_PASSWORD: kabuステーション API のパスワード（発注系で使用）
     - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知を行う場合
     - KABUSYS_ENV: development / paper_trading / live（省略時 development）
     - LOG_LEVEL: DEBUG/INFO/…（省略時 INFO）
     - DUCKDB_PATH: デフォルト data/kabusys.duckdb（設定可）
     - SQLITE_PATH: 監視用 SQLite（設定可）
   - 例 (.env)
     JQUANTS_REFRESH_TOKEN=your_refresh_token
     OPENAI_API_KEY=sk-xxxx
     KABU_API_PASSWORD=...
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C12345678
     KABUSYS_ENV=development
     DUCKDB_PATH=data/kabusys.duckdb

使い方（基本例）
----------------

- DuckDB 接続の作成（デフォルト DB パスは settings.duckdb_path）
  - Python:
    from datetime import date
    import duckdb
    conn = duckdb.connect("data/kabusys.duckdb")

- 日次 ETL の実行
    from kabusys.data.pipeline import run_daily_etl
    from datetime import date
    conn = duckdb.connect("data/kabusys.duckdb")
    result = run_daily_etl(conn, target_date=date(2026,3,20))
    print(result.to_dict())

- ニュース NLP（OpenAI を用いた銘柄スコアリング）
    from datetime import date
    import os
    import duckdb
    from kabusys.ai.news_nlp import score_news
    conn = duckdb.connect("data/kabusys.duckdb")
    # api_key を明示的に渡すか、環境変数 OPENAI_API_KEY を設定
    n = score_news(conn, target_date=date(2026,3,20), api_key=os.getenv("OPENAI_API_KEY"))
    print(f"wrote {n} ai_scores")

- 市場レジーム判定（MA + マクロニュース）
    from datetime import date
    import duckdb
    from kabusys.ai.regime_detector import score_regime
    conn = duckdb.connect("data/kabusys.duckdb")
    score_regime(conn, target_date=date(2026,3,20), api_key=os.getenv("OPENAI_API_KEY"))

- 監査ログ DB 初期化
    from kabusys.data.audit import init_audit_db
    conn = init_audit_db("data/audit.duckdb")
    # 返される conn は DuckDB の接続オブジェクト

- ETL の個別実行（株価のみ等）
    from kabusys.data.pipeline import run_prices_etl
    from datetime import date
    conn = duckdb.connect("data/kabusys.duckdb")
    fetched, saved = run_prices_etl(conn, target_date=date(2026,3,20))
    print(f"fetched={fetched}, saved={saved}")

- データ品質チェックを単独で実行
    from kabusys.data.quality import run_all_checks
    issues = run_all_checks(conn, target_date=date(2026,3,20))
    for issue in issues:
        print(issue)

注意点 / ヒント
- OpenAI 呼び出しは API キーが必要です（環境変数 OPENAI_API_KEY を推奨）。
- J-Quants はレート制限・認証トークンの管理があるため、JQUANTS_REFRESH_TOKEN を設定してください。
- config モジュールは .env/.env.local をプロジェクトルートから自動ロードします。CI やテストで自動ロードを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- ETL は差分・バックフィルロジックを備えていますが、バックテスト等で使用する際は Look-ahead に注意してください（コード内に対策はありますが、利用方法次第で注意が必要です）。

主要ディレクトリ構成
-------------------
src/kabusys/
- __init__.py
- config.py
  - 環境変数・.env ロードロジック、settings オブジェクト
- ai/
  - __init__.py
  - news_nlp.py        — ニュースセンチメント評価（OpenAI 統合）
  - regime_detector.py — ETF MA とマクロニュースの合成による市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py  — J-Quants API クライアント（取得・保存・リトライ・レート制御）
  - pipeline.py        — ETL パイプライン（run_daily_etl 他）
  - calendar_management.py — 市場カレンダー管理（営業日判定、更新ジョブ）
  - news_collector.py  — RSS 収集・前処理・SSRF 対策
  - quality.py         — データ品質チェック
  - stats.py           — 汎用統計ユーティリティ（z-score 等）
  - audit.py           — 監査ログ（DDL / 初期化）
  - etl.py             — ETLResult 再エクスポート
- research/
  - __init__.py
  - factor_research.py — モメンタム・ボラティリティ・バリュー等のファクター計算
  - feature_exploration.py — forward returns / IC / 統計サマリー 等

例: 重要関数の位置
- run_daily_etl: kabusys.data.pipeline.run_daily_etl
- score_news: kabusys.ai.news_nlp.score_news
- score_regime: kabusys.ai.regime_detector.score_regime
- init_audit_db: kabusys.data.audit.init_audit_db
- J-Quants クライアント: kabusys.data.jquants_client

開発・拡張のポイント
- テスト時は外部 API 呼び出し部分（OpenAI / urllib / _urlopen 等）をモックする設計になっています。
- DuckDB の SQL を活用して効率的に集計・ウィンドウ関数を使う実装が多いため、クエリの最適化やスキーマ変更に注意してください。
- ai モジュールはレスポンスパース・バリデーションを厳密に行います。OpenAI のモデル/レスポンス形式を変える場合はそれらのバリデーションロジックの更新が必要です。

サンプル .env.example（参考）
--------------------------
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

サポート / 貢献
---------------
- バグ報告 / 機能提案は Issue を作成してください。
- 新機能追加時はテストとドキュメントを同梱してください。特に外部 API を使う箇所はモック可能な設計になっていることを確認してください。

以上がこのコードベースの README.md の概要です。必要であれば、導入手順の具体的なコマンドや .env.example の完全テンプレート、主要 API（関数）ごとの使用例を追加で作成します。どの部分を詳しく載せたいか教えてください。