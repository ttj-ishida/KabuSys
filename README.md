# KabuSys

日本株自動売買プラットフォームのコアライブラリセット。  
データ取得（J-Quants）、ETLパイプライン、データ品質チェック、ニュース収集、DuckDBスキーマ、監査ログなどを含むモジュール群を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は、日本株の自動売買システム向けに設計されたライブラリコレクションです。主に以下を提供します。

- J-Quants API からの株価・財務・マーケットカレンダー取得（レート制御・リトライ・トークン自動更新対応）
- RSSベースのニュース収集・前処理・銘柄抽出
- DuckDB を用いたデータスキーマ定義と初期化（Raw / Processed / Feature / Execution / Audit 層）
- 日次 ETL パイプライン（差分更新・バックフィル・品質チェック）
- マーケットカレンダー管理（営業日判定、prev/next 等のユーティリティ）
- 監査ログ：シグナル→発注→約定までのトレーサビリティ

設計方針として、冪等性（ON CONFLICT / RETURNING）、Look-ahead バイアス回避（fetched_at の記録）、SSRF 等のセキュリティ対策、メモリ DoS 対策などが取り入れられています。

---

## 主な機能一覧

- データ取得
  - 株価日足（OHLCV）のページネーション取得（fetch_daily_quotes）
  - 財務データ（四半期）取得（fetch_financial_statements）
  - JPX マーケットカレンダー取得（fetch_market_calendar）
  - トークンの自動リフレッシュ（401 発生時）
  - API レート制御（120 req/min 固定間隔スロットリング）
  - リトライ（指数バックオフ、HTTP 408/429/5xx で最大 3 回等）
- データ保存（DuckDB）
  - raw_prices / raw_financials / market_calendar 等への冪等保存関数（ON CONFLICT）
  - スキーマ初期化機能（init_schema）
- ETL
  - 日次 ETL（run_daily_etl）：カレンダー取得 → 株価差分取得 → 財務差分取得 → 品質チェック
  - 差分更新ロジック（最後に取得した日付を基に必要範囲のみ取得）
  - バックフィルオプション（API の後出し修正対応）
- ニュース収集
  - RSS 取得・XML パース（defusedxml）、URL 正規化、トラッキングパラメータ除去
  - 記事ID を正規化 URL の SHA-256（先頭32文字）で生成して冪等保存
  - SSRF 回避（リダイレクト時のスキーム・内部IP検査）、受信サイズ制限
  - 銘柄コード抽出（4桁数字）と news_symbols への紐付け
- カレンダー管理
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day
  - 夜間バッチ更新ジョブ（calendar_update_job）
- 品質チェック
  - 欠損データ、スパイク（前日比）、重複、日付不整合の検出（QualityIssue）
  - run_all_checks によりまとめて実行
- 監査ログ
  - signal_events / order_requests / executions 等の監査テーブル、インデックス
  - init_audit_schema による初期化

---

## 前提 / 要件

- Python 3.10+
- 必須パッケージ（例）
  - duckdb
  - defusedxml
- 標準ライブラリ urllib 等を使用（追加 HTTP ライブラリは不要）
- 任意で Slack 連携、kabuステーション連携など外部設定が必要

例: pip でのインストール（プロジェクトに setup/pyproject がある想定）
```
python -m pip install -r requirements.txt
# または開発時:
python -m pip install -e .
```
requirements.txt の例:
```
duckdb
defusedxml
```

---

## 環境変数 / 設定

設定は環境変数またはプロジェクトルートの `.env` / `.env.local` から自動読み込みされます。自動読み込みは、パッケージ内の設定モジュールで以下の順序で適用されます:

1. OS 環境変数
2. .env.local（存在すれば上書き）
3. .env（存在すれば未設定キーに設定）

自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主要な環境変数:
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL — kabuステーション API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack ボットトークン（通知等で使用）
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境 (development | paper_trading | live)（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）

注意: Settings クラスは未設定の必須変数を参照すると ValueError を投げます。

例（.env）
```
JQUANTS_REFRESH_TOKEN=xxxxxxxx...
KABU_API_PASSWORD=secret
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. リポジトリをクローン／展開
2. Python 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate (UNIX) / .venv\Scripts\activate (Windows)
3. 依存パッケージをインストール
   - pip install duckdb defusedxml
   - あるいはプロジェクトの requirements を使用
4. .env を作成して必要な環境変数を設定（.env.example を参考に）
5. DuckDB スキーマを初期化
   - Python REPL またはスクリプトで以下を実行（例）
     ```
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     conn.close()
     ```
6. 監査ログ用テーブルを別途初期化（必要な場合）
   - init_audit_schema(conn) または init_audit_db("data/audit.duckdb")

---

## 使い方（基本例）

以下は Python コード例です。各関数はモジュールからインポートして使用します。

- DuckDB スキーマ初期化
```
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

- 日次 ETL 実行（デフォルトは今日）
```
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn)
print(result.to_dict())
```

- カレンダーの夜間更新ジョブ
```
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn)
print(f"calendar saved: {saved}")
```

- ニュース収集（デフォルト RSS ソースから）
```
from kabusys.data.news_collector import run_news_collection
# known_codes は銘柄コードセットを渡すと抽出・紐付け処理を行う
res = run_news_collection(conn, known_codes={"7203", "6758"})
print(res)
```

- J-Quants のデータ取得（個別に呼ぶ場合）
```
from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
token = get_id_token()  # settings.jquants_refresh_token を使って自動取得
records = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))
```

- 品質チェックを個別実行
```
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn)
for i in issues:
    print(i)
```

注意: 実運用（live）モードでは設定や安全対策に細心の注意を払い、バックテストや paper_trading で充分検証してください。

---

## 推奨運用

- ETL・カレンダー更新・ニュース収集などは Cron・Airflow 等のジョブスケジューラで定期実行する。
- ETL 実行後は品質チェック結果（QualityIssue）を Slack 等で通知して監視を自動化する。
- 監査ログ（order_requests / executions）を有効にし、発注フローの完全なトレーサビリティを担保する。
- 環境切替（development / paper_trading / live）は KABUSYS_ENV で管理する。

---

## ディレクトリ構成（主要ファイル説明）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み・Settings クラス（自動 .env ロード機能・必須チェック）
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（fetch_*, save_*、レート制御・リトライ・トークン管理）
    - news_collector.py
      - RSS フィード取得・前処理・DuckDB へ保存、銘柄抽出と紐付け
    - schema.py
      - DuckDB のスキーマ定義と init_schema/get_connection
    - pipeline.py
      - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
    - calendar_management.py
      - マーケットカレンダーの管理・営業日判定ユーティリティ・calendar_update_job
    - audit.py
      - 監査ログ（signal_events, order_requests, executions）初期化とヘルパー
    - quality.py
      - データ品質チェック（欠損、重複、スパイク、日付不整合）
  - strategy/
    - __init__.py
    - （戦略実装用モジュール・プレースホルダ）
  - execution/
    - __init__.py
    - （発注 / ブローカー連携用モジュール・プレースホルダ）
  - monitoring/
    - __init__.py
    - （監視・アラート用モジュール・プレースホルダ）

---

## 備考 / 注意点

- DuckDB の datetime 型や日付パース周りは実行環境のロケールや Python のバージョンによる差異に注意してください。
- jquants_client は urllib を用いているため、プロキシ設定や TLS 設定が必要な環境では適宜対応してください。
- news_collector は defusedxml を利用して安全に XML をパースします。外部からの入力をそのまま扱う箇所はセキュリティ観点で注意を払っていますが、運用時は追加の制約（ホワイトリスト等）を検討してください。
- このリポジトリ内の strategy / execution / monitoring は拡張ポイントとして設計されています。実際の戦略ロジック、発注ロジック、監視ルールは個別実装が必要です。

---

必要に応じて README のサンプル .env.example やデプロイ手順書を追加できます。どの箇所をより詳しく書くか指定いただければ、追記します。