# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ。  
J-Quants API から市場データを取得して DuckDB に保存し、データ品質チェック・監査ログ・ETL パイプラインを提供します。戦略・発注・モニタリングの各モジュールの土台となる共通機能群を含みます。

バージョン: 0.1.0

---

## 概要

主な役割は以下です。

- J-Quants API から株価（OHLCV）、財務情報、マーケットカレンダーを取得するクライアント（rate limit / retry / トークン自動リフレッシュ対応）。
- DuckDB を用いたスキーマ定義と初期化（Raw / Processed / Feature / Execution レイヤー）。
- ETL パイプライン（差分取得、バックフィル、先読みカレンダー、品質チェック）。
- データ品質チェック（欠損、スパイク、重複、日付不整合）。
- 監査ログ（シグナル→発注→約定のトレーサビリティ用テーブル群）。
- 環境変数による設定管理（.env 自動読み込み、テスト用に無効化可能）。

設計上のポイント:
- API レート制限（120 req/min）と指数バックオフを実装。
- 取得時刻を UTC で記録し、Look-ahead Bias を防止。
- DuckDB への挿入は冪等（ON CONFLICT DO UPDATE）。
- 品質チェックは Fail-Fast ではなく全件収集して呼び出し元で判断可能。

---

## 機能一覧

- data/jquants_client.py
  - get_id_token(), fetch_daily_quotes(), fetch_financial_statements(), fetch_market_calendar()
  - save_daily_quotes(), save_financial_statements(), save_market_calendar()
  - rate limiting（120 req/min）、リトライ（408/429/5xx、最大3回）、401 発生時の自動トークンリフレッシュ
- data/schema.py
  - init_schema(db_path), get_connection(db_path)
  - Raw/Processed/Feature/Execution 層のテーブル定義とインデックス
- data/pipeline.py
  - run_prices_etl(), run_financials_etl(), run_calendar_etl(), run_daily_etl()
  - 差分更新・backfill・カレンダー先読み・品質チェック統合
- data/quality.py
  - check_missing_data(), check_spike(), check_duplicates(), check_date_consistency(), run_all_checks()
  - QualityIssue 型（check_name, table, severity, detail, rows）
- data/audit.py
  - init_audit_schema(conn), init_audit_db(db_path)
  - シグナル / 発注要求 / 約定 の監査テーブルとインデックス（UTC タイムスタンプ）
- config.py
  - 環境変数読み込み（.env 自動読み込み）、Settings オブジェクト（各種必須設定をプロパティで提供）

---

## セットアップ手順

前提
- Python >= 3.10（型注釈に `X | Y` を使用）
- pip が利用可能

1. リポジトリをクローン／配置
   - あるいはパッケージを配置した Python 環境に `src` を含める。

2. 依存パッケージをインストール
   - 必須: duckdb
   - 例:
     pip install duckdb

   （プロジェクトで他に必要なパッケージがあれば pyproject.toml / requirements.txt を参照してインストールしてください）

3. 環境変数の設定
   - プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（CWD ではなくパッケージ位置から .git または pyproject.toml を探索してプロジェクトルートを決定します）。
   - 自動読み込みを無効化する場合:
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

4. 必要な環境変数（一例）
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
   - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト: INFO）
   - KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
   - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知用（必須の場合あり）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）

   例 .env:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxx
   KABU_API_PASSWORD=your_password
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   ```

---

## 使い方（簡易サンプル）

注意: 以下は Python REPL / スクリプト例です。

1. DuckDB スキーマ初期化
```
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

2. 監査ログテーブルを追加（必要時）
```
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn)
```

3. 日次 ETL 実行（デフォルトは本日を対象）
```
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn)
print(result.to_dict())
```

4. ETL の詳細コントロール（バックフィルや品質チェックの有無）
```
from datetime import date
res = run_daily_etl(conn, target_date=date(2026,1,15), run_quality_checks=True, backfill_days=5)
```

5. J-Quants の手動トークン取得（テスト用に id_token を注入可能）
```
from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes
id_token = get_id_token()
quotes = fetch_daily_quotes(id_token=id_token, date_from=date(2026,1,1), date_to=date(2026,1,15))
```

6. 個別 ETL ジョブを呼ぶ
```
from kabusys.data.pipeline import run_prices_etl, run_financials_etl
run_prices_etl(conn, target_date=date.today())
run_financials_etl(conn, target_date=date.today())
```

---

## 主要なディレクトリ構成

（src 配下を想定）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得 / 保存 / 認証 / retry / rate limit）
    - schema.py              — DuckDB スキーマ定義・初期化
    - pipeline.py            — ETL パイプライン（差分取得・backfill・品質チェック）
    - quality.py             — データ品質チェック
    - audit.py               — 監査ログ（シグナル/発注/約定）初期化
    - pipeline.py            — ETL ロジック
  - strategy/                 — 戦略モジュール（スケルトン）
  - execution/                — 実行（発注）モジュール（スケルトン）
  - monitoring/               — モニタリング周り（スケルトン）

主要テーブル（DuckDB スキーマの要約）
- Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
- Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
- Feature Layer: features, ai_scores
- Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
- Audit: signal_events, order_requests, executions

---

## 補足 / 実装上の注意点

- Python 3.10 以上が必要（型アノテーションに `|` を使用）。
- J-Quants API のレート制限は 120 req/min に固定（_RateLimiter による制御）。大量取得時はスロットリングにより遅延が入ります。
- API リトライは最大 3 回（408/429/5xx、指数バックオフ）。429 の場合は Retry-After を尊重します。
- get_id_token() はリフレッシュトークンから ID トークンを取得し、401 発生時に自動リフレッシュして 1 回リトライします。
- DuckDB 側の INSERT は ON CONFLICT DO UPDATE による冪等実装。ETL は差分（最終取得日ベース）で実行されます。
- 監査ログのタイムスタンプは UTC で保存されます（init_audit_schema は SET TimeZone='UTC' を実行）。
- 品質チェックは致命的な問題を検出しても ETL を停止せず、検出結果を返します。呼び出し元で適切な対応（アラート、手動確認など）を行ってください。

---

## さらに進めるために

- strategy / execution / monitoring モジュールを実装して、シグナル生成→リスク管理→発注→約定取り込み→ポジション管理のフローを完成させてください。
- CI / テスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して環境周りの副作用を抑えると便利です。
- 大量データ取り込み・長期間運用を想定する場合は、DuckDB ファイルの置き場所（バックアップ・永続化）やログ・メトリクスの取り扱いを検討してください。

---

必要であれば、README に含める具体的な `.env.example`、サンプルワークフロー（cron / Airflow での実行例）、あるいはユニットテストの書き方例も作成できます。どの情報を追加しますか？