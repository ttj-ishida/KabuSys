# KabuSys

日本株向け自動売買 / リサーチ基盤のプロジェクトです。  
ファクター計算・特徴量作成、シグナル生成、ポートフォリオ構築、バックテスト、データ収集（J‑Quants / RSS）などのコンポーネントを備えています。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の機能群を持つモジュール化されたライブラリです。

- データ取得・ETL（J-Quants API、RSS ニュース収集）
- 研究・ファクター計算（モメンタム、ボラティリティ、バリュー等）
- 特徴量エンジニアリング（正規化・フィルタリング・features テーブルへの保存）
- シグナル生成（features+AIスコアの統合による BUY/SELL 判定）
- ポートフォリオ構築（候補選定、重み付け、サイジング、セクター制限）
- バックテストエンジン（擬似約定、スリッページ/手数料モデル、評価指標）
- ニュース収集と銘柄マッチング（RSS 収集・前処理・DB 保存）

設計方針は「ルックアヘッドバイアスの排除」「DB 操作は明確に」「発注/実行層と研究・特徴量処理の分離」にあります。

---

## 主な機能一覧

- data/
  - J‑Quants クライアント（API 呼び出し、取得 → DuckDB への保存）
  - RSS ニュース収集・前処理・銘柄抽出
- research/
  - calc_momentum / calc_volatility / calc_value 等のファクター計算
  - IC 計算、将来リターン計算、ファクター統計サマリー
- strategy/
  - build_features(conn, target_date): features を構築して DB に保存
  - generate_signals(conn, target_date): signals（buy/sell）を生成して DB に保存
- portfolio/
  - select_candidates, calc_equal_weights, calc_score_weights
  - calc_position_sizes（等配分/スコア配分/リスクベース）
  - apply_sector_cap（セクター集中制限）、calc_regime_multiplier
- backtest/
  - run_backtest(conn, start_date, end_date, ...): バックテストのメイン関数
  - PortfolioSimulator: 擬似約定とポートフォリオ状態管理
  - metrics: CAGR / Sharpe / MaxDD / WinRate / Payoff などの算出
  - CLI エントリポイント: python -m kabusys.backtest.run
- config/
  - Settings クラスで環境変数を一元管理（.env 自動読み込み対応）

---

## セットアップ手順

以下は開発環境向けの最小セットアップ手順例です。

1. Python 環境準備（推奨: 3.10+）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. パッケージをインストール
   - プロジェクトルートに pyproject.toml がある想定です:
     - pip install -e .
   - 必要な外部依存（例）
     - pip install duckdb defusedxml

   ※ 実プロジェクトでは pyproject.toml / requirements.txt を参照してください。

3. 環境変数 (.env) の準備
   - プロジェクトルートに `.env`（本番や dev 用） / `.env.local`（上書き用）を置くと自動で読み込まれます。
   - 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します（テストで有用）。

4. 必須環境変数（例）
   - JQUANTS_REFRESH_TOKEN — J‑Quants API 用リフレッシュトークン
   - KABU_API_PASSWORD — kabu API（発注）パスワード
   - SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
   - SLACK_CHANNEL_ID — Slack チャンネル ID

   これらは `kabusys.config.settings` 経由で取得され、未設定時は例外を投げます。

5. データベース
   - デフォルトのパスは Settings で定義：
     - DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
     - SQLITE_PATH: data/monitoring.db（デフォルト）
   - DuckDB スキーマ初期化関数は `kabusys.data.schema.init_schema` を参照して使ってください（実装は別ファイル）。

---

## 使い方（代表的な例）

ここではライブラリとしての主要な使用例を示します。

1. バックテスト（CLI）
   - 事前準備: DuckDB ファイルに prices_daily, features, ai_scores, market_regime, market_calendar 等が整っている必要があります。
   - 実行例:
     - python -m kabusys.backtest.run --start 2023-01-01 --end 2023-12-31 --db path/to/kabusys.duckdb
   - 主要オプション:
     - --cash, --slippage, --commission, --allocation-method（equal|score|risk_based）、--max-positions 等

2. features 作成（Python API）
   - DuckDB 接続を作成して呼び出します（init_schema を使用）。
   - 例:
     - from kabusys.strategy import build_features
     - from kabusys.data.schema import init_schema
     - conn = init_schema("path/to/kabusys.duckdb")
     - build_features(conn, target_date=date(2024, 1, 10))

3. シグナル生成（Python API）
   - from kabusys.strategy import generate_signals
   - generate_signals(conn, target_date=date(2024, 1, 10), threshold=0.6)

4. J‑Quants からデータ取得→保存
   - from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes, get_id_token
   - token = get_id_token()  # settings からリフレッシュトークンを使って取得
   - recs = fetch_daily_quotes(id_token=token, date_from=..., date_to=...)
   - save_daily_quotes(conn, recs)

5. ニュース収集（RSS）
   - from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
   - run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes_set)

6. バックテストを Python API から呼ぶ
   - from kabusys.backtest.engine import run_backtest
   - result = run_backtest(conn, start_date, end_date, initial_cash=10_000_000, ...)

---

## 設定と動作の注意点

- .env 自動読み込み順:
  - OS 環境変数 > .env.local > .env
  - 自動ロードはプロジェクトルート（.git または pyproject.toml を手掛かり）を基準に行います。
- Settings の検証:
  - KABUSYS_ENV は "development" / "paper_trading" / "live" のいずれかに制限されています。
  - LOG_LEVEL は "DEBUG/INFO/WARNING/ERROR/CRITICAL"。
- J‑Quants API クライアント:
  - レート制限（120 req/min）を守る組み込み RateLimiter、リトライ、401 の自動トークンリフレッシュを持ちます。
- NewsCollector:
  - RSS の取得では SSRF 対策、応答サイズ上限、XML パース時の安全対策（defusedxml）を実施しています。
- バックテスト:
  - run_backtest は本番 DB を読み取り専用で使用し、内部は in-memory DuckDB にデータをコピーして実行します（本番テーブルを汚染しません）。
  - シミュレータは SELL を先に、BUY を後で処理するポリシーです（資金確保のため）。

---

## ディレクトリ構成（主要ファイル）

（ソースルート: src/kabusys/）

- kabusys/
  - __init__.py
  - config.py
  - data/
    - jquants_client.py
    - news_collector.py
    - (schema.py を含む想定の DB ユーティリティ)
    - calendar_management.py (参照)
    - stats.py (zscore_normalize 等)
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
    - run.py (CLI)
    - clock.py
  - execution/ (発注／実行インタフェース用の空ディレクトリ/モジュール)
  - monitoring/ (監視用 DB/API 統合用の想定場所)

（上記はこの README を生成するために参照したコードベースの主要ファイルです）

---

## 開発・貢献

- コーディング規約・ドキュメントに従ってください（README や doc/、Design doc を参照）。
- 危険なデータベース操作やバックテストのループには注意してテストを行ってください。
- API トークン等の機密情報は `.env` に保存し、リポジトリに含めないでください。

---

## 参考

- 主要公開 API:
  - strategy.build_features(conn, target_date)
  - strategy.generate_signals(conn, target_date, threshold=None, weights=None)
  - backtest.run_backtest(conn, start_date, end_date, ...)
  - data.jquants_client.fetch_daily_quotes / save_daily_quotes
  - data.news_collector.run_news_collection

---

必要であれば、README に追加する「DB スキーマ（tables とカラム）」「詳しい CLI 使用例」「.env.example のテンプレート」「依存ライブラリ一覧（requirements）」を別途作成します。どれを優先して追加しますか？