# KabuSys

バージョン: 0.1.0

KabuSys は日本株向けの自動売買プラットフォーム／データ基盤のプロトタイプです。  
J-Quants からデータを取得して DuckDB に格納し、データ品質チェック、特徴量生成、リサーチ（ファクター分析）、ニュース収集、監査ログ（発注→約定トレース）などを行うためのモジュール群を提供します。

---

## 主要な目的・概要

- J-Quants API から株価・財務・マーケットカレンダーを取得して DuckDB に保存（冪等）
- ETL（差分取得・バックフィル・品質チェック）パイプラインの提供
- ニュース RSS 収集と銘柄紐付け（SSRF 対策・トラッキング除去）
- 研究用ファクター計算（モメンタム／バリュー／ボラティリティ）と評価（IC 等）
- 発注・監査用スキーマ（監査ログ／order_requests／executions など）
- 小規模なユーティリティ（Zスコア正規化、カレンダー管理、統計関数等）

---

## 機能一覧

- 環境変数管理
  - .env / .env.local をプロジェクトルートから自動読み込み（必要に応じて無効化可能）
- データ取得／保存
  - J-Quants クライアント (jquants_client)
    - 株価日足、財務データ、マーケットカレンダーの取得（ページネーション対応）
    - レート制限・リトライ・自動トークンリフレッシュ対応
  - DuckDB への冪等保存ユーティリティ（raw_prices / raw_financials / market_calendar 等）
- ETL パイプライン
  - 差分取得（最終取得日からの再取得 + backfill）
  - 日次 ETL（run_daily_etl）でカレンダー→価格→財務→品質チェックを実行
- データ品質チェック（quality）
  - 欠損、スパイク、重複、日付不整合の検出
- ニュース収集（news_collector）
  - RSS 取得・XML 防御（defusedxml）・gzip 対応・SSRF/プライベートIP対策
  - 記事ID は正規化 URL の SHA-256 ハッシュ先頭を使用し冪等性を保証
  - raw_news / news_symbols に保存
- リサーチ（research）
  - ファクター計算（momentum, value, volatility）
  - 将来リターン計算、IC（Spearman ρ）計算、ファクター統計サマリー
  - zscore_normalize 再利用可能
- スキーマ管理（data.schema）
  - DuckDB のテーブル定義と初期化（Raw / Processed / Feature / Execution 層）
  - 監査ログ用スキーマの初期化（data.audit）
- カレンダー管理
  - 営業日判定 / next/prev_trading_day / get_trading_days / calendar_update_job

---

## セットアップ手順

前提
- Python 3.8+（typing の仕様に依存）
- DuckDB を利用（Python パッケージ duckdb）
- 必要なパッケージ（例）
  - duckdb
  - defusedxml

例: 仮想環境作成と依存インストール（pip）
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# 開発インストールがあれば:
# pip install -e .
```

環境変数
- プロジェクトルートに `.env` を作成してください（.env.example を参考に）。
- このプロジェクトで必須の環境変数:
  - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
  - KABU_API_PASSWORD     : kabuステーション API パスワード（必須）
  - SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン（必須）
  - SLACK_CHANNEL_ID      : 通知先 Slack チャンネル ID（必須）
- オプション:
  - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
  - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — デフォルト: INFO
  - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
  - SQLITE_PATH — デフォルト: data/monitoring.db

自動 .env ロードの制御
- デフォルトで .env/.env.local をプロジェクトルートから自動読み込みします。
- 自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

DuckDB スキーマ初期化
- スキーマを初期化するには Python から次を実行します:
```python
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")  # ファイルパスまたは ":memory:"
```

監査ログ専用 DB 初期化
```python
from kabusys.data import audit
conn_audit = audit.init_audit_db("data/kabusys_audit.duckdb")
```

---

## 使い方（主要な例）

1) 日次 ETL を実行して J-Quants から差分データを取得・保存・チェックする
```python
from datetime import date
import kabusys
from kabusys.data import schema, pipeline

# DB 初期化 / 接続
conn = schema.init_schema("data/kabusys.duckdb")

# ETL 実行（id_token は省略して内部キャッシュを使う）
result = pipeline.run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

2) ニュース収集ジョブの実行（既知銘柄セットを渡して銘柄紐付け）
```python
from kabusys.data import news_collector, schema

conn = schema.get_connection("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984"}  # 例: 有効銘柄コード
res = news_collector.run_news_collection(conn, known_codes=known_codes)
print(res)
```

3) ファクター計算・IC 計算（リサーチ用）
```python
from datetime import date
import duckdb
from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic

conn = duckdb.connect("data/kabusys.duckdb")
d = date(2024, 1, 31)

factors = calc_momentum(conn, d)
vols = calc_volatility(conn, d)
vals = calc_value(conn, d)

forw = calc_forward_returns(conn, d, horizons=[1,5,21])
# 例: mom_1m と fwd_1d の IC を計算
ic = calc_ic(factors, forw, factor_col="mom_1m", return_col="fwd_1d")
print("IC (mom_1m vs fwd_1d) =", ic)
```

4) J-Quants から個別データを取得して保存する
```python
from kabusys.data import jquants_client as jq
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
saved = jq.save_daily_quotes(conn, records)
print("saved:", saved)
```

5) カレンダー更新バッチ
```python
from kabusys.data import calendar_management, schema
conn = schema.get_connection("data/kabusys.duckdb")
saved = calendar_management.calendar_update_job(conn)
print("calendar saved:", saved)
```

---

## ディレクトリ構成（主なファイル）

リポジトリの主要な Python モジュールは `src/kabusys` 以下に配置されています。主要ファイルを抜粋します。

- src/kabusys/__init__.py                 — パッケージ定義（バージョン）
- src/kabusys/config.py                   — 環境変数・設定管理
- src/kabusys/data/
  - __init__.py
  - jquants_client.py                      — J-Quants API クライアント（取得・保存ユーティリティ）
  - news_collector.py                      — RSS ニュース収集・DB 保存
  - schema.py                              — DuckDB スキーマ定義・初期化
  - pipeline.py                            — ETL パイプライン（差分取得・日次 ETL）
  - quality.py                             — データ品質チェック
  - stats.py                               — 統計ユーティリティ（zscore_normalize）
  - features.py                            — features の公開インターフェース
  - calendar_management.py                 — 市場カレンダー管理
  - audit.py                               — 監査ログ（発注→約定トレース）用スキーマ
  - etl.py                                 — ETL 結果型の再エクスポート
- src/kabusys/research/
  - __init__.py
  - feature_exploration.py                 — 将来リターン / IC / summary 等
  - factor_research.py                     — momentum / value / volatility 計算
- src/kabusys/strategy/                     — 戦略関連 (空の __init__.py がある)
- src/kabusys/execution/                    — 発注関連 (空の __init__.py がある)
- src/kabusys/monitoring/                   — 監視関連 (空の __init__.py がある)

---

## 注意点 / 設計方針の要点

- DuckDB をデータレイクとして使用。DDL は冪等（CREATE TABLE IF NOT EXISTS）で定義。
- J-Quants API 呼び出しはレート制限 / リトライ / トークンリフレッシュを考慮。
- ETL は差分とバックフィルを行い、API の後出し修正に対応。
- ニュース収集は SSRF 対策・XML 安全パーサ（defusedxml）・受信サイズ制限を実装。
- リサーチ用モジュールは本番発注 API にアクセスしない（データベースの prices_daily, raw_financials のみ参照）。
- 環境変数の自動ロードは .git または pyproject.toml を基準にプロジェクトルートから探します。テスト時に無効にすることも可能。

---

## よくある操作例（まとめ）

- スキーマ初期化
  - schema.init_schema("data/kabusys.duckdb")
- 監査ログ DB 初期化
  - audit.init_audit_db("data/kabusys_audit.duckdb")
- 日次 ETL 実行
  - pipeline.run_daily_etl(conn)
- RSS ニュース収集
  - news_collector.run_news_collection(conn, known_codes=...)
- ファクター算出 / リサーチ
  - research.calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic

---

必要であれば、README に具体的な .env.example のテンプレートや、CI/運用向けの cron/airflow 連携例、ロギング／モニタリング設定のサンプルも追記できます。どの項目を詳細化したいか教えてください。