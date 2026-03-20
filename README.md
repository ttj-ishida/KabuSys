# KabuSys

日本株向け自動売買プラットフォーム用ライブラリ（部分実装）。  
データ取得（J-Quants）、ETL、特徴量計算、シグナル生成、ニュース収集、マーケットカレンダー管理、監査ログなどを含むモジュール群を提供します。

---

## プロジェクト概要

KabuSys は日本株の量的投資パイプラインを支える内部ライブラリ群です。主な目的は次のとおりです。

- J-Quants API からの株価・財務・カレンダー等の取得と DuckDB への保存（冪等）
- データ品質チェックと差分 ETL の自動化
- 研究用に実装されたファクター（モメンタム・ボラティリティ・バリュー等）の計算
- 特徴量の正規化・合成（features テーブル作成）
- 合成スコアに基づく売買シグナル生成（signals テーブル）
- RSS からのニュース収集と銘柄紐付け
- マーケットカレンダー管理（営業日判定、next/prev/trading days）
- 監査ログ（シグナル→発注→約定のトレース）設計

設計方針として、ルックアヘッドバイアスを避けるため「target_date 時点の情報のみ」を使用すること、外部発注 API や実口座との直接結合を行わないこと、DuckDB を中心としたローカル DB に冪等に保存することが挙げられます。

---

## 主な機能一覧

- 設定管理
  - .env / .env.local の自動読み込み（プロジェクトルート基準）と環境変数ラッパー（kabusys.config.settings）
  - 必須環境変数の検証（未設定時は例外）

- Data 層（kabusys.data）
  - jquants_client: J-Quants API クライアント（レートリミット、リトライ、トークン自動リフレッシュ）
  - schema: DuckDB スキーマ定義と初期化（init_schema）
  - pipeline: 差分 ETL（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - news_collector: RSS 取得、前処理、raw_news/nnews_symbols への保存（SSRF対策、gzip制限、トラッキング除去）
  - calendar_management: 営業日判定・next/prev_trading_day 等のユーティリティ
  - stats: z-score 正規化などの統計ユーティリティ

- Research 層（kabusys.research）
  - factor_research: モメンタム・ボラティリティ・バリュー等のファクター計算
  - feature_exploration: 将来リターン、IC（Spearman）、ファクターサマリー計算

- Strategy 層（kabusys.strategy）
  - feature_engineering.build_features: 生ファクターを統合・正規化して features テーブルへ保存
  - signal_generator.generate_signals: features と ai_scores を統合して final_score を算出、BUY/SELL シグナルを生成して signals テーブルへ保存

- Execution / Monitoring
  - パッケージ構成上のプレースホルダ（発注・監視ロジックは別モジュールで実装）

- 監査（audit）
  - signal_events / order_requests / executions など、監査用テーブル定義（トレーサビリティ確保）

---

## 必要な環境変数

主に以下が必須・推奨されています（kabusys.config.Settings 参照）:

必須:
- JQUANTS_REFRESH_TOKEN  — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD      — kabuステーション API のパスワード（発注連携がある場合）
- SLACK_BOT_TOKEN        — Slack 通知用 Bot トークン（通知実装を使う場合）
- SLACK_CHANNEL_ID       — Slack チャネル ID

任意（デフォルトあり）:
- KABUSYS_ENV            — 環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL              — ログレベル（DEBUG/INFO/...、デフォルト: INFO）
- DUCKDB_PATH            — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH            — 監視用 SQLite パス（デフォルト: data/monitoring.db）

自動ロード:
- プロジェクトルートにある `.env` および `.env.local` を、自動的にロードします（OS 環境変数を保護）。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

---

## セットアップ手順

前提: Python 3.10 以上（typing の union 型等を使用）、pip が使用可能であること。

1. リポジトリをクローン:
   - git clone ...

2. 仮想環境の作成（任意）:
   - python -m venv .venv
   - source .venv/bin/activate  # macOS/Linux
   - .venv\Scripts\activate     # Windows

3. 依存パッケージのインストール:
   - pip install duckdb defusedxml
   - （プロジェクト配布用に setup/pyproject があれば）pip install -e .

   ※ 実行環境に応じて追加パッケージやバージョン管理を行ってください。

4. 環境変数の準備:
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` を作成してください（例: .env.example を参考）。
   - 必須トークンを設定します（JQUANTS_REFRESH_TOKEN 等）。

5. DuckDB スキーマ初期化:
   Python REPL やスクリプトで次を実行します:

   from kabusys.config import settings
   from kabusys.data import schema
   conn = schema.init_schema(settings.duckdb_path)

   （db_path を文字列で直接指定することも可能 ":memory:" でメモリDB）

---

## 使い方（基本例）

以下はライブラリ関数の簡単な使用例です。実運用時は適切な例外処理やログ管理を追加してください。

- DB 初期化

  from kabusys.config import settings
  from kabusys.data import schema
  conn = schema.init_schema(settings.duckdb_path)

- 日次 ETL 実行（J-Quants から差分取得して DB 保存・品質チェック）

  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn)  # target_date を指定可能
  print(result.to_dict())

- 特徴量の構築（features テーブルへ書き込み）

  from kabusys.strategy import build_features
  from datetime import date
  count = build_features(conn, target_date=date(2025, 1, 1))
  print(f"features upserted: {count}")

- シグナル生成（signals テーブルへ書き込み）

  from kabusys.strategy import generate_signals
  from datetime import date
  total = generate_signals(conn, target_date=date.today())
  print(f"signals generated: {total}")

- ニュース収集ジョブ（RSS 取得 → raw_news 保存 → 銘柄紐付け）

  from kabusys.data.news_collector import run_news_collection
  known_codes = {"7203","6758", ...}  # 有効銘柄コードセット（抽出に使用）
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)

- マーケットカレンダーユーティリティ

  from kabusys.data.calendar_management import is_trading_day, next_trading_day
  is_td = is_trading_day(conn, date(2025, 1, 2))
  next_td = next_trading_day(conn, date.today())

---

## よく使う API と注意点

- settings（kabusys.config.settings）は環境変数を直接読み、必須項目が未設定だと ValueError を投げます。
- jquants_client は内部でレートリミットとリトライを実装しています（120 req/min、指数バックオフ、401 のトークン自動更新）。
- news_collector は SSRF 対策やレスポンスサイズ制限（10MB）など堅牢性を考慮しています。
- schema.init_schema は冪等的にテーブル作成およびインデックス作成を行います。
- pipeline.run_daily_etl は品質チェックモジュール（quality）を呼び出します。品質チェックでエラーを検出しても ETL は継続し、結果オブジェクトに問題情報を集約します。
- generate_signals は欠損コンポーネントを中立（0.5）で補完し、重みのバリデーションと再スケーリングを行います。Bear レジーム検知により BUY を抑制するロジックがあります。

---

## ディレクトリ構成

（リポジトリの一部を抜粋）

src/
  kabusys/
    __init__.py
    config.py
    data/
      __init__.py
      jquants_client.py
      news_collector.py
      schema.py
      pipeline.py
      stats.py
      features.py
      calendar_management.py
      audit.py
      pipeline.py
      (その他 data 関連モジュール)
    research/
      __init__.py
      factor_research.py
      feature_exploration.py
    strategy/
      __init__.py
      feature_engineering.py
      signal_generator.py
    execution/
      __init__.py
    monitoring/   # パッケージ表明は __all__ に含まれるが、実装は別途
    (その他モジュール)

主なテーブル（DuckDB）:
- raw_prices, raw_financials, raw_news, raw_executions
- prices_daily, market_calendar, fundamentals, news_articles, news_symbols
- features, ai_scores
- signals, signal_queue, orders, trades, positions, portfolio_performance
- audit 用: signal_events, order_requests, executions

---

## 開発上のメモ / 注意事項

- 環境変数の自動ロード機能はデフォルトで有効（.env/.env.local）。テスト時に無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB の SQL 実行時は一部 raw SQL を直接渡しているため、外部からの文字列結合には注意してください（本コードはプレースホルダを使用する設計）。
- news_collector の RSS パーサは defusedxml を使って XML の攻撃対策を行っています。依存パッケージはプロジェクトの要件に合わせて追加してください。
- jquants_client は HTTP のタイムアウトや特定ステータスでのリトライを行います。API 利用制限やエラー挙動に合わせた運用が必要です。
- 実運用で発注を行う場合は、execution 層とブローカ接続（kabuステーション等）を適切に実装・テストしてください。本リポジトリ内の発注関連テーブル・監査設計はそのための土台です。

---

以上が KabuSys の概要・セットアップ・基本的な使い方です。詳細は各モジュールのドキュメント文字列（docstring）やコードコメントを参照してください。必要であれば README を拡張して CLI やサンプルスクリプト、.env.example を追記できます。