# KabuSys

KabuSys は日本株向けの自動売買・データプラットフォームです。J-Quants から市場データ・財務データを取得し、DuckDB に保存、特徴量計算・シグナル生成・ニュース収集・カレンダー管理などを通じて戦略を実行するためのライブラリ群を提供します。

---

## 概要

主な目的は以下です。

- J-Quants API から株価・財務・市場カレンダーを差分取得して保存（ETL）
- DuckDB 上でのデータスキーマ管理と効率的な分析処理
- 研究用ファクター計算（モメンタム／ボラティリティ／バリュー等）
- クロスセクション Z スコア正規化、特徴量の構築（features テーブル）
- 正規化済み特徴量と AI スコアを統合して売買シグナルを生成
- RSS ベースのニュース収集と銘柄紐付け
- JPX カレンダー管理（営業日判定、先読み更新）
- 発注・実行・監査ログ用のスキーマ（Execution / Audit レイヤー）

設計上の特徴として、ルックアヘッドバイアス防止、冪等性（ON CONFLICT / upsert）、外部 API のレートリミット遵守、テスト容易性（トークン注入など）に配慮しています。

---

## 機能一覧

- データ取得・保存
  - J-Quants クライアント（fetch / save: 日足、財務、カレンダー）
  - 差分 ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
- スキーマ管理
  - DuckDB スキーマ初期化（init_schema）
  - 各レイヤー（raw / processed / feature / execution / audit）テーブル定義
- 研究・特徴量
  - ファクター計算（calc_momentum / calc_volatility / calc_value）
  - Z スコア正規化（zscore_normalize）
  - 特徴量作成（build_features → features テーブルへUPSERT）
- シグナル生成
  - generate_signals（features と ai_scores を統合して BUY/SELL を生成）
  - エグジット判定（ストップロス、スコア低下等）
- ニュース収集
  - RSS フィード取得（fetch_rss）・記事保存（save_raw_news）
  - 銘柄コード抽出と紐付け（extract_stock_codes / save_news_symbols）
  - SSRF / XML Bomb / レスポンスサイズ上限等の安全対策実装
- カレンダー管理
  - market_calendar の差分更新と営業日判定 API（is_trading_day, next_trading_day, ...）
- ユーティリティ
  - 設定管理（環境変数 / .env 自動ロード）
  - ログレベル / 環境（development / paper_trading / live）判定

---

## セットアップ手順

1. Python を用意（推奨: 3.9+）
2. 必要なパッケージをインストール（例）

   ```bash
   python -m pip install duckdb defusedxml
   # 開発中でパッケージ化されている場合:
   # python -m pip install -e .
   ```

   - ライブラリ依存はプロジェクトにより追加される可能性があります。必要に応じて requirements.txt を参照してください。

3. DuckDB ファイル用ディレクトリを用意する（デフォルトは data/kabusys.duckdb）

   ```bash
   mkdir -p data
   ```

4. 環境変数設定 (.env)

   プロジェクトルート（.git か pyproject.toml を探します）に `.env` と `.env.local` を置けます。ロード優先度は OS 環境変数 > .env.local > .env です。

   主な環境変数（例）:

   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabuステーション等と連携する場合のパスワード（必須: 利用時）
   - KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
   - SLACK_BOT_TOKEN: Slack 通知を使う場合（必須: 利用時）
   - SLACK_CHANNEL_ID: Slack チャネル ID（必須: 利用時）
   - DUCKDB_PATH: DuckDB データベースパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
   - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

   自動で .env を読み込ませたくない場合:

   ```bash
   export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   ```

---

## 使い方（代表的な例）

以下は Python スクリプトから主要機能を呼ぶ簡単な例です。DuckDB 接続には duckdb パッケージを使用します。

1. スキーマ初期化

   ```python
   from kabusys.data.schema import init_schema

   conn = init_schema("data/kabusys.duckdb")
   ```

2. 日次 ETL を実行（J-Quants トークンは環境変数から自動取得）

   ```python
   from datetime import date
   from kabusys.data.pipeline import run_daily_etl
   from kabusys.data.schema import get_connection

   conn = get_connection("data/kabusys.duckdb")
   result = run_daily_etl(conn, target_date=date.today())
   print(result.to_dict())
   ```

3. 特徴量構築（features テーブルへの upsert）

   ```python
   from datetime import date
   from kabusys.strategy import build_features
   from kabusys.data.schema import get_connection

   conn = get_connection("data/kabusys.duckdb")
   count = build_features(conn, target_date=date.today())
   print(f"features upserted: {count}")
   ```

4. シグナル生成

   ```python
   from datetime import date
   from kabusys.strategy import generate_signals
   from kabusys.data.schema import get_connection

   conn = get_connection("data/kabusys.duckdb")
   total_signals = generate_signals(conn, target_date=date.today(), threshold=0.6)
   print(f"signals written: {total_signals}")
   ```

5. ニュース収集ジョブ（RSS 収集 → raw_news に保存 → news_symbols 紐付け）

   ```python
   from kabusys.data.news_collector import run_news_collection
   from kabusys.data.schema import get_connection

   conn = get_connection("data/kabusys.duckdb")
   # known_codes は抽出に利用する有効な銘柄コードセット（例: {'7203', '6758', ...}）
   results = run_news_collection(conn, known_codes={'7203', '6758'})
   print(results)
   ```

6. カレンダー更新ジョブ（夜間バッチ）

   ```python
   from kabusys.data.calendar_management import calendar_update_job
   from kabusys.data.schema import get_connection

   conn = get_connection("data/kabusys.duckdb")
   saved = calendar_update_job(conn)
   print(f"market_calendar saved: {saved}")
   ```

---

## 設定の取り扱い

- 設定は基本的に環境変数（os.environ）から取得します。`.env` / `.env.local` はプロジェクトルートから自動読込されます。
- 自動ロードを抑止したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 必須の環境変数が未設定の場合、Settings のプロパティアクセスで ValueError が発生します（例: JQUANTS_REFRESH_TOKEN）。

---

## ディレクトリ構成（主要ファイル）

プロジェクトは src/kabusys 以下に配置されています。主なモジュールと責務は下記のとおりです。

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数・.env ロード・Settings クラス
  - data/
    - __init__.py
    - jquants_client.py       — J-Quants API クライアント（取得・保存）
    - news_collector.py       — RSS ニュース収集・保存・銘柄抽出
    - schema.py               — DuckDB スキーマ定義・初期化
    - stats.py                — zscore_normalize 等の統計ユーティリティ
    - pipeline.py             — ETL パイプライン（差分更新 / run_daily_etl 等）
    - features.py             — features に関する公開ユーティリティ（再エクスポート）
    - calendar_management.py  — JPX カレンダー管理（営業日判定 / update job）
    - audit.py                — 監査ログスキーマ（signal_events / order_requests / executions）
  - research/
    - __init__.py
    - factor_research.py      — モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py  — forward returns / IC / factor summary 等
  - strategy/
    - __init__.py
    - feature_engineering.py  — ファクター統合 → features テーブルへの保存
    - signal_generator.py     — features + ai_scores → signals の生成
  - execution/
    - __init__.py
    - (発注・ブローカー連携実装箇所想定)
  - monitoring/
    - (監視・アラート用モジュール想定)

ファイル単位でも詳細な docstring がついており、各関数の引数・戻り値・副作用について明記されています。

---

## 運用上の注意

- J-Quants API のレート制限（120 req/min）を遵守するため内部でスロットリングとリトライが実装されています。過度の同時リクエストは避けてください。
- DuckDB スキーマは init_schema で作成してください。既存スキーマに対する処理は冪等的に行われます。
- ニュース収集モジュールは外部 RSS を扱うため、SSRF / XML 攻撃・大容量レスポンス等に対する防御（実装済み）がありますが、実運用時は収集元の監査も行ってください。
- 本リポジトリには発注層（execution）・監査層のスキーマが含まれますが、実際の証券会社との接続や本番運用を行う際は細心の注意（リスク管理・二重発注防止・テスト環境での検証）を行ってください。
- 環境は KABUSYS_ENV によって切り替えられます。production / live の場合は特にログ・通知・発注フローに注意してください。

---

問題や改善提案がある場合は、コード内の docstring や各モジュールのログ出力を参照し、必要に応じて issue を作成してください。README 以外に具体的なユースケースやデプロイ手順が必要であればご依頼ください。