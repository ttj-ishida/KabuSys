# KabuSys

KabuSys は日本株向けの自動売買基盤（データ取得・ETL・品質チェック・監査ログ等）を提供する Python パッケージです。J-Quants API や RSS を用いたデータ収集、DuckDB によるスキーマ管理、日次 ETL パイプライン、データ品質チェック、監査ログテーブルの初期化などを主要機能として備えています。

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（簡易サンプル）
- ディレクトリ構成
- 主要モジュールの説明
- 環境変数一覧（必須/任意）
- 注意事項

---

## プロジェクト概要

KabuSys は以下の目的で設計されています。

- J-Quants API から日次株価（OHLCV）、四半期財務、JPX マーケットカレンダーを取得
- RSS フィードからニュース記事を収集し DB に保存、銘柄タグ付け
- DuckDB を用いて Raw / Processed / Feature / Execution の多層スキーマを管理・初期化
- 日次 ETL パイプライン（差分取得・バックフィル・品質チェック）を提供
- データ品質チェックと監査ログ（シグナル→発注→約定のトレーサビリティ）を提供
- セキュリティ・耐障害性設計（API レート制御、リトライ、SSRF 対策、XML パースの安全化等）

---

## 機能一覧

- 環境設定自動ロード（.env / .env.local、CWD に依存しないプロジェクトルート探索）
- J-Quants API クライアント
  - レート制限（120 req/min）
  - 再試行（指数バックオフ、401 時の自動トークンリフレッシュ）
  - fetch/save の冪等（DuckDB 側で ON CONFLICT を使用）
- ニュース収集（RSS）
  - URL 正規化（トラッキングパラメータ除去）
  - SSRF 対策（リダイレクト先検査、プライベートアドレス拒否）
  - defusedxml を使った安全な XML パース
  - 記事ID は正規化 URL の SHA-256（先頭32文字）
  - raw_news / news_symbols へのバルク挿入（チャンク処理・トランザクション）
- DuckDB スキーマ定義と初期化（init_schema）
- ETL パイプライン
  - run_daily_etl（カレンダー→価格→財務→品質チェック）
  - 差分更新・バックフィルの自動算出
- マーケットカレンダー管理（営業日判定・前後営業日取得・夜間更新ジョブ）
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 監査ログスキーマ（signal_events / order_requests / executions）と初期化関数
- ストラテジー・実行・モニタリング用のパッケージ構成（拡張用の空パッケージ）

---

## セットアップ手順

前提:
- Python 3.9+ を推奨（typing の Union|None 表記などを使用しています）
- duckdb, defusedxml 等が必要

1. 仮想環境を作成・有効化（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

2. 依存ライブラリをインストール（最小例）
   ```bash
   pip install duckdb defusedxml
   ```
   ※ プロジェクトの requirements.txt / pyproject.toml がある場合はそちらに従ってください。

3. このプロジェクトをインストール（開発モード）
   ```bash
   pip install -e .
   ```

4. 環境変数の準備
   - プロジェクトルートに `.env` または `.env.local` を配置すると自動で読み込まれます（モジュール import 時に探索）。
   - 自動読み込みを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
   - 必須環境変数（後述）を設定してください。

5. DuckDB スキーマ初期化（例）
   Python REPL やスクリプトで:
   ```python
   from kabusys.data import schema
   conn = schema.init_schema("data/kabusys.duckdb")
   ```

---

## 使い方（簡易サンプル）

### 1) DuckDB の初期化
```python
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")
```
- ":memory:" を指定するとインメモリ DB を使用できます。
- 親ディレクトリがなければ自動作成されます。

### 2) J-Quants トークン取得（必要に応じて）
```python
from kabusys.data import jquants_client as jq
id_token = jq.get_id_token()  # settings.jquants_refresh_token を使用
```

### 3) 日次 ETL を実行
```python
from kabusys.data import pipeline
result = pipeline.run_daily_etl(conn)
print(result.to_dict())
```
- ETL は市場カレンダー → 価格 → 財務 → 品質チェック（デフォルト）を順に実行します。
- 差分更新やバックフィル日数は引数で調整可能です。

### 4) RSS ニュース収集
```python
from kabusys.data import news_collector
from kabusys.data import schema
conn = schema.get_connection("data/kabusys.duckdb")
# デフォルトソースを使って収集・保存
from kabusys.data.news_collector import run_news_collection
results = run_news_collection(conn, known_codes={"7203", "6758", ...})
print(results)
```

### 5) 監査 DB 初期化（監査ログ専用 DB）
```python
from kabusys.data import audit
audit_conn = audit.init_audit_db("data/audit.duckdb")
```

### 6) 品質チェックの個別実行
```python
from kabusys.data import quality
issues = quality.run_all_checks(conn)
for issue in issues:
    print(issue)
```

---

## ディレクトリ構成

（主要ファイルを抜粋）

- src/kabusys/
  - __init__.py
  - config.py                      # 環境変数・設定管理（.env 自動読み込み）
  - data/
    - __init__.py
    - jquants_client.py            # J-Quants API クライアント（fetch / save）
    - news_collector.py           # RSS ニュース収集・保存・銘柄抽出
    - schema.py                   # DuckDB スキーマ定義・init_schema
    - pipeline.py                 # ETL パイプライン（run_daily_etl 等）
    - calendar_management.py      # カレンダー管理 / calendar_update_job
    - audit.py                    # 監査ログスキーマ / init_audit_db
    - quality.py                  # データ品質チェック
  - strategy/
    - __init__.py                  # 戦略ロジック用パッケージ（拡張点）
  - execution/
    - __init__.py                  # 発注実行関連パッケージ（拡張点）
  - monitoring/
    - __init__.py                  # モニタリング関連（拡張点）

---

## 主要モジュールの簡単説明

- kabusys.config
  - .env / .env.local をプロジェクトルートから自動読み込み
  - settings オブジェクト経由で設定取得（例: settings.jquants_refresh_token）
  - KABUSYS_ENV（development/paper_trading/live）、LOG_LEVEL などを検証

- kabusys.data.jquants_client
  - API レート制御（_RateLimiter）
  - _request に指数バックオフ・401 リフレッシュ処理実装
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar（DuckDB へ冪等保存）

- kabusys.data.news_collector
  - RSS フィード取得（fetch_rss）
  - テキスト前処理（URL 除去、空白正規化）
  - SQL バルク挿入（save_raw_news / save_news_symbols）
  - SSRF 対策、gzip/untrusted XML 対応、受信サイズ制限などを実装

- kabusys.data.schema
  - Raw / Processed / Feature / Execution 各レイヤの DDL 定義
  - init_schema(db_path) で全テーブル・インデックスを作成

- kabusys.data.pipeline
  - run_prices_etl / run_financials_etl / run_calendar_etl（差分取得）
  - run_daily_etl：一連の ETL と品質チェックを実行し ETLResult を返す

- kabusys.data.calendar_management
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days
  - calendar_update_job：夜間カレンダー差分更新ジョブ

- kabusys.data.audit
  - signal_events / order_requests / executions の DDL
  - init_audit_db / init_audit_schema により監査ログテーブルを初期化

- kabusys.data.quality
  - check_missing_data / check_spike / check_duplicates / check_date_consistency
  - run_all_checks でまとめて実行し QualityIssue のリストを返す

---

## 環境変数一覧

必須（モジュールが参照する環境変数）
- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（get_id_token で使用）
- KABU_API_PASSWORD — kabu ステーション API パスワード（将来的な発注モジュール向け）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID

任意 / デフォルトあり
- KABUSYS_ENV — 実行環境 (development|paper_trading|live)。デフォルト: development
- LOG_LEVEL — ログレベル (DEBUG|INFO|WARNING|ERROR|CRITICAL)。デフォルト: INFO
- DUCKDB_PATH — DuckDB ファイルパス（data/kabusys.duckdb がデフォルト）
- SQLITE_PATH — 監視用 SQLite のパス（data/monitoring.db がデフォルト）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効化（1 を設定）

.env の雛形（例）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_api_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 注意事項 / 実運用上のポイント

- J-Quants API に対するリクエスト数は 120 req/min に制限されています。本クライアントは固定間隔スロットリングでこれを守る実装ですが、運用時は他プロセスとの同時アクセスにも注意してください。
- get_id_token() はリフレッシュトークンを利用して ID トークンを取得します。refresh token は安全に保管してください。
- DuckDB のファイルはデフォルトでプロジェクト内 data/ に作られます。本番環境では適切なデータバックアップを行ってください。
- news_collector は外部 URL を開くため、ネットワークアクセスのポリシーやプロキシ設定等に注意してください。SSRF 対策はありますが、運用環境固有の制約がある場合は追加の安全策を検討してください。
- audit.init_audit_db() はタイムゾーンを UTC に設定します。UTC での時刻保存・表示を前提にしてください。
- DuckDB は一部のトランザクション振る舞い（ネストトランザクション等）で制限があるため、init_audit_schema の transactional フラグ等の呼び出し方に注意してください。

---

問題報告・貢献
- バグ報告や改善提案は issue を通じてお願いします。
- 戦略、実行、モニタリング部分は拡張ポイントとして空パッケージで用意しています。PR 大歓迎です。

---

この README はコードベースの注釈・設計に基づいて作成しています。具体的な運用手順（cron/airflow/CI 経由での ETL 実行、モニタリング設定、証券会社 API 連携等）は実運用要件に応じて追加してください。