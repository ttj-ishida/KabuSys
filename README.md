# KabuSys

日本株の自動売買プラットフォーム用ライブラリ（KabuSys）。  
データ取得・ETL・品質チェック・ニュース収集・監査ログ・マーケットカレンダーなど、取引システムに必要な基盤処理を提供します。

---

## 概要

KabuSys は J-Quants や RSS 等の外部データソースから日本株関連データを取得し、DuckDB に保存・整形して戦略や実行層へ受け渡すためのモジュール群です。設計における主な方針は次のとおりです。

- API レート制御、リトライ、トークン自動リフレッシュを備えた J-Quants クライアント
- DuckDB を用いたスキーマ定義（Raw / Processed / Feature / Execution / Audit）
- 日次 ETL パイプライン（差分取得、バックフィル、品質チェック）
- RSS ベースのニュース収集（SSRF / XML Bomb 対策、トラッキング除去）
- 監査ログ（シグナル→注文→約定のトレーサビリティ）
- マーケットカレンダー管理（営業日判定、next/prev 営業日計算）

---

## 機能一覧

- J-Quants API クライアント（jquants_client）
  - 株価日足（OHLCV）、財務（四半期 BS/PL）、市場カレンダーの取得
  - レートリミット、リトライ、レンスポンスのページネーション対応
  - DuckDB への冪等保存（ON CONFLICT ... DO UPDATE）
- ETL パイプライン（data.pipeline）
  - 差分取得（最終取得日ベース）、backfill による後出し修正吸収
  - 日次 ETL 実行（calendar → prices → financials → 品質チェック）
- データ品質チェック（data.quality）
  - 欠損、スパイク、重複、日付整合性チェック
  - QualityIssue を返し、呼び出し側で扱える設計
- ニュース収集（data.news_collector）
  - RSS 取得、記事 ID（正規化 URL の SHA-256）の生成、前処理、DuckDB への保存
  - SSRF 対策、受信サイズ制限、XML 安全パーサ使用
  - 記事と銘柄コードの紐付け（news_symbols）
- スキーマ管理（data.schema）
  - DuckDB のスキーマ初期化（Raw / Processed / Feature / Execution）
  - 各種インデックス作成
- マーケットカレンダー管理（data.calendar_management）
  - 営業日判定、next/prev 営業日、期間内営業日取得
  - 夜間バッチ更新ジョブ
- 監査ログ（data.audit）
  - signal_events / order_requests / executions 等の監査テーブル初期化（UTC タイムスタンプ）

---

## セットアップ手順

1. リポジトリをクローン／コピー。

2. Python 仮想環境を作成・有効化（例）:

   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージをインストール（pip）:

   必須の主なパッケージ:
   - duckdb
   - defusedxml

   直接インストール例:

   ```bash
   pip install duckdb defusedxml
   ```

   ※プロジェクトに requirements.txt があればそれを使用してください。

4. 環境変数（.env）を準備:

   プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（CWD に依存せず、パッケージファイル位置からプロジェクトルートを探索）。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   必要な環境変数の例（.env）:

   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_api_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   DUCKDB_PATH=data/kabusys.duckdb          # 任意（デフォルト）
   SQLITE_PATH=data/monitoring.db           # 任意（デフォルト）
   KABUSYS_ENV=development                  # development | paper_trading | live
   LOG_LEVEL=INFO                           # DEBUG/INFO/WARNING/ERROR/CRITICAL
   ```

   - KABUSYS_ENV の有効値: development, paper_trading, live
   - LOG_LEVEL は上記のいずれかでなければ ValueError になります

---

## 使い方（主な例）

以下は Python REPL またはスクリプト内での利用例です。

- 設定取得

  ```python
  from kabusys.config import settings

  print(settings.jquants_refresh_token)  # 必須: 環境変数 JQUANTS_REFRESH_TOKEN
  print(settings.duckdb_path)            # Path オブジェクト（デフォルト data/kabusys.duckdb）
  print(settings.is_live)                # True/False
  ```

- DuckDB スキーマ初期化

  ```python
  from kabusys.data.schema import init_schema
  from kabusys.config import settings

  conn = init_schema(settings.duckdb_path)  # ファイル作成・ディレクトリ自動生成
  ```

- J-Quants トークン取得 / データ取得

  ```python
  from kabusys.data import jquants_client as jq

  id_token = jq.get_id_token()  # settings.jquants_refresh_token を使って取得
  quotes = jq.fetch_daily_quotes(id_token=id_token, date_from=date(2024,1,1), date_to=date(2024,1,31))
  # DuckDB に保存する場合
  saved = jq.save_daily_quotes(conn, quotes)
  ```

- 日次 ETL を実行する（差分取得＋品質チェック）

  ```python
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.data.schema import init_schema
  from kabusys.config import settings

  conn = init_schema(settings.duckdb_path)
  result = run_daily_etl(conn)  # デフォルトで今日を対象に実行
  print(result.to_dict())
  ```

- ニュース収集ジョブ

  ```python
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  # known_codes を渡すと記事内の 4 桁コード抽出→news_symbols に紐付けを行う
  known_codes = {"7203", "6758", "9432"}
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)  # {source_name: saved_count}
  ```

- 監査用スキーマの初期化（audit 層）

  ```python
  from kabusys.data.audit import init_audit_schema, init_audit_db
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  init_audit_schema(conn)  # 既存接続へ監査テーブルを追加
  # または監査専用 DB を作る場合
  audit_conn = init_audit_db("data/kabusys_audit.duckdb")
  ```

---

## 環境変数一覧（主要）

- JQUANTS_REFRESH_TOKEN (必須) : J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) : kabuステーション API のパスワード
- KABU_API_BASE_URL (任意) : kabu API ベース URL（デフォルト http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) : Slack Bot トークン（通知等で使用）
- SLACK_CHANNEL_ID (必須) : Slack チャネル ID
- DUCKDB_PATH (任意) : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH (任意) : SQLite（監視用途）パス（デフォルト data/monitoring.db）
- KABUSYS_ENV (任意) : 環境 ('development' | 'paper_trading' | 'live')（デフォルト development）
- LOG_LEVEL (任意) : ログレベル（'DEBUG','INFO','WARNING','ERROR','CRITICAL'）

注意: 自動 `.env` ロードはプロジェクトルートの検出に基づき行われ、.git または pyproject.toml が存在するディレクトリをルートとします。テスト等で自動ロードを避ける場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ディレクトリ構成

（リポジトリ内の主要ファイル／モジュール）

- src/
  - kabusys/
    - __init__.py
    - config.py                    — 環境変数／設定管理
    - data/
      - __init__.py
      - jquants_client.py          — J-Quants API クライアント（取得＋保存）
      - news_collector.py          — RSS ニュース収集・保存・銘柄抽出
      - schema.py                  — DuckDB スキーマ定義と初期化
      - pipeline.py                — ETL パイプライン（差分取得・品質チェック）
      - calendar_management.py     — マーケットカレンダー管理（営業日判定等）
      - audit.py                   — 監査ログ（signal/order/execution）
      - quality.py                 — データ品質チェック（欠損・スパイク・重複等）
    - strategy/
      - __init__.py                — 戦略関連（拡張用）
    - execution/
      - __init__.py                — 発注／実行関連（拡張用）
    - monitoring/
      - __init__.py                — 監視関連（拡張用）

---

## 運用上の注意

- J-Quants API のレート制限（120 req/min）を守る実装が組み込まれています。直接 HTTP クライアントを追加する場合は同様の配慮が必要です。
- DuckDB への挿入は冪等（ON CONFLICT）を想定していますが、外部からの直接操作やスキーマ変更で不整合が発生する可能性があるため品質チェックを定期実行してください。
- ニュース収集では外部からの悪意あるコンテンツ（XML Bomb、SSRF 等）に対する対策を実装していますが、運用環境での追加検証は推奨します。
- 本ライブラリは戦略ロジック・ブローカー接続の実装を含まず、インフラ／データ基盤部分を提供することを目的としています。実際の発注実装は安全性・冗長性を考慮して別途実装してください。

---

必要であれば、README に以下を追記できます：
- 開発（テスト）手順（pytest 等）
- CI/CD のセットアップ例
- 具体的な SQL スキーマの解説（テーブル毎の列説明）
- サンプルの Docker イメージ / systemd ジョブ／cron の設定例

ご希望があれば上記のいずれかを追加します。