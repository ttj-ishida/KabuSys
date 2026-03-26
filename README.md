# KabuSys

日本株向けの自動売買 / バックテストシステムのライブラリ群です。  
特徴量計算・シグナル生成・ポートフォリオ構築・バックテスト・データ収集など、研究〜運用ワークフローをカバーするモジュール群を提供します。

---
目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（主要 API / CLI 例）
- 環境変数（設定）
- ディレクトリ構成（主なファイルの説明）
- 注意事項 / 補足

---

## プロジェクト概要

KabuSys は日本株（J-Quants 等のデータソース想定）を対象とした、特徴量エンジニアリング → シグナル生成 → ポートフォリオ構築 → 約定シミュレーション（バックテスト）までを包含するライブラリ群です。  
設計方針として以下を重視しています。

- ルックアヘッドバイアス防止（各処理は target_date 時点の情報のみを使用）
- 冪等性（DB への UPSERT / 日次置換など）
- テストしやすい純粋関数の分離（DB 参照を持たない計算関数群）
- バックテストと本番ロジックの再利用性

---

## 機能一覧

主な機能（モジュール別）

- data
  - J-Quants API クライアント（レート制限・リトライ・トークンリフレッシュ対応）: fetch/save 関数
  - ニュース収集（RSS）と前処理、記事→銘柄紐付け
- research
  - ファクター計算（momentum / volatility / value 等）
  - 将来リターン計算、IC（Information Coefficient）、ファクター統計サマリー
- strategy
  - 特徴量の正規化・合成（features テーブル作成）
  - シグナル生成（final_score 計算、BUY/SELL の作成）と signals テーブル書き込み
- portfolio
  - 候補選定（スコア順選択）
  - 重み算出（等分・スコア加重）
  - リスク調整（セクターキャップ、レジーム乗数）
  - ポジションサイジング（risk_based / equal / score、単元丸め、aggregate cap）
- backtest
  - ポートフォリオシミュレータ（約定ロジック・スリッページ・手数料・マークツーマーケット）
  - バックテストエンジン（ループ制御、シグナル適用、ポジション管理）
  - メトリクス計算（CAGR, Sharpe, Max Drawdown, Win Rate, Payoff 等）
  - CLI 実行エントリ（python -m kabusys.backtest.run）
- config
  - 環境変数 / .env の自動読み込み、必須設定の取得ラッパー

---

## セットアップ手順

前提:
- Python 3.10 以上（型記法や union 演算子 (|) を利用）
- git 等の開発ツール

推奨手順（ローカル開発）:

1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (macOS / Linux)
   - .venv\Scripts\activate     (Windows)

3. 依存パッケージをインストール
   - 必須（最低限）:
     - duckdb
     - defusedxml
   - 例:
     - pip install duckdb defusedxml
   - もしプロジェクトに requirements.txt / pyproject.toml があればそれに従ってください。
   - 開発インストール:
     - pip install -e .

4. 環境変数／.env の準備
   - プロジェクトルートに `.env` / `.env.local` を置くと自動でロードされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須環境変数については「環境変数」節を参照してください。

5. DuckDB スキーマ初期化
   - 本リポジトリの data/schema 初期化関数（init_schema）を利用して DB を作成・テーブルを準備してください。
   - 既に準備済みの DuckDB ファイルがある場合はそのファイルを指定して利用できます。

---

## 使い方

主要な API と CLI の使用例を示します。

1) 特徴量の計算（features テーブル生成）
   - 関数: kabusys.strategy.build_features(conn, target_date)
   - 例:
     - from kabusys.strategy import build_features
       build_features(conn, date(2024, 1, 31))

   - 引数: DuckDB 接続（kabusys.data.schema.init_schema() が返す接続）、計算基準日

2) シグナル生成（signals テーブル作成）
   - 関数: kabusys.strategy.generate_signals(conn, target_date, threshold, weights)
   - 例:
     - from kabusys.strategy import generate_signals
       generate_signals(conn, date(2024, 1, 31), threshold=0.6)

3) バックテスト（CLI / Python API）
   - CLI:
     - python -m kabusys.backtest.run \
         --start 2023-01-01 --end 2024-12-31 \
         --db path/to/kabusys.duckdb \
         --cash 10000000 --allocation-method risk_based
   - Python API:
     - from kabusys.backtest.engine import run_backtest
       result = run_backtest(conn, start_date, end_date, initial_cash=10_000_000)
     - 戻り値: BacktestResult (history, trades, metrics)

4) データ取得 / 保存（J-Quants）
   - J-Quants からデータ取得:
     - from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
       records = fetch_daily_quotes(date_from=..., date_to=...)
       save_daily_quotes(conn, records)

5) ニュース収集
   - from kabusys.data.news_collector import run_news_collection
     run_news_collection(conn, sources=None, known_codes=set_of_codes)

注意:
- 多くの処理は DuckDB のテーブル（prices_daily, raw_financials, features, ai_scores, market_regime, market_calendar, stocks など）を前提とします。Schema の準備と適切なデータの投入が必要です。

---

## 環境変数（主な設定）

config.Settings で参照される主な環境変数:

- JQUANTS_REFRESH_TOKEN (必須)
  - J-Quants API のリフレッシュトークン

- KABU_API_PASSWORD (必須)
  - kabuステーション API 用パスワード（運用時）

- KABU_API_BASE_URL (任意, デフォルト: http://localhost:18080/kabusapi)
  - kabu API のベース URL

- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)

- DUCKDB_PATH (任意, デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (任意, デフォルト: data/monitoring.db)

- KABUSYS_ENV (任意, デフォルト: development)
  - 有効値: development, paper_trading, live
  - is_live / is_paper / is_dev で判定に利用

- LOG_LEVEL (任意, デフォルト: INFO)
  - 有効値: DEBUG, INFO, WARNING, ERROR, CRITICAL

- KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  - パッケージ初期化時の .env 自動読み込みを無効化（テスト用途）

.env の例ファイル（.env.example）を用意し、それを基に .env を作成してください。

---

## ディレクトリ構成（抜粋）

以下は src/kabusys 以下の主なファイル・モジュールと短い説明です。

- src/kabusys/__init__.py
  - パッケージのメタ情報（バージョンなど）

- src/kabusys/config.py
  - 環境変数読み込み／Settings クラス

- src/kabusys/data/
  - jquants_client.py
    - J-Quants API クライアント（取得/保存関数、レート制限、リトライ）
  - news_collector.py
    - RSS 収集、テキスト前処理、raw_news / news_symbols 保存

- src/kabusys/research/
  - factor_research.py
    - momentum / volatility / value のファクター計算
  - feature_exploration.py
    - 将来リターン、IC、統計サマリー

- src/kabusys/strategy/
  - feature_engineering.py
    - feature 正規化・features テーブルへの UPSERT
  - signal_generator.py
    - final_score 計算、BUY/SELL シグナルの生成と signals テーブル書き込み

- src/kabusys/portfolio/
  - portfolio_builder.py
    - 候補選定（select_candidates）と重み計算（equal/score）
  - position_sizing.py
    - 発注株数計算（risk_based, equal, score）
  - risk_adjustment.py
    - セクターキャップ適用、レジーム乗数計算

- src/kabusys/backtest/
  - engine.py
    - バックテストループ、全体オーケストレーション（run_backtest）
  - simulator.py
    - 約定シミュレータ（PortfolioSimulator、DailySnapshot、TradeRecord）
  - metrics.py
    - バックテスト評価指標計算
  - run.py
    - CLI エントリポイント（python -m kabusys.backtest.run）

- src/kabusys/portfolio/__init__.py, src/kabusys/strategy/__init__.py, src/kabusys/research/__init__.py, src/kabusys/backtest/__init__.py
  - 主要 API を公開する __all__ の定義

---

## 注意事項 / 補足

- DuckDB のスキーマ初期化・テーブル定義（schema.py など）は本 README のコード抜粋に含まれていません。バックテストや各種保存関数を使うには該当スキーマを用意してください（init_schema 関数が想定されています）。
- J-Quants API を利用する場合、トークン取り扱いとレート制限に注意してください。jquants_client は内部で固定間隔スロットリングとリトライを実装していますが、実際の利用状況に応じた運用設計が必要です。
- ニュース収集は外部 HTTP を呼ぶため、RSS ソースの可用性や外部ネットワーク制限（社内ネットワーク等）に依存します。news_collector には SSRF 保護やレスポンスサイズ制限等の安全対策を実装しています。
- バックテスト結果は DuckDB 内のデータに依存します。データの前処理や欠損値扱いが結果に影響しますので注意してください。

---

もし README に追加したい項目（例: CI / テスト手順、詳細なスキーマ定義、依存関係の完全なリスト、サンプルデータの準備手順など）があれば教えてください。必要に応じて追記します。