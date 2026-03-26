KabuSys
=======

概要
----
KabuSys は日本株の自動売買・研究・バックテストを支援する Python コードベースです。  
主に以下のレイヤで構成され、DuckDB をデータ層として想定した設計になっています。

- データ収集（J-Quants API / RSS ニュース）
- 研究（ファクター計算、特徴量探索）
- 特徴量エンジニアリング / シグナル生成
- ポートフォリオ構築（候補選定、重み付け、サイジング、リスク調整）
- バックテスト（シミュレータ、評価指標）
- 実運用（execution）・監視（monitoring）用の雛形

本 README はリポジトリ内の主要モジュールと使い方の概要をまとめたものです。

主な機能
--------
- J-Quants API クライアント（ページネーション、レート制御、トークン自動リフレッシュ、リトライ）
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar / fetch_listed_info
  - DuckDB への冪等保存関数（save_daily_quotes 等）
- RSS ニュース収集（SSRF 対策、サイズ制限、記事ID 正規化、銘柄抽出）
  - fetch_rss / save_raw_news / run_news_collection / extract_stock_codes
- 研究モジュール
  - ファクター計算: calc_momentum, calc_volatility, calc_value
  - 将来リターン・IC 計算・統計サマリー
  - Z スコア正規化ユーティリティを利用
- 特徴量エンジニアリング
  - build_features: 研究データから features テーブルへ書き込み（Z スコア正規化、ユニバースフィルタ等）
- シグナル生成
  - generate_signals: features + ai_scores を統合して final_score を算出、BUY/SELL を signals テーブルへ冪等書き込み
  - Bear レジーム抑制、エグジット（ストップロス / スコア低下）判定
- ポートフォリオ構築
  - 候補選定（select_candidates）
  - 重み計算（等金額 / スコア加重）
  - サイジング（calc_position_sizes）: risk-based / equal / score、単元丸め、aggregate cap 調整
  - リスク調整（apply_sector_cap, calc_regime_multiplier）
- バックテストフレームワーク
  - run_backtest: DuckDB を読み取り、インメモリコピーして日次ループでシミュレーション
  - PortfolioSimulator: 約定ロジック（スリッページ、手数料、部分約定、SELL 先行）
  - メトリクス計算: CAGR、Sharpe、MaxDD、勝率、Payoff Ratio 等
  - CLI エントリポイント: python -m kabusys.backtest.run

セットアップ手順
----------------
1. Python 環境を作成（推奨: venv）
   - 例:
     python -m venv .venv
     source .venv/bin/activate

2. 必要な依存パッケージをインストール
   - 最低限必要なパッケージ:
     - duckdb
     - defusedxml
   - 例:
     pip install duckdb defusedxml

   （プロジェクトに requirements.txt / pyproject.toml があればそちらを使ってください）

3. 環境変数の設定
   - 必須（apps の一部を動かすには必須）:
     - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
     - SLACK_BOT_TOKEN : Slack 通知を使う場合
     - SLACK_CHANNEL_ID : Slack 通知先チャンネルID
     - KABU_API_PASSWORD : kabuステーション API を使う場合
   - 任意 / デフォルトあり:
     - KABUSYS_ENV : development | paper_trading | live （デフォルト: development）
     - LOG_LEVEL : DEBUG | INFO | WARNING | ERROR | CRITICAL （デフォルト: INFO）
     - KABU_API_BASE_URL : kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH : 監視用 SQLite（デフォルト: data/monitoring.db）

   - .env 自動読み込み:
     - プロジェクトルート（.git または pyproject.toml を基準）に .env/.env.local を置くと自動的に読み込みます。
     - 自動読み込みを無効化する場合:
       export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

4. DuckDB スキーマ初期化
   - リポジトリ内に schema 初期化用モジュール（kabusys.data.schema）がある想定です（この README 作成時に一部参照あり）。
   - 既存データベースがない場合は init_schema 等でテーブルを作成してください。

使い方（代表例）
----------------

- バックテスト（CLI）
  - 前提: DuckDB に prices_daily, features, ai_scores, market_regime, market_calendar が整備済みであること
  - 実行例:
    python -m kabusys.backtest.run \
      --start 2023-01-01 --end 2024-12-31 \
      --cash 10000000 --db path/to/kabusys.duckdb

  - 利用可能オプション（主なもの）:
    --slippage / --commission / --max-position-pct / --allocation-method (equal|score|risk_based) / --max-utilization / --max-positions / --risk-pct / --stop-loss-pct / --lot-size

- 特徴量構築（Python REPL）
  from datetime import date
  import duckdb
  from kabusys.strategy.feature_engineering import build_features
  from kabusys.data.schema import init_schema  # schema が提供されている想定

  conn = init_schema("path/to/kabusys.duckdb")
  cnt = build_features(conn, target_date=date(2024, 1, 31))
  print(f"upserted: {cnt}")
  conn.close()

- シグナル生成（Python REPL）
  from datetime import date
  from kabusys.strategy.signal_generator import generate_signals
  conn = init_schema("path/to/kabusys.duckdb")
  n = generate_signals(conn, target_date=date(2024, 1, 31))
  print(f"signals written: {n}")
  conn.close()

- ニュース収集ジョブ
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  conn = init_schema("path/to/kabusys.duckdb")
  known_codes = {"7203", "6758", "9984", ...}  # stocks テーブルなどと合わせる
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
  print(results)
  conn.close()

- J-Quants のデータ取得と保存
  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
  conn = init_schema("path/to/kabusys.duckdb")
  records = fetch_daily_quotes(date_from=date(2023,1,1), date_to=date(2023,12,31))
  saved = save_daily_quotes(conn, records)
  conn.close()

注意点 / 前提
--------------
- Look-ahead バイアス対策:
  - 多くのモジュールが「target_date 時点で利用可能なデータのみ」を参照するよう設計されています（prices_daily の最新日付参照や fetched_at の取り扱いなど）。
- 冪等性:
  - DB への書き込みは原則冪等（DELETE/INSERT の日付単位置換や ON CONFLICT を利用）。
- セキュリティ:
  - news_collector は SSRF / XML BOM / 大容量応答対策を実装しています。
- 実運用（kabu API / 発注）層は本リポジトリ内に基礎的な構造を持ちますが、実際の接続・認証・運用には追加実装・十分なテストが必要です。

ディレクトリ構成（主要ファイル）
-------------------------------
src/kabusys/
- __init__.py
- config.py                         — 環境変数 / 設定読み込み
- data/
  - jquants_client.py               — J-Quants API クライアント / 保存ロジック
  - news_collector.py               — RSS 取得・前処理・DB 保存
  - (schema.py 等: DB 初期化・スキーマ定義を想定)
- research/
  - factor_research.py              — モメンタム / ボラティリティ / バリュー計算
  - feature_exploration.py          — IC / forward returns / 統計サマリー
- strategy/
  - feature_engineering.py          — features を構築して DB に保存
  - signal_generator.py             — final_score 計算と signals 書き込み
- portfolio/
  - portfolio_builder.py            — 候補選定・重み計算
  - position_sizing.py              — サイジング（risk_based / equal / score）
  - risk_adjustment.py              — セクター上限・レジーム乗数
- backtest/
  - engine.py                       — バックテスト全体ループ
  - simulator.py                    — PortfolioSimulator（擬似約定）
  - metrics.py                      — バックテスト評価指標
  - run.py                          — CLI ラッパー
  - clock.py                        — 将来拡張向け模擬時計
- portfolio/ __init__.py
- strategy/ __init__.py
- research/ __init__.py
- backtest/ __init__.py
- execution/                         — 実行層の雛形（空ファイルあり）
- monitoring/                        — 監視層の雛形（公開 API 想定）

補足: 設定キー一覧（主要）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須 if using kabu api)
- KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID (Slack 通知)
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- KABUSYS_ENV (development | paper_trading | live) — 動作モードによる挙動切替
- LOG_LEVEL (ログレベル)

貢献
----
- バグ修正・機能追加は Pull Request を歓迎します。コードの変更はユニットテストとドキュメントの更新を添えてください。
- 実運用での発注ロジック（kabu 接続や注文管理）についてはリスクが伴います。実マネー運用の前に十分なペーパートレード・レビューを行ってください。

ライセンス
----------
- 本リポジトリ内に明示的なライセンス表記がない場合は、利用・配布等についてプロジェクトオーナーに確認してください。

以上が KabuSys の簡易 README です。必要であれば、セットアップの詳細（pyproject.toml / CI / テスト方法）や DuckDB のスキーマ定義（schema.py の内容）を追記します。どの部分を詳しく書き足しましょうか？