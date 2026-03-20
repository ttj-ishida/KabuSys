# KabuSys

日本株向け自動売買基盤ライブラリ（KabuSys）。  
データ収集（J-Quants）→ ETL（DuckDB）→ 研究/特徴量作成 → シグナル生成 → 実行/監視の各層を想定したモジュール群を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買パイプラインのための内部ライブラリ群です。主な目的は以下。

- J-Quants API からの市場データ・財務データ・カレンダー取得
- DuckDB を用いたローカル DB スキーマと ETL パイプライン
- 研究（factor）モジュールによるファクター計算
- 特徴量正規化と戦略シグナル生成
- RSS ベースのニュース収集と銘柄紐付け
- 発注・約定・監査ログ用スキーマ（Execution / Audit）

設計方針として、ルックアヘッドバイアス防止、冪等性、明示的なトランザクション管理、外部 API 呼び出しのレート制御やリトライなどを重視しています。

---

## 主な機能一覧

- 環境設定管理
  - .env ファイル（および OS 環境変数）から設定を読み込み
  - 必須キーのバリデーション（例: JQUANTS_REFRESH_TOKEN 等）
- データ層（kabusys.data）
  - J-Quants クライアント（fetch / save）: 日足、財務、マーケットカレンダー
  - DuckDB スキーマ定義・初期化（init_schema）
  - ETL パイプライン（差分取得・バックフィル・品質チェック統合）
  - ニュース収集（RSS 取得・正規化・raw_news 保存・銘柄抽出）
  - マーケットカレンダー管理（営業日判定・next/prev_trading_day 等）
  - 汎用統計ユーティリティ（Z スコア正規化等）
- 研究層（kabusys.research）
  - momentum / volatility / value などのファクター計算
  - 将来リターン計算、IC（Spearman）や統計サマリ
- 戦略層（kabusys.strategy）
  - 特徴量構築（build_features）
  - シグナル生成（generate_signals）
    - AI スコア統合、Bear レジーム抑制、BUY/SELL 判定、signals テーブルへの書き込み
- 実行 / 監査（スキーマ定義あり）
  - signal_queue / orders / trades / positions / audit テーブル定義（DB 側）
- セキュリティと堅牢性
  - J-Quants API のレートリミット遵守、リトライ・トークン自動更新
  - RSS の SSRF 対策、XML パースの防御（defusedxml）
  - DB 保存は冪等を意識（ON CONFLICT / トランザクション）

---

## 必要な環境変数

下記の環境変数が使用されます。必須のものは README 例や .env に設定してください。

必須（Settings._require でチェックされるもの）
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

任意（デフォルトあり）
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- KABUSYS_ENV (development | paper_trading | live、デフォルト: development)
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL、デフォルト: INFO)

自動 .env ロードの無効化
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると、自動でプロジェクトルートの .env / .env.local を読み込まなくなります（テスト用）。

.env ファイルの自動ロード
- プロジェクトルート判定は __file__ の親ディレクトリから `.git` または `pyproject.toml` を探索して行われます。見つからない場合は自動ロードをスキップします。

---

## セットアップ手順

1. リポジトリをクローン
   - git clone ...

2. Python（推奨）と仮想環境
   - Python 3.9+ を想定（コードは型ヒントで 3.10 の union 演算子を使用していますが、互換性にご注意ください）。
   - 仮想環境を作成して有効化
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - 必須: duckdb, defusedxml
   - 例:
     - pip install duckdb defusedxml

   （プロジェクトに requirements.txt / pyproject.toml があればそちらを利用してください）

4. 環境変数設定
   - プロジェクトルートに .env を作成するか、OS 環境変数で設定します。
   - 例 (.env):
     JQUANTS_REFRESH_TOKEN=xxxxx
     KABU_API_PASSWORD=xxxxx
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C0123456789
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO

   - セキュリティ上、トークンやパスワードは絶対に公開リポジトリにコミットしないでください。

5. DuckDB スキーマ初期化
   - 以下サンプルを実行して DB とテーブルを作成します（例: Python スクリプトまたは REPL）。
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")

---

## 使い方（主要なサンプル）

以下は代表的な Python スニペット例です。すべて DuckDB 接続（kabusys.data.schema.init_schema）を受け取るよう設計されています。

- DuckDB 初期化と ETL（日次）
  ```python
  from datetime import date
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- 特徴量の構築（戦略用 features テーブル）
  ```python
  from datetime import date
  from kabusys.data.schema import init_schema
  from kabusys.strategy import build_features

  conn = init_schema("data/kabusys.duckdb")
  n = build_features(conn, target_date=date(2024, 1, 31))
  print(f"features upserted: {n}")
  ```

- シグナル生成
  ```python
  from datetime import date
  from kabusys.data.schema import init_schema
  from kabusys.strategy import generate_signals

  conn = init_schema("data/kabusys.duckdb")
  total = generate_signals(conn, target_date=date(2024, 1, 31))
  print(f"signals generated: {total}")
  ```

- ニュース収集
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.data.news_collector import run_news_collection

  conn = init_schema("data/kabusys.duckdb")
  known_codes = {"7203", "6758", "9432"}  # 例: 有効銘柄コードセット
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)
  ```

- カレンダー更新バッチ
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.data.calendar_management import calendar_update_job

  conn = init_schema("data/kabusys.duckdb")
  saved = calendar_update_job(conn)
  print(f"calendar saved: {saved}")
  ```

注意点
- ほとんどの公開 API は DuckDB 接続と target_date を受け取り、対象日分のレコードを読み書きします（ルックアヘッドバイアス防止のため）。
- J-Quants API 呼び出しはトークン・レート制御・リトライを内蔵しています。API トークンは環境変数で指定してください。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要モジュール構成です（抜粋）。

- kabusys/
  - __init__.py
  - config.py                      — 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API クライアント（fetch/save）
    - news_collector.py             — RSS ニュース収集・前処理・保存
    - schema.py                     — DuckDB スキーマと初期化
    - pipeline.py                   — ETL パイプライン（run_daily_etl 等）
    - stats.py                      — 統計ユーティリティ（zscore_normalize）
    - features.py                   — data.stats 再エクスポート
    - calendar_management.py        — カレンダー管理 / 営業日ロジック
    - audit.py                      — 監査ログテーブル DDL
    - quality.py?                   — 品質チェック（参照あり。実装箇所が別にある場合あり）
  - research/
    - __init__.py
    - factor_research.py            — ファクター計算（momentum/volatility/value）
    - feature_exploration.py        — 将来リターン / IC / 統計サマリ
  - strategy/
    - __init__.py
    - feature_engineering.py        — features 作成（build_features）
    - signal_generator.py           — generate_signals（BUY/SELL判定）
  - execution/
    - __init__.py                   — 発注/実行層（プレースホルダ）
  - monitoring/                     — 監視用モジュール（プレースホルダ）
  - その他: README.md, pyproject.toml 等（プロジェクトルート）

（注）一部ファイルは本ドキュメントに含まれていない場合があります。上記はコードベース内に現れるモジュールの主な一覧です。

---

## 実運用上の注意 / ベストプラクティス

- 機密情報（API トークン・パスワード）は .env を使う際も gitignore に追加して管理してください。
- KABUSYS_ENV を `live` に設定すると実運用モードになります。paper_trading / development との切替に注意してください（取引・Slack 通知等の挙動分岐に利用されます）。
- DuckDB ファイルのバックアップ・スナップショット運用を推奨します（ロールバック目的）。
- ETL はネットワーク依存の処理が含まれます。スケジューラ（cron / Airflow 等）での再実行と冪等性を考慮してください。
- ニュース収集や外部 RSS は不特定多数のフォーマットを返すため、文字化けやパーサー例外などをログで監視してください。
- 実際の発注ロジック（ブローカー連携）は execution 層で別実装が必要です。本リポジトリは主にデータ・戦略・シグナル生成を提供します。

---

## 参考・補足

- J-Quants クライアントはリフレッシュトークンから ID トークンを取得する仕組み（get_id_token）を持ち、401 時に自動リフレッシュします。
- RSS の URL 正規化・記事 ID 生成、SSRF 対策（リダイレクト検査・プライベートホスト拒否）等、セキュリティ面の配慮が実装されています。
- 各保存関数は DB 側での冪等（ON CONFLICT）やトランザクション処理を行っています。

---

必要に応じて、README に追記したいサンプル（cron 設定、Dockerfile、CI 設定、さらに詳細な .env.example など）を教えてください。追加で作成します。