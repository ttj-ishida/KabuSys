# KabuSys

日本株向けの自動売買プラットフォーム向けライブラリです。  
データ取得（J-Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、マーケットカレンダー管理、実行/監査向けスキーマを含むモジュール群を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の階層構造に従う設計の日本株自動売買システム用ライブラリです。

- Data Layer: J-Quants からの株価・財務・カレンダー・ニュースの取得、DuckDB への保存（冪等）
- Processed Layer: prices_daily / fundamentals / market_calendar などの整形済みテーブル
- Feature Layer: 戦略用の正規化済み特徴量（features / ai_scores）
- Strategy Layer: 特徴量から戦略シグナル（BUY/SELL）を生成
- Execution / Audit Layer: 発注・約定・ポジション管理・監査ログ用スキーマ

設計思想のポイント:
- ルックアヘッドバイアス回避（target_date 時点のデータのみ使用）
- 冪等性（ON CONFLICT / トランザクション）を重視
- 外部依存を最小化（DuckDB + 標準ライブラリ中心）
- セキュリティ配慮（RSS の SSRF 対策、XML パースの安全化 等）

---

## 主な機能一覧

- J-Quants API クライアント（rate-limit / retry / token refresh 対応）
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_* 系で DuckDB に冪等保存
- ETL パイプライン（差分更新・バックフィル・品質チェック付き）
  - run_daily_etl（カレンダー → 株価 → 財務 → 品質チェック）
- DuckDB スキーマの初期化
  - init_schema / get_connection
- 特徴量計算（research/factor_research）
  - calc_momentum, calc_volatility, calc_value
  - zscore_normalize（クロスセクション Z スコア正規化）
- 特徴量生成 / シグナル生成（strategy）
  - build_features: features テーブルの構築（ユニバースフィルタ・正規化・UPSERT）
  - generate_signals: features + ai_scores を統合して BUY/SELL を判定して signals テーブルに書き込む
- ニュース収集（RSS）
  - fetch_rss, save_raw_news, run_news_collection（SSRF対策・gzip / サイズ制限・トラッキング除去）
  - 銘柄コード抽出と news_symbols への紐付け
- マーケットカレンダー管理（is_trading_day / next_trading_day / calendar_update_job）
- 監査ログスキーマ（signal_events / order_requests / executions など）

---

## セットアップ手順

最小限の依存：
- Python 3.9+（typing の表記や型ヒントを利用）
- duckdb
- defusedxml

例（仮想環境を使用）:

1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージのインストール
   - pip install duckdb defusedxml

   ※プロジェクト配布が PyPI 等にある場合は pip install kabusys または開発時は pip install -e . を想定します。

3. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml のある場所）に `.env` と `.env.local` を置くと自動的に読み込まれます（優先度: OS 環境 > .env.local > .env）。
   - 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須環境変数（config.Settings で参照）:
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
- KABU_API_PASSWORD     : kabuステーション API のパスワード（使用する場合）
- SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン（使用する場合）
- SLACK_CHANNEL_ID      : Slack 通知先チャンネル ID

任意（デフォルトあり）:
- KABUSYS_ENV (development | paper_trading | live) — デフォルト development
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — デフォルト INFO
- DUCKDB_PATH — デフォルト data/kabusys.duckdb
- SQLITE_PATH — デフォルト data/monitoring.db

---

## 使い方（基本例）

以下は最小限のワークフロー例です。DuckDB を初期化して日次 ETL → 特徴量構築 → シグナル生成まで行う例です。

Python スクリプト例:

```python
from datetime import date
import duckdb

from kabusys.data.schema import init_schema, get_connection
from kabusys.data.pipeline import run_daily_etl
from kabusys.strategy import build_features, generate_signals
from kabusys.config import settings

# DB の初期化（デフォルトパス: settings.duckdb_path）
conn = init_schema(settings.duckdb_path)

# 日次 ETL を実行（J-Quants トークンは settings から自動取得）
etl_result = run_daily_etl(conn, target_date=date.today())

# 特徴量を作る（features テーブルを更新）
n_feats = build_features(conn, target_date=date.today())

# シグナルを生成（signals テーブルへ書き込む）
n_signals = generate_signals(conn, target_date=date.today())

print("ETL:", etl_result.to_dict())
print("features:", n_feats)
print("signals:", n_signals)
```

ニュース収集（RSS）を実行する例:

```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
# known_codes は銘柄抽出に使う有効なコード集合。None にすると紐付けをスキップ。
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=None)
print(results)
```

マーケットカレンダー更新ジョブ:

```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
saved = calendar_update_job(conn)
print("calendar saved:", saved)
```

注意点:
- 各処理はトランザクションや冪等性を考慮しているため、何度実行しても整合性を保つようになっています。
- 実環境（ライブ口座）で実行する前に KABUSYS_ENV を `paper_trading` で十分に検証してください。
- ログレベルや Slack 通知等は設定により変更可能です。

---

## ディレクトリ構成（主要ファイル・モジュール）

（リポジトリのルートが `src/kabusys` 配下にある想定）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み・設定（Settings）
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（取得・保存ユーティリティ）
    - schema.py
      - DuckDB スキーマ定義・init_schema / get_connection
    - stats.py
      - zscore_normalize 等の統計ユーティリティ
    - pipeline.py
      - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
    - news_collector.py
      - RSS 取得・前処理・DB 保存、銘柄抽出、run_news_collection
    - calendar_management.py
      - is_trading_day / next_trading_day / calendar_update_job
    - audit.py
      - 監査ログスキーマ定義（signal_events / order_requests / executions）
    - features.py
      - zscore_normalize の再エクスポート
    - execution/
      - (実行関連パッケージ用ディレクトリ)
  - research/
    - __init__.py
    - factor_research.py
      - calc_momentum / calc_volatility / calc_value
    - feature_exploration.py
      - calc_forward_returns / calc_ic / factor_summary / rank
  - strategy/
    - __init__.py
    - feature_engineering.py
      - build_features（ユニバースフィルタ・Zスコア正規化・UPSERT）
    - signal_generator.py
      - generate_signals（重み付け・Bear レジーム判定・BUY/SELL 生成）
  - execution/
    - __init__.py
    - (発注・ブローカー連携等の実装領域)

---

## 実運用・開発上の注意

- 環境変数と .env の取り扱い:
  - プロジェクトルートにある `.env` / `.env.local` を自動で読み込みます（CWD 依存しない）。
  - テスト時は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動読み込みをオフにできます。
- DuckDB:
  - デフォルトの DB パスは `data/kabusys.duckdb`。`init_schema` は親ディレクトリを自動作成します。
  - 初回は `init_schema` を呼び出してスキーマを作成してください。
- J-Quants API:
  - レート制限（120 req/min）をモジュール側で制御しますが、並列リクエストや複数インスタンスでの実行時は注意が必要です。
- セキュリティ:
  - RSS 取得は SSRF/ZIP/XML 攻撃対策が組み込まれていますが、プロダクション環境ではソース URL の管理を厳格にしてください。
- テスト:
  - モジュール内で外部呼び出しをモックできる設計（例: _urlopen の差し替え、id_token 注入）になっています。

---

## 参考（主な公開 API）

- 設定:
  - from kabusys.config import settings
- DB スキーマ:
  - from kabusys.data.schema import init_schema, get_connection
- ETL:
  - from kabusys.data.pipeline import run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl
- 特徴量 / 戦略:
  - from kabusys.strategy import build_features, generate_signals
- ニュース:
  - from kabusys.data.news_collector import run_news_collection, fetch_rss
- カレンダー:
  - from kabusys.data.calendar_management import is_trading_day, next_trading_day, calendar_update_job

---

必要に応じて README に追加する内容（例）
- CI / テストの実行方法（pytest 等）
- デプロイ手順（cron / Airflow / CI）
- API キーの取得方法や具体的な .env.example

ご希望があれば、README にサンプル .env.example、さらに詳しい API 使用例（各関数の引数説明付きスニペット）、運用手順（Cron ジョブ例、Slack 通知設定）などを追加します。