# KabuSys

日本株向けの自動売買／データ基盤ライブラリです。  
DuckDB を用いたデータレイク（Raw / Processed / Feature / Execution 層）と、J‑Quants API からのデータ収集、特徴量計算、シグナル生成、ニュース収集、マーケットカレンダー管理などを含むモジュール群を提供します。

主な設計方針：  
- ルックアヘッドバイアスの排除（target_date 時点のデータのみを利用）  
- 冪等性（DB への保存は ON CONFLICT / トランザクションで安全に）  
- テスト容易性（id_token 等を注入可能）  
- セキュリティ配慮（RSS 収集の SSRF対策、XML の安全パース等）  

---

## 機能一覧

- データ取得・保存
  - J‑Quants API クライアント（株価日足 / 財務 / マーケットカレンダー）
  - レート制限・リトライ・自動トークンリフレッシュ
  - DuckDB へ冪等保存（raw_prices, raw_financials, market_calendar 等）
- ETL / パイプライン
  - 日次差分 ETL（market calendar → prices → financials）と品質チェックの実行
  - バックフィル・差分取得ロジック
- カレンダー管理
  - 営業日判定、前後営業日取得、カレンダー夜間更新ジョブ
- 研究・ファクター計算
  - Momentum / Volatility / Value 等のファクター計算（prices_daily / raw_financials を参照）
  - cross‑section の Z スコア正規化ユーティリティ
  - 将来リターン計算、IC（Spearman）計算、統計サマリー
- 特徴量エンジニアリング
  - research で算出した生ファクターを合成・正規化して `features` テーブルへ UPSERT
  - ユニバースフィルタ（最低株価・平均売買代金）など
- シグナル生成
  - features と ai_scores を統合し final_score を算出して BUY/SELL シグナルを生成
  - Bear レジーム判定、ストップロス等のエグジット条件
  - signals テーブルへ日付単位の置換（冪等）
- ニュース収集
  - RSS フィードの取得、前処理、raw_news への保存、記事と銘柄コードの紐付け
  - URL 正規化・トラッキングパラメータ除去、記事ID（SHA‑256 の先頭 32 文字）
  - SSRF 対策、受信サイズ制限、gzip 対応、defusedxml による安全な XML パース
- 監査ログ（audit）
  - signal → order_request → execution までのトレーサビリティを確保する DB テーブル群

---

## 前提・依存関係

- Python 3.10+
- 必要ライブラリ（例）
  - duckdb
  - defusedxml
- ネットワークアクセス（J‑Quants API、RSS フィード）
- DuckDB ファイル（デフォルト: data/kabusys.duckdb）

※ パッケージ化や requirements.txt はプロジェクトの配布方法に応じて用意してください。最低限は pip install duckdb defusedxml を行ってください。

---

## 環境変数（主なもの）

config モジュールは .env/.env.local または OS 環境変数を自動的にロードします（プロジェクトルートに .git か pyproject.toml がある場合）。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須（Settings._require を通すもの）
- JQUANTS_REFRESH_TOKEN — J‑Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード（発注機能を使う場合）
- SLACK_BOT_TOKEN — Slack 通知用ボットトークン（通知を使う場合）
- SLACK_CHANNEL_ID — Slack チャンネル ID

任意（デフォルト値あり）
- KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）

例 (.env)
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

---

## セットアップ手順（簡易）

1. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate

2. 必要パッケージをインストール
   - pip install duckdb defusedxml

   （プロジェクトに requirements.txt / pyproject.toml がある場合はそれに従ってください）

3. 環境変数を設定
   - プロジェクトルートに .env を作成するか、環境変数を設定します。

4. DuckDB スキーマ初期化
   - Python REPL またはコマンドでスキーマを作成します（親ディレクトリは自動生成されます）。

     python -c "from kabusys.data.schema import init_schema; init_schema('data/kabusys.duckdb')"

---

## 使い方（例）

- DuckDB 接続の初期化（ファイル作成 + テーブル作成）

  python -c "from kabusys.data.schema import init_schema; conn = init_schema('data/kabusys.duckdb'); print(conn)"

- 日次 ETL 実行（市場カレンダー／株価／財務の差分取得および品質チェック）

  python -c "from kabusys.data.schema import init_schema; from kabusys.data.pipeline import run_daily_etl; import datetime; conn=init_schema('data/kabusys.duckdb'); res=run_daily_etl(conn, target_date=None); print(res.to_dict())"

- 特徴量構築（features テーブルの作成）

  python -c "from kabusys.data.schema import get_connection; from kabusys.strategy import build_features; import datetime; conn=get_connection('data/kabusys.duckdb'); print(build_features(conn, datetime.date.today()))"

- シグナル生成（signals テーブルへの書き込み）

  python -c "from kabusys.data.schema import get_connection; from kabusys.strategy import generate_signals; import datetime; conn=get_connection('data/kabusys.duckdb'); print(generate_signals(conn, datetime.date.today()))"

- ニュース収集ジョブ（RSS 収集 → raw_news 保存 → news_symbols 紐付け）

  python -c "from kabusys.data.schema import get_connection; from kabusys.data.news_collector import run_news_collection; conn=get_connection('data/kabusys.duckdb'); print(run_news_collection(conn, known_codes={'7203','6758'}))"

- カレンダー夜間更新ジョブ

  python -c "from kabusys.data.schema import get_connection; from kabusys.data.calendar_management import calendar_update_job; conn=get_connection('data/kabusys.duckdb'); print(calendar_update_job(conn))"

備考：
- 各モジュールは DuckDB の接続オブジェクト（duckdb.DuckDBPyConnection）を受け取ります。初回は init_schema() でテーブルを作成してから get_connection() を使って接続してください。
- J‑Quants の API 呼び出しは内部でトークンを取得・キャッシュし、レート制限（120 req/min）を守るように実装されています。

---

## 主要エントリポイント（モジュール / 関数抜粋）

- kabusys.config.settings — 環境設定オブジェクト
- kabusys.data.schema
  - init_schema(db_path) — DuckDB スキーマ初期化
  - get_connection(db_path) — 既存 DB 接続取得
- kabusys.data.jquants_client
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar
  - get_id_token
- kabusys.data.pipeline
  - run_daily_etl(conn, target_date=None, ...)
  - run_prices_etl, run_financials_etl, run_calendar_etl
- kabusys.data.news_collector
  - fetch_rss, save_raw_news, run_news_collection
- kabusys.data.calendar_management
  - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, calendar_update_job
- kabusys.research
  - calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary
- kabusys.strategy
  - build_features(conn, target_date)
  - generate_signals(conn, target_date, threshold=..., weights=...)

---

## ディレクトリ構成

プロジェクトの主要ファイル群（src/kabusys）:

- kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py
    - news_collector.py
    - schema.py
    - stats.py
    - pipeline.py
    - features.py
    - calendar_management.py
    - audit.py
    - execution/ (空パッケージ placeholder)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - strategy/
    - __init__.py
    - feature_engineering.py
    - signal_generator.py
  - monitoring/ (パッケージ placeholder)

（上記はリポジトリ内の主要モジュールを抜粋したものです）

---

## 運用上の注意・ベストプラクティス

- 本システムは実際の発注を行う場合、十分なバックテスト・リスク管理・監査を行ってください。KabuSys の戦略ロジックは参考実装を意図しています。
- 本番運用では KABUSYS_ENV を `live` に設定し、Slack 通知や発注層の確認を行ってください。
- J‑Quants の API レート制限や利用規約に従ってください。大量取得時はバックオフやスケジューリングを検討してください。
- RSS 取得は外部サイトに負荷をかけないよう適切な間隔（ポーリング間隔）を設定してください。
- DB のバックアップを定期的に取り、監査ログ（audit）を削除しない運用を推奨します。

---

## 貢献・拡張

- 新しい戦略を strategy/ 以下に実装し、build_features / generate_signals のフローに沿って統合してください。
- execution 層（発注ロジック・ブローカー連携）は execution パッケージに実装してください（Kabu API 等のブリッジを想定）。
- 監視（monitoring）や運用ジョブのスクリプトを追加して自動化してください。

---

不明点や追加してほしい内容（例: CLI スクリプト、詳細なテーブル定義・ER 図、CI 設定など）があれば教えてください。README をその要望に合わせて拡張します。