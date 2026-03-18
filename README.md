# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ（KabuSys）。  
DuckDB をデータストアとして用い、J-Quants API や RSS ニュースを取り込み、特徴量計算・品質チェック・ETL パイプライン・監査ログなどを提供します。

---

## プロジェクト概要

KabuSys は以下の目的を持つモジュール群を含むライブラリです。

- J-Quants API からの市場データ（株価日足、財務、カレンダー）の取得と DuckDB への冪等保存
- RSS を用いたニュース収集と記事 ⇄ 銘柄の紐付け
- データ品質チェック（欠損、重複、スパイク、日付不整合）
- 研究向けのファクター / 特徴量計算（momentum, volatility, value 等）および IC 計算
- ETL パイプライン（差分取得、バックフィル、品質チェック）
- 監査ログ（signal → order → execution までのトレーサビリティ）
- 簡易な設定管理（.env 自動読込）

設計方針として、DuckDB を中心に SQL と軽量な Python 実装で高速に処理を行い、本番の注文 API 等への直接アクセスは行わない（研究/データ基盤フェーズに注力）ことを想定しています。

---

## 主な機能一覧

- data/jquants_client
  - J-Quants API クライアント（ページネーション、リトライ、トークン自動リフレッシュ、レートリミット考慮）
  - raw_prices/raw_financials/market_calendar の保存ユーティリティ
- data/news_collector
  - RSS 取得、前処理、記事ID生成（URL 正規化 + SHA256）、DB 保存、銘柄抽出
  - SSRF 対策、受信サイズ制限、gzip 解凍対応
- data/schema, data/audit
  - DuckDB のスキーマ定義と初期化（Raw / Processed / Feature / Execution 層）
  - 監査ログテーブル（signal_events / order_requests / executions など）
- data/pipeline
  - 差分 ETL（prices / financials / market_calendar）
  - run_daily_etl：日次 ETL のエントリポイント（品質チェック付き）
- data/quality
  - 欠損、スパイク、重複、日付不整合のチェック（QualityIssue の集合を返す）
- research
  - calc_momentum, calc_volatility, calc_value（prices_daily / raw_financials に依存）
  - calc_forward_returns, calc_ic, factor_summary, rank（IC / 統計・評価用）
  - zscore_normalize（data.stats）
- config
  - .env / 環境変数読み込み、自動ロード（プロジェクトルート検出）と Settings API

---

## 前提条件

- Python 3.10+
- 必要なパッケージ（例）
  - duckdb
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS フィード）

（pip 用の依存はプロジェクトの pyproject.toml / requirements.txt を参照してください）

---

## セットアップ手順

1. リポジトリをクローン / ワークツリーに配置

2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install duckdb defusedxml
   - （ローカル開発用）pip install -e .

4. 環境変数設定
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` を置くと自動読み込みされます。
   - 自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須の環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabu ステーション API のパスワード（必須）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack チャネル ID（必須）

オプション
- KABUSYS_ENV: development | paper_trading | live（デフォルト development）
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト INFO）
- DUCKDB_PATH: デフォルト data/kabusys.duckdb
- SQLITE_PATH: デフォルト data/monitoring.db

例 (.env)
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb

---

## データベース初期化

DuckDB スキーマを作成するには data.schema.init_schema を使用します。

例（Python REPL / スクリプト）:
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")
# conn は duckdb.DuckDBPyConnection オブジェクト

監査ログ専用 DB を初期化する場合:
from kabusys.data import audit
audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")

注意: init_schema は必要なディレクトリが無ければ自動で作成します（db_path != ":memory:" の場合）。

---

## 使い方（主要ユースケース）

- 日次 ETL（市場カレンダー・株価・財務の差分取得 + 品質チェック）

例:
from datetime import date
import duckdb
from kabusys.data import schema, pipeline

conn = schema.init_schema("data/kabusys.duckdb")
result = pipeline.run_daily_etl(conn, target_date=date.today())
print(result.to_dict())

run_daily_etl は次を行います:
1. market_calendar の先読み取得
2. raw_prices の差分取得（backfill を含む）
3. raw_financials の差分取得
4. 品質チェック（run_quality_checks=True の場合）

- ニュース収集ジョブ（RSS 取得 → raw_news 保存 → news_symbols の紐付け）

例:
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
from kabusys.data import schema
conn = schema.get_connection("data/kabusys.duckdb")  # 既存 DB へ接続
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203","6758"})
print(results)

- 研究用ファクター計算（DuckDB 接続を渡して利用）

例:
from datetime import date
import duckdb
from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, zscore_normalize

conn = duckdb.connect("data/kabusys.duckdb")
d = date(2024, 1, 31)
momentum = calc_momentum(conn, d)
vol = calc_volatility(conn, d)
value = calc_value(conn, d)
forwards = calc_forward_returns(conn, d, horizons=[1,5,21])
# ファクターと将来リターンで IC を計算（例）
ic = calc_ic(momentum, forwards, factor_col="mom_1m", return_col="fwd_1d")

- Z スコア正規化
from kabusys.data.stats import zscore_normalize
normed = zscore_normalize(momentum, ["mom_1m","mom_3m","ma200_dev"])

---

## 設定管理の注意点

- config モジュールはプロジェクトルート（.git または pyproject.toml）を基点に `.env` / `.env.local` を自動で読み込みます（OS 環境変数が優先）。
- 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テストでの利用想定）。
- Settings API を使ってコード内から値を取得できます:
  from kabusys.config import settings
  token = settings.jquants_refresh_token

---

## 開発・テストのヒント

- J-Quants API の呼び出しはレート制限・リトライ・401 リフレッシュ等を備えています。テスト時は id_token を注入して外部依存を切り離すことを推奨します。
- news_collector._urlopen 等、内部のネットワーク呼び出しはモックしやすく設計されています。
- ETL は Fail-Fast ではなく、可能な限り各ステップを継続して実行し、問題を収集して返す設計です（ETLResult.errors / quality_issues を確認してください）。

---

## ディレクトリ構成

src/kabusys/
- __init__.py
- config.py                         - 環境変数・設定管理
- data/
  - __init__.py
  - jquants_client.py               - J-Quants API クライアント + 保存ユーティリティ
  - news_collector.py               - RSS ニュース収集、前処理、DB 保存
  - schema.py                       - DuckDB スキーマ定義・初期化
  - stats.py                        - 汎用統計ユーティリティ（zscore_normalize）
  - pipeline.py                     - ETL パイプライン（run_daily_etl 等）
  - features.py                     - 特徴量ユーティリティの公開
  - calendar_management.py          - 市場カレンダー管理ユーティリティ
  - audit.py                        - 監査ログ（signal/order/execution）テーブル初期化
  - etl.py                          - ETL 結果クラスの公開
  - quality.py                      - データ品質チェック
- research/
  - __init__.py
  - feature_exploration.py          - 将来リターン、IC、統計サマリー
  - factor_research.py              - momentum / value / volatility の計算
- strategy/                          - 戦略関連（拡張用 / 空のパッケージ）
- execution/                         - 発注/監視関連（拡張用 / 空のパッケージ）
- monitoring/                        - 監視関連（拡張用 / 空のパッケージ）

その他:
- .env, .env.local (プロジェクトルートで自動読み込み対象)
- data/ (デフォルトの DuckDB ファイル格納先)

---

## 注意事項 / ベストプラクティス

- J-Quants の API レート制限に従うこと（モジュールは 120 req/min を想定して制御します）。
- 本ライブラリはデータ収集・特徴量算出・監査ログに重点があり、証券会社への実際の発注を行う箇所は別途安全設計（冪等性、障害回復、認証、権限制御）を行ってください。
- DuckDB の ON CONFLICT / RETURNING を活用し冪等性を担保していますが、外部からの直接書き込みがある場合は品質チェックで不整合を検出してください。
- 全ての TIMESTAMP は UTC で扱うことが想定されています（監査 DB 初期化で SET TimeZone='UTC' を実行）。

---

必要に応じて README を拡張して、CI/CD、デプロイ手順、詳細な API 使用例、pyproject.toml によるパッケージ化手順などを追記できます。追加したいセクションがあれば教えてください。