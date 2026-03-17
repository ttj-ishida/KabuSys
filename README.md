# KabuSys

日本株向けの自動売買基盤ライブラリ（骨組み）。データ収集（J-Quants・RSS）、ETL、スキーマ定義、データ品質チェック、監査ログなど、バックエンド側の共通処理を提供します。

主な想定用途:
- 市場データ / 財務データの定期収集と DuckDB 保存
- ニュース（RSS）収集と銘柄紐付け
- ETL パイプライン（差分更新・バックフィル・品質チェック）
- 監査ログ（シグナル→発注→約定のトレース）

バージョン: 0.1.0

---

## 機能一覧

- 環境変数/設定管理
  - .env / .env.local の自動読み込み（プロジェクトルート検出）
  - 必須設定の検証（Settings クラス）
  - KABUSYS_ENV / LOG_LEVEL のバリデーション

- J-Quants API クライアント（kabusys.data.jquants_client）
  - 日次株価（OHLCV）、財務四半期データ、JPX カレンダー取得
  - レート制限（120 req/min）および固定間隔スロットリング実装
  - リトライ（指数バックオフ、408/429/5xx）、401 時の自動トークンリフレッシュ
  - ページネーション対応、取得時刻（fetched_at）記録
  - DuckDB へ冪等的に保存（ON CONFLICT...DO UPDATE）

- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得・XML パース（defusedxml を使用）
  - URL 正規化（トラッキングパラメータ除去）、記事ID は SHA-256（先頭32文字）
  - SSRF 対策（スキーム検証、ホストのプライベートアドレス判定、リダイレクト検査）
  - レスポンスサイズ制限（デフォルト 10MB）、gzip 対応
  - DuckDB への冪等保存（INSERT ... RETURNING、トランザクション）

- データ品質チェック（kabusys.data.quality）
  - 欠損（OHLC 欠損）、重複（主キー重複）、スパイク（前日比閾値）、日付不整合（未来日付・非営業日）
  - QualityIssue オブジェクトで詳細を返す（severity: error|warning）

- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新（DB の最終取得日から必要分だけ取得）
  - backfill（日次の後出し修正吸収）
  - 市場カレンダーの先読み（デフォルト 90 日）
  - 品質チェック実行、結果を ETLResult で返却

- スキーマ定義 / 初期化（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層のテーブル DDL を提供
  - init_schema() で DuckDB を初期化

- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions などトレーサビリティ用テーブル
  - init_audit_schema() / init_audit_db() を提供

---

## 必要な環境変数

主に Settings で参照される環境変数:

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID

任意（デフォルトあり）:
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 動作環境（development, paper_trading, live。デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL。デフォルト: INFO）

自動ロード制御:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると、自動で .env/.env.local を読み込まなくなります。

.env の読み込み順序（優先度低→高）:
- .env → .env.local（.env.local が上書き）

例（.env）:
JQUANTS_REFRESH_TOKEN=your_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

---

## セットアップ手順

1. リポジトリをクローン（プロジェクトルートに pyproject.toml または .git があることを期待）:
   git clone <repo-url>

2. 開発用インストール（推奨: 仮想環境を作る）
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows

   pip install -e ".[dev]"  # もし pyproject が適切に設定されている場合
   ※ 必須パッケージの例: duckdb, defusedxml

   もしパッケージ化されていない場合は最低限:
   pip install duckdb defusedxml

3. 環境変数を設定
   - プロジェクトルートに .env を作成するか、環境変数を直接設定してください。
   - 自動読み込みを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

4. DuckDB スキーマ初期化（Python スクリプト、REPL、またはアプリ起動時に実行）
   from pathlib import Path
   import duckdb
   from kabusys.data import schema

   conn = schema.init_schema(Path("data/kabusys.duckdb"))
   # 監査テーブルを追加する場合:
   from kabusys.data import audit
   audit.init_audit_schema(conn)

---

## 使い方（基本的なコード例）

- 設定アクセス:
  from kabusys.config import settings
  token = settings.jquants_refresh_token
  is_live = settings.is_live

- DuckDB スキーマ初期化:
  from kabusys.data import schema
  conn = schema.init_schema("data/kabusys.duckdb")

- J-Quants から日次株価取得と保存:
  from kabusys.data import jquants_client as jq
  import duckdb

  conn = duckdb.connect("data/kabusys.duckdb")
  # id_token を明示的に取得することも可能（自動キャッシュあり）
  id_token = jq.get_id_token()
  records = jq.fetch_daily_quotes(id_token=id_token, date_from=date(2024,1,1), date_to=date(2024,3,31))
  saved = jq.save_daily_quotes(conn, records)

- RSS ニュース収集（例: デフォルトソースから収集して DB 保存、銘柄紐付け）:
  from kabusys.data import news_collector
  import duckdb

  conn = duckdb.connect("data/kabusys.duckdb")
  # known_codes は銘柄コードの集合（例: 既知上場コードリスト）
  results = news_collector.run_news_collection(conn, known_codes={"7203","6758"})

- 日次 ETL 実行（市場カレンダー → 株価 → 財務 → 品質チェック）:
  from kabusys.data import pipeline
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  result = pipeline.run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())

- 品質チェック単体実行:
  from kabusys.data import quality
  issues = quality.run_all_checks(conn, target_date=date.today())
  for i in issues:
      print(i.check_name, i.severity, i.detail)

---

## ディレクトリ構成

（主要ファイルのみ抜粋、実際はリポジトリに合わせてください）

src/
  kabusys/
    __init__.py
    config.py                         # 環境変数・設定管理
    data/
      __init__.py
      jquants_client.py               # J-Quants API クライアント（取得・保存）
      news_collector.py               # RSS ニュース収集・保存・銘柄抽出
      schema.py                       # DuckDB スキーマ定義と init_schema
      pipeline.py                     # ETL パイプライン
      audit.py                        # 監査ログ（signal/order/execution）
      quality.py                      # データ品質チェック
    strategy/
      __init__.py                      # 戦略関連モジュール（拡張ポイント）
    execution/
      __init__.py                      # 発注・ブローカー連携（拡張ポイント）
    monitoring/
      __init__.py                      # 監視・メトリクス関連（拡張ポイント）

---

## 設計上の注意点 / 実装上の特長

- レート制限とリトライ:
  J-Quants は 120 req/min の制限を想定。内部で固定間隔のレートリミッタとリトライ（指数バックオフ）を実装しています。401 の場合はトークン自動リフレッシュ後に一回再試行します。

- 冪等性:
  DuckDB への保存関数は ON CONFLICT ... DO UPDATE / DO NOTHING を使って冪等に設計されています。ETL は差分取得とバックフィルを組み合わせて運用される想定です。

- セキュリティ:
  RSS 取得では defusedxml を使った XML パース、SSRF 対策、受信サイズ制限（Gzip 解凍後も検査）などを組み込んでいます。

- テスト容易性:
  id_token の注入や _urlopen の差し替え（モック化）によりユニットテストが容易になるよう設計されています。

---

## よくある質問 / トラブルシューティング

- .env が読み込まれない:
  - プロジェクトルートが探せない（.git または pyproject.toml がない）と自動ロードはスキップされます。手動で環境変数を設定するか、KABUSYS_DISABLE_AUTO_ENV_LOAD を使って自動ロードを無効にしてから独自に読み込んでください。

- J-Quants で 401 が大量発生する:
  - リフレッシュトークンが無効化されている可能性があります。settings.jquants_refresh_token を確認し、jq.get_id_token() を手動で試してください。

- DuckDB のスキーマを変更したい:
  - schema.init_schema() は冪等なので既存テーブルは上書きしません。DDL を変更した場合はマイグレーションを検討してください（本ライブラリにはマイグレーション機能は含まれていません）。

---

README は以上です。必要に応じて「使い方」セクションのスクリプト例や .env.example を追加で作成できます。どの例が欲しいか（ETL バッチの cron 設定例、Slack 通知の使い方案内など）があれば教えてください。