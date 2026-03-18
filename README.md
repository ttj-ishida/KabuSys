KabuSys
======

日本株向けの自動売買・データ基盤ライブラリ（プロトタイプ）。  
J-Quants API や RSS を使ったデータ収集、DuckDB によるスキーマ管理、ETL パイプライン、データ品質チェックや監査ログなど、アルゴリズム取引の基盤機能を提供します。

主な設計方針
- データ取得は冪等（ON CONFLICT を使用）で安全に保存
- API レート制限・リトライ・トークンリフレッシュ対応
- Look-ahead bias を防ぐため fetched_at 等のトレーサビリティを保持
- SSRF / XML Bomb 等の外部入力に対する安全対策（ニュース収集）
- DuckDB を中心としたシンプルなローカルデータベース設計

機能一覧
- 環境変数 / .env 管理（kabusys.config）
  - プロジェクトルートの .env / .env.local を自動読み込み（無効化可）
  - 必須環境変数の明示的取得
- J-Quants API クライアント（kabusys.data.jquants_client）
  - 株価日足（OHLCV）、四半期財務データ、JPX マーケットカレンダーの取得
  - レートリミッタ、再試行（指数バックオフ）、401 時の自動トークンリフレッシュ
  - DuckDB への安全な保存ユーティリティ（save_*）
- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得（gzip 対応）、XML パースの安全化（defusedxml）
  - URL 正規化・トラッキングパラメータ除去・記事ID のハッシュ化（冪等）
  - SSRF 対策（スキーム検証・プライベートIP検査・リダイレクト検査）
  - DuckDB へのバルク保存（INSERT ... RETURNING）と銘柄抽出
- DuckDB スキーマ定義・初期化（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層のテーブル群
  - インデックスや制約を含む DDL の一括実行（init_schema）
- ETL パイプライン（kabusys.data.pipeline）
  - 日次 ETL（市場カレンダー → 株価 → 財務 → 品質チェック）
  - 差分取得・バックフィル設定・品質チェック統合
- カレンダー管理（kabusys.data.calendar_management）
  - 営業日判定・次/前営業日取得・期間の営業日リスト取得
  - 夜間バッチ（calendar_update_job）
- データ品質チェック（kabusys.data.quality）
  - 欠損、スパイク、重複、日付不整合などのチェック
  - QualityIssue オブジェクトで詳細を返す
- 監査ログ（kabusys.data.audit）
  - signal / order_request / execution の監査テーブルと初期化（init_audit_schema / init_audit_db）
- 将来的な拡張ポイント
  - strategy, execution, monitoring パッケージ（プレースホルダ）

必要要件
- Python 3.10 以上
- 依存パッケージ（例）
  - duckdb
  - defusedxml
- ネットワーク接続（J-Quants API、RSS フィード）

セットアップ手順（ローカル開発）
1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存ライブラリをインストール
   - pip install duckdb defusedxml

   （プロジェクトで pyproject.toml / requirements.txt があればそれに従ってください）

3. 環境変数を用意
   - プロジェクトルートに .env または .env.local を作成すると自動読み込みされます（kabusys.config がプロジェクトルートを検出した場合）。
   - 自動読み込みを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

必須環境変数（例）
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD     : kabu ステーション API のパスワード（必須）
- SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID      : Slack チャンネル ID（必須）

任意 / デフォルト
- KABU_API_BASE_URL     : kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH           : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH           : 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV           : "development" | "paper_trading" | "live"（デフォルト: development）
- LOG_LEVEL             : "DEBUG" | "INFO" | "WARNING" | "ERROR" | "CRITICAL"（デフォルト: INFO）

基本的な使い方（例）
- DuckDB スキーマ初期化
  - from kabusys.data import schema
    conn = schema.init_schema("data/kabusys.duckdb")

- 日次 ETL の実行
  - from kabusys.data.pipeline import run_daily_etl
    result = run_daily_etl(conn)
    print(result.to_dict())

  パラメータで target_date, id_token, run_quality_checks, backfill_days 等を指定可能。

- ニュース収集の実行（RSS から記事を収集して保存）
  - from kabusys.data.news_collector import run_news_collection
    results = run_news_collection(conn, sources=None, known_codes=set(["7203","6758"]))
    # results は {source_name: 新規保存件数}

- J-Quants トークンの直接取得（テスト等）
  - from kabusys.data.jquants_client import get_id_token
    token = get_id_token()

- 監査ログ用スキーマ初期化
  - from kabusys.data.audit import init_audit_db
    audit_conn = init_audit_db("data/kabusys_audit.duckdb")

注意点・運用上のヒント
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml があるディレクトリ）を基準に行います。配布後に別場所から呼ぶ場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して手動で環境設定してください。
- J-Quants API はレート制限（120 req/min）があります。jquants_client は内部でスロットリングと再試行を行いますが、運用時は過剰な並列化を避けてください。
- ニュース収集は外部 URL を開くため SSRF を避けるための多層防御（スキーム検査、プライベートIP拒否、リダイレクト検査、最大受信バイト上限）を実装しています。ただし社内運用時はさらにネットワークレベルで制限を行うと良いです。
- DuckDB ファイルのバックアップおよび排他制御（複数プロセスの同時書き込み）については運用ポリシーに従ってください。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                       # 環境変数・設定の取り扱い
  - data/
    - __init__.py
    - jquants_client.py              # J-Quants API クライアント（取得・保存）
    - news_collector.py             # RSS ニュース収集・保存処理
    - schema.py                     # DuckDB スキーマ定義・初期化
    - pipeline.py                   # ETL パイプライン（run_daily_etl 等）
    - calendar_management.py        # 市場カレンダー管理・営業日判定
    - audit.py                      # 監査ログスキーマ（signal/order/execution）
    - quality.py                    # データ品質チェック
  - strategy/
    - __init__.py                    # 戦略モジュール（拡張ポイント）
  - execution/
    - __init__.py                    # 発注/約定関連（拡張ポイント）
  - monitoring/
    - __init__.py                    # 監視機能（拡張ポイント）

拡張方法
- strategy / execution / monitoring パッケージに独自実装を追加して、signal 生成 → order_request 作成 → 発注実行 → 約定受信 のフローを組み立てます。
- ETL のカスタマイズは pipeline.run_daily_etl 内の引数や個別 run_* 関数を呼び出して組み合わせます。
- DuckDB スキーマを変更する場合は schema.py の DDL を更新し、init_schema を再実行してください（既存テーブルには影響しないためマイグレーションは別途検討が必要です）。

ライセンス / 責任
- 本リポジトリはサンプル・テンプレートとしての提供を想定しています。実運用に導入する場合は API 利用規約、証券会社のルール、テストおよびセキュリティ監査を十分に行ってください。

お問い合わせ
- 実装や利用に関する質問があれば、コード内の docstring を参照してください。README に載せてほしい追加項目やサンプルスクリプト等の要望があれば教えてください。