# KabuSys

日本株向け自動売買 / データプラットフォームライブラリ。  
ETL・データ品質、ニュース収集・NLP（OpenAI）による銘柄センチメント、リサーチ用ファクター計算、監査ログ（約定トレーサビリティ）などの機能を提供します。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 環境変数（.env）の説明
- 使い方（簡易コード例）
- ディレクトリ構成

---

プロジェクト概要
- KabuSys は日本株のデータ収集（J-Quants API 等）、ETL、データ品質チェック、ニュース収集・NLP（OpenAI を利用）、リサーチ用ファクター計算、そして戦略→発注までの監査ログを管理するためのユーティリティ群を含む Python パッケージです。
- Look-ahead bias を避ける設計や API 呼び出しのリトライ／フェイルセーフなど実運用を意識した設計方針が採られています。

主な機能一覧
- 環境設定管理（kabusys.config）
  - .env/.env.local の自動ロード（プロジェクトルート検出）
  - 必須変数の検査ユーティリティ
- データ取得・ETL（kabusys.data.jquants_client / kabusys.data.pipeline）
  - J-Quants API からの株価・財務・カレンダー取得、DuckDB への冪等保存
  - 日次 ETL パイプライン run_daily_etl（差分取得・バックフィル・品質チェック）
- データ品質チェック（kabusys.data.quality）
  - 欠損・スパイク・重複・日付不整合検出
- カレンダー管理（kabusys.data.calendar_management）
  - 営業日判定 / next/prev_trading_day / カレンダー更新ジョブ
- ニュース収集（kabusys.data.news_collector）
  - RSS フィード収集、記事正規化、SSRF 対策、raw_news への保存想定
- ニュースNLP / レジーム判定（kabusys.ai.news_nlp / kabusys.ai.regime_detector）
  - OpenAI（gpt-4o-mini）を使った銘柄ごとのセンチメント（ai_scores）やマクロセンチメントを組み合わせた市場レジーム判定
- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions など監査テーブルの初期化・運用ヘルパー
- 研究用ユーティリティ（kabusys.research）
  - ファクター計算（モメンタム / バリュー / ボラティリティ）、将来リターン計算、IC 計算、Z スコア標準化

セットアップ手順（開発環境向け、例）
1. Python 環境（3.10+ 推奨）を用意
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - 主要な依存パッケージ（最低限）:
     - duckdb
     - openai
     - defusedxml
   - 例:
     - pip install duckdb openai defusedxml

   ※ 実プロジェクトでは pyproject.toml / requirements.txt を用意して pip install -e . や pip install -r requirements.txt を実行してください。

3. 環境変数を設定
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に .env を置くと自動読み込みされます（kabusys.config）。
   - 自動読み込みを無効にする場合:
     - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用リフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で使用）
- KABU_API_PASSWORD: kabu ステーション API のパスワード
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: 通知用（任意）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視等で使用）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START: 実行監視用
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT: 監視閾値
- KABUSYS_ENV: environment (development / paper_trading / live)
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）

例 (.env)
    JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
    OPENAI_API_KEY=sk-...
    KABU_API_PASSWORD=your_kabu_password
    DUCKDB_PATH=data/kabusys.duckdb
    KABUSYS_ENV=development
    LOG_LEVEL=INFO

設定読み込みの振る舞い
- 読み込み優先順位: OS環境変数 > .env.local > .env
- プロジェクトルート検出は kabusys.config._find_project_root() により .git または pyproject.toml を上位ディレクトリから探索して行われます
- .env のパースはシェル形式に近い仕様（コメント、export 付き行、クォート処理）に対応

使い方（簡易例）
- DuckDB 接続を開き ETL 実行（最も基本的な流れ）
    import duckdb
    from datetime import date
    from kabusys.data.pipeline import run_daily_etl

    conn = duckdb.connect("data/kabusys.duckdb")
    result = run_daily_etl(conn, target_date=date(2026, 3, 20))
    print(result.to_dict())

- OpenAI を使ったニューススコアリング
    import duckdb
    from datetime import date
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect("data/kabusys.duckdb")
    written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key を None にすると環境変数 OPENAI_API_KEY を参照
    print(f"scored {written} codes")

- 市場レジーム判定
    from kabusys.ai.regime_detector import score_regime
    from datetime import date

    conn = duckdb.connect("data/kabusys.duckdb")
    score_regime(conn, target_date=date(2026, 3, 20), api_key=None)

- 監査テーブル初期化（別 DB を使う場合）
    from kabusys.data.audit import init_audit_db
    conn = init_audit_db("data/monitoring_audit.duckdb")

- news_collector の RSS 収集（単体）
    from kabusys.data.news_collector import fetch_rss
    articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")

注意点 / 実運用上のポイント
- OpenAI API 呼び出しは料金が発生するため、開発時はモックや少量テストを推奨します。score_news / score_regime はレスポンスパース失敗時にフェイルセーフでスコア 0 にフォールバックします。
- J-Quants API はレート制限や認証トークンのリフレッシュ処理が組み込まれています。JQUANTS_REFRESH_TOKEN を必ず設定してください。
- DuckDB executemany に空リストを渡すとエラーになるバージョンがあるため（コード内で対策済み）、ETL 呼び出しは通常問題ありません。
- ニュース収集では SSRF 対策や受信サイズ制限、XML パース安全化（defusedxml）を行っています。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                          -- 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                       -- ニュースセンチメント解析・score_news
    - regime_detector.py                -- マクロ + MA200 による市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py                -- J-Quants API クライアント・保存ロジック
    - pipeline.py                      -- ETL パイプライン（run_daily_etl 等）
    - etl.py                           -- ETLResult エクスポート
    - calendar_management.py           -- マーケットカレンダー管理
    - news_collector.py                -- RSS 収集・前処理
    - stats.py                         -- zscore_normalize 等
    - quality.py                       -- データ品質チェック
    - audit.py                         -- 監査ログ（テーブル初期化等）
  - research/
    - __init__.py
    - factor_research.py               -- ファクター計算（momentum/value/volatility）
    - feature_exploration.py           -- 将来リターン / IC / 統計サマリー
  - (その他) strategy / execution / monitoring 用モジュールがエクスポート対象として定義されていますが、ここに示したファイル群がコアです。

開発・拡張のヒント
- OpenAI 呼び出し部はテスト容易性のため _call_openai_api を内部で分離しているので、unittest.mock.patch で差し替えてテストが可能です。
- DuckDB を用いているためローカルでの高速な分析・クエリ試行が可能です。ETL は差分更新・バックフィルを行う設計なので、定期ジョブ化（cron / systemd timer / Airflow 等）が現実的です。
- 監査ログは削除しない前提の設計で、order_request_id を冪等キーとして再送対策を内包しています。

ライセンス / 貢献
- この README はコードベースから生成されたドキュメント案です。パッケージのライセンスやコントリビュートルール（CONTRIBUTING.md）がプロジェクトルートに存在する場合はそちらを参照してください。

---

必要に応じて README に含める実行例、API の戻り値形式、.env.example の完全サンプルや CI / デプロイ手順を追加できます。追加を希望する項目があれば教えてください。