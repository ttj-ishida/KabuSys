# KabuSys — 日本株自動売買システム (README)

簡潔な説明:
KabuSys は日本株の自動売買プラットフォーム／データ基盤の骨組みを提供する Python パッケージです。J-Quants API からのデータ取得、DuckDB によるデータスキーマ管理、監査ログ（発注〜約定のトレーサビリティ）など、自動売買システムの基盤機能を揃えています。

主な設計方針（抜粋）
- API レート制限・リトライ・トークン自動リフレッシュを備えた堅牢なデータ取得
- 取得時刻（fetched_at）で Look-ahead bias を防止
- DuckDB 上で冪等的にデータを保存（ON CONFLICT DO UPDATE）
- 監査ログによる完全なトレーサビリティ（UUID による連鎖）
- 環境変数・.env による設定管理（自動ロード可）

---

## 機能一覧
- 環境設定管理（kabusys.config）
  - .env / .env.local をプロジェクトルートから自動読み込み（必要に応じて無効化可能）
  - 必須設定の検証（未設定時は ValueError を発生）
- データ取得（kabusys.data.jquants_client）
  - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーの取得
  - レート制限（120 req/min）の遵守、再試行（指数バックオフ）、401 時のトークン自動リフレッシュ
  - ページネーション対応および取得時刻の記録
- DuckDB スキーマ管理（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層のテーブル定義と初期化
  - インデックス定義、テーブル作成の順序管理（外部キー依存）
- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions の監査テーブル定義と初期化
  - 発注の冪等キー（order_request_id）による二重発注防止
- （プレースホルダ）strategy / execution / monitoring パッケージ骨組み

---

## 動作要件
- Python 3.10 以上（型注釈に Python 3.10 の union 表記（A | B）を使用）
- duckdb パッケージ
  - インストール: pip install duckdb

（将来的に外部 API 連携や Slack 通知を使う場合は該当 SDK を追加で導入してください）

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <このリポジトリの URL>
   cd <リポジトリ>
   ```

2. 仮想環境を作成して有効化（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール
   ```
   pip install duckdb
   # パッケージが pyproject/セットアップされている場合:
   # pip install -e .
   ```

4. 設定（.env ファイルの作成）
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` を置くと自動で読み込まれます。
   - 自動ロードを無効にしたい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト等で有用）。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - 任意・デフォルト:
     - KABUSYS_ENV (development | paper_trading | live) — default: development
     - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — default: INFO
     - KABU_API_BASE_URL — default: http://localhost:18080/kabusapi
     - DUCKDB_PATH — default: data/kabusys.duckdb
     - SQLITE_PATH — default: data/monitoring.db

   サンプル `.env`:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxx...
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development
   DUCKDB_PATH=data/kabusys.duckdb
   ```

---

## 使い方（基本例）

- 設定取得:
  ```python
  from kabusys.config import settings
  print(settings.env)  # 'development' / 'paper_trading' / 'live'
  print(settings.duckdb_path)  # Path オブジェクト
  # 注意: secrets をログ出力しないでください
  ```

- DuckDB スキーマ初期化:
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.config import settings

  conn = init_schema(settings.duckdb_path)
  # conn は duckdb の接続オブジェクト
  ```

- J-Quants から日足データを取得して保存:
  ```python
  from datetime import date
  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
  from kabusys.data.schema import init_schema
  from kabusys.config import settings

  conn = init_schema(settings.duckdb_path)

  # 例: 銘柄コード 7203（トヨタ）の日足を取得
  records = fetch_daily_quotes(code="7203", date_from=date(2023, 1, 1), date_to=date(2023, 12, 31))
  n = save_daily_quotes(conn, records)
  print(f"保存したレコード数: {n}")
  ```

- ID トークン取得（内部で refresh_token を使用して POST）:
  ```python
  from kabusys.data.jquants_client import get_id_token
  token = get_id_token()  # settings.jquants_refresh_token を使う
  ```

- 監査ログテーブルの初期化:
  ```python
  from kabusys.data.audit import init_audit_schema, init_audit_db
  from kabusys.config import settings
  from kabusys.data.schema import init_schema

  # 既存の接続に追記する場合:
  conn = init_schema(settings.duckdb_path)
  init_audit_schema(conn)

  # 監査専用 DB を別で用意する場合:
  audit_conn = init_audit_db("data/kabusys_audit.duckdb")
  ```

- テスト等で .env の自動読み込みを抑止する:
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  # または Windows PowerShell:
  # $env:KABUSYS_DISABLE_AUTO_ENV_LOAD = "1"
  ```

---

## よくあるトラブルと注意点
- 必須環境変数が未設定の場合、settings の該当プロパティアクセスで ValueError が発生します。
- J-Quants API のレート制限はモジュールレベルで制御されます。短時間に大量リクエストを投げると待機やリトライが発生します。
- DuckDB の初期化時に親ディレクトリが存在しない場合は自動作成されます。
- すべての TIMESTAMP は UTC 扱い（監査ログ初期化時に TimeZone='UTC' を設定します）。
- 補助的な外部サービス（Slack、kabu-station など）の連携はトークンやエンドポイント設定が必要です。当該機能はこのコードベースの一部として保持されていますが、実動作はそれらの環境構築に依存します。

---

## ディレクトリ構成（抜粋）
以下はリポジトリ内の主要ファイル・パッケージ構成です（src/kabusys 配下）。

- src/
  - kabusys/
    - __init__.py
    - config.py                # 環境変数・設定管理
    - data/
      - __init__.py
      - jquants_client.py      # J-Quants API クライアント（取得・保存ロジック）
      - schema.py              # DuckDB スキーマ定義・初期化
      - audit.py               # 監査ログ（signal / order_request / execution）
      - audit.py
    - strategy/
      - __init__.py            # 戦略層（骨組み）
    - execution/
      - __init__.py            # 発注・ブローカー連携（骨組み）
    - monitoring/
      - __init__.py            # 監視・メトリクス（骨組み）

主要なテーブル（schema.py / audit.py に定義）
- Raw レイヤー: raw_prices, raw_financials, raw_news, raw_executions
- Processed レイヤー: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
- Feature レイヤー: features, ai_scores
- Execution レイヤー: signals, signal_queue, orders, trades, positions, portfolio_*
- 監査レイヤー: signal_events, order_requests, executions

---

## 今後の拡張案（参考）
- strategy / execution / monitoring の具現化（戦略実装、リアルブローカー連携、監視ダッシュボード）
- Slack 通知・アラートの実装
- J-Quants 以外のデータソース追加
- テストカバレッジの整備（ユニット・統合テスト）

---

お問い合わせ・貢献
- バグ報告や機能提案は Issue を立ててください。Pull Request は歓迎します。
- セキュリティ上の懸念（トークン漏洩等）があれば直ちに連絡してください（公開レポジトリではトークンを絶対にコミットしないでください）。

以上。必要であれば README に加えたい具体的なサンプル（Slack 統合例、戦略テンプレート、CI 設定など）を教えてください。