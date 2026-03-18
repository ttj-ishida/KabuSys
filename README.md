# KabuSys

KabuSys は日本株の自動売買プラットフォーム向けに設計されたデータ取得・ETL・監査基盤のライブラリ群です。J-Quants API や RSS フィードからのデータ収集、DuckDB を使ったスキーマ定義・永続化、データ品質チェック、監査ログ（発注→約定のトレーサビリティ）など、運用に必要な基盤処理を提供します。

---

## 主要な機能

- J-Quants API クライアント
  - 日次株価（OHLCV）、四半期財務データ、JPX マーケットカレンダーの取得
  - レートリミット遵守、リトライ（指数バックオフ）、トークン自動リフレッシュ
  - 取得時刻（fetched_at）の記録で Look-ahead Bias を防止

- RSS ニュース収集
  - RSS フィードから記事を取得し正規化して DuckDB に保存
  - URL 正規化・追跡パラメータ除去、SSRF対策、XML 攻撃対策（defusedxml）、受信サイズ制限
  - 記事 → 銘柄コード紐付け（既知銘柄セットを利用）

- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution / Audit 層のテーブル定義と初期化
  - 冪等に実行できる DDL（IF NOT EXISTS）とインデックス定義

- ETL パイプライン
  - 差分取得（最終取得日＋バックフィル）、保存（ON CONFLICT）、品質チェックの実行
  - 市場カレンダー考慮による営業日調整、品質チェック（欠損、スパイク、重複、日付不整合）

- 監査ログ（Audit）
  - シグナル → 発注要求 → 約定のトレーサビリティ用テーブル群
  - 発注の冪等性（order_request_id）やステータス管理、UTC タイムスタンプ固定

- 品質チェック（quality）
  - 欠損データ、スパイク（前日比）、重複、未来日・非営業日データ検出

---

## 必要条件

- Python 3.10 以上（PEP 604 型注釈等を使用）
- 必要パッケージ（最低限）
  - duckdb
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS フィード）

実際のプロジェクトでは依存関係を requirements.txt / pyproject.toml で管理してください。

---

## セットアップ手順

1. リポジトリをクローンしてワークディレクトリに入る

   ```bash
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境を作成して有効化（任意）

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール

   例（最低限）:

   ```bash
   pip install duckdb defusedxml
   ```

   実運用ではロガーや HTTP クライアントなど他パッケージも追加する想定です。

4. 環境変数を設定

   プロジェクトルートの `.env` / `.env.local` を用意するか、OS 環境変数で設定します。自動読み込み機能は package 内の `kabusys.config` によりプロジェクトルート（.git または pyproject.toml を基準）から `.env` を読み込みます。自動ロードを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   必須の環境変数:
   - JQUANTS_REFRESH_TOKEN（J-Quants のリフレッシュトークン）
   - KABU_API_PASSWORD（kabuステーション API 用パスワード）
   - SLACK_BOT_TOKEN（Slack 通知用、必要な場合）
   - SLACK_CHANNEL_ID（Slack 通知用、必要な場合）

   オプション（デフォルトがあるものや動作に影響するもの）:
   - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）

   .env のフォーマットは一般的な KEY=VALUE です。`kabusys.config` はクォートの扱いやコメントの処理に対応します。

---

## 使い方（基本例）

以下はライブラリを使った典型的な操作例です。実際はアプリケーション側でログ設定・例外処理を追加してください。

- DuckDB スキーマ初期化

  ```python
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")  # ファイルがなければ親ディレクトリを作成
  ```

- 日次 ETL の実行（株価・財務・カレンダー取得 + 品質チェック）

  ```python
  from kabusys.data.schema import get_connection
  from kabusys.data.pipeline import run_daily_etl

  conn = get_connection("data/kabusys.duckdb")
  result = run_daily_etl(conn)  # 戻り値は ETLResult
  print(result.to_dict())
  ```

- ニュース収集ジョブの実行

  ```python
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")

  # known_codes: 銘柄コード抽出に使用する有効コード集合（例: 既存銘柄リスト）
  known_codes = {"7203", "6758", "9984"}

  results = run_news_collection(conn, known_codes=known_codes)
  print(results)  # {source_name: 新規保存件数}
  ```

- 監査ログテーブルの初期化（監査専用DBを作る場合）

  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  ```

- J-Quants からのデータ取得（直接呼び出し）

  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token

  id_token = get_id_token()  # settings からリフレッシュトークンを参照して取得
  records = fetch_daily_quotes(id_token=id_token, date_from=date(2024,1,1), date_to=date(2024,1,31))
  ```

---

## 環境変数と自動 .env 読み込み挙動

- パッケージロード時に `.git` または `pyproject.toml` を持つ親ディレクトリをプロジェクトルートとみなし、そのルートにある `.env` と `.env.local` を読み込みます。
  - 読み込み優先度: OS 環境変数 > .env.local > .env
  - `.env.local` は .env の上書き（override=True）
- 自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定
- 必須環境変数が欠けている場合、Settings のプロパティ読み出し時に ValueError が発生します（例: JQUANTS_REFRESH_TOKEN）

---

## ディレクトリ構成（概要）

プロジェクトの主要モジュールは src/kabusys 以下に配置されています。主なファイルと役割は以下の通りです。

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数と Settings 管理、.env 自動ロード
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（fetch / save / 認証 / レート制御 / リトライ）
    - news_collector.py
      - RSS フィード収集 → raw_news 保存、銘柄抽出、SSRF/ZIP/XML 対策
    - schema.py
      - DuckDB スキーマ定義（Raw / Processed / Feature / Execution）と初期化
    - pipeline.py
      - ETL パイプライン（差分取得 / 保存 / 品質チェック）
    - calendar_management.py
      - マーケットカレンダー管理、営業日判定、夜間更新ジョブ
    - audit.py
      - 監査ログ（signal_events / order_requests / executions）と初期化
    - quality.py
      - データ品質チェック（欠損 / スパイク / 重複 / 日付不整合）
  - strategy/
    - __init__.py
    - （戦略関連モジュールを格納する想定）
  - execution/
    - __init__.py
    - （発注・ブローカー連携などを格納する想定）
  - monitoring/
    - __init__.py
    - （モニタリング・メトリクス関連を格納する想定）

---

## ロギング / エラーハンドリング

- 各モジュールは Python 標準 logging を利用しており、LOG_LEVEL 環境変数で制御できます（Settings.log_level）。
- ETL や収集処理は個々のステップで例外を捕捉して継続する設計（Fail-Fast ではない）。ETLResult や戻り値でエラー状況を確認してください。

---

## 運用上の注意点

- J-Quants の API レート制限（120 req/min）を厳守する必要があります。ライブラリは固定間隔スロットリングで対応していますが、複数プロセスから同時に呼ぶ場合は追加の調整が必要です。
- DuckDB のファイルアクセスはプロセス間での排他に注意してください。複数プロセスで同一ファイルを扱う際は運用設計を検討してください。
- ニュース収集では外部リソースにアクセスするため SSRF 対策や受信サイズ制限などの安全対策を講じていますが、追加のセキュリティ要件がある場合は更なる検討をしてください。

---

## 今後の拡張候補

- strategy / execution 層の実装（ポートフォリオ最適化・レバレッジ管理・ブローカー実装）
- Slack 通知や監視ダッシュボードとの統合
- テスト用モックや CI パイプラインの追加
- requirements.txt / pyproject.toml による依存管理

---

README はここまでです。必要であれば、セットアップスクリプト例、より詳細な運用手順、サンプル .env.example の作成、あるいは strategy/execution レイヤーの設計案を追加で作成します。どれを優先しますか？