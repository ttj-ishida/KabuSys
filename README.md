KabuSys — 日本株自動売買基盤 (README)
=================================

概要
----
KabuSys は日本株の自動売買／データプラットフォームを目的とした Python パッケージのコア実装です。  
主に以下の機能を提供します。

- J-Quants API からの市場データ取得（株価日足、四半期財務、マーケットカレンダー）
- DuckDB によるデータ格納（スキーマ定義・初期化）
- ETL パイプライン（差分取得、バックフィル、品質チェック）
- RSS ベースのニュース収集と銘柄抽出（SSRF / XML 攻撃対策、トラッキング除去）
- マーケットカレンダー管理・営業日判定ロジック
- 監査ログ（シグナル→発注→約定のトレース）用スキーマ

設計上のポイント
- API レート制限・リトライ（指数バックオフ）を考慮
- データ取得の冪等性（ON CONFLICT / DO UPDATE / DO NOTHING）
- Look-ahead bias 回避のため fetched_at を UTC で記録
- RSS/HTTP に対する SSRF 対策・受信サイズ上限・安全な XML パース
- 品質チェックは Fail-Fast ではなく問題を集めて報告（呼び出し元で判断）

主な機能一覧
----------------
- データ取得（kabusys.data.jquants_client）
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_* 関数で DuckDB に冪等保存
  - レート制限（120 req/min）、401 時トークン自動リフレッシュ、リトライ制御
- ETL（kabusys.data.pipeline）
  - run_daily_etl: カレンダー → 株価 → 財務 → 品質チェック の一連処理
  - 差分取得・バックフィルの自動算出
- スキーマ管理（kabusys.data.schema）
  - init_schema(db_path) で DuckDB を初期化（Raw / Processed / Feature / Execution 層）
  - get_connection(db_path) で既存 DB に接続
- ニュース収集（kabusys.data.news_collector）
  - fetch_rss, save_raw_news, save_news_symbols
  - URL 正規化（utm 等除去）、記事 ID は URL の SHA-256（先頭32文字）
  - SSRF 防止、gzip 解凍、XML Bomb 防止（defusedxml）
- カレンダー管理（kabusys.data.calendar_management）
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day
  - calendar_update_job による夜間差分更新
- 品質チェック（kabusys.data.quality）
  - 欠損データ、重複、スパイク（前日比閾値）、日付整合性チェック
  - QualityIssue 型で問題を集計して返却
- 監査ログ初期化（kabusys.data.audit）
  - signal_events / order_requests / executions 等の監査用テーブルを作成

前提・依存関係
---------------
- Python 3.10 以上（PEP 604 の型表記（X | None）を使用）
- 必要なパッケージ（例）
  - duckdb
  - defusedxml
- ネットワーク接続（J-Quants API、RSS ソース等）

セットアップ手順
----------------
1. リポジトリを取得
   - git clone でプロジェクトを取得します。

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install --upgrade pip
   - pip install duckdb defusedxml
   - （プロジェクト配布に requirements.txt があれば pip install -r requirements.txt）

4. 環境変数の設定
   - プロジェクトルートに .env/.env.local を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットすると自動ロードを無効化できます）。
   - 必須変数（settings で require として定義）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - 任意・デフォルト付き
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動ロードを無効化する場合に 1 を設定
     - KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db
     - LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）

   例 (.env の一部)
   - JQUANTS_REFRESH_TOKEN=xxxxxxxx
   - KABU_API_PASSWORD=your_password
   - SLACK_BOT_TOKEN=xoxb-...
   - SLACK_CHANNEL_ID=C01234567
   - DUCKDB_PATH=data/kabusys.duckdb
   - KABUSYS_ENV=development

使い方（簡単な流れ・サンプル）
----------------------------

1) DuckDB スキーマの初期化
- Python から呼ぶ例:
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")
  # これで各テーブルとインデックスが作成されます

2) 日次 ETL の実行
- run_daily_etl を使う例:
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn)
  print(result.to_dict())

  - run_daily_etl は市場カレンダー → 株価 → 財務 → 品質チェック の順に処理します。
  - id_token を外部で取得して注入することも可能（テスト容易性のため）。

3) ニュース収集ジョブの実行
- RSS フィード収集と保存:
  from kabusys.data.news_collector import run_news_collection
  results = run_news_collection(conn, sources=None, known_codes={"7203", "6758"})
  print(results)  # {source_name: 新規保存数}

4) 監査ログ用 DB の初期化（監査専用 DB を分ける場合）
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.duckdb")

注意点 / 運用メモ
-----------------
- J-Quants API のレート制限（120 req/min）に合わせて内部でスロットリングされています。大量一括処理時は間隔に注意してください。
- jquants_client は 401 を検出するとリフレッシュトークンから id_token を再取得して 1 回だけリトライします。
- DuckDB のファイルは共有ファイルシステム（NFS など）での同時書き込みに注意してください。複数プロセスでの同時書き込みは想定外の挙動を招く可能性があります。
- RSS 収集では SSRF 対策、gzip 展開後のサイズチェック、defusedxml による安全な XML パースを行っていますが、収集先の信頼性には注意してください。
- ETL の品質チェックは問題を列挙して返す方式です。重大度 (error/warning) に応じて呼び出し元でアクション（停止・アラート等）を決定してください。

ディレクトリ構成（抜粋）
-----------------------
src/kabusys/
- __init__.py
- config.py                     # 環境変数・設定管理
- data/
  - __init__.py
  - jquants_client.py           # J-Quants API クライアント（fetch/save）
  - news_collector.py          # RSS ニュース収集・保存・銘柄抽出
  - pipeline.py                # ETL パイプライン（run_daily_etl 等）
  - schema.py                  # DuckDB スキーマ定義・初期化
  - calendar_management.py     # 市場カレンダー管理 / 営業日判定
  - quality.py                 # データ品質チェック
  - audit.py                   # 監査ログ（signal/order/execution）初期化
- strategy/
  - __init__.py                 # 戦略関連（将来的に拡張）
- execution/
  - __init__.py                 # 発注周り（将来的に拡張）
- monitoring/
  - __init__.py                 # 監視用モジュール（将来的に拡張）

サポートする環境変数（まとめ）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (任意, default http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- DUCKDB_PATH (任意, default data/kabusys.duckdb)
- SQLITE_PATH (任意, default data/monitoring.db)
- KABUSYS_ENV (development | paper_trading | live, default development)
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL, default INFO)
- KABUSYS_DISABLE_AUTO_ENV_LOAD (1 を設定すると .env 自動ロードを無効化)

開発・拡張のポイント
--------------------
- strategy / execution / monitoring パッケージは拡張ポイントです。シグナル生成・リスク管理・ブローカー接続はここに実装してください。
- テストしやすい設計を意識しており、jquants_client の id_token 注入や news_collector._urlopen のモックなど挿し替え可能な箇所があります。
- DuckDB は SQL での集計やウィンドウ関数が高速なので、特徴量計算やバックテスト基盤にも適しています。

ライセンス・その他
------------------
- 本 README にはライセンス情報は含まれていません。プロジェクトのライセンスはリポジトリの LICENSE ファイルを参照してください。

お問い合わせ・貢献
-----------------
- バグや改善提案は Issue を立ててください。Pull Request も歓迎します。

以上。必要であれば、README にサンプル .env.example や簡易の CLI 実行サンプル（cron 用の wrapper スクリプト例など）を追加できます。どの情報を追加したいか教えてください。