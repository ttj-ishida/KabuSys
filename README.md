# KabuSys

KabuSys は日本株向けの自動売買プラットフォームのライブラリ群です。  
データ取得（J-Quants）、ETL、データ品質チェック、特徴量生成、ファクター研究、ニュース収集、監査ログ（発注〜約定トレース）など、量的投資・自動売買に必要な基盤処理を提供します。

バージョン: 0.1.0

---

## 概要

主な設計方針・特徴:
- DuckDB をデータ層に用い、Raw → Processed → Feature → Execution の多層スキーマを提供
- J-Quants API からのデータ取得をサポート（レート制御、リトライ、トークン自動更新対応）
- ETL は差分取得・バックフィルを考慮し、品質チェックで欠損やスパイク等を検出
- ニュースは RSS から収集し、記事と銘柄コードの紐付けを実行
- 研究（research）モジュールは外部ライブラリに依存せず、ファクター計算・IC 等を実装
- 監査ログ（audit）でシグナル→発注→約定までトレース可能なテーブルを提供
- 環境変数／.env による設定管理、自動ロード機能あり（必要に応じて無効化）

---

## 機能一覧

- 設定管理
  - 環境変数読み込み（.env / .env.local、自動検索）
  - 必須環境変数チェック（例: JQUANTS_REFRESH_TOKEN）

- データ取得・保存 (kabusys.data)
  - J-Quants クライアント（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）
  - データ保存（save_daily_quotes / save_financial_statements / save_market_calendar）
  - ニュース収集（fetch_rss / save_raw_news / run_news_collection）
  - DuckDB スキーマ初期化（init_schema、init_audit_schema）
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - 品質チェック（欠損、重複、スパイク、日付不整合）
  - マーケットカレンダー管理（営業日判定、次/前営業日取得等）

- 研究・特徴量 (kabusys.research)
  - ファクター計算（calc_momentum, calc_volatility, calc_value）
  - 将来リターン計算（calc_forward_returns）
  - IC（Information Coefficient）計算（calc_ic）
  - 統計サマリー（factor_summary）
  - 正規化ユーティリティ（zscore_normalize）

- 統計ユーティリティ（kabusys.data.stats）
  - z-score 正規化（クロスセクション）

- 監査ログ（kabusys.data.audit）
  - signal_events, order_requests, executions 等のテーブルと初期化ロジック

- その他
  - SSRF 考慮・圧縮対応の RSS 取得（news_collector）
  - API レート制御・再試行・トークン管理（jquants_client）

※ strategy, execution, monitoring はパッケージのエントリはあるものの（プレースホルダ的に）実装は本リポジトリで展開される想定です。

---

## 動作環境 / 前提

- Python 3.10+
  - PEP 604 (X | Y) などの構文を使用しています。
- 必要パッケージ（例）
  - duckdb
  - defusedxml
  - （標準ライブラリだけで動く部分も多いですが、DuckDB と XML 防御ライブラリが必要です）

推奨インストール例:
pip install duckdb defusedxml

プロジェクトに requirements.txt があればそちらを使用してください。

---

## セットアップ手順

1. リポジトリをクローン / 展開

2. 仮想環境の作成（任意）
- python -m venv .venv
- source .venv/bin/activate  # Windows: .venv\Scripts\activate

3. 依存ライブラリのインストール
- pip install duckdb defusedxml
- （追加で logging/requests 等を使う場合は必要に応じて導入）

4. 環境変数を設定
- プロジェクトルート（.git または pyproject.toml が存在するディレクトリ）に .env と .env.local を置くと自動ロードされます。
- 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

必須の環境変数（例）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- KABU_API_PASSWORD: kabu ステーション API パスワード（発注モジュール使用時）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（通知機能を使う場合）
- SLACK_CHANNEL_ID: Slack 通知対象チャンネル ID

任意
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 sqlite パス（デフォルト: data/monitoring.db）

例 .env:
JQUANTS_REFRESH_TOKEN=xxxxx
KABU_API_PASSWORD=passwd
SLACK_BOT_TOKEN=xoxb-xxxx
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb

5. DuckDB スキーマ初期化
- Python REPL やスクリプトでスキーマを作成します。

例:
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
# 監査ログを追加で初期化する場合
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn, transactional=True)

---

## 使い方（サンプル）

- ETL（日次パイプライン）を実行する

from datetime import date
import duckdb
from kabusys.data.schema import init_schema, get_connection
from kabusys.data.pipeline import run_daily_etl

# DB 初期化（初回）
conn = init_schema("data/kabusys.duckdb")

# 日次 ETL 実行（今日分）
result = run_daily_etl(conn)
print(result.to_dict())

- 価格データの差分 ETL を個別に実行する

from kabusys.data.pipeline import run_prices_etl
fetched, saved = run_prices_etl(conn, target_date=date.today())

- ニュース収集ジョブを実行する

from kabusys.data.news_collector import run_news_collection
known_codes = {"7203", "6758"}  # 有効銘柄一覧
res = run_news_collection(conn, known_codes=known_codes)
print(res)

- ファクター計算 / 研究機能

from datetime import date
from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary
from kabusys.data.stats import zscore_normalize

records_mom = calc_momentum(conn, target_date=date.today())
records_vol = calc_volatility(conn, target_date=date.today())
records_val = calc_value(conn, target_date=date.today())

# 将来リターンと IC 計算
fwd = calc_forward_returns(conn, target_date=date.today(), horizons=[1,5,21])
ic = calc_ic(records_mom, fwd, factor_col="mom_1m", return_col="fwd_1d")

# Zスコア正規化
normed = zscore_normalize(records_mom, ["mom_1m", "ma200_dev"])

- J-Quants から直接データを取得する（テスト用に id_token を指定可能）

from kabusys.data.jquants_client import fetch_daily_quotes, fetch_financial_statements
quotes = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))

---

## .env の自動読み込みについて

- プロジェクトルートは __file__ の親ディレクトリから .git または pyproject.toml を探索して決定されます。CWD に依存しません。
- 自動ロードの優先順位:
  - OS 環境変数（最優先）
  - .env.local（override=True：既存の環境変数を上書き。ただし OS 環境変数は保護）
  - .env（override=False：未設定のキーのみセット）
- 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

.env パーサはシェルの export 形式やシングル/ダブルクォート、行コメントなどに対応しています。

---

## ディレクトリ構成

リポジトリ内の主要ファイル・モジュール（抜粋）:

src/kabusys/
- __init__.py
- config.py                      # 環境変数・設定管理
- data/
  - __init__.py
  - jquants_client.py            # J-Quants API クライアント + 保存ロジック
  - news_collector.py            # RSS ニュース収集・前処理・保存
  - schema.py                    # DuckDB スキーマ定義と初期化
  - pipeline.py                  # ETL パイプライン（差分取得 / run_daily_etl 等）
  - features.py                  # 特徴量ユーティリティ（エクスポート）
  - stats.py                     # 統計ユーティリティ（zscore_normalize）
  - calendar_management.py       # 市場カレンダー管理と更新ジョブ
  - audit.py                     # 監査ログ（信号→発注→約定）テーブル定義
  - etl.py                       # ETL インターフェース再エクスポート
  - quality.py                   # データ品質チェック
- research/
  - __init__.py                  # 主要研究関数のエクスポート
  - feature_exploration.py       # 将来リターン計算、IC、統計サマリー
  - factor_research.py           # モメンタム / ボラティリティ / バリュー計算
- strategy/
  - __init__.py                  # 戦略層（プレースホルダ）
- execution/
  - __init__.py                  # 発注層（プレースホルダ）
- monitoring/
  - __init__.py                  # 監視機能（プレースホルダ）

（README は実装済みモジュールの主要関数を中心に説明しています。strategy / execution / monitoring は必要に応じて実装を追加してください。）

---

## 注意事項 / 運用上のポイント

- J-Quants API のレート制限（120 req/min）に従う設計ですが、実運用ではさらに上位のスロットリングやバッチ設計、ログ監視を導入してください。
- ETL は品質チェックで問題をリストアップしますが、重大な品質問題があってもプロセスは継続する設計です。呼び出し側で result.has_quality_errors や result.has_errors を確認して運用判断を行ってください。
- ニュース収集では SSRF / XML Bomb / 過大レスポンス等に対する対策を実装していますが、外部フィードの扱いには十分注意してください。
- 本ライブラリは発注（実口座）機能を持つため、live 環境での使用時は十分なテスト・安全策（paper_trading フラグ、リスク管理）を設けてください。
- すべての TIMESTAMP は原則 UTC で扱うことを推奨しています（audit.init_audit_schema などで TimeZone を UTC に固定します）。

---

もし README に追加したい具体的な情報（インストール用 requirements.txt、CI 手順、サンプルデータ、実行スクリプトの例 など）があれば教えてください。README を拡張して必要なコマンド例や運用手順を追記します。