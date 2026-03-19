# KabuSys

日本株自動売買システム用ライブラリ（KabuSys）。  
データ取得（J-Quants / RSS）、ETL、特徴量生成、戦略シグナル生成、DuckDB スキーマ定義、監査ログ等を含むモジュール群を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買基盤のための共通ライブラリ群です。主な役割は以下の通りです。

- J-Quants API からの株価・財務・カレンダー取得（レート制御・リトライ・トークン自動更新）
- RSS フィードからのニュース収集と銘柄抽出（SSRF対策・サイズ制限・トラッキングパラメータ除去）
- DuckDB スキーマの定義・初期化（Raw / Processed / Feature / Execution 層）
- ETL パイプライン（差分取得・バックフィル・品質チェック呼び出し）
- 研究用ファクター計算（モメンタム・ボラティリティ・バリュー）
- 特徴量エンジニアリング（Zスコア正規化・ユニバースフィルタ）
- シグナル生成（特徴量＋AIスコアの統合、BUY/SELL 判定、エグジットロジック）
- 監査ログ（シグナル→発注→約定のトレース用テーブル）
- 設定管理（.env 自動読み込み、環境変数アクセスラッパー）

設計方針として「ルックアヘッドバイアス防止」「冪等性」「API レート制御」「ロギング・監査」を重視しています。

---

## 主な機能一覧

- 環境設定管理（kabusys.config）
  - .env / .env.local の自動読み込み（プロジェクトルート検出）
  - 必須環境変数チェック（例: JQUANTS_REFRESH_TOKEN）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化

- データ取得・保存（kabusys.data.jquants_client）
  - J-Quants から日足 / 財務 / カレンダー取得（ページネーション対応）
  - レート制御・リトライ・401 自動リフレッシュ
  - DuckDB への冪等保存（ON CONFLICT による更新）

- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得、XML パース防御（defusedxml）
  - URL 正規化（トラッキング除去）、記事 ID は SHA-256 の先頭 32 文字
  - 銘柄コード抽出と news_symbols 登録
  - SSRF 対策（スキーム検証・プライベートアドレスブロック・リダイレクト検査）
  - レスポンスサイズ上限

- DuckDB スキーマ管理（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層テーブル定義
  - インデックス作成、init_schema() による初期化

- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新、バックフィル、calendar の先読み
  - run_daily_etl() による一括 ETL（品質チェック呼び出し含む）

- 研究・特徴量（kabusys.research, kabusys.strategy）
  - ファクター計算（momentum / volatility / value）
  - Z スコア正規化ユーティリティ
  - features テーブルのビルド（build_features）
  - シグナル生成（generate_signals、BUY/SELL 判定、Bear レジーム抑制）

- 監査・実行（kabusys.data.audit）
  - signal_events, order_requests, executions 等の監査テーブル（UUID トレース）

---

## セットアップ手順

※ 以下は基本的なセットアップ例です。プロジェクトで pip packaging が整備されている場合は `pip install -e .` 等をお使いください。

前提
- Python 3.9+（コードは型注釈に Python 3.10 以上の書式を使っている箇所があるため、3.10 推奨）
- DuckDB を利用可能な環境

1. 仮想環境の作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージのインストール
   - pip install duckdb defusedxml

   （プロジェクトに packaging がある場合）
   - pip install -e .

3. 環境変数設定
   - プロジェクトルートに .env ファイルを作成するか、OS 環境変数を設定してください。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - 任意/デフォルト値:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト "development"
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動読み込みを無効化できます
     - KABUSYS API ベース URL: KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）
     - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト data/monitoring.db）
     - LOG_LEVEL（DEBUG/INFO/...、デフォルト INFO）

4. DuckDB スキーマ初期化
   - Python REPL などで以下を実行:
     from kabusys.data.schema import init_schema, get_connection
     conn = init_schema("data/kabusys.duckdb")
     conn.close()

---

## 使い方（主要なユースケース例）

以下は簡単な利用例です。実際の運用ではログ設定や例外ハンドリングを追加してください。

- DuckDB 初期化と接続
  ```python
  from kabusys.data.schema import init_schema, get_connection
  conn = init_schema("data/kabusys.duckdb")  # ファイルがなければ作成してテーブルを初期化
  # 既存 DB に接続するだけなら:
  # conn = get_connection("data/kabusys.duckdb")
  ```

- 日次 ETL を実行（J-Quants トークンは settings 経由で自動取得）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.data.schema import init_schema
  from datetime import date

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- 特徴量ビルド（features テーブルの作成）
  ```python
  from kabusys.strategy import build_features
  from kabusys.data.schema import get_connection, init_schema
  from datetime import date

  conn = init_schema("data/kabusys.duckdb")
  n = build_features(conn, target_date=date(2025, 1, 15))
  print(f"features upserted: {n}")
  ```

- シグナル生成
  ```python
  from kabusys.strategy import generate_signals
  from kabusys.data.schema import init_schema
  from datetime import date

  conn = init_schema("data/kabusys.duckdb")
  total_signals = generate_signals(conn, target_date=date(2025, 1, 15))
  print(f"signals written: {total_signals}")
  ```

- ニュース収集ジョブ（RSS -> raw_news 保存、銘柄紐付け）
  ```python
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  from kabusys.data.schema import init_schema, get_connection

  conn = init_schema("data/kabusys.duckdb")
  # known_codes は有効な銘柄コードセット（例: prices_daily から取得）
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203","6758"})
  print(results)
  ```

- カレンダー更新ジョブ（夜間バッチ）
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  saved = calendar_update_job(conn)
  print(f"calendar saved: {saved}")
  ```

- 設定値の参照
  ```python
  from kabusys.config import settings
  print(settings.jquants_refresh_token)  # 未設定なら ValueError
  print(settings.duckdb_path)            # Path オブジェクト
  ```

---

## 環境変数一覧（主なもの）

- 必須
  - JQUANTS_REFRESH_TOKEN - J-Quants のリフレッシュトークン
  - KABU_API_PASSWORD - kabu ステーション API パスワード
  - SLACK_BOT_TOKEN - Slack Bot トークン
  - SLACK_CHANNEL_ID - Slack 通知先チャンネル ID

- 任意 / デフォルトあり
  - KABU_API_BASE_URL - kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
  - DUCKDB_PATH - DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH - SQLite 監視 DB（デフォルト data/monitoring.db）
  - KABUSYS_ENV - environment（development/paper_trading/live、デフォルト development）
  - LOG_LEVEL - ログレベル（DEBUG/INFO/...、デフォルト INFO）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD - 1 を設定すると .env 自動読み込みを無効化

注意: settings の必須プロパティを参照するときは、該当環境変数が設定されている必要があります。未設定時は ValueError が投げられます。

---

## ディレクトリ構成

主要ファイルとディレクトリ（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py
    - news_collector.py
    - schema.py
    - pipeline.py
    - stats.py
    - calendar_management.py
    - features.py
    - audit.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - strategy/
    - __init__.py
    - feature_engineering.py
    - signal_generator.py
  - execution/
    - __init__.py
  - monitoring/  (プレースホルダ)

簡単なツリー表示（例）
```
src/kabusys/
├─ __init__.py
├─ config.py
├─ data/
│  ├─ jquants_client.py
│  ├─ news_collector.py
│  ├─ schema.py
│  ├─ pipeline.py
│  └─ ...
├─ research/
│  ├─ factor_research.py
│  └─ feature_exploration.py
├─ strategy/
│  ├─ feature_engineering.py
│  └─ signal_generator.py
├─ execution/
└─ monitoring/
```

---

## 開発・運用上の注意点

- DuckDB のバージョン差による機能差（例えば一部の FOREIGN KEY 挙動や ON DELETE 制約）に注意してください。schema モジュール内のコメントに互換性に関する注記があります。
- ニュース取得では XML パースとネットワーク上の攻撃（XML Bomb / SSRF）対策を行っていますが、外部フィードの変則フォーマットには注意してください。
- J-Quants API はレート制限（120 req/min）があるため、jquants_client の RateLimiter とリトライロジックに従ってください。
- settings は起動時に .env / .env.local を自動読み込みします。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動読み込みを無効化できます。
- シグナル生成は features と ai_scores に依存します。AI スコアが未提供の場合は中立値で補完されますが、実運用時は ai_scores の投入フローを整備してください。

---

## 貢献・拡張

- execution 層やブローカー接続（kabu API での注文送信）モジュールは拡張点です。監査テーブル（audit）を活用して発注の冪等性・トレーサビリティを確保してください。
- 研究用モジュール（research/*）は外部解析や backtest 用に再利用できます。ここから得られた因子を strategy 層に取り込むフローを推奨します。

---

この README はコードベースの主要機能・使い方をまとめたものです。詳細は各モジュールのドキュメント文字列（docstring）を参照してください。必要であれば、サンプル workflow（cron / Airflow）や運用手順（バックアップ、DB パスの切替、ログ集約等）を追記します。