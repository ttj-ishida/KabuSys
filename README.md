# KabuSys

KabuSys は日本株向けの自動売買／データプラットフォーム基盤です。J-Quants API や RSS フィード等から市場データ・財務データ・ニュースを収集し、DuckDB に冪等的に保存、品質チェック、戦略・発注（監査ログ）レイヤーをサポートするためのライブラリ群を提供します。

主に以下を目的としています。
- J-Quants からの OHLCV / 財務データ / 市場カレンダーの定期取得（レート制御・リトライ・トークン自動更新対応）
- RSS フィードからのニュース収集と銘柄紐付け（SSRF・XML攻撃・大容量レスポンス対策付き）
- DuckDB スキーマ定義・初期化、ETL パイプライン、データ品質チェック
- 監査ログ（signal → order → execution のトレーサビリティ）用スキーマ

---

## 主な機能一覧

- 環境変数読み込み・管理 (.env/.env.local 自動ロード、必要変数検証)
- J-Quants API クライアント
  - 株価日足（OHLCV）、財務（四半期）、市場カレンダー取得
  - レートリミット（120 req/min）対応
  - 再試行（指数バックオフ、最大 3 回）、401 での自動トークンリフレッシュ
  - 取得時刻（fetched_at）を UTC で記録
  - DuckDB への冪等保存（ON CONFLICT）
- RSS ニュースコレクタ
  - RSS 取得・パース（defusedxml）、URL 正規化・トラッキングパラメータ除去
  - SSRF 対策（スキーム検証・プライベートIPブロック・リダイレクト検査）
  - レスポンスサイズ制限（メモリ DoS 防止）、gzip 解凍チェック
  - 記事ID は正規化 URL の SHA-256（先頭 32 文字）
  - DuckDB への冪等保存（INSERT ... RETURNING / トランザクション）
  - 記事と銘柄コードの紐付け（抽出ロジック付）
- DuckDB スキーマ（Raw / Processed / Feature / Execution / Audit）
  - テーブル定義とインデックス、監査ログ用スキーマの初期化ユーティリティ
- ETL パイプライン
  - 差分更新（最終取得日に基づく差分取得 + backfill）
  - 市場カレンダー先読み（lookahead）
  - 品質チェック（欠損・スパイク・重複・日付不整合）
  - ETL 実行結果を表す ETLResult（品質情報・エラー情報含む）
- カレンダー管理（営業日判定 / next/prev / 期間の営業日取得 / nightly update job）
- 監査ログ（signal_events / order_requests / executions）初期化・管理

---

## セットアップ

前提
- Python 3.10+（typing の一部構文を利用）
- pip / 仮想環境

依存ライブラリ（主要）
- duckdb
- defusedxml

インストール例（開発環境）:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .             # パッケージ化されている場合
pip install duckdb defusedxml
```

環境変数
- プロジェクトルートにある `.env` / `.env.local` が自動読み込みされます（CWD ではなくパッケージ位置からプロジェクトルートを探索）。
- 自動ロードを無効化する場合:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト用途など）。
- 必須環境変数（Settings で参照されるもの）
  - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
  - KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
  - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
  - SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- 任意 / デフォルト
  - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
  - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
  - KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視 DB などで使用（デフォルト: data/monitoring.db）

例: `.env`（最小）

```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
```

---

## 使い方（主要なユースケース）

※ 以下は Python から直接呼び出す例です。

1) DuckDB スキーマの初期化

```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
# またはメモリDB
# conn = init_schema(":memory:")
```

2) 日次 ETL を実行する（市場カレンダー → 株価 → 財務 → 品質チェック）

```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

オプションで id_token（J-Quants の ID トークン）を注入したり、バックフィル日数やスパイク閾値を変更できます。

3) ニュース収集ジョブの実行

```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
known_codes = {"7203", "6758", ...}  # 事前に有効な銘柄コードセットを用意
results = run_news_collection(conn, sources=None, known_codes=known_codes)
print(results)  # {source_name: saved_count}
```

4) 監査ログ（audit）スキーマ初期化（監査専用 DB を使う場合）

```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/kabusys_audit.duckdb")
```

5) J-Quants API を直接使った取得（トークンは自動管理される）

```python
from kabusys.data.jquants_client import fetch_daily_quotes, fetch_market_calendar
from kabusys.config import settings

# id_token を明示的に与えることもできる。省略時は内部キャッシュ経由で自動取得・更新される。
quotes = fetch_daily_quotes(code="7203", date_from=date(2024,1,1), date_to=date(2024,3,31))
```

6) カレンダー夜間バッチ（calendar_update_job）

```python
from kabusys.data.calendar_management import calendar_update_job
conn = init_schema(settings.duckdb_path)
saved = calendar_update_job(conn)
print("saved", saved)
```

---

## 重要な設計・運用上のポイント

- J-Quants API
  - レート制限: 120 req/min に合わせた固定間隔スロットリングを実装
  - 再試行: 408/429/5xx 等はリトライ、429 の Retry-After ヘッダを尊重
  - 401 が来た場合はリフレッシュトークンから id_token を取得して 1 回だけ再試行
  - 取得時刻は UTC で fetched_at に記録（Look-ahead Bias の抑止）
- News Collector
  - defusedxml を用いた XML パースで XML Bomb 等を防止
  - URL 正規化とトラッキングパラメータ削除で冪等を担保（記事ID は URL のハッシュ）
  - SSRF 対策（スキーム検査、プライベートIP ブロック、リダイレクト検査）
  - レスポンス上限（10 MB）と gzip 解凍後のサイズ検査
- DuckDB スキーマは冪等性を考慮（CREATE TABLE IF NOT EXISTS / ON CONFLICT）
- ETL は差分更新 + short backfill（デフォルト 3 日）で API の後出し修正を吸収
- 品質チェックは Fail-Fast ではなく全チェックを実行し、問題を報告する設計

---

## ディレクトリ構成

以下は主要ファイル／モジュールの概観（src 配下）:

- src/kabusys/
  - __init__.py
  - config.py                     -- 環境変数と Settings
  - data/
    - __init__.py
    - jquants_client.py            -- J-Quants API クライアント（取得 + 保存）
    - news_collector.py            -- RSS ニュース収集／保存
    - pipeline.py                  -- ETL パイプライン（run_daily_etl 等）
    - schema.py                    -- DuckDB スキーマ定義と初期化
    - calendar_management.py       -- カレンダー管理（営業日判定等）
    - audit.py                     -- 監査ログスキーマ（signal/order/execution）
    - quality.py                   -- データ品質チェック
  - strategy/
    - __init__.py                  -- 戦略層（拡張ポイント）
  - execution/
    - __init__.py                  -- 発注層（拡張ポイント）
  - monitoring/
    - __init__.py                  -- 監視・メトリクス（拡張ポイント）

---

## 開発・拡張のヒント

- strategy/ と execution/ は拡張ポイント。シグナル生成 → signal_queue 登録 → order_requests 登録 → ブローカー送信 → executions 登録 という流れを想定しています。
- テストでは settings の自動 .env 読み込みを妨げたい場合、環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- news_collector._urlopen はテスト用にモック可能です（外部 HTTP を差し替えられるように設計）。
- DuckDB の接続オブジェクトを引数として受け取る設計のため、単体テストで :memory: DB を使って検証できます。

---

## おわりに

この README はコードベースの主要機能と運用上のポイントをまとめたものです。各モジュールには詳細な docstring が記載されていますので、実装の利用や拡張時は該当モジュールの docstring を参照してください。追加のコマンドラインスクリプトやサービス化（例: cron・Airflow・Kubernetes CronJob での定期実行）を行う場合は、環境変数や接続先（DuckDB ファイルパス）を適切に管理してください。