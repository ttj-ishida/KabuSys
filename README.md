# KabuSys

日本株向けの自動売買／データ基盤ライブラリ群です。  
本リポジトリはデータ取得（J-Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、マーケットカレンダー管理、監査・実行レイヤーのスキーマ定義などを含むモジュール群で、研究・本番の両方で利用できる設計になっています。

---

## プロジェクト概要

KabuSys は以下を目的としたコンポーネント群を提供します。

- J-Quants API からの株価・財務・市場カレンダー取得（レート制御・リトライ・トークン自動リフレッシュ対応）
- DuckDB を用いたデータレイク（Raw / Processed / Feature / Execution 層）のスキーマ定義と初期化
- ETL パイプライン（差分更新、バックフィル、品質チェック連携）
- 特徴量エンジニアリング（research モジュールの生ファクターを正規化して features テーブルへ保存）
- シグナル生成（features + ai_scores を統合して BUY / SELL シグナルを作成）
- ニュース収集（RSS -> raw_news、銘柄抽出、SSRF/サイズ制限等の安全対策あり）
- マーケットカレンダー管理（営業日の判定・次営業日の計算等）
- 実行／監査レイヤー（signal / order / execution / positions 等のテーブル定義）

設計上の特徴:
- ルックアヘッドバイアス回避（target_date 時点のみを参照）
- 冪等性（DB への保存は ON CONFLICT / INSERT ... DO UPDATE / DO NOTHING を活用）
- 外部依存は最小限（標準ライブラリ中心、主要に duckdb / defusedxml 等）

---

## 主な機能一覧

- データ取得
  - J-Quants クライアント（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）
  - レートリミッタ、リトライ、トークン自動更新
- データ保存
  - DuckDB への冪等保存関数（raw_prices, raw_financials, market_calendar, raw_news 等）
- ETL
  - 日次差分 ETL（run_daily_etl）：calendar → prices → financials → 品質チェック
  - 差分取得・バックフィル対応
- 研究 / 戦略
  - factor_research: momentum/volatility/value の計算
  - feature_engineering: ファクターの統合・Zスコア化・ユニバースフィルタ → features
  - signal_generator: final_score 計算、BUY/SELL シグナル生成、signals テーブル書き込み
- ニュース収集
  - RSS フィード取得（SSRF 対策・gzip・サイズ制限・XML 脆弱性対策）
  - raw_news / news_symbols への冪等保存
- カレンダー管理
  - 営業日判定・next/prev_trading_day・calendar_update_job
- スキーマ & 初期化
  - DuckDB スキーマの定義と init_schema 関数
- 監査ログ
  - signal_events / order_requests / executions 等、監査テーブル

---

## 前提・依存関係

- Python 3.10+
  - 理由: 型注釈に `|` を使用しているため
- 必要パッケージ（代表例）
  - duckdb
  - defusedxml
- （オプション）その他 logging 等は標準ライブラリで利用

インストール例（仮に pyproject.toml がある想定）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb defusedxml
pip install -e .    # パッケージを editable install（ローカル開発向け）
```

---

## 環境変数（主な必須設定）

アプリ設定は環境変数 / .env(.local) から自動読込されます（プロジェクトルートに .git または pyproject.toml がある場合）。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須（少なくとも設定が必要なもの）:
- JQUANTS_REFRESH_TOKEN: J-Quants の refresh token
- KABU_API_PASSWORD: kabuステーション API パスワード（execution 層用）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（通知機能を使う場合）
- SLACK_CHANNEL_ID: Slack チャネル ID（通知先）

その他（任意／デフォルトあり）:
- KABUSYS_ENV: development | paper_trading | live（デフォルト development）
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト INFO）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB 等（デフォルト data/monitoring.db）

.env 例:
```
JQUANTS_REFRESH_TOKEN=xxxxx
KABU_API_PASSWORD=secret
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
DUCKDB_PATH=data/kabusys.duckdb
```

---

## セットアップ手順

1. Python 仮想環境の作成
   - python -m venv .venv ; source .venv/bin/activate

2. 必要パッケージのインストール
   - pip install duckdb defusedxml
   - プロジェクトに pyproject.toml があれば pip install -e . など

3. 環境変数設定
   - 上記の必須環境変数を .env または環境へ設定

4. DuckDB スキーマ初期化
   - 例:
     ```python
     from kabusys.config import settings
     from kabusys.data.schema import init_schema

     conn = init_schema(settings.duckdb_path)  # data/kabusys.duckdb を作成・テーブル生成
     ```

---

## 使い方（代表的な操作例）

以下は基本的なワークフロー例です。コードスニペットは Python REPL やスクリプト内で実行してください。

- DuckDB の初期化:
  ```python
  from kabusys.config import settings
  from kabusys.data.schema import init_schema

  conn = init_schema(settings.duckdb_path)
  ```

- 日次 ETL（株価 / 財務 / カレンダーの差分取得 + 品質チェック）:
  ```python
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn)
  print(result.to_dict())
  ```

- 特徴量作成（research の計算結果を統合して features テーブルに保存）:
  ```python
  from datetime import date
  from kabusys.strategy import build_features

  target = date(2025, 3, 18)
  n = build_features(conn, target)
  print(f"features upserted: {n}")
  ```

- シグナル生成（features + ai_scores を基に signals を作成）:
  ```python
  from datetime import date
  from kabusys.strategy import generate_signals

  target = date(2025, 3, 18)
  total = generate_signals(conn, target, threshold=0.6)
  print(f"signals created: {total}")
  ```

- ニュース収集ジョブ（RSS から raw_news を保存し銘柄紐付け）:
  ```python
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

  known_codes = {"7203", "6758", "9984"}  # 例: 有効な銘柄コードセット
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
  print(results)
  ```

- カレンダーの夜間更新ジョブ:
  ```python
  from kabusys.data.calendar_management import calendar_update_job

  saved = calendar_update_job(conn)
  print(f"calendar saved: {saved}")
  ```

- スキーマのみを取得する場合（既存 DB に接続）:
  ```python
  from kabusys.data.schema import get_connection
  conn = get_connection("data/kabusys.duckdb")
  ```

ログレベルの調整は環境変数 LOG_LEVEL または Python 側で logging.basicConfig(level=...) にて行ってください。

---

## ディレクトリ構成

主要ファイル・モジュール構成（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py                       — 環境変数 / 設定管理（.env 自動読み込み）
  - data/
    - __init__.py
    - jquants_client.py              — J-Quants API クライアント（レート制御・リトライ）
    - news_collector.py              — RSS 収集・前処理・保存
    - schema.py                      — DuckDB スキーマ定義 / init_schema
    - stats.py                       — zscore_normalize 等の統計ユーティリティ
    - pipeline.py                    — ETL パイプライン（run_daily_etl 等）
    - features.py                    — data.stats の再エクスポート
    - calendar_management.py         — マーケットカレンダー管理/ユーティリティ
    - audit.py                       — 監査ログ関連 DDL（signal_events, order_requests, executions）
    - (その他: quality 等が想定される)
  - research/
    - __init__.py
    - factor_research.py             — momentum/volatility/value の計算
    - feature_exploration.py         — forward returns / IC / summary
  - strategy/
    - __init__.py
    - feature_engineering.py         — features テーブル作成（正規化・フィルタ）
    - signal_generator.py            — final_score 計算・BUY/SELL 生成
  - execution/                       — 発注・実行関連（パッケージ化済み）
  - monitoring/                      — 監視周り（sqlite 等を利用する想定）

（上記は本コードベースに含まれる主要モジュールの抜粋です。実運用時は quality、monitoring、execution の実装や補助ユーティリティも合わせて確認してください。）

---

## 注意点 / 運用メモ

- DuckDB のファイルパスはデフォルト `data/kabusys.duckdb`。別パスを利用する場合は DUCKDB_PATH 環境変数または init_schema の引数で変更してください。
- J-Quants API のレート制限（120 req/min）に合わせた設計になっています。クライアント層で固定間隔スロットリングを実装しています。
- 自動で .env を読み込む処理はプロジェクトルート（.git または pyproject.toml）を基準に探索します。テスト時等に自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- 本ライブラリはルックアヘッドバイアスを意識した実装方針（target_date 時点のデータのみを参照）を採用しています。研究時には date を明示して計算してください。
- signals → 実際の発注（execution 層）への送出は別モジュール（execution/）で行う想定です。本リポジトリのコードだけで自動発注する場合は追加の実装・注意（テスト、リスク管理）が必要です。

---

## 補足

- README に記載の方法はライブラリ利用の基本例です。実際の運用ではログ収集、監視、アラート、リスクパラメータ（最大保有数・最大エクスポージャ等）を追加してください。
- API キーやパスワードは安全に保管し、CI/CD 等での取り扱いに注意してください（シークレットストアの使用を推奨）。

---

必要であれば README に「デプロイ手順」「cron/ジョブ管理（例: Airflow / systemd timer）」やサンプル SQL（テーブル定義の確認方法）、具体的な .env.example を追記できます。どの情報を追加しますか？