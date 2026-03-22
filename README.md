KabuSys — 日本株自動売買システム
================================

このリポジトリは、日本株のデータ取得・特徴量生成・シグナル生成・バックテスト・簡易実行レイヤを含む自動売買フレームワーク（実験/研究〜運用を想定）です。  
コードは主に DuckDB をデータ層として利用し、J-Quants API / RSS ニュース / kabu ステーション等との連携を想定したモジュール群で構成されています。

主な特徴
--------

- データ収集（J-Quants API）と保存（DuckDB）を行うクライアント／ETL
  - 差分更新、ページネーション、リトライ、レート制御、トークン自動更新
- ニュース収集（RSS）と記事 → 銘柄紐付け機能（SSRF対策・前処理・重複除去）
- 研究用ファクター計算（モメンタム／ボラティリティ／バリュー）
- 特徴量エンジニアリング（正規化・ユニバースフィルタ・features テーブルへの保存）
- シグナル生成（features + AI スコア統合、BUY/SELL 生成、Bear レジーム抑制）
- バックテストフレームワーク（シミュレータ、メトリクス計算、バックテスト実行 CLI）
- 実行レイヤー（スキーマ／orders/trades/positions 等のテーブル定義を含む）

機能一覧（モジュール別）
------------------------

- kabusys.config
  - 環境変数/.env の自動ロードと Settings クラス（必須トークン等の取得）
  - 主要環境変数: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV, LOG_LEVEL
- kabusys.data.jquants_client
  - J-Quants API との通信、取得関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）
  - レート制御、リトライ、トークン管理、DuckDB へ冪等保存（save_*）
- kabusys.data.news_collector
  - RSS フィード取得、前処理、raw_news 保存、銘柄コード抽出・news_symbols 保存
  - SSRF 対策、gzip 上限、XML 解析の堅牢化
- kabusys.data.schema
  - DuckDB のスキーマ定義（raw / processed / feature / execution 層）
  - init_schema(db_path) で初期化、get_connection で接続取得
- kabusys.data.pipeline
  - ETL 管理（差分更新、バックフィル、品質チェックフレーム）
  - run_prices_etl / run_news_collection 等（ETLResult にて結果を返却）
- kabusys.research
  - ファクター計算（calc_momentum / calc_volatility / calc_value）
  - 研究用ユーティリティ（calc_forward_returns, calc_ic, factor_summary, rank）
- kabusys.strategy
  - feature_engineering.build_features(conn, target_date)
  - signal_generator.generate_signals(conn, target_date, ...)
- kabusys.backtest
  - engine.run_backtest(...)：DuckDB からインメモリ DB にデータをコピーして日次シミュレーション
  - simulator.PortfolioSimulator：擬似約定 / ポートフォリオ管理（スリッページ・手数料モデル）
  - metrics.calc_metrics：バックテスト評価指標（CAGR, Sharpe, MaxDD, Win Rate 等）
  - CLI: python -m kabusys.backtest.run (開始/終了日や初期資金等を指定可能)

セットアップ手順
---------------

前提
- Python 3.9+ を推奨（typing の記法を利用）
- DuckDB を使用（Python パッケージ duckdb）
- RSS XML の安全なパースに defusedxml を使用

1. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  または  .venv\Scripts\activate

2. 必要パッケージをインストール
   - pip install duckdb defusedxml
   - （必要に応じて logging など標準以外の依存があれば追加）

3. プロジェクトルートに .env を作成（任意）
   - .env / .env.local を用いて環境変数を管理できます。自動ロードは kabusys.config が行います（プロジェクトルートは .git または pyproject.toml によって検出）。
   - 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

例: .env の内容（最低限）
- JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
- KABU_API_PASSWORD=your_kabu_password
- SLACK_BOT_TOKEN=xoxb-...
- SLACK_CHANNEL_ID=C01234567
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- KABUSYS_ENV=development
- LOG_LEVEL=INFO

DB 初期化
- Python REPL またはスクリプトで schema を初期化:
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")
  conn.close()

使い方（例）
------------

1) DuckDB スキーマ初期化（既出）
- from kabusys.data.schema import init_schema
- conn = init_schema("data/kabusys.duckdb")

2) J-Quants から株価を取得して保存（ETL の一部）
- from kabusys.data import jquants_client as jq
- from kabusys.data.schema import init_schema
- conn = init_schema("data/kabusys.duckdb")
- records = jq.fetch_daily_quotes()  # 環境変数により自動的にトークンが取得されます
- saved = jq.save_daily_quotes(conn, records)

3) ニュース収集
- from kabusys.data.news_collector import run_news_collection
- conn = init_schema("data/kabusys.duckdb")
- results = run_news_collection(conn, sources=None, known_codes=set_of_codes)

4) 特徴量構築（features テーブル作成）
- from kabusys.strategy import build_features
- from kabusys.data.schema import init_schema
- from datetime import date
- conn = init_schema("data/kabusys.duckdb")
- count = build_features(conn, target_date=date(2024, 01, 31))

5) シグナル生成
- from kabusys.strategy import generate_signals
- count = generate_signals(conn, target_date=date(2024, 01, 31), threshold=0.6)

6) バックテスト（CLI）
- DB は prices_daily, features, ai_scores, market_regime, market_calendar が揃っている必要があります
- 実行例:
  python -m kabusys.backtest.run \
    --start 2023-01-01 --end 2023-12-31 \
    --cash 10000000 --db data/kabusys.duckdb

  主なオプション:
  - --start / --end : YYYY-MM-DD（必須）
  - --cash : 初期資金（JPY）
  - --slippage : スリッページ率（デフォルト 0.001）
  - --commission : 手数料率（デフォルト 0.00055）
  - --max-position-pct : 1銘柄あたり最大ポジション比率（デフォルト 0.20）
  - --db : DuckDB ファイルパス（必須）

7) Python API でバックテストを呼び出す
- from kabusys.backtest.engine import run_backtest
- from kabusys.data.schema import init_schema
- conn = init_schema("data/kabusys.duckdb")
- result = run_backtest(conn, start_date, end_date, initial_cash=10_000_000)
- result.history, result.trades, result.metrics を利用

注意・運用上のポイント
--------------------

- 環境（KABUSYS_ENV）は development / paper_trading / live のいずれかで、Settings.env で検証されます。live は実発注運用を想定した安全確認が必要です。
- 機密情報（API トークン等）は .env で管理し、リポジトリに含めないでください。
- J-Quants API のレート制限（120 req/min）や RSS の取得サイズ上限等、安全性・耐障害性に配慮した実装になっていますが、実際の運用時はログ監視・アラート・モニタリングを推奨します。
- DuckDB スキーマは冪等に作成されますが、製造/運用用のマイグレーションが必要な場合は別途対応してください。

ディレクトリ構成（抜粋）
----------------------

src/kabusys/
- __init__.py
- config.py                 — 環境設定 / .env ロード
- data/
  - __init__.py
  - jquants_client.py       — J-Quants API クライアント & 保存
  - news_collector.py       — RSS 取得 / raw_news 保存 / 銘柄抽出
  - pipeline.py             — ETL 管理（差分取得等）
  - schema.py               — DuckDB スキーマ定義・初期化
  - stats.py                — zscore_normalize 等ユーティリティ
- research/
  - __init__.py
  - factor_research.py      — momentum/volatility/value の計算
  - feature_exploration.py  — forward returns, IC, factor summary
- strategy/
  - __init__.py
  - feature_engineering.py  — features テーブル生成
  - signal_generator.py     — final_score 計算と signals 生成
- backtest/
  - __init__.py
  - engine.py               — run_backtest の本体
  - simulator.py            — PortfolioSimulator, TradeRecord, DailySnapshot
  - metrics.py              — バックテスト評価指標
  - run.py                  — CLI エントリポイント
  - clock.py                — 将来拡張用の模擬時計
- execution/                 — 発注周り（プレースホルダ／拡張用）
- monitoring/                — モニタリング用（未実装ファイルがある場合あり）

貢献・開発
----------

- コードベースはテスト可能な関数分割を意識して設計されています。ユニットテストを追加する際は、ネットワーク呼び出し（_request / _urlopen など）をモックすると容易です。
- 開発中に .env の自動ロードが邪魔な場合は、環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

ライセンス
----------

- リポジトリ内に LICENSE ファイルが無ければ、導入先のポリシーに従って追加してください。

補足
----

本 README はソースコードのコメントと公開 API を基に作成しています。実運用前に各モジュール（特に実際の発注・kabu 接続部分）について十分なテストとセキュリティレビューを行ってください。不明点や追加したい使用例があれば教えてください。