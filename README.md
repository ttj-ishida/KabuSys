KabuSys
=======

KabuSys は日本株のデータプラットフォーム・リサーチ・自動売買のためのライブラリ群です。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集・NLP（LLM を用いたニュースセンチメント）、ファクター計算、監査ログ（発注→約定トレーサビリティ）などを提供します。

以下はこのリポジトリの README です。

プロジェクト概要
---------------
- 目的: 日本株のデータ収集・品質管理・ファクター研究・戦略実行のための再現性の高い基盤ライブラリ群を提供します。
- 主な設計方針:
  - ルックアヘッドバイアスに配慮（内部では date / target_date を明示的に使用し、datetime.today() の無責任な参照を避ける）。
  - ETL / 保存は冪等（upsert）で実装。
  - 外部 API 呼び出し（J-Quants / OpenAI 等）はレート制限・リトライ・フォールバックを備える。
  - DuckDB をメインの分析 DB として利用（軽量・高速・オンディスク/インメモリ両対応）。

機能一覧
--------
主なモジュールと機能（抜粋）:

- kabusys.config
  - .env / 環境変数の読み込み・管理（自動ロードあり）。必須設定の検証。
  - settings オブジェクト経由でアクセス可能。
  - 主要環境変数:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN（必須）
    - SLACK_CHANNEL_ID（必須）
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
    - SQLITE_PATH（デフォルト: data/monitoring.db）
    - KABUSYS_ENV（development / paper_trading / live、デフォルト development）
    - LOG_LEVEL（DEBUG/INFO/...、デフォルト INFO）

- kabusys.data
  - jquants_client: J-Quants API クライアント（取得・ページネーション・保存関数 / upsert）
  - pipeline: ETL 実行（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - news_collector: RSS 取得・前処理・raw_news 保存ロジック（SSRF 対策・トラッキング除去）
  - calendar_management: 市場カレンダー（営業日判定、next/prev_trading_day 等）
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit: 監査ログ（signal_events / order_requests / executions テーブル）初期化ユーティリティ
  - etl, stats: ETL 結果型、統計ユーティリティ（zscore_normalize）

- kabusys.ai
  - news_nlp.score_news: ニュース記事を銘柄別に集約して LLM（gpt-4o-mini）でセンチメントを算出し ai_scores テーブルに格納
  - regime_detector.score_regime: ETF (1321) の 200 日 MA 乖離とマクロニュースの LLM センチメントを合成して市場レジームを判定・保存

- kabusys.research
  - factor_research: モメンタム / バリュー / ボラティリティ等のファクター計算
  - feature_exploration: 将来リターン計算 / IC（Information Coefficient） / 統計サマリー 等

セットアップ手順
----------------

1. リポジトリをクローンし、仮想環境を作成
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - 必須（主要）パッケージ:
     - duckdb
     - openai (OpenAI の Python SDK)
     - defusedxml
   - 例（pip）:
     - pip install duckdb openai defusedxml

   ※ 実運用では requirements.txt / Poetry を用意してパッケージ管理してください。

3. 環境変数 (.env) を用意
   - プロジェクトルート（.git もしくは pyproject.toml のあるディレクトリ）に .env を置くと自動で読み込まれます。
   - 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します（テスト時に便利）。
   - .env の例:
     - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     - KABU_API_PASSWORD=your_kabu_password
     - SLACK_BOT_TOKEN=xoxb-...
     - SLACK_CHANNEL_ID=C01234567
     - DUCKDB_PATH=data/kabusys.duckdb
     - KABUSYS_ENV=development

   ※ 秘密情報（トークン等）は絶対にリポジトリにコミットしないでください。

4. DuckDB データベースの準備
   - デフォルトのパスは data/kabusys.duckdb（settings.duckdb_path で変更可）。
   - 初回は ETL を実行するか、スキーマ初期化関数（プロジェクト内に別途 schema 初期化がある場合）を呼んで下さい。
   - audit 用 DB を分離したい場合は kabusys.data.audit.init_audit_db を利用できます。

使い方（基本的な呼び出し例）
--------------------------

- DuckDB 接続を作る（例）:

  from datetime import date
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL を実行する:

  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニュースセンチメント（AI）スコアを生成する:

  from kabusys.ai.news_nlp import score_news
  from datetime import date

  # OPENAI_API_KEY は環境変数で設定するか、api_key 引数で渡す
  n_written = score_news(conn, target_date=date(2026,3,20), api_key="sk-...")
  print("scored:", n_written)

- 市場レジーム判定を実行する:

  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026,3,20), api_key="sk-...")

- 監査テーブルを初期化する（監査専用 DB を作る場合）:

  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit_duckdb.db")
  # init_audit_schema(audit_conn) は内部で呼ばれます

- ファクター計算 / 研究ユーティリティ:

  from kabusys.research.factor_research import calc_momentum
  from datetime import date

  records = calc_momentum(conn, target_date=date(2026,3,20))
  # zscore 正規化
  from kabusys.data.stats import zscore_normalize
  normalized = zscore_normalize(records, ["mom_1m", "mom_3m", "ma200_dev"])

注意点・運用メモ
---------------
- OpenAI 呼び出しは gpt-4o-mini を想定（response_format={"type":"json_object"} を使用）。API レスポンスのパース失敗・API障害時はフォールバック動作します（安全側で 0 スコアなど）。
- J-Quants API 用の id_token は jquants_client.get_id_token / _request が自動で管理します。環境変数 JQUANTS_REFRESH_TOKEN を設定してください。
- ETL と品質チェックは独立してエラーハンドリングされ、1 ステップ失敗でも他を継続します。結果は ETLResult で確認できます。
- ニュース収集は SSRF・Gzip Bomb 等に対する複数の防御を実装しています。
- デフォルトで .env の自動ロードが行われます。テストや特殊用途では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を指定して自動ロードを停止できます。

ディレクトリ構成
----------------

主要ファイルの一覧（src/kabusys 以下、抜粋）:

- src/kabusys/__init__.py
- src/kabusys/config.py

- src/kabusys/ai/
  - __init__.py
  - news_nlp.py           # ニュースセンチメント（LLM）処理
  - regime_detector.py    # 市場レジーム判定（MA + マクロニュース）

- src/kabusys/data/
  - __init__.py
  - jquants_client.py     # J-Quants API クライアント（fetch/save）
  - pipeline.py           # ETL メインロジック（run_daily_etl 等）
  - etl.py                # ETL 型の再エクスポート
  - news_collector.py     # RSS 収集・前処理
  - calendar_management.py# 市場カレンダー管理（営業日判定 等）
  - quality.py            # データ品質チェック
  - stats.py              # 統計ユーティリティ（zscore_normalize）
  - audit.py              # 監査ログ（テーブル定義・初期化）

- src/kabusys/research/
  - __init__.py
  - factor_research.py    # Momentum, Value, Volatility 等
  - feature_exploration.py# forward returns, IC, factor summary, rank

（注）README 要求に含まれていた top-level の monitoring / strategy / execution モジュールは __all__ に含まれていますが、この配布内に実装ファイルがないか部分的なため、実行環境に応じて別モジュールとして実装されていることを想定しています。

ライセンス / 貢献
-----------------
- 本リポジトリのライセンス情報はリポジトリルートの LICENSE ファイルを参照してください（存在しない場合は管理者に確認してください）。
- バグ修正・機能追加の際は既存コーディング規約（テスト、例外安全、ロギング）に従い PR をお願いします。

問い合わせ
----------
- 実運用・設定で不明点があれば、コード内の docstring / logger メッセージを参照してください。追加の使用例や運用手順が必要であれば、どの機能についてのドキュメントを充実させたいか教えてください。

以上。必要であれば、README にサンプル .env.example、requirements.txt、起動スクリプト例（systemd / cron / Airflow セットアップ）などの追加を作成します。どれを優先しますか？