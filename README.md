# KabuSys

日本株向け自動売買プラットフォームのコアライブラリ（KabuSys）。  
データ取得（J-Quants）、ETL、データ品質チェック、ニュース収集、監査ログ（発注→約定トレース）などの基盤機能を提供します。

目次
- プロジェクト概要
- 主な機能
- 前提条件
- セットアップ手順
- 環境変数（.env）
- 使い方（主要 API 例）
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は日本株の自動売買システムのバックエンド基盤モジュール群です。  
主に以下を提供します。

- J-Quants API からのデータ取得（株価日足、財務データ、マーケットカレンダー）
- DuckDB を用いたデータスキーマ（Raw / Processed / Feature / Execution / Audit）
- ETL パイプライン（差分取得・バックフィル・品質チェック）
- RSS からのニュース収集と銘柄紐付け（SSRF/サイズ上限対策済み）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（シグナル → 発注 → 約定 のトレース可能なテーブル群）

設計上の特徴として、API レート制御・リトライ、冪等保存（ON CONFLICT）、Look-ahead bias の抑制（fetched_at 記録）などが組み込まれています。

---

## 主な機能一覧

- data.jquants_client
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_* 関数で DuckDB に冪等保存
  - レートリミット（120 req/min）、リトライ、401 時のトークン自動リフレッシュ対応
- data.schema
  - DuckDB の完全なスキーマ定義（Raw / Processed / Feature / Execution）
  - init_schema(db_path) による初期化
- data.pipeline
  - run_prices_etl / run_financials_etl / run_calendar_etl
  - run_daily_etl: 日次 ETL（差分取得・バックフィル・品質チェック）
- data.news_collector
  - RSS フェッチ（gzip 対応、XML 攻撃対策）、記事の正規化・ID 生成
  - save_raw_news / save_news_symbols / run_news_collection
- data.calendar_management
  - market_calendar の管理・営業日判定（is_trading_day / next_trading_day / prev_trading_day 等）
- data.quality
  - 欠損・スパイク・重複・日付不整合チェック
- data.audit
  - 監査用テーブル群（signal_events, order_requests, executions）と初期化ユーティリティ

---

## 前提条件

- Python 3.10 以上（typing の | 型等を使用）
- 必要な主要パッケージ（例）:
  - duckdb
  - defusedxml
- ネットワークアクセス（J-Quants API / RSS フィード など）
- J-Quants / Slack / kabu API の認証情報（環境変数で指定）

必要パッケージはプロジェクトに合わせて requirements.txt を用意している想定です。最小構成例:

pip install duckdb defusedxml

---

## セットアップ手順

1. リポジトリをチェックアウト／コピー

2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate

3. 必要パッケージのインストール
   - pip install duckdb defusedxml

   （プロジェクトで requirements.txt / pyproject.toml があればそれに従ってください）

4. 環境変数の準備
   - プロジェクトルートに `.env` を作成（下の「環境変数」節を参照）
   - 自動で .env が読み込まれます（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できます）

5. DuckDB スキーマの初期化
   - Python REPL またはスクリプト内で以下を実行して DB を初期化します（例: data/kabusys.duckdb）:
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")

6. 監査ログスキーマの初期化（任意）
   - from kabusys.data.audit import init_audit_schema
     init_audit_schema(conn)

---

## 環境変数（.env 例）

以下を `.env` に設定してください（必要なものは運用機能によって異なります）。

例（.env）:
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_api_password
# KABU_API_BASE_URL はデフォルト http://localhost:18080/kabusapi
KABU_API_BASE_URL=http://localhost:18080/kabusapi
SLACK_BOT_TOKEN=your_slack_bot_token
SLACK_CHANNEL_ID=your_slack_channel_id
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development   # 有効値: development, paper_trading, live
LOG_LEVEL=INFO

注意:
- settings.jquants_refresh_token / slack / kabu 等は必須としている箇所があるため、必要に応じて設定してください。
- 自動ロードを無効にする場合: export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## 使い方（主要 API とワークフロー例）

以下は代表的な使い方の抜粋です。実際はエラーハンドリングやログ設定を追加してください。

1) DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema

# ファイル DB を初期化（親ディレクトリを自動作成）
conn = init_schema("data/kabusys.duckdb")
```

2) 日次 ETL を実行（デフォルトは今日）
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)  # ETLResult を返す
print(result.to_dict())
```

3) ニュース収集ジョブの実行
```python
from kabusys.data.news_collector import run_news_collection

# sources を指定しない場合は DEFAULT_RSS_SOURCES を使用
# known_codes: 銘柄抽出に使う valid コード集合（存在しなければ紐付けスキップ）
known_codes = {"7203", "6758", "9984"}  # 例：実運用では DB から取得
results = run_news_collection(conn, known_codes=known_codes)
print(results)  # {source_name: saved_count}
```

4) 監査ログスキーマ（発注・約定トレース）を有効化
```python
from kabusys.data.audit import init_audit_schema

# 既存の conn に監査用テーブルを追加
init_audit_schema(conn)  # transactional=False（既にトランザクション管理がある場合）
# または init_audit_schema(conn, transactional=True)
```

5) データ品質チェックを個別に実行
```python
from kabusys.data import quality
issues = quality.run_all_checks(conn)
for i in issues:
    print(i.check_name, i.severity, i.detail)
```

6) J-Quants から直接データを取得する（テストやユーティリティ用）
```python
from kabusys.data import jquants_client as jq

# id_token を省略すると settings の refresh token を使って自動取得・キャッシュされる
daily = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
# 保存する場合
jq.save_daily_quotes(conn, daily)
```

---

## 運用上のポイント

- レート制御 / リトライ: jquants_client は 120 req/min を守る実装（内部で待機）とリトライロジックを備えています。
- トークン管理: 401 応答時にリフレッシュトークンを使って id_token を再取得してリトライします。
- ETL は差分取得とバックフィル（デフォルト3日）を行い、API 後出し修正を吸収する設計です。
- ニュース収集は SSRF 対策（スキーム検証・プライベート IP チェック・リダイレクト検査）や XML 検査対策を実装しています。
- DuckDB への書き込みは冪等（ON CONFLICT）あるいは INSERT ... RETURNING を活用して正確な保存数を把握します。

---

## ディレクトリ構成

リポジトリ内の主要ファイル（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / 設定管理（自動 .env ロード、settings）
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API クライアント（取得・保存）
    - news_collector.py             — RSS ニュース収集・前処理・DB 保存
    - schema.py                     — DuckDB スキーマ定義・初期化
    - pipeline.py                   — ETL パイプライン（差分取得・品質チェック）
    - calendar_management.py        — market_calendar 管理 / 営業日ロジック
    - audit.py                      — 監査ログ（signal/order/execution）初期化
    - quality.py                    — データ品質チェック
    - (他モジュール)
  - strategy/
    - __init__.py                   — 戦略層用プレースホルダ
  - execution/
    - __init__.py                   — 発注実行層用プレースホルダ
  - monitoring/
    - __init__.py                   — 監視関連プレースホルダ

---

## 補足 / 開発メモ

- テストや CI で .env 自動ロードを無効化したい場合は、環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- settings.KABUSYS_ENV の有効値: "development", "paper_trading", "live"
- LOG_LEVEL は "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL" のいずれか
- Python の型ヒントは 3.10 以降の構文を使用しているため、ランタイムは 3.10 以上を推奨します。

---

必要であれば README に以下の追加情報を追記できます:
- CI / tests 実行方法
- サンプル .env.example ファイル
- よくあるトラブルシュート集（DB アクセス権限、ネットワーク制限等）
- 実運用上の安全ガイド（発注リスク管理、paper/live 切替手順）

追加で記載したい項目があれば教えてください。