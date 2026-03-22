KabuSys — 日本株自動売買システム
==============================

概要
----
KabuSys は日本株向けの自動売買／リサーチ基盤ライブラリです。  
主な目的は以下のとおりです。

- J-Quants 等の外部データソースから市場データ・財務データ・ニュースを取得・保存
- DuckDB を用いたデータレイク（Raw / Processed / Feature / Execution 層）
- ファクター計算（Momentum / Volatility / Value など）と特徴量生成
- シグナル生成（BUY/SELL）ロジック
- バックテストフレームワーク（シミュレーション・メトリクス算出）
- ニュース収集と銘柄紐付け（RSS → raw_news, news_symbols）
- ETL パイプラインと品質チェック（差分取得・再取得戦略）

本リポジトリは主にライブラリとして設計されており、モジュール単位で ETL / バックテスト / 戦略構成を呼び出して利用します。

主な機能
--------
- データ取得/保存
  - J-Quants API クライアント（fetch / save：日足・財務・カレンダー）
  - RSS ニュース取得とニュース→銘柄紐付け（安全対策・SSRF 対応）
  - DuckDB スキーマ定義 & 初期化（init_schema）
- データ処理 / 研究
  - ファクター計算（calc_momentum, calc_volatility, calc_value）
  - 特徴量正規化（zscore 正規化）と features テーブル構築（build_features）
  - 研究用ユーティリティ（forward returns, IC, summary 等）
- 戦略 / シグナル
  - features + ai_scores を統合した final_score 計算
  - BUY/SELL シグナル生成と signals テーブルへの書き込み（generate_signals）
  - Bear レジーム抑制、重み調整、エグジット条件（ストップロス等）
- バックテスト
  - 日次ループのポートフォリオシミュレータ（スリッページ・手数料も考慮）
  - run_backtest によるバックテスト実行、メトリクス算出（CAGR, Sharpe, MaxDD 等）
  - CLI エントリポイント（python -m kabusys.backtest.run）
- ETL / パイプライン
  - 差分取得・バックフィル戦略、品質チェック、冪等保存（ON CONFLICT を利用）

セットアップ手順
----------------

前提
- Python 3.10 以上（型記法や union 型（A | B）を利用しているため）
- DuckDB を使用するためネイティブバイナリが必要

インストール（開発環境）
1. 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - 最低依存（例）:
     - duckdb
     - defusedxml
   例:
     pip install duckdb defusedxml

   ※ 実際の requirements.txt がある場合はそれを使ってください:
     pip install -r requirements.txt

3. 開発インストール（パッケージとして使う場合）
   pip install -e .

環境変数 / .env
- 設定は環境変数またはプロジェクトルートの .env / .env.local から自動読み込みされます。
- 自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

主な環境変数
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD      : kabuステーション API パスワード（必須）
- KABUS_API_BASE_URL     : kabu API ベース URL（省略時 "http://localhost:18080/kabusapi"）
- SLACK_BOT_TOKEN        : Slack 通知用 bot トークン（必須）
- SLACK_CHANNEL_ID       : Slack チャンネル ID（必須）
- DUCKDB_PATH            : DuckDB ファイルパス（省略時 data/kabusys.duckdb）
- SQLITE_PATH            : SQLite（監視用 DB）パス（省略時 data/monitoring.db）
- KABUSYS_ENV            : environment ('development' / 'paper_trading' / 'live')（省略時 development）
- LOG_LEVEL              : ログレベル（'DEBUG','INFO',...）（省略時 INFO）

設定クラス
- kabusys.config.settings オブジェクト経由でアクセス可能（プロパティで必須チェックを行います）。

使い方（例）
------------

1) DuckDB スキーマ初期化
- Python REPL / スクリプトで:
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")

- メモリ DB:
  conn = init_schema(":memory:")

2) J-Quants から日足を取得して保存
  from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes, save_daily_quotes
  token = get_id_token()  # settings.jquants_refresh_token を使用
  records = fetch_daily_quotes(id_token=token, date_from=..., date_to=...)
  saved = save_daily_quotes(conn, records)

3) ニュース収集（RSS）と保存
  from kabusys.data.news_collector import run_news_collection
  # known_codes は抽出対象の有効な銘柄コードセット（省略可能）
  res = run_news_collection(conn, sources=None, known_codes=set(["7203","6758"]), timeout=30)

4) 特徴量構築（features）
  from kabusys.strategy import build_features
  from datetime import date
  n = build_features(conn, target_date=date(2024, 1, 5))
  # features テーブルに target_date 分が書き込まれます（冪等）

5) シグナル生成
  from kabusys.strategy import generate_signals
  cnt = generate_signals(conn, target_date=date(2024,1,5), threshold=0.6)
  # signals テーブルに BUY / SELL が書き込まれます

6) バックテスト（ライブラリ呼び出し）
  from kabusys.backtest.engine import run_backtest
  from kabusys.data.schema import get_connection
  conn = get_connection("data/kabusys.duckdb")
  result = run_backtest(conn, start_date, end_date, initial_cash=10_000_000)
  # result.history / result.trades / result.metrics を参照

7) バックテスト CLI
  python -m kabusys.backtest.run --start 2023-01-01 --end 2024-12-31 --db data/kabusys.duckdb

注意点・設計上の指針
- 多くの DB 操作は冪等（ON CONFLICT / トランザクション）を前提としているため、定期実行ジョブで安全に再実行可能です。
- ルックアヘッドバイアス防止のため、各計算は target_date 時点で利用可能な情報のみに基づいて実施するよう設計されています。
- ニュース収集は SSRF 対策・受信サイズ上限・XML の安全パース（defusedxml）を組み込んでいます。
- J-Quants クライアントはレートリミット（120 req/min）、リトライ、401 時の自動トークンリフレッシュに対応しています。

ディレクトリ構成
----------------
主要モジュールの配置（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py                    -- 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py          -- J-Quants API クライアント + 保存ロジック
    - news_collector.py          -- RSS フェッチ・記事保存・銘柄抽出
    - schema.py                  -- DuckDB スキーマ定義・初期化
    - stats.py                   -- zscore 等統計ユーティリティ
    - pipeline.py                -- ETL パイプライン（差分取得等）
  - research/
    - __init__.py
    - factor_research.py         -- 各種ファクター計算
    - feature_exploration.py     -- forward returns / IC / summary 等
  - strategy/
    - __init__.py
    - feature_engineering.py     -- features 構築（正規化・ユニバースフィルタ等）
    - signal_generator.py        -- final_score 計算・BUY/SELL 生成
  - backtest/
    - __init__.py
    - engine.py                  -- run_backtest 等
    - simulator.py               -- PortfolioSimulator（約定・時価評価）
    - metrics.py                 -- バックテスト評価指標
    - run.py                     -- CLI エントリポイント
    - clock.py                   -- 模擬時計（将来拡張用）
  - execution/
    - __init__.py                -- 発注関連（現時点は空のパッケージ）
  - monitoring/                  -- 監視・Slack 通知等（将来項目）

（上記は主要ファイルのみ抜粋しています。詳細は src/kabusys 以下のソースを参照してください。）

開発・運用に関する補足
---------------------
- ログ: logging ベースで出力されます。LOG_LEVEL 環境変数で制御可能。
- テスト: 各モジュールは外部依存を注入できるデザイン（id_token 注入、_urlopen のモック等）になっておりユニットテストが容易です。
- 本番運用: KABUSYS_ENV による環境分岐（development / paper_trading / live）をサポート。
- DB バックアップ: DuckDB ファイルは定期的にバックアップを推奨します。

貢献
----
バグ報告やプルリクエストは歓迎します。コードスタイル・型アノテーション・ログ出力を整えた PR をお願いします。

ライセンス
---------
（ここにライセンス情報を記載してください。リポジトリに LICENSE がある場合はそちらに従ってください。）

---

この README はコードベース（src/kabusys 以下）を基に作成しています。使い方や API の詳細は該当モジュールの docstring を参照してください。何か追加で README に入れたい情報（例: CI 設定、具体的な ETL スケジュール例、運用手順など）があれば教えてください。