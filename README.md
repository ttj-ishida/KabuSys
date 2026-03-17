# KabuSys

日本株向けの自動売買・データ基盤ライブラリです。J-Quants など外部データソースからデータを取得し、DuckDB に保存・管理する ETL、ニュース収集、マーケットカレンダー管理、データ品質チェック、監査ログのためのスキーマなどを提供します。

---

目次
- プロジェクト概要
- 機能一覧
- 必要条件
- セットアップ手順
- 環境変数（設定）
- 使い方（簡易例）
- 主な API
- ディレクトリ構成
- 開発・テストに関する補足

---

## プロジェクト概要

KabuSys は日本株の自動売買システム向けに設計されたライブラリ群です。主に下記を目的としています。

- J-Quants API から株価、財務、マーケットカレンダーを取得して DuckDB に保存する ETL パイプライン
- RSS からニュースを収集して前処理・DB保存するニュース収集モジュール（SSRF 対策／サイズ制限等を組み込み）
- 市場カレンダーの管理（営業日判定、前後営業日探索、夜間更新ジョブ）
- データ品質チェック（欠損・スパイク・重複・日付不整合の検出）
- 監査ログ（シグナル→発注→約定のトレース用スキーマ）
- 冪等性・トークン自動リフレッシュ・API レート制御・トランザクション管理などの実用的な設計

---

## 機能一覧

- J-Quants クライアント
  - 株価日足（OHLCV）のページネーション取得
  - 財務（四半期 BS/PL）取得
  - JPX マーケットカレンダー取得
  - レート制限（120 req/min）対応、リトライ（指数バックオフ）、401 時の自動トークンリフレッシュ
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）

- ニュース収集
  - RSS フィード取得（gzip 受信対応）
  - URL 正規化（utm_* 等のトラッキング除去）・記事ID の SHA-256 ハッシュ化による冪等性
  - SSRF 対策（スキーム検証、ホストのプライベートIP検査、リダイレクト検査）
  - メモリ保護（最大受信バイト数制限）
  - DuckDB への一括挿入（トランザクション、INSERT ... RETURNING）

- ETL パイプライン
  - 差分更新（最終取得日ベース）＋バックフィル
  - 市場カレンダー先読み（lookahead）
  - 品質チェック連携（欠損・スパイク・重複・日付不整合）

- データ品質チェック
  - 欠損（OHLC）検出
  - スパイク（前日比）検出
  - 主キー重複検出
  - 日付整合性チェック（未来日・非営業日のデータ）

- スキーマ管理（DuckDB）
  - Raw / Processed / Feature / Execution / Audit 層のテーブル定義
  - 初期化ユーティリティ（init_schema / init_audit_schema）

- カレンダー管理
  - 営業日判定、前後営業日探索、期間内営業日取得
  - 夜間カレンダー更新ジョブ

---

## 必要条件

- Python 3.10 以上（型注釈に `X | None` などを使用）
- 依存ライブラリ（一部）
  - duckdb
  - defusedxml

必要なパッケージはプロジェクトの pyproject.toml / requirements.txt にまとめてください。最低限、次をインストールしてください:

pip install duckdb defusedxml

（プロジェクト配布時には pyproject.toml / requirements を用意することを推奨します）

---

## セットアップ手順

1. リポジトリをクローンまたは展開

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install -r requirements.txt
   - または最低限:
     - pip install duckdb defusedxml

4. 環境変数の準備
   - プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD を設定すると無効化可能）。
   - 必須の環境変数は下の「環境変数（設定）」セクション参照。

5. DuckDB スキーマ初期化（例）
   - Python REPL やスクリプトで data.schema.init_schema() を呼んで DB を作成します（例を後述）。

---

## 環境変数（設定）

このライブラリは環境変数／.env を利用して設定を管理します。自動ロードの優先順位は OS 環境変数 > .env.local > .env です。自動ロードはプロジェクトルートを .git または pyproject.toml から判定して行います。

主な環境変数（必須／任意）:

- JQUANTS_REFRESH_TOKEN (必須)
  - J-Quants のリフレッシュトークン。get_id_token の元になります。

- KABU_API_PASSWORD (必須)
  - kabuステーション API 用のパスワード（実際の発注モジュールで使用）。

- KABU_API_BASE_URL (任意)
  - kabu api の base URL（デフォルト: http://localhost:18080/kabusapi）

- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)

- DUCKDB_PATH (任意)
  - DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）

- SQLITE_PATH (任意)
  - 監視用 SQLite 等（デフォルト: data/monitoring.db）

- KABUSYS_ENV (任意)
  - 動作モード: development / paper_trading / live（デフォルト: development）

- LOG_LEVEL (任意)
  - ログレベル: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）

テストや CI で自動ロードを無効化したい場合:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env の自動読み込みをスキップします。

※ .env.example がある場合はそれをコピーして .env を作成してください（.env.example は本リポジトリに含めることを推奨）。

---

## 使い方（簡易例）

以下は Python スクリプトから主要機能を利用する最小例です。

1) DuckDB スキーマ初期化

```python
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")
# 以後 conn を ETL / ニュース保存などに渡す
```

2) 日次 ETL 実行（株価・財務・カレンダー取得 + 品質チェック）

```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema
from datetime import date

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

3) ニュース収集ジョブ（RSS から raw_news へ保存）

```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
# known_codes を渡すと記事と銘柄紐付けも行う
known_codes = {"7203", "6758", "9984"}  # 例: 有効な銘柄コードセット
res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(res)
```

4) カレンダー夜間更新ジョブ

```python
from kabusys.data.calendar_management import calendar_update_job
conn = init_schema("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"saved={saved}")
```

5) J-Quants からの直接フェッチ（テスト用途など）

```python
from kabusys.data import jquants_client as jq
# モジュールは settings を参照してトークン取得やキャッシュを行います
records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
```

---

## 主な API（抜粋）

- kabusys.config.settings
  - settings.jquants_refresh_token, settings.kabu_api_password, settings.duckdb_path, settings.env, settings.log_level など

- kabusys.data.schema
  - init_schema(db_path)
  - get_connection(db_path)

- kabusys.data.jquants_client
  - get_id_token(refresh_token=None)
  - fetch_daily_quotes(...)
  - fetch_financial_statements(...)
  - fetch_market_calendar(...)
  - save_daily_quotes(conn, records)
  - save_financial_statements(conn, records)
  - save_market_calendar(conn, records)

- kabusys.data.news_collector
  - fetch_rss(url, source, timeout=30)
  - save_raw_news(conn, articles)
  - run_news_collection(conn, sources=None, known_codes=None)

- kabusys.data.pipeline
  - run_prices_etl(...)
  - run_financials_etl(...)
  - run_calendar_etl(...)
  - run_daily_etl(...)

- kabusys.data.quality
  - run_all_checks(conn, target_date=None, reference_date=None, spike_threshold=0.5)

- kabusys.data.calendar_management
  - is_trading_day(conn, d)
  - next_trading_day(conn, d)
  - prev_trading_day(conn, d)
  - get_trading_days(conn, start, end)
  - calendar_update_job(conn, lookahead_days=90)

- kabusys.data.audit
  - init_audit_schema(conn)
  - init_audit_db(path)

---

## ディレクトリ構成

（ソースツリーの主要ファイルを抜粋）

- src/kabusys/
  - __init__.py
  - config.py  — 環境変数 / 設定管理（.env 自動読み込みロジック含む）
  - data/
    - __init__.py
    - schema.py  — DuckDB スキーマ定義・初期化
    - jquants_client.py  — J-Quants API クライアント（取得・保存）
    - pipeline.py  — ETL パイプライン（差分更新・品質チェック）
    - news_collector.py  — RSS ニュース収集・前処理・保存
    - calendar_management.py — マーケットカレンダー管理
    - quality.py  — データ品質チェック
    - audit.py  — 監査ログテーブル（signal→order→execution トレース）
  - strategy/
    - __init__.py  — 戦略層（拡張ポイント）
  - execution/
    - __init__.py  — 発注実装（拡張ポイント）
  - monitoring/
    - __init__.py  — 監視・メトリクス（拡張ポイント）

---

## 開発・テストに関する補足

- 自動環境変数ロード
  - config.py はプロジェクトルート（.git または pyproject.toml を探索）を基準に .env/.env.local を自動読み込みします。CWD に依存しないためパッケージ配布後も動作します。
  - 自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（ユニットテスト等で便利です）。

- セキュリティ設計
  - news_collector は SSRF の予防、受信サイズ制限、defusedxml による XML 攻撃対策を組み込んでいます。
  - J-Quants クライアントは 401 に対する自動トークンリフレッシュ、リトライ/指数バックオフ、レート制限を実装しています。

- テスト
  - ネットワーク呼び出しはモック可能な関数（例: news_collector._urlopen）を通して行っています。ユニットテストではこれらを差し替えて外部依存を排除してください。

---

何か使い方のサンプルスクリプトや、README に追記したい別の情報（例: pyproject.toml のサンプル、CI 設定、Dockerfile、.env.example のテンプレート等）があれば教えてください。README をそれに合わせて拡張します。