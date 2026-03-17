# KabuSys

日本株向けの自動売買／データ基盤ライブラリです。  
J-Quants や RSS などからマーケットデータ・ニュースを取得して DuckDB に格納し、ETL・品質チェック・カレンダー管理・監査ログなどの基盤機能を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下を主な目的としたモジュュール群を含む Python パッケージです。

- J-Quants API から株価（OHLCV）、財務データ、JPX マーケットカレンダーを安全に取得するクライアント
- RSS からのニュース収集と記事→銘柄の紐付け
- DuckDB を用いたスキーマ定義・初期化
- 日次 ETL パイプライン（差分取得・バックフィル・品質チェック）
- マーケットカレンダーの夜間更新・営業日判定ロジック
- 監査ログ（signal → order_request → execution）の専用スキーマ
- 設定管理（環境変数 / .env ファイルの自動ロード）

設計上のポイント:
- API レート制限・リトライ・トークン自動リフレッシュを組み込んだ堅牢なクライアント
- DuckDB への保存は冪等（ON CONFLICT）で実行
- RSS 取得では SSRF / XML Bomb / 大容量レスポンス対策を考慮
- 品質チェックは Fail-Fast ではなく問題を集めて報告

---

## 主な機能一覧

- data.jquants_client
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar
  - トークン自動取得・キャッシュ、レートリミット、リトライ（指数バックオフ）
- data.news_collector
  - fetch_rss / save_raw_news / save_news_symbols
  - URL 正規化、記事ID は正規化URLの SHA256（先頭32文字）で冪等保証
  - SSRF / XML 脆弱性対策、レスポンスサイズ制限
- data.schema
  - DuckDB のテーブル定義（Raw / Processed / Feature / Execution 層）
  - init_schema(db_path) で初期化
- data.pipeline
  - 差分 ETL（run_daily_etl）: カレンダー → 株価 → 財務 → 品質チェック
  - run_prices_etl / run_financials_etl / run_calendar_etl 単体実行も可能
- data.calendar_management
  - market_calendar の夜間更新ジョブ
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day
- data.audit
  - 監査用スキーマ（signal_events, order_requests, executions 等）
  - init_audit_schema / init_audit_db
- data.quality
  - 欠損、スパイク、重複、日付不整合のチェック関数
  - run_all_checks でまとめて実行
- config
  - 環境変数・.env の自動ロード・検証
  - settings オブジェクトから各種設定へアクセス

---

## セットアップ手順

前提:
- Python 3.10 以上を推奨（型注釈に新しい構文を使用）
- 必要なライブラリ（代表例）: duckdb, defusedxml

1. 仮想環境の作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存関係のインストール
   - requirements.txt がある場合:
     - pip install -r requirements.txt
   - ない場合は最低限以下をインストールしてください:
     - pip install duckdb defusedxml

3. パッケージを開発インストール（プロジェクトルートに pyproject.toml がある想定）
   - pip install -e .

4. 環境変数の設定
   - プロジェクトルートに `.env` または `.env.local` を置くと、自動でロードされます（.git または pyproject.toml を起点に探索）。
   - 自動ロードを無効化する場合: export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

必須の環境変数（一部）
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabu API パスワード（必須）
- SLACK_BOT_TOKEN — Slack 通知用トークン（必須）
- SLACK_CHANNEL_ID — Slack チャネル ID（必須）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — environment: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

例 (.env)
```
JQUANTS_REFRESH_TOKEN=xxxx
KABU_API_PASSWORD=secret
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（基本的な例）

以下は最小限の利用例です。Python スクリプト内で利用します。

1. DuckDB スキーマ初期化
```python
from kabusys.config import settings
from kabusys.data import schema

conn = schema.init_schema(settings.duckdb_path)  # ファイルを作成して全テーブルを作る
```

2. 日次 ETL を実行（市場カレンダー・株価・財務・品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)  # target_date を指定しないと今日が対象
print(result.to_dict())
```

3. ニュース収集ジョブ（RSS 取得 → raw_news 保存 → 銘柄紐付け）
```python
from kabusys.data.news_collector import run_news_collection

# known_codes は銘柄抽出で有効なコードの集合（例: データベースから読み出した銘柄一覧）
known_codes = {"7203", "6758", "9984"}
results = run_news_collection(conn, sources=None, known_codes=known_codes)
print(results)  # {source_name: 新規保存件数}
```

4. カレンダーの夜間更新ジョブ（単体）
```python
from kabusys.data.calendar_management import calendar_update_job

saved = calendar_update_job(conn)
print(f"saved calendar rows: {saved}")
```

5. 監査ログ用 DB 初期化（監査専用 DB を別ファイルで使う場合）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
```

注意点:
- jquants_client は内部でレート制限とリトライを行いますが、大量の一括取得を行う際は十分な配慮をお願いします。
- テストや特殊用途では、id_token を明示的に注入して API 呼び出しをモックできます（fetch_* 関数は id_token 引数を受け取ります）。
- news_collector の HTTP 部分はテスト用に _urlopen を差し替えてモック可能です。

---

## よく使う API の説明（抜粋）

- settings (kabusys.config.settings)
  - settings.jquants_refresh_token
  - settings.kabu_api_password
  - settings.kabu_api_base_url
  - settings.slack_bot_token / settings.slack_channel_id
  - settings.duckdb_path / settings.sqlite_path
  - settings.env / settings.is_live / settings.is_paper / settings.is_dev
  - settings.log_level

- data.schema
  - init_schema(db_path) → DuckDB 接続（テーブル作成）
  - get_connection(db_path) → 接続（スキーマ初期化は行わない）

- data.pipeline
  - run_daily_etl(conn, target_date=None, id_token=None, run_quality_checks=True, ...)

- data.news_collector
  - fetch_rss(url, source, timeout=30) → 記事リスト
  - save_raw_news(conn, articles) → 新規保存記事ID のリスト
  - run_news_collection(conn, sources=None, known_codes=None)

- data.calendar_management
  - is_trading_day(conn, d)
  - next_trading_day(conn, d)
  - prev_trading_day(conn, d)
  - get_trading_days(conn, start, end)
  - calendar_update_job(conn, lookahead_days=90)

- data.audit
  - init_audit_schema(conn, transactional=False)
  - init_audit_db(db_path)

---

## ディレクトリ構成

主要ファイル・モジュール（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / .env の読み込み・Settings
  - data/
    - __init__.py
    - schema.py              — DuckDB スキーマ定義・init_schema
    - jquants_client.py      — J-Quants API クライアント（取得＋保存）
    - pipeline.py            — ETL パイプラインのエントリポイント
    - news_collector.py      — RSS 収集・前処理・保存
    - calendar_management.py — マーケットカレンダー管理と判定ロジック
    - quality.py             — データ品質チェック
    - audit.py               — 監査ログスキーマの初期化
  - strategy/
    - __init__.py            — 戦略層（拡張ポイント）
  - execution/
    - __init__.py            — 発注・実行ロジック（拡張ポイント）
  - monitoring/
    - __init__.py            — 監視用コード（拡張ポイント）

プロジェクトルートに .env / .env.local / pyproject.toml / .git があると config が自動で .env を読み込みます。

---

## 運用上の注意・トラブルシューティング

- .env 自動ロード:
  - プロジェクトルートはこのパッケージのファイル位置から親ディレクトリを上がって `.git` または `pyproject.toml` を探して決定します。CI やテストで自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- API トークン関連:
  - J-Quants のトークンは settings.jquants_refresh_token に設定してください。jquants_client はリフレッシュトークンから id_token を取得し、401 時に自動リフレッシュします。
- DuckDB ファイル:
  - デフォルトは `data/kabusys.duckdb`。親ディレクトリがない場合は自動作成されます。
- 大量データ取得時:
  - J-Quants のレート制限（120 req/min）に注意。jquants_client は固定間隔のレートリミッタを実装していますが、外部ジョブで並列実行すると制限を超える可能性があります。
- ニュース収集:
  - RSS の取得時にリダイレクトで内部アドレスが返ってきた場合は拒否されます（SSRF 対策）。また、レスポンスサイズ上限（デフォルト 10MB）を超えると取得をスキップします。

---

## 今後の拡張ポイント（参考）

- strategy / execution モジュールに具体的な戦略・発注アダプタを実装
- Slack などへの通知機能の実装（settings に Slack トークンはあるが利用箇所は実装次第）
- モニタリングダッシュボード（monitoring モジュールの拡張）
- テスト用の fixtures / モックユーティリティの整備

---

この README はコードベースから生成した概要です。詳細な仕様（DataPlatform.md など）や運用手順はプロジェクトのドキュメントを参照してください。何か追記・修正したい箇所があれば教えてください。