# KabuSys

日本株向け自動売買プラットフォームのコアライブラリです。  
データ収集（J-Quants）、ETL、特徴量作成、シグナル生成、ニュース収集、監査ログなどの基盤機能を含みます。

---

## プロジェクト概要

KabuSys は次のレイヤーを想定したモジュール群を提供します。

- Data layer: J-Quants からのデータ取得、DuckDB スキーマ定義、ETL パイプライン、ニュース収集
- Research layer: ファクター計算・探索（モメンタム・ボラティリティ・バリュー等）
- Feature / Strategy layer: ファクターの正規化・合成、シグナル生成（BUY/SELL）
- Execution / Audit: 発注・約定・ポジション・監査用スキーマ（初期化ロジック含む）
- 設定管理: 環境変数 / .env 読み込みを行う設定モジュール

設計上の特徴：
- DuckDB を中心にローカルで分析可能
- ETL / 保存処理は冪等（ON CONFLICT / トランザクション）で実装
- J-Quants API はレート制限・リトライ・自動トークン更新を考慮
- ニュース取得は SSRF / XML Bomb / 大容量レスポンス対策あり
- ルックアヘッドバイアスを避けるため、常に target_date 時点のデータのみを使用

---

## 主な機能一覧

- 設定管理
  - 環境変数・.env 自動読み込み（プロジェクトルート判定）
  - 必須設定チェック（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN 等）

- Data / ETL
  - J-Quants クライアント（株価・財務・カレンダー取得、ページネーション対応）
  - ETL パイプライン（差分取得・保存・品質チェック）
  - DuckDB スキーマ初期化（raw / processed / feature / execution 層）
  - 市場カレンダー管理（営業日判定、next/prev_trading_day 等）
  - ニュース収集（RSS -> raw_news、記事ID正規化、銘柄抽出）

- Research / Feature
  - ファクター計算（calc_momentum, calc_volatility, calc_value）
  - ファクター探索ユーティリティ（将来リターン / IC / 統計サマリ）
  - Z スコア正規化ユーティリティ

- Strategy
  - build_features: ファクター合成・正規化・features テーブルへ書き込み
  - generate_signals: features + ai_scores を統合して BUY/SELL シグナル作成、signals テーブルへ保存

- Audit / Execution（スキーマ）
  - signal_events, order_requests, executions など監査用テーブルの定義
  - 発注監査トレースのための DDL/初期化ロジック

---

## 必須依存関係（代表）

- Python 3.10+
- duckdb
- defusedxml

（上のパッケージは setup.py / pyproject.toml に依存関係を追加してください）

---

## 環境変数（.env）

プロジェクトはプロジェクトルート（.git または pyproject.toml）を基準に自動で `.env` / `.env.local` を読み込みします（環境変数が優先）。自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主要な環境変数：

- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabu ステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（省略時: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視用）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 実行環境（development / paper_trading / live）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）

設定はコード内の `kabusys.config.settings` 経由で取得できます。

---

## セットアップ手順（例）

1. Python 3.10+ の仮想環境を作成・有効化

2. 依存関係をインストール（例）
   - requirements.txt または pyproject.toml があればそれに従ってください。最小限:
     pip install duckdb defusedxml

3. リポジトリルートに `.env` を作成（.env.example を参考に必要なキーを設定）

4. DuckDB スキーマ初期化
   - Python REPL またはスクリプトで実行例：

     python - <<'PY'
     from kabusys.data.schema import init_schema
     init_schema("data/kabusys.duckdb")
     print("DuckDB schema initialized")
     PY

   - メモリ DB を使う場合:
     init_schema(":memory:")

---

## 使い方（代表的な例）

- 日次 ETL 実行（株価・財務・カレンダー取得 + 品質チェック）

  Python から呼び出す例：

  python - <<'PY'
  from datetime import date
  import duckdb
  from kabusys.data.schema import init_schema, get_connection
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  PY

  run_daily_etl は idempotent な差分取得を行い、品質チェックも実行します。

- 特徴量の構築（features テーブルへのアップサート）

  from kabusys.strategy import build_features
  from kabusys.data.schema import get_connection
  import duckdb
  from datetime import date

  conn = get_connection("data/kabusys.duckdb")
  count = build_features(conn, date(2025, 1, 31))
  print(f"built features for {count} symbols")

- シグナル生成（signals テーブルへ保存）

  from kabusys.strategy import generate_signals
  from kabusys.data.schema import get_connection
  from datetime import date

  conn = get_connection("data/kabusys.duckdb")
  total = generate_signals(conn, date(2025, 1, 31))
  print(f"generated {total} signals")

  generate_signals は重みや閾値を引数で調整できます。

- ニュース収集ジョブ（RSS -> raw_news, news_symbols）

  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  # known_codes は銘柄抽出で使う有効銘柄セット
  known_codes = {"7203", "6758", "9432"}
  results = run_news_collection(conn, sources=None, known_codes=known_codes)
  print(results)

- J-Quants からのデータ取得（低レベル）
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar

  これらは jquants の認証・リトライ・ページネーション処理を内包しています。

---

## 注意点 / 設計ノート

- ETL / 保存処理は基本的に冪等（ON CONFLICT / トランザクション）です。複数回実行しても重複しないよう設計されています。
- J-Quants クライアントは 120 req/min のレート制限を守るために内部でスロットリングを行います。429/5xx 等のリトライロジックあり。
- ニュース取得は SSRF 対策、gzip 解凍サイズチェック、defusedxml による XML の安全パースを実施します。
- strategy 層は execution 層に直接 API コールを行いません（シグナルは signals テーブルに保存）。
- config モジュールはプロジェクトルートを走査して `.env` を自動読み込みします（必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py                            — 環境変数・設定管理
- data/
  - __init__.py
  - jquants_client.py                  — J-Quants API クライアント + 保存
  - news_collector.py                  — RSS 収集・正規化・DB 保存
  - schema.py                          — DuckDB スキーマ定義と init_schema/get_connection
  - pipeline.py                        — ETL パイプライン（run_daily_etl 等）
  - stats.py                           — 統計ユーティリティ（zscore_normalize）
  - features.py                         — zscore_normalize エクスポート
  - calendar_management.py             — 市場カレンダー管理（is_trading_day 等）
  - audit.py                           — 監査ログ用 DDL
  - (その他 data 関係モジュール)
- research/
  - __init__.py
  - factor_research.py                  — calc_momentum, calc_volatility, calc_value
  - feature_exploration.py              — calc_forward_returns, calc_ic, factor_summary, rank
- strategy/
  - __init__.py                         — build_features, generate_signals を公開
  - feature_engineering.py              — build_features 実装
  - signal_generator.py                 — generate_signals 実装
- execution/                             — execution 層エントリ（実装ファイルは別途）
- monitoring/                            — 監視用モジュール（別途）

（上記は本リポジトリに含まれる主要ファイル群の抜粋です）

---

## 開発 / テストのヒント

- 設定の自動読み込みを無効化するには:
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  これによりテスト時に環境変数を明示的に設定できます。

- DuckDB はインメモリで簡単にテストできます:
  conn = init_schema(":memory:")

- news_collector のネットワーク呼び出しや jquants_client の _urlopen/_request はユニットテストでモック可能に作られています。

---

## コントリビュート / ライセンス

- この README はコードベースの現状に基づく概要および使用例です。実運用前に .env の機密情報管理、API トークン、発注ロジックの安全性検証を必ず行ってください。
- ライセンスやコントリビュート手順はリポジトリのトップレベルファイルを参照してください（LICENSE / CONTRIBUTING.md 等）。

---

必要であれば、README に実際のコマンド例（systemd / cron ジョブ設定、Slack 通知サンプル、デバッグ手順等）を追加で記載します。どの部分を詳しくしたいか教えてください。