# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ群です。  
データ取得（J‑Quants）、DuckDB を使ったデータ格納、ファクター計算、特徴量生成、シグナル生成、ニュース収集、カレンダー管理、ETL パイプラインなどを提供します。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能
- セットアップ手順
- 簡単な使い方（コード例）
- 環境変数
- ディレクトリ構成

---

プロジェクト概要
- KabuSys は日本株向けに設計された研究〜実運用を想定したコンポーネント群です。
- J‑Quants API からのデータ取得、DuckDB による Raw → Processed → Feature → Execution の多層スキーマ、研究用ファクター計算、特徴量正規化、シグナル生成、ニュース収集と紐付け、マーケットカレンダー管理、日次 ETL パイプラインなどを備えます。
- 各モジュールは外部の発注 API や実口座への直接依存を持たない設計（execution 層と分離）です。

主な機能
- データ取得 / 保存
  - J‑Quants から日足・財務データ・マーケットカレンダーを取得（レートリミット／リトライ／トークン自動更新対応）
  - DuckDB へ冪等（ON CONFLICT）で保存するユーティリティ
- ETL パイプライン
  - 差分取得、バックフィル、品質チェックを含む日次 ETL（run_daily_etl）
- スキーマ管理
  - DuckDB のスキーマ初期化（init_schema）と接続取得
- 研究用ファクター / 特徴量
  - momentum / volatility / value 等のファクター計算
  - クロスセクション Z スコア正規化（zscore_normalize）
  - features テーブルの作成（build_features）
- シグナル生成
  - 正規化済み特徴量と AI スコアを統合して final_score を算出、BUY/SELL シグナルを生成（generate_signals）
  - Bear レジーム抑制、エグジット条件（ストップロス 等）
- ニュース収集
  - RSS フィード収集、前処理、記事 ID 生成（URL 正規化 + SHA-256）、raw_news に冪等保存、銘柄コード抽出と紐付け
  - SSRF 対策、gzip サイズチェック、XML パース安全化（defusedxml）
- マーケットカレンダー管理
  - カレンダー差分更新、営業日判定（next/prev/get_trading_days 等）
- 監査・オーディット（監査ログスキーマ）
  - signal_events / order_requests / executions などトレース用テーブルを定義

---

セットアップ手順（ローカル開発向け）
1. リポジトリ（またはパッケージ）を取得
   - 例: git clone ... もしくはソースを配置

2. Python 環境を作成（推奨: venv / pyenv）
   - python -m venv .venv
   - source .venv/bin/activate

3. 依存関係をインストール
   - このコードベースは duckdb, defusedxml などを使用します。
   - 例（最小）:
     - pip install duckdb defusedxml
   - packaging がある場合:
     - pip install -e .

   ※ 実運用では logging や HTTP 用の細かな依存、テスト用パッケージ等を requirements.txt にまとめて管理してください。

4. 環境変数 (.env) を準備
   - プロジェクトルートに .env / .env.local を置くと自動で読み込まれます（.git または pyproject.toml のあるディレクトリをプロジェクトルートと判定）。
   - 自動ロードを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. DuckDB スキーマ初期化
   - Python REPL またはスクリプトから init_schema を呼ぶ（デフォルト DB: data/kabusys.duckdb）。
   - 例:
     - from kabusys.data.schema import init_schema
     - conn = init_schema("data/kabusys.duckdb")

---

環境変数一覧（主なもの）
- JQUANTS_REFRESH_TOKEN (必須)
  - J‑Quants のリフレッシュトークン。settings.jquants_refresh_token で参照。
- KABU_API_PASSWORD (必須)
  - kabuステーション等の API パスワード。
- KABU_API_BASE_URL (任意)
  - デフォルト: http://localhost:18080/kabusapi
- SLACK_BOT_TOKEN (必須)
  - Slack 通知用 Bot トークン。
- SLACK_CHANNEL_ID (必須)
  - Slack チャネル ID。
- DUCKDB_PATH (任意)
  - DuckDB ファイルパスのデフォルト: data/kabusys.duckdb
- SQLITE_PATH (任意)
  - 監視用 sqlite パスのデフォルト: data/monitoring.db
- KABUSYS_ENV (任意)
  - 有効値: development / paper_trading / live（デフォルト development）
- LOG_LEVEL (任意)
  - 有効値: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD
  - 値が設定されていると .env 自動ロードを無効化します（テスト用途など）

注意: settings では未設定の必須項目に対して ValueError を送出します。シークレットは .env.local 等で管理し、リポジトリにコミットしないでください。

---

簡単な使い方（コード例）
- スキーマ初期化（DuckDB の作成とテーブル作成）
  - from kabusys.data.schema import init_schema
  - conn = init_schema("data/kabusys.duckdb")

- ETL（日次）
  - from kabusys.data.pipeline import run_daily_etl
  - res = run_daily_etl(conn)  # target_date を渡すことも可能
  - print(res.to_dict())

- 特徴量構築（features テーブルへ）
  - from kabusys.strategy import build_features
  - from datetime import date
  - n = build_features(conn, date(2024, 1, 1))

- シグナル生成（signals テーブルへ）
  - from kabusys.strategy import generate_signals
  - from datetime import date
  - total = generate_signals(conn, date(2024, 1, 1))

- ニュース収集（RSS）
  - from kabusys.data.news_collector import run_news_collection
  - results = run_news_collection(conn, sources=None, known_codes=set(["7203","6758"]))
  - print(results)

- カレンダー更新ジョブ（夜間バッチ想定）
  - from kabusys.data.calendar_management import calendar_update_job
  - saved = calendar_update_job(conn)

補足:
- これらはすべて DuckDB 接続（duckdb.DuckDBPyConnection）を受け取ります。
- 多くの処理は「日付単位の置換（冪等）」を採用しているため、同じ日を再処理しても重複しない設計です。
- J‑Quants 呼び出しは内部でレート制御やリトライ、401 の自動リフレッシュを行います。

---

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数管理、.env の自動読み込み、settings オブジェクト
  - data/
    - __init__.py
    - jquants_client.py
      - J‑Quants API クライアント（取得 + 保存ユーティリティ）
    - pipeline.py
      - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
    - schema.py
      - DuckDB スキーマ定義・初期化（init_schema, get_connection）
    - stats.py
      - zscore_normalize（クロスセクション正規化）
    - features.py
      - data.stats の再エクスポート
    - news_collector.py
      - RSS 取得 / 前処理 / DB 保存 / 銘柄抽出
    - calendar_management.py
      - マーケットカレンダーの管理（判定ロジック / calendar_update_job）
    - audit.py
      - 発注から約定までの監査ログスキーマ（signal_events / order_requests / executions）
    - pipeline.py, audit など（ETL/監査関連）
  - research/
    - __init__.py
    - factor_research.py
      - momentum / volatility / value 等のファクター計算（prices_daily / raw_financials 参照）
    - feature_exploration.py
      - 将来リターン計算 / IC 計算 / 統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py
      - features テーブル構築（build_features）
    - signal_generator.py
      - シグナル生成ロジック（generate_signals）
  - execution/
    - __init__.py
      - 発注・実行周りのプレースホルダ（将来的な実装想定）
  - monitoring/
    - （監視用の DB / 監査等を想定したモジュール群が入る想定）

---

運用上の注意
- シークレット類は .env/.env.local（gitignore 推奨）や Secret Manager 等で安全に管理してください。
- DuckDB ファイルはプロジェクト外の永続ストレージに置くことを推奨します（例: s3/ネットワークストレージ等、運用方針に合わせる）。
- J‑Quants API の利用はレート制限（120 req/min）や利用規約に従ってください。
- 本ライブラリ自体は発注（ブローカー）APIとの接続を内包していないため、execution 層の実装やブローカー特有の堅牢化は別途実装が必要です。
- 日付の扱いは基本的に営業日（market_calendar）を優先します。calendar の未取得時は曜日ベースでフォールバックします。

---

貢献 / テスト
- 各モジュールは依存注入（DuckDB 接続 / id_token など）を意識しており、ユニットテストが書きやすい設計です。
- テスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動 .env 読み込みを無効化できます。

---

お問い合わせ
- バグ報告・改善提案はリポジトリの Issues にお願いします。README の改善提案も歓迎します。

以上。