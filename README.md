# KabuSys

日本株向けの自動売買システム用ライブラリ / フレームワークです。データ取得（J-Quants）、ファクター計算、特徴量生成、シグナル生成、ポートフォリオ構築、バックテスト、ニュース収集など、アルゴリズムトレーディングの主要コンポーネントを含みます。

- 現バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は研究（research）から本番運用までを意識した日本株向け自動売買基盤のコード群です。設計方針として以下を重視しています。

- ルックアヘッドバイアスの排除（target_date 時点のみのデータ使用）
- 冪等性（DB 書き込みは日付単位の置換や ON CONFLICT を使用）
- モジュール分割（データ取得、研究、戦略、ポートフォリオ、実行、監視）
- バックテストとシミュレーション（約定・スリッページ・手数料モデル内蔵）
- ニュース収集・テキスト前処理（RSS → raw_news、銘柄抽出）

---

## 主な機能一覧

- データ取得 / ETL
  - J-Quants API クライアント（fetch + 保存: 日足 / 財務 / 市場カレンダー）
  - raw データを DuckDB に保存するユーティリティ
- 研究・特徴量
  - ファクター計算（Momentum / Volatility / Value / Liquidity）
  - Z スコア正規化・特徴量テーブル生成（build_features）
  - 特徴量探索（IC, ファクターサマリ等）
- 戦略・シグナル
  - features と ai_scores を統合して final_score を計算、BUY/SELL シグナル生成（generate_signals）
  - Bear レジーム抑制、ストップロス等の売り判定
- ポートフォリオ構築
  - 候補選定（select_candidates）
  - 重み計算（等金額 / スコア加重）
  - リスク調整（セクター上限適用、レジーム乗数）
  - サイジング（risk_based / equal / score、単元丸め、aggregate cap）
- バックテスト
  - インメモリ DuckDB にデータを複製して安全にバックテスト実行（run_backtest）
  - ポートフォリオシミュレータ（約定、部分約定、スリッページ、手数料）
  - メトリクス計算（CAGR, Sharpe, Max Drawdown, Win Rate, Payoff 等）
  - CLI エントリポイント（python -m kabusys.backtest.run）
- ニュース収集
  - RSS フィード収集（SSRF 対策、gzip 対応、トラッキング除去）
  - raw_news / news_symbols への保存、銘柄コード抽出

---

## セットアップ手順

以下は開発環境での基本的なセットアップ手順の例です。プロジェクトに requirements.txt / pyproject.toml がある想定で必要パッケージをインストールしてください。

1. Python 仮想環境作成（例: Python 3.9+ 推奨）
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - 主要依存（コードベースから推定）:
     - duckdb
     - defusedxml
   - 例:
     - pip install duckdb defusedxml
   - 実際には pyproject.toml / requirements.txt を参照してインストールしてください。

3. リポジトリルートに .env を作成
   - .env.example を参考に必要な環境変数を設定します（下記参照）。
   - 自動ロード: kabusys.config はプロジェクトルート（.git または pyproject.toml を基準）を探して .env を自動読込します。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読込を無効化できます。

4. DuckDB データベースの準備
   - データを格納する DuckDB ファイル（例: data/kabusys.duckdb）を用意します。
   - スキーマ初期化関数は kabusys.data.schema.init_schema を使用する設計になっています（実装ファイル参照）。

5. 環境変数（主なもの）
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
   - KABU_API_BASE_URL: kabu API のベース URL（任意、デフォルト: http://localhost:18080/kabusapi）
   - SLACK_BOT_TOKEN: Slack Bot トークン（必須）
   - SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
   - DUCKDB_PATH: デフォルトデータベースパス（例: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite パス（例: data/monitoring.db）
   - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
   - LOG_LEVEL: DEBUG|INFO|...（デフォルト: INFO）

---

## 使い方

ここでは主要なユースケースの簡単な使用例を示します。

1) バックテスト（CLI）

DuckDB に必要なテーブル（prices_daily, features, ai_scores, market_regime, market_calendar 等）が事前に整備されていることを前提とします。

コマンド例:
- python -m kabusys.backtest.run --start 2023-01-01 --end 2023-12-31 --db data/kabusys.duckdb

フル例:
- python -m kabusys.backtest.run \
    --start 2023-01-01 --end 2023-12-31 \
    --cash 10000000 --slippage 0.001 --commission 0.00055 \
    --allocation-method risk_based --max-positions 10 --lot-size 100 \
    --db data/kabusys.duckdb

2) Python からバックテスト呼び出し（スクリプト内）

例:
- from kabusys.data.schema import init_schema
  from kabusys.backtest.engine import run_backtest
  conn = init_schema("data/kabusys.duckdb")
  result = run_backtest(conn, start_date, end_date, initial_cash=10_000_000)
  conn.close()

結果の BacktestResult には history, trades, metrics が含まれます。

3) 特徴量計算とシグナル生成（スクリプト例）

例:
- import duckdb
  from kabusys.strategy import build_features, generate_signals
  conn = duckdb.connect("data/kabusys.duckdb")
  # features を作成（target_date は datetime.date）
  n = build_features(conn, target_date)
  # シグナル生成
  cnt = generate_signals(conn, target_date)

4) J-Quants からのデータ取得 → 保存

例:
- from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")
  recs = fetch_daily_quotes(date_from=..., date_to=...)
  saved = save_daily_quotes(conn, recs)

5) ニュース収集ジョブ

例:
- from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")
  results = run_news_collection(conn, known_codes=set_of_codes)

注意: 上記はコードベースの API に基づく使用例です。実際の動作にはスキーマ定義や事前データ投入、正しい環境変数が必要です。

---

## ディレクトリ構成（主なファイルと説明）

以下は src/kabusys 以下の主要モジュールと役割概観です。

- kabusys/
  - __init__.py
  - config.py
    - 環境変数の読み込み・管理（.env 自動読込、必須変数チェック）
  - data/
    - jquants_client.py
      - J-Quants API クライアント（取得・保存ユーティリティ）
    - news_collector.py
      - RSS 収集・前処理・raw_news 保存・銘柄抽出
    - (schema.py 等は参照されているが省略されている想定：DB スキーマ初期化用)
  - research/
    - factor_research.py
      - Momentum / Volatility / Value ファクター計算
    - feature_exploration.py
      - IC / 将来リターン計算 / 統計サマリ
  - strategy/
    - feature_engineering.py
      - features テーブル作成（正規化・ユニバースフィルタ）
    - signal_generator.py
      - final_score 計算、BUY/SELL シグナル生成、signals テーブル操作
  - portfolio/
    - portfolio_builder.py
      - 候補選定・重み計算
    - position_sizing.py
      - 株数算出（risk_based, equal, score）
    - risk_adjustment.py
      - セクター上限・レジーム乗数
  - backtest/
    - engine.py
      - バックテストのメインループ（run_backtest）
    - simulator.py
      - ポートフォリオシミュレータ（擬似約定・マークツーマーケット）
    - metrics.py
      - 評価指標計算（CAGR, Sharpe, MaxDD, 等）
    - run.py
      - CLI エントリポイント（python -m kabusys.backtest.run）
    - clock.py
      - バックテスト用模擬時計（将来拡張用）
  - execution/
    - (発注・API 実行層のプレースホルダ)
  - monitoring/
    - (監視・アラート関連のプレースホルダ)

---

## 注意事項 / 実運用への留意点

- 環境設定:
  - settings の必須変数が未設定だと起動時に ValueError が発生します（.env.example を参照して .env を用意してください）。
  - 自動 .env 読込はプロジェクトルート (.git または pyproject.toml) を基準に行います。CI / テストで無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Look-ahead bias:
  - 全モジュールで target_date ベースのデータ利用設計がなされています。バックテストや特徴量計算では必ず使用日以前のデータのみを参照することを守ってください。
- エラーハンドリング:
  - J-Quants クライアントはリトライ・トークンリフレッシュ・レート制御を実装していますが、API の仕様変更やレート制限の変化に注意が必要です。
- DB スキーマ:
  - このコードは特定の DuckDB スキーマ（prices_daily, raw_prices, raw_financials, features, ai_scores, signals, positions, market_regime, market_calendar, stocks, raw_news, news_symbols など）との整合を前提とします。schema 初期化・マイグレーションは別途実装されているものとして扱ってください。

---

## 貢献 / 開発者向け

- コードスタイル、テスト、CI を整備していくことで本番利用の信頼性を高めることを推奨します。
- 大きな変更（例: サイジングロジック、約定モデル、DB スキーマ）を行う際は Backtest の互換性と既存の結果再現性に注意してください。
- ドキュメント化（PortfolioConstruction.md, StrategyModel.md, BacktestFramework.md 等の参照ドキュメント）がコード中に多数参照されています。これらの設計文書を更新すると理解が深まります。

---

README は以上です。必要であれば以下を追加で作成できます：
- .env.example のテンプレート
- requirements.txt / pyproject.toml の推奨依存リスト
- DB スキーマ初期化スクリプト（kabusys.data.schema の実装例）
- よくあるエラーとトラブルシュートガイド

必要な追加項目があれば教えてください。