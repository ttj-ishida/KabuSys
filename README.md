# KabuSys

KabuSys は日本株の自動売買・データ基盤を構築するための Python ライブラリ群です。J-Quants や kabuステーション 等の外部 API から株価・財務・カレンダー・ニュース等を取得し、DuckDB に整形・保存、品質チェックや ETL パイプライン、監査ログ（発注〜約定トレーサビリティ）を提供します。

主な設計方針：
- API レート制御とリトライ（J-Quants のレート制限順守）
- データの冪等性（INSERT ... ON CONFLICT）
- Look-ahead bias を防ぐための fetched_at / UTC タイムスタンプ記録
- セキュリティ対策（XML Bomb/SSRF 対策等）
- DuckDB を用いた軽量・高速なローカルデータベース設計

対応 Python バージョンの目安：Python 3.10 以上（型アノテーションに | を使用）。

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（主要な API と使用例）
- ディレクトリ構成
- 環境変数一覧（必須/任意）
- 開発メモ（設計上の注意点）

---

プロジェクト概要
- 日本株のデータ収集・ETL・品質チェック・監査ログ・ニュース収集をまとめて扱えるライブラリ。
- データ保存は DuckDB を中心に設計され、ETL は差分更新・バックフィルを考慮。
- 発注・約定の監査ログ（監査テーブル群）を別途初期化可能。

---

機能一覧
- J-Quants API クライアント（株価日足、財務、マーケットカレンダー取得）
  - レートリミッタ、リトライ、ID トークン自動リフレッシュ
- DuckDB スキーマ定義と初期化（raw / processed / feature / execution / audit 層）
- ETL パイプライン（run_daily_etl）
  - 市場カレンダー、株価、財務データの差分取得・保存・品質チェック
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- ニュース収集（RSS フィード取得、前処理、DuckDB 保存、銘柄抽出）
  - XML および SSRF 対策、受信サイズ制限、記事 ID は正規化 URL の SHA-256 ハッシュ
- カレンダー管理ユーティリティ（営業日判定、前後営業日の取得、夜間更新ジョブ）
- 監査ログ（signal / order_request / executions）テーブルの初期化
- 環境変数 / .env の自動ロード機能（プロジェクトルートを探索して .env / .env.local を読み込み）

---

セットアップ手順（ローカル開発向け）

前提:
- Python 3.10+
- pip

1. リポジトリをクローン（省略）

2. 依存パッケージをインストール
   - 最低限必要なライブラリ:
     - duckdb
     - defusedxml
   例:
     pip install duckdb defusedxml

   （プロジェクトに pyproject.toml / requirements.txt がある場合はそちらに従う）

3. パッケージをインストール（編集可能モード）
     pip install -e .

4. 環境変数の設定
   - プロジェクトルートに .env を作成するか、OS 環境変数に設定します。
   - 自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

環境変数（主要なもの）

必須:
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（jquants_client で使用）
- KABU_API_PASSWORD     : kabuステーション API のパスワード（発注関連）
- SLACK_BOT_TOKEN       : Slack 通知に使用する Bot トークン
- SLACK_CHANNEL_ID      : Slack チャンネル ID

任意／デフォルトあり:
- KABUSYS_ENV           : development | paper_trading | live （デフォルト: development）
- LOG_LEVEL             : DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
- KABUS_API_BASE_URL    : kabu API のベース URL（デフォルトは http://localhost:18080/kabusapi）
- DUCKDB_PATH           : DuckDB の DB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH           : 監視系等での SQLite パス（デフォルト: data/monitoring.db）

注意: 設定値は kabusys.config.settings 経由でアクセスできます。必須変数が未設定の場合は ValueError が発生します。

---

使い方（主要な例）

1) DuckDB スキーマの初期化
- Python コンソールで:
  from kabusys.data import schema
  conn = schema.init_schema("data/kabusys.duckdb")
  # または ":memory:" を指定してインメモリ DB

2) 日次 ETL の実行（株価 / 財務 / カレンダー）
  from kabusys.data import pipeline
  # conn は上で初期化した DuckDB 接続
  result = pipeline.run_daily_etl(conn)
  print(result.to_dict())  # ETLResult の要約

  run_daily_etl は内部で:
  - カレンダー ETL（lookahead を含む）
  - 株価 ETL（差分 + backfill）
  - 財務 ETL（差分 + backfill）
  - オプションで品質チェック（quality.run_all_checks）

3) ニュース収集の実行
  from kabusys.data import news_collector
  # conn は DuckDB 接続
  results = news_collector.run_news_collection(conn, sources=None, known_codes={"7203","6758"})
  # sources を None にするとデフォルト RSS を使用
  # 戻り値は各 source ごとの新規保存件数の辞書

4) J-Quants クライアントの直接利用
  from kabusys.data import jquants_client as jq
  # トークンは settings.jquants_refresh_token から取得される
  quotes = jq.fetch_daily_quotes(code="7203", date_from=date(2024,1,1), date_to=date(2024,1,31))
  # 取得後、jq.save_daily_quotes(conn, quotes) で保存

5) 監査スキーマの初期化（発注・約定トレース用）
  from kabusys.data import audit
  # 既存の conn に audit テーブルを追加
  audit.init_audit_schema(conn, transactional=True)
  # もしくは専用 DB を生成
  audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")

---

ディレクトリ構成（抜粋）
- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数・設定管理（.env 自動ロード機能）
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API クライアント（取得・保存用）
    - news_collector.py            — RSS ニュース収集・保存・銘柄抽出
    - schema.py                    — DuckDB スキーマ定義 & init_schema / get_connection
    - pipeline.py                  — ETL パイプライン（差分更新・品質チェック）
    - calendar_management.py       — カレンダー管理・営業日ユーティリティ
    - audit.py                     — 監査ログ（signal / order_request / executions）初期化
    - quality.py                   — 品質チェック（欠損・重複・スパイク・日付不整合）
  - strategy/
    - __init__.py                  — 戦略層（空のパッケージ、拡張想定）
  - execution/
    - __init__.py                  — 発注実行層（空のパッケージ、拡張想定）
  - monitoring/
    - __init__.py                  — 監視・メトリクス（空のパッケージ、拡張想定）

---

開発メモ / 設計上の注意点
- J-Quants クライアント:
  - レート制限 120 req/min を固定間隔スロットリングで実装
  - 408/429/5xx 系は指数バックオフでリトライ、401 はトークン自動リフレッシュを試行
  - ページネーション対応（pagination_key を継続して取得）
- ニュース収集:
  - XML のパースは defusedxml を使用して脆弱性を低減
  - SSRF 対策としてスキーム検証・リダイレクト時のホスト検査・プライベート IP 拒否
  - レスポンスサイズ上限（デフォルト 10MB）でメモリ DoS を防止
  - 記事 ID は URL を正規化して SHA-256 の先頭 32 文字を使用（冪等性）
- DuckDB スキーマ:
  - Raw / Processed / Feature / Execution / Audit の 3 層＋監査
  - 多数のインデックスを定義して一般的なクエリパターンに対応
- ETL:
  - 差分更新・バックフィル（デフォルト 3 日）で API の後出し修正を吸収
  - 品質チェックは全チェックを実行して問題を集約（Fail-Fast ではない）
- 環境変数の自動ロード:
  - プロジェクトルート（.git または pyproject.toml の存在）を基準に .env / .env.local を読み込み
  - OS 環境変数 > .env.local > .env の優先順位
  - 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

---

トラブルシューティング（よくある事例）
- ValueError: 環境変数が未設定
  - 必須 env の設定を確認してください（JQUANTS_REFRESH_TOKEN 等）。
- 401 Unauthorized 連続
  - リフレッシュトークンが無効の可能性があります。settings.jquants_refresh_token を確認。
- DuckDB ファイルパスの権限エラー
  - DUCKDB_PATH の親ディレクトリが存在するか、書き込み権限を確認してください。init_schema は親ディレクトリを自動作成しますが、パスに権限がないと失敗します。

---

ライセンス / 貢献
- この README に記載のほか、実際のリポジトリ内の LICENSE を参照してください。
- バグ報告・機能要望は Issue を通じてお願いします。

---

以上。必要であれば README に具体的な .env.example のサンプルや、より詳細な CLI／運用手順（cron による夜間 ETL、監視アラート設定等）を追加します。どのセクションを詳しく書き起こしますか？