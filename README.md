# KabuSys — 日本株自動売買フレームワーク

KabuSys は日本株向けのデータ基盤、ファクター計算、シグナル生成、ETL を備えた自動売買システムのライブラリです。  
この README ではプロジェクト概要、主な機能、セットアップ手順、基本的な使い方、ディレクトリ構成を日本語で説明します。

> 注意: このリポジトリはライブラリ／SDK であり、実際の売買（ライブ注文）を行う際は各種設定やリスク管理を十分に行ってください。

---

目次
- プロジェクト概要
- 機能一覧
- 必要な環境変数（.env）
- セットアップ手順
- 使い方（主な API と実行例）
- ディレクトリ構成（主要ファイルの説明）
- 補足 / 注意事項

---

## プロジェクト概要

KabuSys は以下を目的とした Python ベースのモジュール群です。

- J-Quants 等の外部 API から市場データ・財務データ・カレンダーを取得して DuckDB に保存する ETL パイプライン
- ファクター（Momentum / Value / Volatility / Liquidity）計算とクロスセクション正規化
- features と AI スコアを統合したシグナル生成（BUY / SELL）
- RSS ニュース収集と銘柄紐付け
- マーケットカレンダー管理、監査ログ・発注追跡用のスキーマ定義

設計方針として、ルックアヘッドバイアスを避けるため計算は target_date 時点のデータのみを用いること、DuckDB を中心とした冪等的な DB 操作、外部 API 呼び出しはクライアント経由で明示的に行うこと、などを採用しています。

---

## 機能一覧

- データ取得 / 保存
  - J-Quants API クライアント（レート制御・リトライ・トークン自動更新）
  - 株価（OHLCV）、財務データ、JPX カレンダーの取得と DuckDB 保存（冪等）
- ETL パイプライン
  - 日次差分 ETL（calendar / prices / financials）と品質チェック
- データスキーマ
  - Raw / Processed / Feature / Execution 層を含む DuckDB スキーマ初期化
- ファクター計算（research）
  - Momentum, Volatility, Value 等の計算関数（prices_daily / raw_financials を使用）
- 特徴量エンジニアリング（strategy）
  - 正規化（Z スコア）・ユニバースフィルタ適用・features テーブルへの UPSERT
- シグナル生成（strategy）
  - features と AI スコアを統合し final_score を算出、BUY/SELL シグナルを signals テーブルへ保存
- ニュース収集
  - RSS フィードの収集、記事正規化、raw_news 保存、銘柄抽出と紐付け
- カレンダー管理
  - 営業日判定・前後営業日の取得・カレンダー更新ジョブ
- 監査ログ（audit）
  - signal → order_request → executions までのトレース用テーブル群

---

## 必要な環境変数（.env）

自動ロード機構があり、プロジェクトルートの `.env` / `.env.local` を読みます（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

主に使用される環境変数（必須は README に明示）:

- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API のパスワード（必須 for execution 層）
- KABU_API_BASE_URL — kabu API の base URL（省略時: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN — Slack 通知に使用（必須 if Slack 機能を利用）
- SLACK_CHANNEL_ID — Slack チャネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境 (development | paper_trading | live)。デフォルト development
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）

例（.env）:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. リポジトリをクローン／コピー

2. Python 仮想環境を作成（例）
   - python3 -m venv .venv
   - source .venv/bin/activate

3. 必要パッケージのインストール  
   本コードベースで利用している主な外部依存:
   - duckdb
   - defusedxml

   例:
   - pip install --upgrade pip
   - pip install duckdb defusedxml

   （プロジェクトに requirements.txt / pyproject.toml があればそれに従ってください。editable install をする場合は pip install -e .）

4. 環境変数を設定
   - プロジェクトルートに `.env` を作成するか、シェルで環境変数を export してください。
   - 自動ロードは .env / .env.local をプロジェクトルートから読み込みます（.git または pyproject.toml を探索してルートを判定）。

5. DuckDB スキーマ初期化
   - Python REPL で:
     ```
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     ```
   - またはスクリプト内で同様に呼び出してください。`:memory:` を渡すとインメモリ DB になります。

---

## 使い方（主要な API と実行例）

以下は基本的な操作フローの例です。すべての操作は DuckDB 接続（kabusys.data.schema.init_schema の戻り値）に対して行います。

1. DB の初期化（再掲）
   ```
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   ```

2. 日次 ETL（市場カレンダー・株価・財務の差分 ETL）
   ```
   from kabusys.data.pipeline import run_daily_etl
   result = run_daily_etl(conn)  # target_date を指定可能
   print(result.to_dict())
   ```

3. 特徴量（features）構築
   ```
   from kabusys.strategy import build_features
   from datetime import date
   cnt = build_features(conn, date(2025, 1, 15))
   print("upserted features:", cnt)
   ```

4. シグナル生成
   ```
   from kabusys.strategy import generate_signals
   from datetime import date
   total = generate_signals(conn, date(2025, 1, 15), threshold=0.6)
   print("signals written:", total)
   ```

5. ニュース収集（RSS）
   ```
   from kabusys.data.news_collector import run_news_collection
   # sources は {source_name: rss_url} の辞書。省略時はデフォルトソースを使用
   known_codes = {"7203", "6758", "9984"}  # 有効銘柄コードセット（省略可能）
   results = run_news_collection(conn, known_codes=known_codes)
   print(results)
   ```

6. カレンダー更新ジョブ（夜間バッチ）
   ```
   from kabusys.data.calendar_management import calendar_update_job
   saved = calendar_update_job(conn)
   print("calendar saved:", saved)
   ```

7. J-Quants からデータ取得（低レベル）
   ```
   from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
   records = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,12,31))
   saved = save_daily_quotes(conn, records)
   ```

その他、research 側の関数（calc_forward_returns, calc_ic, factor_summary 等）はリサーチ用途で直接呼び出せます。

---

## ディレクトリ構成（主要ファイルの説明）

リポジトリの主要なソースは `src/kabusys/` 以下にあります。主なモジュールと役割：

- kabusys/
  - __init__.py — パッケージメタ情報
  - config.py — 環境変数 / 設定の読み込み・検証（.env 自動読み込み機能含む）
- kabusys/data/
  - schema.py — DuckDB スキーマ定義と init_schema / get_connection
  - jquants_client.py — J-Quants API クライアント（取得・保存ユーティリティ）
  - pipeline.py — ETL パイプライン（run_daily_etl など）
  - news_collector.py — RSS 収集・保存・銘柄抽出
  - calendar_management.py — カレンダー管理 / 更新ジョブ / 営業日ユーティリティ
  - features.py — zscore_normalize の公開インターフェース
  - stats.py — 汎用統計関数（zscore_normalize）
  - audit.py — 監査ログ（signal_events, order_requests, executions など）
  - other files: quality.py 等（品質チェック用、存在しない場合は別モジュール）
- kabusys/research/
  - factor_research.py — Momentum / Value / Volatility の計算
  - feature_exploration.py — 将来リターン・IC・統計サマリー等
  - __init__.py — research API の再エクスポート
- kabusys/strategy/
  - feature_engineering.py — features を構築して features テーブルへ保存
  - signal_generator.py — final_score 計算と signals テーブルへの書き込み
  - __init__.py — strategy API の再エクスポート
- kabusys/execution/ — 発注／ブローカ連携コード（未具体化のサブモジュール）
- kabusys/monitoring/ — 監視・アラート用モジュール（監視DB 等）

（この README に掲載しているモジュールのサブ間の依存関係はコード内ドキュメントに従っています）

---

## 補足 / 注意事項

- DB 初期化は一度行えば良いですが、スキーマが変更された場合はマイグレーション方針に従ってください。本リポジトリは簡易スキーマ初期化を提供します。
- J-Quants API のレート制限（120 req/min）やエラーレスポンスに対するリトライロジックは jquants_client に組み込まれています。長時間のバルク取得は配慮が必要です。
- ニュース収集は外部 RSS を読み込むため SSRF や XML 関連の攻撃に配慮し、防御策を実装しています（defusedxml、ホストチェック、受信サイズ制限等）。
- 本システムは paper_trading / live の運用切替を環境変数 KABUSYS_ENV で切り替えます。live 運用では十分なテストとリスク管理を行ってください。
- .env の自動ロードを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト用など）。

---

この README はコードベースから抜粋してまとめた概要です。各モジュールの詳細な使い方やパラメータは該当ファイルの docstring / 関数コメントを参照してください。必要であれば、実行スクリプト例や運用手順（cron / Airflow / CI でのスケジューリング）に関する追加ドキュメントも作成できます。必要な内容を教えてください。