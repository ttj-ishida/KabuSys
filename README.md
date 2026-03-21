# KabuSys

KabuSys は日本株のデータ収集・特徴量構築・シグナル生成・ETL を行う自動売買基盤ライブラリです。DuckDB をデータレイヤに用い、J-Quants API や RSS ニュースを取り込んで戦略用の特徴量（features）を作成し、最終スコアに基づく売買シグナルを生成します。

主な設計方針:
- ルックアヘッドバイアスの防止（target_date 時点のデータのみを利用）
- 冪等性（DB への保存は ON CONFLICT / トランザクションで安全）
- 本番環境と開発環境の分離（KABUSYS_ENV）
- 外部 API 呼び出しのレート制御・リトライ・トークン自動更新などを内包

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（クイックスタート）
- 環境変数
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は以下を実現するモジュール群を提供します。

- Data layer: J-Quants から株価・財務・市場カレンダーを取得して DuckDB に保存（差分取得 / バックフィル対応）
- Research layer: ファクター計算（Momentum / Volatility / Value など）、将来リターン・IC 計算、統計サマリ
- Feature engineering: 生ファクターの正規化・ユニバースフィルタ適用・features テーブルへの保存
- Strategy layer: features と AI スコアを統合して final_score を計算、BUY / SELL シグナルを生成して signals テーブルへ保存
- News collection: RSS フィードから記事収集、本文前処理、銘柄抽出および news テーブルへの保存（SSRF/サイズ制限/トラッキング除去対応）
- Calendar management: market_calendar の夜間更新、営業日/前後営業日の判定ユーティリティ
- ETL pipeline: 日次 ETL（calendar / prices / financials）と品質チェック
- Schema & audit: DuckDB のスキーマ初期化・監査ログテーブルの提供

---

## 機能一覧

主な機能（モジュールと代表的な関数）:

- kabusys.config
  - 自動 `.env` ロード（`.env` / `.env.local`、OS 環境変数優先）
  - settings: 環境変数アクセス・バリデーション

- kabusys.data.jquants_client
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes, save_financial_statements, save_market_calendar
  - レートリミット、リトライ、トークン自動更新

- kabusys.data.schema
  - init_schema(db_path) - DuckDB スキーマ作成（冪等）

- kabusys.data.pipeline
  - run_daily_etl(conn, target_date, ...) - 日次 ETL 実行
  - 個別: run_prices_etl, run_financials_etl, run_calendar_etl

- kabusys.research
  - calc_momentum, calc_volatility, calc_value
  - calc_forward_returns, calc_ic, factor_summary, rank

- kabusys.strategy
  - build_features(conn, target_date) - features テーブルにファクターを格納
  - generate_signals(conn, target_date, threshold, weights) - signals テーブルへ BUY/SELL を出力

- kabusys.data.news_collector
  - fetch_rss, save_raw_news, run_news_collection
  - URL 正規化、トラッキング除去、SSRF 対策、記事ID 冪等化

- kabusys.data.calendar_management
  - calendar_update_job(conn, lookahead_days)
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day

その他:
- 統計ユーティリティ（zscore_normalize）
- audit（signal_events / order_requests / executions 等）スキーマ

---

## セットアップ手順

前提:
- Python 3.10 以上（PEP 604 の型表記などを使用）
- pip / virtualenv を推奨

1. リポジトリをチェックアウト
   - git clone ...

2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install -U pip
   - 必須の主要ライブラリ:
     - duckdb
     - defusedxml
   - 例:
     - pip install duckdb defusedxml

   （プロジェクトに requirements.txt / pyproject.toml がある場合はそちらに従ってください）
   開発インストール（パッケージ化されていれば）:
   - pip install -e .

4. 環境変数の準備
   - プロジェクトルートに `.env` を作成（例は下記「環境変数」参照）
   - 自動ロードはデフォルトで有効（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）

5. データベース初期化
   - Python REPL / スクリプト で以下を実行して DuckDB スキーマを作成します（例: data/kabusys.duckdb）:
     - from kabusys.data.schema import init_schema
       conn = init_schema("data/kabusys.duckdb")

---

## 使い方（クイックスタート）

典型的なワークフロー例（日次バッチ）:

1) DB 初期化（1 回）
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

2) 日次 ETL を実行（J-Quants トークンを環境変数で設定済みであること）
```python
from kabusys.data.pipeline import run_daily_etl
res = run_daily_etl(conn)  # target_date を指定しなければ本日
print(res.to_dict())
```

3) 特徴量構築
```python
from kabusys.strategy import build_features
from datetime import date
count = build_features(conn, date.today())
print(f"features built: {count}")
```

4) シグナル生成
```python
from kabusys.strategy import generate_signals
from datetime import date
n = generate_signals(conn, date.today())
print(f"signals generated: {n}")
```

5) ニュース収集（既知の銘柄コード集合を渡して紐付け）
```python
from kabusys.data.news_collector import run_news_collection
known_codes = {"7203", "6758", "9984"}  # 例
result = run_news_collection(conn, known_codes=known_codes)
print(result)
```

6) カレンダー更新ジョブ（夜間バッチ）
```python
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn)
print(f"calendar saved: {saved}")
```

実運用では上記を cron / Airflow / Prefect 等のジョブスケジューラで順序（calendar -> prices -> financials -> quality -> features -> signals -> execution）に沿って実行します。

---

## 環境変数

このプロジェクトは .env（および .env.local）を自動で読み込みます。必須・推奨の環境変数は以下の通りです。

必須 (Settings._require によってチェックされる)
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- KABU_API_PASSWORD: kabuステーション API 用のパスワード（execution 層で使用）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID

オプション / デフォルトあり
- KABU_API_BASE_URL: kabu API のエンドポイント（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 環境 (development / paper_trading / live)（デフォルト: development）
- LOG_LEVEL: ログレベル (DEBUG/INFO/WARNING/ERROR/CRITICAL)（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: "1" にすると自動 .env 読み込みを無効化（テスト用）

.env の簡単な例:
JQUANTS_REFRESH_TOKEN=xxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

注意:
- .env.local が存在する場合は .env の設定を上書きします（OS 環境変数は常に優先されます）。
- 自動読み込みを無効にすることで、テスト時に環境を制御できます。

---

## ディレクトリ構成

主要ファイルとモジュール（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                      -- 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py             -- J-Quants API クライアント（取得 + 保存）
    - news_collector.py             -- RSS 収集・保存・銘柄抽出
    - schema.py                     -- DuckDB スキーマ定義・init_schema
    - stats.py                      -- 統計ユーティリティ（zscore_normalize）
    - pipeline.py                   -- ETL パイプライン（run_daily_etl 等）
    - calendar_management.py        -- 市場カレンダー管理ジョブ
    - audit.py                      -- 監査ログスキーマ（signal_events 等）
    - features.py                   -- features 公開インターフェース
    - execution/                     -- 発注・実行に関するモジュール群（空の __init__ あり）
  - research/
    - __init__.py
    - factor_research.py            -- ファクター計算（mom/vol/value）
    - feature_exploration.py        -- 将来リターン・IC・サマリ
  - strategy/
    - __init__.py
    - feature_engineering.py        -- features を構築して DB に保存
    - signal_generator.py           -- final_score 計算と signals 生成
  - monitoring/                      -- 監視関連（SQLite など） （ディレクトリ想定）
  - execution/                       -- 発注/ブローカー連携モジュール（実装の想定）

各モジュールはドキュメント文字列（docstring）で設計方針や処理フロー、戻り値の仕様を明記しています。DuckDB を中心に SQL と Python を組み合わせた実装になっており、外部依存は最小限に抑えられています。

---

## 注意事項 / 運用上のポイント

- Python バージョン: 3.10 以上を推奨（型表記に PEP 604 等を使用）
- DuckDB ファイルはバックアップ・スナップショット運用を検討してください（監査ログは削除しない前提）
- J-Quants API のレート制限・リトライ処理は実装済みですが、ID トークンや API 利用制限に注意してください
- 本リポジトリの機能は研究/ペーパー/ライブ環境で使えるよう env による切替が可能です。Live 環境では必ず十分なテストとリスク管理を行ってください
- 発注（execution）部分は外部ブローカー API と接続するための追加開発や安全弁（注文制限、リスクチェック）が必要です

---

もし README に追加したい具体的な使用例（Airflow DAG、systemd unit、cron のサンプル）、CI 設定やテストケース、あるいは environment のテンプレート（.env.example）等があれば教えてください。必要に応じて追記して整備します。