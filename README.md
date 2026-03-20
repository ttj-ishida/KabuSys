# KabuSys

KabuSys は日本株向けの自動売買 / データプラットフォーム用ライブラリです。J-Quants API からのデータ取得、DuckDB ベースのデータスキーマ、ファクター計算（research）、特徴量合成（strategy）、シグナル生成、ニュース収集など、データ取得から戦略生成までの主要機能を提供します。

バージョン: 0.1.0

---

## 概要

主な設計方針・特徴：

- DuckDB を内部データストアに利用し、Raw → Processed → Feature → Execution の多層スキーマを提供
- J-Quants API から株価・財務・カレンダーを差分取得（レート制御・リトライ・トークン自動リフレッシュ対応）
- 研究用モジュール（research）でファクターを計算し、strategy 層で特徴量正規化・スコア計算・シグナル生成
- ニュース収集（RSS）と記事→銘柄紐付け機能（SSRF・XML攻撃対策、サイズ上限等を実装）
- ETL パイプライン、マーケットカレンダー管理、監査ログ用スキーマ等を備える
- 本番（live）／ペーパー（paper_trading）／開発（development）を環境変数で切替可能

---

## 機能一覧

- データ取得・保存
  - J-Quants クライアント（fetch / save: 日足、財務、カレンダー）
  - 差分 ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - DuckDB スキーマ初期化（init_schema）
- データ処理・品質
  - DuckDB ベースのスキーマ（raw_prices / prices_daily / raw_financials / features / signals / ...）
  - 品質チェック（quality モジュール経由、ETL 実行時に呼出し）
- 研究用ファクター計算（research）
  - momentum / volatility / value 等のファクター計算
  - 将来リターン算出・IC（Spearman）・統計サマリー
- 特徴量生成（strategy.feature_engineering）
  - ファクター合成、ユニバースフィルタ（最低株価・流動性）、Zスコア正規化、features テーブルへの保存
- シグナル生成（strategy.signal_generator）
  - features と ai_scores を統合して final_score を計算
  - Bear レジーム判定、BUY/SELL シグナル生成、signals テーブルへの保存（冪等）
- ニュース収集（data.news_collector）
  - RSS 取得・前処理・raw_news 保存、記事ID の冪等生成、銘柄抽出・news_symbols 保存
- 監査ログ（data.audit）
  - signal_events / order_requests / executions などの監査用スキーマ

---

## セットアップ手順

1. Python（3.9+ を想定）と pip を準備してください。

2. 依存パッケージをインストール（最低限）:

   pip install duckdb defusedxml

   （実行環境に応じて追加の依存がある場合は適宜インストールしてください）

3. パッケージをプロジェクトとしてインストール（開発モード例）:

   pip install -e .

   （プロジェクトルートに setup/pyproject があることを想定）

4. 環境変数（または .env ファイル）を設定

   必須環境変数（Settings で必須とされるもの）:
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD
   - SLACK_BOT_TOKEN
   - SLACK_CHANNEL_ID

   任意（デフォルトあり）:
   - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
   - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — デフォルト: INFO
   - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
   - SQLITE_PATH — デフォルト: data/monitoring.db

   .env ロードの挙動:
   - 自動ロード順序: OS 環境変数 > .env.local > .env
   - 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

   例 `.env`:

   JQUANTS_REFRESH_TOKEN=your_refresh_token
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb

5. DuckDB スキーマ初期化

   Python から初期化:

   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")

   これにより必要なテーブル・インデックスが作成されます（冪等）。

---

## 使い方（簡単な例）

- DuckDB 接続の初期化

  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")

- 日次 ETL の実行

  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn)  # target_date を指定しなければ今日で実行
  print(result.to_dict())

- 特徴量の構築（strategy.feature_engineering.build_features）

  from kabusys.strategy import build_features
  from datetime import date
  count = build_features(conn, date(2026, 3, 20))
  print(f"features upserted: {count}")

- シグナル生成（strategy.signal_generator.generate_signals）

  from kabusys.strategy import generate_signals
  from datetime import date
  total = generate_signals(conn, date(2026, 3, 20))
  print(f"signals generated: {total}")

- ニュース収集ジョブ（RSS）

  from kabusys.data.news_collector import run_news_collection
  # known_codes: 銘柄抽出に使う有効コードセット（例: set of "7203", ...）
  stats = run_news_collection(conn, known_codes=set(["7203", "6758"]))
  print(stats)

- 認証トークン取得（J-Quants）

  from kabusys.data.jquants_client import get_id_token
  token = get_id_token()  # settings.jquants_refresh_token を使用して取得

注意点:
- ETL / API 呼び出しは rate limit（120 req/min）・リトライ・自動トークンリフレッシュのロジックを内蔵しています。
- DuckDB へは冪等に保存するよう設計されていますが、運用時はバックアップとアクセス制御を行ってください。

---

## ディレクトリ構成（主なファイル）

以下はコードベースの主要モジュール一覧（src/kabusys 以下）：

- __init__.py
- config.py
- data/
  - __init__.py
  - jquants_client.py         -- J-Quants API クライアント（fetch/save）
  - news_collector.py        -- RSS ニュース収集・保存
  - schema.py                -- DuckDB スキーマ定義 / init_schema
  - stats.py                 -- 統計ユーティリティ（zscore_normalize）
  - pipeline.py              -- ETL パイプライン（run_daily_etl 等）
  - features.py              -- data 層の feature ユーティリティ再エクスポート
  - calendar_management.py   -- マーケットカレンダー管理 / 更新ジョブ
  - audit.py                 -- 監査ログ（signal_events / order_requests / executions）
  - (その他モジュール: quality 等、必要に応じて)
- research/
  - __init__.py
  - factor_research.py       -- momentum / volatility / value の計算
  - feature_exploration.py   -- 将来リターン・IC・統計サマリー
- strategy/
  - __init__.py
  - feature_engineering.py   -- features テーブル構築（正規化・ユニバースフィルタ）
  - signal_generator.py      -- final_score 計算・BUY/SELL シグナル生成
- execution/
  - __init__.py
  - （発注・約定ラッパー等を実装予定）
- monitoring/
  - （監視・メトリクス関連を実装予定）

上記は実装の要点を抜粋したものです。詳細は各モジュールの docstring をご参照ください。

---

## 開発・運用上の留意点

- 環境設定: 必須トークン類は秘匿して管理してください（CI/Secrets 等）。
- テスト: KABUSYS_DISABLE_AUTO_ENV_LOAD を 1 にして自動 .env ロードを無効化し、環境依存性を切ってテスト可能です。
- リトライ・レート制御: J-Quants 呼び出しには内部でスロットリングと指数バックオフを実装していますが、運用側でも適切な間隔で呼び出してください。
- ルックアヘッド対策: research/strategy はルックアヘッドバイアスに配慮して設計しています（target_date 時点のデータのみ参照）。

---

## 参考: よく使う API

- 初期化: kabusys.data.schema.init_schema(db_path)
- ETL: kabusys.data.pipeline.run_daily_etl(conn, target_date=None)
- ファクター計算: kabusys.research.calc_momentum / calc_volatility / calc_value
- 特徴量構築: kabusys.strategy.build_features(conn, target_date)
- シグナル生成: kabusys.strategy.generate_signals(conn, target_date)
- ニュース収集: kabusys.data.news_collector.run_news_collection(conn, sources=None, known_codes=None)

---

必要であれば README に含める具体的なコマンドやサンプルスクリプト（systemd タイマー / cron での実行例、Dockerfile、CI 設定など）を追加で作成します。どの内容を詳しく書くか教えてください。