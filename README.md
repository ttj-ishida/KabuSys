KabuSys — 日本株自動売買基盤（README）
=================================

概要
---
KabuSys は日本株向けのデータプラットフォーム / 研究・ファクター解析 / ニュース NLP / 市場レジーム判定 / ETL / 監査ログなどを含む自動売買基盤のライブラリ群です。  
主に以下の目的に使います：

- J-Quants からの株価・財務・カレンダー等の差分 ETL
- ニュース収集と OpenAI を使ったニュースセンチメント解析（銘柄別 ai_score）
- マクロニュースと ETF（1321）に基づく市場レジーム判定
- ファクター（モメンタム・バリュー・ボラティリティ等）の計算・探索
- データ品質チェック、監査ログ（signal/order/execution）のスキーマ初期化・管理

主要な設計方針：
- Look-ahead バイアス回避（内部で date.today() を安易に参照しない設計）
- DuckDB をデータストアとして利用（軽量で高速な分析向け DB）
- OpenAI（gpt-4o-mini）を JSON Mode で呼び出して NLP を行う（失敗時はフェイルセーフ）
- 冪等性（ON CONFLICT / idempotent 保存）とトランザクション管理を重視

主な機能一覧
---------------
- ETL（kabusys.data.pipeline）
  - run_daily_etl：市場カレンダー／価格／財務の差分取得・保存・品質チェックの一括実行
  - run_prices_etl / run_financials_etl / run_calendar_etl：個別ジョブ
- J-Quants API クライアント（kabusys.data.jquants_client）
  - fetch_* / save_* 系関数（ページネーション・認証リフレッシュ・レートリミット・リトライ対応）
- ニュース収集（kabusys.data.news_collector）
  - RSS 取得・URL 正規化・前処理・raw_news への冪等保存設計
- データ品質チェック（kabusys.data.quality）
  - 欠損・スパイク・重複・日付不整合の検出
- 監査ログ（kabusys.data.audit）
  - signal_events, order_requests, executions の DDL/インデックス定義と初期化ユーティリティ
- AI 関連（kabusys.ai）
  - score_news：銘柄別ニュースセンチメントを ai_scores テーブルへ書き込み
  - score_regime：ETF 1321 の MA200 乖離とマクロニュース LLM スコアを合成して market_regime に保存
- 研究用ユーティリティ（kabusys.research）
  - calc_momentum / calc_value / calc_volatility / calc_forward_returns / calc_ic / factor_summary / zscore_normalize
- 設定管理（kabusys.config）
  - .env / .env.local 自動読み込み（プロジェクトルート検出）・必須環境変数チェック

前提・依存
-----------
- Python 3.10+
- 必要パッケージ（例）:
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリ以外は requirements.txt にまとめてください）
- J-Quants API アカウント（リフレッシュトークン）
- OpenAI API キー（ニュース / レジーム判定で使用）
- kabuステーション API 情報（発注周りを扱う場合）

セットアップ手順
-----------------
1. 仮想環境作成と依存インストール（例）
   - python -m venv .venv
   - source .venv/bin/activate
   - pip install --upgrade pip
   - pip install duckdb openai defusedxml
   - （プロジェクト用に requirements.txt / pyproject.toml があればそちらを使用）

2. リポジトリ配置
   - パッケージが src/kabusys 以下にある想定です。開発時は editable install を推奨:
     - pip install -e .

3. 環境変数 / .env の準備
   - プロジェクトルート（pyproject.toml または .git のある親ディレクトリ）が自動検出され、
     ルートの .env と .env.local が自動読み込みされます（OS 環境変数が優先）。
   - 自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
   - 必要な環境変数（一例）:
     - JQUANTS_REFRESH_TOKEN=...
     - OPENAI_API_KEY=...
     - KABU_API_PASSWORD=...
     - SLACK_BOT_TOKEN=...
     - SLACK_CHANNEL_ID=...
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - KABUSYS_ENV=development|paper_trading|live
     - LOG_LEVEL=INFO|DEBUG|...
   - .env.example（プロジェクト側で用意してください）を参考に作成します。

4. DuckDB ファイルの作成（任意）
   - デフォルトの duckdb ファイルは data/kabusys.duckdb（settings.duckdb_path）
   - 監査専用 DB は init_audit_db で初期化可能（例: data/audit.duckdb）

使い方（簡単なコード例）
-----------------------

共通：settings の使用
- 環境変数は kabusys.config.settings から取得できます（必須値は未設定時に ValueError を出します）。
  例：
    from kabusys.config import settings
    db_path = settings.duckdb_path
    is_live = settings.is_live

1) DuckDB 接続を作って ETL を実行する
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

2) ニュースセンチメント（銘柄別）を算出して ai_scores に書き込む
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込み銘柄数: {written}")

  - score_news は OpenAI API キーを api_key 引数で渡すか、環境変数 OPENAI_API_KEY を参照します。
  - テスト時は kabusys.ai.news_nlp._call_openai_api をパッチしてモックできます。

3) 市場レジーム判定を実行する
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))

4) 監査ログスキーマ初期化（order/signals 用）
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # または既存接続に対して:
  # from kabusys.data.audit import init_audit_schema
  # init_audit_schema(conn, transactional=True)

5) 研究用ファクター計算（例: モメンタム）
  from kabusys.research.factor_research import calc_momentum
  conn = duckdb.connect(str(settings.duckdb_path))
  records = calc_momentum(conn, target_date=date(2026, 3, 20))
  # records は各銘柄ごとの辞書リスト

運用上の注意・補足
-----------------
- OpenAI 呼び出しは外部 API に依存するため、API の制限やコストに注意してください。モック可能な設計になっています（テスト時は _call_openai_api を差し替え）。
- J-Quants クライアントは rate limit（120 req/min）や 401 のリフレッシュ、リトライロジックを実装しています。ID トークンのキャッシュをモジュール内で保持します。
- ETL は部分失敗を許容する設計（各ステップは例外をキャッチして結果を集約）。品質チェックで error が検出された場合は呼び出し元で対応を決めてください。
- プロジェクトルートの自動 .env ロードは __file__ を基準に親ディレクトリを探索するため、パッケージ配布後も機能します。自動ロードを停止する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

ディレクトリ構成（抜粋）
------------------------
src/kabusys/
- __init__.py                 — パッケージ初期化（__version__ など）
- config.py                   — 環境変数 / 設定読み込みユーティリティ
- ai/
  - __init__.py
  - news_nlp.py               — ニュース NLP（score_news 等）
  - regime_detector.py        — 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - calendar_management.py    — 市場カレンダー判定・更新ロジック
  - jquants_client.py         — J-Quants API クライアント（fetch / save）
  - pipeline.py               — ETL パイプライン（run_daily_etl 等）
  - etl.py                    — ETLResult の再エクスポート
  - stats.py                  — zscore_normalize 等の統計ユーティリティ
  - quality.py                — データ品質チェック
  - audit.py                  — 監査ログ DDL / 初期化ユーティリティ
  - news_collector.py         — RSS 収集・前処理
- research/
  - __init__.py
  - factor_research.py        — モメンタム / バリュー / ボラティリティ
  - feature_exploration.py    — 将来リターン / IC / 統計サマリー 等

ライセンス・貢献
----------------
- 本リポジトリ固有のライセンスファイル（LICENSE）をプロジェクトルートに配置してください。
- バグ報告・プルリクエスト歓迎です。外部 API キーや機密情報は含めないでください。

最後に
------
この README はコードベースの主要機能と使い方の概観を示しています。より詳細な API ドキュメントや運用手順（cron / Airflow / コンテナ化・監視の設定など）は別途作成することを推奨します。必要であれば具体的なユースケース（ETL スケジュール、発注フロー、モニタリング通知）向けのドキュメント作成も支援します。