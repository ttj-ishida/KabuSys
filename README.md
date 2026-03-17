# KabuSys

日本株向けの自動売買（データ収集・ETL・監査）ライブラリ / システムコンポーネント群です。  
J-Quants API や RSS フィードからデータを収集し、DuckDB に格納、品質チェックやマーケットカレンダー管理、監査ログ（発注 → 約定のトレーサビリティ）を提供します。

バージョン: 0.1.0

---

## 主な概要

- J-Quants API から株価（日足）、財務データ（四半期 BS/PL）、マーケットカレンダーを安全に取得して DuckDB に保存します。
- RSS フィードからニュース記事を収集し、テキスト前処理・銘柄抽出・DB保存を行います（ニュース収集は SSRF / XML 攻撃対策やサイズ制限あり）。
- ETL パイプライン（差分更新、バックフィル、品質チェック）を実装しています。
- 監査ログ（signal → order_request → executions）用スキーマ群を提供し、UUID による完全トレーサビリティを確保します。
- レート制限やリトライ（指数バックオフ）、IDトークン自動リフレッシュなどを備え、API 利用における堅牢性を重視しています。

---

## 機能一覧

- 環境設定管理
  - .env（および .env.local）自動ロード（OS 環境変数優先）。自動読み込みは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - 必須/任意の環境変数アクセスをラップした `kabusys.config.settings`。

- J-Quants クライアント（kabusys.data.jquants_client）
  - ID トークン取得（自動リフレッシュ対応）
  - 株価（daily_quotes）/ 財務（statements）/ カレンダー（trading_calendar）取得（ページネーション、レート制御、リトライ）
  - DuckDB への冪等保存関数（ON CONFLICT を利用）：raw_prices, raw_financials, market_calendar

- ニュース収集（kabusys.data.news_collector）
  - RSS 取得（gzip サポート、受信サイズ上限、SSRF 対策）
  - URL 正規化 / トラッキングパラメータ除去 / SHA-256 ベースの記事 ID
  - DuckDB へのバルク保存（INSERT ... RETURNING、トランザクションまとめ）
  - 銘柄コード抽出（4桁数値 + known_codes フィルタ）

- スキーマ管理（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層を含む DuckDB テーブル定義と初期化関数 `init_schema` / `get_connection`

- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新（最終取得日時ベース）、バックフィル、カレンダー先読み
  - 日次 ETL エントリ `run_daily_etl`（品質チェックオプションあり）

- カレンダー管理（kabusys.data.calendar_management）
  - 営業日判定 / 前後の営業日取得 / 期間内営業日取得
  - 夜間バッチ更新 `calendar_update_job`

- 品質チェック（kabusys.data.quality）
  - 欠損データ・スパイク（前日比）・重複・日付整合性チェック
  - 各チェックは QualityIssue のリストを返す（重大度に応じた扱いが可能）

- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions テーブルとインデックス
  - `init_audit_schema` / `init_audit_db` による初期化

---

## セットアップ手順（ローカル開発向け）

前提: Python 3.9+（型ヒントに Union | を使っているため 3.10 推奨）

1. リポジトリをクローンして venv を作成
   ```bash
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   ```

2. 依存パッケージのインストール（例）
   ```bash
   pip install duckdb defusedxml
   ```
   ※ プロジェクトに requirements.txt がある場合は `pip install -r requirements.txt` を使用してください。  
   追加で linters やテストツールがある場合は適宜インストールしてください。

3. 開発モードでインストール（任意）
   ```bash
   pip install -e .
   ```

4. 環境変数設定
   - プロジェクトルートに `.env` / `.env.local` を配置すると自動で読み込まれます（OS 環境変数が優先）。
   - 自動ロードを無効にしたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   主要な環境変数（必須）:
   - JQUANTS_REFRESH_TOKEN    -- J-Quants リフレッシュトークン（必須）
   - KABU_API_PASSWORD        -- kabuステーション（証券API）パスワード（必須）
   - SLACK_BOT_TOKEN          -- Slack 通知用 Bot トークン（必須）
   - SLACK_CHANNEL_ID         -- Slack チャンネル ID（必須）

   任意 / デフォルト値:
   - KABUSYS_ENV              -- development | paper_trading | live（デフォルト: development）
   - LOG_LEVEL                -- DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
   - KABU_API_BASE_URL        -- kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
   - DUCKDB_PATH              -- DuckDB のパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH              -- SQLite（監視DB）パス（デフォルト: data/monitoring.db）

   .env の例:
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development
   DUCKDB_PATH=data/kabusys.duckdb
   ```

---

## 基本的な使い方（コード例）

以下は Python スクリプトや REPL での基本操作例です。

- DuckDB スキーマ初期化
  ```python
  from kabusys.data import schema

  conn = schema.init_schema("data/kabusys.duckdb")
  # またはインメモリ:
  # conn = schema.init_schema(":memory:")
  ```

- 日次 ETL 実行（J-Quants から差分取得して保存・品質チェック）
  ```python
  from kabusys.data import pipeline
  from kabusys.data import schema
  from datetime import date

  conn = schema.get_connection("data/kabusys.duckdb")  # 既存 DB に接続
  result = pipeline.run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- ニュース収集ジョブ（既知銘柄セットを渡して銘柄紐付けを行う例）
  ```python
  from kabusys.data import news_collector
  from kabusys.data import schema

  conn = schema.get_connection("data/kabusys.duckdb")
  known_codes = {"7203", "6758", "9432"}  # 例: 有効な銘柄コードセット
  stats = news_collector.run_news_collection(conn, known_codes=known_codes)
  print(stats)  # {source_name: saved_count}
  ```

- カレンダー夜間更新ジョブ
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  from kabusys.data import schema

  conn = schema.get_connection("data/kabusys.duckdb")
  saved = calendar_update_job(conn)
  print("saved:", saved)
  ```

- 監査スキーマ初期化（監査専用に DB を用意する場合）
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/kabusys_audit.duckdb")
  ```

- J-Quants の ID トークン取得（明示的に呼ぶ）
  ```python
  from kabusys.data.jquants_client import get_id_token
  token = get_id_token()  # settings.jquants_refresh_token を使用
  ```

---

## 注意点 / 実装上の留意点

- API のレート制限とリトライ
  - J-Quants は rate limit を想定（120 req/min）。モジュール内でミニマム間隔を保つ RateLimiter を実装しています。
  - リトライは指数バックオフ（最大 3 回）。HTTP 401 受信時は自動的にリフレッシュを試行して 1 回だけ再試行します。

- データのトレーサビリティ
  - 取得時刻（fetched_at）を UTC で記録し、Look-ahead bias を防止できるよう設計されています。

- ニュース収集のセキュリティ
  - defusedxml を使用して XML 攻撃を緩和。
  - リダイレクト先のスキーム検証、プライベート IP/ホストへのアクセス拒否（SSRF 対策）。
  - レスポンスサイズを上限（10MB）でチェック。

- DuckDB への保存は可能な限り冪等（ON CONFLICT）で行い、重複や再実行に耐えるようにしています。

- 品質チェックは Fail-Fast を取らず、全チェックを実行して問題の一覧を返す設計です。呼び出し元で閾値に応じた対応（ETL 停止、アラートなど）を実装してください。

---

## ディレクトリ構成

リポジトリの主要ファイル（src 内）:

- src/kabusys/
  - __init__.py
  - config.py                         — 環境設定管理
  - data/
    - __init__.py
    - jquants_client.py                — J-Quants クライアント（取得・保存）
    - news_collector.py                — RSS ニュース収集
    - schema.py                        — DuckDB スキーマ定義/初期化
    - pipeline.py                      — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py           — マーケットカレンダー管理
    - audit.py                         — 監査ログ（signal/order/execution）
    - quality.py                       — データ品質チェック
  - strategy/
    - __init__.py                       — 戦略関連（拡張ポイント）
  - execution/
    - __init__.py                       — 発注実行関連（拡張ポイント）
  - monitoring/
    - __init__.py                       — 監視・アラート用（拡張ポイント）

（上記はコードベースに含まれる主要モジュールです。戦略・実行・監視モジュールは骨組みを提供しており、実際のアルゴリズムやブローカー接続はここに実装していきます）

---

## 拡張 / 実運用での検討点

- ブローカーとの発注実装（kabu API 連携）は execution モジュールに実装可能です。現在は設定・監査用のスキーマが整っています。
- Slack 連携などの通知機能は環境変数でトークンを設定し、各ジョブで活用してください。
- 運用時は KABUSYS_ENV を `paper_trading` や `live` に設定して安全制御やロギング挙動を切り替えることを想定しています。
- バックアップポリシー、DuckDB の VACUUM / コンパクション、運用ログのローテーションなどは運用チーム側で設計してください。

---

もし README に追加したい具体的な運用手順（例: cron / Airflow でのジョブ定義、Slack 通知例、CI 設定）や、要求される外部依存の正確な一覧（requirements.txt）を提供いただければ、さらに詳細な手順とサンプルを追記します。