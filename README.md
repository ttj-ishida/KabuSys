# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
データ収集（J-Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、マーケットカレンダー管理、監査ログ等を含んだモジュール化された実装を提供します。

バージョン: 0.1.0

## 概要
KabuSys は DuckDB をデータストアに用い、J-Quants API から市場データ・財務データ・カレンダーを取得して整備し、研究用ファクター計算・特徴量正規化・戦略シグナル生成までを行うことを目的としたパッケージです。  
設計上、発注 API（実際のブローカー接続）への直接依存を最小限にし、戦略ロジックやデータ処理をテストしやすく分離しています。

主な設計方針:
- ルックアヘッドバイアスを防ぐ（target_date 時点のみのデータ利用）
- 冪等性（DB 保存は ON CONFLICT / トランザクションで保証）
- 外部 API へはレート制御・リトライを備える
- DuckDB を中心としたシンプルなデータ層

## 機能一覧
- 環境変数/設定管理（kabusys.config）
- J-Quants API クライアント（取得・保存・ページネーション・トークン自動更新）
  - 日足（OHLCV）取得・保存
  - 財務データ取得・保存
  - マーケットカレンダー取得・保存
- DuckDB スキーマ定義と初期化（data.schema）
- ETL パイプライン（差分取得・バックフィル・品質チェック）（data.pipeline）
- マーケットカレンダー管理（is_trading_day / next_trading_day 等）
- ニュース収集（RSS 取得、記事正規化、銘柄抽出、DB 保存）
- 研究モジュール（factor 計算、将来リターン、IC 計算、統計サマリー）
- 特徴量構築（feature_engineering: ファクター合成・Z スコア正規化・ユニバースフィルタ）
- シグナル生成（signal_generator: コンポーネントスコア合成・BUY/SELL 判定・エグジット判定）
- 監査ログスキーマ（signal → order → execution のトレーサビリティ設計）
- 汎用統計ユーティリティ（zscore_normalize）

## 前提 / 必要条件
- Python 3.10 以上（型注釈に新版構文を使用）
- duckdb
- defusedxml
- （ネットワークアクセスが必要な API 呼び出しにはインターネット接続）

推奨インストールパッケージ（例）:
- duckdb
- defusedxml

例:
pip install duckdb defusedxml

※ 実際のプロジェクトでは requirements.txt や pyproject.toml を用意して依存を固定してください。

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境を作成・有効化（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール
   ```
   pip install duckdb defusedxml
   ```

4. 環境変数（.env）を作成  
   ルートに `.env`（または `.env.local`）を置くと自動で読み込まれます（kabusys.config がプロジェクトルートを検出する場合）。自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   必要な主な環境変数（例）:
   - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   - KABU_API_PASSWORD=your_kabu_api_password
   - SLACK_BOT_TOKEN=your_slack_bot_token
   - SLACK_CHANNEL_ID=your_slack_channel_id
   - DUCKDB_PATH=data/kabusys.duckdb      # 任意（デフォルト）
   - SQLITE_PATH=data/monitoring.db       # 任意（監視用）
   - KABUSYS_ENV=development|paper_trading|live
   - LOG_LEVEL=INFO|DEBUG|...

   例 .env:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=pass
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=DEBUG
   ```

5. データベース初期化（DuckDB スキーマ作成）
   Python REPL またはスクリプトで:
   ```python
   from kabusys.data.schema import init_schema
   from kabusys.config import settings

   conn = init_schema(settings.duckdb_path)
   # conn は duckdb の接続オブジェクト
   ```

## 使い方（代表的な操作）

- 日次 ETL を実行（J-Quants からデータ取得して DB 保存・品質チェック）
  ```python
  from datetime import date
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings

  conn = init_schema(settings.duckdb_path)
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- 特徴量構築（features テーブルへ保存）
  ```python
  from datetime import date
  from kabusys.data.schema import get_connection
  from kabusys.strategy import build_features
  from kabusys.config import settings

  conn = get_connection(settings.duckdb_path)
  count = build_features(conn, target_date=date.today())
  print(f"features upserted: {count}")
  ```

- シグナル生成（signals テーブルへ保存）
  ```python
  from datetime import date
  from kabusys.data.schema import get_connection
  from kabusys.strategy import generate_signals
  from kabusys.config import settings

  conn = get_connection(settings.duckdb_path)
  total = generate_signals(conn, target_date=date.today())
  print(f"signals generated: {total}")
  ```

- ニュース収集ジョブ（RSS から raw_news と news_symbols を作成）
  ```python
  from kabusys.data.schema import get_connection
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  from kabusys.config import settings

  conn = get_connection(settings.duckdb_path)
  # known_codes: 銘柄コードの集合（例: all codes in prices_daily）
  known_codes = {"7203", "6758", "9432"}  # 実運用では DB から取得
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
  print(results)
  ```

- カレンダー夜間更新ジョブ
  ```python
  from kabusys.data.schema import get_connection
  from kabusys.data.calendar_management import calendar_update_job
  from kabusys.config import settings

  conn = get_connection(settings.duckdb_path)
  saved = calendar_update_job(conn)
  print(f"market calendar saved: {saved}")
  ```

- J-Quants からの手動データ取得（例）
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
  token = get_id_token()
  rows = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))
  ```

注意:
- すべての ETL / 生成処理は target_date 時点の情報のみを使用する設計です（ルックアヘッド防止）。
- DB 操作は DuckDB の接続を直接受け取り、トランザクションで日付単位の置換（DELETE → INSERT）を行います。

## 主要モジュール / ディレクトリ構成
（src/kabusys 以下の主要ファイルを抜粋）

- kabusys/
  - __init__.py
  - config.py  — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py        — J-Quants API クライアント（fetch / save）
    - schema.py                — DuckDB スキーマ定義 & init_schema / get_connection
    - pipeline.py              — 日次 ETL（run_daily_etl 等）
    - news_collector.py        — RSS 収集・記事整形・DB 保存
    - calendar_management.py   — カレンダー判定 / 更新ジョブ
    - features.py              — データ統計ユーティリティ再エクスポート
    - stats.py                 — zscore_normalize 等の統計関数
    - audit.py                 — 監査ログスキーマ
    - (その他: quality, monitoring などを想定)
  - research/
    - __init__.py
    - factor_research.py       — mom/volatility/value 等のファクター計算
    - feature_exploration.py   — forward returns / IC / summary
  - strategy/
    - __init__.py
    - feature_engineering.py   — ファクター合成・正規化 -> features テーブル
    - signal_generator.py      — final_score 計算 -> signals テーブル
  - execution/                 — 発注・注文管理に関する実装（空/拡張用）
  - monitoring/                — 監視・アラート用ロジック（空/拡張用）

（上記は主要ファイルの抜粋です。詳細はソースコードを参照してください）

## 環境変数一覧（主要）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabuAPI のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用トークン（必須）
- SLACK_CHANNEL_ID: 通知先チャンネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 環境（development, paper_trading, live）
- LOG_LEVEL: ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）

## テスト・開発メモ
- config モジュールはプロジェクトルート（.git または pyproject.toml）を探して `.env` / `.env.local` を自動で読み込みます。テスト時は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して自動ロードを無効にできます。
- DuckDB を ":memory:" に指定すればインメモリ DB で高速にテスト可能です。
- 外部接続（J-Quants、RSS）をモックすることで単体テストを容易に実装できます（関数が id_token を引数で受け取る等、DI に配慮した設計）。

## 今後の拡張案（参考）
- execution 層と実証済みのブローカー接続の実装
- 品質チェックモジュール（quality）の追加・強化
- CI 用のテストスイート・Lint/フォーマット設定
- Docker イメージ化／デプロイ向けの設定

---

不明点や README に追記したい内容（例: 実行例、CI 設定、テーブル定義の詳細など）があれば教えてください。必要に応じてサンプルスクリプトや運用手順を追加します。