KabuSys
=======

バージョン: 0.1.0

概要
----
KabuSys は日本株向けの自動売買 / 研究 / バックテスト基盤です。  
主な目的は以下を実現することです。
- J‑Quants など外部データソースからのデータ取得・格納（OHLCV、財務、カレンダー等）
- 研究用ファクター計算・特徴量構築（Zスコア正規化、ユニバースフィルタ等）
- シグナル生成（ファクター + AI スコア統合、売買・エグジット判定）
- ポートフォリオ構築（候補選定・重み算出・ポジションサイズ算出・セクター制約）
- バックテスト用シミュレータ（約定処理、スリッページ・手数料モデル、メトリクス）
- ニュース収集（RSS → raw_news、銘柄抽出）

主要機能
--------
- 環境設定管理（.env 自動読み込み、必須環境変数チェック）
- J‑Quants API クライアント（レートリミット、リトライ、トークン自動更新、ページネーション）
- データ保存ユーティリティ（DuckDB への冪等保存）
- ニュース収集器（RSS パーシング、SSRF 対策、記事ID正規化、銘柄抽出）
- 研究モジュール（momentum / volatility / value 等のファクター計算、IC/統計サマリ）
- 特徴量構築（Zスコア正規化、ユニバースフィルタ、features テーブルへの UPSERT）
- シグナル生成（ファクター + AI スコア統合、Bear フィルタ、BUY/SELL 判定、signals テーブルへ）
- ポートフォリオ構築（候補選定、等配分・スコア加重、リスクベースサイジング、セクター上限）
- バックテストエンジン（データをインメモリにコピーして安全に実行、履歴とトレードを出力）
- バックテスト CLI（python -m kabusys.backtest.run）

セットアップ
-----------
前提
- Python 3.9 以上（typing に Optional | 表記を使用しているため）
- DuckDB（Python パッケージ）
- defusedxml（ニュース収集で XML パースに安全対策を利用）
- ネットワークアクセス（J‑Quants API / RSS フィード等）

推奨インストール手順（例）
1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb defusedxml

   ※ プロジェクトが配布パッケージ化されている場合は requirements.txt / pyproject.toml を参照してください。

3. 環境変数設定
   - プロジェクトルートに .env（および .env.local）を置くと自動で読み込まれます（自動読み込みはデフォルトで有効）。
   - 自動読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

必須環境変数（例）
- JQUANTS_REFRESH_TOKEN: J‑Quants のリフレッシュトークン
- SLACK_BOT_TOKEN: Slack 通知用（未使用の箇所がある場合もありますが基本設定として）
- SLACK_CHANNEL_ID
- KABU_API_PASSWORD: kabu API を使う場合
- （オプション）KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV, LOG_LEVEL

使い方（代表例）
----------------

1) バックテスト（CLI）
- DB ファイル（DuckDB）が prices_daily, features, ai_scores, market_regime, market_calendar, stocks など必要テーブルを持っていることを前提に実行します。
- 例:
  - python -m kabusys.backtest.run --start 2023-01-01 --end 2023-12-31 --db path/to/kabusys.duckdb
  - オプション: --cash, --slippage, --commission, --allocation-method 等

2) 特徴量構築（コードから呼ぶ）
- build_features(conn, target_date)
  - duckdb の接続オブジェクトを渡し、target_date の features を再構築します（冪等）。

3) シグナル生成（コードから呼ぶ）
- generate_signals(conn, target_date, threshold=0.6, weights=None)
  - features / ai_scores / positions を参照して signals テーブルを書き換えます（冪等）。

4) データ取得 & 保存（J‑Quants）
- fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar を用いて API から取得後、save_daily_quotes / save_financial_statements / save_market_calendar で DuckDB に保存します。
- get_id_token(refresh_token) を使ってトークンを明示的に取得可能。

5) ニュース収集ジョブ
- run_news_collection(conn, sources=None, known_codes=None)
  - RSS ソースごとに fetch_rss → save_raw_news を行います。known_codes を渡すと記事と銘柄の紐付けも行います。

6) バックテストをプログラム的に呼ぶ
- run_backtest(conn, start_date, end_date, initial_cash=..., ...)
  - 戻り値は BacktestResult（history, trades, metrics）で、metrics は CAGR、Sharpe、MaxDD、Win Rate、Payoff 等を含みます。

設定・挙動に関する注意点
------------------------
- .env 読み込み順序: OS 環境変数 > .env.local > .env。自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で抑止可能。
- Settings クラスに必須キーがあり、未設定でアクセスすると ValueError を投げます（例: settings.jquants_refresh_token）。
- J‑Quants クライアントは内部で固定間隔のレートリミッタ・リトライ・401 リフレッシュを実装しています。
- ニュース収集では SSRF 対策、受信サイズ制限、gzip 解凍後のサイズ検査など堅牢性を考慮しています。
- バックテストは本番 DB を直接汚さないために、必要テーブルをインメモリの DuckDB にコピーして実行します。

ディレクトリ構成（抜粋）
-----------------------
src/kabusys/
- __init__.py                 — パッケージ定義（version=0.1.0）
- config.py                   — 環境変数 / 設定管理
- data/
  - jquants_client.py         — J‑Quants API クライアント + DuckDB 保存ユーティリティ
  - news_collector.py         — RSS 取得・前処理・DB 保存・銘柄抽出
  - ...（データ ETL 関連ユーティリティ）
- research/
  - factor_research.py        — momentum/volatility/value のファクター計算
  - feature_exploration.py    — 将来リターン、IC、ファクター統計
- strategy/
  - feature_engineering.py    — features 作成パイプライン
  - signal_generator.py       — final_score 計算と BUY/SELL シグナル生成
- portfolio/
  - portfolio_builder.py      — 候補選定・重み計算（等配分・スコア加重）
  - position_sizing.py        — 発注株数計算（risk_based / equal / score）
  - risk_adjustment.py        — セクターキャップ・レジーム乗数
- backtest/
  - engine.py                 — run_backtest（全体ループ、データコピー、発注フロー）
  - simulator.py              — PortfolioSimulator（約定・mark_to_market）
  - metrics.py                — バックテスト評価指標計算
  - run.py                    — CLI エントリポイント
- execution/                   — 発注/実行周り（雛形ファイル）
- monitoring/                  — 監視／通知周り（雛形ファイル）
- その他モジュール...

追加情報・開発メモ
------------------
- テーブルスキーマは kabusys.data.schema.init_schema() によって初期化される想定です（DuckDB スキーマが必要）。
- モジュール設計上、多くの機能は純粋関数で DB 参照を限定しているため、テストが容易です（例えば portfolio/.* は DB を参照しない）。
- ログレベルは LOG_LEVEL 環境変数で制御できます（DEBUG/INFO/...）。
- Bear レジームやスコア不足時の保護ロジックなど、StrategyModel/PortfolioConstruction の仕様に基づくフォールバック処理が多数あります。ソース内コメントを参照してください。

問い合わせ / 貢献
----------------
バグ報告・機能提案やパッチは issue / PR で受け付けてください。ソースのドキュメントコメント（関数 docstring）を優先的に参照すると実装意図がわかりやすいです。

おわりに
--------
この README はコードベースの現状（主要モジュールと公開 API）をまとめたものです。各機能を実運用で使う際は、必ずテストデータで検証し、Look‑ahead bias や取引コストの取り扱いに注意してください。