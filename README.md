KabuSys
======

日本株向けの自動売買 / 研究プラットフォームの軽量実装（ライブラリ）。  
バックテストフレームワーク、ファクター計算、シグナル生成、データ収集（J‑Quants / RSS）などの主要機能をモジュール化しています。

主な用途
- 研究（ファクター計算・特徴量探索）
- 日次バッチでの features / signals 生成
- DuckDB を用いたデータパイプライン（raw_prices / prices_daily / features / ai_scores 等）
- バックテスト（擬似約定モデル付き）
- ニュース収集（RSS -> raw_news / news_symbols）
- J-Quants API クライアント（株価・財務データ・市場カレンダー取得）

特徴
- DuckDB を中心とした軽量なローカルデータ格納
- ルックアヘッドバイアス防止を意識した設計（fetched_at など）
- 冪等（UPSERT / ON CONFLICT）での DB 保存
- バックテストはメモリ内シミュレータで完結
- RSS 収集での SSRF / XML 関連対策（SSRF 検査・defusedxml 使用）
- J-Quants API 呼び出しにおけるレートリミット・リトライ・トークン自動更新対応

機能一覧
- kabusys.config
  - .env 自動読み込み（プロジェクトルート検出） / 環境変数ラッパー（Settings）
- kabusys.data
  - jquants_client: J-Quants API の取得 / DuckDB への保存ユーティリティ
  - news_collector: RSS 取得・正規化・raw_news 保存・銘柄抽出
  - （schema / calendar などデータ周りの補助モジュールを想定）
- kabusys.research
  - factor_research: momentum / volatility / value などの定量ファクター計算
  - feature_exploration: IC / forward returns / 統計サマリー
- kabusys.strategy
  - feature_engineering.build_features: features テーブル作成（正規化・クリップ含む）
  - signal_generator.generate_signals: features + ai_scores から BUY/SELL シグナル生成
- kabusys.portfolio
  - portfolio_builder.select_candidates / calc_equal_weights / calc_score_weights
  - position_sizing.calc_position_sizes（等配分・スコア基準・リスク基準）
  - risk_adjustment.apply_sector_cap / calc_regime_multiplier
- kabusys.backtest
  - engine.run_backtest: DuckDB からインメモリコピーしてバックテスト実行
  - simulator.PortfolioSimulator: 擬似約定・履歴管理
  - metrics.calc_metrics: バックテスト評価指標算出
  - CLI: python -m kabusys.backtest.run（start/end/db 等の引数）
- その他
  - news_collector.fetch_rss / save_raw_news / extract_stock_codes
  - jquants_client.fetch_daily_quotes / save_daily_quotes / fetch_financial_statements / save_financial_statements / fetch_market_calendar / save_market_calendar
  - 自動環境ロードは .env / .env.local（OS 環境 > .env.local > .env）を採用。無効化フラグあり。

前提・要件
- Python 3.10 以上（| 型・match などの構文を含むため）
- 必要パッケージ例（プロジェクトの requirements.txt に依存）:
  - duckdb
  - defusedxml
  - （標準ライブラリ以外の依存は実装に応じて追加）
- J-Quants API を使う場合は有効なリフレッシュトークン
- DuckDB ファイル（スキーマ初期化用の utilities がプロジェクト内にある想定）

環境変数（主に必須）
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABUSYS_ENV — 実行環境（development / paper_trading / live）。省略時は development
- LOG_LEVEL — ログレベル（DEBUG, INFO, ...）
- SLACK_BOT_TOKEN — Slack 通知用の bot token（必須）
- SLACK_CHANNEL_ID — Slack チャネル ID（必須）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト data/monitoring.db）
自動 .env 読み込み:
- プロジェクトルートに .env / .env.local があれば自動で読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。

セットアップ手順（例）
1. リポジトリをクローン
   - git clone <repo>
2. Python 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install -U pip
   - pip install duckdb defusedxml
   - （プロジェクトの requirements.txt / pyproject.toml があればそれに従ってください）
4. パッケージを編集可能モードでインストール（任意）
   - pip install -e .
5. 環境変数設定
   - プロジェクトルートに .env を作成（.env.example を参照する想定）
   - 例:
     - JQUANTS_REFRESH_TOKEN=xxxx
     - KABU_API_PASSWORD=yyyy
     - SLACK_BOT_TOKEN=zzz
     - SLACK_CHANNEL_ID=C12345678
6. DuckDB スキーマ初期化
   - プロジェクト内のデータスキーマ初期化関数（kabusys.data.schema.init_schema）を使って DB を作成してください。
     例（Python REPL）:
       from kabusys.data.schema import init_schema
       conn = init_schema("data/kabusys.duckdb")
       conn.close()
   - （実装によっては init_schema(":memory:") が使用可能）

使い方（主要な操作例）
- J-Quants から株価を取得して保存（簡易）
  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes, get_id_token
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")
  token = get_id_token()  # settings.jquants_refresh_token を利用
  records = fetch_daily_quotes(id_token=token, date_from=..., date_to=...)
  save_daily_quotes(conn, records)

- features のビルド（DuckDB 接続と日付を渡す）
  from kabusys.strategy.feature_engineering import build_features
  from kabusys.data.schema import init_schema
  from datetime import date
  conn = init_schema("data/kabusys.duckdb")
  count = build_features(conn, target_date=date(2024, 1, 31))
  conn.close()

- シグナル生成
  from kabusys.strategy.signal_generator import generate_signals
  conn = init_schema("data/kabusys.duckdb")
  n = generate_signals(conn, target_date=date(2024,1,31), threshold=0.6)
  conn.close()

- バックテスト（CLI）
  python -m kabusys.backtest.run \
    --start 2023-01-01 --end 2024-12-31 \
    --db data/kabusys.duckdb \
    --cash 10000000 --allocation-method risk_based --lot-size 100
  主なオプション: --start, --end, --db, --cash, --slippage, --commission,
  --allocation-method (equal|score|risk_based), --max-utilization, --max-positions, --risk-pct, --stop-loss-pct

- ニュース収集（RSS）
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")
  res = run_news_collection(conn, sources=None, known_codes={'7203','6758'}, timeout=30)
  conn.close()

注意点 / 運用上のヒント
- Look-ahead バイアスを避けるため、バックテストでは事前に取得された（バックテスト期間以前の）stocks / raw_prices / raw_financials 等を用意してください。
- generate_signals は market_regime / features / ai_scores / positions を参照します。必要データがないと BUY が発生しない/SELL のみ発生することがあります。
- .env 読み込みはプロジェクトルート（.git または pyproject.toml を基準）から行われます。CI やテスト時に自動読み込みを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- news_collector は外部ネットワークアクセスを行います。SSRF・XML 脆弱性対策を組み込んでいますが、運用上はアクセス先・ネットワークルールに注意してください。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py             — パッケージ定義
  - config.py               — 環境変数 / .env ローダー / Settings
  - data/
    - jquants_client.py     — J-Quants API クライアント（取得＋保存）
    - news_collector.py     — RSS 収集・整形・DB 保存
    - (schema.py, calendar_management など想定)
  - research/
    - factor_research.py    — モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py— 将来リターン / IC / summary
  - strategy/
    - feature_engineering.py— features 作成（正規化・クリップ・UPSERT）
    - signal_generator.py   — final_score 計算と signals テーブル生成
  - portfolio/
    - portfolio_builder.py  — 候補選定・重み計算
    - position_sizing.py    — 発注株数計算・集計キャップ
    - risk_adjustment.py    — セクター上限・レジーム乗数
    - __init__.py
  - backtest/
    - engine.py             — run_backtest 実装（ループ／データコピー）
    - simulator.py          — PortfolioSimulator（擬似約定 / history / trades）
    - metrics.py            — バックテスト評価指標
    - run.py                — CLI エントリポイント
    - clock.py              — SimulatedClock（将来拡張用）
  - execution/              — 実行層（発注）用パッケージ（空実装含む）
  - monitoring/            — 監視・メトリクス用（実装想定）

貢献・拡張案
- 銘柄ごとの lot_size マスタを導入して position_sizing を拡張
- AI スコア取り込みパイプライン（ai_scores 更新）の追加
- 分足シミュレーション / マイクロバーチャルタイムのサポート
- Slack 通知 / 監視ダッシュボードの実装（monitoring 層）

ライセンス / 注意
- 本 README はコードベースに基づく簡易説明です。実運用する際は各モジュールの実装・ログ出力・例外処理・セキュリティ周りを十分にレビューしてください。
- 実際の取引に利用する場合、API 利用規約と法規制に従い、十分なテストとリスク管理を行ってください。

以上。補足で README に追記したい項目（例: requirements, .env.example の内容、DB スキーマ定義等）があれば教えてください。