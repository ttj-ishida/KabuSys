# KabuSys

日本株自動売買システム（ライブラリ）  
このリポジトリは、データ取得・ファクター計算・シグナル生成・ポートフォリオ構築・バックテストを含む日本株向けのトレーディング基盤モジュール群です。モジュールは可能な限り純粋関数・DB分離を保ち、バックテストと本番処理のコードを共通化できるよう設計されています。

主な設計理念：
- ルックアヘッドバイアス防止（target_date 時点のデータのみを使用）
- 冪等性（DB への upsert / on conflict 処理）
- テスト容易性（純粋関数、DuckDB を利用した軽量ストレージ）

---

## 機能一覧

- データ取得 / ETL
  - J-Quants API クライアント（株価・財務・マーケットカレンダー）
  - RSS ニュース収集（SSRF 対策、トラッキングパラメータ除去、記事→銘柄紐付け）
  - DuckDB への保存ユーティリティ（冪等保存）
- 研究（research）
  - ファクター計算（Momentum / Volatility / Value 等）
  - ファクター探索・IC（Information Coefficient）計算など
  - Zスコア正規化ユーティリティ
- 特徴量エンジニアリング（strategy.feature_engineering）
  - raw ファクターを正規化・クリップして `features` テーブルへ保存
- シグナル生成（strategy.signal_generator）
  - features と AI スコアを統合して final_score を算出
  - BUY / SELL シグナルを生成して `signals` テーブルへ保存
  - Bear レジーム時の BUY 抑制やエグジット判定を実装
- ポートフォリオ（portfolio）
  - 候補選定（select_candidates）
  - 重み計算（等配分 / スコア加重）
  - リスク調整（セクターキャップ適用・レジーム乗数）
  - ポジションサイジング（risk_based / equal / score）
- バックテスト（backtest）
  - ポートフォリオシミュレータ（擬似約定、スリッページ・手数料モデル）
  - バックテストループ（データコピー、シグナル生成→約定→評価の一連処理）
  - メトリクス計算（CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio）
  - CLI エントリポイント（python -m kabusys.backtest.run）
- 設定（config）
  - .env 自動読み込み（プロジェクトルート検出）と環境変数アクセス用ラッパ

---

## 要件

- Python 3.10+
- 主要依存パッケージ（少なくとも次をインストールしてください）
  - duckdb
  - defusedxml
- 実運用で J-Quants 等の外部 API を利用する場合はネットワーク接続・API トークンが必要

（パッケージ化されたプロジェクトであれば pyproject.toml / requirements.txt を利用して依存を管理してください）

---

## セットアップ手順

1. リポジトリをクローンし、仮想環境を作成
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - pip install -U pip
   - pip install duckdb defusedxml

   （プロジェクトに requirements.txt / pyproject.toml があればそれに従ってください）

3. DuckDB スキーマ初期化
   - このコードベースでは `kabusys.data.schema.init_schema(path)` で DB 初期化を行う想定です（schema モジュールが存在する前提）。
   - 例（Python REPL / スクリプト）:
     ```
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     conn.close()
     ```

4. 環境変数設定
   - プロジェクトルートの `.env` / `.env.local` を読み込みます（自動ロード）。必要な環境変数を設定してください。自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
   - 主な必須環境変数:
     - JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン
     - KABU_API_PASSWORD — kabuステーション API パスワード（本番 execution 層で使用）
     - SLACK_BOT_TOKEN — Slack 通知（必要に応じて）
     - SLACK_CHANNEL_ID — Slack チャンネルID
   - 任意 / デフォルトあり:
     - KABUSYS_ENV — {development, paper_trading, live}（default: development）
     - LOG_LEVEL — {DEBUG, INFO, WARNING, ERROR, CRITICAL}（default: INFO）
     - DUCKDB_PATH — データベースパス（default: data/kabusys.duckdb）
     - SQLITE_PATH — 監視 DB（default: data/monitoring.db）

---

## 使い方（代表例）

以下は開発時に便利な代表的な操作例です。すべて Python から呼び出せます。

- DuckDB 接続の作成（schema モジュールを利用）
  ```
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")
  ```

- ファクター計算と features の作成
  ```
  from datetime import date
  from kabusys.strategy import build_features

  build_features(conn, target_date=date(2024, 1, 31))
  ```

- シグナル生成（features と ai_scores を参照して signals に書き込み）
  ```
  from kabusys.strategy import generate_signals
  generate_signals(conn, target_date=date(2024, 1, 31))
  ```

- バックテスト（CLI）
  - コマンドラインから直接実行:
    ```
    python -m kabusys.backtest.run \
      --start 2023-01-01 --end 2023-12-31 \
      --db data/kabusys.duckdb --cash 10000000
    ```
  - 主要オプション:
    - --start / --end: バックテスト期間
    - --db: DuckDB ファイル
    - --allocation-method: equal | score | risk_based（デフォルト: risk_based）
    - --slippage / --commission / --lot-size 等のパラメータを調整可能

- ニュース収集ジョブの実行（例）
  ```
  from kabusys.data.news_collector import run_news_collection
  # known_codes は stocks テーブルから取得した有効な銘柄コードの集合を渡すと抽出精度が向上します
  res = run_news_collection(conn, sources=None, known_codes=None, timeout=30)
  print(res)
  ```

- J-Quants データ取得（例）
  ```
  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
  quotes = fetch_daily_quotes(date_from=date(2023,1,1), date_to=date(2023,12,31))
  save_daily_quotes(conn, quotes)
  ```

---

## 重要な設計上の注意点

- ルックアヘッド防止
  - strategy / research / feature_engineering 等は target_date 時点で利用可能なデータのみを使うように設計されています。バックテストで信頼性を保つためこの制約を守ってください。
- .env 自動読み込み
  - パッケージはパッケージ内からプロジェクトルート（.git または pyproject.toml）を探索して `.env` / `.env.local` を自動読み込みします。自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- レート制限と再試行
  - J-Quants クライアントはレートリミット（120 req/min）を守るための簡易 RateLimiter とリトライ（指数バックオフ）を実装しています。API エラー時はログを確認してください。
- 冪等性
  - データ保存関数（save_*）は可能な限り ON CONFLICT / upsert を使い冪等に動作します。

---

## ディレクトリ構成（抜粋）

以下は主要ファイル・モジュールとその役割の簡易一覧です。

- src/kabusys/
  - __init__.py — パッケージ初期化（version 等）
  - config.py — 環境変数 / 設定管理（.env 自動読み込み・Settings クラス）
  - data/
    - jquants_client.py — J-Quants API クライアント（取得・保存ユーティリティ）
    - news_collector.py — RSS ニュース収集と raw_news 保存・銘柄抽出
    - (schema.py, stats.py, calendar_management.py など別ファイルでスキーマやユーティリティを想定)
  - research/
    - factor_research.py — Momentum/Volatility/Value 等のファクター計算
    - feature_exploration.py — forward returns / IC / summary 等の解析ユーティリティ
  - strategy/
    - feature_engineering.py — features テーブル作成（正規化・クリップ）
    - signal_generator.py — final_score 計算と signals 生成
  - portfolio/
    - portfolio_builder.py — 候補選定、重み計算
    - position_sizing.py — 株数計算、aggregate cap・単元丸め
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - backtest/
    - engine.py — バックテストエンジン（全ループ）
    - simulator.py — ポートフォリオシミュレータ（約定モデル）
    - metrics.py — バックテスト評価指標
    - run.py — CLI エントリポイント
    - clock.py — 模擬時計（将来的拡張用）
  - execution/ — 本番注文送信等（stub / 実装場所）
  - monitoring/ — 監視・アラート関連（stub / 実装場所）

注: README 内で参照されているドキュメントファイル（例: PortfolioConstruction.md, StrategyModel.md, BacktestFramework.md, DataPlatform.md）はコード内コメントで言及されています。実際の運用ではこれらの設計文書をプロジェクトルートに配置して参照してください。

---

## 追加情報

- 開発環境では `KABUSYS_ENV=development` に設定してロギングや安全制約を緩めることができます。本番では `paper_trading` / `live` を適切に使い分けてください。
- パッケージを pip install -e で編集可能インストールすることでローカル開発が容易になります。
  ```
  pip install -e .
  ```
- バックテスト結果は標準出力に主要メトリクスを表示します。必要であれば結果オブジェクト（BacktestResult）を受け取って永続化してください。

---

もし README に追記したい具体的な手順（例: schema の SQL、.env.example の具体例、CI 設定、テスト実行手順）があれば、その情報を教えてください。README をそれに合わせて拡張します。