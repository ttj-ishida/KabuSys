# KabuSys — 日本株自動売買プラットフォーム（README）

概要
----
KabuSys は日本株のデータ収集・品質管理・ETL を行う基盤ライブラリです。J-Quants API から株価・財務・カレンダー情報を取得して DuckDB に保存し、RSS からニュース収集を行い、監査・発注レイヤー用のスキーマや品質チェック機能を備えています。自動売買（strategy / execution）レイヤーの基盤を提供することを目的としています。

主な設計方針:
- API レート制御とリトライ（指数バックオフ、401 時のトークン自動リフレッシュ）
- データ取得時の look-ahead bias 回避のため fetched_at を記録
- DuckDB へ冪等（idempotent）に保存（ON CONFLICT DO UPDATE / DO NOTHING）
- RSS ニュース収集における SSRF 対策、XML 攻撃対策、トラッキングパラメータ除去
- データ品質チェックを組み込んだ ETL パイプライン

機能一覧
--------
- 設定管理
  - .env / .env.local を自動読み込み（プロジェクトルート検出）
  - 必須環境変数取得（例: JQUANTS_REFRESH_TOKEN）
  - 環境（development / paper_trading / live）・ログレベル検証
- J-Quants API クライアント（kabusys.data.jquants_client）
  - 日次株価（OHLCV）、四半期財務データ、JPX カレンダー取得
  - レートリミッタ、リトライ、401 自動リフレッシュ、ページネーション対応
  - DuckDB への保存関数（raw_prices / raw_financials / market_calendar）
- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得、HTML や URL の前処理、記事IDの正規化（SHA-256）
  - SSRF 対策、gzip 制限、defusedxml による安全な XML パース
  - raw_news / news_symbols への冪等保存
- スキーマ定義と初期化（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層のテーブルを定義
  - インデックス作成、init_schema で初期化
- ETL パイプライン（kabusys.data.pipeline）
  - 差分取得（最終取得日ベース）、バックフィル、品質チェック統合
  - run_daily_etl によりカレンダー→価格→財務→品質チェックを実行
- カレンダー管理（kabusys.data.calendar_management）
  - 営業日判定、前後営業日の取得、カレンダー更新ジョブ
- 監査ログ（kabusys.data.audit）
  - signal / order_request / execution の監査用スキーマ
  - 監査DB 初期化（UTC タイムゾーン固定）
- 品質チェック（kabusys.data.quality）
  - 欠損、重複、スパイク（前日比）、日付不整合（未来日・非営業日）検出
  - QualityIssue により検出結果を返却

セットアップ手順
--------------
前提
- Python 3.10 以上（型注釈に | None などを使用）
- インターネット接続（J-Quants / RSS 取得用）
- DuckDB を使うためディスク書き込み権限

1. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージのインストール
   - 例（最低限）:
     - pip install duckdb defusedxml
   - 実際のプロジェクトでは requirements.txt / pyproject.toml を用意して管理してください。

3. 環境変数の準備
   - プロジェクトルート（.git または pyproject.toml が存在するディレクトリ）に .env または .env.local を置くと自動で読み込まれます。
   - 自動読み込みを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

   必要な（または利用される）環境変数例:
   - JQUANTS_REFRESH_TOKEN (必須): J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD (必須): kabuステーション API 用パスワード
   - KABU_API_BASE_URL (任意): デフォルト http://localhost:18080/kabusapi
   - SLACK_BOT_TOKEN (必須): Slack 通知用
   - SLACK_CHANNEL_ID (必須): Slack チャネル ID
   - DUCKDB_PATH (任意): 例 data/kabusys.duckdb（デフォルト）
   - SQLITE_PATH (任意): 監視 DB など（デフォルト data/monitoring.db）
   - KABUSYS_ENV (任意): development | paper_trading | live（デフォルト development）
   - LOG_LEVEL (任意): DEBUG | INFO | WARNING | ERROR | CRITICAL

   .env の行の例:
   JQUANTS_REFRESH_TOKEN=your_refresh_token_here
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development

使い方（主要な API / コマンド例）
--------------------------------

以下は Python REPL / スクリプトからの利用例です。

- DuckDB スキーマ初期化
  from kabusys.data.schema import init_schema
  from kabusys.config import settings
  conn = init_schema(settings.duckdb_path)
  # またはメモリ DB:
  # conn = init_schema(":memory:")

- 日次 ETL 実行
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn)  # target_date を指定しなければ本日が対象
  print(result.to_dict())

- ニュース収集（RSS 取得 & 保存）
  from kabusys.data.news_collector import run_news_collection
  # known_codes があれば銘柄抽出して news_symbols へ紐付け可能
  known_codes = {"7203", "6758", "9984"}  # 例
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)  # {source_name: saved_count, ...}

- カレンダー更新ジョブ（夜間バッチ想定）
  from kabusys.data.calendar_management import calendar_update_job
  saved = calendar_update_job(conn)
  print(f"saved={saved}")

- 監査ログスキーマの初期化（監査専用 DB）
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.duckdb")

- 品質チェックの個別実行
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn)
  for i in issues:
      print(i)

設計上の注意 / 動作上のポイント
--------------------------------
- .env 自動読み込みはプロジェクトルート（.git / pyproject.toml）を基準に行います。テストなどで無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- J-Quants クライアントは 120 req/min のレート制御を実装しています。短時間で大量リクエストを行うと待ち時間が発生します。
- fetch_* 関数はページネーションを内部で処理します（pagination_key）。
- save_* 関数は冪等性を意識しており、既存レコードは更新、重複は排除します。
- news_collector は SSRF や XML の脆弱性対策（defusedxml、ホストのプライベートチェック、受信サイズ制限等）を実装しています。
- init_audit_schema はデフォルトで TimeZone を UTC に固定します（UTC タイムスタンプ運用推奨）。
- DuckDB のパフォーマンス上、まとめて挿入する際にチャンク化を行っています（news_collector 等）。

ディレクトリ構成（抜粋）
-----------------------
リポジトリの主要ファイルとモジュール構成（src/kabusys 以下）:

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / 設定読み込み
  - data/
    - __init__.py
    - jquants_client.py          — J-Quants API クライアント (fetch/save)
    - news_collector.py          — RSS ニュース収集・保存
    - schema.py                  — DuckDB スキーマ定義・init_schema
    - pipeline.py                — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py     — カレンダー更新・営業日判定
    - audit.py                   — 監査ログスキーマの定義・初期化
    - quality.py                 — データ品質チェック
  - strategy/
    - __init__.py                — 戦略層（拡張ポイント）
  - execution/
    - __init__.py                — 発注/ブローカー連携（拡張ポイント）
  - monitoring/
    - __init__.py                — 監視関連（拡張ポイント）

トラブルシューティング（よくある問題）
------------------------------------
- DuckDB のファイルが書き込めない / ディレクトリがない:
  - DUCKDB_PATH の親ディレクトリを作成してください。init_schema は親ディレクトリを自動作成しますが、権限がない場合は失敗します。
- J-Quants API の認証エラー:
  - JQUANTS_REFRESH_TOKEN が正しく設定されているか確認してください。get_id_token はリフレッシュトークンから idToken を取得します。
- RSS 取得でエラーが出る:
  - URL のスキームが http/https か、ホストがプライベートネットワークになっていないか確認してください。news_collector は SSRF 防止のためプライベートアドレスを拒否します。

拡張ポイント
------------
- strategy / execution / monitoring パッケージは最小限の雛形を提供しています。ここに戦略ロジック、発注ロジック、監視ジョブを実装してシステムを完成させてください。
- Slack 通知や外部モニタリングは config の Slack 設定を活用して実装できます。

ライセンス・貢献
----------------
- 本リポジトリのライセンスはリポジトリ内の LICENSE ファイルに従ってください（ここには明記されていません）。
- バグ報告や機能追加は Pull Request / Issue を通じて歓迎します。

最後に
------
この README はコードベース（src/kabusys）に基づいて作成しています。実際に使用する際は依存パッケージの固定や CI 設定、運用用のドキュメント（デプロイ手順、ロギング/監視ルール、復旧手順）を整備してください。質問や追加のドキュメントが必要であれば教えてください。