KabuSys — 日本株自動売買プラットフォーム
=================================

概要
----
KabuSys は日本株向けのデータパイプライン、ファクター研究、ニュース NLP、監査ログ、ETL、マーケットカレンダー管理などを備えた自動売買基盤のライブラリ群です。本リポジトリは主に以下を目的としています。

- J-Quants API からのデータ取得（株価・財務・カレンダー）
- DuckDB を用いたデータ格納と ETL パイプライン
- ニュース記事の収集 → LLM（OpenAI）によるセンチメント解析（銘柄別 ai_score）
- マーケットレジーム判定（ETF MA とマクロニュースの組合せ）
- 研究用ファクター計算・特徴量解析（モメンタム、ボラティリティ、バリュー、IC 等）
- 監査ログ（signal → order_request → executions のトレーサビリティ）
- データ品質チェック、カレンダー管理、ニュース収集のユーティリティ

主な機能一覧
-------------
- 環境変数管理（自動 .env ロード、必須設定のバリデーション）: kabusys.config
- J-Quants API クライアント（認証自動リフレッシュ、レート制御、リトライ）: kabusys.data.jquants_client
- ETL パイプライン（日次 ETL、差分取得、品質チェック）: kabusys.data.pipeline
- ニュース収集（RSS → raw_news、SSRF/サイズ/トラッキング対策）: kabusys.data.news_collector
- ニュース NLP（OpenAI を用いた銘柄別センチメント評価）: kabusys.ai.news_nlp
- 市場レジーム判定（ETF 1321 の MA とマクロニュースを合成）: kabusys.ai.regime_detector
- 研究用ファクター計算（momentum/value/volatility 等）: kabusys.research
- 統計ユーティリティ（Z-score 正規化等）: kabusys.data.stats
- カレンダー管理（営業日判定、次の営業日/前の営業日取得、カレンダー更新ジョブ）: kabusys.data.calendar_management
- データ品質チェック（欠損・重複・スパイク・日付不整合）: kabusys.data.quality
- 監査ログテーブルの初期化／専用 DB 作成ユーティリティ: kabusys.data.audit

前提・依存
-----------
最低限の想定依存パッケージ（抜粋）:
- Python 3.10+（typing 機能や union 型記法に依存）
- duckdb
- openai (OpenAI Python SDK)
- defusedxml

実際のプロジェクトでは pyproject.toml / requirements.txt を参照して依存をインストールしてください。

セットアップ手順
----------------

1. リポジトリをチェックアウト
   - git clone ...

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存をインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml

   （本プロジェクトに合わせた requirements ファイルがある場合はそちらを使用してください）

4. 環境変数 / .env の準備
   プロジェクトルートに .env（および任意で .env.local）を作成してください。自動読み込みの仕組みがあり、OS 環境変数 > .env.local > .env の順でマージされます。自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

   主要な環境変数（例）
   - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
   - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime で使用）
   - KABU_API_PASSWORD: kabu ステーション API のパスワード（運用時）
   - SLACK_BOT_TOKEN: Slack 通知用トークン（運用時）
   - SLACK_CHANNEL_ID: Slack チャンネル ID（運用時）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH: SQLite（監視用）パス（デフォルト data/monitoring.db）
   - PID_FILE_PATH: デーモン監視用 PID ファイル（デフォルト data/execution.pid）
   - KABUSYS_ENV: development | paper_trading | live（デフォルト development）
   - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト INFO）

5. DuckDB データベースの準備
   - デフォルトでは settings.duckdb_path が data/kabusys.duckdb です。
   - 必要に応じて db ファイルを作成しスキーマを適用する初期化スクリプトを用意してください（本リポジトリではテーブル作成関数群が提供されています）。

使い方（主要ユーティリティの例）
------------------------------

以下は Python REPL / スクリプトでの呼び出し例です。settings を利用してパスや環境変数を参照します。

- DuckDB 接続取得（例）
  from kabusys.config import settings
  import duckdb
  conn = duckdb.connect(str(settings.duckdb_path))

- ETL を日次で実行する
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings
  import duckdb
  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=None)  # target_date を指定すればその日で実行
  print(result.to_dict())

- ニュースのセンチメントを評価して ai_scores に書き込む
  from kabusys.ai.news_nlp import score_news
  import duckdb, datetime
  conn = duckdb.connect(str(settings.duckdb_path))
  date = datetime.date(2026, 3, 20)
  count = score_news(conn, date, api_key=None)  # api_key None なら OPENAI_API_KEY を参照
  print(f"書き込み件数: {count}")

- 市場レジーム判定を実行して market_regime に書き込む
  from kabusys.ai.regime_detector import score_regime
  import duckdb, datetime
  conn = duckdb.connect(str(settings.duckdb_path))
  date = datetime.date(2026, 3, 20)
  score_regime(conn, date, api_key=None)

- 監査ログ DB の初期化（監査専用 DB を作る）
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit.duckdb")
  # conn_audit をアプリで使用

- 監査スキーマだけを既存接続に適用する
  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn, transactional=True)

設計上の注意点（重要）
--------------------
- Look-ahead バイアス対策: 多くの関数（news_nlp, regime_detector, research）では内部で datetime.today()/date.today() を直接参照せず、必ず引数で target_date を渡す設計です。バックテストや再現性のため、必ず明示的な日付を使用してください。
- OpenAI 呼び出し: news_nlp と regime_detector は JSON モードを利用します。テスト時には _call_openai_api をモックして外部呼び出しを差し替えることができます（モジュール内のパスを patch してください）。
- 自動 .env ロード: kabusys.config はプロジェクトルート（.git または pyproject.toml がある親ディレクトリ）を探索して .env/.env.local を読み込みます。テストで自動ロードを抑止したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB executemany の特性: 一部処理で executemany に空リストを渡すとエラーになるため、パラメータが空でないかチェックした上で呼び出しています。

ディレクトリ構成（概要）
-----------------------

- src/kabusys/
  - __init__.py                : パッケージ初期化（__version__ / __all__）
  - config.py                  : 環境変数・設定管理（.env 自動ロード、Settings クラス）
  - ai/
    - __init__.py
    - news_nlp.py              : ニュース NLP（OpenAI で銘柄別センチメントを算出）
    - regime_detector.py      : 市場レジーム判定（ETF + マクロニュース）
  - data/
    - __init__.py
    - jquants_client.py       : J-Quants API クライアント（取得＋DuckDB 保存）
    - pipeline.py             : ETL パイプライン（run_daily_etl 等）
    - etl.py                  : ETLResult の再エクスポート
    - calendar_management.py  : 市場カレンダー管理（営業日判定・更新ジョブ）
    - news_collector.py       : RSS → raw_news 収集ユーティリティ（SSRF 対策等）
    - quality.py              : データ品質チェック（欠損・スパイク・重複・日付不整合）
    - stats.py                : 統計ユーティリティ（zscore_normalize 等）
    - audit.py                : 監査ログスキーマ初期化・audit DB の生成
  - research/
    - __init__.py
    - factor_research.py      : ファクター計算（momentum/value/volatility）
    - feature_exploration.py  : 将来リターン計算／IC／統計サマリー／rank
  - monitoring/ (必要に応じた監視関連モジュールが入る想定)
  - strategy/, execution/ (戦略・約定関連モジュールはパッケージ外部で実装想定)

運用上のヒント
--------------
- ETL は定期バッチ（深夜）で実行し、calendar_update_job を先に動かすことで営業日の扱いが正しくなります。
- ニュース NLP とレジーム判定は API コスト（OpenAI）とレイテンシを考慮してスケジュール／バッチ化してください。
- 監査ログは削除せず永続化する設計になっています（ON DELETE RESTRICT）。バックアップ戦略を推奨します。
- ログレベルと KABUSYS_ENV を適切に設定し、production（live）運用時は十分な監視とフェイルセーフを用意してください。

テスト・モック
--------------
- OpenAI 呼び出しや外部 HTTP を伴う箇所はモック可能です。news_nlp と regime_detector 内の _call_openai_api はユニットテストで patch してレスポンスを差し替えることを想定しています。
- jquants_client._request もネットワークを伴うため、ユニット／統合テストでは HTTP 呼び出しをモックしてください。

ライセンス／貢献
----------------
本 README はコードベースの説明を目的としています。実際の運用・商用利用に際してはライセンス、API 利用規約（J-Quants、OpenAI 等）を確認してください。パッチや改善提案は Pull Request を歓迎します。

付録: よく使うコードスニペット
----------------------------
- settings の参照
  from kabusys.config import settings
  print(settings.duckdb_path, settings.jquants_refresh_token is not None)

- ニューススコアの一括取得（例）
  import duckdb, datetime
  conn = duckdb.connect(str(settings.duckdb_path))
  d = datetime.date(2026, 3, 20)
  from kabusys.ai.news_nlp import score_news
  score_news(conn, d)

- レジーム判定の実行（例）
  from kabusys.ai.regime_detector import score_regime
  score_regime(conn, d)

以上が KabuSys の概観と基本的な使い方です。必要に応じて各モジュール内の docstring（関数・クラス説明）を参照してください。README に載せてほしい追加情報（CI, Docker, 詳細なスキーマ定義等）があれば教えてください。