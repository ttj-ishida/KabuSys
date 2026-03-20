README — KabuSys
=================

概要
----
KabuSys は日本株向けの自動売買 / データプラットフォームのライブラリ群です。  
J-Quants などの外部データソースから市場データ・財務データ・ニュースを取得し、DuckDB に格納、特徴量計算 → シグナル生成 → 発注監査までのワークフローをサポートします。設計上は「ルックアヘッドバイアスの排除」「冪等性」「ネットワーク／セキュリティ対策（SSRF・XML BOM 等）」を重視しています。

主な機能
---------
- データ取得 / ETL
  - J-Quants API 経由で日次株価（OHLCV）、財務データ、JPX カレンダーを差分取得（RateLimit / retry / トークン自動リフレッシュ対応）
  - RSS からのニュース収集（SSRF対策・XML安全パース・URL正規化・記事ID生成）
  - DuckDB スキーマ定義・初期化（冪等）
- データ加工 / 解析
  - ファクター計算（Momentum / Volatility / Value 等）
  - クロスセクション Z スコア正規化ユーティリティ
  - 将来リターン・IC（Spearman）・統計サマリー等の研究用ユーティリティ
- 戦略 / シグナル
  - 特徴量構築（feature_engineering.build_features）
  - シグナル生成（strategy.signal_generator.generate_signals） — final_score による BUY/SELL 判定、Bear フィルタ、エグジット判定（ストップロス等）
- 実行層 / 監査
  - signals / signal_queue / orders / executions / positions 等の実行レイヤーテーブル定義
  - 監査ログ（signal_events / order_requests / executions）でトレーサビリティを確保
- その他
  - マーケットカレンダー管理（営業日判定, next/prev_trading_day）
  - DB 品質チェック（pipeline の品質チェックフロー）

セットアップ手順
----------------
前提
- Python 3.10 以上（型注釈や | 合成型を使用）
- ネットワーク接続（J-Quants API / RSS フィードへのアクセス）
- 推奨: 仮想環境（venv, pipenv, poetry 等）

1. リポジトリをクローンして仮想環境を用意
   - git clone ...  
   - python -m venv .venv && source .venv/bin/activate

2. 依存ライブラリをインストール
   - 最低限必要なパッケージ:
     - duckdb
     - defusedxml
   - 例:
     - pip install duckdb defusedxml

   （プロジェクトに requirements.txt / pyproject.toml があればそちらを使ってください）

3. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml がある場所）に .env を置くと自動でロードされます（.env.local を上書きする形で読み込み）。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
   - 主な環境変数（.env.example を参照して作成してください）:
     - 必須:
       - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
       - SLACK_BOT_TOKEN — Slack 通知用トークン（本プロジェクトの Slack 統合を使う場合）
       - SLACK_CHANNEL_ID — Slack チャネルID
       - KABU_API_PASSWORD — kabuステーション API を使う場合のパスワード
     - オプション／デフォルトあり:
       - KABUSYS_ENV (development | paper_trading | live) — デフォルト development
       - LOG_LEVEL (DEBUG|INFO|...) — デフォルト INFO
       - DUCKDB_PATH — デフォルト data/kabusys.duckdb
       - SQLITE_PATH — デフォルト data/monitoring.db

4. DuckDB スキーマ初期化
   - Python REPL またはスクリプトで実行:
     - from kabusys.data.schema import init_schema
     - conn = init_schema("data/kabusys.duckdb")
   - ":memory:" を指定すればインメモリ DB を使用可能です。

基本的な使い方（コード例）
--------------------------

1) DB 初期化と接続
- 例:
  - from kabusys.data.schema import init_schema
  - conn = init_schema("data/kabusys.duckdb")

2) 日次 ETL を実行する（J-Quants から差分取得して保存）
- 例:
  - from kabusys.data.pipeline import run_daily_etl
  - result = run_daily_etl(conn)
  - print(result.to_dict())

3) 特徴量の構築（features テーブルへ書き込む）
- 例:
  - from kabusys.strategy import build_features
  - from datetime import date
  - n = build_features(conn, date(2024, 1, 1))
  - print(f"features upserted: {n}")

4) シグナル生成（signals テーブルへ書き込む）
- 例:
  - from kabusys.strategy import generate_signals
  - from datetime import date
  - total = generate_signals(conn, date(2024, 1, 1), threshold=0.6)
  - print(f"signals written: {total}")

5) ニュース収集
- 例:
  - from kabusys.data.news_collector import run_news_collection
  - known_codes = {"7203", "6758", ...}  # 既知の銘柄コードセット
  - results = run_news_collection(conn, known_codes=known_codes)
  - print(results)

6) カレンダー更新バッチ
- 例:
  - from kabusys.data.calendar_management import calendar_update_job
  - saved = calendar_update_job(conn)
  - print(f"calendar saved: {saved}")

設定と挙動に関する注意点
-----------------------
- 自動環境変数ロード:
  - パッケージ読み込み時にプロジェクトルートの .env および .env.local を自動で読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。ファイルはプロジェクトルート（.git または pyproject.toml のあるディレクトリ）から探します。
  - .env のパースは export プレフィックス・クォート・インラインコメント等に対応しています。

- J-Quants クライアント:
  - レート制限 120 req/min を守るため固定間隔スロットリングを実装しています。
  - 408/429/5xx に対して指数バックオフリトライ、401 はトークン自動リフレッシュを試みます。
  - 取得データは fetched_at に UTC 時刻を記録し、いつデータが得られたかをトレース可能にしています。

- ニュース収集:
  - RSS の XML パースは defusedxml を使用して安全化しています。
  - URL 正規化 → SHA-256（先頭32文字）で記事IDを作成するため冪等性を確保します。
  - SSRF 対策としてリダイレクト先のスキーム・ホストの検査、受信サイズ上限（デフォルト 10MB）制限、gzip 解凍後のサイズチェック等を行います。

- 冪等性:
  - DuckDB への保存処理は ON CONFLICT DO UPDATE / DO NOTHING を多用しており、同じデータを複数回保存しても重複しない設計です。

- 安全系ログ／例外:
  - 各主要処理は例外を捕捉してログ出力し、できる限り他の処理を続行する設計です（ETL の各ステップは独立してエラーハンドリング）。

ディレクトリ構成（省略版）
-------------------------
以下は本リポジトリ中の主要なモジュール構成（src/kabusys 以下）です。README 用に主要ファイルのみ列挙しています。

- src/
  - kabusys/
    - __init__.py
    - config.py                      -- 環境変数 / 設定管理
    - data/
      - __init__.py
      - jquants_client.py            -- J-Quants API クライアント（取得・保存）
      - news_collector.py            -- RSS ニュース収集・前処理・保存
      - schema.py                    -- DuckDB スキーマ定義 / init_schema
      - stats.py                     -- zscore_normalize 等統計ユーティリティ
      - pipeline.py                  -- ETL パイプライン（run_daily_etl 等）
      - features.py                  -- public re-export
      - calendar_management.py       -- カレンダー管理（営業日判定等）
      - audit.py                     -- 監査ログ DDL / 初期化（部分）
      - (その他)                     -- quality 等（参照される）
    - research/
      - __init__.py
      - factor_research.py           -- Momentum/Volatility/Value 等
      - feature_exploration.py       -- 将来リターン・IC・summary
    - strategy/
      - __init__.py
      - feature_engineering.py       -- features テーブル構築
      - signal_generator.py          -- signals テーブルの生成ロジック
    - execution/                      -- 実行層（発注・監視）関連（空の __init__ など）
    - monitoring/                     -- 監視用 DB / ログ関連（別途実装）

（プロジェクトルートには .git / pyproject.toml / .env.example 等が想定されます）

環境変数一覧（主なもの）
------------------------
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants の refresh token。
- KABU_API_PASSWORD (必須 if using kabu API) — kabu API パスワード。
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須 if using Slack) — Slack ボットトークン
- SLACK_CHANNEL_ID (必須 if using Slack) — Slack チャンネルID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト data/monitoring.db）
- KABUSYS_ENV — development | paper_trading | live（デフォルト development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...、デフォルト INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 任意: 自動 .env 読み込みを無効化（"1" 等）

運用上の注意
------------
- 本コードは実運用を想定した多くの安全策を組み込んでいますが、実際の資金運用を行う前に十分なテストと監査を行ってください。
- 発注・ブローカー接続部分（execution 層）は環境に依存するため、paper_trading 環境での動作確認を推奨します。
- API トークンやシークレットは必ず安全に管理し、リポジトリやログに漏らさないでください。

ライセンス / 貢献
-----------------
- 本 README はコードベースから生成されています。ライセンス・貢献ルールはリポジトリルートの LICENSE / CONTRIBUTING.md を参照してください（存在する場合）。

サンプルスクリプト（まとめ）
---------------------------
簡単な起動スクリプト例:

from datetime import date
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl
from kabusys.strategy import build_features, generate_signals

conn = init_schema("data/kabusys.duckdb")
etl_result = run_daily_etl(conn)
# ETL 後に特徴量・シグナル生成
trading_day = date.today()
build_features(conn, trading_day)
generate_signals(conn, trading_day)

以上。README に不足している箇所やサンプルの追加・日本語表現の調整などが必要であれば教えてください。