# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ。J-Quants API からのデータ取得、DuckDB スキーマ定義・初期化、ETL パイプライン、品質チェック、監査ログ用スキーマなどを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は次の目的を持つモジュール群です。

- J-Quants API から株価・財務・市場カレンダーなどを取得し、DuckDB に保存する
- ETL（差分取得・バックフィル）パイプラインを実装する
- データ品質チェック（欠損・スパイク・重複・日付不整合）を実行する
- 監査トレーサビリティ用のテーブル（シグナル→発注→約定の連鎖）を提供する
- 設定は環境変数（.env）経由で管理し自動ロードを行う（任意で無効化可）

設計上の特徴:
- J-Quants API 呼び出しはレート制限（120 req/min）とリトライ、トークン自動リフレッシュを備える
- DuckDB への保存は冪等（ON CONFLICT DO UPDATE）で実装
- ETL は差分更新＋バックフィルを標準とし、品質チェックは全件収集を行う（Fail-Fast ではない）
- 監査ログは削除しない設計、すべてのタイムスタンプは UTC を前提

---

## 主な機能一覧

- 環境変数 / .env 自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）
- settings オブジェクト経由で設定取得（例: settings.jquants_refresh_token）
- J-Quants API クライアント
  - get_id_token（リフレッシュトークンから ID トークン取得）
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar（ページネーション対応）
  - レートリミット制御、リトライ（408/429/5xx）、401 時の自動トークンリフレッシュ
  - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）
- DuckDB スキーマ管理
  - init_schema(db_path)：Raw / Processed / Feature / Execution 層のテーブル作成
  - get_connection(db_path)
- 監査ログスキーマ（signal_events / order_requests / executions 等）
  - init_audit_schema(conn)
  - init_audit_db(db_path)
- ETL パイプライン
  - run_prices_etl / run_financials_etl / run_calendar_etl
  - run_daily_etl：日次 ETL（カレンダー→株価→財務→品質チェック）
  - ETL 結果オブジェクト (ETLResult)
- データ品質チェック
  - 欠損、スパイク、重複、日付不整合を検出（QualityIssue）

---

## セットアップ手順

前提:
- Python 3.10 以上（型アノテーションの構文で | 型を使用）
- pip, virtualenv 等

1. 仮想環境の作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージのインストール
   - 本コードは標準ライブラリの urllib 等を利用しますが、DuckDB が必須です。
   - pip install duckdb

   （プロジェクトに requirements.txt / pyproject.toml がある場合はそちらを使用してください）

3. 環境変数の設定
   - プロジェクトルートに .env または .env.local を置くと、自動でロードされます（CWD ではなくパッケージファイル位置を基準にプロジェクトルートを探索）。
   - 自動ロードを無効にする場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

4. DuckDB スキーマ初期化（例は「使い方」参照）

---

## 必須 / 推奨環境変数 (.env 例)

以下は本ライブラリで参照される主な環境変数の例です。必須項目には README 中で明示します。

例 (.env):
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token     # 必須（J-Quants の refresh token）
KABU_API_PASSWORD=your_kabu_station_password        # 必須（kabu API パスワード）
KABU_API_BASE_URL=http://localhost:18080/kabusapi   # 任意（デフォルトは上記）
SLACK_BOT_TOKEN=xoxb-xxxxx                           # 必須（Slack 通知機能を使う場合）
SLACK_CHANNEL_ID=C0123456789                         # 必須（Slack 通知先）
DUCKDB_PATH=data/kabusys.duckdb                      # 保存先（デフォルト）
SQLITE_PATH=data/monitoring.db                       # 監視用 DB パス（必要に応じて）
KABUSYS_ENV=development                              # 有効値: development, paper_trading, live
LOG_LEVEL=INFO                                       # 有効値: DEBUG, INFO, WARNING, ERROR, CRITICAL

注意:
- settings.jquants_refresh_token / slack_bot_token / slack_channel_id / kabu_api_password は必須で、未設定時は ValueError が発生します。
- 自動ロード前に OS 環境で既に設定されている値は優先され、.env による上書きは .env.local（override）でなければ行われません。

---

## 使い方（サンプル）

以下はよく使う初期化・ETL 実行のサンプルです。

1) DuckDB スキーマを初期化して接続を取得する
```python
from kabusys.data import schema
from kabusys.config import settings

# settings.duckdb_path は Path オブジェクトを返します
conn = schema.init_schema(settings.duckdb_path)
```

2) 日次 ETL を実行する
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data import schema
from kabusys.config import settings
from datetime import date

conn = schema.get_connection(settings.duckdb_path)  # 既存 DB へ接続
result = run_daily_etl(conn, target_date=date.today())

# 結果の確認
print(result.to_dict())
```

3) 監査ログスキーマを初期化（既存の DuckDB 接続に追加）
```python
from kabusys.data.audit import init_audit_schema
from kabusys.data import schema

conn = schema.get_connection(settings.duckdb_path)
init_audit_schema(conn)
```

4) J-Quants API を直接呼ぶ例
```python
from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
from kabusys.config import settings

id_token = get_id_token()  # settings.jquants_refresh_token を使用
records = fetch_daily_quotes(id_token=id_token, date_from=date(2023,1,1), date_to=date(2023,1,31))
```

注意点:
- jquants_client は内部でレート制御・リトライ・401 リフレッシュを行います。大量取得時は rate limit に注意してください。
- save_* 関数は ON CONFLICT DO UPDATE により冪等性が担保されています。

---

## API 概要（主なモジュール）

- kabusys.config
  - settings: 環境変数ラッパー（プロパティアクセス）
  - 自動 .env 読み込み（プロジェクトルート検出）

- kabusys.data.jquants_client
  - get_id_token(refresh_token=None)
  - fetch_daily_quotes(...)
  - fetch_financial_statements(...)
  - fetch_market_calendar(...)
  - save_daily_quotes(conn, records)
  - save_financial_statements(conn, records)
  - save_market_calendar(conn, records)

- kabusys.data.schema
  - init_schema(db_path)
  - get_connection(db_path)

- kabusys.data.pipeline
  - run_prices_etl(...)
  - run_financials_etl(...)
  - run_calendar_etl(...)
  - run_daily_etl(...)

- kabusys.data.quality
  - check_missing_data(...)
  - check_spike(...)
  - check_duplicates(...)
  - check_date_consistency(...)
  - run_all_checks(...)

- kabusys.data.audit
  - init_audit_schema(conn)
  - init_audit_db(db_path)

---

## ディレクトリ構成

（リポジトリ内の主要ファイル / モジュール）
- src/
  - kabusys/
    - __init__.py
    - config.py               # 環境変数 / 設定管理
    - data/
      - __init__.py
      - jquants_client.py     # J-Quants API クライアント（取得・保存・レート制御）
      - schema.py            # DuckDB スキーマ定義・初期化
      - pipeline.py          # ETL パイプライン（差分取得・バックフィル・品質チェック）
      - quality.py           # データ品質チェック
      - audit.py             # 監査ログテーブル定義・初期化
      - pipeline.py
    - strategy/
      - __init__.py           # 戦略モジュール（拡張ポイント）
    - execution/
      - __init__.py           # 発注 / 実行関連（拡張ポイント）
    - monitoring/
      - __init__.py           # 監視関連（未実装/拡張ポイント）

---

## 運用上の注意 / ベストプラクティス

- 環境の切り替えは KABUSYS_ENV を使用（development / paper_trading / live）。
  - 本番運用時は is_live フラグ等で安全措置を組み込んでください。
- DuckDB ファイルは定期バックアップを推奨。監査ログは削除しない設計です。
- run_daily_etl は各ステップで例外を捕捉して継続します。結果の ETLResult.errors と quality_issues を監視して運用判断を行ってください。
- J-Quants API のレート制限とリトライの挙動（Retry-After ヘッダの尊重等）を理解したうえで並列実行やバッチ設計を行ってください。
- テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定し、テスト用設定を注入してください。

---

## 貢献 / 拡張ポイント

- strategy/ および execution/ 以下は戦略実装や証券会社 API 連携の拡張ポイントです。戦略は signal_events → order_requests を経て監査ログに記録する設計を想定しています。
- 監視（monitoring）モジュールで ETL/取引のメトリクス・アラート（Slack 連携など）を実装できます。

---

必要があれば README に以下を追加できます:
- 具体的な requirements.txt / pyproject.toml の記載
- CI / テスト実行例
- よくあるトラブルシュート（認証エラー、DuckDB の権限、レート制限による遅延 など）

ご希望があれば、README にそれらを追記します。