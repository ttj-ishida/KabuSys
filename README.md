# KabuSys

日本株向け自動売買プラットフォームのコアライブラリ（KabuSys）。  
データ取得（J-Quants）、DuckDBスキーマ管理、監査ログ、環境設定を中心にした基盤実装を提供します。

主な設計方針：
- データ取得はレート制限・リトライ・トークン自動更新に対応
- DuckDB を用いた多層（Raw / Processed / Feature / Execution）スキーマ
- 発注フローの監査（トレーサビリティ）を強く意識した設計
- 環境変数を .env/.env.local から自動ロード（任意で無効化可能）

---

## 機能一覧
- 環境設定管理（kabusys.config）
  - .env / .env.local をプロジェクトルートから自動読み込み
  - 必須環境変数の検査（例: JQUANTS_REFRESH_TOKEN 等）
  - KABUSYS_ENV / LOG_LEVEL のバリデーション
- J-Quants API クライアント（kabusys.data.jquants_client）
  - 日足（OHLCV）・財務データ（四半期）・JPX マーケットカレンダーの取得
  - レート制御（120 req/min 固定間隔スロットリング）
  - リトライ（指数バックオフ、最大 3 回。408/429/5xx 対象）
  - 401時の自動トークンリフレッシュ（1 回のみ）
  - fetched_at による Look-ahead Bias 防止（UTC）
  - DuckDB へ冪等的に保存するユーティリティ（ON CONFLICT DO UPDATE）
- DuckDB スキーマ管理（kabusys.data.schema）
  - Raw / Processed / Feature / Execution レイヤーのテーブル定義
  - インデックス定義とテーブル作成（冪等）
  - init_schema / get_connection API
- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions テーブルによるトレーサビリティ
  - order_request_id を冪等キーとして扱う設計
  - UTC タイムゾーン固定、監査テーブル初期化 API（init_audit_schema / init_audit_db）
- パッケージ骨格: strategy / execution / monitoring 用の名前空間を準備（実装は各所）

---

## 動作要件
- Python 3.10+
  - 型注釈に union 型 (X | Y) を使用しているため 3.10 以上が必要です
- 依存パッケージ（最低限）:
  - duckdb

（プロジェクトルートに requirements.txt / pyproject.toml があればそれに従って下さい）

---

## セットアップ手順（開発環境向け）

1. リポジトリをクローン
   - git clone <リポジトリURL>
2. 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install --upgrade pip
   - pip install duckdb
   - （パッケージ化されている場合）pip install -e .
4. .env を作成
   - プロジェクトルートに .env（および任意で .env.local）を作成してください。
   - 自動ロードはデフォルトで有効です。自動ロードを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

必須環境変数（kabusys.config.Settings から）
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API のパスワード（必須）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID — Slack 送信先チャンネル ID（必須）

任意 / デフォルトあり
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV — environment: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...、デフォルト: INFO）

---

## 使い方（簡単なコード例）

- DuckDB スキーマの初期化
  - from kabusys.data import schema
  - conn = schema.init_schema(settings.duckdb_path)

- J-Quants から日足を取得して保存する例
  - from kabusys.data import jquants_client
  - from kabusys.config import settings
  - conn = schema.init_schema(settings.duckdb_path)
  - records = jquants_client.fetch_daily_quotes(code="7203", date_from=date(2024,1,1), date_to=date(2024,3,31))
  - inserted = jquants_client.save_daily_quotes(conn, records)
  - print(f"{inserted} 件保存しました")

- id_token を直接取得したい場合
  - from kabusys.data.jquants_client import get_id_token
  - token = get_id_token()  # settings.jquants_refresh_token を使用して POST で取得

- 監査ログの初期化
  - from kabusys.data import audit
  - conn = schema.init_schema(settings.duckdb_path)
  - audit.init_audit_schema(conn)

注意点（実装上の振る舞い）
- fetch 系関数はページネーションに対応しており、pagination_key を追って全件取得します。
- レート制限は _RateLimiter による固定間隔スロットリングで守られます（120 req/min）。
- HTTP 401 はトークン自動リフレッシュを行い 1 回だけ再試行します（無限ループ防止）。
- save_* 系関数は冪等（ON CONFLICT DO UPDATE）で DuckDB に保存します。
- すべてのタイムスタンプは UTC を前提に扱われます（監査テーブルでは明示的に SET TimeZone='UTC' を実行）。

---

## ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py — パッケージエントリ（version 等）
  - config.py — 環境変数 / 設定管理（.env 自動ロード、Settings クラス）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得 / 保存ロジック）
    - schema.py — DuckDB スキーマ定義・初期化（Raw/Processed/Feature/Execution）
    - audit.py — 監査ログ（signal_events / order_requests / executions）
    - (その他: audit 用 DB 初期化ユーティリティ等)
  - strategy/
    - __init__.py — 戦略関連の名前空間（実装を追加する場所）
  - execution/
    - __init__.py — 発注関連の名前空間（実装を追加する場所）
  - monitoring/
    - __init__.py — 監視／アラート関連の名前空間（実装を追加する場所）

テーブルの一例（schema.py に定義）
- raw_prices, raw_financials, raw_news, raw_executions
- prices_daily, market_calendar, fundamentals, news_articles, news_symbols
- features, ai_scores
- signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance

監査用テーブル（audit.py）
- signal_events, order_requests, executions

---

## 開発・運用上の留意点
- 環境変数の自動読み込みはプロジェクトルート（.git または pyproject.toml が見つかる場所）から行います。テスト時に自動ロードを抑止するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- J-Quants のレート制限や HTTP 状態コードに対する扱いは jquants_client.py に実装されています。外部 API の変更に合わせて適切に更新してください。
- DuckDB のスキーマは冪等で作成されますが、本番運用時はバックアップ・マイグレーション方針を別途用意してください。
- 監査ログは削除しない前提（ON DELETE RESTRICT 等）で設計されています。容量管理・ローテーション戦略を検討してください。

---

この README はコードベースの現状実装（src/ 以下）に基づく簡易ドキュメントです。戦略ロジック（strategy）や発注実装（execution）の具体的な実装はプロジェクトに応じて追加していってください。必要であれば、README にサンプル .env.example、ユニットテストの実行方法、CI 設定のテンプレート等も追記できます。希望があれば教えてください。