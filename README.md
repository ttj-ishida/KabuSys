KabuSys
======

日本株向けの自動売買・データプラットフォーム用 Python ライブラリ群です。  
データ取得（J-Quants）、ETL、特徴量作成、シグナル生成、バックテスト、ニュース収集、簡易シミュレータなどを含み、DuckDB をデータストアとして利用します。

概要
----
KabuSys は「データ層（Raw → Processed → Feature）」「戦略層」「実行層」「バックテスト層」を分離した設計の日本株自動売買システム基盤です。  
主に以下を提供します。

- J-Quants API からの株価・財務・マーケットカレンダー取得クライアント（レート制限・リトライ・トークンリフレッシュ対応）
- DuckDB ベースのスキーマ定義・初期化・永続化ユーティリティ
- ETL パイプライン（差分取得・品質チェック・冪等保存）
- ニュース（RSS）収集・前処理・銘柄紐付け
- 研究用ファクター計算（モメンタム、ボラティリティ、バリュー等）
- 特徴量正規化・features テーブルへの保存
- シグナル生成（ファクター + AI スコアの統合、売買・エグジットロジック）
- バックテストエンジン（シミュレータ、評価指標）
- バックテスト用 CLI エントリポイント

主な機能一覧
--------------
- data/
  - jquants_client: J-Quants API クライアント（ページング、リトライ、レート制御、id token 自動更新）
  - news_collector: RSS 取得・正規化・raw_news への保存、銘柄抽出（SSRF 対策・gzip 上限等）
  - schema: DuckDB スキーマ定義・init_schema() による初期化
  - stats: Z スコア正規化などの統計ユーティリティ
  - pipeline: ETL ジョブ（差分取得、バックフィル、品質チェックのラッパ）
- research/
  - factor_research: momentum / volatility / value 等のファクター計算
  - feature_exploration: 将来リターン計算、IC（Spearman）計算、統計サマリ
- strategy/
  - feature_engineering: 生ファクターの正規化・ユニバースフィルタ・features への UPSERT
  - signal_generator: features と ai_scores を統合して BUY/SELL シグナルを生成、signals テーブルへ書き込み
- backtest/
  - engine: run_backtest() による日次バックテストループ（インメモリ DuckDB を構築）
  - simulator: 擬似約定（スリッページ・手数料）とポートフォリオ状態管理
  - metrics: バックテスト評価指標計算（CAGR, Sharpe, MaxDD, WinRate, PayoffRatio）
  - run: CLI エントリポイント（python -m kabusys.backtest.run）
- execution/ monitoring/
  - 将来の実取引・監視機能を想定したパッケージ（現状モジュール分割）

セットアップ手順
----------------

1. 必要な Python バージョン
   - Python 3.10 以上（型注釈で | 記法を利用）

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージのインストール（最低限）
   - pip install duckdb defusedxml
   - プロジェクトをパッケージとして扱う場合:
     - pip install -e .

   （本リポジトリの要件ファイルがあればそれに従ってください。Slack 連携など別途 SDK が必要な機能がある場合は追加してください。）

4. 環境変数設定
   - ルートに .env / .env.local を配置することで自動読み込みされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 読み込み優先順: OS 環境変数 > .env.local > .env
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（jquants_client で使用）
     - KABU_API_PASSWORD     : kabuステーション API のパスワード（実行層用）
     - SLACK_BOT_TOKEN       : Slack 通知用（必要時）
     - SLACK_CHANNEL_ID      : Slack 通知先チャンネル ID
   - オプション:
     - KABUSYS_ENV (development | paper_trading | live) 既定: development
     - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) 既定: INFO
     - DUCKDB_PATH (デフォルト data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト data/monitoring.db)

5. DuckDB スキーマ初期化
   - Python REPL またはスクリプトで:
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     conn.close()
   - インメモリ DB を使う場合: init_schema(":memory:")

使い方（代表的なワークフロー）
----------------------------

- 1) データ取得（ETL）
  - J-Quants から差分取得して保存する（例）:
    from datetime import date
    from kabusys.data.schema import init_schema
    from kabusys.data.pipeline import run_prices_etl
    conn = init_schema("data/kabusys.duckdb")
    res = run_prices_etl(conn, target_date=date.today())
    print(res.to_dict())
    conn.close()
  - jquants_client の低レイヤ関数を直接使うことも可能:
    from kabusys.data import jquants_client as jq
    rows = jq.fetch_daily_quotes(date_from=..., date_to=...)
    saved = jq.save_daily_quotes(conn, rows)

- 2) ニュース収集
  - RSS 収集と DB 保存:
    from kabusys.data.news_collector import run_news_collection
    conn = init_schema("data/kabusys.duckdb")
    results = run_news_collection(conn, sources=None, known_codes=set_of_codes)
    conn.close()

- 3) 特徴量構築
  - DuckDB 接続と日付を渡して features を構築:
    from datetime import date
    from kabusys.data.schema import init_schema
    from kabusys.strategy import build_features
    conn = init_schema("data/kabusys.duckdb")
    count = build_features(conn, target_date=date(2024, 1, 31))
    print(f"features upserted: {count}")
    conn.close()

- 4) シグナル生成
  - features / ai_scores / positions を参照して signals を生成:
    from datetime import date
    from kabusys.data.schema import init_schema
    from kabusys.strategy import generate_signals
    conn = init_schema("data/kabusys.duckdb")
    total = generate_signals(conn, target_date=date(2024,1,31))
    print(f"signals written: {total}")
    conn.close()

- 5) バックテスト（CLI）
  - CLI から実行:
    python -m kabusys.backtest.run \
      --start 2023-01-01 --end 2024-12-31 \
      --cash 10000000 --db data/kabusys.duckdb
  - Python API:
    from datetime import date
    from kabusys.data.schema import init_schema
    from kabusys.backtest.engine import run_backtest
    conn = init_schema("data/kabusys.duckdb")
    result = run_backtest(conn, start_date=date(2023,1,1), end_date=date(2024,12,31))
    print(result.metrics)
    conn.close()

- 6) バックテスト出力
  - run_backtest は BacktestResult を返し、history（DailySnapshot）、trades（TradeRecord）、metrics（BacktestMetrics）を利用できます。

環境変数・設定について（詳細）
------------------------------
- 自動ロード:
  - パッケージの config モジュールはプロジェクトルート（.git または pyproject.toml があるディレクトリ）を起点に .env / .env.local を自動読み込みします。
  - テストや特殊用途で自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- settings（kabusys.config.settings）で以下のプロパティが利用可能:
  - jquants_refresh_token / kabu_api_password / kabu_api_base_url
  - slack_bot_token / slack_channel_id
  - duckdb_path / sqlite_path
  - env / log_level / is_live / is_paper / is_dev

ディレクトリ構成
----------------
（主要ファイルのみ抜粋）

src/kabusys/
- __init__.py
- config.py
- data/
  - __init__.py
  - jquants_client.py
  - news_collector.py
  - pipeline.py
  - schema.py
  - stats.py
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- strategy/
  - __init__.py
  - feature_engineering.py
  - signal_generator.py
- backtest/
  - __init__.py
  - engine.py
  - simulator.py
  - metrics.py
  - clock.py
  - run.py
- execution/
  - __init__.py
- monitoring/
  - （将来の監視機能用）

設計上の注意点・ポリシー
-----------------------
- 冪等性: DB への保存は ON CONFLICT / UPSERT を多用し、再実行可能性を重視しています。
- ルックアヘッドバイアスの回避: 戦略/研究モジュールは target_date 時点で利用可能なデータのみを参照する方針です。
- セキュリティ: news_collector は SSRF 対策、XML パースに defusedxml を利用、応答サイズ上限などを実装しています。
- レート制御: J-Quants クライアントは固定間隔のスロットリングとリトライ（指数バックオフ）を実装しています。
- テスト容易性: 多くの関数は id_token や接続オブジェクトを外部注入できるよう設計されています（モックが容易）。

よくある実行例
--------------
- DB 初期化:
  python -c "from kabusys.data.schema import init_schema; init_schema('data/kabusys.duckdb')"
- 簡易バックテスト:
  python -m kabusys.backtest.run --start 2023-01-01 --end 2023-12-31 --db data/kabusys.duckdb

拡張・運用
----------
- 実取引接続（kabu API）や Slack 通知などは設定・実装を追加することで対応可能です（必要な環境変数は config で要求されます）。
- production 用には KABUSYS_ENV を適切に設定（paper_trading / live）し、ログレベルや DB パスを調整してください。
- 大量データ取得時は J-Quants のレート制限（120 req/min）に留意してください。

フィードバック / 開発
---------------------
- 新機能追加やバグ報告は Issue / PR を通じて行ってください。テストとドキュメントの追加を歓迎します。

付録：便利な参照 API
--------------------
- DuckDB スキーマ初期化: kabusys.data.schema.init_schema(db_path)
- J-Quants: kabusys.data.jquants_client.fetch_daily_quotes / save_daily_quotes
- ニュース: kabusys.data.news_collector.fetch_rss / save_raw_news / run_news_collection
- 特徴量: kabusys.strategy.build_features(conn, target_date)
- シグナル生成: kabusys.strategy.generate_signals(conn, target_date)
- バックテスト実行: kabusys.backtest.engine.run_backtest(...), CLI: python -m kabusys.backtest.run

以上。README の内容に関して補足や特定の使い方（例: 実データでの ETL スケジュール、Docker 化、CI/CD の設定等）をご希望であれば教えてください。