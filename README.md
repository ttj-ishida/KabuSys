# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ群です。データ取得・ETL、特徴量計算、シグナル生成、ニュース収集、マーケットカレンダー管理、監査ログなどを含むモジュール群を提供します。

主な設計方針は「ルックアヘッドバイアスの排除」「DuckDB を用いた冪等なデータ保存」「外部 API 呼び出しのリトライ／レート制御」「モジュール分離によるテスト性」です。

対応 Python バージョン: 3.10 以降（| 型注釈などを使用しています）

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（簡単なサンプル）
- ディレクトリ構成
- 環境変数一覧 / 設定
- 開発メモ・注意事項

---

プロジェクト概要
- KabuSys は日本株の自動売買基盤向けに設計されたライブラリ群です。
- J-Quants API から市場データ／財務データ／カレンダーを取得して DuckDB に保存する ETL、特徴量計算（research 層）、特徴量の正規化・合成（strategy 層）、シグナル生成、RSS ベースのニュース収集と銘柄紐付け、監査ログ（order/signal/trade のトレーサビリティ）などの機能を提供します。
- 各モジュールは発注 API（execution 層）への直接依存を持たないように設計されており、戦略ロジックと発注ロジックを分離しています。

---

機能一覧
- データ取得・保存
  - J-Quants API クライアント（レート制御、リトライ、トークン自動リフレッシュ）
  - daily quotes / financial statements / market calendar の取得と DuckDB への冪等保存
  - raw_prices / raw_financials / market_calendar などのスキーマ定義と初期化
- ETL パイプライン
  - 差分取得（最終取得日からの差分のみ取得、バックフィル対応）
  - run_daily_etl による日次一括 ETL（カレンダー → 株価 → 財務 → 品質チェック）
- データ品質チェック（quality モジュールと連携、ETL 結果に品質問題を記録）
- 研究用ファクター計算（research）
  - モメンタム、ボラティリティ（ATR）、バリュー（PER/ROE）など
  - 将来リターン計算（forward returns）、IC（Spearman）計算、ファクター統計サマリ
- 特徴量生成（strategy.feature_engineering）
  - research で得た生ファクターを統合・正規化（Zスコア）、ユニバースフィルタ適用、features テーブルへ UPSERT
- シグナル生成（strategy.signal_generator）
  - features と ai_scores を統合して final_score を計算、BUY/SELL シグナルを生成し signals テーブルへ UPSERT
  - Bear レジーム判定、ストップロスなどのエグジット判定
- ニュース収集（data.news_collector）
  - RSS フィードの取得（SSRF 対策、gzip サイズ制限、XML パース保護）
  - 正規化された記事を raw_news に保存、記事→銘柄の紐付け（news_symbols）
- マーケットカレンダー管理（data.calendar_management）
  - market_calendar を用いた営業日・SQ 日判定、next/prev_trading_day、calendar_update_job
- 監査ログ（data.audit）
  - signal_events / order_requests / executions など監査用テーブル（UUID ベースのトレーサビリティ）
- 汎用統計ユーティリティ（data.stats: zscore_normalize）

---

セットアップ手順

前提:
- Python 3.10+
- 必要な外部パッケージ（最低限）:
  - duckdb
  - defusedxml

1. リポジトリをクローンして開発用インストール
   ```bash
   git clone <repo-url>
   cd <repo-dir>
   pip install -e .[dev]   # または pip install -r requirements.txt
   ```
   ※ requirements / extras はプロジェクト側の packaging に依存します。最低で duckdb と defusedxml をインストールしてください。

2. 環境変数設定
   - プロジェクトルートに .env を置くと自動的に読み込まれます（os 環境 > .env.local > .env の順で上書き）。
   - あるいは環境変数を直接エクスポートしてください。
   - 自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

   必須の主な環境変数（例）:
   - JQUANTS_REFRESH_TOKEN=xxxxx
   - KABU_API_PASSWORD=xxxxx
   - SLACK_BOT_TOKEN=xxxxx
   - SLACK_CHANNEL_ID=xxxxx

   任意 / デフォルト:
   - DUCKDB_PATH=data/kabusys.duckdb
   - SQLITE_PATH=data/monitoring.db
   - KABUSYS_ENV=development | paper_trading | live  (デフォルト: development)
   - LOG_LEVEL=INFO

3. DuckDB スキーマ初期化
   Python REPL やスクリプトで初期化します。ファイルパスに ":memory:" を指定してインメモリ DB を使うこともできます。
   ```python
   from kabusys.data.schema import init_schema, get_connection
   conn = init_schema("data/kabusys.duckdb")
   # あるいは既存 DB へ接続（スキーマ初期化は行わない）
   conn = get_connection("data/kabusys.duckdb")
   ```

4. ETL 実行（例）
   日次 ETL を実行して J-Quants からデータを取得・保存します。
   ```python
   from datetime import date
   from kabusys.data.pipeline import run_daily_etl
   from kabusys.data.schema import init_schema

   conn = init_schema("data/kabusys.duckdb")
   result = run_daily_etl(conn, target_date=date.today())
   print(result.to_dict())
   ```

---

使い方（簡単なサンプル）

- 特徴量を生成して戦略シグナルを作る一連の流れ（DB が初期化済みで必要な raw テーブルが埋まっていることが前提）:
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.schema import get_connection, init_schema
  from kabusys.strategy import build_features, generate_signals

  conn = init_schema("data/kabusys.duckdb")
  target = date.today()

  # 1) features を作成
  n_features = build_features(conn, target)
  print("features upserted:", n_features)

  # 2) シグナル生成
  total_signals = generate_signals(conn, target)
  print("signals generated:", total_signals)
  ```

- ニュース収集ジョブ（RSS）:
  ```python
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  known_codes = {"7203", "6758", "9984"}  # 事前に把握している有効銘柄コード集合

  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
  print(results)
  ```

- マーケットカレンダー更新ジョブ:
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  saved = calendar_update_job(conn)
  print("calendar saved:", saved)
  ```

- テスト用にインメモリ DB を使う:
  ```python
  conn = init_schema(":memory:")
  ```

---

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                         — 環境変数設定 / Settings
  - data/
    - __init__.py
    - jquants_client.py               — J-Quants API クライアント（取得/保存ユーティリティ）
    - news_collector.py               — RSS ベースのニュース収集・保存・銘柄抽出
    - schema.py                       — DuckDB スキーマ定義・初期化
    - stats.py                        — zscore_normalize 等の統計ユーティリティ
    - pipeline.py                     — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py          — カレンダー更新・営業日ユーティリティ
    - features.py                      — data 層の features 再エクスポート
    - audit.py                         — 監査用テーブル定義（signal/order/execution）
    - ...（quality 等、他モジュールと連携）
  - research/
    - __init__.py
    - factor_research.py              — momentum / volatility / value 計算
    - feature_exploration.py          — forward returns / IC / factor summary
  - strategy/
    - __init__.py
    - feature_engineering.py          — features テーブル生成（正規化・フィルタ）
    - signal_generator.py             — final_score 計算・BUY/SELL シグナル生成
  - execution/
    - __init__.py                     — 発注層のプレースホルダ（実装は別途）
  - monitoring/ (exported in package root via __all__ but実際のファイル群はここに配置される想定)

（README 生成時点のコードベースでは execution パッケージは初期化ファイルのみなど、発注接続部分は別実装/インテグレーションが必要です）

---

環境変数一覧（主なもの）
- 必須:
  - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（get_id_token 用）
  - KABU_API_PASSWORD — kabuステーション API パスワード（発注等で使用）
  - SLACK_BOT_TOKEN — Slack 通知用トークン（通知実装がある場合）
  - SLACK_CHANNEL_ID — Slack チャネルID
- 任意（デフォルトがあるもの）:
  - DUCKDB_PATH (default: data/kabusys.duckdb)
  - SQLITE_PATH (default: data/monitoring.db)
  - KABUSYS_ENV (development | paper_trading | live) default: development
  - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) default: INFO
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で .env 自動ロードを無効化

注意: config.Settings のプロパティは必須 env が未設定だと ValueError を投げます。

---

開発メモ・注意事項
- DuckDB への保存は多くの関数で ON CONFLICT や UPSERT の形で冪等性を保証しています。
- J-Quants API はレート制限（120 req/min）に合わせた固定間隔スロットリングとリトライを実装しています。大量の並列リクエストは避けてください。
- RSS 収集では SSRF 対策・受信サイズ上限・XML パース保護を行っていますが、追加のソースを登録する際は URL の正当性を確認してください。
- strategy モジュールは発注層に依存しない設計です。実際の発注ロジックは execution 層を実装して統合してください。
- テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動ロードをオフにできます。
- Python タイプ注釈と logging を多用しています。ログレベルは LOG_LEVEL で制御してください。

---

問い合わせ / 貢献
- バグ報告・機能追加は Issue を通じてお願いします。コードの貢献は Pull Request を歓迎します。

---

以上。必要があれば README にチュートリアル（より詳しい ETL スケジュール例、cron / CI での運用手順、DuckDB の VACUUM/バックアップ方針、テスト手順）を追加できます。どの部分を詳しく追記しますか？