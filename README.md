KabuSys — 日本株自動売買システム
===============================

概要
----
KabuSys は日本株向けのデータプラットフォームと自動売買／リサーチ基盤のプロトタイプです。  
主に次を提供します。

- J-Quants API を用いた株価・財務・マーケットカレンダーの差分 ETL パイプライン
- RSS ベースのニュース収集と OpenAI を用いたニュースセンチメント（AI スコアリング）
- 市場レジーム判定（ETF の MA とマクロニュースの合成）
- ファクター計算・特徴量探索・統計ユーティリティ（Research 用）
- 監査ログ（signal → order → execution トレース）の初期化ユーティリティ
- データ品質チェックモジュール

設計上の特徴：
- ルックアヘッドバイアス（Look-ahead bias）に配慮した設計（target_date を引数で明示、date.today() を不必要に参照しない）
- DuckDB をデータレイクとして使用（冪等保存・トランザクション制御を重視）
- OpenAI（gpt-4o-mini 等）を JSON Mode で利用する耐障害設計（リトライ・フォールバックあり）
- セキュリティ配慮（RSS の SSRF 対策、XML パースの defusedxml 利用 等）

機能一覧
--------
主な機能（モジュール単位）：

- kabusys.config
  - 環境変数の自動読み込み（.env/.env.local）と Settings（設定プロパティ）
  - 必須設定の検証（例: JQUANTS_REFRESH_TOKEN）

- kabusys.data
  - jquants_client: J-Quants API 呼び出し・保存関数（株価・財務・カレンダー）
  - pipeline: 日次 ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - news_collector: RSS 取得・前処理・保存（raw_news / news_symbols）
  - quality: データ品質チェック（欠損・スパイク・重複・日付整合性）
  - calendar_management: 営業日判定・カレンダー更新ジョブ
  - audit: 監査ログテーブルの初期化（signal_events / order_requests / executions）
  - stats: zscore_normalize などの統計ユーティリティ

- kabusys.ai
  - news_nlp.score_news: ニュースをまとめて LLM に送信し銘柄ごとの ai_score を生成
  - regime_detector.score_regime: ETF（1321）の MA200 乖離とマクロニュースの LLM スコアを合成して market_regime を算出

- kabusys.research
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank

セットアップ手順
----------------

前提
- Python 3.10+（typing | future の union 用法や型注釈を想定）
- duckdb, openai, defusedxml などの依存パッケージ

推奨手順（ローカル開発）
1. リポジトリをクローン
   - git clone <repo_url>

2. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. パッケージをインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml

   または開発用に setup.py/pyproject.toml がある場合:
   - pip install -e .

4. 環境変数設定
   - プロジェクトルートに .env を置く（自動読み込み機能あり）。主なキー:
     - JQUANTS_REFRESH_TOKEN (必須)
     - OPENAI_API_KEY (LLM 呼び出しに必要)
     - KABU_API_PASSWORD
     - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト: data/monitoring.db)
     - PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START
     - CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT
     - KABUSYS_ENV (development / paper_trading / live)
     - LOG_LEVEL (DEBUG/INFO/...)
   - 自動ロードを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. データディレクトリ作成（必要に応じて）
   - mkdir -p data

使い方（基本例）
----------------

DuckDB 接続の作成例
- Python REPL またはスクリプト内で:

  from kabusys.config import settings
  import duckdb
  conn = duckdb.connect(str(settings.duckdb_path))

ETL（翌日のデータを取得して保存）:
- 日次 ETL の実行（例: 今日分）
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings
  import duckdb
  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn)  # ETLResult オブジェクトを返す

個別 ETL ジョブ:
- 株価差分 ETL
  from kabusys.data.pipeline import run_prices_etl
  run_prices_etl(conn, target_date)

ニューススコアリング（AI）:
- 指定日分のニューススコアを生成し ai_scores テーブルへ書き込む
  from kabusys.ai.news_nlp import score_news
  from datetime import date
  score_news(conn, date(2026, 3, 20))  # OPENAI_API_KEY が必要

市場レジーム判定（AI + MA）:
  from kabusys.ai.regime_detector import score_regime
  from datetime import date
  score_regime(conn, date(2026, 3, 20))  # OPENAI_API_KEY が必要

監査ログ DB 初期化:
- 監査用 DuckDB を初期化（ファイル or :memory:）
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit.duckdb")

データ品質チェック:
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=date(2026,3,20))
  for i in issues:
      print(i.check_name, i.severity, i.detail)

設定（環境変数）の注意点
- Settings クラスは必要なキーをプロパティでラップしており、未設定の必須キー取得時には ValueError が発生します（例: settings.jquants_refresh_token）。
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml を上位に探索）を基準に行われます。自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OPENAI_API_KEY は AI モジュール（news_nlp, regime_detector）で使用します。引数で API キーを直接渡すことも可能です。

ディレクトリ構成
----------------
リポジトリ内の主なファイル・ディレクトリ（src/kabusys 以下を抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                   — 環境変数 / Settings 管理（.env 自動ロード含む）
  - ai/
    - __init__.py
    - news_nlp.py                — ニュースの LLM によるセンチメントスコア生成
    - regime_detector.py         — ETF MA とマクロニュースの合成による市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py          — J-Quants API クライアント（取得・保存関数）
    - pipeline.py                — ETL パイプライン（run_daily_etl 等）
    - news_collector.py          — RSS 収集 / 前処理 / 保存
    - calendar_management.py     — 市場カレンダー管理・営業日ロジック
    - quality.py                 — データ品質チェック
    - audit.py                   — 監査ログスキーマ定義・初期化
    - etl.py                     — ETLResult 再エクスポート
    - stats.py                   — zscore_normalize 等の統計ユーティリティ
  - research/
    - __init__.py
    - factor_research.py         — momentum / value / volatility 等の計算
    - feature_exploration.py     — forward returns / IC / summary / rank 等
  - ai, research, data 以下の詳細な実装ファイル...

注意・運用上のポイント
---------------------
- OpenAI API 呼び出しはリトライ等の耐障害ロジックがありますが、APIキーが無いと例外になります。CI／テストではモックを用いることを推奨します（モジュール内の _call_openai_api をパッチ可能）。
- jquants_client はレート制御（120 req/min）とリトライを備えています。ID トークンの自動リフレッシュも実装済みです。
- ニュース収集では SSRF 対策・XML の安全パース・レスポンスバイト上限等を実装しています。
- DuckDB の executemany に空リストを渡すとエラーになるバージョンがあります（0.10 等）。そのためコード内で空チェックを行っています。
- 監査ログは基本的に削除しない前提で設計されています（FK は ON DELETE RESTRICT）。

開発／テストのヒント
-------------------
- .env をテスト用に用意しつつ、テスト実行時に自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI / J-Quants の外部呼び出しはユニットテストでモックし、ネットワークに依存しないテストを作ることを推奨します。
- ETL の個別関数（run_prices_etl 等）は引数で id_token を渡せるため、テストではトークン注入が可能です。

貢献
----
バグ修正・改善提案・ドキュメント追加は歓迎します。Pull Request を送る前に issue を立てて概要を共有してください。

ライセンス
---------
（ここにプロジェクトのライセンス表記を入れてください）

以上。必要であれば、README にコマンド例（systemd / cron 用の実行例、Dockerfile、CI の設定例）や .env.example の雛形を追加します。どの情報がさらに欲しいか教えてください。