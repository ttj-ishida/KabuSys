# KabuSys

日本株向けのデータプラットフォーム兼自動売買研究基盤。  
DuckDB をコアストレージに、J-Quants / RSS / OpenAI 等と連携してデータ取得・品質チェック・特徴量算出・ニュース NLP・市場レジーム判定・監査ログ（注文〜約定のトレーサビリティ）を提供します。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（主要 API の例）
- 環境変数（.env）
- ディレクトリ構成（主要ファイル説明）

---

プロジェクト概要
- DuckDB を用いた金融データ ETL と品質管理、研究（factor / feature）ライブラリ、ニュース NLP（OpenAI）を組み合わせた日本株向け基盤。
- J-Quants API から株価・財務・市場カレンダー等を差分取得して DuckDB に保存し、品質チェック・監査ログ・研究用特徴量計算を行う。
- ニュースは RSS で収集し、OpenAI（gpt-4o-mini 等）で銘柄ごとのセンチメントやマクロセンチメントを算出。
- バックテストや自動売買の上位レイヤーから利用可能なユーティリティ群を提供。

機能一覧
- 環境変数管理（自動 .env ロード／読み取り）
- J-Quants API クライアント（認証、ページネーション、レート制御、再試行）
- ETL パイプライン（株価・財務・カレンダーの差分取得と保存）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- マーケットカレンダー管理（営業日判定、次/前営業日取得）
- ニュース収集（RSS → raw_news、SSRF 対策、正規化）
- ニュース NLP（OpenAI を用いた銘柄センチメント、JSON Mode バリデーション、バッチ処理）
- 市場レジーム判定（ETF の MA とマクロニュースセンチメントの加重合成）
- 研究用ユーティリティ（momentum / volatility / value 等のファクター、forward returns、IC、統計サマリ）
- 監査ログスキーマ（signal / order_request / executions の冪等・トレーサビリティ用テーブル）
- DuckDB へ冪等的にデータ保存するユーティリティ

セットアップ手順（開発環境）
1. Python バージョンの確認（3.10+ 推奨）
2. リポジトリをクローン
   - git clone <repo>
3. パッケージをインストール（開発用）
   - python -m pip install -e .
   - 必要な外部ライブラリ（例）
     - duckdb
     - openai
     - defusedxml
     - もし要件ファイルがあれば: pip install -r requirements.txt
4. 環境変数の設定
   - プロジェクトルートに `.env` / `.env.local` を置く（下の「環境変数」を参照）
   - 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定
5. DuckDB / SQLite 用ディレクトリを作成（settings のデフォルトに従う）
   - data フォルダなど（settings.duckdb_path の親ディレクトリを作成）

主要環境変数（.env の例）
- 必須
  - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
  - SLACK_BOT_TOKEN=your_slack_bot_token
  - SLACK_CHANNEL_ID=your_slack_channel_id
  - KABU_API_PASSWORD=your_kabu_station_password
  - OPENAI_API_KEY=your_openai_api_key
- 任意 / デフォルトあり
  - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (デフォルト: data/monitoring.db)
  - PID_FILE_PATH (デフォルト: data/execution.pid)
  - CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT
  - KABUSYS_ENV (development | paper_trading | live) - default: development
  - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL)

例 (.env)
JQUANTS_REFRESH_TOKEN=REPLACE_ME
OPENAI_API_KEY=REPLACE_ME
SLACK_BOT_TOKEN=REPLACE_ME
SLACK_CHANNEL_ID=REPLACE_ME
DUCKDB_PATH=data/kabusys.duckdb

使い方（コード例）
- 共通: settings を使って設定を取得できます
  from kabusys.config import settings
  print(settings.duckdb_path)

- DuckDB 接続を開く
  import duckdb
  from kabusys.config import settings
  conn = duckdb.connect(str(settings.duckdb_path))

- ETL（日次パイプライン）の実行
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings
  import duckdb
  from datetime import date

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニュースセンチメント（銘柄ごと）をスコアリングして ai_scores に保存
  from kabusys.ai.news_nlp import score_news
  import duckdb
  from datetime import date
  conn = duckdb.connect(str(settings.duckdb_path))
  n = score_news(conn, target_date=date(2026,3,20), api_key=None)  # OPENAI_API_KEY を環境から参照
  print(f"scored {n} codes")

- 市場レジーム判定（market_regime テーブルへ保存）
  from kabusys.ai.regime_detector import score_regime
  import duckdb
  from datetime import date
  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026,3,20), api_key=None)

- 研究用ファクター計算
  from kabusys.research.factor_research import calc_momentum, calc_volatility, calc_value
  conn = duckdb.connect(str(settings.duckdb_path))
  records = calc_momentum(conn, target_date=date(2026,3,20))
  # records は [{ "date": ..., "code": "...", "mom_1m": ..., ... }, ...]

- 監査ログ DB 初期化（監査専用 DB を作る）
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit.duckdb")
  # テーブルが作成されます

- RSS フィード取得（ニュースコレクタの HTTP 部分）
  from kabusys.data.news_collector import fetch_rss
  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", "yahoo_finance")
  # NewsArticle のリストが返る（id, datetime, source, title, content, url）

注意点 / 実運用上のポイント
- API キーが未設定だと score_news / score_regime 等は ValueError を送出します（api_key 引数で上書き可能）。
- J-Quants API はレート制限（120 req/min）を守る実装が入っていますが、実行環境の並列処理には注意してください。
- OpenAI 呼び出しは冗長トライアル・エクスポネンシャルバックオフ等フォールバック実装あり。API障害時は安全に 0.0 を返すなどの設計です。
- データ品質チェック（quality.run_all_checks）により問題を検知できます。ETL 実行結果の quality_issues を確認して運用判断してください。
- カレンダー情報や raw_news などが未取得のままだとフォールバック（曜日ベース等）で動作しますが、正確性のため ETL を定期実行して最新データを確保してください。

ディレクトリ構成（src/kabusys の主なファイルと責務）
- __init__.py
  - パッケージレベルのバージョン宣言と公開モジュール
- config.py
  - 環境変数読み込み（.env/.env.local 自動ロード）と Settings クラス
- ai/
  - news_nlp.py: ニュースをまとめて OpenAI に投げて銘柄別スコアを作成するロジック
  - regime_detector.py: ETF 1321 の MA とニュースセンチメントを合成して市場レジームを出す
- data/
  - pipeline.py: ETL のエントリポイント（run_daily_etl 等）・ETLResult
  - jquants_client.py: J-Quants API 用クライアント（取得・保存関数含む）
  - quality.py: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - calendar_management.py: 市場カレンダー・営業日ユーティリティ
  - news_collector.py: RSS 収集、SSRF 防御、テキスト正規化
  - audit.py: 監査ログスキーマ初期化（signal / order_requests / executions）
  - etl.py: pipeline.ETLResult の公開再エクスポート
  - stats.py: z-score 正規化などの小さな統計ユーティリティ
- research/
  - factor_research.py: Momentum / Volatility / Value の計算
  - feature_exploration.py: forward returns / IC / factor summary / rank 等の研究用関数
  - __init__.py: 研究 API の再エクスポート
- その他
  - data ディレクトリに DuckDB ファイルを置くことを想定（settings.duckdb_path の既定: data/kabusys.duckdb）

補足
- README では主要な API と使い方例のみを示しています。実装の詳細は各モジュールの docstring を参照してください。
- 自動ロードされる .env の優先順は OS 環境 > .env.local > .env です。テスト等で自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

以上。必要であれば README の英語版や、より詳細な運用手順（Cron / systemd / コンテナ化、監視・アラート設定例、DB スキーマ図など）も作成できます。どの追加情報が欲しいか教えてください。