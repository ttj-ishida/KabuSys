# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリ（KabuSys）。  
J-Quants API から市場データ・財務データ・マーケットカレンダーを取得し、DuckDB に保存して ETL／品質チェック／監査ログを行うことを主目的としたモジュール群を提供します。

主な想定用途:
- データレイクの構築（Raw → Processed → Feature 層）
- 日次 ETL（差分取得・バックフィル・品質チェック）
- 発注／約定トレースのための監査ログ初期化

## 特徴（機能一覧）
- J-Quants API クライアント
  - 日足（OHLCV）・四半期財務データ・JPX カレンダーの取得
  - レートリミット（120 req/min）順守（固定間隔スロットリング）
  - リトライ、指数バックオフ、401 時の自動トークンリフレッシュ
  - ページネーション対応、取得時刻（fetched_at）を UTC で記録
- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution 層のテーブル定義（冪等）
  - インデックス定義、外部キー考慮の作成順
  - 監査ログ（signal_events / order_requests / executions）を別モジュールで初期化可能
- ETL パイプライン
  - 差分取得（最終取得日に基づく）とバックフィル
  - 市場カレンダーの先読み（lookahead）
  - 品質チェック（欠損、重複、スパイク、日付不整合）
  - エラーを収集して報告（Fail-Fast ではなく全件収集）
- データ品質チェック（quality モジュール）
  - 欠損（OHLC）検出、主キー重複検出、スパイク検出（前日比閾値）、将来日付／非営業日検出
- 簡易な構成管理（config モジュール）
  - OS 環境変数および .env / .env.local の自動読み込み（プロジェクトルートを .git または pyproject.toml で探索）
  - 必須環境変数の取得ヘルパ
  - KABUSYS_ENV（development / paper_trading / live）・LOG_LEVEL サポート

## 必要条件
- Python 3.10 以上（Union 型演算子（|）を使用）
- 依存パッケージ（例）
  - duckdb
- ネットワーク接続（J-Quants API へアクセスする場合）
- J-Quants のリフレッシュトークン等の外部サービス認証情報

（実際のプロジェクトでは requirements.txt / pyproject.toml を用意してパッケージ依存を管理してください）

## セットアップ手順

1. Python 環境を作成（例: venv）
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

2. 依存パッケージをインストール
   - 最小限は duckdb が必要です。例:
   ```bash
   pip install duckdb
   ```
   - プロジェクト配布用に setup / pyproject があれば:
   ```bash
   pip install -e .
   # または
   pip install -r requirements.txt
   ```

3. 環境変数を用意する
   プロジェクトルート（.git または pyproject.toml がある場所）に `.env`（および必要に応じて `.env.local`）を配置すると自動で読み込まれます。自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   主な環境変数（必須は明記）:
   - JQUANTS_REFRESH_TOKEN (必須) — J-Quants の refresh token
   - KABU_API_PASSWORD (必須) — kabu ステーション API パスワード（発注系を使う場合）
   - SLACK_BOT_TOKEN (必須) — Slack 通知に使う場合
   - SLACK_CHANNEL_ID (必須) — Slack 通知先チャネルID
   - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
   - KABUSYS_ENV — 環境（development / paper_trading / live）（デフォルト: development）
   - LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）

   config.Settings 内のプロパティは、直接 import して利用できます:
   ```python
   from kabusys.config import settings
   print(settings.jquants_refresh_token)
   ```

## 使い方（基本例）

以下は代表的なユースケースのサンプルコードです（Python REPL やスクリプトで実行）。

- DuckDB スキーマの初期化（全テーブル）
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

# settings.duckdb_path に基づいてファイルを作成（デフォルト data/kabusys.duckdb）
conn = init_schema(settings.duckdb_path)
```

- 監査ログテーブルを初期化（既存接続へ追加）
```python
from kabusys.data.audit import init_audit_schema

# すでに init_schema で得た conn を渡す
init_audit_schema(conn)
```

- J-Quants のトークン取得 / データ取得 / 保存
```python
from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes, save_daily_quotes

id_token = get_id_token()  # settings.jquants_refresh_token を使用
records = fetch_daily_quotes(id_token=id_token, date_from=date(2023,1,1), date_to=date(2023,1,31))
saved = save_daily_quotes(conn, records)
print(f"saved {saved} rows")
```

- 日次 ETL 実行（差分取得・保存・品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)  # target_date を省略すると今日
print(result.to_dict())
if result.has_errors:
    # ログ送信やアラート処理を行う
    pass
```

- 品質チェック単体実行
```python
from kabusys.data.quality import run_all_checks

issues = run_all_checks(conn, target_date=None)  # 日付を指定するとその日のデータを対象にする
for issue in issues:
    print(issue.check_name, issue.severity, issue.detail)
```

## API（主要モジュールと関数）
- kabusys.config
  - settings: 環境設定オブジェクト（プロパティ経由で値を取得）
- kabusys.data.jquants_client
  - get_id_token(refresh_token=None)
  - fetch_daily_quotes(id_token=None, code=None, date_from=None, date_to=None)
  - fetch_financial_statements(...)
  - fetch_market_calendar(...)
  - save_daily_quotes(conn, records)
  - save_financial_statements(conn, records)
  - save_market_calendar(conn, records)
- kabusys.data.schema
  - init_schema(db_path)
  - get_connection(db_path)
- kabusys.data.pipeline
  - run_daily_etl(conn, target_date=None, ...)
  - run_prices_etl(...)
  - run_financials_etl(...)
  - run_calendar_etl(...)
- kabusys.data.audit
  - init_audit_schema(conn)
  - init_audit_db(db_path)
- kabusys.data.quality
  - run_all_checks(conn, target_date=None, reference_date=None, spike_threshold=...)

（strategy / execution / monitoring パッケージは骨組みとして用意されています。戦略や実行ロジックは各プロジェクトで実装してください。）

## .env 自動読み込みについて
- 起点: このパッケージのファイル位置から親ディレクトリを遡り、.git または pyproject.toml を見つけたディレクトリをプロジェクトルートとみなします。
- 読み込み順序: OS 環境変数 > .env.local > .env
- 無効化: 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると自動読み込みをスキップします（テスト等で利用）。
- .env のパースは一般的な形式（例: KEY=val, export KEY=val, クォート・エスケープ・コメントの一部対応）をサポートします。

## ディレクトリ構成
リポジトリの主要ファイル・ディレクトリ構成（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py              — 環境設定／.env 読み込みロジック
  - data/
    - __init__.py
    - jquants_client.py    — J-Quants API クライアント（取得／保存）
    - schema.py            — DuckDB スキーマ定義・初期化
    - pipeline.py          — ETL パイプライン（差分取得・品質チェック）
    - audit.py             — 監査ログ（signal/order/execution）初期化
    - quality.py           — データ品質チェック
  - strategy/
    - __init__.py          — 戦略層（拡張用）
  - execution/
    - __init__.py          — 発注実行層（拡張用）
  - monitoring/
    - __init__.py          — 監視用モジュール（拡張用）

## 運用上の注意 / ベストプラクティス
- 認証情報は必ず安全に管理（.env はバージョン管理から除外すること）。
- DuckDB ファイルはバックアップ／バージョニング方針を決める。大容量データではファイルサイズに注意。
- 本ライブラリの ETL は「差分取得＋バックフィル」を行いますが、初回ロードや大幅なデータ再作成が必要な場合は date_from を明示的に指定して実行してください。
- run_daily_etl は内部で複数のステップを実行します。各ステップで例外が発生しても可能な限り他ステップを続行し、エラーは ETLResult.errors に集約されます。
- レート制限（120 req/min）に従っていますが、実運用では J-Quants の利用規約／レート制約の確認を行ってください。

## 貢献・拡張
- strategy / execution / monitoring パッケージは拡張ポイントです。戦略ロジック、ポジション管理、Broker 接続（kabu ステーション連携）などは各自実装してください。
- 品質チェック（quality）は SQL ベースで実装されているため、新しいチェックは関数を追加し run_all_checks に組み込むことで拡張できます。

---

問題点の検出や実装に関する質問、README に追加したい使用例や運用手順があれば教えてください。README を用途に合わせて追記・調整します。