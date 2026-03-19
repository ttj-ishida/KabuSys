# KabuSys — 日本株自動売買基盤 (README)

KabuSys は日本株のデータ収集・処理・特徴量生成・シグナル生成を行う自動売買基盤向けの Python モジュール群です。J-Quants API からのデータ取得、DuckDB によるデータ保管、特徴量エンジニアリング、戦略シグナル生成、ニュース収集、マーケットカレンダー管理、ETL パイプライン、監査ログ/発注周りのスキーマを提供します。

主な設計方針
- ルックアヘッドバイアス防止：target_date 時点のデータのみ参照する設計
- 冪等性：DB への保存は ON CONFLICT / トランザクションで安全に行う
- 外部依存を最小化：データ処理は可能な限り標準ライブラリと DuckDB で実装
- 安全性配慮：RSS 収集の SSRF 対策、XML の defusedxml 処理、API レート制御、リトライ

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（簡易例）
- 環境変数（主要設定）
- ディレクトリ構成
- よくある問題と対処

---

プロジェクト概要
- J-Quants API から株価・財務・カレンダー等を取得して DuckDB に保存する ETL。
- research 層で計算した raw ファクターを正規化して features テーブルへ保存。
- features と ai_scores を統合して最終スコア（final_score）を計算、BUY/SELL シグナルを生成して signals テーブルへ保存。
- RSS フィードからニュースを収集して raw_news に保存、銘柄紐付けも実装。
- 市場カレンダー管理（営業日判定・次/前営業日の計算）や監査ログスキーマも提供。

---

機能一覧
- データ取得・保存
  - J-Quants クライアント（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）
  - DuckDB への冪等セーブ（raw_prices / raw_financials / market_calendar など）
- ETL パイプライン
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl（差分取得、バックフィル、品質チェック）
- データスキーマ管理
  - init_schema(db_path) による DuckDB スキーマ作成（Raw / Processed / Feature / Execution 層）
- 特徴量・戦略
  - factor_research: calc_momentum / calc_volatility / calc_value
  - feature_engineering: build_features（Zスコア正規化、ユニバースフィルタ、features テーブルに UPSERT）
  - signal_generator: generate_signals（コンポーネントスコア、重み付き合成、BUY/SELL 判定、signals テーブルへ保存）
- ニュース収集
  - RSS 取得（fetch_rss）＋ raw_news 保存（save_raw_news）＋銘柄抽出・news_symbols 保存
  - SSRF 防止・gzip/サイズチェック・XML 安全パース
- マーケットカレンダー管理
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job
- 統計ユーティリティ
  - zscore_normalize / ranking / IC（Spearman）計算 / factor_summary
- 監査ログ（audit）
  - signal_events / order_requests / executions 等の監査テーブル定義

---

セットアップ手順（開発環境向け）
前提: Python 3.9+（型ヒントに Union 表記などを使用。環境に合わせて調整してください）

1. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージのインストール
   - 必須: duckdb, defusedxml
   - 例:
     - pip install duckdb defusedxml

   プロジェクトを editable インストール可能なら（pyproject.toml / setup.py があれば）
   - pip install -e .

3. データベース初期化
   - Python REPL またはスクリプトから:
     - from kabusys.data.schema import init_schema
     - conn = init_schema("data/kabusys.duckdb")  # デフォルトパスを使用する場合

4. 環境変数設定
   - .env または環境変数で各種シークレット・パスを設定（下記参照）
   - パッケージはプロジェクトルートの .env/.env.local を自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）

---

使い方（簡易例）

- Config の取得（コード中で利用）
  - from kabusys.config import settings
  - token = settings.jquants_refresh_token

- DB 初期化
  - from kabusys.data.schema import init_schema
  - conn = init_schema("data/kabusys.duckdb")

- 日次 ETL 実行（J-Quants トークンが settings に設定されている前提）
  - from kabusys.data.pipeline import run_daily_etl
  - result = run_daily_etl(conn)
  - print(result.to_dict())

- 特徴量作成
  - from datetime import date
  - from kabusys.strategy import build_features
  - build_features(conn, date(2024, 1, 1))

- シグナル生成
  - from kabusys.strategy import generate_signals
  - total = generate_signals(conn, date(2024, 1, 1))
  - print(f"signals generated: {total}")

- ニュース収集（既知銘柄セットを渡すと銘柄紐付けも行う）
  - from kabusys.data.news_collector import run_news_collection
  - results = run_news_collection(conn, sources=None, known_codes={"7203","6758"})

- calendar 更新ジョブ
  - from kabusys.data.calendar_management import calendar_update_job
  - saved = calendar_update_job(conn)

注意: 上記関数群は基本的に DuckDB 接続（duckdb.DuckDBPyConnection）を受け取ります。DB 接続は init_schema で初期化するか get_connection() を使用してください。

---

主要な環境変数（settings）
設定は .env ファイルまたは OS 環境変数から読み込まれます。自動読み込みはプロジェクトルート（.git または pyproject.toml を探索）から .env → .env.local の順で行われ、OS 環境変数が優先されます。

必須:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（get_id_token に使用）
- KABU_API_PASSWORD: kabu ステーション API のパスワード
- SLACK_BOT_TOKEN: Slack 通知に使用する Bot トークン
- SLACK_CHANNEL_ID: 通知先チャンネル ID

任意（デフォルト値あり）:
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 実行環境 (development | paper_trading | live)。デフォルト: development
- LOG_LEVEL: ログレベル (DEBUG | INFO | WARNING | ERROR | CRITICAL)。デフォルト: INFO
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると自動 .env ロードを無効化（テストなどで使用）

.env の例（例示）
```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

環境変数未設定の必須キーにアクセスすると ValueError が発生します（settings が検証するため）。

---

ディレクトリ構成（主要ファイル抜粋）
プロジェクトは src/kabusys 以下にモジュール群を配置します。主要ファイル:

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数/設定管理
  - data/
    - __init__.py
    - jquants_client.py       — J-Quants API クライアント（取得/保存）
    - schema.py               — DuckDB スキーマ定義 / init_schema
    - pipeline.py             — ETL パイプライン（run_daily_etl 等）
    - news_collector.py       — RSS 収集・raw_news 保存・銘柄抽出
    - calendar_management.py  — 市場カレンダー管理
    - features.py             — zscore_normalize 再エクスポート
    - stats.py                — 統計ユーティリティ（zscore_normalize）
    - audit.py                — 監査ログスキーマ（signal_events 等）
    - execution/               — 発注関連（空の __init__ がある）
  - research/
    - __init__.py
    - factor_research.py      — ファクター計算（momentum/volatility/value）
    - feature_exploration.py  — 将来リターン / IC / 統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py  — build_features（正規化・UPSERT）
    - signal_generator.py     — generate_signals（最終スコア・BUY/SELL）
  - monitoring/               — 監視関連（sqlite 等を想定、ファイルは含まれます）

（上記は本リポジトリに含まれる主要モジュールを抜粋したものです）

---

よくある問題と対処

- ValueError: 環境変数 '<KEY>' が設定されていません
  - settings で必須キーが未設定のため発生。.env を作成するか環境変数をセットしてください。

- DuckDB の接続エラー / パスが存在しない
  - init_schema は DB の親ディレクトリを自動作成します。パスを確認してください。

- J-Quants API の 401/レート制限
  - jquants_client は 401 時のトークンリフレッシュ、120 req/min の固定間隔制御・指数バックオフを実装しています。API 側制限に合わせて実行間隔を調整してください。

- RSS 取得が失敗する（XML エラー / 大きすぎるレスポンス）
  - news_collector は不正な XML、過度なサイズ、gzip 解凍エラー等を検出して安全側にフォールバックします。ソース URL を確認してください。

- テストで .env の自動読み込みを無効化したい
  - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

貢献 / 拡張ポイント（案内）
- 発注/ブローカー接続層（execution）を実装して信号→実注文フローを 완성
- AI スコア生成パイプライン（ai_scores の充填）
- 品質チェックモジュール（data.quality）実装・拡張（pipeline から呼び出される想定）
- テスト用のフィクスチャ・CI ワークフロー追加

---

ライセンス / その他
- 本 README はコードベースの説明を目的としています。実運用の際は API キー管理・セキュリティ・コンプライアンスに十分注意してください。

---

問い合わせ
- コード内の docstring とログメッセージに処理の意図や注意点が記載されています。実装を読むことで詳細な挙動を確認できます。質問があればコードの該当モジュール名を指定して問い合わせください。