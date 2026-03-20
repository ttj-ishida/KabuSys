# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ（KabuSys）の README。  
このリポジトリはデータ取得（J-Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、カレンダー管理、監査ログなどを含む内部ライブラリ群を提供します。

---

## プロジェクト概要

KabuSys は以下レイヤーを持つ日本株自動売買システムのコア部分を提供する Python パッケージです。

- Data layer: J-Quants からのデータ取得、DuckDB への保存（生データ / 加工データ / 特徴量 / 実行ログ）
- Research layer: ファクター計算、特徴量探索、IC や将来リターン計算
- Strategy layer: 特徴量の正規化・合成（feature_engineering）、最終スコアによる売買シグナル生成（signal_generator）
- Execution / Audit: 発注・約定・ポジション・監査ログ用のスキーマ（API 統合は別層で実装）
- News collection: RSS からのニュース収集と銘柄紐付け
- Calendar management: JPX カレンダー管理、営業日判定

設計方針の一例:
- ルックアヘッドバイアスを避けるため「target_date 時点のデータのみ」を使用
- DuckDB を使ったローカル DB（冪等保存 / トランザクション）によるデータ永続化
- 外部依存を最小化（標準ライブラリ + 必須ライブラリのみ）

---

## 主な機能一覧

- J-Quants API クライアント（rate limit / retry / token refresh 対応）
  - 株価（daily quotes）、財務データ、マーケットカレンダー取得
- ETL パイプライン
  - 差分取得、バックフィル、品質チェックを含む日次 ETL（run_daily_etl）
- DuckDB スキーマ初期化（init_schema）
- ファクター計算（momentum / volatility / value）
- 特徴量構築（Z スコア正規化・ユニバースフィルタ） → features テーブル保存
- シグナル生成（AI スコアとの統合、ベア相場抑制、BUY/SELL 識別） → signals テーブル保存
- ニュース収集（RSS）と銘柄抽出・紐付け
- マーケットカレンダー管理・営業日演算（next_trading_day / prev_trading_day / get_trading_days）
- 監査ログ・トレーサビリティ用スキーマ（signal_events, order_requests, executions 等）

---

## 必要条件 / 推奨

- Python 3.10+
  - 型注釈に新しい構文（X | None など）を使用しているため 3.10 以上を想定しています。
- 主要依存パッケージ（例）
  - duckdb
  - defusedxml

（プロジェクトに pyproject.toml / requirements.txt があればそちらを利用してください）

---

## セットアップ手順

1. リポジトリをクローン / 取得
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成・有効化（例）
   ```
   python -m venv .venv
   source .venv/bin/activate   # Unix/macOS
   .venv\Scripts\activate      # Windows (PowerShell: .venv\Scripts\Activate.ps1)
   ```

3. 必要パッケージをインストール
   - 最低限:
     ```
     pip install duckdb defusedxml
     ```
   - もしパッケージ化されていれば editable install:
     ```
     pip install -e .
     ```
   - その他、テストや補助ツールがあれば requirements を参照してインストールしてください。

4. 環境変数を設定
   - プロジェクトルートに `.env` / `.env.local` を配置できます（自動読み込み機能あり）。
   - 必須の環境変数（Settings クラス参照）:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD — kabuステーション API パスワード（実行層で使用）
     - SLACK_BOT_TOKEN — Slack 通知用トークン（モニタリング等）
     - SLACK_CHANNEL_ID — Slack チャンネル ID
   - 任意:
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
     - KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト development）
     - LOG_LEVEL — ログレベル: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）

   例 `.env`（簡易）
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxx
   KABU_API_PASSWORD=secret
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=DEBUG
   ```

   注: 自動環境変数ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をセットすると無効化できます（テスト時に便利）。

5. DuckDB スキーマ初期化
   - 初回はスキーマを作成します。Python REPL やスクリプトから:
     ```python
     from kabusys.data.schema import init_schema
     from kabusys.config import settings

     conn = init_schema(settings.duckdb_path)
     conn.close()
     ```

---

## 使い方（代表的な操作例）

以下はライブラリを直接呼ぶ簡単な例です。実際は CLI やワークフロー管理ツール（cron / Airflow / Prefect 等）から呼ぶ想定です。

- 日次 ETL を実行（市場カレンダー・株価・財務の差分取得 + 品質チェック）
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.schema import init_schema, get_connection
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings

  # 初期化済み DB に接続（既に init_schema 済みなら get_connection を使う）
  conn = init_schema(settings.duckdb_path)

  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- 特徴量の構築（features テーブルの作成）
  ```python
  from datetime import date
  from kabusys.strategy import build_features
  from kabusys.data.schema import get_connection
  from kabusys.config import settings

  conn = get_connection(settings.duckdb_path)
  n = build_features(conn, target_date=date(2025, 3, 1))
  print(f"features upserted: {n}")
  ```

- シグナル生成（signals テーブルの作成）
  ```python
  from datetime import date
  from kabusys.strategy import generate_signals
  from kabusys.data.schema import get_connection
  from kabusys.config import settings

  conn = get_connection(settings.duckdb_path)
  total = generate_signals(conn, target_date=date(2025, 3, 1))
  print(f"signals created: {total}")
  ```

- ニュース収集ジョブを実行
  ```python
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  from kabusys.data.schema import get_connection
  from kabusys.config import settings

  conn = get_connection(settings.duckdb_path)
  known_codes = {"7203", "6758", ...}  # 既知の銘柄コードセット
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
  print(results)
  ```

- カレンダーを差分更新
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  from kabusys.data.schema import get_connection
  from kabusys.config import settings

  conn = get_connection(settings.duckdb_path)
  saved = calendar_update_job(conn)
  print(f"calendar saved: {saved}")
  ```

---

## 実行モード

環境変数 `KABUSYS_ENV` により実行モードを切り替えます（Settings クラスで検証）:

- development — 開発用（デフォルト）
- paper_trading — ペーパートレード用
- live — 実運用（本番）

コード内で `settings.is_dev`, `settings.is_paper`, `settings.is_live` を使用してモード判定できます。

---

## ディレクトリ構成（主なファイル / モジュール）

以下は主要なパッケージ構成です（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得 / 保存ユーティリティ）
    - news_collector.py — RSS ニュース収集・前処理・DB 保存
    - schema.py — DuckDB スキーマ定義・初期化
    - stats.py — Z-score など統計ユーティリティ
    - pipeline.py — ETL パイプライン（run_daily_etl など）
    - calendar_management.py — 市場カレンダー管理（営業日演算、更新ジョブ）
    - audit.py — 監査ログ用スキーマ
    - features.py — data.stats の再エクスポート
  - research/
    - __init__.py
    - factor_research.py — momentum / volatility / value のファクター計算
    - feature_exploration.py — 将来リターン / IC / 統計サマリー等
  - strategy/
    - __init__.py
    - feature_engineering.py — 生ファクターの正規化・ユニバースフィルタ・features 保存
    - signal_generator.py — final_score 計算、BUY/SELL シグナル生成、signals 保存
  - execution/
    - __init__.py  — 実行層（今後発注連携やブローカー相互作用を実装）
  - monitoring/ (パッケージとして __all__ に含まれますがコードは省略されている可能性があります)

（上記はリポジトリ内のソースから抽出した概略です。実際のファイル/追加モジュールはリポジトリを参照してください）

---

## テスト・開発メモ

- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行われます。
- テスト時に自動読み込みを無効化する場合:
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```
- DuckDB の `:memory:` を使えばインメモリ DB でテスト可能です:
  ```python
  from kabusys.data.schema import init_schema
  conn = init_schema(":memory:")
  ```
- J-Quants API のリクエストは内部で rate limit / retry / token refresh を行いますが、API 呼び出し部分はテスト用にモック可能です（関数単位で id_token を注入できる実装になっています）。

---

## ライセンス / 貢献

（この README にライセンス・コントリビューション規約の情報を追加してください。プロジェクトに LICENSE ファイルがあればその内容を参照してください。）

---

この README はコードベースの主要機能と利用方法の概要をまとめたものです。詳細な設計仕様（StrategyModel.md, DataPlatform.md 等）がリポジトリに含まれている場合はそちらも参照してください。必要であれば、CLI 例や Airflow / cron での運用例、監視・アラート設定方法などの追加ドキュメントも作成します。