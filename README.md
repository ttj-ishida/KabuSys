# KabuSys

日本株向けの自動売買／データ基盤ライブラリです。  
J-Quants API からマーケットデータ（株価日足・財務・市場カレンダー等）を取得して DuckDB に保存し、データ品質チェック、監査ログ（発注 → 約定のトレーサビリティ）を提供します。戦略・実行・監視用の基礎を備えたモジュール群を含みます。

バージョン: 0.1.0

---

## 主要な特徴

- J-Quants API クライアント
  - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX 市場カレンダーの取得
  - API レート制御（120 req/min 固定間隔スロットリング）
  - リトライ（指数バックオフ、最大 3 回）。408 / 429 / 5xx を対象
  - 401 受信時はリフレッシュトークンから自動で ID トークンを取得して 1 回リトライ
  - 取得時刻（fetched_at）を UTC で記録し Look-ahead バイアスを管理
  - DuckDB への保存は冪等（ON CONFLICT DO UPDATE）

- DuckDB スキーマ定義／初期化
  - Raw / Processed / Feature / Execution 層に対応したテーブル群
  - インデックス定義、外部キーを考慮した作成順

- ETL パイプライン
  - 差分更新（DB の最終取得日に基づく差分取得）
  - backfill による後出し修正吸収
  - 品質チェック（欠損、スパイク、重複、日付不整合）
  - 各ステップは独立エラーハンドリング（1 ステップ失敗でも残りを継続）

- データ品質チェック
  - 欠損（OHLC 欠損）
  - 前日比スパイク（デフォルト 50%）
  - 主キー重複
  - 将来日付・非営業日データの検出

- 監査ログ（順序トレーサビリティ）
  - signal_events, order_requests, executions テーブルで戦略→発注→約定まで追跡可能
  - order_request_id を冪等キーとして利用

- 環境変数／設定管理
  - .env / .env.local を自動で読み込み（OS 環境変数を優先）
  - 必須設定の取得を容易にする Settings API

---

## 必要環境

- Python 3.10 以上（型注釈の Union 記法などのため）
- 依存パッケージ（一例）
  - duckdb
- （任意）J-Quants API の利用には J-Quants のリフレッシュトークンが必要

※プロジェクトに pyproject.toml / requirements.txt がある場合はそちらに従ってください。

---

## セットアップ手順（開発環境例）

1. 仮想環境を作成して有効化（例）:
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール:
   - pip install duckdb
   - （プロジェクト配布が pip パッケージ化されている場合）pip install -e .

3. 環境変数を用意:
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すれば自動ロードを無効化可能）。
   - 必須の環境変数（最低限）:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD — kabuステーション API パスワード（必須）
     - SLACK_BOT_TOKEN — Slack ボットトークン（必須）
     - SLACK_CHANNEL_ID — Slack チャンネル ID（必須）
   - オプション / デフォルト:
     - KABUSYS_ENV — development | paper_trading | live（デフォルト: development）
     - LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH — 監視 DB などに使用（デフォルト: data/monitoring.db）

4. .env サンプル（例）
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development
   DUCKDB_PATH=data/kabusys.duckdb
   ```

---

## 使い方（主な例）

- 設定取得
  ```python
  from kabusys.config import settings
  print(settings.jquants_refresh_token)
  print(settings.duckdb_path)
  ```

- DuckDB スキーマ初期化（最初に一度だけ実行）
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.config import settings

  conn = init_schema(settings.duckdb_path)
  # conn は DuckDB 接続（duckdb.DuckDBPyConnection）
  ```

- 監査ログ（audit）スキーマの追加（既存接続へ）
  ```python
  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn)  # conn: DuckDB 接続
  ```

- 日次 ETL 実行（カレンダー取得→価格→財務→品質チェック）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.data.schema import init_schema
  from kabusys.config import settings
  from datetime import date

  conn = init_schema(settings.duckdb_path)
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- 個別データ取得（J-Quants クライアントを直接利用）
  ```python
  from kabusys.data import jquants_client as jq
  from kabusys.config import settings
  from kabusys.data.schema import init_schema

  conn = init_schema(settings.duckdb_path)
  # 銘柄コード指定・期間指定で取得
  recs = jq.fetch_daily_quotes(code="7203", date_from=date(2023,1,1), date_to=date(2023,12,31))
  jq.save_daily_quotes(conn, recs)
  ```

- 品質チェック単体実行
  ```python
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=None)
  for i in issues:
      print(i)
  ```

---

## 実装メモ（重要な設計・挙動）

- 環境変数の自動読み込み
  - パッケージ読み込み時にプロジェクトルート（.git または pyproject.toml があるディレクトリ）を探索し、`.env` → `.env.local` を順に読み込みます。
  - OS 環境変数が優先され、`.env.local` は `.env` 上書き可能（ただし既存 OS 変数は保護されます）。
  - 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

- J-Quants クライアントの仕様
  - 基本 URL: https://api.jquants.com/v1
  - レート制御: 120 req/min（約 0.5秒間隔）
  - リトライ: 最大 3 回、408/429/5xx はリトライ対象。429 の場合は Retry-After ヘッダを優先。
  - 401 を受けた場合はリフレッシュトークンで ID トークンを再取得して 1 回だけリトライ（無限再帰を防止）。
  - ページネーション対応（pagination_key を使って全ページ取得）
  - DuckDB への保存関数は冪等（ON CONFLICT DO UPDATE）なので同じデータを何度保存しても安全。

- ETL パイプライン
  - デフォルトでは最終取得日から backfill_days（デフォルト 3 日）遡って再取得し、API の後出し修正を吸収します。
  - 市場カレンダーは lookahead で将来分を先読み（デフォルト 90 日）。
  - 品質チェックはエラーが見つかっても ETL は継続し、結果オブジェクトに問題一覧を返します。呼び出し側で停止判断を行ってください。

- 監査ログ
  - 発生する各種 ID（signal_id、order_request_id、broker_order_id、execution_id 等）を保存し、発注フローを完全にトレース可能にします。
  - order_request_id を冪等キーとして二重発注を防止する設計になっています。

---

## ディレクトリ構成（概要）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings 管理
  - data/
    - __init__.py
    - jquants_client.py       — J-Quants API クライアント（取得・保存ロジック）
    - pipeline.py             — ETL パイプライン（daily_etl 等）
    - schema.py               — DuckDB スキーマ定義と init/get 接続
    - audit.py                — 監査ログ（signal/events/order_requests/executions）
    - quality.py              — データ品質チェック
  - strategy/
    - __init__.py             — 戦略関連（拡張ポイント）
  - execution/
    - __init__.py             — 発注実行関連（拡張ポイント）
  - monitoring/
    - __init__.py             — 監視・アラート用（拡張ポイント）

---

## 開発・運用上の注意

- 本ライブラリは実運用向けに「live / paper_trading / development」の環境切替をサポートします。`KABUSYS_ENV` を適切に設定してください。
- DuckDB ファイルはデフォルトで `data/kabusys.duckdb` に作成されます。永続化パスとバックアップに注意してください。
- J-Quants の API レート制御・リトライの設計は含まれていますが、実際の運用時はネットワーク状況や API 利用規約に注意してください。
- 監査ログは削除しない前提で設計されています（ON DELETE RESTRICT 等）。過度に大きくならないよう運用面でのローテーション方針を検討してください。

---

## 追加情報 / 貢献

- 機能追加（戦略実装、約定ブリッジ、監視ダッシュボードなど）は strategy/、execution/、monitoring/ の拡張により実現できます。
- バグ報告・プルリクエスト歓迎です。README をベースに利用方法や設計意図を追記してください。

---

必要であれば、README に含めるコマンド例や .env.example の完全なテンプレート、CI 用の手順、テストの実行方法（ユニットテストの構成）なども作成します。どの情報を追加しますか？