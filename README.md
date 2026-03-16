# KabuSys

日本株向け自動売買プラットフォームのコアライブラリ（プロトタイプ）

バージョン: 0.1.0

概要
----
KabuSys は日本株のデータ取得・ETL、品質チェック、監査ログ、実行/戦略レイヤの基盤となるライブラリ群です。J-Quants API から市場データ（株価日足・財務データ・JPX マーケットカレンダー）を取得し、DuckDB に冪等的に保存、品質チェックを実施する ETL パイプラインを提供します。発注や監査ログのスキーマも定義しており、自動売買システムの上位レイヤ（戦略・発注実行・監視）と連携するための土台を目的としています。

主な機能
--------
- J-Quants API クライアント
  - 株価日足（OHLCV）、財務（四半期 BS/PL）、JPX カレンダー取得
  - レート制限対応（120 req/min）、リトライ（指数バックオフ）、401 時の自動トークンリフレッシュ
  - 取得日時（fetched_at）を UTC で記録
  - ページネーション対応
- DuckDB スキーマ定義・初期化
  - Raw / Processed / Feature / Execution 層を含むテーブル群
  - インデックス、制約、外部キーを含むDDL（冪等）
  - 監査用テーブル（signal_events / order_requests / executions）と初期化ユーティリティ
- ETL パイプライン
  - 差分更新（最終取得日に基づく自動算出 + バックフィル）
  - 市場カレンダーの先読み（lookahead）
  - ETL 完了後の品質チェック（欠損・スパイク・重複・日付不整合）
  - ETL 結果を ETLResult dataclass で返却
- データ品質チェック
  - 欠損データ検出（OHLC）
  - 異常値（スパイク）検出（前日比閾値）
  - 主キー重複検出
  - 日付不整合（未来日・非営業日データ）
- 設定管理
  - .env / .env.local 自動読み込み（プロジェクトルートを基準に検出）
  - 必須環境変数の明示と検査
  - 環境モード（development / paper_trading / live）とログレベル設定

セットアップ
--------
前提
- Python 3.10 以上（型ヒントに `X | None` を使用）
- pip

手順（開発環境）
1. リポジトリをクローン:
   ```bash
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境を作成・有効化:
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS/Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージをインストール:
   - ここで必須の外部パッケージは duckdb などです。セットアップ済みの pyproject.toml / requirements.txt があればそちらを使用してください。
   ```bash
   pip install duckdb
   # もしパッケージとしてインストールする場合:
   pip install -e .
   ```

環境変数（必須）
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD      : kabuステーション API のパスワード（必須）
- SLACK_BOT_TOKEN        : Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID       : Slack チャンネル ID（必須）

任意 / デフォルトあり
- KABUSYS_ENV            : development / paper_trading / live（デフォルト: development）
- LOG_LEVEL              : DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- KABUS_API_BASE_URL     : kabu API の base URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH            : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH            : 監視用 SQLite（デフォルト: data/monitoring.db）

自動 .env 読み込み
- パッケージは起動時にプロジェクトルート（.git または pyproject.toml があるディレクトリ）を探索し、`.env` と `.env.local` を順に読み込みます。
- OS 環境変数が優先され、`.env.local` は`.env` を上書きします。
- 自動ロードを無効化するには環境変数を設定:
  ```bash
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```

使い方（基本例）
----------------

1) DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
# またはメモリ DB:
# conn = init_schema(":memory:")
```

2) 監査ログ（オプション）を追加する
```python
from kabusys.data.audit import init_audit_schema

init_audit_schema(conn)
```

3) 単発 ETL（当日分）
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

4) 個別ジョブ（例: 株価差分ETL）
```python
from kabusys.data.pipeline import run_prices_etl
from datetime import date

fetched, saved = run_prices_etl(conn, target_date=date.today())
print(f"fetched={fetched}, saved={saved}")
```

5) J-Quants クライアント直接利用
```python
from kabusys.data import jquants_client as jq
from kabusys.config import settings
import duckdb

# id_token を自前で取得（settings.jquants_refresh_token を使用）
id_token = jq.get_id_token()

# 日足取得
records = jq.fetch_daily_quotes(id_token=id_token, date_from=date(2024,1,1), date_to=date(2024,3,1))

# 保存
conn = duckdb.connect("data/kabusys.duckdb")
jq.save_daily_quotes(conn, records)
```

設定（コードでの参照）
- 設定は `kabusys.config.settings` オブジェクト経由で取得できます。
  - settings.jquants_refresh_token
  - settings.kabu_api_password
  - settings.kabu_api_base_url
  - settings.slack_bot_token
  - settings.slack_channel_id
  - settings.duckdb_path
  - settings.sqlite_path
  - settings.env / settings.log_level / settings.is_live / settings.is_paper / settings.is_dev

ディレクトリ構成
----------------
以下はソースの主要ファイル構成（src 配下）です:

- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py         # J-Quants API クライアント（取得 + 保存）
    - schema.py                 # DuckDB スキーマ定義・初期化
    - pipeline.py               # ETL パイプライン（差分更新・品質チェック）
    - audit.py                  # 監査ログ（signal / order_request / executions）
    - quality.py                # データ品質チェック
  - strategy/
    - __init__.py
  - execution/
    - __init__.py
  - monitoring/
    - __init__.py

設計上のポイント（注目点）
------------------------
- 冪等性: DuckDB への保存は ON CONFLICT DO UPDATE を使い、再実行による重複を避けます。
- トレーサビリティ: audit モジュールでシグナル→発注→約定まで UUID 連鎖を保つ設計。
- レート制限と安定性: J-Quants クライアントは 120 req/min に合わせた レートリミッタ と、リトライ/バックオフ、401 時のトークンリフレッシュを備えています。
- 品質チェック: ETL 後に各種チェックを走らせ、問題は QualityIssue オブジェクトとして集約されます（致命的な問題は呼び出し元で判断）。

トラブルシューティング
---------------------
- 環境変数が足りない（ValueError）
  - settings のプロパティは必須 env が未設定だと ValueError を投げます。`.env.example` を参考に設定してください。
- 自動 .env 読み込みを無効化したい場合:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
- DuckDB 接続エラー
  - パスの親ディレクトリが存在しない場合、schema.init_schema は自動でディレクトリを作成しますが、パーミッション等に注意してください。

拡張ポイント / 次の作業
-----------------------
- strategy/ と execution/ を実装して、シグナル生成・発注実行の具体ロジックを組み込む
- 監視（monitoring）モジュールを拡充して Slack 通知・メトリクス収集を行う
- 単体テスト・CI の整備（自動 .env 読み込みをテストで無効化する仕組みあり）

ライセンス / コントリビューション
---------------------------------
（必要に応じてライセンスや貢献ルールをここに記載してください）

以上。必要であれば README にサンプル .env.example やコマンドラインツールの使い方を追記します。どの部分を詳しく書き足しましょうか？