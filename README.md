# KabuSys

日本株向け自動売買プラットフォーム（KabuSys）のコードベース用 README。  
本リポジトリはデータ収集・特徴量作成・シグナル生成・ポートフォリオ構築・バックテストまでを含むモジュール群で構成されています。

---

## プロジェクト概要

KabuSys は以下の機能を持つ日本株アルゴリズム取引基盤のプロトタイプです。

- J-Quants API からの価格・財務・カレンダ取得（rate limit / retry / token refresh 対応）
- RSS ベースのニュース収集と銘柄紐付け（SSRF 対策、前処理、重複排除）
- 研究（research）用のファクター計算（モメンタム / バリュー / ボラティリティ 等）
- 特徴量エンジニアリング（Zスコア正規化・ユニバースフィルタ）
- シグナル生成（ファクター統合 + AIスコア統合、BUY/SELL の判定ロジック）
- ポートフォリオ構築（候補選定・重み付け・リスク調整・ポジションサイズ算出）
- バックテストフレームワーク（擬似約定、スリッページ・手数料モデル、メトリクス）
- DB は DuckDB を想定（スキーマ初期化ユーティリティ参照）

設計方針として、Look-ahead バイアス回避、冪等性、堅牢なネットワーク/入力検証を重視しています。

---

## 主な機能一覧

- 環境設定管理
  - .env/.env.local を自動読み込み（プロジェクトルート検出、無効化フラグあり）
- データ取得・保存
  - J-Quants クライアント：fetch/save（prices, financials, market calendar）
  - News collector：RSS 取得、前処理、raw_news / news_symbols 保存
- 研究・特徴量
  - factor_research: calc_momentum / calc_volatility / calc_value
  - strategy.feature_engineering: build_features（Z スコア正規化、ユニバースフィルタ）
- シグナル生成
  - strategy.signal_generator: generate_signals（ファクター統合、Bear 判定、BUY/SELL 書き込み）
- ポートフォリオ構築
  - portfolio.portfolio_builder: select_candidates / calc_equal_weights / calc_score_weights
  - portfolio.position_sizing: calc_position_sizes（risk_based / equal / score）
  - portfolio.risk_adjustment: apply_sector_cap / calc_regime_multiplier
- バックテスト
  - backtest.engine: run_backtest（データコピー、ループ、サイジング、約定）
  - backtest.simulator: PortfolioSimulator（擬似約定、mark_to_market、trade リスト）
  - backtest.metrics: パフォーマンス指標（CAGR, Sharpe, MaxDD, WinRate, Payoff 等）
  - backtest.run: CLI エントリポイント
- 補助ユーティリティ
  - research.feature_exploration: IC, forward returns, factor summary
  - data.news_collector: RSS 正規化 / 銘柄抽出 / DB 保存（SSRF/サイズ制限/圧縮対応）
  - config: 環境変数管理（必須キー取得時は ValueError を上げる）

---

## セットアップ手順

前提
- Python 3.10+（コード上で型アノテーションに union 型などを使用）
- DuckDB（Python パッケージ）を利用
- ネットワークアクセス（J-Quants API / RSS）

1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install duckdb defusedxml

   （追加でロギングやテスト用ライブラリを導入する場合は requirements.txt を利用してください。現状のコードは標準ライブラリと上記を前提としています）

4. 環境変数設定
   - プロジェクトルート（.git または pyproject.toml がある場所）に `.env` を作成してください。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - 任意:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — デフォルト: INFO
     - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト data/monitoring.db）
   - 自動 .env 読み込みを抑止する場合:
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1

   例 (.env)
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. DuckDB スキーマ初期化
   - コード中にある `kabusys.data.schema.init_schema` を呼んでスキーマを作成してください（本 README の付随ファイルとして schema 実装があることを前提）。
   - 例:
     ```py
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     conn.close()
     ```

---

## 使い方

以下は代表的なユースケースと実行例です。

1. バックテスト（CLI）
   - 必要条件: DuckDB ファイルに事前に prices_daily, features, ai_scores, market_regime, market_calendar が存在すること
   - 実行例:
     ```
     python -m kabusys.backtest.run \
       --start 2023-01-01 --end 2023-12-31 \
       --cash 10000000 --db data/kabusys.duckdb \
       --allocation-method risk_based --max-positions 10
     ```
   - 出力: 最終的なメトリクス（CAGR, Sharpe 等）を標準出力に表示

2. 特徴量ビルド（Python API）
   ```py
   import duckdb
   from datetime import date
   from kabusys.strategy.feature_engineering import build_features
   from kabusys.data.schema import init_schema

   conn = init_schema("data/kabusys.duckdb")
   n = build_features(conn, target_date=date(2024, 1, 31))
   print(f"features upserted: {n}")
   conn.close()
   ```

3. シグナル生成（Python API）
   ```py
   from datetime import date
   from kabusys.strategy.signal_generator import generate_signals
   conn = init_schema("data/kabusys.duckdb")
   count = generate_signals(conn, target_date=date(2024, 1, 31))
   print("signals written:", count)
   conn.close()
   ```

4. J-Quants から価格取得・保存
   ```py
   from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   recs = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
   saved = save_daily_quotes(conn, recs)
   conn.close()
   ```

5. ニュース収集ジョブ
   ```py
   from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
   from kabusys.data.schema import init_schema

   conn = init_schema("data/kabusys.duckdb")
   known_codes = {"6758","7203","9984"}  # 事前に stocks テーブルを構築しておく
   results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
   print(results)
   conn.close()
   ```

注意点:
- バックテストは本番データベースのテーブルをそのまま書き換えないよう、内部でインメモリ DuckDB に必要部分をコピーして処理します（_build_backtest_conn）。
- J-Quants API はレート制限・リトライを実装しています。API トークンは JQUANTS_REFRESH_TOKEN 環境変数で指定します。

---

## よく使うモジュール / API（抜粋）

- kabusys.config.settings — 環境設定アクセス（.jquants_refresh_token 等）
- kabusys.data.jquants_client — fetch_*/save_* 系
- kabusys.data.news_collector — fetch_rss / save_raw_news / run_news_collection
- kabusys.research.* — calc_momentum / calc_volatility / calc_value / zscore_normalize 等
- kabusys.strategy.build_features / generate_signals — ETL → シグナル生成
- kabusys.portfolio.* — select_candidates / calc_equal_weights / calc_score_weights / calc_position_sizes / apply_sector_cap / calc_regime_multiplier
- kabusys.backtest.run / kabusys.backtest.engine.run_backtest — バックテスト実行

---

## ディレクトリ構成

主要ファイルとディレクトリの概観（src/kabusys 以下）:

- src/kabusys/
  - __init__.py
  - config.py  -- 環境変数 / .env 管理
  - data/
    - __init__ (モジュールエントリ)
    - jquants_client.py  -- J-Quants API クライアント（fetch/save）
    - news_collector.py  -- RSS ニュース収集・保存
    - (schema.py, calendar_management.py などが存在する想定)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - strategy/
    - __init__.py
    - feature_engineering.py
    - signal_generator.py
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - backtest/
    - __init__.py
    - engine.py
    - metrics.py
    - simulator.py
    - run.py
    - clock.py
  - execution/  -- 実行層（空のパッケージ/拡張ポイント）
  - monitoring/ -- 監視/通知機能（将来的に Slack 連携等）
  - research/ (上記)

（実際のリポジトリでは追加ファイルや schema 実装、ユーティリティ群が存在することが予想されます）

---

## 開発・運用上の注意

- 環境変数の未設定は Settings._require により ValueError を発生させます。`.env.example` を参照して `.env` を作成してください。
- Look-ahead バイアスを避ける設計になっていますが、データの投入順・タイムスタンプ（fetched_at）管理は運用で正しく行ってください。
- バックテストで使うデータは事前に取得・整形（prices_daily, features, ai_scores, market_regime, market_calendar）しておく必要があります。
- ニュース取得は外部 RSS に依存します。SSRF 対策・レスポンスサイズ制限など安全性対策を実装していますが、運用時には監視が必要です。
- 本番運用（kabuステーション等への注文送信）を行う場合は execution 層とセキュリティ対策（API パスワード管理・接続監査等）を厳密に実装してください。

---

もし README に加えたい補足（例: schema の具体的な初期化方法、Docker 環境設定、CI/CD のセットアップ、実演用データの取得スクリプト）などがあれば教えてください。必要事項に合わせて追記します。