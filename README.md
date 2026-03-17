# KabuSys

KabuSys は日本株向けのデータプラットフォーム兼自動売買基盤の一部を実装したライブラリです。  
J-Quants API や RSS フィードを使ったデータ収集、DuckDB ベースのスキーマ管理、ETL パイプライン、品質チェック、監査ログ機能などを備え、戦略層 / 実行層と連携して自動売買システムを構築するための基盤を提供します。

---

## 主な機能

- 環境変数 / .env の自動読み込みと設定管理（kabusys.config）
  - プロジェクトルート（.git または pyproject.toml）を基準に .env/.env.local を読み込む
  - 必須設定を Settings 経由で取得
  - 自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能

- J-Quants API クライアント（kabusys.data.jquants_client）
  - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX カレンダー取得
  - レート制限（120 req/min）・リトライ（指数バックオフ）・トークン自動リフレッシュ対応
  - 取得時刻（fetched_at）の記録、DuckDB への冪等保存（ON CONFLICT）

- RSS ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得、URL 正規化（トラッキング除去）、記事 ID のハッシュ化（SHA-256 の先頭32文字）
  - defusedxml による安全な XML パース、SSRF 対策、応答サイズ制限
  - DuckDB へ冪等保存（INSERT ... RETURNING）

- DuckDB スキーマ & 初期化（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層のテーブル定義
  - インデックス、外部キー、初期化ヘルパー（init_schema, get_connection）

- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新（最終取得日からの差分）、バックフィル、カレンダー先読み
  - 品質チェック（欠損・スパイク・重複・日付不整合）との連携
  - 日次 ETL エントリ（run_daily_etl）

- マーケットカレンダー管理（kabusys.data.calendar_management）
  - 営業日判定・前後営業日検索・期間内営業日の列挙
  - 夜間バッチによる calendar 更新ジョブ（calendar_update_job）

- データ品質チェック（kabusys.data.quality）
  - 欠損データ、スパイク検出、重複、日付不整合の検出
  - QualityIssue を返し、重大度に応じて呼び出し元が対応

- 監査ログ（kabusys.data.audit）
  - シグナル → 発注要求 → 約定 のトレーサビリティ（UUID 連鎖）
  - 発注ログ・約定ログのテーブル初期化（init_audit_schema / init_audit_db）
  - すべての TIMESTAMP は UTC 保存

---

## 動作要件

- Python 3.10 以上（| 型注釈や最新構文を使用）
- 主要依存ライブラリ（例）
  - duckdb
  - defusedxml
- 標準ライブラリで urllib を使用（追加 HTTP クライアントは不要）

（実際のプロジェクトでは requirements.txt / pyproject.toml に依存を明示してください）

---

## セットアップ手順

1. リポジトリをクローン（あるいはパッケージを取得）
   ```
   git clone <this-repo>
   cd <this-repo>
   ```

2. 仮想環境を作成して有効化
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存関係をインストール
   - pyproject.toml / requirements.txt がある場合はそれに従う。最低限 duckdb と defusedxml を入れてください。
   ```
   pip install duckdb defusedxml
   # またはローカルパッケージを editable install
   pip install -e .
   ```

4. 環境変数を設定
   - 必須環境変数（例）
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD — kabu ステーション API パスワード
     - SLACK_BOT_TOKEN — Slack 通知用トークン
     - SLACK_CHANNEL_ID — Slack チャンネル ID
   - 任意 / デフォルト
     - KABUSYS_ENV （development / paper_trading / live、デフォルト development）
     - KABU_API_BASE_URL （デフォルト http://localhost:18080/kabusapi）
     - DUCKDB_PATH （デフォルト data/kabusys.duckdb）
     - SQLITE_PATH （デフォルト data/monitoring.db）
   - プロジェクトルートに .env/.env.local を置くと自動ロードされます（起動時に自動で読み込み）。
   - 自動ロードを無効にする場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

   .env の例:
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456789
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. DuckDB スキーマを初期化
   Python REPL やスクリプトから:
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   # 必要なら監査スキーマを追加
   from kabusys.data.audit import init_audit_schema
   init_audit_schema(conn)
   ```

---

## 使い方（簡単な例）

- 日次 ETL を実行する（日次の株価・財務・カレンダーの取得と品質チェック）
  ```python
  from kabusys.data.schema import get_connection, init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")  # まだ初期化していなければ init_schema を使う
  result = run_daily_etl(conn)
  print(result.to_dict())
  ```

- ニュース収集ジョブを実行する
  ```python
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import get_connection, init_schema

  conn = init_schema("data/kabusys.duckdb")
  # known_codes に有効な銘柄コードのセットを渡すと銘柄紐付けを行う
  saved = run_news_collection(conn, known_codes={"7203","6758"})
  print(saved)
  ```

- J-Quants の株価を直接取得する（テスト用）
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes
  # id_token を渡さないと内部で refresh してキャッシュを使う
  records = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  print(len(records))
  ```

- カレンダー更新バッチ
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  conn = init_schema("data/kabusys.duckdb")
  saved = calendar_update_job(conn)
  print(f"saved: {saved}")
  ```

- 監査ログの初期化（独立 DB として）
  ```python
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit.duckdb")
  ```

---

## ディレクトリ構成（主要ファイル）

（抜粋: src/kabusys 以下）

- __init__.py
  - パッケージのバージョンと公開モジュール一覧

- config.py
  - 環境変数と Settings クラス、自動 .env ロードロジック

- data/
  - __init__.py
  - jquants_client.py
    - J-Quants API クライアント、取得・保存ロジック（fetch_* / save_*）
  - news_collector.py
    - RSS 取得・前処理・DuckDB 保存・銘柄抽出
  - schema.py
    - DuckDB スキーマ定義と init_schema / get_connection
  - pipeline.py
    - ETL パイプライン（run_daily_etl、run_prices_etl 等）
  - calendar_management.py
    - market_calendar の管理、営業日判定、calendar_update_job
  - audit.py
    - 監査用テーブル定義、init_audit_schema / init_audit_db
  - quality.py
    - データ品質チェックと run_all_checks

- strategy/
  - __init__.py
  - （戦略関連コードを格納する想定ディレクトリ）

- execution/
  - __init__.py
  - （発注 / ブローカー連携に関するコードを配置する想定ディレクトリ）

- monitoring/
  - __init__.py
  - （監視・メトリクス系のコードを配置する想定ディレクトリ）

---

## 注意点・運用上のヒント

- 環境変数管理
  - 自動で .env をロードしますが、本番環境では OS 環境変数で管理することを推奨します。
  - 自動ロードをテストで無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

- DB（DuckDB）運用
  - デフォルトは file-based DuckDB（data/kabusys.duckdb）。バックアップや世代管理を行ってください。
  - 大量データの一括 INSERT はチャンク化（news_collector 等）によりメモリと SQL 長を制御しています。

- セキュリティ
  - RSS の取得では defusedxml を使用し、SSRF 対策や応答サイズ制限を実施しています。
  - 外部 API の認証情報は厳重に管理してください（トークンは環境変数で）。

- ログ・監査
  - audit モジュールはシグナルから約定までのトレーサビリティを提供します。実運用では全てのイベントを監査テーブルへ必ず永続化する方針が望ましいです。

---

## 今後の拡張候補

- kabu ステーション（ブローカー）向けの実注文送信・WebSocket ステータス受信モジュールの実装
- Slack 通知やモニタリングダッシュボードの統合
- 戦略実装例（リスク管理・ポートフォリオ最適化）
- CI による DB スキーマ検証・品質チェックの自動化

---

README に記載されていない細かな使い方や API の挙動については、各モジュールの docstring を参照してください。必要であれば README に入れてほしい詳細（例: 環境変数の完全一覧、具体的な運用手順、サンプル cron 設定 など）を教えてください。