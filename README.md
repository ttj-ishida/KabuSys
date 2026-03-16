# KabuSys

日本株自動売買システムのコアライブラリ（データ取得・ETL・品質チェック・監査ログなど）

このリポジトリは J-Quants API を用いた市場データの取得、DuckDB を用いたスキーマ管理と ETL パイプライン、データ品質チェック、監査ログの初期化機能などを提供します。戦略・発注ロジックは strategy/、execution/ モジュールに置く想定の骨組みを備えています。

バージョン: 0.1.0

---

## 主な機能

- J-Quants API クライアント
  - 日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーの取得
  - レート制限（120 req/min）の順守（固定間隔スロットリング）
  - リトライ（指数バックオフ）、401 時のトークン自動リフレッシュ
  - ページネーション対応、取得時刻（fetched_at）の記録（look-ahead bias 対策）
- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution 層のテーブル定義とインデックス
  - 冪等性を意識したテーブル初期化（CREATE IF NOT EXISTS 等）
- ETL パイプライン
  - 差分更新（最終取得日ベース）とバックフィル（デフォルト 3 日）
  - カレンダー先読み（デフォルト 90 日）
  - 各ステップを独立して実行し、障害時も他ステップは継続
- データ品質チェック
  - 欠損、主キー重複、株価スパイク（前日比閾値）、日付不整合（未来日・非営業日）を検出
  - 問題は QualityIssue の一覧として返却（error / warning）
- 監査ログ（audit）
  - signal_events / order_requests / executions の監査テーブルを初期化
  - 発注フローのトレーサビリティ（UUID 連鎖）、冪等キー、UTC タイムスタンプ

---

## 必要条件

- Python 3.10+
- 必要パッケージ（最低限）
  - duckdb
- 外部サービス（実運用時）
  - J-Quants のリフレッシュトークン
  - kabuステーション API パスワード（発注連携時）
  - Slack（通知用）ボット token / channel id

パッケージは各自の環境に合わせてインストールしてください。最低限のインストール例:

```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb
```

（ローカル開発用に pyproject.toml / requirements.txt を用意することを推奨します）

---

## 環境変数（設定項目）

設定は環境変数またはプロジェクトルートの `.env` / `.env.local` ファイルから自動読み込みされます（自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。

必須:
- JQUANTS_REFRESH_TOKEN - J-Quants のリフレッシュトークン
- KABU_API_PASSWORD - kabuステーション API パスワード
- SLACK_BOT_TOKEN - Slack ボットトークン
- SLACK_CHANNEL_ID - Slack チャンネル ID

任意（デフォルトあり）:
- KABU_API_BASE_URL - kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH - DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH - 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV - 実行環境（development / paper_trading / live、デフォルト: development）
- LOG_LEVEL - ログレベル（DEBUG / INFO / ...、デフォルト: INFO）

.env の例:

```
JQUANTS_REFRESH_TOKEN=xxxxxxx
KABU_API_PASSWORD=passwd
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（簡易）

1. リポジトリをクローンし、仮想環境を作成して依存ライブラリをインストールする
   - 例: duckdb のみを利用する場合は `pip install duckdb`
2. プロジェクトルートに `.env` を作成して必要な環境変数を設定する
3. DuckDB スキーマを初期化する（例は次節を参照）

---

## 初期化と使い方（コード例）

以下は Python REPL やスクリプトで行う基本的な操作例です。

- DuckDB スキーマ（全テーブル）を初期化する:

```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

# settings.duckdb_path は .env の DUCKDB_PATH を参照（なければ data/kabusys.duckdb）
conn = init_schema(settings.duckdb_path)
```

- 監査ログ（audit）テーブルを追加で初期化する:

```python
from kabusys.data.audit import init_audit_schema

# すでに init_schema で接続を取得している conn を渡す
init_audit_schema(conn)
```

- 日次 ETL を実行する（市場カレンダー・株価・財務を差分取得し品質チェックまで実行）:

```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)  # target_date を指定しなければ今日（ローカル日）を使用
print(result.to_dict())
```

- J-Quants から直接データをフェッチする例:

```python
from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes

token = get_id_token()
records = fetch_daily_quotes(id_token=token, date_from=date(2023,1,1), date_to=date(2023,1,31))
```

注意点:
- run_daily_etl では ETL の各ステップで例外が発生しても他ステップは継続します。結果の ETLResult.errors や quality_issues を確認して運用側で判断してください。
- デフォルトでは J-Quants API のレート制限に従うため、短時間に多数のリクエストを投げると待ちが発生します。

---

## 主要モジュールの説明

- kabusys.config
  - 環境変数読み込みと Settings クラス（設定の取得）
  - 自動的にプロジェクトルートの `.env` / `.env.local` を読み込む
- kabusys.data.jquants_client
  - J-Quants API との通信、トークン取得、fetch/save 関数
  - save_* 系関数は DuckDB に対して冪等に保存する
- kabusys.data.schema
  - DuckDB のスキーマ（DDL）と初期化関数 init_schema, get_connection
- kabusys.data.pipeline
  - 差分 ETL（run_prices_etl, run_financials_etl, run_calendar_etl, run_daily_etl）
  - 品質チェック呼び出し（quality モジュール）
- kabusys.data.quality
  - 欠損、重複、スパイク、日付不整合等の検査ロジック
- kabusys.data.audit
  - 監査ログ用テーブル定義・初期化（init_audit_schema / init_audit_db）
- kabusys.strategy / kabusys.execution / kabusys.monitoring
  - 将来的な戦略・発注・監視ロジックのプレースホルダ（現在は空 __init__）

---

## ディレクトリ構成

以下はコードベースの主要ファイル構成（抜粋）です。

- src/
  - kabusys/
    - __init__.py
    - config.py
    - execution/
      - __init__.py
    - strategy/
      - __init__.py
    - monitoring/
      - __init__.py
    - data/
      - __init__.py
      - jquants_client.py
      - schema.py
      - pipeline.py
      - audit.py
      - quality.py

（README.md やドキュメントが追加される想定でプロジェクトルートに .env.example, pyproject.toml 等を置くことを推奨します）

---

## 運用上の注意・トラブルシュート

- 環境変数が不足していると Settings プロパティが ValueError を投げます。特に JQUANTS_REFRESH_TOKEN などは必須です。
- J-Quants の API リクエストは内部で最大 3 回のリトライ（指数バックオフ）を行います。429 応答時は Retry-After ヘッダを尊重します。
- ID トークンはモジュールレベルでキャッシュされ、401 時に自動更新して 1 回リトライします。
- DuckDB のパスを ":memory:" にすればインメモリ DB になります（テスト用途に便利）。
- 自動で .env を読み込ませたくない場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時など）。

---

## 今後の拡張案

- strategy/、execution/ の具体的な実装（ポートフォリオ管理、発注ロジック、資金管理）
- Slack や監視システムとの通知連携（監査ログや ETL 結果の通知）
- CI 用のテスト・静的解析・型チェック設定（pyproject.toml、tox、pre-commit 等）
- requirements.txt / pyproject.toml による依存管理

---

もし README に追記したい使用例やデプロイ手順（Docker、Kubernetes、ジョブスケジューラ）などがあれば教えてください。必要に応じて日本語での例や運用手順を追加します。