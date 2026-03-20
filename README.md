# KabuSys

日本株向け自動売買プラットフォームのコアライブラリ（モジュール群）。  
データ取得（J-Quants）、ETL、特徴量計算、シグナル生成、ニュース収集、監査ログ用スキーマなどを含む取得・前処理・戦略レイヤーの実装がまとめられています。

主な設計方針
- ルックアヘッドバイアス回避（target_date 時点の情報のみで計算）
- 冪等性（DB への保存は ON CONFLICT / トランザクションで安全に）
- テスト容易性（id_token 注入や :memory: DB 対応など）
- 外部依存を最小化（多くの統計処理は標準ライブラリで実装）

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（簡易サンプル）
- 環境変数一覧 / .env 例
- ディレクトリ構成

---

プロジェクト概要
- J-Quants API から日本株データ（日足・財務・市場カレンダー）を収集し、DuckDB に保存する ETL パイプライン。
- 保存済みデータからファクター（Momentum / Volatility / Value 等）を計算し、特徴量（features）テーブルへ保存。
- 特徴量と AI スコア等を統合して売買シグナルを生成（signals テーブルへ保存）。
- RSS フィードからニュース収集して raw_news / news_symbols に保存。
- 発注・約定・ポジション・監査ログのためのスキーマ定義を含む。

機能一覧
- データ取得
  - J-Quants API クライアント（レート制限・リトライ・トークン自動リフレッシュ対応）
  - 株価（日足）、四半期財務、マーケットカレンダーの取得と DuckDB への保存（冪等）
- ETL パイプライン
  - 差分取得ロジック（最終取得日からの差分 + バックフィル）
  - 日次 ETL 実行（calendar → prices → financials → 品質チェック）
- データスキーマ
  - DuckDB 用のスキーマ初期化（Raw / Processed / Feature / Execution 層）
- 研究・特徴量
  - calc_momentum, calc_volatility, calc_value（research/factor_research）
  - クロスセクション Z スコア正規化ユーティリティ
  - 特徴量構築（strategy.feature_engineering.build_features）
- シグナル生成
  - 正規化済み特徴量 + ai_scores 統合 → final_score 計算
  - BUY / SELL シグナル生成（エグジット判定含む）
- ニュース収集
  - RSS 取得（SSRF 対策、gzip 制限、XML 安全パーサ）
  - raw_news / news_symbols への保存（冪等）
- 監査ログ
  - signal_events / order_requests / executions などの監査テーブル DDL
- ユーティリティ
  - マーケットカレンダー管理（営業日判定、次/前営業日取得）
  - 統計ユーティリティ（zscore_normalize, IC 計算など）

---

セットアップ手順（開発環境想定）
前提
- Python 3.10 以上（型注釈で `|` を使用）
- DuckDB を利用するためネイティブ拡張が必要（pip install duckdb）

1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境を作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate (Linux / macOS)
   - .venv\Scripts\activate (Windows)

3. 必要パッケージをインストール
   - pip install duckdb defusedxml
   - その他、プロジェクトに合わせた依存があれば追加してください。
   - 開発中は pip install -e .（セットアップ済みの setup/pyproject がある場合）

4. 環境変数を設定
   - プロジェクトルートに .env / .env.local を置くと自動で読み込まれます（初期ロードは .git または pyproject.toml を起点に行われます）。
   - 自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

5. DuckDB スキーマ初期化（例）
   - Python REPL やスクリプトで以下を実行して DB を初期化します（:memory: でインメモリ DB も可）:
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")

---

使い方（簡易サンプル）

1) 最低限の初期化（DB 作成）
- 例: インメモリで試す
  from kabusys.data.schema import init_schema
  conn = init_schema(":memory:")

- 例: ファイル DB を使用
  from kabusys.config import settings
  from kabusys.data.schema import init_schema
  conn = init_schema(settings.duckdb_path)

2) 日次 ETL を実行（J-Quants トークンが設定済みの場合）
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn)  # default: target_date = today
  print(result.to_dict())

3) 特徴量を構築（ETL 後の対象営業日で実行）
  from datetime import date
  from kabusys.strategy import build_features
  # target_date は ETL で取得・整備済みの営業日を指定
  num = build_features(conn, date(2024, 1, 4))
  print(f"features upserted: {num}")

4) シグナルを生成
  from kabusys.strategy import generate_signals
  num_signals = generate_signals(conn, date(2024, 1, 4))
  print(f"signals written: {num_signals}")

5) RSS ニュース収集ジョブ
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import get_connection
  # known_codes は銘柄コードの集合（抽出時のフィルタ）
  result = run_news_collection(conn, sources=None, known_codes={"7203","6758"})
  print(result)

6) マーケットカレンダーの夜間更新ジョブ
  from kabusys.data.calendar_management import calendar_update_job
  saved = calendar_update_job(conn)
  print("saved calendar rows:", saved)

注意点
- settings は環境変数から値を読み込みます。必須の環境変数が未設定だと ValueError が発生します。
- 対外 API 呼び出しを行う関数（fetch_*）はネットワーク例外や API エラーを投げる可能性があります。呼び出し側で例外処理を行ってください。
- スキーマ初期化（init_schema）は冪等です。既存テーブルがあれば上書きせずにスキップします。

---

環境変数一覧（主要）
- JQUANTS_REFRESH_TOKEN (必須)
  - J-Quants のリフレッシュトークン。settings.jquants_refresh_token から参照されます。
- KABU_API_PASSWORD (必須)
  - kabuステーション API のパスワード。
- KABU_API_BASE_URL (任意、デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須)
  - Slack 通知用 Bot トークン。
- SLACK_CHANNEL_ID (必須)
  - 通知先チャンネル ID。
- DUCKDB_PATH (任意、デフォルト: data/kabusys.duckdb)
  - DuckDB ファイルパス（settings.duckdb_path）
- SQLITE_PATH (任意、デフォルト: data/monitoring.db)
- KABUSYS_ENV (任意: development | paper_trading | live)（デフォルト: development）
- LOG_LEVEL (任意: DEBUG | INFO | WARNING | ERROR | CRITICAL)（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると、自動で .env を読み込む処理を無効化できます（テスト時に便利）。

サンプル .env
# J-Quants
JQUANTS_REFRESH_TOKEN=your_refresh_token_here

# kabuステーション
KABU_API_PASSWORD=your_kabu_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# Slack
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567

# DB
DUCKDB_PATH=data/kabusys.duckdb

# 環境
KABUSYS_ENV=development
LOG_LEVEL=INFO

---

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                -- 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py      -- J-Quants API クライアント + 保存ユーティリティ
    - news_collector.py      -- RSS 収集・保存
    - schema.py              -- DuckDB スキーマ定義 & init_schema
    - stats.py               -- 統計ユーティリティ（zscore 等）
    - pipeline.py            -- ETL パイプライン（run_daily_etl 等）
    - calendar_management.py -- カレンダー管理ユーティリティ
    - features.py            -- zscore_normalize 再エクスポート
    - audit.py               -- 監査ログ用 DDL
    - quality.py?            -- （品質チェック用モジュール参照あり）
  - research/
    - __init__.py
    - factor_research.py     -- momentum/value/volatility 計算
    - feature_exploration.py -- IC / forward returns / summary
  - strategy/
    - __init__.py
    - feature_engineering.py -- features テーブル作成処理
    - signal_generator.py    -- final_score 計算と signals 生成
  - execution/
    - __init__.py            -- 発注層（未実装部分の置き場）
  - monitoring/              -- 監視・モニタリング周り（エクスポート対象）
  - その他（ユーティリティ等）

（上記はコードベースに基づく主要ファイルの一覧です。細かいファイルは実際のリポジトリ構成を参照してください。）

---

運用上の注意
- J-Quants のレート制限（120 req/min）に合わせたスロットリングと再試行ロジックを実装していますが、ジョブのスケジューリングは運用側で調整してください。
- DuckDB のファイルロックやバックアップ、ディスク容量には注意してください。
- production（live）環境では KABUSYS_ENV を "live" に設定し、paper_trading / development とログ・動作を分離してください。
- 発注 / execution 層は実取引リスクを伴います。実際に発注を行う前に十分なテスト・レビューを行ってください。

---

貢献・拡張
- 新たなファクターの追加は research/factor_research.py に関数を追加し、strategy.feature_engineering.build_features のフローへ組み込んでください。
- 発注ブリッジ（ブローカー固有の API 実装）は execution パッケージ内に実装し、signal → order_queue → orders → executions のフローへ接続してください。
- 品質チェックやモニタリングは data/quality.py や monitoring パッケージを拡張して追加してください。

---

問い合わせ・ライセンス
- 本ドキュメントはコード読み取りに基づく概要のため、実運用時はソースの詳細コメントを参照し実装意図を確認してください。
- ライセンス情報や運用上の契約はリポジトリルートの LICENSE / CONTRIBUTING を参照してください（本リポジトリに含まれる場合）。

以上。