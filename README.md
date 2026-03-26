# KabuSys

KabuSys は日本株向けの自動売買・リサーチ／バックテスト基盤ライブラリです。  
ファクター計算、特徴量生成、シグナル生成、ポートフォリオ構築、バックテスト・シミュレータ、データ取得（J-Quants）やニュース収集などのモジュールを含みます。

以下はコードベースに基づく README.md（日本語）です。

---

## プロジェクト概要

KabuSys は、研究（research）→特徴量生成（feature engineering）→シグナル生成（strategy）→ポートフォリオ構築（portfolio）→約定シミュレーション／バックテスト（backtest）までの一連ワークフローを提供する Python パッケージです。  
また、J-Quants API からの市場データ取得や RSS ニュース収集のためのユーティリティも備えています。設計はルックアヘッドバイアスの排除、冪等性、堅牢なエラーハンドリングを重視しています。

想定用途:
- 研究環境でのファクター探索・IC 計算
- 特徴量・AIスコアの統合によるシグナル生成
- ポートフォリオ構築ロジックの検証
- 履歴データに対するバックテスト実行
- 実運用に向けたデータ収集（J-Quants）・ニュース収集

対象: 日本株（銘柄コード 4 桁想定）、Python 3.10 以上を推奨。

---

## 主な機能一覧

- 環境設定読み込み（.env / OS 環境変数）
  - 自動的にプロジェクトルートの `.env` / `.env.local` を読み込む（無効化可）
- データ取得・ETL
  - J-Quants API クライアント（ページネーション、トークン自動リフレッシュ、リトライ、レート制御）
  - RSS ベースのニュース収集（SSRF対策、トラッキングパラメータ除去、記事ID生成）
- 研究（research）
  - momentum / volatility / value 等のファクター計算
  - 将来リターン計算、IC（Spearman）計算、統計サマリー
- 特徴量エンジニアリング（strategy.feature_engineering）
  - ファクター正規化（Z スコア）、ユニバースフィルタ、features テーブルへの書き込み
- シグナル生成（strategy.signal_generator）
  - ファクター＋AI スコア統合 → final_score 算出
  - Bear レジーム検知による BUY 抑制、SELL（exit）判定
  - signals テーブルへの冪等書き込み
- ポートフォリオ構築（portfolio）
  - 候補選定（select_candidates）、等金額・スコア加重・リスクベース配分
  - セクター上限適用、レジーム乗数の計算
  - 発注数量（単元丸め、aggregate cap によるスケーリング）算出
- バックテスト（backtest）
  - インメモリ DuckDB を用いた安全なバックテスト接続作成
  - PortfolioSimulator による擬似約定（スリッページ・手数料モデル、部分約定対応）
  - 日次スナップショット／TradeRecord の収集、評価指標（CAGR, Sharpe, MaxDD, Win Rate, Payoff）
  - CLI エントリーポイントで期間指定による実行が可能

---

## 要件

- Python 3.10+
- 主要依存ライブラリ（例）
  - duckdb
  - defusedxml

（プロジェクト配布時は `requirements.txt` / `pyproject.toml` を参照してください）

---

## セットアップ手順

1. リポジトリをクローン、あるいはパッケージを取得する。

2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb defusedxml
   - （他に必要なパッケージはプロジェクト側で提供される requirements を参照）

4. 環境変数の設定
   - プロジェクトルートに `.env`（およびローカル用の `.env.local`）を配置すると自動読み込みされます。
   - 主要な環境変数（必須）:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD — kabu API パスワード（実運用時）
     - SLACK_BOT_TOKEN — Slack 通知（未使用の箇所あり）
     - SLACK_CHANNEL_ID — Slack チャネル
   - 任意 / デフォルトあり:
     - KABUSYS_ENV — development / paper_trading / live（デフォルト development）
     - LOG_LEVEL — DEBUG/INFO/...
     - KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると .env 自動読み込みを無効化
     - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト data/monitoring.db）

5. データベース（DuckDB）初期化
   - コード内の init_schema 関数（kabusys.data.schema）を使用して DB ファイルを初期化してください。
   - 例:
     - from kabusys.data.schema import init_schema
     - conn = init_schema("data/kabusys.duckdb")

---

## 使い方（代表的な例）

- バックテスト（CLI）
  - 典型的な実行例:
    - python -m kabusys.backtest.run \
        --start 2023-01-01 --end 2023-12-31 \
        --cash 10000000 --db path/to/kabusys.duckdb
  - 主なオプション:
    - --start / --end: 開始／終了日（YYYY-MM-DD）
    - --cash: 初期資金
    - --slippage / --commission: スリッページ・手数料率
    - --allocation-method: equal | score | risk_based
    - --max-positions, --max-utilization, --risk-pct, --stop-loss-pct, --lot-size
    - --db: DuckDB ファイルパス（必須）

- 特徴量構築（Python API）
  - 例:
    - from datetime import date
      import duckdb
      from kabusys.strategy import build_features
      conn = duckdb.connect("data/kabusys.duckdb")
      build_features(conn, date(2024, 1, 31))
      conn.close()

- シグナル生成（Python API）
  - 例:
    - from kabusys.strategy import generate_signals
      generate_signals(conn, date(2024, 1, 31))

- J-Quants データ取得（API クライアント）
  - 例:
    - from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
      records = fetch_daily_quotes(date_from=..., date_to=...)
      save_daily_quotes(conn, records)

- ニュース収集（RSS）
  - 例:
    - from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
      res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=my_known_codes)

- バックテストを Python API で実行
  - 例:
    - from kabusys.backtest.engine import run_backtest
      result = run_backtest(conn, start_date, end_date, initial_cash=10_000_000)
      # result.history / result.trades / result.metrics を参照

注意:
- 各種関数は DuckDB のスキーマ（prices_daily, features, ai_scores, positions, signals, stocks, market_regime 等）に依存します。DB は事前に init_schema により作成・データ投入してください。
- J-Quants の利用には有効なトークンが必要です。

---

## ディレクトリ構成（抜粋）

以下はソースの主要ファイル・モジュールと説明です（src/kabusys 配下）。

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数管理（.env 自動読み込み・Settings クラス）
  - data/
    - jquants_client.py — J-Quants API クライアント、データ取得・DuckDB 保存関数
    - news_collector.py — RSS ニュース収集、前処理、DB 保存
    - (schema.py 等が存在して DB 初期化を担当)
  - research/
    - factor_research.py — momentum/volatility/value のファクター計算
    - feature_exploration.py — forward returns, IC, 統計サマリ
  - strategy/
    - feature_engineering.py — features テーブル構築（正規化・フィルタ）
    - signal_generator.py — final_score 計算、BUY/SELL シグナル生成
  - portfolio/
    - portfolio_builder.py — 候補選定・重み算出
    - position_sizing.py — 株数算出（リスクベース／等配分）
    - risk_adjustment.py — セクターキャップ／レジーム乗数
  - backtest/
    - engine.py — バックテストループ、データコピー、発注ロジック組合せ
    - simulator.py — PortfolioSimulator（擬似約定、マークトゥマーケット）
    - metrics.py — バックテスト評価指標
    - run.py — CLI エントリポイント
    - clock.py — 将来拡張用模擬時計
  - execution/ (プレースホルダ)
  - monitoring/ (プレースホルダ)

---

## 追加の注意点 / 運用上の留意点

- 環境（KABUSYS_ENV）により挙動が切り替わります（development / paper_trading / live）。live 実行は十分な注意と検証が必要です。
- J-Quants API はレート制限があります（コード内で 120 req/min を想定した RateLimiter を実装）。大規模取得時は注意してください。
- ニュース収集には SSRF 対策やレスポンスサイズ制限等を組み込んでいますが、フィードソースの信頼性を確認して運用してください。
- DuckDB スキーマ（init_schema）はデータ構造に依存するため、バックテスト・本番ともにスキーマ整備が必要です。
- 本 README はコードのスニペットと実装に基づく簡易ドキュメントです。実運用前に各モジュール内部の仕様（コメント・StrategyModel.md 等の設計書）を確認してください。

---

もし README に追加したい内容（例: サンプル .env.example、依存パッケージの完全な一覧、CI / テストの実行方法、開発ルールなど）があれば教えてください。必要に応じて追記します。