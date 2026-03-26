# KabuSys

日本株向けの自動売買・研究プラットフォーム (KabuSys)。  
特徴量計算、シグナル生成、ポートフォリオ構築、バックテスト、データ収集（J‑Quants / RSS）などのモジュールを提供します。

---

## プロジェクト概要

KabuSys は以下の目的を持つ Python パッケージです。

- DuckDB ベースの時系列データ（株価・財務・ニュース）を扱い、研究用ファクターを算出する
- 正規化済み特徴量と AI スコアを統合して売買シグナルを生成する
- セクター制限・レジーム乗数・リスクベースのサイジングを含むポートフォリオ構築
- 約定モデル（スリッページ・手数料）を組み込んだバックテスト実行
- J‑Quants API からのデータ取得や RSS ニュース収集の ETL 機能

パッケージは src/kabusys 配下にモジュール群を持ち、研究環境と本番運用の両方に対応する設計になっています。

---

## 主な機能一覧

- 環境設定管理（.env の自動ロード、必須環境変数検査）
- データ取得／保存
  - J‑Quants API クライアント（株価、財務、上場情報、カレンダー）
  - RSS ニュース収集（正規化・SSRF 対策・銘柄抽出）
  - DuckDB への冪等保存ユーティリティ
- 研究モジュール
  - モメンタム / ボラティリティ / バリュー等のファクター計算（DuckDB SQL ベース）
  - 将来リターン、IC（Spearman）、ファクター統計サマリー
  - Z スコア正規化ユーティリティ
- 戦略モジュール
  - 特徴量生成（build_features）
  - シグナル生成（generate_signals）：ファクター＋AIスコア統合、BUY/SELL 判定、Bear レジーム抑制
- ポートフォリオモジュール
  - 候補選定、等金額／スコア加重配分、リスクベース・ポジションサイジング
  - セクターキャップ適用、レジーム乗数
- バックテスト
  - ポートフォリオシミュレータ（擬似約定、スリッページ・手数料モデル）
  - エンジン（run_backtest）: シグナル生成→約定→時価評価→次日注文ループを再現
  - 評価指標（CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio）
- 実運用（execution / monitoring）用のプレースホルダ（拡張ポイント）

---

## セットアップ手順

前提
- Python 3.10 以上（型ヒントの |Union を使用）
- システムに DuckDB がインストールされていること（pip で duckdb を入れます）

推奨手順（開発環境）

1. リポジトリをクローン／配置
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール（最低限）
   - pip install duckdb defusedxml
   - 実運用や追加機能では他パッケージが必要になる可能性があります（例: requests 等）。
4. パッケージを editable インストール（プロジェクトルートに pyproject.toml / setup がある前提）
   - pip install -e .

環境変数（.env）を準備する：
- プロジェクトルートに `.env` / `.env.local` を置くと自動的に読み込まれます（自動ロードを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。
- `.env.example` を参考にして値を作成してください（.env.example がない場合は下の「環境変数一覧」を参照）。

---

## 環境変数一覧（主要なもの）

必須（実行する機能に応じて必要になります）

- JQUANTS_REFRESH_TOKEN — J‑Quants 用リフレッシュトークン（fetch_* 系 API）
- KABU_API_PASSWORD — kabuステーション API パスワード（execution 連携時）
- SLACK_BOT_TOKEN — Slack 通知（monitoring 用）
- SLACK_CHANNEL_ID — Slack チャネル ID

任意／デフォルトあり

- KABUSYS_ENV — 実行環境: development / paper_trading / live （デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...。デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（monitoring 等）（デフォルト: data/monitoring.db）

設定は config.Settings を通じて取得できます。未設定の必須変数は Settings が ValueError を送出します。

自動ロードの挙動
- 起点ファイルからプロジェクトルート（.git または pyproject.toml）を探索し、`.env` → `.env.local` の順に読み込みます。
- OS 環境変数があるキーは上書きされません（.env.local は override=True だが OS 環境は保護されます）。
- 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 使い方

以下に主要なユースケースの実行例を示します。

1) バックテスト実行（CLI）
- 事前準備: DuckDB に prices_daily, features, ai_scores, market_regime, market_calendar, stocks などのテーブルが用意されていること
- 実行コマンド例:
  - python -m kabusys.backtest.run --start 2023-01-01 --end 2023-12-31 --db path/to/kabusys.duckdb
  - オプションで --cash, --slippage, --commission, --allocation-method, --max-positions 等を指定可能

2) 特徴量構築（research → strategy）
- Python から呼び出し例:
  - from kabusys.strategy import build_features
  - conn = init_schema("path/to/kabusys.duckdb")  # data.schema.init_schema を使用
  - build_features(conn, target_date=date(2024,1,31))

3) シグナル生成
- from kabusys.strategy import generate_signals
- generate_signals(conn, target_date=date(2024,1,31), threshold=0.6)

4) バックテスト API（プログラム的に）
- from kabusys.backtest.engine import run_backtest
- result = run_backtest(conn, start_date, end_date, initial_cash=10_000_000, allocation_method="risk_based", ...)

5) J‑Quants からのデータ取得と保存
- from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
- data = fetch_daily_quotes(date_from=..., date_to=...)
- save_daily_quotes(conn, data)

6) ニュース収集
- from kabusys.data.news_collector import run_news_collection
- run_news_collection(conn, sources=None, known_codes=set_of_codes)

注意点・設計ポリシー
- 研究ロジック（feature / factor 計算）は target_date 時点の情報のみを使用し、ルックアヘッドバイアスを避けるよう設計されています。
- DB への書き込みは日付単位の置換（DELETE→INSERT）で冪等性を保ちます。トランザクションを使って原子性を確保しています。
- J‑Quants クライアントはレート制限（120 req/min）、リトライ、トークン自動リフレッシュなどのロジックを組み込んでいます。

---

## API（主要関数・モジュール一覧）

- kabusys.config
  - settings — 環境設定オブジェクト（プロパティ経由で取得）
- kabusys.data.jquants_client
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar, fetch_listed_info
  - save_daily_quotes, save_financial_statements, save_market_calendar
  - get_id_token
- kabusys.data.news_collector
  - fetch_rss, save_raw_news, save_news_symbols, run_news_collection, extract_stock_codes
- kabusys.research
  - calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank, zscore_normalize
- kabusys.strategy
  - build_features(conn, target_date)
  - generate_signals(conn, target_date, threshold, weights)
- kabusys.portfolio
  - select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes, apply_sector_cap, calc_regime_multiplier
- kabusys.backtest
  - run_backtest(conn, start_date, end_date, ...)
  - backtest simulator & metrics

---

## ディレクトリ構成

（抜粋・主要ファイル）

- src/
  - kabusys/
    - __init__.py
    - config.py
    - data/
      - jquants_client.py
      - news_collector.py
      - (schema.py, calendar_management.py など別途実装想定)
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
      - run.py
      - clock.py
    - execution/            # 実運用用の発注層（プレースホルダ）
    - monitoring/          # 監視・通知用のプレースホルダ

各ファイルはモジュール責務が明確に分離されており、DB 参照や I/O を必要としない純粋関数と、DuckDB 接続等の I/O を伴う関数が混在します。用途に応じてモックしやすい設計です。

---

## 開発・テストのヒント

- DuckDB 接続はテストで ":memory:" を用いることでインメモリ DB に対する検証が可能です（data.schema.init_schema(":memory:") を想定）。
- config の自動 .env 読み込みはテストで干渉するため、環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して無効化できます。
- ネットワーク関連（jquants / RSS）の関数は外部呼び出しを伴うため、単体テストでは HTTP 呼び出し部分をモックしてください（news_collector._urlopen 等を差し替え可能）。

---

## ライセンス・貢献

（リポジトリに LICENSE があれば記載してください。ここでは省略します）  
バグ報告や機能提案、プルリクエスト歓迎です。変更は小さな単位で、ユニットテストを添えてください。

---

以上が KabuSys の README.md（日本語）です。README に追記したい情報（例: 実際の依存関係リスト、pyproject.toml のインストール手順、.env.example 内容、スキーマ定義など）があれば提供してください。必要に応じて README を拡張・整形します。