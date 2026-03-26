# KabuSys

KabuSys は日本株向けの自動売買 / 研究プラットフォームのコアライブラリです。  
DuckDB を使ったデータ処理・研究モジュール、シグナル生成、ポートフォリオ構築、バックテスト、ニュース収集、J‑Quants API クライアントなどを含みます。

以下はこのリポジトリの README（日本語）です。

---

## プロジェクト概要

KabuSys は次の目的のために設計されたモジュール群です。

- 価格・財務データの取得と DuckDB への格納（J‑Quants API クライアント）
- 特徴量（features）作成とシグナル生成（strategy）
- ポートフォリオ構築（候補選定、配分、リスク調整、サイジング）
- バックテスト（シミュレータ、評価指標、実行エントリ）
- ニュース収集（RSS → raw_news、銘柄紐付け）
- 研究ユーティリティ（ファクター計算、IC 計算、統計サマリー）

設計方針として、ルックアヘッドバイアス回避、冪等性（DB 書き込み）、ネットワーク堅牢性（リトライ・レート制限）、SSRF 保護等を重視しています。

---

## 主な機能一覧

- data/
  - J‑Quants クライアント（認証・ページネーション・リトライ・レート制限）
  - RSS ニュース収集（SSRF 対策、トラッキングパラメータ除去、記事ID生成）
  - DuckDB への保存ユーティリティ（raw_prices、raw_financials、market_calendar 等）
- research/
  - モメンタム・ボラティリティ・バリューのファクター計算
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリー
- strategy/
  - 特徴量構築（features テーブルへの UPSERT、Z スコア正規化）
  - シグナル生成（ファクター + AI スコア統合、BUY / SELL 判定）
- portfolio/
  - 候補選定、等配分／スコア加重、リスクベースのサイジング
  - セクター集中制限、レジーム乗数
- backtest/
  - ポートフォリオシミュレータ（スリッページ・手数料モデル）
  - バックテスト実行エンジン（データのインメモリコピー、ループ処理）
  - 評価指標（CAGR、Sharpe、Max Drawdown、勝率、Payoff Ratio）
  - CLI エントリポイント（python -m kabusys.backtest.run）
- その他
  - 環境設定読み込み（.env 自動ロード、settings オブジェクト）
  - ロギング / エラーハンドリングを意識した実装

---

## 必要条件

- Python 3.10 以上（typing の `|` 等を使用）
- 必要パッケージの一例:
  - duckdb
  - defusedxml
- 標準ライブラリのみで動く部分も多いですが、DuckDB を使う機能は duckdb が必須です。

推奨: 仮想環境（venv / pyenv）を使用してください。

---

## インストール

ソースツリーをクローン後、仮想環境で必要パッケージをインストールします（例）:

1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows は .venv\Scripts\activate)

2. 必要パッケージをインストール（例）
   - pip install duckdb defusedxml

3. 開発インストール（任意）
   - pip install -e .

（※ プロジェクトに setup/pyproject がある場合はそちらに従ってください）

---

## 環境変数設定

設定は環境変数またはプロジェクトルートの `.env` / `.env.local` から自動読み込みされます（起動時に自動ロード）。自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主に必要な環境変数:

- J-Quants（データ取得）
  - JQUANTS_REFRESH_TOKEN — 必須（J‑Quants リフレッシュトークン）
- kabu ステーション API（実トレード用）
  - KABU_API_PASSWORD — 必須
  - KABU_API_BASE_URL — 任意（デフォルト: http://localhost:18080/kabusapi）
- Slack（通知など）
  - SLACK_BOT_TOKEN — 必須
  - SLACK_CHANNEL_ID — 必須
- DB パス（デフォルト）
  - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
  - SQLITE_PATH — デフォルト: data/monitoring.db
- 実行モード / ログ
  - KABUSYS_ENV — development | paper_trading | live（デフォルト: development）
  - LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

注意: settings オブジェクト（kabusys.config.settings）を通じてアプリケーション内でアクセスします。

---

## セットアップ手順（簡易）

1. 必要パッケージをインストール（上記参照）
2. DuckDB スキーマ初期化
   - データベーススキーマを初期化するユーティリティがプロジェクトに含まれている前提です（例: kabusys.data.schema.init_schema(path) を使用）。init_schema を呼んで必要なテーブルを作成してください。
   - 例:
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     conn.close()
3. .env を作成して必要な環境変数を設定
   - .env.example 等があればそれを参考に作成してください
4. J‑Quants データを取得して raw テーブルを埋める（任意）
   - kabusys.data.jquants_client.fetch_daily_quotes / fetch_financial_statements を使用し、save_* 関数で DuckDB に保存

---

## 使い方（主要な操作例）

以下は主要なユースケースと実行方法の例です。

- バックテスト（CLI）
  - コマンド例:
    python -m kabusys.backtest.run \
      --start 2023-01-01 --end 2024-12-31 \
      --cash 10000000 --db path/to/kabusys.duckdb
  - オプション:
    --slippage, --commission, --allocation-method (equal|score|risk_based), --max-positions, --risk-pct, --stop-loss-pct, --lot-size など
  - 内部では DuckDB から必要なテーブルをコピーし、PortfolioSimulator を用いて売買をシミュレートします。

- プログラムからバックテストを呼ぶ
  - run_backtest を直接呼び出します（kabusys.backtest.engine.run_backtest）。
  - 例:
    from kabusys.data.schema import init_schema
    from kabusys.backtest.engine import run_backtest
    conn = init_schema("path/to/kabusys.duckdb")
    result = run_backtest(conn, start_date, end_date, initial_cash=10_000_000)
    conn.close()

- 特徴量構築（features テーブル更新）
  - strategy.feature_engineering.build_features(conn, target_date)
  - DuckDB 接続と計算対象日を渡すと、features テーブルを日付単位で置換（冪等）します。

- シグナル生成（signals テーブル更新）
  - strategy.signal_generator.generate_signals(conn, target_date, threshold=0.6, weights=None)
  - features / ai_scores / positions を参照して BUY/SELL を算出し signals テーブルへ書き込みます。

- ニュース収集（RSS）
  - data.news_collector.run_news_collection(conn, sources=None, known_codes=None)
  - デフォルトの RSS ソースを使って raw_news テーブルに記事を挿入し、既知コードが与えられれば news_symbols に紐付けします。
  - セキュリティ面: SSRF 検査、受信サイズ制限、XML デコードの安全化（defusedxml）等を実装済み。

- J‑Quants API からのデータ取得
  - data.jquants_client.fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar / fetch_listed_info
  - get_id_token(refresh_token) で ID トークンを取得。API はページネーション・レート制限・リトライ・自動トークンリフレッシュに対応。
  - 取得結果の DuckDB 保存関数: save_daily_quotes, save_financial_statements, save_market_calendar

---

## 主要モジュール（プログラムインターフェースの例）

- kabusys.config
  - settings: 必要な環境値をプロパティ経由で取得（例: settings.jquants_refresh_token）
- kabusys.data.jquants_client
  - fetch_*/save_* 関数群
- kabusys.data.news_collector
  - fetch_rss, save_raw_news, run_news_collection, extract_stock_codes
- kabusys.research
  - calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank
- kabusys.strategy
  - build_features, generate_signals
- kabusys.portfolio
  - select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes, apply_sector_cap, calc_regime_multiplier
- kabusys.backtest
  - run_backtest, BacktestResult, simulator / metrics
  - CLI: python -m kabusys.backtest.run

---

## ディレクトリ構成

（主要ファイルを抜粋）

- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - jquants_client.py
    - news_collector.py
    - (schema.py, calendar_management.py などの補助モジュールが期待される)
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
  - backtest/
    - engine.py
    - simulator.py
    - metrics.py
    - run.py  (CLI エントリポイント)
    - clock.py
  - execution/  (発注 / 実行層 placeholder)
  - monitoring/ (監視・通知用モジュール placeholder)
  - portfolio/ (上記)
  - research/ (上記)

（プロジェクトルートに pyproject.toml や .git がある想定）

---

## 開発・運用上の注意

- ルックアヘッドバイアス回避のため、特徴量計算・シグナル生成は target_date 時点で利用可能なデータのみを使う設計です。バックテストでもこのポリシーが守られるように DB に投入するデータ管理に注意してください。
- settings は起動時に .env/.env.local を自動ロードします。テスト等で自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- J‑Quants API はレート制限（120 req/min）に従う必要があります。jquants_client は内部でレート制御を行いますが、大量取得スクリプトは適切にスリープやバッチ化してください。
- news_collector は外部 URL を扱います。SSRF や巨大レスポンス対策が組み込まれていますが、運用時は信頼できる RSS ソースを使い、known_codes による紐付けを検討してください。
- 本ライブラリは、実際の発注（kabuステーションや証券API）部分を別レイヤーで安全に組み合わせることを想定しています。運用（live）モードで使用する際は API 認証情報・エラーハンドリング・監視を厳重にしてください。

---

## よくあるコマンドまとめ

- バックテスト（CLI）
  - python -m kabusys.backtest.run --start 2023-01-01 --end 2023-06-30 --db data/kabusys.duckdb
- DuckDB スキーマ初期化（例）
  - python -c "from kabusys.data.schema import init_schema; init_schema('data/kabusys.duckdb')"
- 特徴量構築（Python）
  - from kabusys.data.schema import init_schema
    from kabusys.strategy.feature_engineering import build_features
    conn = init_schema('data/kabusys.duckdb')
    build_features(conn, date(2024, 1, 31))
    conn.close()
- ニュース収集（Python）
  - from kabusys.data.schema import init_schema
    from kabusys.data.news_collector import run_news_collection
    conn = init_schema('data/kabusys.duckdb')
    run_news_collection(conn, known_codes={'7203','6758'})
    conn.close()

---

必要に応じて README にサンプル .env、DB スキーマ定義（schema.py）の使用方法、CI / ローカルテスト手順を追記してください。質問や追加で記載したいサンプル（.env.example、schema の具体例、よく使うスクリプト等）があれば教えてください。