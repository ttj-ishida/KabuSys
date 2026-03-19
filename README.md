# KabuSys

KabuSys は日本株のデータ収集・処理・特徴量生成・シグナル生成を行う自動売買向けライブラリです。J-Quants API から市場データ・財務データを取得して DuckDB に蓄積し、研究用ファクター、特徴量正規化、戦略のシグナル生成、ニュース収集、マーケットカレンダー管理、ETL パイプラインなどを提供します。

主な設計方針：
- ルックアヘッドバイアス対策（計算は target_date 時点のデータのみを使用）
- 冪等性（DB への保存は ON CONFLICT 回避やトランザクションで安全に）
- 本番 API への直接依存を最小化（research モジュールは DuckDB のみ参照）
- セキュリティ考慮（J-Quants のリトライ・トークン自動更新、RSS の SSRF/サイズ対策 など）

---

## 機能一覧

- データ取得・保存
  - J-Quants API クライアント（株価日足 / 財務データ / マーケットカレンダー）
  - DuckDB への冪等保存（raw_prices / raw_financials / market_calendar 等）
- ETL パイプライン
  - 差分取得（最終取得日からの差分 + バックフィル）
  - 日次 ETL 実行（カレンダー → 株価 → 財務 → 品質チェック）
- 特徴量・研究
  - ファクター計算（モメンタム / ボラティリティ / バリュー 等）
  - Z スコア正規化ユーティリティ
  - 将来リターン計算・IC（Information Coefficient）・統計サマリー
- 戦略
  - 特徴量の組み合わせ（features テーブル作成）
  - final_score 計算と BUY / SELL シグナル生成（signals テーブルへの保存）
  - Bear レジーム抑制、売却（エグジット）条件の判定（ストップロス等）
- ニュース収集
  - RSS 取得（トラッキングパラメータ除去、ID ハッシュ生成）、raw_news 保存、銘柄抽出
  - SSRF 防止、レスポンスサイズ制限、XML パース安全化
- マーケットカレンダー管理
  - 営業日判定、前後の営業日検索、カレンダー更新ジョブ
- スキーマ・監査
  - DuckDB スキーマ初期化（raw / processed / feature / execution 層）
  - 監査ログ（signal_events / order_requests / executions）設計（トレーサビリティ）

---

## セットアップ手順

前提
- Python 3.10+（typing の Union | を使用）
- DuckDB と必要パッケージ（下記参照）

1. リポジトリのクローン（あるいはローカルに配置）
   git clone <repo_url>

2. 仮想環境の作成（推奨）
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows

3. 必要パッケージのインストール（最低限）
   pip install duckdb defusedxml

   ※ プロジェクトに requirements.txt があれば
   pip install -r requirements.txt

4. 開発インストール（任意）
   pip install -e .

5. 環境変数および .env
   - パッケージの起動時にプロジェクトルートの `.env` / `.env.local` を自動で読み込みます（OS 環境変数が優先）。
   - 自動ロードを無効化する場合:
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

   必要な環境変数（一部必須）：
   - JQUANTS_REFRESH_TOKEN （必須）: J-Quants リフレッシュトークン
   - KABU_API_PASSWORD （必須）: kabuステーション API 用パスワード
   - SLACK_BOT_TOKEN （必須）: Slack 通知用 Bot トークン
   - SLACK_CHANNEL_ID （必須）: Slack チャネル ID
   - DUCKDB_PATH（任意）: デフォルト "data/kabusys.duckdb"
   - SQLITE_PATH（任意）: デフォルト "data/monitoring.db"
   - KABUSYS_ENV（任意）: development / paper_trading / live（デフォルト development）
   - LOG_LEVEL（任意）: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）

---

## 使い方（主要 API と実行例）

以下は代表的な操作例です。実行はプロジェクトルートから行ってください。

1. DuckDB スキーマ初期化
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")

   - メモリ DB を使う場合:
     conn = init_schema(":memory:")

2. 日次 ETL 実行
   from datetime import date
   from kabusys.data.pipeline import run_daily_etl
   conn = init_schema("data/kabusys.duckdb")
   result = run_daily_etl(conn, target_date=date.today())
   print(result.to_dict())

   - ETL はカレンダー → 株価 → 財務 → 品質チェック の順に行います。

3. 特徴量（features）を構築
   from datetime import date
   import duckdb
   from kabusys.strategy import build_features

   conn = duckdb.connect("data/kabusys.duckdb")
   n = build_features(conn, target_date=date.today())
   print(f"features written: {n}")

4. シグナル生成
   from datetime import date
   import duckdb
   from kabusys.strategy import generate_signals

   conn = duckdb.connect("data/kabusys.duckdb")
   total = generate_signals(conn, target_date=date.today(), threshold=0.6)
   print(f"signals written: {total}")

5. RSS ニュース収集ジョブ（run_news_collection）
   from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
   import duckdb
   conn = duckdb.connect("data/kabusys.duckdb")
   known_codes = {"7203", "6758", ...}  # 有効な銘柄コードセット（抽出用）
   results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
   print(results)

6. カレンダー更新バッチ
   from kabusys.data.calendar_management import calendar_update_job
   conn = duckdb.connect("data/kabusys.duckdb")
   saved = calendar_update_job(conn)
   print(f"saved calendar rows: {saved}")

7. J-Quants の手動データ取得（例）
   from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
   conn = duckdb.connect("data/kabusys.duckdb")
   records = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,12,31))
   saved = save_daily_quotes(conn, records)

ログや警告が出る場合は LOG_LEVEL を調整してください。

---

## 主要モジュールとディレクトリ構成

おおまかなディレクトリ（src/kabusys）:

- kabusys/
  - __init__.py
  - config.py                -- 環境変数 / 設定管理（.env 自動ロード、Settings）
  - data/
    - __init__.py
    - jquants_client.py      -- J-Quants API クライアント（リトライ・レート制御・保存）
    - news_collector.py      -- RSS 取得・前処理・保存・銘柄抽出
    - schema.py              -- DuckDB スキーマ定義と初期化（init_schema）
    - stats.py               -- zscore_normalize 等の統計ユーティリティ
    - pipeline.py            -- ETL パイプライン（run_daily_etl 等）
    - features.py            -- data.stats の再エクスポート
    - calendar_management.py -- 市場カレンダー管理 / 更新ジョブ
    - audit.py               -- 監査ログテーブル定義（signal_events 等）
  - research/
    - __init__.py
    - factor_research.py     -- モメンタム / バリュー / ボラティリティの計算
    - feature_exploration.py -- 将来リターン / IC / 統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py -- features テーブル作成ロジック（Z スコア正規化 / ユニバースフィルタ）
    - signal_generator.py    -- final_score 計算と signals テーブルへの書き込み
  - execution/               -- 発注・実行関連（初期プレースホルダ）
  - monitoring/              -- 監視・Slack 通知等（未詳細実装）

（上記はソース内ドキュメントに基づく主要ファイル群の概要です）

---

## 設計メモ（重要な注意点）

- 環境変数は .env / .env.local から自動でロードされます（OS 環境変数 > .env.local > .env の優先度）。自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB の初期化は init_schema() を一度実行してください。get_connection() は既存 DB へ接続するだけでスキーマ初期化は行いません。
- J-Quants API 呼び出しはレート制限（120 req/min）をモジュール内で守るようになっています。また 401 時のトークン自動更新や指数バックオフによるリトライが組み込まれています。
- ニュース収集では URL 正規化、トラッキングパラメータ除去、SSRF 対策、応答サイズ制限などの安全対策が導入されています。
- strategy 層と execution 層は分離されています。strategy は signals テーブルへシグナルを書き出しますが、発注は execution 層（または外部ブローカーアダプタ）で行う設計です。
- テーブル定義には一部 DuckDB の制約（ON DELETE CASCADE 等の未対応）に合わせた注記があります。運用時はアプリ側で整合性を扱ってください。

---

必要な追加情報や、README に載せたい具体的な運用手順（cron / Airflowジョブ例、Slack通知設定、CI/CD 設定など）があれば教えてください。README を拡張して実運用向けドキュメントに仕上げます。