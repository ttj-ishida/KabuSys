# KabuSys

日本株向け自動売買プラットフォームのコアライブラリ（KabuSys）。  
データ取得・スキーマ管理・監査ログ・データ品質チェック等の基盤機能を提供します。

注意: このリポジトリはフレームワーク/ライブラリ層の実装を含んでおり、実際の売買ロジック（strategy）や発注実行（execution）の具体実装は別途作成する想定です。

---

## 主な特徴（機能一覧）

- 環境変数／設定読み込み
  - `.env` / `.env.local` をプロジェクトルート（.git または pyproject.toml があるディレクトリ）から自動読み込み
  - 環境変数の保護（OS 環境変数を上書きしない等）
  - 必須環境変数未設定時は明示的に例外を投げる

- J-Quants API クライアント（data/jquants_client.py）
  - 株価日足（OHLCV）、四半期財務、JPX マーケットカレンダー等の取得機能
  - レート制限（120 req/min）を厳守する固定間隔スロットリング
  - リトライ（指数バックオフ、最大 3 回）、408/429/5xx に対応
  - 401 受信時はリフレッシュトークンで自動的に ID トークンを更新して再試行
  - 取得時刻（fetched_at）を UTC で記録（look-ahead bias 対策）
  - DuckDB への保存は冪等（ON CONFLICT DO UPDATE）で重複を排除

- DuckDB スキーマ管理（data/schema.py）
  - 3 層（Raw / Processed / Feature）＋ Execution / Audit 用のテーブル定義と初期化
  - インデックス定義やテーブル作成順（外部キー依存を考慮）
  - init_schema() / get_connection() を提供

- 監査ログ（data/audit.py）
  - シグナル → 発注要求 → 約定 の追跡を可能にする監査テーブル
  - 冪等キー（order_request_id）、作成・更新時刻（created_at/updated_at）、UTC タイムゾーン運用方針

- データ品質チェック（data/quality.py）
  - 欠損データ検出、前日比スパイク検出、主キー重複チェック、日付整合性検査など
  - 各チェックは QualityIssue のリストを返し、一括で収集して呼び出し元で対処可能

---

## 動作要件（前提）

- Python 3.10 以上（PEP 604 のユニオン型表記 (X | Y) を使用しているため）
- 依存パッケージ（代表）
  - duckdb
- 標準ライブラリで実装されている部分も多いですが、実行には duckdb などが必要です。

依存パッケージはプロジェクトの配布方法に合わせて requirements.txt / pyproject.toml 等で管理してください。

---

## セットアップ手順

1. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージのインストール（例）
   - pip install duckdb

   （プロジェクト配布に合わせて `pip install -e .` や `pip install -r requirements.txt` を使用してください）

3. 環境変数の設定
   - プロジェクトルートに `.env` を作成することを想定（`.env.example` を参考に）
   - 自動ロードはデフォルトで有効。無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
   - 構成に必要な主な環境変数（必須／任意）

     必須:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD — kabuステーション API パスワード
     - SLACK_BOT_TOKEN — Slack 通知用ボットトークン
     - SLACK_CHANNEL_ID — Slack チャンネル ID

     任意（デフォルトあり）:
     - KABU_API_BASE_URL — kabu ステーションのベース URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH — SQLite（監視用 DB）パス（デフォルト: data/monitoring.db）
     - KABUSYS_ENV — 動作環境: development | paper_trading | live（デフォルト: development）
     - LOG_LEVEL — ログレベル: DEBUG | INFO | WARNING | ERROR | CRITICAL

4. データベース初期化（DuckDB）
   - Python REPL またはスクリプトからスキーマを初期化します。

   例:
   - from kabusys.data import schema
   - conn = schema.init_schema(settings.duckdb_path)

   監査ログを既存接続に追加する場合:
   - from kabusys.data import audit
   - audit.init_audit_schema(conn)

---

## 使い方（基本的な利用例）

以下は主要 API の利用イメージです（実行前に環境変数を設定し、DuckDB スキーマを初期化してください）。

- DuckDB スキーマ初期化
  - from kabusys.config import settings
  - from kabusys.data import schema
  - conn = schema.init_schema(settings.duckdb_path)

- J-Quants から日足を取得して保存する
  - from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
  - records = fetch_daily_quotes(code="7203", date_from=date(2023,1,1), date_to=date(2023,12,31))
  - inserted = save_daily_quotes(conn, records)

  ポイント:
  - 接続は DuckDB の接続オブジェクトを渡す
  - fetch_* 系はページネーションに対応し、内部で ID トークンのキャッシュ・自動リフレッシュを行います
  - save_* は冪等で、重複は ON CONFLICT DO UPDATE により上書きされます

- 監査ログの初期化（別 DB に分けることも可能）
  - from kabusys.data import audit
  - audit_conn = audit.init_audit_db("data/audit.duckdb")

- データ品質チェックの実行
  - from kabusys.data.quality import run_all_checks
  - issues = run_all_checks(conn, target_date=date(2024,1,1))
  - for issue in issues:
        print(issue.check_name, issue.severity, issue.detail)
        # issue.rows にサンプル行が入る

- 環境設定参照
  - from kabusys.config import settings
  - print(settings.duckdb_path, settings.env, settings.is_live)

---

## 実装上の注意点・設計方針（抜粋）

- API 呼び出し制御
  - 固定間隔スロットリングで 120 req/min のレート制限を守る実装
  - リトライロジックは指数バックオフ（2^attempt 秒）で最大 3 回、429 の場合は Retry-After を尊重
  - 401 が返った場合はリフレッシュトークンで ID トークンを再取得して再試行（無限再帰防止あり）

- データ整合性
  - 取得時刻（fetched_at）は UTC の ISO フォーマットで保存し、いつシステムがデータを知り得たかを記録
  - DuckDB の INSERT は ON CONFLICT DO UPDATE を用い冪等性を担保

- 監査ログ設計
  - order_request_id を冪等キーとして二重発注を防止
  - 監査テーブルは削除せず、すべて UTC タイムスタンプで保存

- データ品質
  - 各チェックは全件を走査して QualityIssue のリストを返す（Fail-Fast ではなく、問題をまとめて検出）

---

## ディレクトリ構成

（プロジェクトルート直下に `src/` を置く構成を想定）

- src/
  - kabusys/
    - __init__.py
    - config.py              — 環境変数・設定管理
    - data/
      - __init__.py
      - jquants_client.py    — J-Quants API クライアント（取得・保存ロジック）
      - schema.py            — DuckDB スキーマ定義＆初期化
      - audit.py             — 監査ログ（追跡トレーサビリティ）
      - quality.py           — データ品質チェック
    - strategy/
      - __init__.py          — 戦略モジュール（拡張ポイント）
    - execution/
      - __init__.py          — 発注 / 約定管理（拡張ポイント）
    - monitoring/
      - __init__.py          — 監視・メトリクス（拡張ポイント）

---

## 今後の拡張ポイント（例）

- strategy と execution モジュールの具体実装（シグナル生成 / 発注実装）
- Slack 通知や監視ダッシュボード連携（settings に Slack 用設定あり）
- ETL ジョブスケジューラー・ワークフロー（Airflow / Prefect 等）との統合
- 単体テスト／統合テスト用のテストヘルパー（DB のモック等）

---

## 問い合わせ・貢献

バグ報告や機能提案、PR はリポジトリの Issue / Pull Request を通じてお願いします。  
README に記載の環境変数や DB 初期化手順に沿って再現可能な最小限の手順を添えてください。

---

README は上記の内容で初期版です。実運用やチーム共有のために、運用手順（runbook）、ETL スケジュール例、.env.example、CI/CD やテスト方針などを追加することを推奨します。