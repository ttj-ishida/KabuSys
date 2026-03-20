# KabuSys

バージョン: 0.1.0

KabuSys は日本株向けの自動売買システム基盤です。データ取得（J-Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、DuckDB ベースのデータレイヤ、監査ログなどを提供します。研究（research）用途と実運用（execution）用途を分離した設計で、ルックアヘッドバイアス防止や冪等性（idempotency）を重視しています。

---

## 主な機能一覧

- データ取得（J-Quants API クライアント）
  - 株価日足（OHLCV）、財務諸表、マーケットカレンダー取得
  - レート制限遵守・リトライ・トークン自動リフレッシュ
- ETL（差分更新）
  - 差分フェッチ、バックフィル、品質チェックとの連携
  - 日次バッチ実行（run_daily_etl）
- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution 層を含むスキーマ定義・初期化（init_schema）
- ニュース収集
  - RSS 取得、前処理、記事保存、銘柄抽出（SSRF/XML Bomb 対策済み）
- 研究用ファクター計算（research）
  - Momentum / Volatility / Value 等のファクター計算
  - 将来リターン計算、IC（Spearman）や統計サマリー
- 特徴量エンジニアリング（strategy.feature_engineering）
  - ファクター統合、ユニバースフィルタ、Zスコア正規化、features テーブルへのアップサート
- シグナル生成（strategy.signal_generator）
  - 正規化ファクター + AI スコアを統合して final_score を算出
  - Bear レジーム検出、BUY/SELL シグナル生成、signals テーブルへの書き込み
- 監査ログ（audit）
  - signal_events / order_requests / executions 等の監査テーブル
- 設定管理
  - .env / 環境変数読み込み（自動読み込み、無効化オプションあり）

---

## 要件

- Python 3.10 以上（PEP 604 の union 型記法などを使用）
- 推奨パッケージ（例）
  - duckdb
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS フィード）

---

## セットアップ手順

1. リポジトリをクローン（省略可）
   - git clone <リポジトリURL>

2. 仮想環境作成・有効化
   - macOS / Linux:
     - python -m venv .venv
     - source .venv/bin/activate
   - Windows (PowerShell):
     - python -m venv .venv
     - .\.venv\Scripts\Activate.ps1

3. パッケージインストール
   - 開発中にソースを編集するなら編集可能インストール:
     - pip install -e .
   - 必要に応じて依存を直接インストール:
     - pip install duckdb defusedxml

4. 環境変数設定
   - J-Quants / kabuステーション / Slack 等の認証情報を環境変数またはプロジェクトルートの .env / .env.local に設定します。
   - 必須（Settings で _require されるもの）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - その他（デフォルト値あり）
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — デフォルト: INFO
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db
   - 自動 .env 読み込みを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

   例 (.env):
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. DuckDB スキーマ初期化
   - Python REPL またはスクリプトから:
     ```
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     ```
   - ":memory:" を指定するとインメモリ DB が作成されます（テスト用途）。

---

## 使い方（主なユースケース）

- 日次 ETL（株価 / 財務 / カレンダー 取得 + 品質チェック）
  ```
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn)  # target_date を省略すると今日を使用
  print(result.to_dict())
  ```

- メーケットカレンダーの夜間更新ジョブ
  ```
  from kabusys.data.schema import init_schema
  from kabusys.data.calendar_management import calendar_update_job

  conn = init_schema("data/kabusys.duckdb")
  saved = calendar_update_job(conn)
  print("saved calendar rows:", saved)
  ```

- ニュース収集（RSS）
  ```
  from kabusys.data.schema import init_schema
  from kabusys.data.news_collector import run_news_collection

  conn = init_schema("data/kabusys.duckdb")
  # known_codes は銘柄抽出で使用する有効コードセット（例: {"7203","6758",...}）
  res = run_news_collection(conn, known_codes=set_of_codes)
  print(res)
  ```

- 研究用ファクター/特徴量作成
  ```
  from kabusys.data.schema import init_schema
  from kabusys.strategy import build_features
  from datetime import date

  conn = init_schema("data/kabusys.duckdb")
  n = build_features(conn, date(2025, 1, 15))
  print("features upserted:", n)
  ```

- シグナル生成
  ```
  from kabusys.data.schema import init_schema
  from kabusys.strategy import generate_signals
  from datetime import date

  conn = init_schema("data/kabusys.duckdb")
  total = generate_signals(conn, date.today())
  print("signals written:", total)
  ```

- 設定参照（コード内から）
  ```
  from kabusys.config import settings
  print(settings.jquants_refresh_token)
  print(settings.kabu_api_base_url)  # デフォルト: http://localhost:18080/kabusapi
  ```

注意点:
- 多くの関数は DuckDB 接続（DuckDBPyConnection）を直接受け取ります。スキーマ初期化後に同じ接続を渡すか、get_connection() で接続を取得してください。
- ETL や API 呼び出しはネットワークや外部 API の状態に依存するため、ログやエラーハンドリングに注意してください。

---

## ディレクトリ構成（抜粋）

プロジェクトの主要モジュールとファイルを抜粋して示します（src 配下）。

- src/kabusys/
  - __init__.py  (パッケージ定義, __version__ = "0.1.0")
  - config.py  (環境変数/.env 読み込みと Settings)
  - data/
    - __init__.py
    - jquants_client.py  (J-Quants API クライアント、取得/保存ユーティリティ)
    - news_collector.py  (RSS 収集・前処理・保存・銘柄抽出)
    - schema.py  (DuckDB スキーマ定義・init_schema)
    - stats.py  (zスコア正規化等の統計ユーティリティ)
    - pipeline.py  (ETL パイプライン、run_daily_etl 他)
    - features.py  (zscore_normalize の公開再エクスポート)
    - calendar_management.py (市場カレンダー周りのユーティリティ / ジョブ)
    - audit.py  (監査ログスキーマ)
    - execution/ (発注・約定関連層の空パッケージ)
  - research/
    - __init__.py  (research 公開関数)
    - factor_research.py (Momentum/Volatility/Value の計算)
    - feature_exploration.py (将来リターン / IC / summary)
  - strategy/
    - __init__.py  (build_features, generate_signals の公開)
    - feature_engineering.py (features テーブル生成)
    - signal_generator.py (シグナル生成ロジック)
  - monitoring/ (監視・監査系モジュールが入る想定)
  - execution/ (発注実行層、外部ブローカー連携など)

各モジュールはソース中に詳細な docstring と設計方針・処理フローが記載されています。実装の意図（ルックアヘッドバイアス回避、冪等性、トレース可能性、セキュリティ対策など）に留意して設計されています。

---

## 開発者向けメモ

- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml のある場所）を探索して行われます。テストや特殊環境で自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- DuckDB スキーマは init_schema() が idempotent（既に存在するテーブルはスキップ）なので何度でも安全に呼べます。
- ニュース収集は RSS の XML パースや外部 URL の扱いに対して SSRF/ZipBomb/XML Bomb 等の防御処理を組み込んでいます（defusedxml, サイズ制限, プライベートホストの排除 など）。
- J-Quants クライアントは内部でレート制御とリトライを実装しており、401 の場合にはリフレッシュトークンで ID トークンを更新して再試行します。

---

README に記載のない詳細はソースコード内の docstring（各モジュール先頭コメント）を参照してください。もし具体的な利用シナリオや追加の実行スクリプト（cron ジョブの例、Dockerfile、systemd ユニット等）が必要であれば、要件に応じてサンプルを作成します。