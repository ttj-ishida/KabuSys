# KabuSys

日本株自動売買システム用ライブラリ（部分実装）

このリポジトリは、J-Quants API や RSS フィードを用いたデータ収集・ETL、DuckDB ベースのスキーマ定義、データ品質チェック、ニュース収集といった機能群を提供するパッケージ「KabuSys」のコア部分です。戦略や発注（execution）・監視（monitoring）は拡張可能な形で用意されています。

---

## プロジェクト概要

- パッケージ名: `kabusys`
- 目的: J-Quants 等の外部データソースから日本株データ（株価日足・財務データ・マーケットカレンダー）とニュースを収集し、DuckDB に冪等（idempotent）に保存、ETL と品質チェックを実行するための基盤ライブラリ。
- 設計上の特徴:
  - API レート制御およびリトライ（J-Quants クライアント）
  - データ取得時の fetched_at によるトレーサビリティ（look-ahead bias 防止）
  - DuckDB に対する冪等保存（ON CONFLICT / DO UPDATE）
  - RSS ニュース収集における SSRF 防御・XML ハードニング・受信サイズ制限
  - データ品質チェック（欠損・重複・スパイク・日付不整合）
  - 監査ログ（signal → order → execution のトレーサビリティ用スキーマ）

---

## 機能一覧

- 環境変数 / .env ロード（自動ロード、プロジェクトルート検出）
- J-Quants API クライアント
  - 株価日足（OHLCV）取得（ページネーション対応）
  - 財務データ取得（四半期等）
  - マーケットカレンダー取得
  - トークン自動リフレッシュ、リトライ、レート制御
- DuckDB スキーマ定義・初期化（raw / processed / feature / execution 層）
- ETL パイプライン（差分取得、バックフィル、品質チェック統合）
- ニュース収集（RSS 取得、テキスト前処理、記事ID生成、DuckDB 保存、銘柄紐付け）
- マーケットカレンダー管理（営業日判定、next/prev_trading_day 等）
- 監査ログスキーマ（signal / order_request / executions）
- データ品質チェックモジュール（欠損・重複・スパイク・日付不整合）

---

## セットアップ手順

1. Python 環境を準備
   - Python 3.9+ を推奨

2. 仮想環境の作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate（Windows: .venv\Scripts\activate）

3. 必要パッケージのインストール
   - 少なくとも以下をインストールしてください:
     - duckdb
     - defusedxml
   - 例:
     - pip install duckdb defusedxml

   （プロジェクトに requirements ファイルがある場合はそちらを利用してください）

4. 環境変数設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動でロードされます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットすると無効化可能）。
   - 必須の環境変数（少なくとも以下を設定してください）:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD — kabuステーション API のパスワード（execution 実装で使用）
     - SLACK_BOT_TOKEN — Slack 通知用（monitoring 等で使用）
     - SLACK_CHANNEL_ID — Slack チャンネル ID
   - 任意 / デフォルト:
     - KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL — DEBUG/INFO/…（デフォルト: INFO）
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH — 監視/メトリクス用 SQLite（デフォルト: data/monitoring.db）

   - .env の例:
     ```
     JQUANTS_REFRESH_TOKEN=your_refresh_token_here
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C12345678
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

---

## 使い方（簡単な例）

以下は Python REPL やスクリプトでの基本操作例です。

1. DuckDB スキーマ初期化
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   ```
   - ":memory:" を渡すとインメモリ DB を使用できます。
   - 親ディレクトリが無ければ自動作成します。

2. 日次 ETL 実行（株価・財務・カレンダー取得 + 品質チェック）
   ```python
   from datetime import date
   from kabusys.data.pipeline import run_daily_etl
   # conn は上で初期化した DuckDB 接続
   result = run_daily_etl(conn, target_date=date.today())
   print(result.to_dict())
   ```
   - J-Quants の id_token を明示的に渡すことも可能。省略時は Settings から取得してキャッシュします。

3. ニュース収集（RSS）と DB 保存
   ```python
   from kabusys.data.news_collector import run_news_collection
   # known_codes は銘柄抽出に使う有効銘柄コードの集合（例: {'7203','6758',...}）
   stats = run_news_collection(conn, sources=None, known_codes={'7203','6758'})
   print(stats)  # {source_name: 新規保存件数, ...}
   ```

4. カレンダー判定ユーティリティ
   ```python
   from kabusys.data.calendar_management import is_trading_day, next_trading_day
   import datetime
   d = datetime.date(2025, 1, 1)
   print(is_trading_day(conn, d))
   print(next_trading_day(conn, d))
   ```

5. 監査ログスキーマの初期化（監査用テーブルを追加）
   ```python
   from kabusys.data.audit import init_audit_schema
   init_audit_schema(conn, transactional=True)
   ```

---

## 環境変数・設定（まとめ）

主な環境変数:
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (任意、デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- DUCKDB_PATH (任意、デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (任意、デフォルト: data/monitoring.db)
- KABUSYS_ENV (development | paper_trading | live、デフォルト: development)
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL、デフォルト: INFO)
- KABUSYS_DISABLE_AUTO_ENV_LOAD (1 をセットすると .env 自動ロードを無効化)

設定は .env/.env.local または OS 環境変数から読み込まれます。パッケージ起動時にプロジェクトルート（.git または pyproject.toml を基準）を探索して自動ロードします。

---

## ディレクトリ構成

（主要ファイル・モジュールのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                    — 環境変数 / 設定管理
    - data/
      - __init__.py
      - jquants_client.py          — J-Quants API クライアント（取得・保存ロジック）
      - news_collector.py          — RSS ニュース収集・前処理・保存
      - schema.py                  — DuckDB スキーマ定義と init_schema()
      - pipeline.py                — ETL パイプライン（run_daily_etl 等）
      - calendar_management.py     — マーケットカレンダー管理（営業日判定・更新ジョブ）
      - audit.py                   — 監査ログ（signal/order/execution スキーマ）
      - quality.py                 — データ品質チェック
    - strategy/
      - __init__.py                — 戦略関連の拡張ポイント（空モジュール）
    - execution/
      - __init__.py                — 発注 / ブローカ連携の拡張ポイント（空モジュール）
    - monitoring/
      - __init__.py                — 監視 / 通知の拡張ポイント（空モジュール）

---

## 注意点 / 補足

- この README はコードベースの現状に基づく説明です。発注（証券会社連携）や Slack 通知などの機能は設定値や追加実装が必要です。
- J-Quants API のレート制限・認証仕様は外部仕様に依存します。実運用ではトークン管理・エラーハンドリングの監視が重要です。
- DuckDB のファイルをバックアップ・運用する場合は適切なバックアップ運用を検討してください。
- news_collector は外部 RSS の扱いに際して SSRF 対策・XML ハードニング・レスポンスサイズ制限を組み込んでいます。実運用でソースを追加する際はソースの信頼性確認を行ってください。

---

もし README に追加したい内容（例: CI / テスト実行手順、より詳細な API 使用例、開発向けセットアップ手順など）があれば指示してください。必要に応じてサンプルコードや .env.example を追記します。