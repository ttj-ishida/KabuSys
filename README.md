# KabuSys

日本株向けの自動売買／リサーチ基盤ライブラリです。  
このリポジトリはデータ取得（J-Quants）、ファクター計算、特徴量エンジニアリング、シグナル生成、ポートフォリオ構築、バックテスト、ニュース収集などのコンポーネントを含み、研究〜バックテスト〜運用のワークフローをサポートします。

---

## プロジェクト概要

KabuSys は以下の機能を備えたモジュール群で構成される Python パッケージです:

- J-Quants API クライアント（データ取得・保存、トークン自動更新、レート制御）
- DuckDB を用いたデータスキーマ／ETL（raw_prices / prices_daily / features / signals などを想定）
- 研究用ファクター計算（Momentum / Volatility / Value 等）
- 特徴量作成（正規化、ユニバースフィルタ）
- シグナル生成（final_score に基づく BUY / SELL 判定、レジーム考慮）
- ポートフォリオ構築（候補選定、重み付け、サイジング、セクターキャップ）
- バックテストエンジン（模擬約定、スナップショット、メトリクス算出）
- ニュース収集（RSS → raw_news、記事と銘柄の紐付け）

設計方針として、バックテストループ中の「ルックアヘッドバイアス」防止、冪等性、HTTP リクエストやDB操作での堅牢性（トランザクションやリトライ）に配慮しています。

---

## 主な機能一覧

- data/
  - J-Quants クライアント（fetch_* / save_*）
  - RSS ニュース収集・保存（SSRF や XML 攻撃対策、記事ID の正規化）
- research/
  - ファクター計算: calc_momentum / calc_volatility / calc_value
  - 研究支援: IC 計算、将来リターン計算、統計サマリ
- strategy/
  - build_features(conn, target_date): features テーブル作成
  - generate_signals(conn, target_date): signals テーブル生成（BUY/SELL）
- portfolio/
  - 候補選定・重み付け・ポジションサイズ計算
  - セクター制限・レジーム乗数
- backtest/
  - run_backtest(...): バックテストのフル実行
  - PortfolioSimulator: 擬似約定（スリッページ・手数料モデル）
  - metrics: CAGR, Sharpe, Max Drawdown 等の計算
  - CLI: python -m kabusys.backtest.run
- config.py
  - .env 自動読み込み（プロジェクトルート検出）、必須環境変数チェック、KABUSYS_ENV 等の設定

---

## セットアップ手順

※ 以下は最小限の導入手順です。プロジェクトの pyproject.toml / requirements.txt に合わせて調整してください。

1. Python バージョン
   - Python 3.10+ 推奨（型注釈等に依存）

2. 仮想環境の作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージのインストール（例）
   - pip install duckdb defusedxml
   - ※ その他必要ライブラリをプロジェクトの依存に応じて追加してください。

4. パッケージのインストール（開発モード）
   - リポジトリルートに pyproject.toml/setup.py がある想定で:
     - pip install -e .

5. 環境変数 / .env の準備
   - プロジェクトルート（.git または pyproject.toml を含むディレクトリ）に `.env`（および開発用に `.env.local`）を置くと自動で読み込まれます。
   - 自動読み込みを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   - 必須環境変数（config.Settings が要求するもの）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - 任意 / デフォルト:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト development）
     - LOG_LEVEL: DEBUG|INFO|...（デフォルト INFO）
     - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト data/monitoring.db）

6. データベーススキーマの初期化
   - このコードは `kabusys.data.schema.init_schema()` を参照しています（本リポジトリ側に schema 実装がある前提）。
   - DuckDB ファイルを用意し、必要なテーブル（prices_daily, raw_prices, features, ai_scores, signals, positions, market_regime, market_calendar, stocks, raw_news, news_symbols, raw_financials ...）を作成してください。

---

## 使い方（主な例）

以下は代表的な操作のサンプルです。

1. バックテスト（CLI）
   - コマンド例:
     - python -m kabusys.backtest.run \
       --start 2023-01-01 --end 2023-12-31 \
       --cash 10000000 --db path/to/kabusys.duckdb
   - オプション: --slippage, --commission, --allocation-method, --max-positions, --lot-size など

2. バックテスト（API 呼び出し）
   - Python から:
     - from datetime import date
       from kabusys.data.schema import init_schema
       from kabusys.backtest.engine import run_backtest
       conn = init_schema("path/to/kabusys.duckdb")
       result = run_backtest(conn, start_date=date(2023,1,1), end_date=date(2023,12,31))
       conn.close()
     - result.history / result.trades / result.metrics を参照

3. 特徴量構築 / シグナル生成（DB 接続が前提）
   - from kabusys.strategy import build_features, generate_signals
     - build_features(conn, target_date)
     - generate_signals(conn, target_date)

4. J-Quants データ取得と保存
   - from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes, get_id_token
     - token = get_id_token()  # settings.jquants_refresh_token を利用
     - records = fetch_daily_quotes(id_token=token, date_from=..., date_to=...)
     - save_daily_quotes(conn, records)

   - 財務データやカレンダーも同様に fetch_* → save_* を呼ぶことで DuckDB に格納できます。

   - 注意: API レート制限、リトライ、トークン自動更新等はクライアント実装に組み込まれています。

5. ニュース収集
   - from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
     - results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=set_of_valid_codes)
     - results は各ソースの新規保存件数を返す

6. 研究用ファクター回収・解析
   - from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic
     - それぞれ DuckDB 接続と target_date を与えて実行

---

## 環境変数（主要）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants API の refresh token
- KABU_API_PASSWORD (必須) — kabuステーション API 用パスワード
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — 通知先 Slack チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — SQLite 用監視 DB（デフォルト data/monitoring.db）
- KABUSYS_ENV — environment: development | paper_trading | live（既定 development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）

config.py によりプロジェクトルートの `.env` / `.env.local` が自動ロードされます（OS 環境変数が優先）。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

---

## ディレクトリ構成（主要ファイルの説明）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数・設定管理（.env 自動読み込み、必須チェック）
  - data/
    - jquants_client.py — J-Quants API クライアント（fetch / save）
    - news_collector.py — RSS 収集 → raw_news / news_symbols 保存
    - （schema.py 等、DB スキーマ定義が別途存在する想定）
  - research/
    - factor_research.py — Momentum / Volatility / Value の計算
    - feature_exploration.py — 将来リターン・IC・統計サマリ等
  - strategy/
    - feature_engineering.py — features の作成（正規化・ユニバースフィルタ）
    - signal_generator.py — final_score に基づく BUY/SELL 生成
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 発注株数計算（risk_based / equal / score）
    - risk_adjustment.py — セクター制限・レジーム乗数
  - backtest/
    - engine.py — バックテストのメインループ（run_backtest）
    - simulator.py — 擬似約定・ポジション管理・スナップショット
    - metrics.py — バックテスト評価指標計算
    - run.py — CLI エントリポイント
    - clock.py — 模擬時計（将来拡張用）
  - portfolio/、research/、strategy/ の __init__.py は外部向け API を整理してエクスポートします。

（上記はリポジトリ内の主要モジュールのみを抜粋して記載しています）

---

## 注意事項 / ベストプラクティス

- Look-ahead バイアス回避:
  - feature / signal 生成・バックテスト実行時は、target_date 時点で「利用可能なデータのみ」を用いる設計になっています。データ投入や ETL を行う際は、バックテスト開始日に先立って取得したデータを用いる等の運用ルールを守ってください。
- 冪等性:
  - 多くの save_* 関数は ON CONFLICT や INSERT ... DO NOTHING を使って冪等に保存します。DB のスキーマ定義が対応していることを確認してください。
- API レート制御:
  - J-Quants はレート制限があります。jquants_client は固定間隔スロットリングとリトライを実装していますが、大量取得時は運用側でもレートを配慮してください。
- テスト:
  - config.py は自動で .env を読み込みます。テスト時に環境依存を排除するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を利用してください。

---

## 貢献・実装補足

- システムはモジュール分割と純粋関数（DB非依存）を意識した実装になっています。拡張（例: 銘柄別単元数のサポート、追加ファクター、分足シミュレーション等）は各モジュールの責任範囲に沿って実装可能です。
- schema.py（DB スキーマ）や運用用の CLI / ETL スクリプトは別途用意することを想定しています。

---

もし README に追加したい具体的な使い方（例: 実際の .env.example、schema の定義、CI / デプロイ手順、テスト実行コマンドなど）があれば教えてください。必要に応じてサンプル .env.example や最小限の schema.sql 例も作成できます。