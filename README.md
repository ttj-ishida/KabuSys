# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
J-Quants API や RSS フィードからデータを取得し、DuckDB に蓄積・品質チェック・監査ログを行うためのモジュール群を含みます。戦略・実行・モニタリングの基盤となる処理（ETL、カレンダー管理、ニュース収集、監査スキーマなど）を提供します。

---

## 主な特徴（機能一覧）

- 環境変数ベースの設定管理（.env 自動読み込み、必要な変数の検証）
- J-Quants API クライアント
  - 日次株価（OHLCV）、財務諸表、JPX マーケットカレンダーの取得
  - レート制限（120 req/min）を考慮したスロットリング
  - 再試行（指数バックオフ、最大 3 回）および 401 時のトークン自動リフレッシュ
  - 取得時刻（fetched_at）を UTC で記録して Look-ahead バイアスを低減
  - DuckDB へ冪等的に保存（ON CONFLICT DO UPDATE）
- ETL パイプライン
  - 差分更新、バックフィル、品質チェックを行う日次 ETL（run_daily_etl）
  - 市場カレンダー先読み・営業日調整機能
- ニュース収集（RSS）
  - RSS 取得 → 前処理（URL 除去・空白正規化）→ DuckDB へ冪等保存
  - URL 正規化（トラッキングパラメータ除去）による記事 ID 生成（SHA-256）
  - SSRF 対策、受信サイズ上限、gzip 解凍の安全対策
  - 記事と銘柄の紐付け（news_symbols）
- データ品質チェック
  - 欠損、スパイク（急騰・急落）、重複、日付不整合の検出
  - 問題は QualityIssue オブジェクトとして収集
- 監査ログ（Audit）
  - シグナル→発注→約定までトレース可能な監査テーブルを提供
  - 発注の冪等キー（order_request_id）や broker_execution_id 管理
- DuckDB スキーマ定義・初期化ユーティリティ
  - Raw / Processed / Feature / Execution / Audit の階層テーブル群
  - インデックス定義、初期化関数（init_schema / init_audit_schema）

---

## セットアップ手順

前提
- Python 3.10 以上（型ヒントに `|` 記法を使用）
- Git（任意）

1. リポジトリをクローン（既にコードがある場合は省略）
   ```
   git clone <repository-url>
   cd <repository-dir>
   ```

2. 仮想環境を作成・有効化
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージをインストール（最低限）
   ```
   pip install duckdb defusedxml
   ```
   （プロジェクト配布に requirements.txt / pyproject.toml があればそれを使用してください）

4. 環境変数の設定
   - プロジェクトルートの `.env` / `.env.local` を自動的に読み込みます（環境変数より後に読み込まれる挙動や override は config モジュールで管理）。
   - 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   必須の環境変数（最低限）
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD: kabuステーション API のパスワード
   - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
   - SLACK_CHANNEL_ID: Slack チャンネル ID

   任意 / デフォルトあり
   - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）

   例 `.env`（参考）
   ```
   JQUANTS_REFRESH_TOKEN=xxxxx
   KABU_API_PASSWORD=yyyyy
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. データベーススキーマの初期化（最初に一度だけ）
   Python コンソールまたはスクリプトで：
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")  # ファイルパスまたは ":memory:"
   conn.close()
   ```
   監査ログ用スキーマ（Audit）を別 DB に作る場合：
   ```python
   from kabusys.data.audit import init_audit_db
   conn_audit = init_audit_db("data/kabusys_audit.duckdb")
   conn_audit.close()
   ```

---

## 使い方（主要な API と実行例）

以下は代表的な利用例です。実運用ではログやエラーハンドリング、ジョブスケジューラ（cron / systemd timer / Airflow など）を組み合わせて運用してください。

- 設定値の参照
  ```python
  from kabusys.config import settings
  print(settings.jquants_refresh_token)
  print(settings.is_live, settings.env, settings.log_level)
  ```

- DuckDB スキーマ初期化（既定パス使用）
  ```python
  from kabusys.config import settings
  from kabusys.data.schema import init_schema

  conn = init_schema(settings.duckdb_path)
  ```

- 日次 ETL を実行する（株価・財務・カレンダー取得 + 品質チェック）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.data.schema import get_connection
  from datetime import date

  conn = get_connection("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- 市場カレンダーの夜間更新ジョブ
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  saved = calendar_update_job(conn)
  print("saved calendar rows:", saved)
  ```

- ニュース収集（RSS）を実行して DuckDB に保存
  ```python
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  # sources を省略するとデフォルトの RSS ソースを使用
  # known_codes に有効な銘柄コードセットを渡すと記事→銘柄紐付け処理が走る
  known_codes = {"7203", "6758", "9984"}
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)  # {source_name: saved_count, ...}
  ```

- J-Quants の id_token を明示的に取得する（必要に応じて）
  ```python
  from kabusys.data.jquants_client import get_id_token
  token = get_id_token()  # settings.jquants_refresh_token を使用
  ```

- 品質チェックを単体で実行
  ```python
  from kabusys.data.quality import run_all_checks
  from kabusys.data.schema import get_connection
  from datetime import date

  conn = get_connection("data/kabusys.duckdb")
  issues = run_all_checks(conn, target_date=date.today())
  for i in issues:
      print(i.check_name, i.severity, i.detail)
  ```

---

## 環境変数の自動ロード挙動（補足）

- パッケージの config モジュールは、プロジェクトルート（.git または pyproject.toml があるディレクトリ）を探索して `.env` と `.env.local` を自動的に読み込みます。
- 読み込み順序: OS 環境変数 > .env.local > .env（.env.local の方が優先）
- 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時などに有用）。

---

## ディレクトリ構成（主要ファイル）

（リポジトリの src/kabusys 以下を抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理
  - data/
    - __init__.py
    - schema.py              — DuckDB スキーマ定義・初期化
    - jquants_client.py      — J-Quants API クライアント（取得・保存）
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - news_collector.py      — RSS ニュース収集・保存
    - calendar_management.py — マーケットカレンダーの管理・ユーティリティ
    - quality.py             — データ品質チェック
    - audit.py               — 監査ログ（signal / order_request / executions）
  - strategy/                 — 戦略用モジュール（骨組み）
  - execution/                — 発注・ブローカー連携（骨組み）
  - monitoring/               — 監視関連モジュール（骨組み）

各モジュールは分離されており、テスト容易性を考え id_token の注入や DB 接続の外部注入が可能です。

---

## 運用上の注意

- DuckDB はファイルロックや同時書き込みに注意が必要です。複数プロセスからの同時書き込みは運用設計（排他制御）を行ってください。
- J-Quants の API レート制限と再試行ロジックは実装済みですが、実運用ではさらにバックオフ方針や監視を整備してください。
- ニュース収集は外部 URL にアクセスします。news_collector には SSRF 対策や受信サイズ制限など安全策を入れていますが、社内ポリシーに従って実行環境のネットワーク制御を行ってください。
- 監査ログは削除しない前提で設計されています。運用時はストレージ確保とログ保全を検討してください。

---

以上がこのコードベースの簡易 README です。必要であれば、インストール用の requirements ファイル、実行用の CLI スクリプト例、CI／デプロイ手順、より詳細な運用ガイド（ログ・アラート設定、バックアップ方針など）を追記します。どの部分を拡張したいか教えてください。