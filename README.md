# KabuSys

日本株向け自動売買／データ基盤ライブラリ KabuSys のリポジトリルート用 README。

この README はソースコード（src/kabusys/ 以下）を元に作成しています。実装済みの主要機能、セットアップ方法、簡単な使い方、ディレクトリ構成を日本語でまとめています。

注意: 本ライブラリは実際の発注を行う可能性のある機能（kabuステーション API 連携など）を含みます。実運用（特に `KABUSYS_ENV=live`）で使用する前に十分なテストとリスク管理（バックテスト、ペーパートレード等）を行ってください。

---

## プロジェクト概要

KabuSys は日本株向けに設計されたデータパイプライン、ファクター計算、戦略シグナル生成、ニュース収集、監査ログ等を含む自動売買・研究基盤です。主に以下を目的としています：

- J-Quants API から市場データ・財務データ・カレンダーを取得し DuckDB に保存する ETL パイプライン
- 研究（research）モジュールでファクター計算、特徴量探索を行う
- 特徴量の正規化・合成（feature_engineering）およびシグナル生成（signal_generator）
- RSS ベースのニュース収集、テキスト前処理と銘柄抽出
- DuckDB に対するスキーマ初期化・管理
- 発注・約定・ポジション管理を想定した実行レイヤ（スキーマ、監査ログ設計）

設計方針として、ルックアヘッドバイアス防止、冪等性（重複挿入回避）、外部ライブラリへの極力依存しない実装（pandas等を使わない）を重視しています。

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API のクライアント（ページネーション・レート制御・リトライ・トークン自動リフレッシュ）
  - schema: DuckDB のスキーマ定義と初期化（raw / processed / feature / execution 層）
  - pipeline: 日次差分 ETL 実行（価格・財務・カレンダー取得、品質チェック呼び出し）
  - news_collector: RSS フィード取得・前処理・DB 保存、銘柄コード抽出
  - calendar_management: 市場カレンダー操作・営業日判定ユーティリティ・夜間更新ジョブ
  - stats: Zスコア正規化などの統計ユーティリティ
- research/
  - factor_research: Momentum / Value / Volatility / Liquidity 等ファクター計算
  - feature_exploration: 将来リターン計算、IC（Spearman）計算、ファクター統計サマリー
- strategy/
  - feature_engineering: 生ファクターのフィルタリング・正規化・features テーブルへの保存
  - signal_generator: features と ai_scores を統合して final_score を算出、BUY/SELL シグナルを生成して signals テーブルへ保存
- config: .env 自動読み込み・設定管理
  - 自動ロード優先順: OS環境変数 > .env.local > .env（プロジェクトルートに .git または pyproject.toml を見つけて自動検出）
  - 環境変数が必須のキーは実行時に例外を投げる

その他、監査ログ（audit）や execution 層のテーブル定義・管理コードを備えます。

---

## 要件（概略）

- Python 3.10 以上（ソースは型ヒントで | 記法を使用）
- duckdb
- defusedxml
- 標準ライブラリの urllib 等を使用
- そのほか運用に応じて Slack API クライアントや kabuステーション API クライアント等（本リポジトリでは kabu API 呼び出しは別モジュールや実行層で扱う想定）

（実プロジェクトでは requirements.txt / pyproject.toml を用意してください）

---

## セットアップ手順

1. リポジトリをクローン／チェックアウト
   - 例: git clone <repo-url>

2. Python 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージのインストール（例）
   - pip install duckdb defusedxml

   ※ 実環境では PyPI 依存を requirements.txt や pyproject.toml にまとめてください。

4. 環境変数設定
   - プロジェクトルート（.git のある親ディレクトリ）に `.env` または `.env.local` を置くと自動で読み込まれます（ただし、KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込みを無効化できます）。
   - 必須の環境変数（少なくとも以下を設定してください）:

     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD: kabu API のパスワード（発注を行う場合）
     - SLACK_BOT_TOKEN: Slack 連携を行う場合
     - SLACK_CHANNEL_ID: Slack 連携チャネル ID
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: SQLite（監視用）パス（デフォルト: data/monitoring.db）
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）

   - .env の例:
     ```
     JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C12345678
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

5. DuckDB スキーマ初期化
   - Python REPL やスクリプトから以下を実行して DB を初期化します:

     ```python
     from kabusys.data.schema import init_schema, get_connection
     conn = init_schema("data/kabusys.duckdb")  # ファイルパスに合わせて変更
     # またはメモリDB:
     # conn = init_schema(":memory:")
     ```

---

## 使い方（主要ユースケース）

下に示すのは主要機能の呼び出し例です。実運用ではロギング設定・例外処理・スケジューラ（cron等）を適切に組み合わせてください。

- 日次 ETL（市場カレンダー、株価、財務の差分取り込み）
  ```python
  from datetime import date
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- 特徴量構築（features テーブルへの保存）
  ```python
  from datetime import date
  import duckdb
  from kabusys.strategy import build_features
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  count = build_features(conn, target_date=date(2026, 1, 31))
  print(f"features updated: {count}")
  ```

- シグナル生成（signals テーブルへの保存）
  ```python
  from datetime import date
  from kabusys.strategy import generate_signals
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  total = generate_signals(conn, target_date=date(2026,1,31))
  print(f"signals generated: {total}")
  ```

- RSS ニュース収集ジョブ
  ```python
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  known_codes = {"7203", "6758", "9984"}  # 既知の銘柄コードセット
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
  print(results)
  ```

- カレンダー夜間更新ジョブ
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  saved = calendar_update_job(conn)
  print(f"market calendar saved: {saved}")
  ```

- J-Quants データ取得（個別）
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
  from kabusys.config import settings

  token = get_id_token()  # settings.jquants_refresh_token を使用
  quotes = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))
  ```

重要: 上の例では DuckDB 接続を直接使っています。init_schema はテーブル作成まで行い、get_connection は既存 DB へ接続します。

---

## 環境変数（主要項目）

- JQUANTS_REFRESH_TOKEN (必須): J-Quants API のリフレッシュトークン。jquants_client が ID トークンを取得するために使用されます。
- KABU_API_PASSWORD (必須 for execution): kabuステーション API のパスワード（発注する場合）。
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: Slack 通知用（オプション）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite パス（監視用、デフォルト: data/monitoring.db）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL: ログレベル（デフォルト INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1: 自動 .env ロードを無効化

自動読み込みの優先順は OS 環境変数 > .env.local > .env です。プロジェクトルートは実ファイル位置から上位の親ディレクトリで `.git` または `pyproject.toml` を探索して決定します。見つからない場合は .env 自動ロードをスキップします。

---

## ディレクトリ構成（抜粋）

以下は src/kabusys/ 以下の主要ファイル・パッケージと役割の一覧です。

- kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み・Settings クラス（J-Quants/SLACK/Kabu/DB 設定等）
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（レート制御・リトライ・トークン管理・保存ユーティリティ）
    - news_collector.py
      - RSS 収集、前処理、raw_news 保存、銘柄抽出
    - schema.py
      - DuckDB スキーマ定義・init_schema / get_connection
    - stats.py
      - zscore_normalize 等の統計ユーティリティ
    - pipeline.py
      - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
    - calendar_management.py
      - 市場カレンダー操作（is_trading_day / next_trading_day / get_trading_days / calendar_update_job）
    - features.py
      - zscore_normalize の再エクスポート
    - audit.py
      - 監査ログ用 DDL（signal_events, order_requests, executions）
  - research/
    - __init__.py
    - factor_research.py
      - calc_momentum / calc_volatility / calc_value（prices_daily, raw_financials を参照）
    - feature_exploration.py
      - calc_forward_returns / calc_ic / factor_summary / rank
  - strategy/
    - __init__.py
      - build_features, generate_signals を公開
    - feature_engineering.py
      - 生ファクターのユニバースフィルタ、Zスコア正規化、features への UPSERT（冪等）
    - signal_generator.py
      - final_score 計算、BUY/SELL シグナル生成、signals への書き込み（冪等）
  - execution/
    - __init__.py
      - （発注・実行ロジックは別モジュールで実装想定／未実装の部分あり）

---

## 設計上の注意点・運用上のヒント

- ルックアヘッドバイアス対策: feature/strategy の計算は target_date 時点のデータのみを使うよう設計されています。ETL や特徴量計算の呼び出し順に注意し、未来データが混入しないようにしてください。
- 冪等性: jquants_client の保存関数や schema の DDL は冪等に設計されています（ON CONFLICT 句を使用）。
- レート制御: J-Quants API はレート制限（120 req/min）を想定した固定間隔スロットリングを実装しています。
- Bear レジーム: signal_generator は ai_scores に基づき Bear レジームを検知し、BUY シグナルを抑制するロジックを持っています。
- 実取引時の安全策: live 環境で稼働させる前に paper_trading で十分に検証を行ってください。ストップロスやエグジット条件がコード内にあるものの、発注部分／ブローカーとの整合性・ネットワークエラー処理など細心の注意が必要です。

---

## 貢献・拡張案

- execution 層の broker 連携（kabu API クライアント実装、order lifecycle の管理）
- モニタリング／アラート（Slack 通知の実装）
- テストカバレッジ増強（ユニット・インテグレーション）
- requirements.txt / pyproject.toml の整備、CI（Lint / type check / tests）の導入
- 設定ファイル・ロギング設定の標準化

---

以上。README の内容はソースコードの現状に基づいてまとめています。追加で README に含めたい具体的なコマンド例や、pyproject.toml / CI のテンプレートなどがあれば教えてください。