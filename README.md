# KabuSys

日本株向けの自動売買／リサーチ用ライブラリ群です。データ取得（J-Quants）、特徴量エンジニアリング、シグナル生成、ポートフォリオ構築、バックテスト、ニュース収集等のコンポーネントを含みます。

## プロジェクト概要
- 目的: 日本株アルゴリズムの研究・運用・バックテストが可能な汎用モジュール群を提供する。
- 設計方針:
  - DuckDB をデータレイク／分析 DB として利用
  - ルックアヘッドバイアス回避（target_date 以前のデータのみ参照）
  - 冪等性・トランザクションを重視した DB 操作
  - ネットワーク処理はリトライ／レート制御／SSRF 対策を実装

## 主な機能一覧
- data/
  - J-Quants API クライアント（jquants_client.py）: 日次株価、財務、上場銘柄情報、マーケットカレンダー取得・保存
  - ニュース収集（news_collector.py）: RSS 収集、前処理、記事保存、銘柄抽出
- research/
  - ファクター計算（factor_research.py）: momentum / volatility / value 等の定量ファクター
  - ファクター探索（feature_exploration.py）: 将来リターン、IC、統計サマリー
- strategy/
  - 特徴量作成（feature_engineering.py）: raw factor を正規化して `features` テーブルへ保存
  - シグナル生成（signal_generator.py）: features + ai_scores を統合して BUY/SELL シグナルを生成
- portfolio/
  - 候補選定・重み（portfolio_builder.py）
  - ポジションサイジング（position_sizing.py）
  - リスク調整（risk_adjustment.py）
- backtest/
  - バックテストエンジン（engine.py）: フルバックテストループ、擬似約定
  - シミュレータ（simulator.py）: 約定・手数料・スリッページモデル、日次スナップショット
  - メトリクス算出（metrics.py）
  - CLI（run.py）: コマンドラインでバックテスト実行
- その他
  - 設定管理（config.py）: 環境変数・.env の読み込み、必須設定取得 API
  - ETL/スキーマ初期化（データスキーマ用モジュールが想定されます）

## 必要な環境変数
以下はこのコードベースで参照される主要な環境変数（例）です。運用時は .env/.env.local に定義してください。

- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API（発注）用パスワード（必須）
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN — Slack 通知用トークン（必須）
- SLACK_CHANNEL_ID — Slack チャンネル ID（必須）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視用）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL — ログレベル (DEBUG/INFO/WARNING/ERROR/CRITICAL)
- KABUSYS_DISABLE_AUTO_ENV_LOAD — "1" を設定すると自動で .env を読み込まない

注意: Settings クラスのプロパティは未設定の場合に ValueError を送出するものがあるため、実行前に必須環境変数を用意してください。

## セットアップ手順（開発用）
1. Python（推奨 3.10+）をインストール
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - requirements.txt がある前提:
     - pip install -r requirements.txt
   - 主要依存候補（本コードで使用）:
     - duckdb
     - defusedxml
   - その他はプロジェクトで必要に応じて追加してください。
4. 環境変数設定
   - リポジトリルートに .env を置くと自動で読み込まれます（優先順位: OS 環境変数 > .env.local > .env）。
   - テスト等で自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
   - 例 (.env):
     JQUANTS_REFRESH_TOKEN=your_refresh_token
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C00000000
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
5. データベース初期化
   - プロジェクトに提供される schema/init スクリプト（kabusys.data.schema.init_schema 等）で DuckDB スキーマを初期化してください。
   - バックテスト等は prices_daily, features, ai_scores, market_regime, market_calendar テーブルが事前に整っている必要があります。

## 使い方（代表的な操作・コマンド）
- バックテスト（CLI）
  - 必要条件: DuckDB ファイルに最低限のデータがあること
  - 実行例:
    python -m kabusys.backtest.run \
      --start 2023-01-01 --end 2024-12-31 \
      --cash 10000000 --db path/to/kabusys.duckdb
  - オプション: --slippage, --commission, --allocation-method, --max-positions など多数（help を参照）

- 特徴量作成（DuckDB 接続がある前提）
  - Python スクリプト例:
    from datetime import date
    import duckdb
    from kabusys.strategy import build_features
    conn = duckdb.connect("path/to/kabusys.duckdb")
    cnt = build_features(conn, target_date=date(2024, 1, 31))
    conn.close()
    print("upserted:", cnt)

- シグナル生成
  - 例:
    from datetime import date
    import duckdb
    from kabusys.strategy import generate_signals
    conn = duckdb.connect("path/to/kabusys.duckdb")
    n = generate_signals(conn, target_date=date(2024, 1, 31))
    conn.close()
    print("signals:", n)

- ニュース収集（RSS）
  - 例:
    from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
    import duckdb
    conn = duckdb.connect("path/to/kabusys.duckdb")
    known_codes = {"7203", "6758", ...}  # stocks テーブル等から作る
    results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
    conn.close()
    print(results)

- J-Quants データ取得
  - fetch_daily_quotes / fetch_financial_statements / fetch_listed_info 等の API を呼び、save_* 関数で DuckDB に永続化します。
  - トークンは settings.jquants_refresh_token に依存。自動リフレッシュ・リトライ・レート制御を実装済み。

## 実装上のポイント・注意点
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml を探索）を基準に行われます。テスト等で無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- J-Quants クライアントはページネーション、401 自動リフレッシュ、指数バックオフを備えています。
- ニュース収集は SSRF 対策、gzip 解凍サイズチェック、XML パースの安全ライブラリ（defusedxml）を使用しています。
- バックテストは実データをコピーしてインメモリ DuckDB 接続を構築し、実 DB を汚さずに実行します。
- 多くの DB 操作は冪等（DELETE/INSERT の日付単位置換、ON CONFLICT）を意識して実装されています。

## ディレクトリ構成（主要ファイル）
例: src/kabusys 以下の主要モジュール

- kabusys/
  - __init__.py
  - config.py
  - data/
    - jquants_client.py
    - news_collector.py
    - (schema / calendar_management 等の補助モジュール想定)
  - research/
    - factor_research.py
    - feature_exploration.py
  - strategy/
    - feature_engineering.py
    - signal_generator.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - backtest/
    - engine.py
    - simulator.py
    - metrics.py
    - run.py (CLI)
    - clock.py
  - execution/          (発注/実行層: 空または別ファイル)
  - monitoring/         (監視・アラート用モジュール: 想定)

（実際のファイル群はリポジトリにあるソースを参照してください。上は代表的なファイル一覧です）

## 開発上のヒント
- DuckDB を用いたローカル開発が中心になります。大量の歴史データを扱う場合はファイル I/O とクエリの最適化に注意してください。
- `KABUSYS_ENV` による動作モード切替（development / paper_trading / live）を活用して、安全に本番 API 呼び出しを制御してください。
- テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使って環境の差し替えを容易にできます。

---

不明点や README に追加したいサンプル（具体的な .env.example、requirements.txt の想定内容、schema 初期化手順の詳細など）があれば教えてください。必要に応じて README を補完します。