# KabuSys

日本株向けの自動売買データ基盤・ETL・監査ライブラリ群。  
J-Quants API や RSS ニュースを収集して DuckDB に保存し、品質チェック・カレンダー管理・監査ログを備えたデータパイプラインを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株自動売買システム向けのデータ基盤コンポーネントを集めたライブラリです。主な目的は以下です。

- J-Quants API から株価（OHLCV）、財務データ、JPX カレンダーを取得して DuckDB に保存
- RSS フィードからニュース記事を収集し正規化して保存、銘柄コードとの紐付けを行う
- ETL（差分更新・バックフィル）パイプラインを提供
- データ品質チェック（欠損・スパイク・重複・日付不整合）を実行
- マーケットカレンダーの管理（営業日判定、next/prev など）
- 監査ログ（シグナル→発注→約定のトレース）用スキーマを提供

設計上のポイント：
- API レート制限順守（J-Quants：120 req/min）、指数バックオフ付きリトライ、401 時の自動トークンリフレッシュ
- Look-ahead bias 対策のため fetched_at を UTC で記録
- DuckDB 側は冪等操作（ON CONFLICT）で重複を排除
- RSS 収集は SSRF / XML Bomb / Gzip bomb 等の脅威に配慮した実装

---

## 機能一覧

- データ取得（src/kabusys/data/jquants_client.py）
  - 株価日足（OHLCV）のページネーション取得
  - 財務データ（四半期 BS/PL）
  - JPX マーケットカレンダー
  - トークン管理・リトライ・レートリミット対応

- ニュース収集（src/kabusys/data/news_collector.py）
  - RSS フィード取得（gzip サポート）
  - URL 正規化、トラッキングパラメータ除去、記事IDの SHA-256 ハッシュ化
  - SSRF 対策、受信サイズ制限、defusedxml による XML 攻撃対策
  - DuckDB へ冪等保存（INSERT ... ON CONFLICT DO NOTHING / RETURNING）
  - 記事と銘柄コードの紐付け（news_symbols）

- スキーマ管理（src/kabusys/data/schema.py）
  - Raw / Processed / Feature / Execution 層のテーブル DDL を定義
  - 初期化関数 init_schema(db_path) / get_connection()

- ETL パイプライン（src/kabusys/data/pipeline.py）
  - 差分取得、バックフィル、品質チェックの統合 run_daily_etl()
  - 個別ジョブ: run_prices_etl, run_financials_etl, run_calendar_etl

- カレンダー管理（src/kabusys/data/calendar_management.py）
  - 営業日判定、next/prev_trading_day、営業日リスト取得
  - 夜間バッチ更新 job（calendar_update_job）

- 品質チェック（src/kabusys/data/quality.py）
  - 欠損データ、スパイク（前日比）、重複、日付不整合の検出
  - QualityIssue レポートを返す

- 監査ログ（src/kabusys/data/audit.py）
  - signal_events / order_requests / executions 等、監査用スキーマ
  - init_audit_schema / init_audit_db を提供（UTC タイムゾーン固定）

---

## 要件

- Python 3.10+
  - 型注釈で PEP 604（|）を使用しているため Python 3.10 以上を想定
- 必須パッケージ（例）
  - duckdb
  - defusedxml

（その他は標準ライブラリ（urllib, gzip, hashlib, socket, ipaddress 等）で実装されています）

インストール例:
```bash
python -m pip install "duckdb" "defusedxml"
```

---

## セットアップ手順

1. リポジトリをクローン／展開してプロジェクトルート（.git または pyproject.toml がある場所）に移動。

2. 必要なパッケージをインストール:
   - pip を使用:
     pip install duckdb defusedxml

3. 環境変数の設定:
   - プロジェクトルートに `.env`（および必要なら `.env.local`）を作成すると、自動的に読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD を設定すれば自動ロードを抑制可能）。
   - 必須項目は後述の「環境変数」を参照。

4. DuckDB スキーマ初期化（例）:
   - Python REPL やスクリプトから:
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")

5. 監査ログ用スキーマ初期化（必要な場合）:
   - from kabusys.data.audit import init_audit_db
     audit_conn = init_audit_db("data/kabusys_audit.duckdb")

---

## 環境変数

自動ロードの挙動:
- プロジェクトルート（.git または pyproject.toml）を基準に `.env` → `.env.local` の順で読み込みます（OS 環境変数を保護）。  
- 自動ロードを無効化する場合:
  KABUSYS_DISABLE_AUTO_ENV_LOAD=1

主要な環境変数:
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL — kabu ステーションのベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用トークン
- SLACK_CHANNEL_ID (必須) — Slack 通知対象チャンネル ID
- DUCKDB_PATH — デフォルト DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — environment ('development' | 'paper_trading' | 'live'), デフォルト 'development'
- LOG_LEVEL — ログレベル ('DEBUG'|'INFO'|'WARNING'|'ERROR'|'CRITICAL')

サンプル .env:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（簡単なコード例）

- DuckDB スキーマ初期化:
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")  # ディレクトリは自動作成されます
```

- 日次 ETL 実行（市場カレンダー取得 → 株価・財務差分取得 → 品質チェック）:
```python
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn)  # target_date を指定可能
print(result.to_dict())
```

- J-Quants の ID トークン取得（必要に応じて明示的に取得）:
```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # settings.jquants_refresh_token を使用
```

- 個別取得（例: 指定銘柄の日足取得と保存）:
```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes, _get_cached_token
id_token = _get_cached_token()
records = fetch_daily_quotes(id_token=id_token, code="7203", date_from=..., date_to=...)
saved = save_daily_quotes(conn, records)
```

- RSS ニュース収集（全ソース）:
```python
from kabusys.data.news_collector import run_news_collection
# known_codes は有効とみなす銘柄コードの集合（抽出に使用）
results = run_news_collection(conn, known_codes={"7203", "6758"})
```

- ニュースを直接フェッチして保存（個別ソース）:
```python
from kabusys.data.news_collector import fetch_rss, save_raw_news
articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
new_ids = save_raw_news(conn, articles)
```

- 監査 DB 初期化:
```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/kabusys_audit.duckdb")
```

注意点:
- J-Quants API 呼び出しは内部でレート制御・リトライ・トークン自動更新を行います。
- run_daily_etl は各ステップで例外をキャッチして継続する設計です。戻り値の ETLResult でエラーや品質問題を確認してください。
- news_collector は RSS の HTTP レスポンスサイズや圧縮内容、リダイレクト先のホストを検査します（SSRF 対策）。

---

## ディレクトリ構成（主要ファイル）

プロジェクトの主要なファイル構成（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py  — 環境変数設定管理（.env 自動ロード、Settings クラス）
  - data/
    - __init__.py
    - jquants_client.py  — J-Quants API クライアント（取得・保存ロジック）
    - news_collector.py  — RSS ニュース収集・前処理・保存
    - schema.py          — DuckDB スキーマ定義・初期化
    - pipeline.py        — ETL パイプライン（差分取得・統合処理）
    - calendar_management.py — マーケットカレンダー管理、営業日判定
    - audit.py           — 監査ログスキーマの初期化
    - quality.py         — データ品質チェック
  - strategy/            — （空のパッケージ、戦略モジュール配置用）
  - execution/           — （空のパッケージ、発注・実行関連配置用）
  - monitoring/          — （空のパッケージ、監視機能用）

DuckDB テーブルカテゴリ:
- Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
- Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
- Feature Layer: features, ai_scores
- Execution Layer: signals, signal_queue, orders, trades, positions, portfolio_*

監査（audit）用テーブル:
- signal_events, order_requests, executions

---

## 補足・運用上の注意

- 環境変数を `.env` に置く場合、OS 環境変数が優先されます（.env の上書きは .env.local のみ可能）。
- J-Quants のレート制限を超えないよう内部で固定間隔スロットリングを実装していますが、並列プロセスからの同時呼び出しには注意が必要です（モジュール内の単一インメモリ RateLimiter はプロセス内での制御）。
- DuckDB はプロジェクト用途に適切ですが、マルチプロセス同時書き込みなどのシナリオではロックや別の DB を検討してください。
- news_collector の URL 検証や DNS 解決は安全性を優先するため一部ホストの取得を拒否することがあります（プライベート IP など）。

---

README は以上です。必要であれば以下も作成できます：
- サンプル .env.example
- requirements.txt / pyproject.toml のテンプレート
- 小さな CLI スクリプト（日次 ETL / カレンダー更新 / ニュース収集 の実行ラッパー）