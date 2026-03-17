# KabuSys

日本株向けの自動売買／データ基盤ライブラリ（KabuSys）。  
J-Quants API からの市場データ取得、DuckDB ベースのスキーマ管理、ETL パイプライン、ニュース収集、データ品質チェック、監査ログなどを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買システムを支えるデータ基盤とユーティリティ群です。主に以下を提供します。

- J-Quants API クライアント（株価、財務、マーケットカレンダー）
- DuckDB を使ったスキーマ定義・初期化
- 日次 ETL パイプライン（差分取得・バックフィル・品質チェック）
- RSS ベースのニュース収集と記事→銘柄の紐付け
- マーケットカレンダー管理（営業日判定・次/前営業日取得）
- 監査ログ（シグナル→発注→約定 のトレーサビリティ）
- 環境変数管理（.env の自動読み込み、設定ラッパー）

設計上のポイント:
- API レート制御（J-Quants: 120 req/min）とリトライ（指数バックオフ）
- データ取得時の fetched_at による Look‑ahead Bias の防止
- DuckDB への冪等保存（ON CONFLICT を利用）
- ニュース収集時の SSRF・XML脆弱性対策、サイズ上限（メモリ DoS 対策）
- 品質チェックは Fail‑Fast しない（問題を全件収集して報告）

---

## 主な機能一覧

- data/jquants_client.py
  - get_id_token, fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes, save_financial_statements, save_market_calendar（DuckDB への保存）
  - レートリミッタ、リトライ、トークン自動リフレッシュ
- data/schema.py
  - DuckDB の全テーブル定義と init_schema / get_connection
- data/pipeline.py
  - 日次 ETL（run_daily_etl） / prices/financials/calendar の差分 ETL
  - 差分取得・バックフィル・品質チェック統合
- data/news_collector.py
  - RSS フィード取得（fetch_rss）、前処理、ID 生成、raw_news 保存、銘柄抽出・紐付け
  - SSRF 対策、gzip 解凍制限、XML の安全パース（defusedxml）
- data/calendar_management.py
  - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, calendar_update_job
- data/quality.py
  - 欠損・重複・スパイク・日付不整合などのチェック（QualityIssue を返す）
- data/audit.py
  - 監査用テーブル（signal_events, order_requests, executions）と初期化
- config.py
  - .env または環境変数から設定を読み込み、settings オブジェクトでアクセス

---

## 必要環境（依存関係）

- Python 3.9+
- duckdb
- defusedxml

（プロジェクトに requirements.txt / pyproject.toml がある想定で、適宜追加の依存が必要になる場合があります）

インストール例（開発環境）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# パッケージとしてローカルインストールする場合
# pip install -e .
```

---

## セットアップ手順

1. リポジトリをクローン / ローカルにコピー。

2. Python 仮想環境を用意して依存をインストール（上記参照）。

3. DuckDB DB パス等を設定するための環境変数を用意。プロジェクトルートに `.env` を置くと自動読み込みされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。

推奨の .env（例）:
```
# J-Quants
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

# kabu API (kabuステーション) - 発注周りで利用
KABU_API_PASSWORD=your_kabu_password
# KABU_API_BASE_URL はデフォルト "http://localhost:18080/kabusapi" を使用

# Slack 通知
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567

# DB パス
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# 実行環境: development | paper_trading | live
KABUSYS_ENV=development

# ログレベル
LOG_LEVEL=INFO
```

環境変数名は `kabusys.config.Settings` のプロパティに対応しています。必須項目（未設定だと例外）:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

必要に応じて `.env.local` を用いてローカル上書きが可能です。

---

## 使い方（クイックスタート）

以下は Python REPL あるいはスクリプトから使う基本例です。

1) DuckDB スキーマ初期化
```python
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")
# またはインメモリ:
# conn = schema.init_schema(":memory:")
```

2) J-Quants トークン取得（通常は settings から自動取得されます）
```python
from kabusys.data import jquants_client as jq
id_token = jq.get_id_token()  # settings.jquants_refresh_token を使用して取得
```

3) 日次 ETL を実行（株価・財務・カレンダーの差分取得 + 品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn)  # target_date を指定可能
print(result.to_dict())
```

4) ニュース収集ジョブ実行
```python
from kabusys.data.news_collector import run_news_collection
# known_codes を渡すと記事に含まれる4桁銘柄コードを紐付ける（set of strings）
res = run_news_collection(conn, known_codes={"7203","6758"})
print(res)  # {source_name: saved_count}
```

5) カレンダーの夜間更新（バッチ）
```python
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn)
print("saved", saved)
```

6) 監査ログテーブルの初期化（既存 conn に追加）
```python
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn)
```

7) 品質チェックのみ実行
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn)
for issue in issues:
    print(issue.check_name, issue.severity, issue.detail)
```

---

## 実装上の注意点 / 動作方針

- ETL の差分取得は DB 内の最終取得日から自動算出され、デフォルトで直近数日分をバックフィルして API 側の後出し修正を吸収します。
- J-Quants API 呼び出しは 120 req/min のレート制限に従うように固定間隔スロットリングで制御されます（_RateLimiter）。
- J-Quants へのリクエストはリトライ（指数バックオフ）を行います。401 受信時はリフレッシュトークンで自動更新し1回リトライします。
- ニュース収集は SSRF、XML Bomb、過大レスポンス等に対する複数の防御を実装しています（_SSRFBlockRedirectHandler、defusedxml、MAX_RESPONSE_BYTES 等）。
- DuckDB への保存はできるだけ冪等（ON CONFLICT DO UPDATE / DO NOTHING）になるよう設計されています。
- 品質チェックは重大度を保持する QualityIssue を返します。ETL はチェックでエラーが出ても基本的に継続します（呼び出し元で判断）。

---

## ディレクトリ構成

（主要なファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py               -- 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py     -- J-Quants API クライアント（取得・保存ロジック）
    - news_collector.py     -- RSS ニュース収集・保存・銘柄抽出
    - pipeline.py           -- ETL パイプライン（run_daily_etl 等）
    - schema.py             -- DuckDB スキーマ定義・init_schema
    - calendar_management.py-- マーケットカレンダー管理（営業日判定等）
    - quality.py            -- データ品質チェック
    - audit.py              -- 監査ログテーブル定義と初期化
  - strategy/               -- 戦略モジュール（拡張箇所）
    - __init__.py
  - execution/              -- 発注／約定管理（拡張箇所）
    - __init__.py
  - monitoring/             -- 監視・モニタリング（拡張箇所）
    - __init__.py

---

## テスト / デバッグのヒント

- 自動で .env をプロジェクトルートから読み込みます。テストで自動読み込みを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- jquants_client のネットワーク呼び出しにはタイムアウトやリトライが入るため、ユニットテストではネットワーク部分（_urlopen / urllib）や get_id_token をモックすることを推奨します。
- news_collector._urlopen や fetch_rss の外部呼び出しはモック可能に設計されています（テスト用に置換してください）。
- DuckDB はインメモリ ":memory:" でテスト用 DB を作れます（schema.init_schema(":memory:")）。

---

## 貢献 / ライセンス

本 README はコードベースの要約を目的としたものであり、実際のパッケージ配布時は pyproject.toml / requirements を整備し、CI・テストを追加してください。ライセンスやコントリビューションに関する記載が必要であればリポジトリ方針に従って追記してください。

---

不足しているサンプルや具体的な運用手順（例: 発注フロー、Slack 通知の実装例、戦略の雛形）を追加希望であれば、用途に合わせた README の拡張（運用手順や例スクリプト）を作成します。必要な内容を教えてください。