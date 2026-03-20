# KabuSys

日本株向け自動売買プラットフォーム用ライブラリ（KabuSys）。  
データ収集（J-Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、監査ログなどを含むモジュール群を提供します。

---

## プロジェクト概要

KabuSys は日本株のデータパイプラインと戦略レイヤーを提供する Python パッケージです。主な目的は以下です。

- J-Quants API からの市場データ・財務データ・カレンダーの取得と DuckDB への保存（冪等）
- ニュース（RSS）収集と記事→銘柄の紐付け
- 研究用ファクター計算（モメンタム・ボラティリティ・バリュー等）
- 特徴量の正規化と戦略向け features テーブル作成
- final_score に基づくシグナル生成（BUY/SELL）と signals テーブルへの保存
- カレンダー管理、ETL の差分更新、品質チェック、監査ログ用テーブルの初期化

設計上の特徴：
- ルックアヘッドバイアスに配慮（target_date 時点の情報のみを使用）
- 冪等性（DB 保存は ON CONFLICT / DO UPDATE 等で重複を排除）
- 外部依存を最小化（可能な限り標準ライブラリと duckdb を使用）
- API 呼び出しに対するレート制御、リトライ、トークン自動リフレッシュ実装

---

## 機能一覧

- data
  - jquants_client: J-Quants API クライアント（ページネーション・レート制御・リトライ・トークン自動更新）
  - schema: DuckDB のスキーマ定義と初期化（raw/processed/feature/execution のテーブル群）
  - pipeline: 日次 ETL（差分更新・backfill・品質チェック）と個別 ETL ジョブ
  - news_collector: RSS フィード収集・前処理・DB 保存・銘柄抽出
  - calendar_management: 市場カレンダーの更新と営業日関連ユーティリティ
  - stats: Z スコア正規化等の統計ユーティリティ
  - audit: 発注/約定までの監査ログ用スキーマ（トレーサビリティ）
- research
  - factor_research: momentum / volatility / value などのファクター計算
  - feature_exploration: 将来リターン計算、IC（Spearman）計算、統計サマリー
- strategy
  - feature_engineering.build_features: raw ファクターから features テーブル作成（Z スコア正規化・クリップ・ユニバースフィルタ）
  - signal_generator.generate_signals: features + ai_scores を統合して final_score を算出し BUY/SELL シグナル生成
- config
  - 環境変数管理（.env 自動ロード、必須変数チェック）
- その他: execution / monitoring 用のプレースホルダモジュール

---

## 要件

- Python 3.10 以上（型注釈で | を使用）
- 必要パッケージ（例）
  - duckdb
  - defusedxml
  - （標準ライブラリ: urllib, json 等は不要インストール）
- J-Quants API トークン等の環境変数

pip の依存情報はプロジェクト側の pyproject.toml / requirements.txt に合わせてください。

---

## 環境変数（.env）

パッケージはプロジェクトルート（.git または pyproject.toml）を起点に `.env` / `.env.local` を自動ロードします。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主な環境変数（例）:

- JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
- KABU_API_PASSWORD=your_kabu_api_password
- KABU_API_BASE_URL=http://localhost:18080/kabusapi  # 任意（デフォルトあり）
- SLACK_BOT_TOKEN=xoxb-...
- SLACK_CHANNEL_ID=C...
- DUCKDB_PATH=data/kabusys.duckdb  # デフォルト: data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- KABUSYS_ENV=development|paper_trading|live  # デフォルト: development
- LOG_LEVEL=INFO|DEBUG|...

（.env.example を作成して上記を埋めることを推奨）

---

## セットアップ手順（Quickstart）

1. リポジトリをクローンして作業ディレクトリへ移動
   - git clone ...
   - cd <repo>

2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Linux/macOS)  
     .venv\Scripts\activate     (Windows)

3. 依存パッケージをインストール
   - pip install -U pip
   - pip install duckdb defusedxml
   - （プロジェクトに pyproject.toml がある場合）pip install -e .

4. 環境変数を設定（.env を作成）
   - プロジェクトルートに `.env` を作成し、上の環境変数を設定してください。

5. DuckDB スキーマの初期化
   - Python REPL またはスクリプトで:
     from kabusys.data.schema import init_schema, get_connection
     conn = init_schema("data/kabusys.duckdb")  # または settings.duckdb_path
   - これにより必要なテーブル（raw/prices/features/signals 等）が作成されます。

---

## 使い方（主要ワークフロー例）

下記は典型的な日次ワークフロー例です。

1) データベース接続と初期化
- 初回のみスキーマ初期化（以降は get_connection を使用）
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")

2) 日次 ETL を実行（J-Quants から差分取得 → 保存 → 品質チェック）
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn)  # target_date を指定可能
  print(result.to_dict())

3) 特徴量を構築（features テーブルへ保存）
  from kabusys.strategy import build_features
  from datetime import date
  n = build_features(conn, date.today())
  print("features upserted:", n)

4) シグナルを生成（signals テーブルへ保存）
  from kabusys.strategy import generate_signals
  count = generate_signals(conn, date.today(), threshold=0.6)
  print("signals saved:", count)

5) ニュース収集ジョブ
  from kabusys.data.news_collector import run_news_collection
  known_codes = {"7203", "6758", ...}  # 既知の銘柄セット
  res = run_news_collection(conn, known_codes=known_codes)
  print(res)

6) カレンダーの夜間更新ジョブ（スケジューラから呼ぶ）
  from kabusys.data.calendar_management import calendar_update_job
  saved = calendar_update_job(conn)
  print("calendar saved:", saved)

注意点:
- run_daily_etl 等は内部でエラーハンドリングを行い、エラーや品質問題を ETLResult に集約します。戻り値を確認して運用してください。
- 各保存関数（save_*）は冪等に設計されています（ON CONFLICT を利用）。

---

## 主要 API リファレンス（抜粋）

- kabusys.config.settings
  - settings.jquants_refresh_token, settings.kabu_api_password, settings.slack_bot_token, settings.duckdb_path, settings.env, settings.log_level, など

- データ層
  - kabusys.data.schema.init_schema(db_path) -> DuckDB 接続（初期化）
  - kabusys.data.schema.get_connection(db_path) -> DuckDB 接続（スキーマ初期化なし）
  - kabusys.data.jquants_client.fetch_daily_quotes(...)
  - kabusys.data.jquants_client.save_daily_quotes(conn, records)
  - kabusys.data.pipeline.run_daily_etl(conn, target_date=None, ...)

- 研究 / 戦略
  - kabusys.research.calc_momentum(conn, target_date)
  - kabusys.research.calc_volatility(conn, target_date)
  - kabusys.research.calc_value(conn, target_date)
  - kabusys.strategy.build_features(conn, target_date)
  - kabusys.strategy.generate_signals(conn, target_date, threshold=0.6, weights=None)

- ニュース
  - kabusys.data.news_collector.fetch_rss(url, source)
  - kabusys.data.news_collector.save_raw_news(conn, articles)
  - kabusys.data.news_collector.run_news_collection(conn, sources=None, known_codes=None)

（関数の詳しい引数・戻り値は各モジュールのドックストリングを参照してください）

---

## ディレクトリ構成

以下は主要ファイル／ディレクトリの構成（抜粋）です:

- src/kabusys/
  - __init__.py
  - config.py               — 環境変数 / 設定管理（.env 自動ロード）
  - data/
    - __init__.py
    - jquants_client.py     — J-Quants API クライアント（取得/保存ユーティリティ）
    - news_collector.py     — RSS 収集・前処理・DB 保存
    - pipeline.py           — ETL パイプライン（run_daily_etl 等）
    - schema.py             — DuckDB スキーマ定義・初期化
    - stats.py              — 統計ユーティリティ（zscore_normalize）
    - calendar_management.py— 市場カレンダー管理
    - audit.py              — 監査ログ用スキーマ（signal_events / order_requests / executions）
    - features.py           — features の公開インターフェース
    - execution/            — 発注実装用プレースホルダ
  - research/
    - __init__.py
    - factor_research.py    — ファクター計算（momentum/volatility/value）
    - feature_exploration.py— 将来リターン / IC / summary 等
  - strategy/
    - __init__.py
    - feature_engineering.py— features テーブル構築（正規化・フィルタ）
    - signal_generator.py   — final_score 計算・BUY/SELL シグナル生成
  - monitoring/             — 監視・アラート用プレースホルダ

上記以外にドキュメント（DataPlatform.md, StrategyModel.md 等）が参照される設計ノートが想定されています。

---

## 運用・開発上の注意

- 環境（KABUSYS_ENV）: development / paper_trading / live を想定。live では実際の発注につながるため運用時は注意してください。
- 認証トークン管理: J-Quants の refresh token を環境変数で安全に管理してください。get_id_token は自動で refresh を扱います。
- レート制御: jquants_client は 120 req/min を想定したスロットリングを実装しています。大量リクエスト時は注意。
- テスト: 自動 .env ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使用してください。
- DB のバックアップ・移行: DuckDB ファイルは単一ファイルなのでバックアップを推奨します。:memory: モードでのテストも可能です。

---

## 参考例（.env.example）

JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_api_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO

---

README の内容はコードのドキュストリングに基づいて作成しています。追加の運用手順、CI/CD、テスト例、具体的な pyproject/requirements の整備が必要であれば、さらに追記します。