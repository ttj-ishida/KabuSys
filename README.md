# KabuSys

日本株向けの自動売買基盤（データ収集・ETL・監査・実行基盤の骨格実装）

## プロジェクト概要

KabuSys は日本株のデータプラットフォームと自動売買ワークフローの基盤となるライブラリ群です。  
主に以下を提供します。

- J-Quants API からの時系列データ・財務データ・市場カレンダーの取得と耐障害性の高い HTTP / リトライ処理
- RSS ベースのニュース収集と記事の前処理・SSRF 対策・トラッキングパラメータ除去
- DuckDB を利用したスキーマ定義・初期化・接続ヘルパー
- ETL パイプライン（差分取得、バックフィル、品質チェックの統合）
- マーケットカレンダー管理（営業日判定、前後営業日の列挙）
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 監査ログ（シグナル→発注→約定のトレーサビリティ用スキーマ実装）

設計方針としては、冪等性、トレーサビリティ、外部 API のレート制御とリトライ、SSRF/XML攻撃対策などに重点を置いています。

## 主な機能一覧

- 環境設定管理（.env / OS 環境変数の自動読み込み、必須キー検証）
- J-Quants API クライアント
  - 株価日足（OHLCV）、財務データ、マーケットカレンダーの取得
  - ページネーション対応、レートリミット（120 req/min）制御、再試行・トークン自動更新
  - DuckDB への冪等保存（ON CONFLICT ... DO UPDATE）
- ニュース収集モジュール
  - RSS 取得、XML の安全パース（defusedxml）、URL 正規化、記事IDは SHA-256 ハッシュ
  - SSRF 対策（スキーム検証、プライベートホスト拒否、リダイレクト検査）
  - DuckDB へのバルク挿入（INSERT ... RETURNING）
- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution / Audit レイヤの DDL
  - インデックス定義、init_schema 関数で一括作成
- ETL パイプライン
  - run_daily_etl: カレンダー → 株価 → 財務 → 品質チェックの統合ワークフロー
  - 差分取得（最終取得日から必要部分のみ取得）とバックフィル
- マーケットカレンダー管理
  - 営業日判定、前後営業日取得、バッチ更新ジョブ
- 品質チェック
  - 欠損・スパイク（前日比）・重複・日付不整合の検出
  - QualityIssue オブジェクトで検出結果を集約
- 監査ログスキーマ
  - signal_events / order_requests / executions 等、発注フローの完全トレースを可能にするスキーマ群

## セットアップ手順

前提:
- Python 3.10 以上（組み込みの型注釈に `|` を使用）
- Git（プロジェクトルート検出のために .git または pyproject.toml があることを想定）

1. リポジトリをクローン／配置
   git clone ... またはソースを取得

2. 仮想環境作成（推奨）
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows

3. 必要パッケージをインストール
   pip install duckdb defusedxml
   （本リポジトリに requirements.txt がある場合は pip install -r requirements.txt）

4. 環境変数の準備
   プロジェクトルート（.git または pyproject.toml を含むディレクトリ）に `.env` として必要なキーを置くか、OS 環境変数で設定してください。自動読み込みはデフォルトで有効です（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

   必須環境変数（Settings が要求するもの）
   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD     : kabu API（kabuステーション）パスワード
   - SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン
   - SLACK_CHANNEL_ID      : Slack 送信先チャンネル ID

   オプション（デフォルトあり）
   - KABUSYS_ENV (development / paper_trading / live) 既定: development
   - LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL) 既定: INFO
   - DUCKDB_PATH (DuckDB ファイル: default "data/kabusys.duckdb")
   - SQLITE_PATH (監視 DB: default "data/monitoring.db")
   - KABUSYS_DISABLE_AUTO_ENV_LOAD = 1 で自動.envロードを無効化

   .env の例:
   JQUANTS_REFRESH_TOKEN=your_refresh_token
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO

5. DuckDB スキーマ初期化
   Python REPL またはスクリプトで以下を実行して初期スキーマを作成します（`db_path` は `:memory:` でインメモリ DB を使えます）。

   from kabusys.data import schema
   conn = schema.init_schema("data/kabusys.duckdb")

## 使い方（代表的な例）

- J-Quants からの株価取得（低レベル）
  from kabusys.data import jquants_client as jq
  token = jq.get_id_token()  # settings が取得する Refresh Token を利用
  records = jq.fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))

- DuckDB に保存（冪等）
  from kabusys.data import schema
  conn = schema.get_connection("data/kabusys.duckdb")
  saved = jq.save_daily_quotes(conn, records)

- ニュース収集
  from kabusys.data import news_collector as nc
  articles = nc.fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
  # DuckDB に保存
  from kabusys.data import schema
  conn = schema.get_connection("data/kabusys.duckdb")
  new_ids = nc.save_raw_news(conn, articles)

- 日次 ETL を実行（推奨の高レベル API）
  from kabusys.data import schema, pipeline
  conn = schema.get_connection("data/kabusys.duckdb")
  result = pipeline.run_daily_etl(conn)
  print(result.to_dict())

  run_daily_etl は以下を行います:
  1) カレンダー ETL（先読み）
  2) 株価差分 ETL（最終取得日を元に差分／バックフィル）
  3) 財務差分 ETL
  4) 品質チェック（オプション）

- カレンダー関連ユーティリティ
  from kabusys.data import calendar_management as cm
  next_day = cm.next_trading_day(conn, date(2024,3,1))
  is_trading = cm.is_trading_day(conn, date.today())

- 品質チェックの実行
  from kabusys.data import quality
  issues = quality.run_all_checks(conn)
  for i in issues:
      print(i.check_name, i.severity, i.detail)

- 監査スキーマ初期化（監査専用 DB）
  from kabusys.data import audit
  audit_conn = audit.init_audit_db("data/audit.duckdb")

注意点:
- J-Quants API のレート制限（120 req/min）やリトライ方針は jquants_client に組み込まれています。
- news_collector は SSRF や XML 攻撃対策（defusedxml）を施しています。
- 多くの保存処理は ON CONFLICT / RETURNING を用いて冪等性と正確な新規件数取得を実現しています。

## 環境変数の詳細（Settings）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu API 用パスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視用 sqlite ファイルパス（デフォルト data/monitoring.db）
- KABUSYS_ENV — 実行環境（development / paper_trading / live）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると .env の自動読み込みを無効化

自動読み込みの挙動:
- プロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を起点に `.env` → `.env.local` の順で読み込みます。
- OS 環境変数が既にあるキーは上書きされません（`.env.local` は override=True だが OS 環境変数は保護されます）。
- 自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

## 開発・テストのヒント

- 単体テストや CI では J-Quants の呼び出しをモックし、DB は ":memory:" を使うと簡便です。
- news_collector._urlopen をモックしてネットワーク依存を切り離せます。
- audit.init_audit_schema には transactional フラグがあり、ネストトランザクションの扱いに注意してください（DuckDB はネストトランザクション非対応）。

## ディレクトリ構成

（主なファイル/モジュールのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py           — J-Quants API クライアント（取得・保存）
    - news_collector.py          — RSS ニュース収集・保存
    - schema.py                  — DuckDB スキーマ定義 / init_schema
    - pipeline.py                — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py     — マーケットカレンダー管理
    - audit.py                   — 監査ログスキーマの初期化
    - quality.py                 — データ品質チェック
  - strategy/
    - __init__.py                — 戦略層のプレースホルダ（将来的な実装領域）
  - execution/
    - __init__.py                — 発注・約定関連（将来的な実装領域）
  - monitoring/
    - __init__.py                — 監視・メトリクス関連（将来的な実装領域）

（プロジェクトルートに README.md、pyproject.toml / setup.cfg 等を置くことを想定）

## ライセンス・注意事項

- 本リポジトリはサンプル実装／基盤コードとして設計されています。実運用で用いる場合は以下に注意してください。
  - 証券会社 API（kabu など）へ接続しての自動発注は重大なリスクを伴います。発注ロジック・リスク管理は別途厳密に実装・テストしてください。
  - API キー・トークン等の秘密情報は適切に管理し、レポジトリに直接コミットしないでください。
  - 時刻・タイムゾーンの扱い、トレーサビリティ要件は運用ポリシーに合わせて確認してください。

---

ご要望があれば、README に以下を追加できます:
- 具体的な CLI/cron ジョブ例（systemd / cron / Docker Compose）
- テスト例（pytest を用いたユニットテストの書き方）
- `pyproject.toml` / `setup.cfg` の推奨設定例
- CI（GitHub Actions）での ETL 実行サンプル

必要な追加項目があれば教えてください。