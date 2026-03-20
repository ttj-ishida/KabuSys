# KabuSys

KabuSys は日本株向けの自動売買プラットフォームのコードベースです。データ取得（J-Quants）、ETL、特徴量生成、シグナル算出、ニュース収集、監査・実行レイヤーまでを備えたモジュール群を提供します。研究（research）用のファクター計算や、DuckDB を使ったローカルデータベース運用を想定しています。

## 主な特徴
- J-Quants API クライアント（レート制限、リトライ、トークン自動更新）
- DuckDB スキーマ定義と初期化（Raw / Processed / Feature / Execution 層）
- 日次 ETL（差分取得・バックフィル・品質チェック）
- ファクター計算（Momentum / Volatility / Value 等）
- 特徴量エンジニアリング（Z スコア正規化・ユニバースフィルタ）
- シグナル生成（複数コンポーネントの重み付け統合、BUY/SELL 判定）
- ニュース収集（RSS 取得、前処理、銘柄抽出、DB 保存）
- マーケットカレンダー管理（JPX カレンダー、営業日判定）
- 監査ログ / 発注トレーサビリティ（order_requests / executions テーブル等）
- 環境変数ベースの設定管理（.env の自動ロードと保護）

## 前提条件
- Python 3.9+
- duckdb
- defusedxml
- ネットワークアクセス（J-Quants API / RSS フィード）
- J-Quants のリフレッシュトークン（本番/テストで必要）

（実際の package の依存は pyproject.toml / requirements.txt を参照してください）

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローンして venv を作る
   ```bash
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate
   ```

2. 必要パッケージをインストール（例）
   ```bash
   pip install -e ".[dev]"   # 開発用エキストラがある場合
   # あるいは最低限:
   pip install duckdb defusedxml
   ```

3. 環境変数を設定
   - プロジェクトルートに `.env`（および必要なら `.env.local`）を作成すると自動で読み込まれます。
   - 自動ロードを無効にしたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   主要な環境変数（必須）
   - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD — kabu ステーション API パスワード（必須）
   - SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（必須）
   - SLACK_CHANNEL_ID — 通知先チャンネル ID（必須）

   オプション（デフォルト値あり）
   - KABUSYS_ENV — 環境。`development` / `paper_trading` / `live`（デフォルト `development`）
   - LOG_LEVEL — ログレベル。`DEBUG, INFO, WARNING, ERROR, CRITICAL`（デフォルト `INFO`）
   - DUCKDB_PATH — DuckDB ファイルパス（デフォルト `data/kabusys.duckdb`）
   - SQLITE_PATH — 監視用 SQLite パス（デフォルト `data/monitoring.db`）

4. データベース初期化（例）
   以下は Python REPL やスクリプトで実行します。
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   ```

## 使い方（主要なユースケース）

- 日次 ETL を実行してデータを更新する（market calendar / prices / financials）
  ```python
  from datetime import date
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- 特徴量のビルド（features テーブルへ書き込む）
  ```python
  from datetime import date
  import duckdb
  from kabusys.strategy import build_features

  conn = duckdb.connect("data/kabusys.duckdb")
  n = build_features(conn, target_date=date(2025, 1, 31))
  print(f"built features for {n} symbols")
  ```

- シグナル生成（features + ai_scores を使って signals テーブルへ）
  ```python
  from datetime import date
  import duckdb
  from kabusys.strategy import generate_signals

  conn = duckdb.connect("data/kabusys.duckdb")
  total = generate_signals(conn, target_date=date(2025, 1, 31))
  print(f"written {total} signals")
  ```

- ニュース収集ジョブ（RSS から raw_news を保存し、既知銘柄へ紐付け）
  ```python
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  import duckdb

  conn = duckdb.connect("data/kabusys.duckdb")
  known_codes = {"7203", "6758", "9984"}  # 例
  stats = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
  print(stats)
  ```

- カレンダー更新ジョブ（夜間バッチ）
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  import duckdb

  conn = duckdb.connect("data/kabusys.duckdb")
  saved = calendar_update_job(conn, lookahead_days=90)
  print(f"saved {saved} calendar rows")
  ```

- 設定の参照
  ```python
  from kabusys.config import settings
  print(settings.jquants_refresh_token)
  print(settings.env, settings.is_live)
  ```

注意:
- 多くの処理は DuckDB 接続を受け取る関数です。トランザクションは内部で適切に扱われますが、必要に応じて外側でトランザクションを管理できます。
- generate_signals / build_features は基本的に「日付単位で DELETE してから INSERT」するため冪等です。

## 環境変数と自動 .env 読み込み
- パッケージはプロジェクトルート（.git または pyproject.toml を検索）にある `.env` と `.env.local` を自動で読み込みます（OS 環境変数の上書きルールに従う）。
- 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
- 必須変数が未定義のまま呼び出すと `ValueError` が発生します（Settings クラス）。

## ディレクトリ構成（主要ファイル）
以下は主要なパッケージ・モジュールの概要です（src/kabusys 配下）。

- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント + 保存ユーティリティ
    - news_collector.py — RSS 取得・前処理・保存
    - schema.py — DuckDB スキーマ定義と init_schema()
    - stats.py — z-score 正規化など統計ユーティリティ
    - pipeline.py — ETL パイプライン（run_daily_etl など）
    - calendar_management.py — 市場カレンダー管理
    - features.py — data.stats の再エクスポート
    - audit.py — 監査ログ用スキーマ
    - (その他: quality 等想定)
  - research/
    - __init__.py
    - factor_research.py — momentum/volatility/value 等の計算
    - feature_exploration.py — forward returns / IC / factor summary
  - strategy/
    - __init__.py
    - feature_engineering.py — 生ファクターから features 生成
    - signal_generator.py — final_score 計算と signals 書き込み
  - execution/ — 発注・実行に関するモジュール（空ファイルや実装想定）
  - monitoring/ — 監視・メトリクス関連（存在想定）

（実際のリポジトリでは上記に加えて tests/, docs/, scripts/ 等が存在する場合があります）

## 開発・貢献
- バグ修正・機能追加は PR を送ってください。CI・テストはリポジトリの設定に従ってください。
- 重要な設計文書（StrategyModel.md, DataPlatform.md 等）が参照されています。変更時はこれらの整合性も保ってください。

## 注意事項
- 本プロジェクトは金融データ処理および発注を扱います。実際の運用で使用する場合は十分な検証（特に発注ロジック・監査・リスク管理）を行ってください。
- Live 環境での動作には証券会社 API（kabu ステーション等）や Slack トークンなどの本番資格情報が必要です。テスト時は `KABUSYS_ENV=paper_trading` を使用してください。

---

必要であれば README にサンプル .env.example、追加の CLI / systemd ジョブ定義、よくあるトラブルシューティング（トークン更新方法、DuckDB ファイル場所の変更方法など）を追記できます。どの情報を優先して追記しましょうか？