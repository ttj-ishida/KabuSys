# KabuSys

KabuSys は日本株向けの自動売買フレームワークです。データ収集（J-Quants / RSS）・特徴量作成・シグナル生成・ポートフォリオ構築・バックテスト・シミュレーションを含むモジュール群を提供します。DuckDB を中心としたローカル DB を採用し、研究（research）→本番（execution）へ移行しやすい設計です。

主な設計方針
- ルックアヘッドバイアスを避ける（時点ベースのデータ参照）
- 冪等（idempotent）処理を重視（DB への upsert 等）
- ネットワーク操作はレート制限 / リトライ / セキュリティ対策を実装
- バックテストは DB をコピーしてインメモリで実行（本番データを汚さない）

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方
  - バックテスト CLI
  - ライブラリ的な利用例
  - データ収集（J-Quants / ニュース）
- 環境変数（必須・推奨）
- ディレクトリ構成

---

プロジェクト概要
- 日本株の定量戦略向けフレームワーク。
- 研究用の factor 計算（momentum / volatility / value 等）と、features 正規化、AIスコア統合によるシグナル生成を提供。
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ計算・セクターキャップ・レジーム乗数）を備え、バックテスト用シミュレータで約定・時価評価・トレード履歴を生成する。
- データレイヤーは DuckDB を用い、J-Quants API / RSS ニュースの収集・保存ユーティリティを含む。

---

機能一覧
- データ取得・ETL
  - J-Quants API クライアント（fetch / save: 日足、財務、上場情報、マーケットカレンダー）
    - レート制限 / リトライ / token 自動更新対応
  - RSS ニュース収集（SSRF 対策・トラッキング除去・正規化・DB 保存）
- 研究（research）
  - ファクター計算: calc_momentum, calc_volatility, calc_value
  - ファクター探索: forward returns, IC（Spearman）計算、統計サマリー
  - Z スコア正規化ユーティリティ
- 特徴量エンジニアリング（strategy.feature_engineering）
  - ユニバースフィルタ（株価・流動性）
  - ファクター統合・Zスコアクリップ・features テーブルへの UPSERT
- シグナル生成（strategy.signal_generator）
  - ファクター + AI スコア統合による final_score 計算
  - Bear レジーム検出による BUY 抑制
  - BUY / SELL の生成・signals テーブルへの冪等書込み
- ポートフォリオ構築（portfolio/*）
  - 候補選定（select_candidates）
  - 重み計算（等金額 / スコア加重）
  - ポジションサイズ計算（risk_based / equal / score）
  - セクター上限適用、レジーム乗数
- バックテスト（backtest/*）
  - データをインメモリ DuckDB にコピーして安全にバックテスト実行
  - ポートフォリオシミュレータ（約定ロジック、スリッページ・手数料処理）
  - 評価指標（CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio）
  - CLI runner（python -m kabusys.backtest.run）
- その他
  - 環境設定管理（kabusys.config）: .env 自動読み込み（プロジェクトルート判定）と必須変数チェック

---

セットアップ手順（開発環境向け）
前提: Python 3.10+（typing の Union | 演算子等を利用しているため）を想定します。

1. リポジトリを取得
   - git clone <repo-url>
   - cd <repo-root>

2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (UNIX/macOS)
   - .venv\Scripts\activate     (Windows)

3. インストール（開発時は editable が便利）
   - pip install -e . 
   - もしくは最低限の依存を入れる:
     - pip install duckdb defusedxml

   （requirements.txt / pyproject.toml があればそちらを利用してください）

4. 環境変数の準備
   - プロジェクトルートに .env を置くと自動で読み込まれます（.git または pyproject.toml を基準にルートを探索）。
   - 自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
   - 必須の環境変数は下記「環境変数」節を参照。

5. DuckDB スキーマ初期化
   - 本プロジェクトでは schema 初期化関数（kabusys.data.schema.init_schema）を使って DB を生成・接続する想定です。実データを用いる場合は価格データ等を事前にロードしてください。
   - バックテスト実行には prices_daily / features / ai_scores / market_regime / market_calendar / stocks 等のテーブルが必要です。

---

使い方

1) バックテスト CLI
- 付属の runner を用いて CLI でバックテストを実行できます。

例:
  python -m kabusys.backtest.run \
    --start 2023-01-01 --end 2023-12-31 \
    --cash 10000000 --db path/to/kabusys.duckdb

主要オプション:
- --start / --end: 開始/終了日 (YYYY-MM-DD)
- --cash: 初期資金（JPY）
- --slippage / --commission: スリッページ率 / 手数料率
- --allocation-method: equal | score | risk_based
- --max-positions, --max-utilization, --risk-pct, --stop-loss-pct, --lot-size
- --db: DuckDB ファイルパス（必須）

2) プログラム的にバックテストを実行
Python コードから run_backtest を呼ぶことができます。

例:
  from kabusys.data.schema import init_schema
  from kabusys.backtest.engine import run_backtest
  conn = init_schema("path/to/kabusys.duckdb")
  result = run_backtest(conn, start_date, end_date, initial_cash=10_000_000)
  conn.close()

戻り値: BacktestResult (history: list[DailySnapshot], trades: list[TradeRecord], metrics: BacktestMetrics)

3) 特徴量作成 / シグナル生成（DuckDB 接続が前提）
- build_features(conn, target_date)  — features テーブルを target_date 基準で構築
- generate_signals(conn, target_date) — signals テーブルに BUY/SELL を書き込む

4) データ収集
- J-Quants:
  - jquants_client.fetch_daily_quotes / fetch_financial_statements / fetch_listed_info / fetch_market_calendar
  - 保存は save_daily_quotes / save_financial_statements / save_market_calendar を使用（DuckDB 接続を渡す）

- ニュース収集:
  - news_collector.fetch_rss(url, source) で RSS 取得（SSRF 等の安全対策あり）
  - save_raw_news(conn, articles) / save_news_symbols(conn, news_id, codes) で DuckDB に保存
  - run_news_collection(conn, sources, known_codes) で複数ソース一括収集

注意:
- J-Quants の利用にはリフレッシュトークンが必要（環境変数参照）。
- NewsCollector は defusedxml, gzip 等の処理を行います。HTTP レスポンスサイズ上限やリダイレクト先の検査を行います。

---

環境変数（主要）
kabusys.config.Settings で参照されるキー（必須のものは起動時にチェックされます）:

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API の refresh token
- KABU_API_PASSWORD — kabuステーション API のパスワード（execution 層で使用）
- SLACK_BOT_TOKEN — Slack 通知用ボットトークン
- SLACK_CHANNEL_ID — Slack チャンネル ID

オプション・デフォルトあり:
- KABUSYS_ENV — "development" | "paper_trading" | "live" （デフォルト "development"）
- LOG_LEVEL — "DEBUG" | "INFO" | "WARNING" | "ERROR" | "CRITICAL"（デフォルト "INFO"）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite DB（デフォルト data/monitoring.db）

その他:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 — 起動時の .env 自動ロードを無効化（テスト時に有用）

.env のパースはシェル風の基本的な構文をサポートします（export プレフィックス、クォート、コメント等）。

---

DB / テーブル（バックテスト実行に最低限必要なテーブル）
- prices_daily — 日次 OHLCV データ
- raw_prices / raw_financials — 生データ保存テーブル（ETL 用）
- features — strategy の入力特徴量
- ai_scores — AI/ニュースのスコア（任意だが存在するとシグナルへ組み込まれる）
- signals — シグナル出力テーブル（生成後、実行エンジンが参照）
- positions — 保有情報（バックテストループ内で simulator の状態を書き戻す）
- market_regime, market_calendar — レジーム情報 / 取引カレンダー
- stocks — 銘柄マスタ（セクター情報を含む）

（スキーマ初期化は data.schema.init_schema を利用してください）

---

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - jquants_client.py
    - news_collector.py
    - (schema.py, calendar_management.py などが別途存在する想定)
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
  - execution/             (実取引関連の実装格納領域)
  - monitoring/            (監視・アラート用の実装格納領域)
  - research/              (先述の研究モジュール)
  - その他モジュール群...

---

開発上の注意点 / TODO（コードベースに示された点）
- position_sizing 等で price が欠損（0.0）の場合、エクスポージャーが過少見積もられる可能性あり。将来的にはフォールバック価格の導入を検討。
- news_collector と jquants_client は外部ネットワークを使用するため、テスト時はモックしてください（_urlopen などは差し替え可能）。
- 一部関数・機能は research 環境向けであり、本番ループから直接呼ばないでください（Look-ahead を防ぐため）。

---

貢献・ライセンス
- コントリビューションは Pull Request で受け付けます。詳細はリポジトリの CONTRIBUTING.md（存在する場合）を参照してください。
- ライセンス情報はリポジトリルートの LICENSE ファイルを参照してください。

---

補足 / 参考
- 主要な API 呼び出し例や schema 初期化の使い方は doc またはサンプルスクリプトとしてリポジトリに含めることを推奨します。
- 本 README はソースコードの docstring と実装に基づいて作成しています。実運用前に各テーブルのスキーマや ETL 手順を整備してください。

--- 

必要であれば、README に含めるサンプル .env.example、より詳細な CLI 使用例、あるいは schema の簡易サンプルを作成します。どれを優先しますか？