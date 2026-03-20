# KabuSys

日本株向け自動売買プラットフォーム用ライブラリ群（KabuSys）。  
データ取り込み（J-Quants）、DuckDB スキーマ、ETL パイプライン、特徴量生成、シグナル生成、ニュース収集、マーケットカレンダー管理などを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株のアルゴリズム取引システム向けに設計された Python モジュール群です。主な役割は次の通りです。

- J-Quants API からの株価・財務・カレンダー取得（レート制御、リトライ、トークン自動リフレッシュ）
- DuckDB を用いたデータスキーマ定義と永続化（Raw / Processed / Feature / Execution 層）
- ETL パイプライン（差分取得、バックフィル、品質チェック）
- 研究用ファクター計算と特徴量作成（ルックアヘッド回避に配慮）
- シグナル生成ロジック（複数コンポーネントの重み付け、Bear 判定、EXIT 条件）
- RSS ベースのニュース収集と銘柄抽出（SSRF 対策、gzip 制限、記事IDの冪等性）
- マーケットカレンダー管理（営業日判定 / next/prev / 範囲取得）
- 環境変数による設定管理（.env, .env.local 自動読込）

設計方針として「ルックアヘッドバイアス回避」「冪等性」「ネットワーク・セキュリティ対策」「最小限の外部依存」を重視しています。

---

## 主な機能一覧

- data/jquants_client.py
  - J-Quants API クライアント（レートリミット、再試行、トークン自動更新）
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - 保存関数：save_daily_quotes / save_financial_statements / save_market_calendar

- data/schema.py
  - DuckDB スキーマ定義（raw_prices / prices_daily / features / signals / orders など）
  - init_schema(db_path) による初期化

- data/pipeline.py
  - run_daily_etl: カレンダー取得 → 株価 ETL → 財務 ETL → 品質チェック（日次 ETL の統合）
  - run_prices_etl / run_financials_etl / run_calendar_etl（個別 ETL ジョブ）

- data/news_collector.py
  - RSS フィードの取得、テキスト前処理、raw_news 保存、銘柄抽出、news_symbols 保存
  - SSRF 対策、gzip / サイズ上限、XML セキュリティ対応

- data/calendar_management.py
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job

- data/audit.py
  - 監査ログ（signal_events / order_requests / executions）の DDL と初期化方針

- data/stats.py
  - zscore_normalize（クロスセクション Z スコア正規化）

- research/
  - factor_research.py: calc_momentum / calc_volatility / calc_value
  - feature_exploration.py: calc_forward_returns / calc_ic / factor_summary / rank

- strategy/
  - feature_engineering.py: build_features（research の生ファクターを正規化して features テーブルへ保存）
  - signal_generator.py: generate_signals（features + ai_scores を用いて BUY/SELL を生成）

その他：config.py（環境変数 / .env ロード / Settings クラス）

---

## セットアップ手順

前提
- Python 3.9+（typing | None 型注釈を使用）
- DuckDB ライブラリが必要
- defusedxml（ニュース収集で使用）
- ネットワークアクセスが必要（J-Quants / RSS）

例: pip で最低限の依存を入れる
```bash
python -m pip install duckdb defusedxml
```

パッケージを開発モードでインストールする場合:
```bash
git clone <リポジトリ>
cd <リポジトリ>
python -m pip install -e .
```

環境変数（必須）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- KABU_API_PASSWORD: kabuステーション API パスワード（実行層で必要）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（通知機能を使う場合）
- SLACK_CHANNEL_ID: Slack チャネル ID

設定可能な他の環境変数（デフォルト値あり）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: monitoring 用 SQLite（デフォルト: data/monitoring.db）

.env 自動読み込み
- パッケージはプロジェクトルート（.git または pyproject.toml があるディレクトリ）を探索し、.env を自動で読み込みます。
- 読み込み順序: OS 環境変数 > .env.local > .env
- 自動読み込みを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

例: .env の最小サンプル
```
JQUANTS_REFRESH_TOKEN=xxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C1234567890
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

DB 初期化
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

conn = init_schema(settings.duckdb_path)  # ファイルがなければ親ディレクトリを作成して初期化
```

---

## 使い方（主な API・実行例）

以下は代表的な利用フローの例です。

1) DuckDB スキーマ初期化
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

conn = init_schema(settings.duckdb_path)
```

2) 日次 ETL 実行
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)  # 今日をターゲットに ETL を実行
print(result.to_dict())
```

3) 特徴量の構築（ある基準日で）
```python
from datetime import date
from kabusys.strategy import build_features

cnt = build_features(conn, date(2024, 1, 4))
print(f"features upserted: {cnt}")
```

4) シグナル生成
```python
from datetime import date
from kabusys.strategy import generate_signals

n = generate_signals(conn, date(2024, 1, 4), threshold=0.6)
print(f"signals generated: {n}")
```

5) ニュース収集（RSS）
```python
from kabusys.data.news_collector import run_news_collection

# known_codes は銘柄コードの集合 (例: {'7203', '6758', ...})
res = run_news_collection(conn, sources=None, known_codes=known_codes)
print(res)  # {source_name: inserted_count, ...}
```

6) カレンダー更新バッチ
```python
from kabusys.data.calendar_management import calendar_update_job

saved = calendar_update_job(conn)
print("saved calendar rows:", saved)
```

7) 研究用ユーティリティ
```python
from kabusys.research import calc_momentum, calc_forward_returns, calc_ic
# DuckDB 接続 conn, target_date を指定して呼ぶ
```

注意点
- ほとんどの関数は DuckDB 接続を受け取ります（テスト容易性のため）。
- ルックアヘッドバイアス回避のため、feature/signal の計算は target_date 時点のデータのみを使う設計です。
- generate_signals は ai_scores テーブルを参照し、空の場合は中立扱い（AI スコア補完）します。
- save_* 関数や ETL は基本的に冪等化（ON CONFLICT / UPSERT）されています。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数読み込みと Settings
  - data/
    - __init__.py
    - jquants_client.py          — J-Quants API クライアント（取得＋保存）
    - schema.py                  — DuckDB スキーマ定義と init_schema
    - pipeline.py                — ETL パイプライン（run_daily_etl 等）
    - news_collector.py          — RSS 収集と保存、銘柄抽出
    - calendar_management.py     — 市場カレンダー関連ユーティリティ
    - audit.py                   — 監査ログ DDL / 設計
    - stats.py                   — 統計ユーティリティ（zscore_normalize）
    - features.py                — データ機能の公開インターフェース
    - execution/                 — 実行層（発注など：現状空のパッケージ）
  - research/
    - __init__.py
    - factor_research.py         — ファクター計算（momentum/value/volatility）
    - feature_exploration.py     — 将来リターン / IC / 統計サマリ等
  - strategy/
    - __init__.py
    - feature_engineering.py     — build_features
    - signal_generator.py        — generate_signals
  - execution/                   — 発注実装（将来拡張）
  - monitoring/                  — 監視・メトリクス（未提供ファイルもあり）

---

## 開発・運用上の注意

- 環境切替:
  - KABUSYS_ENV で環境を切替（development / paper_trading / live）。is_live/properties で判定可能。
- ログ:
  - LOG_LEVEL でログレベルを制御。各モジュールは logging を利用しています。
- セキュリティ:
  - news_collector は SSRF、XML Bomb、gzip Bomb に対する対策を実装しています。
  - jquants_client はトークンの自動更新、レート制御、リトライ（バックオフ）を実装しています。
- DB スキーマ:
  - init_schema() は冪等。運用初回に必ず呼ぶこと。
- テスト:
  - 設定自動ロードを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください（テストで .env を無効化して明示的に注入する等）。

---

## 参考: よく使う関数一覧（抜粋）

- init_schema(db_path)
- get_connection(db_path)
- run_daily_etl(conn, target_date=None, ...)
- run_prices_etl(conn, target_date, ...)
- fetch_daily_quotes / save_daily_quotes
- fetch_financial_statements / save_financial_statements
- fetch_market_calendar / save_market_calendar
- build_features(conn, target_date)
- generate_signals(conn, target_date, threshold=0.6, weights=None)
- fetch_rss(url, source) / save_raw_news(conn, articles)
- calendar_update_job(conn)

---

必要であれば README にサンプル .env.example を追加したり、実行スクリプト (cron / systemd timer / Airflow DAG) の例、CI 用のテスト手順、より詳細なモジュール API ドキュメントを追記できます。どの情報を優先して追記しますか？