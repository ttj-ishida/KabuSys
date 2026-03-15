# KabuSys

日本株向け自動売買プラットフォーム用ライブラリ（モジュールセット）。  
データ取得、DuckDB スキーマ定義、監査ログ、戦略・実行・モニタリング基盤の骨組みを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株自動売買システム構築のための共通ライブラリ群です。主な目的は次のとおりです。

- 外部データソース（J-Quants 等）からの市場データ取得と保存
- DuckDB を用いた3層（Raw / Processed / Feature）データレイヤと実行・監査テーブルのスキーマ定義・初期化
- 発注フローの監査ログ（order_request → executions のトレーサビリティ）
- 環境変数ベースの設定管理（.env 自動ロード機構）

設計上の特徴:
- API レート制御（固定間隔スロットリング）
- 再試行（指数バックオフ）と 401 トークン自動リフレッシュ対応
- データ取得時の fetched_at 記録（Look‑ahead bias 対策）
- DuckDB への挿入は冪等（ON CONFLICT DO UPDATE）

---

## 機能一覧

- 環境設定管理（kabusys.config）
  - .env / .env.local をプロジェクトルートから自動ロード（.git または pyproject.toml を基準）
  - 必須設定の取得（例: JQUANTS_REFRESH_TOKEN）とバリデーション
  - 環境（development / paper_trading / live）とログレベル検証
  - 自動ロード無効化フラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`

- J-Quants API クライアント（kabusys.data.jquants_client）
  - 株価日足（OHLCV）、財務（四半期 BS/PL）、JPX マーケットカレンダー取得
  - レート制御（120 req/min）
  - 再試行ロジック（最大 3 回、指数バックオフ）
  - 401 を受信した場合のリフレッシュと再試行
  - ページネーション対応
  - DuckDB へ保存するユーティリティ（save_* 関数）

- DuckDB スキーマ定義・初期化（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層のテーブル DDL
  - インデックス定義とテーブル作成順を考慮した初期化 API:
    - init_schema(db_path)
    - get_connection(db_path)

- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions の監査テーブル
  - order_request_id を冪等キーとして発注の重複を防止
  - UTC タイムゾーン固定、インデックス定義

- フレームワーク的ディレクトリ（strategy, execution, monitoring）を想定（各モジュールは拡張用）

---

## セットアップ手順

前提:
- Python 3.10 以上（型ヒントで `X | Y` 構文を使用）
- duckdb が必要（pip でインストール）

手順例:

1. 仮想環境を作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (または Windows の場合 .venv\Scripts\activate)

2. 依存パッケージをインストール（最低限 duckdb）
   - pip install duckdb

   （プロジェクトで requirements.txt があればそちらを利用してください）

3. プロジェクトルートに .env を用意
   - プロジェクトルートは .git または pyproject.toml の存在で自動検出されます。
   - 例（.env.example）:

     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     KABU_API_PASSWORD=your_kabu_api_password
     KABU_API_BASE_URL=http://localhost:18080/kabusapi  # 任意
     SLACK_BOT_TOKEN=your_slack_token
     SLACK_CHANNEL_ID=your_channel_id
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     KABUSYS_ENV=development
     LOG_LEVEL=INFO

   - .env.local がある場合は .env の値を上書きします（ただし OS 環境変数は保護されます）。

4. 自動 .env 読み込みを無効化したい場合:
   - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を環境変数に設定します（テスト等で利用）。

---

## 使い方（簡易例）

以下は主要な API の利用例です。実際はログ設定やエラーハンドリングを適切に行ってください。

- DuckDB スキーマを初期化して接続を取得する:

  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")
  # ":memory:" を渡すとインメモリ DB

- J-Quants から日足を取得して保存する:

  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes

  # id_token を明示的に渡すこともできますが、指定しなければモジュール内で
  # refresh トークンから自動取得・キャッシュされます。
  records = fetch_daily_quotes(code="7203", date_from=date(2023,1,1), date_to=date(2023,12,31))
  count = save_daily_quotes(conn, records)
  print(f"保存したレコード数: {count}")

- 財務データやカレンダーの取得・保存も同様:

  from kabusys.data.jquants_client import fetch_financial_statements, save_financial_statements
  records = fetch_financial_statements(code="7203")
  save_financial_statements(conn, records)

  from kabusys.data.jquants_client import fetch_market_calendar, save_market_calendar
  cal = fetch_market_calendar()
  save_market_calendar(conn, cal)

- 監査ログの初期化（既存の DuckDB 接続に追加）:

  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn)

- 設定（環境変数）を参照する例:

  from kabusys.config import settings
  token = settings.jquants_refresh_token
  is_live = settings.is_live

注意点（J-Quants クライアント）:
- レート制限: 120 req/min（内部でスロットリング）
- リトライ: 408/429/5xx に対し最大 3 回（指数バックオフ）；429 の場合は Retry-After を優先
- 401 受信時はトークンを自動リフレッシュして1回リトライ
- ページネーションキーは自動で追跡

---

## ディレクトリ構成

リポジトリ内の主要ファイル構成（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py                    # 環境変数・設定管理
    - data/
      - __init__.py
      - jquants_client.py          # J-Quants API クライアント（fetch/save 関数）
      - schema.py                  # DuckDB スキーマ定義 & init_schema
      - audit.py                   # 監査ログ（signal_events, order_requests, executions）
      - (その他: raw/processed テーブル関連)
    - strategy/
      - __init__.py                # 戦略モジュールのエントリ（実装は拡張）
    - execution/
      - __init__.py                # 発注・ブローカ連携のための拡張ポイント
    - monitoring/
      - __init__.py                # モニタリング用モジュール（拡張）
- .env.example (任意: サンプル設定ファイル)
- pyproject.toml / setup.cfg 等（パッケージ配布用）

---

## 補足・運用上の注意

- DuckDB を永続化する場合は DUCKDB_PATH を適切に設定してください（デフォルト: data/kabusys.duckdb）。
- 監査ログは削除しない前提です。order_requests.order_request_id を冪等キーとして再送対策を行ってください。
- すべての TIMESTAMP は監査ログにおいて UTC 保存が前提です（init_audit_schema は `SET TimeZone='UTC'` を実行します）。
- 本ライブラリは骨格的な実装に重点を置いています。実際の取引（特に live 環境）で使用する場合は、リスク管理・例外処理・証券会社 API の実装など追加の実装・レビューが必須です。

---

もし README に記載してほしい追加情報（例: 依存パッケージ一覧、CI / テスト手順、拡張ガイドなど）があれば教えてください。必要に応じてサンプル .env.example やサンプルスクリプトも追加します。