# KabuSys

日本株向けの自動売買システム用ライブラリ集（KabuSys）。  
データ収集・ETL、特徴量計算、シグナル生成、発注・監視レイヤーの基盤的モジュールを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の主要機能を持つモジュール群から構成されるライブラリです。

- J-Quants API からの市場データ・財務データ・マーケットカレンダー取得と DuckDB への保存
- RSS からのニュース収集と銘柄抽出（SSRF対策・トラッキングパラメータ除去付き）
- DuckDB スキーマ定義と初期化（Raw / Processed / Feature / Execution 層）
- ETL パイプライン（差分取得・バックフィル・品質チェック統合）
- 研究用ファクター計算（モメンタム・バリュー・ボラティリティなど）
- 特徴量正規化と戦略用 features テーブルの構築
- シグナル生成（複数コンポーネントの重み付け、Bear レジーム抑制、SELL 条件判定）
- 監査ログ（発注〜約定のトレーサビリティ用スキーマ）
- 設定管理（.env / 環境変数の自動読み込み）

設計方針として、ルックアヘッドバイアスを避けるために「target_date 時点のデータのみ」を使うこと、DuckDB を中心に冪等性（ON CONFLICT / トランザクション）を重視する点が挙げられます。

---

## 主な機能一覧

- データ取得
  - J-Quants からの OHLCV / 財務情報 / マーケットカレンダー取得（ページネーション・レート制御・トークン自動リフレッシュ・リトライ付き）
  - RSS フィード収集（SSRF対策、gzip/サイズ制限、記事IDのデデュープ）
- データ保存
  - DuckDB への冪等保存（raw_prices, raw_financials, market_calendar, raw_news 等）
  - スキーマ初期化（init_schema）
- ETL
  - 日次差分ETL（run_daily_etl）: カレンダー → 株価 → 財務 → 品質検査の流れ
- 研究 / 特徴量
  - モメンタム、ボラティリティ、バリュー計算（research/factor_research）
  - Zスコア正規化ユーティリティ（data.stats.zscore_normalize）
  - 特徴量探索・IC計算ツール（research/feature_exploration）
- 戦略
  - 特徴量構築（strategy.feature_engineering.build_features）
  - シグナル生成（strategy.signal_generator.generate_signals）
- ニュース
  - RSS 収集と raw_news/news_symbols 保存（data.news_collector）
- 監査・実行層スキーマ
  - signal_events / order_requests / executions など監査用 DDL（data.audit）
- 設定管理
  - .env 自動読み込み（プロジェクトルート検出）と settings オブジェクト（kabusys.config）

---

## セットアップ手順

必要条件
- Python 3.9+（typing の一部表現を使用）
- DuckDB（Python パッケージ）
- defusedxml（RSS XML を安全に解析するため）

推奨手順（Unix 系の例）:

1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate

2. 必要パッケージをインストール
   - pip install duckdb defusedxml

   （プロジェクトで追加のパッケージがあれば適宜 pip install してください）

3. 環境変数設定
   - プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます。
   - 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時など）。

4. 必須環境変数（代表例）
   - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabu API パスワード（必須）
   - SLACK_BOT_TOKEN: Slack Bot トークン（必須）
   - SLACK_CHANNEL_ID: Slack チャネル ID（必須）
   - その他オプション:
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL: DEBUG / INFO / ...（デフォルト: INFO）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）

5. データベース初期化（DuckDB スキーマ作成）
   - Python REPL やスクリプトから:
     ```
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")  # ":memory:" も可
     ```
   - init_schema はスキーマを冪等に作成します。（必要な親ディレクトリを自動作成）

---

## 使い方（主要 API / サンプル）

ここでは代表的な利用シーンを簡単に示します。実運用はこれらをラッパースクリプトやジョブ管理（cron / Airflow 等）から呼ぶことを想定しています。

1) DuckDB 初期化
```
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

2) 日次 ETL 実行（J-Quants からの差分取得と保存）
```
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn)  # target_date を指定して特定日を処理可能
print(result.to_dict())
```

3) 特徴量（features）構築
```
from datetime import date
from kabusys.strategy import build_features

cnt = build_features(conn, date(2024, 1, 31))
print(f"features upserted: {cnt}")
```

4) シグナル生成
```
from datetime import date
from kabusys.strategy import generate_signals

total_signals = generate_signals(conn, date(2024, 1, 31))
print(f"signals written: {total_signals}")
```

5) RSS ニュース収集と保存
```
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

# known_codes: 銘柄抽出に使う有効な銘柄コードの集合（例: {'7203','6758',...}）
res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=set_of_codes)
print(res)
```

6) J-Quants API を直接使ってデータを取得・保存（テストや部分取得）
```
from kabusys.data import jquants_client as jq
rows = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
saved = jq.save_daily_quotes(conn, rows)
```

7) 設定取得例
```
from kabusys.config import settings
print(settings.jquants_refresh_token)
print(settings.duckdb_path)
```

注意:
- 各種関数は DuckDB 接続を受け取る設計です。接続は init_schema または get_connection から取得してください。
- トランザクションやエラーハンドリングはライブラリ側で行われますが、呼び出し元でも例外を捕捉してロギング等を行ってください。

---

## 環境変数一覧（主要）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

任意／デフォルト:
- KABUSYS_ENV (development | paper_trading | live) — default: development
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — default: INFO
- DUCKDB_PATH — default: data/kabusys.duckdb
- SQLITE_PATH — default: data/monitoring.db
- KABUSYS_DISABLE_AUTO_ENV_LOAD — set to "1" to disable auto-loading of .env files

設定は .env / .env.local に書くことができ、プロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を自動検出して読み込みます。`.env.local` は `.env` 上書き想定です。

---

## ディレクトリ構成（主要ファイル）

リポジトリの主要なモジュール配置（概略）:

- src/kabusys/
  - __init__.py
  - config.py — 環境変数・設定管理（.env 自動読み込み含む）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得・保存ロジック）
    - news_collector.py — RSS 収集・前処理・保存
    - schema.py — DuckDB スキーマ定義・init_schema
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - features.py — zscore_normalize 再エクスポート
    - calendar_management.py — 営業日判定 / calendar update job
    - audit.py — 監査ログ用スキーマ
    - stats.py — zscore_normalize 等統計ユーティリティ
    - (その他: quality モジュール想定)
  - research/
    - __init__.py
    - factor_research.py — モメンタム/ボラティリティ/バリュー計算
    - feature_exploration.py — IC や将来リターン、統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py — features テーブル構築ロジック
    - signal_generator.py — final_score 計算と signals 生成
  - execution/
    - __init__.py
    - （発注実装 / broker adapter 等を配置）
  - monitoring/
    - __init__.py
    - （監視・メトリクス、Slack 通知等を配置）

各モジュールはドキュメント文字列や logger を備え、DuckDB を中心にデータフローが設計されています。

---

## 運用上の注意 / ヒント

- DuckDB ファイルはデフォルトで `data/kabusys.duckdb` に保存されます。運用時は永続ストレージへ置くこと。
- J-Quants API はレート制限（120 req/min）があります。クライアントは内部でスロットリング・リトライを行いますが、大量バッチ時は注意してください。
- RSS 収集では SSRF 対策やサイズ制限を行っています。ただし、運用用 RSS の追加やカスタマイズ時は URL の安全性を確認してください。
- テスト時は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して .env の自動ロードを抑制できます。
- features / signals 生成は target_date を明示することで過去の日付に対して再計算が可能です（冪等性あり）。

---

この README はコードベースに基づく概要・使用例をまとめたもので、実運用や拡張では追加の設定（認証情報管理、ジョブスケジューラ、監視）やテストが必要です。詳細は各モジュールの docstring を参照してください。