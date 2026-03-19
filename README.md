KabuSys
=======

KabuSys は日本株のデータ収集・ETL・特徴量作成・シグナル生成・監査用スキーマを備えた
自動売買 / 研究プラットフォームの軽量ライブラリです。
主要コンポーネントは DuckDB を利用したデータレイヤ、J-Quants API クライアント、RSS ベースのニュース収集、
研究用ファクター計算、戦略の特徴量エンジニアリングとシグナル生成、発注・監査用スキーマ群です。

主な特徴
--------

- データ取得
  - J-Quants API クライアント（ページネーション対応、トークン自動リフレッシュ、レート制限・リトライ制御）
  - 株価（日足）、財務データ、JPX カレンダーの取得/保存
- ETL パイプライン
  - 差分フェッチ（最終取得日ベース）、backfill による後出し修正吸収
  - 品質チェックフック（quality モジュールとの連携）
- データレイヤ（DuckDB）
  - Raw / Processed / Feature / Execution の多層スキーマを提供（冪等な DDL・INDEX 定義）
  - raw_prices / prices_daily / raw_financials / features / ai_scores / signals / orders / executions など
- 研究・特徴量
  - momentum / volatility / value 等のファクター計算（research/factor_research）
  - Z スコア正規化ユーティリティ（data.stats）
  - 特徴量構築（strategy.feature_engineering）と保存（features テーブル）
- シグナル生成
  - ファクター + AI スコアを統合して final_score を算出、BUY / SELL を生成して signals テーブルへ保存
  - Bear レジーム抑制、ストップロス等のエグジット判定を実装
- ニュース収集
  - RSS フィード取得・安全対策（SSRF対策、size-limit、defusedxml）・記事正規化・銘柄抽出・DB保存
- 監査ログ
  - signal_events / order_requests / executions 等の監査用テーブルでトレーサビリティを保持

必須環境変数
--------------

KabuSys は .env または環境変数から設定を読み込みます（プロジェクトルートに .env / .env.local があれば自動読み込み）。
必須のキーは下記です。各キーは settings 経由で参照されます。

- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD : kabu ステーション API のパスワード（必須）
- SLACK_BOT_TOKEN : Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID : Slack 投稿先チャンネル ID（必須）

その他の任意/デフォルト設定:
- KABUSYS_ENV : development | paper_trading | live （デフォルト: development）
- LOG_LEVEL : DEBUG | INFO | WARNING | ERROR | CRITICAL （デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD : 1 を設定すると .env 自動ロードを無効化
- KABU_API_BASE_URL : kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH : 監視用 SQLite パス（デフォルト: data/monitoring.db）

セットアップ手順
---------------

前提
- Python 3.10 以上（型注釈で | を使用）
- Git（.env 自動探索でプロジェクトルートを検出するため推奨）

1. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  または  .\.venv\Scripts\activate

2. 依存パッケージのインストール
   - pip install duckdb defusedxml
   - （パッケージ配布用に pyproject / requirements があれば pip install -e . 等）

3. 環境変数準備
   - プロジェクトルートに .env を作成（例: .env.example を参考に）
   - 例 (.env):
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development

4. DuckDB スキーマ初期化
   - Python REPL / スクリプトで以下を実行:
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
   - ":memory:" を渡すとインメモリ DB が使えます。

使い方（主要 API 例）
--------------------

基本的なワークフロー例:

1) スキーマ初期化 / 接続
   from kabusys.config import settings
   from kabusys.data.schema import init_schema, get_connection
   # 初回は init_schema を使ってファイルを作成
   conn = init_schema(settings.duckdb_path)

2) 日次 ETL 実行（株価・財務・カレンダー取得 + 品質チェック）
   from kabusys.data.pipeline import run_daily_etl
   from datetime import date
   result = run_daily_etl(conn, target_date=date.today())
   print(result.to_dict())

3) 特徴量構築（features テーブルへ保存）
   from kabusys.strategy import build_features
   build_count = build_features(conn, date.today())  # target_date に対して冪等に上書き
   print(f"features upserted: {build_count}")

4) シグナル生成（signals テーブルへ保存）
   from kabusys.strategy import generate_signals
   total_signals = generate_signals(conn, date.today(), threshold=0.60)
   print(f"signals written: {total_signals}")

5) ニュース収集（RSS 取得 → raw_news / news_symbols 保存）
   from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
   known_codes = {"7203", "6758", "9984", ...}  # 既知銘柄セット（抽出用）
   res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
   print(res)

6) カレンダー更新ジョブ（夜間バッチ）
   from kabusys.data.calendar_management import calendar_update_job
   saved = calendar_update_job(conn, lookahead_days=90)
   print(f"calendar saved: {saved}")

実装上の注意点
--------------

- .env の自動読み込み:
  - プロジェクトルートを .git または pyproject.toml を基準に探索し、.env/.env.local を読み込みます。
  - OS 環境変数は優先され、.env.local は .env を上書きします。
  - 自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- 冪等性:
  - jquants_client.save_* 系、news_collector.save_raw_news / save_news_symbols、schema.init_schema などは冪等に設計されています。
  - ETL / 特徴量構築 / シグナル生成は「日付単位で DELETE してから INSERT」することで日付単位の置換を行い、冪等化しています。

- セキュリティ & 安全対策:
  - RSS フェッチは SSRF 対策（リダイレクト先チェック、プライベートIP拒否）、受信サイズ制限、defusedxml を用いた XML パースを実装。
  - J-Quants クライアントはリトライ・レート制限・トークン自動更新を実装。

ディレクトリ構成
---------------

（重要なファイル・モジュールを抜粋）

- src/kabusys/
  - __init__.py
  - config.py                         # 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py               # J-Quants API クライアント & 保存ロジック
    - news_collector.py               # RSS 収集・前処理・保存
    - schema.py                       # DuckDB スキーマ / init_schema / get_connection
    - pipeline.py                     # ETL パイプライン（run_daily_etl 等）
    - calendar_management.py          # JPX カレンダー管理・ユーティリティ
    - features.py                     # zscore_normalize の再エクスポート
    - stats.py                        # 統計ユーティリティ（zscore_normalize）
    - audit.py                         # 監査ログ用テーブル定義
    - execution/                       # 実行（発注）関連の空ディレクトリ（拡張ポイント）
  - research/
    - __init__.py
    - factor_research.py              # ファクター計算（momentum/volatility/value）
    - feature_exploration.py          # IC / forward returns / summary
  - strategy/
    - __init__.py
    - feature_engineering.py          # features テーブルの構築
    - signal_generator.py             # final_score 計算と signals 生成
  - monitoring/                        # 監視・監査用（SQLite 連携など、拡張ポイント）

開発・拡張ガイド
----------------

- 研究用の factor 計算等は research/ 以下で提供され、strategy 層は research に依存しますが発注・execution 層には依存しない設計です。
- DuckDB はファイルベースで軽量に利用できます。テーブル定義は schema.py に集約されているため、スキーマ変更時はここを編集してください。
- news_collector.fetch_rss / save_raw_news はテスト容易性のため個別にモックできます（_urlopen 等を差し替え可能）。
- 監査テーブル設計は audit.py にまとまっており、order_request_id を冪等キーとして発注連携を実装できます。

ライセンス
---------

（ここにプロジェクトのライセンス情報を記載してください）

問い合わせ / 貢献
-----------------

バグ報告や機能要望は Issue を開いてください。
プルリクエストは歓迎します。コードスタイル・テストを付与するとマージがスムーズです。

以上。必要あれば README に具体的な .env.example、requirements.txt、実行スクリプト例（cron / systemd unit / GitHub Actions）を追加します。どのフォーマットがよいか教えてください。