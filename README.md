# KabuSys

日本株向けの自動売買 / データプラットフォームライブラリです。データ取得（J-Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、マーケットカレンダー管理、監査ログなどを一貫して提供します。

## 概要（Project overview）

KabuSys は以下の層を提供するモジュール群で構成されています。

- data: J-Quants からのデータ取得クライアント、DuckDB スキーマ定義・初期化、ETL パイプライン、ニュース収集、統計ユーティリティ等
- research: ファクター計算・特徴量探索ツール（研究用）
- strategy: 特徴量の正規化・合成（feature engineering）およびシグナル生成ロジック
- execution: 発注／実行層（パッケージ構成上のプレースホルダ）
- monitoring: 監視／モニタリング（パッケージ構成上のプレースホルダ）

設計思想の要点:
- ルックアヘッドバイアス防止（target_date 時点のデータのみを参照）
- 冪等性（DB への保存は ON CONFLICT / DO UPDATE 等で上書き）
- API レート制御・リトライ・トークン自動リフレッシュ
- DuckDB を中心とした軽量で自己完結したデータ基盤

## 主な機能（Features）

- J-Quants API クライアント（株価日足、財務データ、マーケットカレンダー）
  - レート制御、リトライ、401 時のトークン自動リフレッシュ、ページネーション対応
- DuckDB スキーマ定義・初期化（raw / processed / feature / execution 層）
- ETL パイプライン（日次差分更新、バックフィル、品質チェック）
- 特徴量エンジニアリング（モメンタム・ボラティリティ・バリュー系の合成と Z スコア正規化）
- シグナル生成（複数コンポーネントスコアの重み合成、Bear レジーム抑制、BUY/SELL 判定）
- ニュース収集（RSS、URL 正規化、SSRF 対策、記事→銘柄紐付け）
- マーケットカレンダー管理（営業日判定、next/prev_trading_day 等）
- 監査ログ用スキーマ（signal → order → execution のトレーサビリティ）
- 研究（research）向けユーティリティ（将来リターン計算、IC、統計サマリー）

## セットアップ手順（Setup）

以下はローカルで開発・実行するための最低手順です。

1. Python 環境を準備（推奨: venv）

   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate

2. 依存パッケージをインストール

   pip install duckdb defusedxml

   （プロジェクトに requirements.txt / pyproject.toml があればそちらを利用してください。上記はコードで利用されている主要パッケージの例です）

3. 環境変数を設定

   必須の環境変数（少なくとも外部 API を使う場合）:
   - JQUANTS_REFRESH_TOKEN : J-Quants の refresh token
   - KABU_API_PASSWORD : kabuステーション API のパスワード（発注を行う場合）
   - SLACK_BOT_TOKEN : Slack 通知用トークン（監視・通知を行う場合）
   - SLACK_CHANNEL_ID : Slack のチャネル ID

   任意 / デフォルトあり:
   - DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH : 監視用 SQLite（デフォルト: data/monitoring.db）
   - KABUSYS_ENV : development | paper_trading | live（デフォルト: development）
   - LOG_LEVEL : DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト: INFO）

   .env ファイルの自動読み込み:
   - プロジェクトルートに .env / .env.local があれば自動的に読み込まれます（os 環境変数より低優先度）
   - 自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください

   例（.env）:
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456789
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO

4. DuckDB スキーマ初期化

   Python コンソールやスクリプトで実行:

   from kabusys.data import schema
   conn = schema.init_schema("data/kabusys.duckdb")  # ":memory:" も可

   init_schema() は parent ディレクトリを自動作成し、全テーブル・インデックスを冪等で作成します。

## 使い方（Usage）

以下は主要な機能の簡単な使い方例です。実行は Python スクリプトまたは REPL で行います。

- ETL（日次）を実行する

  from datetime import date
  import kabusys
  from kabusys.data import schema, pipeline

  conn = schema.init_schema("data/kabusys.duckdb")
  result = pipeline.run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())

- 特徴量を構築（feature layer へ書き込み）

  from datetime import date
  from kabusys.data import schema
  from kabusys.strategy import build_features

  conn = schema.get_connection("data/kabusys.duckdb")
  count = build_features(conn, target_date=date(2025, 1, 20))
  print(f"{count} 銘柄を features に書き込みました")

- シグナル生成

  from datetime import date
  from kabusys.data import schema
  from kabusys.strategy import generate_signals

  conn = schema.get_connection("data/kabusys.duckdb")
  total = generate_signals(conn, target_date=date(2025, 1, 20))
  print(f"{total} 個のシグナルを書き込みました")

- ニュース収集ジョブ（RSS）

  from kabusys.data import schema, news_collector
  conn = schema.get_connection("data/kabusys.duckdb")
  # sources は {source_name: rss_url} の辞書、省略時は DEFAULT_RSS_SOURCES を使用
  results = news_collector.run_news_collection(conn, sources=None, known_codes={"7203", "6758"})
  print(results)

- カレンダー更新（夜間ジョブ）

  from kabusys.data import schema, calendar_management
  conn = schema.get_connection("data/kabusys.duckdb")
  saved = calendar_management.calendar_update_job(conn)
  print(f"saved={saved}")

- 研究用ユーティリティ

  from kabusys.research import calc_forward_returns, calc_ic, factor_summary
  # DuckDB 接続 conn と target_date を渡して解析に使用

注意:
- 各 API は target_date 時点のデータだけを使うよう設計されています（ルックアヘッドバイアス対策）。
- DB 書き込みは多くの箇所でトランザクションで原子性を保証しています（BEGIN/COMMIT/ROLLBACK）。

## 環境変数一覧（主要）

- JQUANTS_REFRESH_TOKEN (必須 for J-Quants)
- KABU_API_PASSWORD (必須 for kabu API 発注)
- KABU_API_BASE_URL (省略可、デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須 for Slack 通知)
- SLACK_CHANNEL_ID (必須 for Slack 通知)
- DUCKDB_PATH (省略可, default: data/kabusys.duckdb)
- SQLITE_PATH (省略可, default: data/monitoring.db)
- KABUSYS_ENV (development | paper_trading | live)
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL)
- KABUSYS_DISABLE_AUTO_ENV_LOAD (1 を設定すると .env 自動ロードを無効化)

## ディレクトリ構成（Directory structure）

主要ファイル・モジュールを抜粋して示します（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py                     # 環境変数・設定管理（.env 自動読み込み）
  - data/
    - __init__.py
    - jquants_client.py            # J-Quants API クライアント（取得/保存）
    - news_collector.py           # RSS ニュース収集・前処理・DB 保存
    - schema.py                   # DuckDB スキーマ定義 & init_schema()
    - stats.py                    # zscore_normalize 等 統計ユーティリティ
    - pipeline.py                 # ETL パイプライン（run_daily_etl 等）
    - calendar_management.py      # マーケットカレンダー管理（営業日判定等）
    - features.py                 # data.stats の再エクスポート
    - audit.py                    # 監査ログ用スキーマ
    - quality.py (想定)           # 品質チェック（pipeline 参照） ※実装ファイルはここに存在する想定
  - research/
    - __init__.py
    - factor_research.py          # ファクター計算（momentum/volatility/value）
    - feature_exploration.py      # 将来リターン/IC/統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py      # features テーブル構築（正規化・フィルタ）
    - signal_generator.py         # final_score 計算・BUY/SELL シグナル生成
  - execution/
    - __init__.py                 # 発注/実行層（プレースホルダ）
  - monitoring/                   # 監視関連（プレースホルダ）

（注）実際のパッケージ内にさらに補助モジュールや未表示のファイルが存在する可能性があります。

## 開発メモ / 注意点

- DuckDB を使うためローカルでの高速な分析や軽量な永続化が可能です。
- ニュース収集では SSRF・XML Bomb・巨大レスポンス等の攻撃対策を講じています（defusedxml、受信サイズ制限、ホスト検査等）。
- J-Quants クライアントは API レート・リトライ・トークン更新を備えています。大量の並列リクエストは避けてください（rate limit: 120 req/min を基準に設計）。
- シグナル生成では欠損コンポーネントに対して中立値で補完するなど欠損耐性を持たせています。
- 本リポジトリは実運用の発注を行う責任を伴います。実稼働前には十分なテストとリスク管理（ペーパー取引モード等）を行ってください。

---

不明点や追加してほしい項目（例: CLI サンプル、Docker 化、CI 設定、詳細な .env.example）などがあれば教えてください。README をその要望に合わせて拡張します。