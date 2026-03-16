# KabuSys

日本株向け自動売買プラットフォームのコアライブラリ（プロトタイプ）。  
主にデータ取得・ETL、データ品質チェック、DuckDBスキーマ定義、監査ログ周りのユーティリティを提供します。

---

## プロジェクト概要

KabuSys は以下を目的とした内部ライブラリです。

- J-Quants API から株価・財務・マーケットカレンダーを安全に取得して DuckDB に格納する
- ETL（差分更新・バックフィル）を行い、取得時刻（fetched_at）を保存して Look-ahead bias を防止する
- データ品質チェック（欠損・スパイク・重複・日付不整合）を行い、問題を一覧化する
- DuckDB のスキーマ（Raw / Processed / Feature / Execution / Audit 層）を定義・初期化する
- 監査ログ（シグナル → 発注 → 約定のトレーサビリティ）を確保する

設計のポイント：
- API レート制御（J-Quants: 120 req/min）とリトライ／トークン自動リフレッシュを実装
- ETL の冪等性（ON CONFLICT DO UPDATE）を重視
- テスト容易性のためにトークン注入や自動ロードの無効化が可能

---

## 主な機能一覧

- データ取得（src/kabusys/data/jquants_client.py）
  - 株価日足（OHLCV）取得・ページネーション対応
  - 財務（四半期 BS/PL）取得・ページネーション対応
  - JPX マーケットカレンダー取得
  - リトライ、指数バックオフ、401 時の自動トークン更新、固定間隔レートリミッタ

- DuckDB スキーマ管理（src/kabusys/data/schema.py）
  - Raw / Processed / Feature / Execution 層テーブル定義
  - インデックス定義
  - init_schema(db_path) による初期化（冪等）

- ETL パイプライン（src/kabusys/data/pipeline.py）
  - 差分更新（最終取得日を確認して未取得分のみ取得）
  - backfill による数日前からの再取得（API 後出し修正の吸収）
  - 市場カレンダー先読み（lookahead）
  - 品質チェック呼び出し（quality モジュール）

- データ品質チェック（src/kabusys/data/quality.py）
  - 欠損データ検出（OHLC 欄）
  - スパイク検出（前日比の閾値）
  - 主キー重複検出
  - 日付整合性チェック（未来日・非営業日のデータ検出）
  - 各チェックは QualityIssue のリストを返す（error / warning）

- 監査ログ（src/kabusys/data/audit.py）
  - signal_events / order_requests / executions テーブル
  - 発注の冪等キーやトレーサビリティを担保
  - init_audit_schema(conn) / init_audit_db(path)

- 設定管理（src/kabusys/config.py）
  - .env（および .env.local）自動読み込み（プロジェクトルートを検出）
  - 環境変数アクセスラッパー（settings）
  - KABUSYS_ENV、LOG_LEVEL 等の検証

---

## セットアップ手順

前提:
- Python 3.9+（ソースは typing | future 注釈を使用）
- DuckDB を利用するために `duckdb` パッケージが必要

1. リポジトリをクローン（またはパッケージをプロジェクトに配置）

2. 仮想環境の作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - pip install duckdb
   - （プロジェクトを editable install する場合）
     - pip install -e .

   ※ 他の依存は標準ライブラリ中心のため、必要に応じて追加パッケージをインストールしてください。

4. 環境変数 / .env の準備  
   プロジェクトルートに `.env` を置くと自動で読み込まれます（.git または pyproject.toml をルート判定に使用）。  
   自動読み込みを無効にしたい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   最低限必要な環境変数（settings で必須とされているもの）:
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD
   - SLACK_BOT_TOKEN
   - SLACK_CHANNEL_ID

   任意（デフォルトを使うことも可能）:
   - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
   - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — デフォルト: INFO
   - KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
   - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
   - SQLITE_PATH — デフォルト: data/monitoring.db

   例 (.env):
   ```
   JQUANTS_REFRESH_TOKEN=xxxx...
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   ```

---

## 使い方（簡易ガイド）

以下は Python REPL やスクリプトでの基本的な利用例です。

1) DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")  # ファイルを作成して全テーブルを作成
```

2) 監査ログスキーマを追加で初期化
```python
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn)  # 既存 conn に監査テーブルを追加
```

3) J-Quants API からデータを取得して保存（個別呼び出し）
```python
from kabusys.data import jquants_client as jq
# トークンは settings から自動取得（JQUANTS_REFRESH_TOKEN が必要）
records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
saved = jq.save_daily_quotes(conn, records)
```

4) 日次 ETL の実行（カレンダー先読み・差分更新・品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn)  # target_date を省略すると本日が対象
print(result.to_dict())
```

5) 品質チェック単体の実行
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=None)
for i in issues:
    print(i.check_name, i.severity, i.detail)
```

6) 設定に関する参照
```python
from kabusys.config import settings
print(settings.duckdb_path)        # Path オブジェクト
print(settings.is_live)            # bool
```

注意点:
- J-Quants API 呼び出しは内部でレート制御・リトライされますが、実稼働環境では API 利用制限に注意してください。
- run_daily_etl は段階ごとにエラーを捕捉して継続します。戻り値の ETLResult に errors および quality_issues が含まれますので運用時にログやアラート連携を行ってください。

---

## ディレクトリ構成

主要なファイルとモジュール（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数・設定ラッパー（自動 .env ロード）
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API クライアント（取得 + 保存）
    - schema.py                     — DuckDB スキーマ定義・初期化
    - pipeline.py                   — ETL パイプライン（差分更新・品質チェック）
    - audit.py                      — 監査ログ（signal / order / execution）
    - quality.py                    — データ品質チェック（QualityIssue）
  - strategy/
    - __init__.py                   — 戦略層（拡張ポイント）
  - execution/
    - __init__.py                   — 発注実行層（拡張ポイント）
  - monitoring/
    - __init__.py                   — 監視・メトリクス（拡張ポイント）

DuckDB スキーマ（主なテーブル）:
- Raw 層: raw_prices, raw_financials, raw_news, raw_executions
- Processed 層: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
- Feature 層: features, ai_scores
- Execution 層: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
- Audit 層: signal_events, order_requests, executions

---

## 運用上の注意・補足

- .env の自動ロードはプロジェクトルート（.git または pyproject.toml があるディレクトリ）を基準に行います。CI やテストで自動ロードが不要な場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- settings のプロパティは必須変数が未設定だと ValueError を投げます（早期検出に有効）。
- ETL の差分判定では raw テーブルの最終取得日を参照します。初回ロードでは J-Quants の利用可能最古日（定数 _MIN_DATA_DATE）を使用します。
- DuckDB の接続は init_schema で初期化した接続を使うのが推奨です。既存 DB に接続する場合は get_connection() を使用してください。
- 監査テーブルは UTC タイムゾーンで TIMESTAMP を保存するように初期化されます（init_audit_schema は SET TimeZone='UTC' を実行）。

---

README に記載のない運用機能（例: Slack 通知、kabuステーションとの発注連携、戦略の実装等）は拡張ポイントとして用意されています。必要に応じて strategy/ や execution/ 下に実装を追加してください。

何か追加で README に載せたい項目（CI やデプロイ手順、サンプル戦略、具体的な監視アラート設定など）があれば教えてください。