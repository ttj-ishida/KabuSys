# KabuSys

日本株自動売買基盤のためのライブラリ群 / ミニフレームワークです。  
データ取得（J-Quants）、ETL パイプライン、DuckDB スキーマ定義、ニュース収集、マーケットカレンダー管理、データ品質チェック、監査ログ（発注→約定トレース）などを提供します。

## 概要
- J-Quants API から株価・財務・マーケットカレンダーを取得して DuckDB に保存する ETL パイプラインを提供します。
- RSS フィードからニュースを収集し、記事と銘柄の紐付けを行います（SSRF や XML 攻撃対策を実装済み）。
- DuckDB に対するスキーマ定義（Raw / Processed / Feature / Execution / Audit）を提供し、冪等な保存ロジック（ON CONFLICT）でデータ整備を行います。
- データ品質チェック（欠損、重複、スパイク、日付不整合）とマーケットカレンダーに基づく営業日ロジックを備えます。
- 発注・約定フローを監査する監査スキーマ（order_request_id による冪等性等）を提供します。

## 主な機能一覧
- J-Quants API クライアント
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - レートリミット制御（120 req/min の固定間隔スロットリング）
  - リトライ（指数バックオフ、最大 3 回）、401 時の自動トークンリフレッシュ
  - DuckDB への冪等保存（save_daily_quotes / save_financial_statements / save_market_calendar）
- ETL パイプライン
  - run_daily_etl：カレンダー → 株価 → 財務 → 品質チェックの差分 ETL
  - 差分取得（DB の最終取得日ベース） + backfill（デフォルト 3 日）
- ニュース収集
  - RSS フィード取得（gzip / XML パース / defusedxml）
  - URL 正規化・トラッキングパラメータ除去・記事ID（SHA-256先頭32文字）
  - SSRF 対策（スキーム検証、プライベート IP ブロック、リダイレクト検査）
  - raw_news テーブルへ冪等保存、news_symbols による銘柄紐付け
- マーケットカレンダー管理
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day
  - calendar_update_job（夜間バッチで J-Quants から差分更新）
- データ品質チェック
  - 欠損データ検出、スパイク検出（前日比閾値）、重複チェック、日付不整合検出
  - run_all_checks でまとめて実行
- 監査ログ（Audit）
  - signal_events / order_requests / executions などの監査用テーブル
  - init_audit_db / init_audit_schema による初期化

## 要件（推奨）
- Python 3.10+
- 必須ライブラリ（例）
  - duckdb
  - defusedxml

インストール例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# もしパッケージ配布があれば: pip install -e .
```

## 環境変数 / .env
config モジュールはプロジェクトルートの `.env` / `.env.local` を自動ロードします（OS 環境変数が優先）。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須（Settings が参照する環境変数）
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API のパスワード（必須）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID — Slack チャネル ID（必須）

任意（デフォルトあり）
- KABUS_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視用）ファイルパス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境 (development | paper_trading | live)（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト INFO）

例 .env:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxx...
KABU_API_PASSWORD=your_kabu_pw
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C...
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

## セットアップ手順（ローカルで動かす最小手順）
1. リポジトリをクローン
2. 仮想環境を作成して依存関係をインストール（上記参照）
3. プロジェクトルートに `.env` を作成し、必要な環境変数を設定
4. DuckDB スキーマを初期化
   - Python REPL またはスクリプトで:
     ```py
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     ```
5. 監査ログ用 DB を別ファイルで初期化する場合:
   ```py
   from kabusys.data.audit import init_audit_db
   audit_conn = init_audit_db("data/kabusys_audit.duckdb")
   ```

## 使い方（簡単なコード例）
- 日次 ETL を実行する（単発）
```py
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn)  # target_date を指定可
print(result.to_dict())
```

- ニュース収集ジョブ（既知銘柄セットを与えて紐付け）
```py
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
# known_codes は事前に DB 等から取得する set[str]
known_codes = {"7203", "6758", "9984"}
res = run_news_collection(conn, known_codes=known_codes)
print(res)  # {source_name: saved_count}
```

- マーケットカレンダーのユーティリティ
```py
from datetime import date
from kabusys.data.schema import get_connection
from kabusys.data.calendar_management import is_trading_day, next_trading_day

conn = get_connection("data/kabusys.duckdb")
d = date(2026, 3, 5)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

- データ品質チェック
```py
from kabusys.data.quality import run_all_checks
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
issues = run_all_checks(conn)
for i in issues:
    print(i.check_name, i.severity, i.detail)
```

注意点:
- J-Quants API のレート上限（120 req/min）やリトライ挙動、401 時のトークン自動リフレッシュなどがクライアントに実装されています。
- news_collector は受信サイズ・gzip 解凍後サイズの検査、SSRF 対策、defusedxml による安全な XML パースを行います。

## ディレクトリ構成
パッケージは `src/kabusys` 配下に実装されています。主なファイルとディレクトリ:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定読み込み（.env 自動読み込み含む）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント & DuckDB 保存ロジック
    - news_collector.py      — RSS ニュース取得・前処理・DB 保存・銘柄抽出
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - schema.py              — DuckDB スキーマ定義 & init_schema
    - calendar_management.py — マーケットカレンダー管理ユーティリティ
    - audit.py               — 監査ログ（発注→約定トレース）用スキーマ初期化
    - quality.py             — データ品質チェック群
  - strategy/                 — 戦略関連（空の初期化ファイルあり）
  - execution/                — 発注/実行関連（空の初期化ファイルあり）
  - monitoring/               — 監視関連（空の初期化ファイルあり）

（注）一部モジュールはインターフェースのみ、あるいは後続実装を想定しています。

## 実運用に関する注意と設計上のポイント
- ETL は差分取得が基本で、バックフィルで API の後出し修正を吸収します。
- 監査ログは削除しない前提で FK は ON DELETE RESTRICT 等を使用しています。order_request_id を冪等キーとして二重発注を防止する設計です。
- すべての TIMESTAMP は UTC で運用することを想定しています（audit.init_audit_schema は TimeZone を UTC に固定します）。
- news_collector は外部 URL を扱うため SSRF・巨大レスポンス・XML攻撃対策を実装していますが、追加のネットワークセキュリティ（プロキシ・アウトバウンド制限等）も推奨します。

## トラブルシューティング
- .env が読み込まれない / テスト時に自動ロードを抑制したい:
  - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- J-Quants のトークン関連で 401 が返って連続失敗する場合:
  - settings.jquants_refresh_token の値を確認し、IP/時間差の問題や API 側の障害を確認してください。
- DuckDB で初期化時にディレクトリがないエラー:
  - init_schema は親ディレクトリを自動作成しますが、権限等で失敗する場合はパスと権限を確認してください。

---

必要であれば README に実行例（cron / systemd / Docker の設定例）や CI 用のサンプル、より詳細な .env.example（例: 権限スコープやトークン取得手順）を追記できます。どの情報が欲しいか教えてください。