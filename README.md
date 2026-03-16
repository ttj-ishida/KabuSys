# KabuSys

日本株向け自動売買プラットフォーム用ライブラリ（KabuSys）。  
データ取得・永続化（DuckDB）、品質チェック、監査ログ、戦略・実行・監視の基盤モジュールを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下を目的とした内部ライブラリです。

- J-Quants API から株価・財務・マーケットカレンダーを取得して永続化
- DuckDB 上に3層（Raw / Processed / Feature）＋実行レイヤーのスキーマを定義・初期化
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 発注フローの監査ログ（signal → order_request → executions のトレーサビリティ）
- 将来的に戦略・実行・監視モジュールと連携するための基盤

設計上のポイント:
- J-Quants API に対するレート制限（120 req/min）のクライアント実装（スロットリング）
- リトライ、指数バックオフ、401 発生時の自動トークンリフレッシュ
- データ取得時に fetched_at を UTC で記録（look-ahead bias 対策）
- DuckDB への挿入は ON CONFLICT DO UPDATE により冪等性を確保

---

## 機能一覧

- 環境変数 / .env 読み込み（自動ロード機能、.env.local を優先）
- J-Quants API クライアント
  - 株価日足（OHLCV）取得（ページネーション対応）
  - 財務データ（四半期 BS/PL）取得
  - JPX マーケットカレンダー取得
  - id_token の取得・キャッシュ・自動リフレッシュ
  - レートリミッタ、リトライ、指数バックオフ
- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution レイヤーのテーブル定義
  - インデックス定義、冪等的な初期化
- 監査ログ（audit）
  - signal_events / order_requests / executions テーブルとインデックス
  - 発注フローの完全なトレーサビリティ
- データ品質チェック（quality）
  - 欠損データ検出、スパイク検知、重複チェック、日付整合性チェック
  - QualityIssue オブジェクトのリストを返す API

---

## セットアップ手順

前提:
- Python 3.9+（型注釈の Union 代替などを使用しているため）
- duckdb が必要
- ネットワーク経由で J-Quants API を利用する場合は適切な API トークン等が必要

1. 仮想環境作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - pip install duckdb

   （他に必要なパッケージがあれば requirements.txt を作成して pip install -r requirements.txt）

3. 環境変数のセット
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` を置くと、自動でロードされます。
   - 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

推奨される .env の例（.env.example の作成を想定）:
- JQUANTS_REFRESH_TOKEN=...
- KABU_API_PASSWORD=...
- KABU_API_BASE_URL=（任意、デフォルトは http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN=...
- SLACK_CHANNEL_ID=...
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- KABUSYS_ENV=development|paper_trading|live
- LOG_LEVEL=INFO

.env のパースは export KEY=val 形式、クォート、インラインコメント等に対応しています。

---

## 使い方（主要 API）

以下は代表的な利用例です。実行はパッケージをプロジェクトルートから import して行ってください。

1) DuckDB スキーマ初期化
- 永続 DB ファイルを作成してスキーマ初期化（ファイルを自動作成）
```
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
# :memory: を渡すとインメモリ DB
# conn は duckdb.DuckDBPyConnection
```

- 既存 DB に接続する（スキーマ初期化は行わない）
```
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
```

2) 監査ログ（audit）初期化
```
from kabusys.data.audit import init_audit_schema

# init_schema で作った conn を渡す
init_audit_schema(conn)
```
または監査専用 DB を初期化:
```
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/kabusys_audit.duckdb")
```

3) J-Quants データ取得・保存
```
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")

# 特定銘柄・期間の取得
records = fetch_daily_quotes(code="7203", date_from=some_date_from, date_to=some_date_to)

# 保存（raw_prices テーブルへ、冪等）
n = save_daily_quotes(conn, records)
print(f"保存件数: {n}")
```

ポイント:
- クライアントは 120 req/min のレート制限を守ります（内部で待機します）。
- 401 を受けた場合は自動で id_token をリフレッシュして 1 回リトライします。
- ページネーションの pagination_key を追跡して全件取得します。

4) データ品質チェック
```
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=None)
for issue in issues:
    print(issue.check_name, issue.severity, issue.detail)
    for row in issue.rows:
        print(row)
```
- 各チェックは QualityIssue のリストを返します。呼び出し側でエラー／警告に応じた処理（ETL 停止、Slack 通知等）を行ってください。

5) 認証トークン取得（直接利用する場合）
```
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # settings.jquants_refresh_token を使用して id_token を取得
```

---

## 自動 .env 読み込みの挙動（要点）

- 実行時、環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` が未設定であれば、パッケージ内で自動的にプロジェクトルートを探索し `.env` と `.env.local` を読み込みます。
- 探索基準はこのパッケージの __file__ を起点に親ディレクトリを上がり、`.git` または `pyproject.toml` が見つかったディレクトリをプロジェクトルートとします。
- 読み込み順（優先度）: OS 環境 > .env.local > .env
- .env のパースは export 形式、クォート、コメントを考慮した堅牢な実装です。

---

## ディレクトリ構成

リポジトリ内の主要構成（抜粋）:
- src/
  - kabusys/
    - __init__.py
    - config.py                # 環境設定の読み込み・Settings
    - data/
      - __init__.py
      - jquants_client.py      # J-Quants API クライアント（取得・保存ロジック）
      - schema.py              # DuckDB スキーマ定義・初期化
      - audit.py               # 監査ログ（発注トレーサビリティ）
      - quality.py             # データ品質チェック
    - strategy/
      - __init__.py
    - execution/
      - __init__.py
    - monitoring/
      - __init__.py

主なテーブル（DuckDB）:
- Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
- Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
- Feature Layer: features, ai_scores
- Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
- Audit: signal_events, order_requests, executions

---

## 開発上の注意点 / 補足

- すべてのタイムスタンプは UTC 保存を前提としています（audit 初期化で SET TimeZone='UTC' を実行）。
- DuckDB の初期化関数は冪等（既存テーブルがあればスキップ）です。初回は init_schema を利用してください。
- J-Quants API のレートやエラー処理はライブラリ側で考慮していますが、上位実装でも適切な例外処理・ログ出力を行ってください。
- データ品質チェックは Fail-Fast ではなく全チェックを実行して問題を集める設計です。集約して通知や ETL 停止判断を行う想定です。

---

もし README に追加してほしいサンプルワークフロー（ETL スクリプト例、Slack 連携例、CI 用のテスト手順など）があれば、どの項目を重視するか教えてください。必要に応じてサンプルコードや .env.example を追記します。