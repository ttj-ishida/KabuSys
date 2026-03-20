# KabuSys

日本株自動売買システム（KabuSys）のリポジトリ内ドキュメントです。  
この README はローカル開発／運用で必要な概要・セットアップ・基本的な使い方とプロジェクト構成をまとめています。

---

## プロジェクト概要

KabuSys は日本株向けのデータプラットフォームと自動売買戦略の基盤を提供する Python パッケージです。  
主な目的は以下です。

- J-Quants API 等から市場データ／財務データ／カレンダーを取得して DuckDB に蓄積する（ETL パイプライン）。
- 研究モジュール（research）で計算した生ファクターを用いて特徴量を作成し（feature layer）、戦略用シグナルを生成する。
- ニュース収集・前処理・銘柄抽出機能を通じてニュース由来のスコアや紐付けを行う。
- 発注／約定／ポジション管理のためのスキーマを備え、監査ログ（トレーサビリティ）を保持する。

設計上のポイント:
- ルックアヘッドバイアス回避のため、各処理は target_date 時点のデータのみ参照する仕様。
- DuckDB によるローカル軽量 DB を採用（冪等性やトランザクションを重視）。
- API クライアントはレート制御・リトライ・トークン自動リフレッシュなどを持つ。

---

## 機能一覧

- データ取得・保存
  - J-Quants API クライアント（株価日足、財務、マーケットカレンダー）
  - raw データの保存（raw_prices, raw_financials, raw_news など）
  - DuckDB スキーマ定義と初期化（init_schema）
- ETL / Data Pipeline
  - run_daily_etl：市場カレンダー→株価→財務の差分ETL（バックフィル対応）
  - 品質チェック（quality モジュール）フックあり
- 研究・特徴量
  - ファクター計算（momentum / volatility / value）
  - Zスコア正規化ユーティリティ
  - 特徴量作成（build_features）
  - 特徴量探索 / IC 計算（research.feature_exploration）
- 戦略
  - シグナル生成（generate_signals：BUY/SELL の判定ロジック）
  - エグジット判定（ストップロス等）
- ニュース収集
  - RSS フィード取得・前処理・記事保存・銘柄抽出
  - SSRF や XML Bomb などを意識した安全対策実装
- カレンダー管理
  - 営業日判定・next/prev_trading_day・カレンダー更新ジョブ
- 監査ログ（audit）
  - signal_events / order_requests / executions 等の監査スキーマ

---

## 要求環境・依存ライブラリ（参考）

本 README はコード内容に基づく一般的な依存の例を示します。実際のパッケージ配布設定（pyproject.toml / requirements.txt）に従ってください。

- Python 3.9+
- duckdb
- defusedxml
- （標準ライブラリのみで書かれている部分が多いですが、HTTP周りで urllib を使用しています）
- （実際に Slack 通知等を行う場合は slack SDK 等が別途必要になる可能性があります）

開発時は仮想環境を作成して依存をインストールしてください。

---

## 環境変数 / 設定

パッケージは環境変数を用いて各種設定を読み込みます。自動的にプロジェクトルートの `.env` と `.env.local` を読み込む処理があります（読み込み順：OS 環境 > .env.local > .env）。自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須の環境変数（Settings クラスで参照）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabu ステーション API のパスワード（利用時）
- SLACK_BOT_TOKEN — Slack 通知に使用する Bot トークン（利用時）
- SLACK_CHANNEL_ID — Slack チャンネル ID（利用時）

その他の設定:
- KABUSYS_ENV — "development" / "paper_trading" / "live"（デフォルト: development）
- LOG_LEVEL — "DEBUG" / "INFO" / "WARNING" / "ERROR" / "CRITICAL"（デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）

簡易的な .env.example（プロジェクトルートに配置）例:
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_api_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb

※ 実運用では機密値の管理に注意してください（.env は .gitignore 推奨）。

---

## セットアップ手順（最短）

1. リポジトリをクローンして仮想環境を作成
   - 例:
     ```
     git clone <repo-url>
     cd <repo>
     python -m venv .venv
     source .venv/bin/activate
     ```

2. 依存のインストール（例）
   - requirements.txt があれば:
     ```
     pip install -r requirements.txt
     ```
   - 最低限（参考）:
     ```
     pip install duckdb defusedxml
     ```

3. 環境変数を設定（`.env` / `.env.local` をプロジェクトルートに作成）
   - `.env` に上で示した必須変数を設定

4. データベーススキーマの初期化
   - Python から DuckDB を初期化:
     ```
     python - <<'PY'
     from kabusys.data.schema import init_schema
     from kabusys.config import settings
     init_schema(settings.duckdb_path)
     print("init done:", settings.duckdb_path)
     PY
     ```
   - または直接パスを指定:
     ```
     python - <<'PY'
     from kabusys.data.schema import init_schema
     init_schema("data/kabusys.duckdb")
     PY
     ```

---

## 使い方（代表的な操作例）

以下はライブラリの主要なエントリポイントの利用例です。実運用コードでは例外処理やログ設定を適切に行ってください。

- 日次 ETL（市場カレンダー / 株価 / 財務 の差分 ETL）を実行:
  ```python
  from datetime import date
  from kabusys.data.schema import init_schema, get_connection
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings

  conn = init_schema(settings.duckdb_path)
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- 特徴量（features）を構築:
  ```python
  from datetime import date
  import duckdb
  from kabusys.strategy import build_features
  from kabusys.config import settings

  conn = duckdb.connect(settings.duckdb_path)
  n = build_features(conn, target_date=date.today())
  print("features upserted:", n)
  ```

- シグナルを生成:
  ```python
  from datetime import date
  import duckdb
  from kabusys.strategy import generate_signals
  from kabusys.config import settings

  conn = duckdb.connect(settings.duckdb_path)
  total = generate_signals(conn, target_date=date.today())
  print("signals generated:", total)
  ```

- ニュース収集（RSS）を実行:
  ```python
  import duckdb
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

  conn = duckdb.connect("data/kabusys.duckdb")
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203","6758"})
  print(results)
  ```

- カレンダー更新バッチ:
  ```python
  import duckdb
  from kabusys.data.calendar_management import calendar_update_job

  conn = duckdb.connect("data/kabusys.duckdb")
  saved = calendar_update_job(conn)
  print("calendar saved:", saved)
  ```

注意:
- 上の例は同期的に動作します。実際の運用ではジョブスケジューラ（cron / Airflow 等）やプロセス管理が必要です。
- J-Quants の API レート制限や認証を正しく設定してください。get_id_token でトークン取得、fetch 系関数は自動リフレッシュを行います。

---

## ディレクトリ構成（主なファイル）

リポジトリの主要なパッケージ／モジュールとその役割を抜粋します（src/kabusys 以下）。

- kabusys/
  - __init__.py — パッケージのエントリ
  - config.py — 環境変数 / 設定管理（.env 自動読み込み、Settings クラス）
  - data/
    - __init__.py
    - schema.py — DuckDB スキーマ定義と init_schema / get_connection
    - jquants_client.py — J-Quants API クライアント（取得 / 保存ユーティリティ）
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - news_collector.py — RSS 取得と raw_news 保存、銘柄抽出
    - calendar_management.py — 市場カレンダー管理（営業日判定等）
    - features.py — zscore_normalize 再エクスポート
    - stats.py — zscore_normalize（汎用統計）
    - audit.py — 監査ログ用スキーマ（signal_events / order_requests / executions）
    - (その他 data 内に quality 等のモジュールを想定)
  - research/
    - __init__.py
    - factor_research.py — momentum / volatility / value の計算
    - feature_exploration.py — 将来リターン・IC・要約統計
  - strategy/
    - __init__.py (build_features, generate_signals をエクスポート)
    - feature_engineering.py — features テーブル構築（正規化・フィルタ）
    - signal_generator.py — final_score 計算と BUY/SELL シグナル生成
  - execution/ — 発注関連（未記載の実装がある場合）
  - monitoring/ — 監視・モニタリング関連（未記載の実装がある場合）

（上記は、ソース内に存在するファイルに基づく抜粋です。実際のリポジトリツリーには他の補助ファイルが含まれる可能性があります。）

簡易ツリー例:
- src/
  - kabusys/
    - config.py
    - data/
      - schema.py
      - jquants_client.py
      - pipeline.py
      - news_collector.py
      - calendar_management.py
      - stats.py
      - features.py
      - audit.py
    - research/
      - factor_research.py
      - feature_exploration.py
    - strategy/
      - feature_engineering.py
      - signal_generator.py
    - execution/
    - monitoring/

---

## 運用上の注意 / ヒント

- 環境変数・機密情報管理
  - .env を直接レポジトリで管理しない（.gitignore へ追加）。秘密情報は Vault 等で管理してください。
- DB のバックアップ
  - DuckDB ファイルは軽量ですが定期バックアップを推奨します。
- レート制御・リトライ
  - J-Quants API はレート制限があり、クライアント側でも固定スロットリングとリトライが実装されています。運用時は API 利用量を監視してください。
- 本番パラメータ
  - KABUSYS_ENV を切り替えることで動作モード（paper_trading / live）を切り替えます。実行前に設定値を十分確認してください。
- テスト
  - config の自動 .env ロードはテストのために無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。

---

ライセンス・貢献等についてはリポジトリのルートにある LICENSE / CONTRIBUTING を参照してください（存在する場合）。質問や補足のドキュメント化が必要であれば、目的の操作（例: ETL の運用スケジュール例、cron/airflow でのデプロイ例、Slack 通知サンプル）を教えてください。README を拡張します。