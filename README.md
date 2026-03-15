# KabuSys

日本株向け自動売買プラットフォームのコアライブラリ（プロトタイプ）。  
このリポジトリはデータ取得、スキーマ定義、監査ログ、設定管理などの基盤機能を提供します。

---

## プロジェクト概要

KabuSys は以下の目的で設計された Python パッケージです。

- J-Quants API など外部データソースからの市場データ取得（株価、財務指標、取引カレンダー）
- 取得データの保存・管理（DuckDB を利用した多層スキーマ）
- 発注・約定の監査ログ（トレーサビリティの確保）
- 環境変数ベースの設定管理（.env の自動読み込みと検証）
- 将来的な戦略層・実行層との接続を想定した基盤実装

設計上のポイント:
- API レート制限（120 req/min）を守る固定間隔レートリミッタ実装
- リトライ（指数バックオフ、特定ステータスで再試行）とトークン自動リフレッシュ（401 時に 1 回）
- Look-ahead bias を防ぐため取得時刻（fetched_at）を UTC で保存
- DuckDB への保存は冪等（ON CONFLICT DO UPDATE）で重複を排除

---

## 機能一覧

主な提供機能（モジュール別）

- kabusys.config
  - .env / .env.local の自動読み込み（プロジェクトルート判定）
  - 設定ラッパー `settings`（必須項目の検証、環境フラグ等）
  - 自動ロード無効化フラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`

- kabusys.data.jquants_client
  - J-Quants API との通信ユーティリティ
  - get_id_token (refresh token から id token を取得)
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar（ページネーション対応）
  - save_daily_quotes / save_financial_statements / save_market_calendar（DuckDB への保存、冪等処理）
  - レートリミッタ・リトライ・トークン管理を内包

- kabusys.data.schema
  - DuckDB 用スキーマ定義（Raw / Processed / Feature / Execution レイヤ）
  - init_schema(db_path) でテーブル・インデックスを作成（冪等）
  - get_connection(db_path) で既存 DB に接続

- kabusys.data.audit
  - 監査ログ用テーブル定義（signal_events, order_requests, executions）
  - init_audit_schema(conn) / init_audit_db(db_path) による初期化
  - 監査トレーサビリティ（UUID 連鎖、タイムスタンプは UTC）

（strategy / execution / monitoring の骨組みは present ですが、具体実装はこのコードベースでは最小限）

---

## 必要条件

- Python 3.10 以上（型アノテーションに union 演算子（|）を使用）
- duckdb Python パッケージ

インストール例:
```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install duckdb
# （必要に応じてパッケージのローカルインストール）
# python -m pip install -e .
```

---

## 環境変数（主なもの）

以下はこのコードベースで参照・必須とされる環境変数の一覧（.env に設定）。

- JQUANTS_REFRESH_TOKEN (必須)  
  J-Quants のリフレッシュトークン。get_id_token に使用される。

- KABU_API_PASSWORD (必須)  
  kabuステーション / 発注 API のパスワード。

- KABU_API_BASE_URL (任意)  
  kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）。

- SLACK_BOT_TOKEN (必須)  
  Slack 通知用トークン（将来のモニタリング用）。

- SLACK_CHANNEL_ID (必須)  
  Slack 通知先チャンネル ID。

- DUCKDB_PATH (任意)  
  デフォルトの DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）。

- SQLITE_PATH (任意)  
  監視用 SQLite のパス（デフォルト: data/monitoring.db）。

- KABUSYS_ENV (任意)  
  実行環境: development / paper_trading / live（デフォルト: development）。不正値は例外。

- LOG_LEVEL (任意)  
  ログレベル: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）。

環境変数の自動ロード:
- プロジェクトルート（.git または pyproject.toml を探索）が見つかれば
  .env を読み込んだ後 .env.local を上書き読み込み（OS 環境変数は保護）。
- 自動読み込みを無効にする: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

.env のパースはシェル風の形式にある程度対応（export プレフィックス、引用符、コメントの扱い等）。

---

## セットアップ手順（簡易）

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境と依存のインストール
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   pip install duckdb
   ```

3. .env を作成（ルートに配置）
   - 必須変数を設定してください（例: JQUANTS_REFRESH_TOKEN 等）。
   - 例:
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

4. DuckDB スキーマ初期化（Python REPL やスクリプト）
   ```python
   from kabusys.data.schema import init_schema
   from kabusys.config import settings

   conn = init_schema(settings.duckdb_path)
   # 必要なら監査ログも初期化
   from kabusys.data.audit import init_audit_schema
   init_audit_schema(conn)
   ```

---

## 使い方（主な API 例）

- J-Quants から日足を取得して保存する（簡易例）:
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
  from kabusys.data.schema import init_schema
  from kabusys.config import settings

  conn = init_schema(settings.duckdb_path)

  # 全銘柄の直近データ（例: date_from/ date_to を指定可能）
  records = fetch_daily_quotes()
  saved = save_daily_quotes(conn, records)
  print(f"saved {saved} rows")
  ```

- 財務データ・マーケットカレンダーの取得・保存:
  ```python
  from kabusys.data.jquants_client import fetch_financial_statements, save_financial_statements
  from kabusys.data.jquants_client import fetch_market_calendar, save_market_calendar

  fin = fetch_financial_statements(code="7203")  # 銘柄コード例
  save_financial_statements(conn, fin)

  cal = fetch_market_calendar()
  save_market_calendar(conn, cal)
  ```

- id_token を直接取得する（必要な場合）:
  ```python
  from kabusys.data.jquants_client import get_id_token
  token = get_id_token()  # settings.jquants_refresh_token を参照
  ```

注意点:
- fetch_... 系はページネーションに対応しており、内部で id_token をキャッシュして共有します。
- HTTP 401 を受けた場合は自動で一度だけリフレッシュして再試行します。
- リトライは最大 3 回、408/429/5xx 等は指数バックオフを適用します。429 の場合は Retry-After を優先。

---

## ディレクトリ構成

リポジトリ内の主要ファイル／ディレクトリ:

- src/kabusys/
  - __init__.py          — パッケージ初期化（__version__ 等）
  - config.py            — 環境変数／設定読み込み（settings オブジェクト）
  - data/
    - __init__.py
    - jquants_client.py  — J-Quants API クライアント（fetch / save / auth / rate limit）
    - schema.py          — DuckDB スキーマ定義・初期化（init_schema, get_connection）
    - audit.py           — 監査ログ（signal_events / order_requests / executions）
  - strategy/
    - __init__.py        — 戦略層（拡張用）
  - execution/
    - __init__.py        — 発注実行層（拡張用）
  - monitoring/
    - __init__.py        — モニタリング／アラート（拡張用）

補足:
- Data スキーマは Raw / Processed / Feature / Execution という 4 層構成で定義されています。
- 監査ログは data.audit モジュールに独立しており、既存の DuckDB 接続に追加可能です。

---

## 開発上の注意点 / 今後の拡張

- strategy, execution, monitoring モジュールは骨組みがあるため、具体的な戦略・ブローカー連携はここに実装してください。
- 発注の冪等性や監査ログは audit モジュールで担保しています。実行層は order_requests の order_request_id を冪等キーとして扱うべきです。
- テスト時は自動 .env ロードを無効化できるため、CI では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を利用すると安全です。
- DuckDB のパフォーマンスやインデックス戦略は、実運用のクエリパターンに合わせて調整してください。

---

必要であれば README に以下を追加できます:
- 詳細な .env.example（テンプレート）
- 開発用の Makefile や tox / pytest セットアップ例
- API レート制御や監査テーブルの ER 図

ご希望があれば追記します。