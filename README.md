KabuSys — 日本株自動売買基盤（README — 日本語）
======================================

概要
----
KabuSys は日本株向けのデータプラットフォームと戦略実行パイプラインを備えた自動売買基盤のライブラリです。  
主に以下の責務を持ちます。

- J-Quants API からの市場データ / 財務データ / カレンダーの取得（レート制御・リトライ・トークン自動更新対応）
- DuckDB を用いたデータスキーマの初期化・永続化（Raw / Processed / Feature / Execution 層）
- ETL（差分取得・保存・品質チェック）を日次バッチで実行
- ニュース収集（RSS）と記事→銘柄紐付け
- 研究用ファクター計算（momentum / volatility / value 等）および特徴量生成（Zスコア正規化等）
- 戦略シグナル生成（複合スコア計算・BUY/SELL 判定）
- 監査ログ／トレーサビリティのためのスキーマ設計

主な設計指針として、ルックアヘッドバイアス回避、冪等性（ON CONFLICT）・トランザクション保護、外部ライブラリへの依存最小化（標準ライブラリ中心）が挙げられます。

主な機能一覧
------------
- データ取得 / 保存
  - J-Quants API クライアント（fetch/save: 日足・財務・カレンダー）
  - DuckDB 用スキーマ定義と初期化（init_schema）
  - 差分 ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
- データ品質・カレンダー管理
  - 市場カレンダーの先読み・営業日判定（is_trading_day / next_trading_day / get_trading_days）
- ニュース収集
  - RSS 取得（fetch_rss）・記事正規化・DB 保存（save_raw_news）・銘柄抽出（extract_stock_codes）
  - SSRF 対策・サイズ制限・XML 安全パース対応
- 研究（Research）
  - ファクター計算（calc_momentum / calc_volatility / calc_value）
  - 将来リターン計算・IC 計算・統計サマリ（calc_forward_returns / calc_ic / factor_summary）
  - 共通統計ユーティリティ（zscore_normalize）
- 特徴量 / 戦略
  - 特徴量構築（build_features）: 生ファクターを正規化・合成して features テーブルへ保存
  - シグナル生成（generate_signals）: 最終スコア計算・BUY / SELL 判定・signals テーブル更新
- 監査
  - signal_events / order_requests / executions など監査用テーブル定義と初期化ロジック

セットアップ手順
----------------

前提
- Python 3.10 以上（PEP 604 の | 型注釈などを使用）
- DuckDB（Python パッケージ）
- defusedxml（RSS パースの安全化）
- ネットワークアクセス（J-Quants API）

1. 仮想環境の作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージのインストール（例）
   - pip install duckdb defusedxml

   （プロジェクトをパッケージ化している場合は pip install -e . など）

3. 環境変数設定
   必須環境変数（少なくとも次を設定してください）:
   - JQUANTS_REFRESH_TOKEN … J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD … kabuステーション等の API パスワード（使用する場合）
   - SLACK_BOT_TOKEN … Slack 通知に使う Bot トークン（使用する場合）
   - SLACK_CHANNEL_ID … Slack チャンネル ID（使用する場合）

   データベースパス（省略可、デフォルト値）
   - DUCKDB_PATH (default: data/kabusys.duckdb)
   - SQLITE_PATH (default: data/monitoring.db)

   実行環境やログレベル:
   - KABUSYS_ENV ∈ {development, paper_trading, live} (default: development)
   - LOG_LEVEL ∈ {DEBUG, INFO, WARNING, ERROR, CRITICAL} (default: INFO)

   .env 自動読み込み:
   - パッケージはプロジェクトルート（.git または pyproject.toml）を探して .env/.env.local を自動で読み込みます。
   - 自動ロードを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

4. データベーススキーマ初期化
   - Python REPL またはスクリプトで DuckDB を初期化します（例: data/kabusys.duckdb を作成）:

     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")

使い方（代表的なコードスニペット）
------------------------------

- DuckDB スキーマ初期化（初回のみ）

  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")
  # 以後 conn を各処理に渡す

- 日次 ETL（市場カレンダー取得・株価・財務差分取得・品質チェック）
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn)  # 省略時は target_date = today
  print(result.to_dict())

- 特徴量構築（例: 2024-01-10 の特徴量を構築）
  from kabusys.strategy import build_features
  from datetime import date
  n = build_features(conn, date(2024, 1, 10))
  print("upserted:", n)

- シグナル生成（features と ai_scores を参照して signals を作成）
  from kabusys.strategy import generate_signals
  from datetime import date
  total = generate_signals(conn, date(2024, 1, 10), threshold=0.6)
  print("signals:", total)

- ニュース収集ジョブ実行（既知銘柄 set を渡して紐付けまで行う）
  from kabusys.data.news_collector import run_news_collection
  known_codes = {"7203","6758", ...}  # 事前に用意
  res = run_news_collection(conn, known_codes=known_codes)
  print(res)

- カレンダー更新夜間ジョブ
  from kabusys.data.calendar_management import calendar_update_job
  saved = calendar_update_job(conn)
  print("saved calendar rows:", saved)

設定・環境変数の注意点
----------------------
- 必須の秘密情報（API トークン等）は .env に保存して権限管理を徹底してください。
- .env.local は .env 上書き用のローカル設定として優先されます（OS 環境変数はさらに優先）。
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使えばテストや CI で自動ロードを抑制できます。

ディレクトリ構成（コードベースの抜粋）
-----------------------------------
src/kabusys/
  __init__.py
  config.py                       # 環境変数 / 設定管理
  data/
    __init__.py
    jquants_client.py              # J-Quants API クライアント（取得/保存）
    news_collector.py              # RSS 収集・保存・銘柄抽出
    pipeline.py                    # ETL パイプライン（run_daily_etl など）
    schema.py                      # DuckDB スキーマ定義 / init_schema
    stats.py                       # zscore_normalize 等の統計ユーティリティ
    features.py                    # 公開ラッパ
    calendar_management.py         # market_calendar 更新・営業日判定等
    audit.py                       # 監査ログ用 DDL
  research/
    __init__.py
    factor_research.py             # momentum / volatility / value 計算
    feature_exploration.py         # 将来リターン/IC/統計サマリ
  strategy/
    __init__.py
    feature_engineering.py         # build_features
    signal_generator.py            # generate_signals
  execution/
    __init__.py                     # 発注層（拡張点）
  monitoring/                        # monitoring モジュールはパッケージ定義に含まれるが個別ファイルは省略（将来的拡張）
テーブル定義や各モジュールは README に書ききれないほど詳細な仕様コメントが含まれており、コード中の docstring を参照することで使用方法・制約（例: 欠損値ハンドリング、トランザクションポリシー）を確認できます。

運用上の注意・トラブルシューティング
---------------------------------
- J-Quants のレート制限（120 req/min）に合わせた内部レートリミッタ実装がありますが、API 側ポリシー変更時はパラメータ調整が必要です。
- ETL は差分取得と backfill（デフォルト 3 日）を行います。運用ポリシーに応じて backfill_days を調整してください。
- DuckDB ファイルは単一プロセスでの更新が前提です。並列プロセスからの同時書き込みは設計に注意してください。
- ニュース収集は外部 RSS をフェッチするためネットワーク・外部サイトの変化（非標準フィード）でパース失敗が発生します。fetch_rss は失敗をログに残して空リストを返す設計です。

貢献・拡張ポイント
------------------
- execution 層（ブローカー API 連携、オーダー送信/約定取込み）の具体実装
- モニタリング / アラート（Slack 通知ラッパ）
- AI スコア生成パイプライン（ai_scores を埋める処理）
- テストカバレッジ（各 ETL / ファクター計算 / RSS パーサのユニット）

最後に
------
この README はコード上の docstring と実装に基づく概要です。各モジュールの使用法や引数の詳細は該当ファイルの docstring を参照してください。質問や利用上の補足が必要であれば、どの機能について知りたいかを教えてください。