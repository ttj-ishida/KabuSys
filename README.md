# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
データ収集（J-Quants、RSS）、DuckDB スキーマ定義、ETL パイプライン、特徴量計算、研究用ユーティリティ、監査ログなどを含みます。  
（本リポジトリは発注エンジン・戦略モジュールと連携することを想定しています。）

バージョン: 0.1.0

---

## 目次
- プロジェクト概要
- 主な機能
- 前提条件 / 依存ライブラリ
- セットアップ手順
- 環境変数（.env）例
- 使い方（簡易コード例）
  - DuckDB スキーマ初期化
  - 日次 ETL 実行
  - RSS ニュース収集
  - 研究用ファクター計算
- ディレクトリ構成
- 補足

---

## プロジェクト概要

KabuSys は以下の責務を持つモジュール群をまとめたパッケージです。

- J-Quants API からの株価・財務・カレンダー取得（レート制御・リトライ・トークン更新対応）
- RSS フィードからのニュース収集と銘柄紐付け（SSRF / XML 攻撃対策、受信サイズ制限）
- DuckDB ベースのデータスキーマ定義および監査テーブルの初期化
- ETL パイプライン（差分取得、バックフィル、品質チェック）
- 研究用ファクター計算（モメンタム、バリュー、ボラティリティ等）と特徴量探索（forward returns / IC 等）
- 汎用統計ユーティリティ（Z-score 正規化など）

設計方針として、本番資金口座や発注 API への直接アクセスを行わない箇所（data / research）は安全性や冪等性を重視しています。

---

## 主な機能

- data/
  - jquants_client: J-Quants API クライアント（ページネーション・レート制御・自動トークン更新・冪等保存）
  - news_collector: RSS 収集、前処理、DuckDB への保存（raw_news / news_symbols）
  - schema: DuckDB の DDL をまとめた初期化ユーティリティ（init_schema, get_connection）
  - pipeline: 日次 ETL（run_daily_etl、差分更新ルール、品質チェック統合）
  - quality: データ品質チェック（欠損、スパイク、重複、日付不整合）
  - calendar_management: JPX カレンダー管理（営業日判定、更新ジョブ）
  - audit: 監査ログ（signal/events/order_requests/executions テーブル群）初期化ユーティリティ
  - stats / features: 汎用統計・正規化ユーティリティ
- research/
  - factor_research: モメンタム・バリュー・ボラティリティ等のファクター計算（DuckDB を直接参照）
  - feature_exploration: 将来リターン計算、IC（Spearman）計算、ファクターサマリー等
- config:
  - 環境変数管理（.env 自動読み込み、必須チェック、環境モード判定）
- strategy/, execution/, monitoring/:
  - パッケージ用の名前空間（将来の戦略・発注・監視ロジックを配置する想定）

---

## 前提条件 / 依存ライブラリ

最低限必要な外部ライブラリ（例）:
- Python 3.10+（型アノテーションに Optional of union 型等を使用）
- duckdb
- defusedxml

実際のプロジェクト環境では logging・urllib 等の標準ライブラリに加え、DuckDB や defusedxml をインストールしてください。

例:
pip install duckdb defusedxml

（パッケージ配布・ビルド用の pyproject.toml / requirements.txt は本スニペットに含まれていません。実プロジェクトではそれらを用意してください。）

---

## セットアップ手順

1. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb defusedxml
   - その他必要なパッケージがあれば requirements.txt からインストール

3. DuckDB データベースの初期化（下段「使い方」参照）

4. 環境変数を設定（.env ファイルをプロジェクトルートに配置。自動読み込みあり）
   - 自動読み込みは config モジュールがプロジェクトルート（.git または pyproject.toml がある場所）を探索して行います
   - 自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

---

## 環境変数（.env）例

config.Settings が参照する主な環境変数:

必須:
- JQUANTS_REFRESH_TOKEN=あなたの_jquants_リフレッシュトークン
- KABU_API_PASSWORD=kabuステーション API のパスワード
- SLACK_BOT_TOKEN=Slack ボットトークン
- SLACK_CHANNEL_ID=通知先の Slack チャンネル ID

任意 / デフォルトあり:
- KABU_API_BASE_URL=http://localhost:18080/kabusapi
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- KABUSYS_ENV=development|paper_trading|live  （デフォルト: development）
- LOG_LEVEL=INFO|DEBUG|... （デフォルト: INFO）

例 (.env):
JQUANTS_REFRESH_TOKEN=xxxxxx
KABU_API_PASSWORD=secret
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG

注意: config.py の自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行われます。

---

## 使い方（簡易例）

以下は主要ユースケースの最小サンプルコードです。適切なエラーハンドリングやログ設定を行ってください。

1) DuckDB スキーマ初期化

from kabusys.data import schema
from kabusys.config import settings

# settings.duckdb_path は Path を返します
conn = schema.init_schema(settings.duckdb_path)
# 以降、conn を使って ETL / 保存 / 参照が可能

2) 日次 ETL 実行（J-Quants から差分取得・品質チェック）

from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn)
print(result.to_dict())

3) RSS ニュース収集ジョブ実行

from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
# known_codes に有効な銘柄コード集合を渡すと記事→銘柄紐付けが行われる
res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203","6758"})
print(res)  # ソースごとの新規保存件数

4) 研究用ファクター計算（DuckDB 接続を与えて呼ぶ）

from datetime import date
from kabusys.research import calc_momentum, calc_volatility, calc_value
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
target = date(2024, 1, 31)
mom = calc_momentum(conn, target)
vol = calc_volatility(conn, target)
val = calc_value(conn, target)

研究用ユーティリティ:
- calc_forward_returns(conn, target_date)
- calc_ic(factor_records, forward_records, factor_col, return_col)
- factor_summary(records, columns)
- zscore_normalize(records, columns)

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py                         -- 環境変数 / 設定管理
- data/
  - __init__.py
  - jquants_client.py               -- J-Quants API クライアント / 保存ユーティリティ
  - news_collector.py               -- RSS 収集 / 前処理 / DB 保存
  - schema.py                       -- DuckDB の DDL 定義と init_schema
  - pipeline.py                     -- ETL パイプライン（run_daily_etl 等）
  - quality.py                      -- データ品質チェック
  - features.py                      -- features API（zscore エクスポート）
  - stats.py                        -- 統計ユーティリティ（zscore_normalize）
  - calendar_management.py          -- market_calendar 管理、営業日判定
  - audit.py                        -- 監査ログテーブルの定義と初期化
  - etl.py                          -- ETL 型定義の公開（ETLResult）
- research/
  - __init__.py
  - feature_exploration.py          -- 将来リターン、IC、サマリ等
  - factor_research.py              -- momentum/value/volatility の計算
- strategy/
  - __init__.py
- execution/
  - __init__.py
- monitoring/
  - __init__.py

（上記以外に補助ファイルやドキュメントがある想定です。）

---

## 補足 / 注意点

- DuckDB の SQL 実行ではパラメータバインディング（?）を多用し、SQL インジェクションリスクを減らす設計です。
- jquants_client は API レート制御（120 req/min）と自動リトライ、401 発生時のトークン再取得ロジックを備えています。
- news_collector は SSRF 対策・XML 攻撃対策（defusedxml）・受信サイズ制限を行っています。
- config モジュールはプロジェクトルートの .env/.env.local を自動で読み込みます。OS 環境変数は上書きされません（.env.local は上書き可能）。自動読み込みを抑止するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- research モジュールの関数は DuckDB 接続を直接受け取り、prices_daily/raw_financials 等のテーブルのみを参照します。発注・ブローカー API を呼ぶことはありません。

---

この README はコードベースから抽出した情報を元に作成しています。運用環境で利用する前に、依存ライブラリや環境変数、DB パスや権限、ログ設定などを適切に構成してください。必要であれば、具体的な実行スクリプトや systemd / cron のサンプルも作成できます。