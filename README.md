# KabuSys

日本株向けの自動売買プラットフォーム向けユーティリティ群。  
データ取得（J-Quants API）、DuckDB ベースのスキーマ定義・初期化、ETL パイプライン、データ品質チェック、監査ログ定義などを含むライブラリ群です。

主な想定用途は「日本株データの継続的な取得・保存・検査」を行い、戦略・発注・監視コンポーネントへデータを提供することです。

---

## 主な機能

- J-Quants API クライアント
  - 株価日足（OHLCV）・四半期財務データ・JPX マーケットカレンダー取得
  - レート制限（120 req/min）対応、リトライ（指数バックオフ）、401 時の自動トークンリフレッシュ
  - ページネーション対応、取得時刻（fetched_at）を UTC で記録

- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution / Audit（監査）を含む包括的なテーブル定義
  - 冪等なテーブル作成（CREATE IF NOT EXISTS）・インデックス定義

- ETL パイプライン
  - 差分更新（最終取得日からの差分のみ取得）、バックフィル機能
  - 市場カレンダーの先読み（デフォルト 90 日）
  - 品質チェック（欠損・スパイク・重複・日付整合性）
  - ETL 結果を ETLResult として返却（品質問題やエラーを収集）

- データ品質チェック
  - 欠損（OHLC）検出、主キー重複、前日比スパイク、未来日付・非営業日データ検出
  - 問題は QualityIssue オブジェクトとして収集（severity: error / warning）

- 監査ログ（Audit）
  - signal -> order_request -> executions へ至るトレーサビリティ用テーブル群
  - 発注の冪等キー（order_request_id）や broker 側の ID 保存、UTC タイムスタンプ運用

---

## 要件

- Python 3.10+
- 依存ライブラリ（抜粋）
  - duckdb
  - （標準ライブラリの urllib 等で HTTP 呼び出しを行います）
- J-Quants API のリフレッシュトークンなどの環境変数

（実プロジェクトでは pyproject.toml / requirements.txt を参照して依存をインストールしてください。）

---

## セットアップ手順

1. リポジトリをクローン / 取得

   git clone <リポジトリURL>

2. 仮想環境を作成して有効化（例）

   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows

3. 依存をインストール

   pip install duckdb
   # その他プロジェクト依存があればインストールしてください

4. 環境変数設定
   - プロジェクトルートに `.env` / `.env.local` を配置すると、自動で読み込まれます（デフォルト）。
   - 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

.env に設定すべき主なキー（例）:
- JQUANTS_REFRESH_TOKEN=（必須）J-Quants のリフレッシュトークン
- KABU_API_PASSWORD=（必須）kabu ステーション API パスワード
- KABU_API_BASE_URL=http://localhost:18080/kabusapi （省略可）
- SLACK_BOT_TOKEN=（必須）Slack 通知に使う Bot トークン
- SLACK_CHANNEL_ID=（必須）通知先チャネル ID
- DUCKDB_PATH=data/kabusys.duckdb （省略時のデフォルト）
- SQLITE_PATH=data/monitoring.db （省略時のデフォルト）
- KABUSYS_ENV=development|paper_trading|live （デフォルト: development）
- LOG_LEVEL=DEBUG|INFO|WARNING|ERROR|CRITICAL （デフォルト: INFO）

注意: Settings から取得される必須キーが未設定の場合、起動時に ValueError が発生します。

---

## データベース初期化（DuckDB）

DuckDB スキーマ全体を作成するには `data.schema.init_schema()` を使用します。例:

python サンプル:
```python
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")  # ファイルを自動作成
# またはインメモリ:
# conn = schema.init_schema(":memory:")
```

監査ログ（Audit）テーブルだけを追加する場合:
```python
from kabusys.data import schema, audit
conn = schema.init_schema("data/kabusys.duckdb")
audit.init_audit_schema(conn)
```

---

## ETL の使い方（日次 ETL）

ETL パイプラインのエントリポイントは `kabusys.data.pipeline.run_daily_etl` です。基本的な実行例:

```python
from datetime import date
import logging

from kabusys.data import schema, pipeline

logging.basicConfig(level=logging.INFO)

# DB 初期化（最初のみ）
conn = schema.init_schema("data/kabusys.duckdb")

# 日次 ETL を実行（target_date を省略すると今日）
result = pipeline.run_daily_etl(conn, target_date=date.today())

# ETL 結果確認
print(result.to_dict())
if result.has_errors:
    print("ETL 中にエラーが発生しました:", result.errors)
if result.has_quality_errors:
    print("重大な品質問題があります")
```

run_daily_etl の主要パラメータ:
- conn: DuckDB 接続
- target_date: ETL 対象日（省略時は当日）
- id_token: テストなどで外部から注入可能
- run_quality_checks: 品質チェックを実行するか（デフォルト True）
- backfill_days: 株価・財務のバックフィル日数（デフォルト 3）
- calendar_lookahead_days: カレンダー先読み日数（デフォルト 90）

ETL は段階ごとにエラーをキャッチして処理を継続し、結果にエラーや品質問題を集約します。

---

## J-Quants クライアントの使い方

トークン取得／データ取得は `kabusys.data.jquants_client` を利用します。ID トークンは内部でキャッシュされ、自動リフレッシュされます。

例: ID トークン取得（明示的に）:
```python
from kabusys.data import jquants_client as jq
id_token = jq.get_id_token()  # settings.jquants_refresh_token を使用
```

例: 株価取得 → 保存:
```python
from kabusys.data import jquants_client as jq, schema
conn = schema.get_connection("data/kabusys.duckdb")
records = jq.fetch_daily_quotes(date_from=date(2023,1,1), date_to=date(2023,12,31))
jq.save_daily_quotes(conn, records)
```

設計上の要点:
- レート制限（120 req/min）を守るよう内部でスロットリング
- リトライ・バックオフ・401 自動リフレッシュ対応
- 保存は冪等（ON CONFLICT DO UPDATE）

---

## データ品質チェック（Quality）

個別チェック関数:
- check_missing_data(conn, target_date)
- check_duplicates(conn, target_date)
- check_spike(conn, target_date, threshold)
- check_date_consistency(conn, reference_date)

まとめて実行:
```python
from kabusys.data import quality
issues = quality.run_all_checks(conn, target_date=date.today())
for i in issues:
    print(i)
```

QualityIssue 型でチェック名・重大度・サンプル行が返ります。呼び出し側で重大度に応じた対応（停止・アラート等）を行ってください。

---

## 環境設定の自動読み込み

- 実行時、パッケージはプロジェクトルート（.git または pyproject.toml が存在する場所）から `.env` と `.env.local` を自動読み込みします。
  - 読み込み順: OS 環境変数 > .env.local > .env
  - .env.local は .env を上書き可能（override）
- 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時に便利）。

.env のパースは `export KEY=val`、クォート、インラインコメント等に対応しています。

---

## ディレクトリ構成

ルートにある想定的なパッケージ構成（本実装ベース）:

- src/
  - kabusys/
    - __init__.py
    - config.py                — 環境変数・Settings
    - data/
      - __init__.py
      - jquants_client.py      — J-Quants API クライアント + 保存関数
      - schema.py              — DuckDB スキーマ定義・初期化
      - pipeline.py            — ETL パイプライン
      - audit.py               — 監査ログスキーマ
      - quality.py             — データ品質チェック
      - pipeline.py
    - strategy/
      - __init__.py            — 戦略関連（未実装のエントリポイント）
    - execution/
      - __init__.py            — 発注/ブローカー連携（拡張箇所）
    - monitoring/
      - __init__.py            — 監視・メトリクス（拡張箇所）

（上記は現状の実装ファイルと構成の抜粋です。実際の配布では追加のモジュールや CLI、ワーカー等が存在する可能性があります。）

---

## よくある利用パターン

- データ基盤初期化:
  - schema.init_schema() を呼んで DB を作成 → run_daily_etl を定期実行してデータを蓄積
- 定期実行:
  - Cron / Airflow / GitHub Actions 等で run_daily_etl を毎営業日実行
- 監査ログ:
  - 発注パスでは audit.init_audit_schema() を呼び出し、order_requests / executions を利用
- テスト:
  - DuckDB の ":memory:" を使ってユニットテストを行うことが可能

---

## トラブルシューティング / 注意点

- 必須環境変数が未設定の場合、Settings プロパティで ValueError が発生します。
- J-Quants のレート制限・429 や Retry-After ヘッダに対応していますが、短時間で大量呼び出しをしない設計にしてください。
- DuckDB は軽量で扱いやすいですが、本番での同時書き込み等の要件がある場合は運用設計（排他制御やバックアップ）を検討してください。
- 監査テーブルは削除しない運用を想定しています（ON DELETE RESTRICT 等）。

---

以上がこのリポジトリの README です。必要であれば、実行スクリプト例（CLI/cron 用）や .env.example、依存を明記した requirements.txt / pyproject.toml のサンプルを追加で作成します。必要なら指示してください。