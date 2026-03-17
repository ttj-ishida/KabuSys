# KabuSys

日本株自動売買基盤（KabuSys）の軽量ライブラリ。J-Quants / kabuステーション 等の外部データ・ブローカーと連携して、データ収集（ETL）、品質チェック、ニュース収集、監査ログ／スキーマ管理を行うためのコンポーネント群を提供します。

主な設計方針：
- データ取得の冪等性（DuckDB へ ON CONFLICT / DO UPDATE）
- API レート制限・リトライ・トークン自動リフレッシュ対応
- Look-ahead bias 回避のため取得時刻（fetched_at）を記録
- ニュース収集での SSRF / XML Bomb 等のセキュリティ対策
- 品質チェックを通じたデータ健全性の自動検出

---

## 機能一覧

- 環境変数 / .env 自動読み込みと設定ラッパー（kabusys.config）
  - 自動読み込みはプロジェクトルート（.git / pyproject.toml）を基準に行われます。
  - 必須環境変数チェック（未設定時に ValueError を投げるプロパティ群）。
  - 自動ロードを無効化するフラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`

- J-Quants API クライアント（kabusys.data.jquants_client）
  - 株価日足（OHLCV）、財務データ、JPX マーケットカレンダーの取得。
  - レート制限（120 req/min）対応（固定間隔スロットリング）。
  - リトライ（指数バックオフ）、401 時トークン自動リフレッシュ。
  - DuckDB へ保存するための save_* 関数（冪等的に保存）。

- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新ロジック（最終取得日からの差分、バックフィル）。
  - 日次 ETL エントリ（run_daily_etl）でカレンダー・株価・財務の取得〜品質チェックまで実行。
  - 品質チェック（欠損・スパイク・重複・日付不整合）を quality モジュール経由で実行。

- DuckDB スキーマ定義 / 初期化（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層のテーブル定義。
  - init_schema() による冪等初期化と接続取得。

- ニュース収集（kabusys.data.news_collector）
  - RSS 取得・前処理・記事ID生成（URL 正規化 → SHA-256 の先頭32文字）・DB 保存。
  - SSRF / プライベートアドレス・gzip 上限・XML パース安全化（defusedxml）等の対策。
  - 銘柄コード抽出と news_symbols 保存ロジック。

- マーケットカレンダー管理（kabusys.data.calendar_management）
  - 営業日判定（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
  - 夜間カレンダー更新ジョブ（calendar_update_job）による差分更新。

- 監査（audit）モジュール（kabusys.data.audit）
  - シグナル〜発注〜約定のトレーサビリティ用スキーマと初期化ヘルパー。
  - 全ての TIMESTAMP を UTC で保存する設定を適用可能。

---

## セットアップ手順

1. 必要環境
   - Python 3.9+（typing の一部機能を想定）
   - OS: 任意（DuckDB が動作する環境）

2. 仮想環境（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 依存パッケージのインストール
   必要最小限の依存：
   - duckdb
   - defusedxml

   pip 例:
   ```
   pip install duckdb defusedxml
   ```

   （実運用では logging、slack SDK、requests 等の追加依存が必要になる場合があります。プロジェクトに合わせて requirements を管理してください。）

4. パッケージを開発インストール（プロジェクト直下に setup/pyproject がある想定）
   ```
   pip install -e .
   ```

5. 環境変数の設定
   - プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD を設定すれば読み込み無効化）。
   - 最低限必要な環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - 任意（デフォルト値あり）:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト development
     - LOG_LEVEL (DEBUG/INFO/...) — デフォルト INFO
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）

   サンプル `.env`:
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token_here
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（基本例）

以下は簡単な Python スクリプト例です。実行前に依存と環境変数を整えてください。

1. DuckDB スキーマ初期化
   ```python
   from kabusys.data import schema

   conn = schema.init_schema("data/kabusys.duckdb")
   # conn は duckdb.DuckDBPyConnection
   ```

2. 日次 ETL を実行（J-Quants トークンは settings から利用）
   ```python
   from kabusys.data import pipeline
   from kabusys.data import schema
   from datetime import date

   conn = schema.get_connection("data/kabusys.duckdb")  # 既存 DB に接続
   result = pipeline.run_daily_etl(conn)  # target_date を省略すると今日
   print(result.to_dict())
   ```

3. RSS ニュース収集と保存
   ```python
   from kabusys.data.news_collector import run_news_collection
   from kabusys.data import schema

   conn = schema.get_connection("data/kabusys.duckdb")
   # known_codes を渡すと記事と銘柄の紐付けまで実行
   res = run_news_collection(conn, known_codes={"7203","6758"})
   print(res)  # {source_name: 新規保存件数, ...}
   ```

4. カレンダー更新ジョブ（夜間バッチ想定）
   ```python
   from kabusys.data.calendar_management import calendar_update_job
   from kabusys.data import schema

   conn = schema.get_connection("data/kabusys.duckdb")
   saved = calendar_update_job(conn)
   print(f"saved={saved}")
   ```

5. 監査スキーマの初期化（監査専用DBまたは既存conn）
   ```python
   from kabusys.data.audit import init_audit_db, init_audit_schema
   from kabusys.data import schema

   # 1) 監査専用DBを作る
   audit_conn = init_audit_db("data/audit.duckdb")

   # 2) 既存の conn に監査スキーマを追加する場合
   conn = schema.get_connection("data/kabusys.duckdb")
   init_audit_schema(conn, transactional=True)
   ```

6. J-Quants の id_token を手動取得（テスト等で）
   ```python
   from kabusys.data.jquants_client import get_id_token
   token = get_id_token()  # settings.jquants_refresh_token を使用
   ```

---

## 運用上の注意 / ポイント

- J-Quants の API レート制限（120 req/min）を守るため、jquants_client は内部でスロットリングしています。大量データを取得する際は実行頻度に注意してください。
- jquants_client は 401 を検知したらリフレッシュトークンを使って自動で id_token を再取得し1回リトライします。
- news_collector は RSS の安全な処理（defusedxml, SSRF 対策, gzip サイズチェック 等）を行いますが、外部フィードの扱いには注意してください（公開フィードの変更など）。
- DuckDB ファイルはデフォルトで data/kabusys.duckdb に作成されます。運用ではバックアップ・排他・権限制御を検討してください。
- 環境（KABUSYS_ENV）により本番（live）/ペーパー（paper_trading）等の挙動分岐を行える設計です。実際の発注ロジックは execution/strategy モジュール側で実装されます（このコードベースではプレースホルダが含まれています）。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py (パッケージメタ情報)
  - config.py (環境変数 / 設定管理)
  - data/
    - __init__.py
    - jquants_client.py (J-Quants API クライアント、保存ロジック)
    - news_collector.py (RSS 収集・前処理・DB保存)
    - schema.py (DuckDB スキーマ定義・初期化)
    - pipeline.py (ETL パイプライン: 日次 ETL 等)
    - calendar_management.py (マーケットカレンダー管理)
    - audit.py (監査ログ用スキーマ／初期化)
    - quality.py (データ品質チェック)
  - strategy/
    - __init__.py (戦略モジュール用プレースホルダ)
  - execution/
    - __init__.py (発注／約定処理用プレースホルダ)
  - monitoring/
    - __init__.py (モニタリング用プレースホルダ)

各モジュールはドキュメント文字列と設計意図が豊富に書かれているため、内部実装を参照して用途拡張・統合が行えます。

---

もし README に追記したい内容（例：CI / テスト手順、具体的な Slack 通知の実装案、kabuステーション連携サンプルなど）があれば教えてください。必要に応じてサンプルスクリプトや docker-compose 設定のテンプレートも作成できます。