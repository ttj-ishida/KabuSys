KabuSys — 日本株自動売買システム
=================================

概要
----
KabuSys は日本株のデータ収集・ファクター生成・シグナル生成・ポートフォリオ構築・バックテストを行うためのライブラリ／フレームワークです。  
モジュール設計により、データ収集（J‑Quants、RSS）、研究（ファクター計算・探索）、戦略（特徴量整形・シグナル生成）、ポートフォリオ構築（サイジング・リスク制御）、バックテスト（擬似約定・評価指標）を分離して実装しています。

主な機能
--------
- データ収集
  - J‑Quants API クライアント（株価日足、財務データ、マーケットカレンダー）
  - RSS を用いたニュース収集（SSRF対策、トラッキングパラメータ除去、記事ID生成）
  - DuckDB への冪等保存ユーティリティ
- 研究（Research）
  - Momentum / Volatility / Value 等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）やファクターサマリー
  - Zスコア正規化ユーティリティ
- 戦略
  - 特徴量構築（feature_engineering.build_features）：研究で算出した生ファクターを統合・正規化して features テーブルに保存
  - シグナル生成（signal_generator.generate_signals）：features と ai_scores を統合して BUY / SELL シグナルを生成して signals テーブルへ保存
- ポートフォリオ構築
  - 候補選択（select_candidates）、等配分／スコア配分（calc_equal_weights / calc_score_weights）
  - サイジング（calc_position_sizes）：risk_based / equal / score に対応、単元丸め、aggregate cap で現金枯渇を回避
  - リスク調整（apply_sector_cap、calc_regime_multiplier）
- バックテスト
  - run_backtest：DuckDB のデータをインメモリにコピーして日次ループで擬似約定を実行
  - PortfolioSimulator：買い/売りの擬似約定、マーク・トゥ・マーケット、トレード履歴管理
  - 評価指標（CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio 等）
- 設定管理
  - .env / 環境変数の自動読み込み（プロジェクトルート検出、.env/.env.local の取り扱い）
  - Settings オブジェクト経由でアプリケーション設定を取得

動作要件
--------
- Python >= 3.10（typing の | や型注釈表記を使用）
- 必要な主要ライブラリ（例）
  - duckdb
  - defusedxml
- ネットワーク接続（J‑Quants API、RSS フィード取得時）
- DuckDB ファイル（バックテストや永続データ用） — スキーマは data.schema.init_schema による初期化を想定

セットアップ
-----------
1. リポジトリをクローン／展開します。
2. 仮想環境を作成して有効化します（推奨）。
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストールします（例: pip）。
   - pip install duckdb defusedxml
   - （プロジェクト内に requirements.txt があればそれを使用）
4. 環境変数を設定します（.env ファイル推奨）。自動読み込みはプロジェクトルート（.git または pyproject.toml 所在）を基準に行われます。テスト等で自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

重要な環境変数（Settings）
-------------------------
以下は Settings クラスが利用する主要な環境変数です。必須項目は README 内で明示しています。

- JQUANTS_REFRESH_TOKEN (必須) — J‑Quants API 用リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード（execution 層利用時）
- KABU_API_BASE_URL — kabuAPI のエンドポイント（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack 通知先チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（モニタリング用）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境（development / paper_trading / live。デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG / INFO / WARNING / ERROR / CRITICAL、デフォルト: INFO）

使い方（主要なワークフロー例）
----------------------------

1) バックテストを実行する（CLI）
- 使い方（例）:
  python -m kabusys.backtest.run \
    --start 2023-01-01 --end 2023-12-31 \
    --cash 10000000 --db path/to/kabusys.duckdb
- オプション: --slippage, --commission, --allocation-method (equal|score|risk_based), --max-positions, --lot-size など
- 前提：指定した DuckDB ファイルは prices_daily、features、ai_scores、market_regime、market_calendar、stocks など必要テーブルが事前に準備されていること

2) 特徴量を構築して features テーブルへ保存（プログラムから）
- 例:
  from datetime import date
  import duckdb
  from kabusys.strategy import build_features
  conn = duckdb.connect("path/to/kabusys.duckdb")
  count = build_features(conn, target_date=date(2024, 1, 31))
  conn.close()

3) シグナルを生成して signals テーブルへ保存（プログラムから）
- 例:
  from datetime import date
  import duckdb
  from kabusys.strategy import generate_signals
  conn = duckdb.connect("path/to/kabusys.duckdb")
  n = generate_signals(conn, target_date=date(2024,1,31), threshold=0.6)
  conn.close()

4) J‑Quants からデータを取得して保存する（ETL）
- 例（株価取得と保存）:
  from datetime import date
  import duckdb
  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
  conn = duckdb.connect("path/to/kabusys.duckdb")
  records = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  saved = save_daily_quotes(conn, records)
  conn.close()

5) ニュース収集ジョブを実行して raw_news / news_symbols を作る
- 例:
  from kabusys.data.news_collector import run_news_collection
  conn = duckdb.connect("path/to/kabusys.duckdb")
  known_codes = {"7203","6758", ...}  # stocks テーブルや外部マスタから構築
  result = run_news_collection(conn, known_codes=known_codes)
  conn.close()
- run_news_collection は各 RSS ソースごとの成功件数を返します

ライブラリとしての利用例
- バックテスト API を直接呼ぶ:
  from datetime import date
  import duckdb
  from kabusys.backtest.engine import run_backtest
  conn = duckdb.connect("path/to/kabusys.duckdb")
  result = run_backtest(conn, start_date=date(2023,1,1), end_date=date(2023,12,31))
  conn.close()
- 戦略/ポートフォリオ関数を組み合わせてカスタム実行フローを作ることも可能です。

ディレクトリ構成（抜粋）
-----------------------
プロジェクトの主要なモジュールと概略は以下の通りです（src/kabusys 以下）。

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / Settings 管理（.env 自動読み込み）
  - data/
    - jquants_client.py          — J‑Quants API クライアント（取得・保存関数）
    - news_collector.py          — RSS ニュース収集・前処理・DB 保存
    - (その他 data/schema 等)
  - research/
    - factor_research.py         — momentum / volatility / value の計算
    - feature_exploration.py     — 将来リターン計算・IC・サマリ
  - strategy/
    - feature_engineering.py     — features 構築（正規化・UPSERT）
    - signal_generator.py        — シグナル生成（BUY / SELL）
  - portfolio/
    - portfolio_builder.py       — 候補選定・重み計算
    - position_sizing.py         — 株数算出・aggregate cap 処理
    - risk_adjustment.py         — セクターキャップ・レジーム乗数
  - backtest/
    - engine.py                  — バックテスト全体ループ
    - simulator.py               — 擬似約定・ポートフォリオ管理
    - metrics.py                 — バックテストの評価指標
    - run.py                     — CLI エントリポイント（python -m kabusys.backtest.run）
    - clock.py
  - portfolio/ (上記)
  - execution/                    — （発注層用プレースホルダ）
  - monitoring/                   — （モニタリング／アラート用プレースホルダ）
  - その他研究 / ユーティリティモジュール

注意点・設計上のポイント
-----------------------
- Look‑ahead バイアス回避: 特徴量・シグナル生成は target_date 時点までのデータのみを使用する設計です。バックテストでのデータ準備時も取得日時（fetched_at）や取得タイミングに注意してください。
- 冪等性: DuckDB への保存処理は可能な限り ON CONFLICT やトランザクションで冪等性を保つよう実装されています。
- セキュリティ: RSS 取得では SSRF 対策・受信サイズ制限・defusedxml を使用した XML パースなどにより外部入力の安全性を配慮しています。
- 実運用（live）環境: KABUSYS_ENV を live にセットすると一部の挙動やチェックが切り替わる想定です。実際に発注を行う execution 層（kabu ステーション連携等）を統合する際は十分なテストと安全弁を設けてください。

開発・貢献
-----------
- 新機能追加やバグ修正はブランチを切って PR を送ってください。自動テストや静的解析の導入を推奨します。
- テストを書く際は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動ロードを無効化できます。

ライセンス
---------
（このリポジトリにライセンスファイルがない場合は、適切なライセンスを明記してください。）

問い合わせ
----------
実装や利用に関する質問はリポジトリの Issue に記載してください。README にない運用上の前提（DB スキーマ詳細、外部シークレットの管理方法など）はプロジェクト内のドキュメント（Design/Markdown）を参照してください。

以上。必要であれば README に使用例（具体的なコードスニペット）や DuckDB スキーマのサンプル、デプロイ手順（systemd / cron / Airflow 等）を追記します。どの部分を詳しく追加しますか？