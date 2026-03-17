# KabuSys

日本株向けの自動売買・データ基盤ライブラリ群です。  
J-Quants など外部データソースから市場データ・財務データ・ニュースを収集し、DuckDB に整備されたスキーマで保存、品質チェック・ETL パイプライン・監査ログ機能を提供します。発注・戦略・監視のためのパッケージ骨格も含まれます。

主な目的は「データの取得→冪等保存→品質チェック→戦略/実行へ橋渡し」を安全・再現可能に行うことです。

## 機能一覧
- 環境変数・設定管理
  - .env / .env.local の自動ロード（優先順位: OS 環境変数 > .env.local > .env）
  - 必須設定の検証
- J-Quants API クライアント（kabusys.data.jquants_client）
  - 日次株価（OHLCV）、財務（四半期 BS/PL）、マーケットカレンダー取得
  - レートリミット遵守（120 req/min）、リトライ（指数バックオフ）、401 時の自動トークンリフレッシュ
  - DuckDB への冪等保存（ON CONFLICT）
- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得、URL 正規化、トラッキングパラメータ除去、記事ID（SHA-256）生成、DuckDB への冪等保存
  - SSRF / XML Bomb 対策、受信サイズ制限、gzip 対応
  - 記事と銘柄コードの紐付け（news_symbols）
- DuckDB スキーマ管理（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層のテーブル定義と初期化
  - インデックス定義
- ETL パイプライン（kabusys.data.pipeline）
  - 差分取得（最終取得日ベース）・バックフィル対応・品質チェック統合
  - 日次 ETL（run_daily_etl）を提供
- マーケットカレンダー管理（kabusys.data.calendar_management）
  - 営業日判定、前後営業日取得、期間内営業日列挙、夜間カレンダー更新ジョブ
- 監査ログ（kabusys.data.audit）
  - シグナル→発注→約定までのトレース用テーブル、監査向け制約・インデックス
- データ品質チェック（kabusys.data.quality）
  - 欠損、重複、スパイク、日付不整合検出
- パッケージ構成上の拡張ポイント
  - strategy, execution, monitoring パッケージの骨格を提供（実装はプロジェクト固有で追加）

---

## 要件
- Python 3.10+
- 必要な Python パッケージ（最低限例）
  - duckdb
  - defusedxml

（実プロジェクトでは、他に HTTP クライアントや Slack クライアント等を追加する可能性があります。）

インストール例:
```bash
python -m pip install "duckdb" "defusedxml"
```

プロジェクト固有の requirements.txt がある場合はそちらを使ってください。

---

## セットアップ手順

1. レポジトリをクローン／展開
2. Python 3.10+ の仮想環境を作成・有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows
   ```
3. 依存パッケージをインストール
   ```bash
   pip install duckdb defusedxml
   ```
4. 環境変数を設定
   - プロジェクトルートに `.env`（または `.env.local`）を置くと自動で読み込まれます（テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 必須環境変数（アプリ実行に必要なもの）
     - JQUANTS_REFRESH_TOKEN - J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD - kabu API のパスワード
     - SLACK_BOT_TOKEN - Slack Bot トークン
     - SLACK_CHANNEL_ID - Slack チャンネル ID
   - 任意／デフォルト
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト "development"
     - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — デフォルト "INFO"
     - DUCKDB_PATH — デフォルト "data/kabusys.duckdb"
     - SQLITE_PATH — デフォルト "data/monitoring.db"
   - 例 `.env`:
     ```
     JQUANTS_REFRESH_TOKEN=xxxxxxxx
     KABU_API_PASSWORD=yyyyyyyy
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C12345678
     KABUSYS_ENV=development
     DUCKDB_PATH=data/kabusys.duckdb
     ```

5. DuckDB スキーマを初期化
   - メインデータベース:
     ```python
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     ```
   - 監査ログ専用 DB（必要に応じて）:
     ```python
     from kabusys.data.audit import init_audit_db
     audit_conn = init_audit_db("data/audit.duckdb")
     ```

---

## 使い方（主要 API と実行例）

以下はライブラリを直接利用する例です。実運用ではこれらを CLI / バッチ / ワーカーに組み込んでください。

- J-Quants 認証トークン取得
  ```python
  from kabusys.data.jquants_client import get_id_token
  token = get_id_token()  # settings.jquants_refresh_token を利用
  ```

- 株価 / 財務 / カレンダーの取得（直接呼び出し）
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar

  quotes = fetch_daily_quotes(code="7203", date_from=date(2024,1,1), date_to=date(2024,1,31))
  financials = fetch_financial_statements(code="7203")
  calendar = fetch_market_calendar()
  ```

- DuckDB へ保存（冪等）
  ```python
  import duckdb
  from kabusys.data.jquants_client import save_daily_quotes

  conn = duckdb.connect("data/kabusys.duckdb")
  saved_count = save_daily_quotes(conn, quotes)
  ```

- 日次 ETL 実行
  ```python
  from datetime import date
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

  - run_daily_etl は市場カレンダー更新→株価差分ETL→財務差分ETL→品質チェックの順で実行します。各ステップは独立して例外ハンドリングされ、結果は ETLResult にまとめられます。

- ニュース収集ジョブ実行
  ```python
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  # known_codes は銘柄抽出に使う有効コードセット（例: 上場銘柄コードセット）
  result_map = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203", "6758"})
  print(result_map)
  ```

- カレンダー夜間更新ジョブ
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  saved = calendar_update_job(conn, lookahead_days=90)
  ```

- データ品質チェック（単体実行）
  ```python
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=None)
  for i in issues:
      print(i)
  ```

---

## 自動環境ロードの挙動
- 起動時に KABUSYS_DISABLE_AUTO_ENV_LOAD が設定されていなければ、プロジェクトルート（.git または pyproject.toml を探索）から `.env` を読み込み、その後 `.env.local` を上書きロードします。
- OS 環境変数は保護され、.env の値で上書きされません（ただし .env.local は override=True の扱いで上書きします）。
- .env のパース機能は export 形式・クォート・コメントなど実用的なケースに対応しています。

---

## セキュリティ / 設計上の注意
- J-Quants クライアントはレート制限とリトライ、401 自動リフレッシュを組み込んでいます。大量リクエスト時は設計（120 req/min）を守ってください。
- news_collector は SSRF、XML Bomb、トラッキングパラメータ対策、受信サイズ制限を実装していますが、取得元の信頼性にも注意してください。
- DuckDB への保存処理はできる限り冪等性（ON CONFLICT）を保つよう設計されています。
- ETL は Fail-Fast ではなく「全件収集し問題をレポートする」方針です。致命的な問題は呼び出し元で判断してください。

---

## ディレクトリ構成（主要ファイル）
プロジェクトのソースは `src/kabusys` 配下に格納されています。主要ファイルの概観は以下のとおりです。

- src/kabusys/
  - __init__.py
  - config.py                       — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py              — J-Quants API クライアント（取得 + DuckDB 保存）
    - news_collector.py              — RSS ニュース収集・整備・保存
    - schema.py                      — DuckDB スキーマ定義・初期化
    - pipeline.py                    — ETL パイプライン（差分更新・品質チェック）
    - calendar_management.py         — マーケットカレンダー管理（営業日判定等）
    - audit.py                       — 監査ログ（signal/order/execution 層）
    - quality.py                     — データ品質チェック
  - strategy/
    - __init__.py                    — 戦略パッケージ（拡張ポイント）
  - execution/
    - __init__.py                    — 実行（発注）パッケージ（拡張ポイント）
  - monitoring/
    - __init__.py                    — 監視 / アラートパッケージ（拡張ポイント）

---

## 開発・拡張のヒント
- strategy / execution / monitoring は各プロジェクトの要件に合わせて実装してください。ETL やデータ品質、監査ログは既に揃っているので、戦略ロジックやブローカー連携をここに組み込む形になります。
- 単体テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して環境ロードを抑制できます。
- jquants_client の _request は urllib を使用しており、ユニットテストでは urllib.request.urlopen をモックするか、モジュール内の _urlopen 等を差し替えてテストしてください。
- news_collector はネットワーク部分（_urlopen）をモック可能に設計しているため、外部接続をテストから切り離せます。

---

必要であれば、README にサンプル .env.example、より詳細な API リファレンス、CLI 実行例、デプロイ手順など追加します。どの情報を追加しますか？