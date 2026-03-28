KabuSys — 日本株自動売買 / データ基盤ライブラリ
====================================

概要
----
KabuSys は日本株向けの自動売買システムおよびデータプラットフォームのためのライブラリ群です。  
主に以下の責務を備えます。

- J-Quants API からの市場データ（株価・財務・カレンダー）取得と ETL
- ニュース収集・NLP（LLM）による銘柄センチメント付与
- 市場レジーム判定（テクニカル指標 + マクロニュースの LLM スコア混合）
- リサーチ用ファクター計算・特徴量探索ユーティリティ
- データ品質チェック
- 発注・約定の監査ログ（監査テーブル初期化ユーティリティ）
- 環境変数を中心とした設定管理

このリポジトリはライブラリとして import して使うことを想定しており、ETL や scoring、監査 DB 初期化などを Python API 経由で実行できます。

主な機能一覧
--------------
- data/jquants_client.py
  - J-Quants API クライアント：株価（OHLCV）、財務、上場情報、マーケットカレンダー取得
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
  - レートリミット・リトライ・トークン自動リフレッシュ対応

- data/pipeline.py / data/etl.py
  - 日次 ETL パイプライン（run_daily_etl）
  - 個別 ETL（run_prices_etl, run_financials_etl, run_calendar_etl）
  - ETL 実行結果を表す ETLResult

- data/news_collector.py
  - RSS フィード収集、URL 正規化、SSRF 対策、raw_news への冪等保存支援

- ai/news_nlp.py
  - raw_news と news_symbols を集約して OpenAI（gpt-4o-mini）に投げ、
    銘柄ごとのセンチメント ai_score を ai_scores テーブルに書き込む（score_news）

- ai/regime_detector.py
  - ETF（1321）の200日移動平均乖離とマクロニュースの LLM スコアを組み合わせて
    日次の市場レジーム（bull/neutral/bear）を market_regime に書き込む（score_regime）

- research/
  - ファクター計算（momentum/value/volatility 等）、将来リターン計算、IC 計算、統計サマリー

- data/quality.py
  - 欠損・スパイク・重複・日付不整合チェック（run_all_checks）

- data/audit.py
  - 発注→約定までの監査ログ用テーブル定義と初期化ユーティリティ（init_audit_schema / init_audit_db）

- config.py
  - .env / .env.local の自動ロード（プロジェクトルート検出）
  - Settings オブジェクト経由で環境変数を型安全に参照
  - 自動ロード無効化：KABUSYS_DISABLE_AUTO_ENV_LOAD=1

セットアップ手順
----------------

1. Python 環境（推奨: 3.10+）を用意する

2. 必要パッケージをインストールする（例）
   - 必要な主な依存: duckdb, openai, defusedxml
   - pip 例:
     python -m pip install duckdb openai defusedxml

   ※ 本リポジトリに requirements.txt / pyproject.toml がある場合はそれに従ってください。
   開発時は editable install:
     python -m pip install -e .

3. 環境変数の準備
   プロジェクトルート（.git や pyproject.toml のある階層）に .env または .env.local を置くと自動読み込みされます（config.py による）。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

   最低限設定が必要な環境変数（主なもの）
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD: kabuステーション API のパスワード（発注系を使う際）
   - SLACK_BOT_TOKEN: Slack 通知を使う場合
   - SLACK_CHANNEL_ID: Slack 通知を使う場合
   - OPENAI_API_KEY: OpenAI を呼ぶ機能（score_news, score_regime）を使う場合

   例 .env:
     JQUANTS_REFRESH_TOKEN=xxxxxxxx
     OPENAI_API_KEY=sk-...
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C0123456789

4. データベースファイル準備
   - デフォルトの DuckDB パスは data/kabusys.duckdb（Settings.duckdb_path）です。必要に応じて .env で DUCKDB_PATH を上書きします。

使い方（主なコード例）
--------------------

- DuckDB に接続して日次 ETL を実行する
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(kabusys.config.settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())

- ニューススコア付与（score_news）
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect(str(kabusys.config.settings.duckdb_path))
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込み銘柄数: {n_written}")

  ※ OpenAI API キーを明示的に渡すことも可能:
    score_news(conn, date(2026,3,20), api_key="sk-...")

- 市場レジーム判定（score_regime）
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect(str(kabusys.config.settings.duckdb_path))
  score_regime(conn, target_date=date(2026,3,20))
  # market_regime テーブルに書き込みが行われます

- 監査ログ用 DB 初期化
  from kabusys.data.audit import init_audit_db

  conn = init_audit_db("data/monitoring.db")
  # 必要な監査テーブル・インデックスが作成されます

- 設定参照
  from kabusys.config import settings
  print(settings.env, settings.duckdb_path, settings.is_live)

主な設計・運用上の注意
--------------------
- ルックアヘッドバイアスの防止:
  多くの処理（news window 計算、MA 計算、ETL）は内部で date 引数を取り、datetime.today()/date.today() を直接参照しない設計です。バックテスト等で意図的に過去日を与えて再現性のある挙動が得られます。

- 自動 .env ロード:
  config.py はプロジェクトルート（.git または pyproject.toml）を起点に .env / .env.local を自動読込します。テストなどで自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

- OpenAI / J-Quants API:
  - OpenAI 呼び出しは retry や 5xx / RateLimit のハンドリングを備えていますが、API キーやレート制限に注意してください。
  - J-Quants 側もリフレッシュトークン→id_token 自動リフレッシュとレート制御を備えています。

- DuckDB executemany の空リスト:
  DuckDB のバージョンによっては executemany に空リストを与えられないため、空チェックを行ってから実行します（pipeline や news_nlp 内で対応済み）。

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py                         — 環境変数 / Settings 管理
- ai/
  - __init__.py
  - news_nlp.py                      — ニュース NLP / score_news
  - regime_detector.py               — 市場レジーム判定 / score_regime
- data/
  - __init__.py
  - jquants_client.py                — J-Quants API クライアント + 保存ロジック
  - pipeline.py                      — ETL パイプライン（run_daily_etl 等）
  - etl.py                           — ETL インターフェース（ETLResult 再エクスポート）
  - news_collector.py                — RSS 収集・前処理
  - calendar_management.py           — 市場カレンダー管理 / 営業日ユーティリティ
  - quality.py                       — データ品質チェック
  - stats.py                         — 共通統計ユーティリティ（zscore_normalize）
  - audit.py                         — 監査ログテーブル定義 / 初期化
- research/
  - __init__.py
  - factor_research.py               — ファクター計算（momentum/value/volatility）
  - feature_exploration.py           — 将来リターン / IC / summary / rank
- research/*.py (補助ユーティリティ等)

その他補足
---------
- テスト容易性のため、AI 呼び出しやネットワーク I/O の部分は内部関数をモック可能に設計されています（例: kabusys.ai.news_nlp._call_openai_api を patch など）。
- セキュリティ面では news_collector で SSRF 対策・XML 外部実行防止（defusedxml）・レスポンスサイズ制限を行っています。

貢献・開発
----------
- バグ報告、改善提案は Issue を作成してください。
- 大きな変更は PR を作成してレビューを依頼してください。

ライセンス
----------
この README はコードベースに付随する説明です。実際のライセンス表記はリポジトリの LICENSE ファイルをご参照ください。

以上。必要であればインストール手順を CI/CD 向けに具体化したり、よく使う CLI スクリプトの例（ETL を定期実行する cron / Airflow タスク等）を追記します。どの操作例を追加したいか教えてください。