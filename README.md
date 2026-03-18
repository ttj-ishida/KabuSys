KabuSys
======

概要
----
KabuSys は日本株の自動売買・データ基盤向けライブラリです。  
J-Quants API 等から市場データ（株価・財務・マーケットカレンダー）や RSS ニュースを収集し、DuckDB ベースのデータレイクに保存・品質チェック・監査ログ管理を行うための ETL・ユーティリティ群を提供します。  
設計上の特徴として、API レート制御・リトライ・冪等性（ON CONFLICT）・Look‑ahead バイアス防止（UTC fetched_at 記録）などを重視しています。

主な機能
--------
- J-Quants API クライアント（data/jquants_client.py）
  - 株価日足（OHLCV）、財務（四半期 BS/PL）、JPX カレンダーを取得
  - レートリミット（120 req/min）対応、リトライ、トークン自動リフレッシュ
  - DuckDB へ冪等保存する save_* 関数を提供
- ニュース収集（data/news_collector.py）
  - RSS フィード取得、テキスト前処理、記事IDの冪等生成（URL 正規化 + SHA‑256）
  - SSRF 対策、gzip / サイズ制限、defusedxml を使った安全な XML パース
  - raw_news / news_symbols テーブルへの一括保存（トランザクション、INSERT ... RETURNING）
- データスキーマ管理（data/schema.py）
  - Raw / Processed / Feature / Execution 層を想定した DuckDB スキーマ定義
  - init_schema(db_path) でスキーマを冪等に作成
- ETL パイプライン（data/pipeline.py）
  - 日次 ETL（run_daily_etl）: カレンダー → 株価 → 財務 → 品質チェック の流れ
  - 差分取得（最終取得日からの差分 + backfill）により API 負荷を低減
  - 品質チェック呼び出しとエラー集約（品質問題は報告のみで継続処理）
- カレンダー管理（data/calendar_management.py）
  - 営業日判定、前後営業日取得、期間内営業日リスト、夜間カレンダー更新ジョブ
  - DB データの有無に応じた曜日フォールバック
- 品質チェック（data/quality.py）
  - 欠損（OHLC 欠損）、スパイク（前日比）、重複、日付不整合（未来日・非営業日）等
  - QualityIssue 型で問題を集約して返す
- 監査ログ（data/audit.py）
  - signal → order_request → execution を UUID でトレース可能にする監査テーブル群
  - init_audit_db(db_path) で専用 DB を初期化

セットアップ
----------
1. リポジトリをクローン／プロジェクトルートへ移動
   - _find_project_root() は .git または pyproject.toml を探して .env 自動読み込みの基準とします。

2. 依存パッケージ（推奨）
   - Python 3.9+
   - duckdb
   - defusedxml
   - （その他：標準ライブラリの urllib 等を利用）

   例:
   pip install duckdb defusedxml

   （プロジェクトで requirements.txt や pyproject.toml があればそちらを使用してください。）

3. 環境変数の設定
   - .env または OS 環境変数を利用できます。自動ロードの優先順は:
     OS 環境変数 > .env.local > .env
   - 自動ロードを無効化する場合:
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

4. 必要な環境変数（config.Settings 参照）
   - JQUANTS_REFRESH_TOKEN (必須)
   - KABU_API_PASSWORD (必須)
   - KABU_API_BASE_URL (任意, デフォルト: http://localhost:18080/kabusapi)
   - SLACK_BOT_TOKEN (必須)
   - SLACK_CHANNEL_ID (必須)
   - DUCKDB_PATH (任意, デフォルト: data/kabusys.duckdb)
   - SQLITE_PATH (任意, デフォルト: data/monitoring.db)
   - KABUSYS_ENV (任意: development | paper_trading | live、デフォルト: development)
   - LOG_LEVEL (任意: DEBUG|INFO|WARNING|ERROR|CRITICAL、デフォルト: INFO)

   .env の例（テンプレート）
   JQUANTS_REFRESH_TOKEN=your_refresh_token
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO

使い方（Python API 例）
-------------------
- スキーマの初期化と ETL の実行（最小例）
  from kabusys.data import schema, pipeline
  conn = schema.init_schema("data/kabusys.duckdb")
  result = pipeline.run_daily_etl(conn)
  print(result.to_dict())

- ニュース収集ジョブ（RSS を取得して保存）
  from kabusys.data import schema, news_collector
  conn = schema.init_schema("data/kabusys.duckdb")
  # known_codes は銘柄抽出に使用する有効コードの集合（任意）
  known_codes = {"7203", "6758"}
  res = news_collector.run_news_collection(conn, known_codes=known_codes)
  print(res)  # {source_name: new_saved_count}

- J-Quants トークン取得（明示的に使用する場合）
  from kabusys.data.jquants_client import get_id_token
  token = get_id_token()  # Settings からリフレッシュトークンを利用して取得

- 監査DB 初期化（監査専用 DB を作る場合）
  from kabusys.data import audit
  audit_conn = audit.init_audit_db("data/audit.duckdb")

設計上のポイント（開発者向けメモ）
--------------------------------
- API 呼び出しは _RateLimiter による固定間隔スロットリングで 120 req/min を守ります。
- リトライは指数バックオフ（最大3回）。408/429/5xx に対して再試行。
- 401 Unauthorized を受けた場合は自動でリフレッシュトークンを用いて ID トークンを更新し、1 回だけ再試行します。
- データの fetched_at は UTC で記録して Look‑ahead Bias を防止します。
- DuckDB への保存は冪等（ON CONFLICT DO UPDATE / DO NOTHING）を採用。
- RSS 処理は SSRF 対策（スキーム検証、プライベート IP 拒否、リダイレクト検査）、gzipサイズ検査、defusedxml による安全パースを行います。

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py             : パッケージ定義（version 等）
- config.py               : 環境変数・設定管理（Settings）
- data/
  - __init__.py
  - jquants_client.py     : J-Quants API クライアント（取得 + 保存ユーティリティ）
  - news_collector.py     : RSS ニュース収集・前処理・DB 保存
  - schema.py             : DuckDB スキーマ定義 & init_schema / get_connection
  - pipeline.py           : ETL パイプライン（run_daily_etl等）
  - calendar_management.py: 市場カレンダーの管理・営業日ユーティリティ
  - audit.py              : 監査ログ用テーブル初期化 / init_audit_db
  - quality.py            : データ品質チェック（欠損・スパイク・重複・日付不整合）
- strategy/
  - __init__.py           : 戦略層用プレースホルダ（戦略実装を置く）
- execution/
  - __init__.py           : 発注・約定処理プレースホルダ
- monitoring/
  - __init__.py           : 監視・メトリクス用プレースホルダ

注意事項
--------
- DuckDB のファイルパス（デフォルト data/kabusys.duckdb）は Settings.duckdb_path で変更可能。
- self-contained な CLI は含まれていません。アプリケーション単位で上記 API を呼び出すスクリプトやジョブランナーを実装してください。
- .env 自動読み込みはプロジェクトルート（.git or pyproject.toml を基準）を探索します。CI やテストでは KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して自動読み込みを抑制可能です。
- 実稼働（live）環境では KABUSYS_ENV=live を設定してログレベルや動作を適切に制御してください。

ライセンス / 貢献
----------------
（ライセンス情報や貢献ルールがある場合はここに追記してください）

以上。README に不明点や追加したい Usage（例えば CLI や systemd ジョブの例）があれば教えてください。必要であれば英語版も作成します。