# KabuSys

日本株向け自動売買システムのライブラリ群です。データ取得（J‑Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、監査/実行レイヤ向けのスキーマなどを含みます。

> 本リポジトリはライブラリ／バッチ処理群を提供します。実際の運用ではこのライブラリを用いてジョブ（ETL／特徴量生成／シグナル生成／カレンダー更新／ニュース収集 等）を組み合わせて実行します。

## 主要機能
- J‑Quants API クライアント（ページネーション、レート制限、リトライ、トークン自動更新）
- DuckDB ベースのデータスキーマ定義と初期化（冪等）
- 日次 ETL パイプライン（市場カレンダー / 株価 / 財務データの差分取得・保存）
- ニュース収集（RSS -> raw_news、SSRF/サイズ/トラッキングパラメータ対策）
- 研究用ファクター計算（モメンタム / ボラティリティ / バリュー 等）
- 特徴量エンジニアリング（Z スコア正規化、ユニバースフィルタ）
- シグナル生成（複数コンポーネントを統合して BUY/SELL を作成、Bear レジーム抑制、エグジット判定）
- 監査ログ（signal/events / order_requests / executions 等）設計を含むスキーマ
- 汎用統計ユーティリティ（Z スコア正規化、IC 計算、要約統計）

## 必要な環境変数
主に以下を使用します（READMEでは必須と想定する主要なものを列記）。

- JQUANTS_REFRESH_TOKEN — J‑Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API のパスワード（必須）
- SLACK_BOT_TOKEN — Slack 通知に使う Bot トークン（必須）
- SLACK_CHANNEL_ID — Slack 通知チャンネル ID（必須）
- DUCKDB_PATH — DuckDB ファイルパス（省略時: `data/kabusys.duckdb`）
- SQLITE_PATH — 監視用 SQLite パス（省略時: `data/monitoring.db`）
- KABUSYS_ENV — 実行環境（`development` / `paper_trading` / `live`。デフォルト `development`）
- LOG_LEVEL — ログレベル（`DEBUG` / `INFO` / `WARNING` / `ERROR` / `CRITICAL`）

自動的にプロジェクトルートの `.env` / `.env.local` を読み込みます（優先順位: OS 環境 > .env.local > .env）。自動読込を無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

## セットアップ

1. リポジトリをクローンし、Python 仮想環境を作成します。
   ```bash
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate
   ```

2. 依存パッケージをインストールします（例）。
   - 最低限必要なパッケージ: duckdb, defusedxml
   ```bash
   pip install duckdb defusedxml
   # 開発インストール（setup.py/pyproject がある場合）
   pip install -e .
   ```

3. 環境変数を設定（`.env` を作成）。
   - プロジェクトルートに `.env` を置くと自動読み込みされます。
   - 例（.env）:
     ```
     JQUANTS_REFRESH_TOKEN=xxxx
     KABU_API_PASSWORD=yyyy
     SLACK_BOT_TOKEN=zzzz
     SLACK_CHANNEL_ID=C0123456
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

4. DuckDB スキーマを初期化します（親ディレクトリが自動作成されます）。
   ```bash
   python -c "from kabusys.data.schema import init_schema; init_schema('data/kabusys.duckdb')"
   ```

## 使い方（主要な実行例）

以下はライブラリ API を直接呼ぶ簡単な例です。実運用では cron／Airflow 等から呼ぶことを想定します。

- 日次 ETL 実行（市場カレンダー・株価・財務の差分取得と品質チェック）
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.schema import get_connection
  from kabusys.data.pipeline import run_daily_etl

  conn = get_connection('data/kabusys.duckdb')
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- 特徴量（features）を構築
  ```python
  from datetime import date
  from kabusys.strategy import build_features
  from kabusys.data.schema import get_connection

  conn = get_connection('data/kabusys.duckdb')
  n = build_features(conn, target_date=date.today())
  print(f"features upserted: {n}")
  ```

- シグナルを生成して signals テーブルへ書き込む
  ```python
  from datetime import date
  from kabusys.strategy import generate_signals
  from kabusys.data.schema import get_connection

  conn = get_connection('data/kabusys.duckdb')
  total = generate_signals(conn, target_date=date.today(), threshold=0.60)
  print(f"signals written: {total}")
  ```

- ニュース収集（RSS）を実行し DB に格納
  ```python
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  from kabusys.data.schema import get_connection

  conn = get_connection('data/kabusys.duckdb')
  known_codes = {'7203', '6758', '9984'}  # 既知の銘柄コードセット
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
  print(results)
  ```

- カレンダー更新バッチ
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  from kabusys.data.schema import get_connection

  conn = get_connection('data/kabusys.duckdb')
  saved = calendar_update_job(conn)
  print(f"market_calendar saved: {saved}")
  ```

## 設計上の注意点 / 実装の特徴
- 環境/設定は `kabusys.config.Settings` から取得できます（例: `from kabusys.config import settings; settings.jquants_refresh_token`）。
- J‑Quants クライアントはレート制限（120 req/min）に従った内部 RateLimiter、リトライ（指数バックオフ）、401 時のトークン自動リフレッシュを提供します。
- DuckDB への保存は可能な限り冪等に（ON CONFLICT / DO UPDATE / DO NOTHING）実装されています。
- ニュース収集は SSRF 対策、gzip/サイズ制限、XML 攻撃対策（defusedxml）など安全性に配慮しています。
- 特徴量・シグナル生成はルックアヘッドバイアス防止のため target_date 時点のデータのみを参照する設計です。
- 設定値検証（KABUSYS_ENV, LOG_LEVEL 等）があり、不正値は例外を投げます。

## 有用なモジュール一覧（主なもの）
- kabusys.config — 環境変数のロード・管理（.env 自動読み込み）
- kabusys.data
  - jquants_client.py — J‑Quants API クライアント（fetch / save 関数）
  - schema.py — DuckDB スキーマ定義と初期化
  - pipeline.py — ETL パイプライン（run_daily_etl 等）
  - news_collector.py — RSS 取得／保存／銘柄抽出
  - calendar_management.py — 市場カレンダー操作・バッチ
  - stats.py / features.py — 統計ユーティリティ（zscore 等）
- kabusys.research — 研究用の factor 計算や探索ユーティリティ
- kabusys.strategy — build_features / generate_signals（特徴量作成とシグナル生成）
- kabusys.execution — 発注/実行層（現状空のパッケージプレースホルダ）
- kabusys.monitoring — 監視用モジュール（パッケージに含まれる想定）

## ディレクトリ構成（抜粋）
以下は主要ファイルを含むディレクトリ構成の抜粋です。

```
src/
  kabusys/
    __init__.py
    config.py
    data/
      __init__.py
      jquants_client.py
      news_collector.py
      schema.py
      pipeline.py
      calendar_management.py
      stats.py
      features.py
      audit.py
      ...
    research/
      __init__.py
      factor_research.py
      feature_exploration.py
      ...
    strategy/
      __init__.py
      feature_engineering.py
      signal_generator.py
    execution/
      __init__.py
    monitoring/
      ...
```

（README に記載されていないファイルも多数あります。上は主要モジュールの概観です。）

## 開発上のヒント
- テスト時は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を使うと .env の自動読み込みを無効化できます。
- DuckDB をインメモリで使いたいときは `":memory:"` を `init_schema()` に渡してください（例: `init_schema(":memory:")`）。
- J‑Quants API のトークン取得は `kabusys.data.jquants_client.get_id_token()` を利用できます。トークンはモジュール内でキャッシュされ、必要に応じて自動リフレッシュされます。
- ロギングは環境変数 `LOG_LEVEL` で制御します。

## ライセンス / 貢献
（ここにライセンスや貢献方法、連絡先などを追加してください。）

---

この README はコードベースの主要機能と利用方法の概観をまとめたものです。各モジュールに詳しいドキュメント（DataPlatform.md / StrategyModel.md / Research 等）がある想定ですので、詳細実装や数式の根拠は該当ドキュメント／モジュールの docstring を参照してください。