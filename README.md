# KabuSys

日本株向けの自動売買 / データプラットフォーム基盤ライブラリです。  
データ収集（J-Quants）、ETL、特徴量計算、シグナル生成、ニュース収集、監査トレーサビリティなどの主要機能を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下のレイヤーを備えた日本株向けの汎用基盤です。

- Data Platform：J-Quants からのデータ取得、DuckDB への永続化、品質チェック
- Feature Layer：研究で算出した生ファクターを正規化・合成して features を生成
- Strategy Layer：正規化済みファクターと AI スコアを統合して売買シグナルを生成
- Execution / Audit：シグナル→注文→約定の監査トレース用スキーマ（DuckDB）
- News Collector：RSS 収集・前処理・銘柄紐付け

設計方針として、ルックアヘッドバイアス回避、冪等性（DB 保存の ON CONFLICT 利用）、外部 API 呼び出しのレート制御／リトライ、テスト容易性を重視しています。

---

## 主な機能一覧

- J-Quants API クライアント（fetch/save／ページネーション、トークン自動リフレッシュ、レートリミット）
- DuckDB ベースのスキーマ定義と初期化（init_schema）
- 日次 ETL パイプライン（差分取得、バックフィル、品質チェック）
- モメンタム・ボラティリティ・バリュー等のファクター計算（research/factor_research）
- クロスセクション Z スコア正規化（data.stats）
- 特徴量構築（strategy.feature_engineering -> build_features）
- シグナル生成（strategy.signal_generator -> generate_signals）
- RSS ニュース収集と銘柄抽出（data.news_collector）
- マーケットカレンダー管理（data.calendar_management）
- 監査ログ用 DDL（order_requests / executions / signal_events 等）

---

## セットアップ手順

前提
- Python 3.9+（typing の一部表記から 3.9 以降を想定）
- 好ましくは仮想環境（venv / pyenv など）

1. リポジトリをクローン／配置（project root に .git / pyproject.toml があると自動で .env を読み込みます）

2. 依存ライブラリをインストール（必要な主要パッケージ）
   - duckdb
   - defusedxml

   例（pip）:
   ```
   python -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   pip install duckdb defusedxml
   # またはパッケージ配布がある場合:
   # pip install -e .
   ```

3. 環境変数（.env）を用意する  
   config.py によりプロジェクトルートの `.env` / `.env.local` が自動読み込みされます（既存の OS 環境変数は上書きされません）。自動ロードを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   必須環境変数（例）
   - JQUANTS_REFRESH_TOKEN=（J-Quants の refresh token）
   - KABU_API_PASSWORD=（kabu API パスワード）
   - SLACK_BOT_TOKEN=（Slack Bot トークン、監視通知用）
   - SLACK_CHANNEL_ID=（Slack チャンネル ID）
   - DUCKDB_PATH=data/kabusys.duckdb（省略可）
   - SQLITE_PATH=data/monitoring.db（省略可）
   - KABUSYS_ENV=development|paper_trading|live（デフォルト: development）
   - LOG_LEVEL=DEBUG|INFO|...（デフォルト: INFO）

   例: `.env`
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   KABU_API_PASSWORD=yyyy
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=DEBUG
   ```

4. DuckDB スキーマを初期化する  
   Python REPL またはスクリプトで次を実行します：
   ```python
   from kabusys.data.schema import init_schema
   init_schema("data/kabusys.duckdb")  # :memory: も可
   ```

---

## 使い方（代表的な操作例）

以下は典型的なワークフローの抜粋です。各モジュールはテストや他スクリプトから直接呼べるように設計されています。

- 日次 ETL 実行（J-Quants から市場カレンダー・株価・財務の差分取得 → 保存 → 品質チェック）
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.schema import get_connection, init_schema
  from kabusys.data.pipeline import run_daily_etl

  # DB 初期化済みであること（初回のみ）
  conn = init_schema("data/kabusys.duckdb")

  # 当日の ETL を実行
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- 特徴量（features）構築
  ```python
  from datetime import date
  from kabusys.data.schema import get_connection
  from kabusys.strategy import build_features

  conn = get_connection("data/kabusys.duckdb")
  n = build_features(conn, target_date=date(2025, 1, 31))
  print(f"features upserted: {n}")
  ```

- シグナル生成
  ```python
  from datetime import date
  from kabusys.data.schema import get_connection
  from kabusys.strategy import generate_signals

  conn = get_connection("data/kabusys.duckdb")
  count = generate_signals(conn, target_date=date(2025, 1, 31))
  print(f"signals written: {count}")
  ```

- ニュース収集ジョブ（RSS）
  ```python
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  # known_codes: 銘柄抽出に使う有効なコード集合（optional）
  res = run_news_collection(conn, sources=None, known_codes={"7203", "6758"})
  print(res)
  ```

- カレンダー更新バッチ
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  saved = calendar_update_job(conn)
  print(f"saved calendar rows: {saved}")
  ```

注意点
- 各処理は DuckDB 接続（duckdb.DuckDBPyConnection）を受け取ります。スクリプト実行時は同一接続を使うことでトランザクション整合性が確保されます。
- ETL 内部で API 呼び出し失敗などが発生しても段階ごとにハンドルして処理を継続する仕様です（結果オブジェクトにエラー詳細が格納されます）。

---

## 環境変数一覧（主なもの）

- JQUANTS_REFRESH_TOKEN — 必須。J-Quants リフレッシュトークン。
- KABU_API_PASSWORD — 必須。kabu ステーション API のパスワード。
- KABU_API_BASE_URL — 任意。kabu API のベース URL（既定: http://localhost:18080/kabusapi）。
- SLACK_BOT_TOKEN — 必須（監視通知を使う場合）。Slack Bot トークン。
- SLACK_CHANNEL_ID — 必須（監視通知を使う場合）。Slack チャンネル ID。
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）。
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）。
- KABUSYS_ENV — development / paper_trading / live（デフォルト: development）。
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）。  
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 にすると自動で .env を読み込まない（テスト用）。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                           -- 環境変数/設定管理
    - data/
      - __init__.py
      - jquants_client.py                 -- J-Quants API クライアント + save_* 関数
      - news_collector.py                 -- RSS 収集と保存ロジック
      - schema.py                         -- DuckDB スキーマ定義 + init_schema
      - stats.py                          -- zscore_normalize 等の統計ユーティリティ
      - pipeline.py                       -- ETL パイプライン（run_daily_etl 等）
      - calendar_management.py            -- market calendar ヘルパー・バッチ
      - audit.py                          -- 監査ログ用 DDL（signal_events / order_requests 等）
      - features.py                       -- data.stats の再エクスポート
    - research/
      - __init__.py
      - factor_research.py                -- モメンタム/ボラティリティ/バリュー計算
      - feature_exploration.py            -- forward returns / IC / summary 等
    - strategy/
      - __init__.py
      - feature_engineering.py            -- build_features
      - signal_generator.py               -- generate_signals
    - execution/                           -- 発注/ブローカー連携層（骨組み）
    - monitoring/                          -- 監視・アラート関連（骨組み）

---

## 開発・テストに関するヒント

- config.py はプロジェクトルート（.git または pyproject.toml）を探索して `.env` / `.env.local` を自動読み込みします。ユニットテストで環境依存を排除する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB は :memory: を使ったインメモリ接続で高速にテストできます（例: init_schema(":memory:")）。
- 外部ネットワークアクセス（J-Quants / RSS）を伴うユニットテストは、jquants_client._request や news_collector._urlopen などをモックすることを推奨します（コード内でテスト用の差し替えポイントが用意されています）。
- RSS パーサは defusedxml を使っており、XML 周りの攻撃対策が組み込まれています。

---

## ライセンス / 貢献

本リポジトリにライセンス情報がある場合はそれに従ってください。バグ報告や機能追加の提案は Issue/PR を通じてお願いいたします。

---

この README はコードベースの主要機能と使い方の最小限をまとめたものです。各モジュール（特に data/jquants_client.py、data/news_collector.py、research/*、strategy/*）には詳細な docstring と設計メモが含まれているため、実装の挙動は該当ファイルを参照してください。