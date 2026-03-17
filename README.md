# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ群です。  
J-Quants API や RSS を取り込み、DuckDB に冪等に保存する ETL、品質チェック、マーケットカレンダー管理、監査ログ（発注→約定トレーサビリティ）などを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の関心領域を持つモジュール群から構成されます。

- データ取得・保存（J-Quants API、RSS ニュース）と DuckDB スキーマ
- ETL パイプライン（差分取得、バックフィル、品質チェック）
- マーケットカレンダー管理（JPX 祝日・半日・SQ）
- ニュース収集と銘柄紐付け（RSS → raw_news, news_symbols）
- 監査ログ（signal / order_request / execution のトレーサビリティ）
- 設定管理（.env / 環境変数、自動読み込み）
- （将来的に）戦略/実行/監視モジュールの場所を提供

設計上の要点:
- API レート制限・リトライ・自動トークンリフレッシュ
- データ取得時刻（fetched_at）による Look-ahead Bias 対策
- DuckDB への保存は冪等（ON CONFLICT）で実装
- RSS 収集は SSRF・XML Bomb 等を考慮した堅牢実装

---

## 主な機能一覧

- 環境変数管理（自動でプロジェクトルートの `.env` / `.env.local` を読み込む）
- J-Quants API クライアント
  - 日足（OHLCV）、財務（四半期 BS/PL）、マーケットカレンダーの取得
  - レート制御、リトライ、トークンリフレッシュ
- DuckDB スキーマ定義・初期化（Raw / Processed / Feature / Execution 層）
- ETL パイプライン（差分取得、バックフィル、品質チェック）
- 市場カレンダーの更新・営業日判定ユーティリティ
- ニュース収集（RSS → raw_news 保存、記事IDは正規化URLの SHA-256）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログスキーマ（signal_events / order_requests / executions）

---

## 動作要件

- Python 3.10+
  - （コード中で X | Y の型記法を使用しているため Python 3.10 以上が必要です）
- 必須パッケージ（例）
  - duckdb
  - defusedxml
- 標準ライブラリ: urllib, json, logging など

インストール例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# パッケージが pip 配布されている想定なら:
# pip install kabusys
# 開発環境ならソースルートで:
# pip install -e .
```

---

## 環境変数 / .env

KabuSys は起動時に自動でプロジェクトルート（.git または pyproject.toml を探索）を特定し、`.env` → `.env.local` の順にロードします（OS 環境変数が優先され、`.env.local` は上書き）。自動ロードを無効化するには:

```bash
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
```

主な必須環境変数:
- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン
- KABU_API_PASSWORD: kabuステーション API パスワード
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID

任意/デフォルト:
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 で自動 .env ロードを無効化
- KABUSYS_API_BASE_URL: kabu API のベース URL（デフォルトはローカルの想定）

例 `.env`（テンプレート）:
```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. Python 仮想環境と依存のインストール
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -U pip
   pip install duckdb defusedxml
   # もしパッケージ化されているなら:
   # pip install -e .
   ```

3. `.env` をプロジェクトルートに作成して必須値を設定

4. DuckDB スキーマ初期化
   Python REPL またはスクリプトで:
   ```python
   from kabusys.config import settings
   from kabusys.data.schema import init_schema

   conn = init_schema(settings.duckdb_path)
   # conn は duckdb.DuckDBPyConnection オブジェクト
   ```

5. （オプション）監査ログテーブル初期化
   ```python
   from kabusys.data.audit import init_audit_schema
   init_audit_schema(conn)
   ```

---

## 使い方（主要な操作例）

基本的な Python API の呼び出し例を示します。

- J-Quants の ID トークンを取得:
  ```python
  from kabusys.data.jquants_client import get_id_token
  token = get_id_token()  # settings.jquants_refresh_token を使用
  ```

- 日次 ETL を実行（市場カレンダー → 日足 → 財務 → 品質チェック）:
  ```python
  from kabusys.config import settings
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema(settings.duckdb_path)
  result = run_daily_etl(conn)  # ETLResult が返る
  print(result.to_dict())
  ```

- 市場カレンダー夜間更新ジョブ:
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  saved = calendar_update_job(conn)
  print("saved:", saved)
  ```

- RSS ニュース収集:
  ```python
  from kabusys.data.news_collector import run_news_collection
  # known_codes は銘柄抽出に使用する有効なコード集合（省略可）
  known_codes = set(code for (code,) in conn.execute("SELECT DISTINCT code FROM prices_daily").fetchall())
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)  # {source_name: 新規保存件数}
  ```

- DuckDB に保存されたテーブルへクエリ:
  ```python
  rows = conn.execute("SELECT date, code, close FROM prices_daily ORDER BY date DESC LIMIT 10").fetchall()
  ```

- 品質チェックを個別に実行:
  ```python
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=None)
  for i in issues:
      print(i)
  ```

---

## 管理コマンド / 注意点

- `.env` の自動ロードはプロジェクトルート（.git / pyproject.toml）を基準に行われます。テストやプロセス上で自動ロードを防ぎたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB のパスは環境変数 `DUCKDB_PATH`（settings.duckdb_path）で定義。デフォルトは `data/kabusys.duckdb`。
- ETL は差分更新を行います。初回は J-Quants の最小日付（2017-01-01）から取得されます。
- J-Quants API のレート制限（120 req/min）を Respect するため内部でスロットリングが行われます。
- RSS 収集は外部リダイレクト先・プライベートIP の接続をブロックするなど SSRF 対策を実装しています。
- DuckDB への挿入は基本的に冪等（ON CONFLICT）で設計されています。

---

## ディレクトリ構成

以下はパッケージ内の主要ファイル構成（src/kabusys）です:

- src/kabusys/
  - __init__.py
  - config.py               — 環境変数/設定管理（.env 自動読み込み）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得 + 保存ユーティリティ）
    - news_collector.py      — RSS 収集・前処理・保存・銘柄抽出
    - schema.py              — DuckDB スキーマ定義 & init_schema / get_connection
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py — 市場カレンダー管理・営業日ユーティリティ
    - audit.py               — 監査ログスキーマ（signal/order_request/execution）
    - quality.py             — データ品質チェック
  - strategy/
    - __init__.py            — 戦略用エントリ（将来拡張）
  - execution/
    - __init__.py            — 発注/実行モジュール（将来拡張）
  - monitoring/
    - __init__.py            — 監視 / メトリクス（将来拡張）

---

## 開発・貢献

- テスト: 現時点でのテストフレームワークは同梱されていません。ユニットテストと統合テストの追加を推奨します（特にネットワーク I/O 部分はモック可能に設計済み）。
- 安全性: RSS パーサは defusedxml を利用し、リダイレクト/レスポンスサイズ/圧縮解凍をチェックしているため、外部入力に対して堅牢にしています。
- 追加希望: ブローカー実装（kabuステーション連携）、戦略テンプレート、永続的監視ジョブなど。

---

この README は現状のコードベース（src/kabusys）を元に作成しています。実行時の詳細設定や CI/CD、テスト等はプロジェクトポリシーに応じて追加してください。質問や使い方の具体例が必要であれば、実行シナリオ（例: 初回ロード、過去データのバックフィル、デイリーバッチの crontab 設定）を教えてください。さらに具体的な手順やサンプルスクリプトを提供します。