# KabuSys

日本株向け自動売買プラットフォームのライブラリ群です。データ取得（J-Quants）、DuckDB ベースのデータ基盤、特徴量計算・リサーチユーティリティ、ETL パイプライン、ニュース収集、監査ログスキーマなどを提供します。

---

## 概要

KabuSys は研究（Research）〜 データ基盤（Data）〜 実運用（Execution）をカバーする Python パッケージです。設計方針としては：

- DuckDB を中心としたローカルデータベース（冪等性を重視）
- J-Quants API からの差分取得（レート制御・リトライ・トークン自動更新）
- RSS ニュース収集（SSRF 対策、トラッキング除去、冪等保存）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- ファクター計算（Momentum / Volatility / Value 等）と評価ユーティリティ（IC, z-score）
- 監査ログ（signal → order → execution のトレース性を保証）

本 README はセットアップ方法・基本的な使い方・ディレクトリ構成の概要を示します。

---

## 主な機能（抜粋）

- 環境設定管理
  - .env / .env.local を自動読み込み（必要に応じて無効化可）
  - 必須項目は Settings で取得（JQUANTS_REFRESH_TOKEN 等）
- Data（データ取得・保存）
  - J-Quants クライアント（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）
  - DuckDB スキーマ定義と初期化（init_schema）
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - ニュース収集（RSS フェッチ・正規化・raw_news 保存・銘柄紐付け）
  - データ品質チェック（欠損・重複・スパイク・日付整合性）
  - カレンダー管理（営業日判定、next/prev_trading_day）
  - 監査ログ（signal_events, order_requests, executions）初期化ユーティリティ
- Research（リサーチ）
  - ファクター計算（calc_momentum / calc_volatility / calc_value）
  - 将来リターン計算（calc_forward_returns）
  - IC（スピアマンランク相関）計算（calc_ic）
  - ファクター統計サマリ（factor_summary）
  - z-score 正規化ユーティリティ（zscore_normalize）
- 実運用（Execution）
  - 発注・約定管理用のテーブル群（signal_queue / orders / trades / positions 等）
  - 監査・トレーサビリティ設計（UUID 連鎖）

---

## 前提条件

- Python 3.10+（typing の Union/Annotated 記法等を使用）
- 必須ライブラリ（例）
  - duckdb
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS フィード）

依存はプロジェクトの pyproject.toml / requirements.txt に合わせてインストールしてください。最低限のインストール例は以下です。

例：
pip install duckdb defusedxml

---

## セットアップ手順

1. リポジトリをクローン / パッケージを展開

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install -r requirements.txt
   - または必要パッケージを個別に: pip install duckdb defusedxml

4. 環境変数（.env）を準備
   - プロジェクトルートに .env / .env.local を配置すると、自動で読み込まれます（自動ロードはデフォルトで有効）。
   - 自動ロードを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

必須環境変数（例）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- KABU_API_PASSWORD: kabu ステーション API パスワード（発注を行う場合）
- SLACK_BOT_TOKEN: Slack 通知を行う場合の Bot トークン
- SLACK_CHANNEL_ID: Slack チャンネル ID

任意 / デフォルト
- KABUSYS_ENV: development / paper_trading / live（デフォルト development）
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）

例 .env（参考）
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb

---

## データベース初期化

DuckDB スキーマを初期化する例（Python スクリプト／REPL）:

from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)

監査ログ用スキーマを追加する場合:

from kabusys.data.audit import init_audit_schema
init_audit_schema(conn)

注意: init_schema は冪等（既に存在するテーブルはスキップ）です。ファイルパスの親ディレクトリが存在しない場合、自動作成されます。":memory:" を指定するとメモリ DB になります。

---

## 使い方（主要ユースケース）

以下はよく使う操作の一例です。詳細は各モジュールのドキュメント参照。

- 日次 ETL（株価 / 財務 / カレンダーの差分取得・保存・品質チェック）

from kabusys.data.schema import init_schema, get_connection
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings
from datetime import date

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn, target_date=date.today())

- 価格差分 ETL の個別実行

from kabusys.data.pipeline import run_prices_etl
fetched, saved = run_prices_etl(conn, target_date=date.today())

- 市場カレンダー更新ジョブ（夜間バッチ）

from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn, lookahead_days=90)

- ニュース収集（RSS 取得 → raw_news 保存 → 銘柄紐付け）

from kabusys.data.news_collector import run_news_collection
# known_codes は有効銘柄コードセット（例: {'7203','6758', ...}）
res = run_news_collection(conn, sources=None, known_codes=known_codes)

- ファクター計算（Research）

from kabusys.research import calc_momentum, calc_volatility, calc_value, zscore_normalize
from datetime import date

momentum = calc_momentum(conn, target_date=date(2024, 1, 31))
vol = calc_volatility(conn, target_date=date(2024, 1, 31))
value = calc_value(conn, target_date=date(2024, 1, 31))

# z-score 正規化の例
normed = zscore_normalize(momentum, ['mom_1m', 'mom_3m', 'mom_6m'])

- 将来リターン / IC（ファクター評価）

from kabusys.research import calc_forward_returns, calc_ic
fwd = calc_forward_returns(conn, target_date=date(2024,1,31), horizons=[1,5,21])
ic = calc_ic(factor_records=momentum, forward_records=fwd, factor_col='mom_1m', return_col='fwd_1d')

- データ品質チェック（ETL 後に自動で実行可能）

from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=date.today())
for i in issues:
    print(i.check_name, i.severity, i.detail)

---

## 環境変数一覧（主要）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD (必須 for execution) — kabu API 用パスワード
- KABUSYS_ENV — environment: development / paper_trading / live（デフォルト development）
- LOG_LEVEL — ログレベル（デフォルト INFO）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID — Slack 通知
- DUCKDB_PATH — DuckDB のファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — "1" をセットすると .env の自動ロードを無効化

設定は settings = kabusys.config.settings から取得できます。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py                — 環境変数/設定管理（.env 自動ローディング含む）
- data/
  - __init__.py
  - jquants_client.py      — J-Quants API クライアント（レート制御・リトライ・保存ユーティリティ）
  - news_collector.py      — RSS ニュース収集・保存・銘柄抽出
  - schema.py              — DuckDB スキーマ定義・初期化
  - stats.py               — z-score 正規化等の統計ユーティリティ
  - pipeline.py            — ETL パイプライン（run_daily_etl 等）
  - features.py            — 特徴量ユーティリティの公開インターフェース
  - calendar_management.py — 市場カレンダー管理（営業日判定・更新ジョブ）
  - audit.py               — 監査ログスキーマ初期化
  - etl.py                 — ETLResult の公開インターフェース
  - quality.py             — データ品質チェック
- research/
  - __init__.py
  - feature_exploration.py — 将来リターン計算 / IC / summary
  - factor_research.py     — Momentum / Volatility / Value の計算
- strategy/
  - __init__.py            — 戦略層用モジュール（実装は拡張想定）
- execution/
  - __init__.py            — 発注・実行層（実装は拡張想定）
- monitoring/
  - __init__.py            — 監視関連（未完）

---

## 設計上の注意点 / トラブルシューティング

- .env の自動ロードはプロジェクトルート（.git または pyproject.toml）を起点に行われます。テストなどで無効にする際は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- J-Quants API のレート制限（120 req/min）や 401 リフレッシュ、リトライロジックは jquants_client.py 内に組み込まれています。API 利用時はトークンやアクセス制限を確認してください。
- ニュース収集は RSS の内容に依存します。SSRF や XML Bomb 対策は実装されていますが、外部 URL へのアクセスは環境のネットワーク制限に注意してください。
- DuckDB のバージョン差異により一部制約（ON DELETE CASCADE 等）がサポートされないため、ドキュメント内にその旨の注記があります。削除時や外部キーに関する運用はアプリ側で制御してください。

---

## 参考（開発者向け）

- 各モジュール内に詳細な docstring（日本語コメント）があります。実装の意図や設計上の考慮事項はソース内コメントを参照してください。
- tests は同梱されていません。ユニットテスト / 統合テストはプロジェクトに合わせて追加してください。

---

もし README に追加したい具体的なサンプルスクリプト（例: cron 用 ETL ラッパー、ニュース収集ジョブ、研究用 Notebook のテンプレート）や、pyproject.toml / requirements の内容があれば、それに合わせて README を拡張します。