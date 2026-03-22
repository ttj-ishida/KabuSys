# KabuSys

日本株向けの自動売買・データ基盤ライブラリ群です。  
データ取得（J-Quants）、ETL、特徴量生成、シグナル生成、バックテスト、ニュース収集、バックテスト用シミュレータなどを含むモジュール構成で、研究（research）→ 運用（execution）までを想定しています。

---

## プロジェクト概要

KabuSys は以下を目的とした Python パッケージです。

- J-Quants API などから市場データを取得し DuckDB に格納するデータパイプライン
- 研究用のファクター計算・特徴量正規化（research）
- 戦略の特徴量合成（feature engineering）とシグナル生成（strategy）
- シミュレーション（バックテスト）フレームワークとメトリクス計算（backtest）
- RSS ベースのニュース収集と銘柄紐付け（news_collector）
- DB スキーマの初期化・管理（data.schema）

設計上、ルックアヘッドバイアスの防止、冪等性（ON CONFLICT やトランザクション）やネットワークの堅牢性（レートリミット・リトライ）に配慮しています。

---

## 主な機能一覧

- データ取得
  - J-Quants から日足（OHLCV）、財務データ、マーケットカレンダーの取得（jquants_client）
  - レート制限・リトライ・トークン自動リフレッシュ対応
- ETL / パイプライン
  - 差分取得・バックフィル対応の ETL（data.pipeline）
  - 品質チェックフック（quality モジュールによる検出）
- データベース
  - DuckDB スキーマ定義と初期化（data.schema.init_schema）
  - raw / processed / feature / execution の 3 層構造
- 研究（Research）
  - ファクター計算（momentum / volatility / value）および特徴量探索（IC, forward returns）（research）
  - Z スコア正規化ユーティリティ（data.stats）
- 戦略
  - 特徴量の合成・正規化して features テーブルへ保存（strategy.feature_engineering.build_features）
  - features と ai_scores を統合して売買シグナルを生成（strategy.signal_generator.generate_signals）
- バックテスト
  - ポートフォリオシミュレータ（スリッページ・手数料モデル対応）
  - 全体ループ / データ準備 / メトリクス（CAGR, Sharpe, MaxDD, Win Rate, Payoff）算出（backtest.engine）
  - CLI エントリポイント（python -m kabusys.backtest.run）
- ニュース収集
  - RSS フィード取得、前処理、raw_news への冪等保存、銘柄コード抽出・紐付け（data.news_collector）

---

## セットアップ手順

1. リポジトリをクローン（あるいはパッケージを配置）  
   git やアーカイブからソースを取得してください。

2. Python 環境を用意（推奨: 3.9+）  
   仮想環境を作成して有効化します。
   ```
   python -m venv .venv
   source .venv/bin/activate    # Unix/macOS
   .venv\Scripts\activate.bat   # Windows
   ```

3. 必要なパッケージをインストール  
   代表的な依存例（実際の requirements.txt がない場合はプロジェクトに応じて追加してください）:
   ```
   pip install duckdb defusedxml
   ```
   追加で requests 等が必要になる箇所があれば随時インストールしてください。

4. 環境変数を設定  
   プロジェクトルートに `.env` / `.env.local` を置くと自動的に読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。主な環境変数:

   - 必須
     - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
     - SLACK_BOT_TOKEN : Slack 通知に使う Bot トークン（必要に応じて）
     - SLACK_CHANNEL_ID : Slack チャンネル ID（必要に応じて）
     - KABU_API_PASSWORD : kabuステーション API のパスワード（execution を使う場合）
   - オプション / デフォルトあり
     - KABUSYS_ENV : development | paper_trading | live（default: development）
     - LOG_LEVEL : DEBUG|INFO|WARNING|ERROR|CRITICAL（default: INFO）
     - KABU_API_BASE_URL : kabuAPI のベース URL（default: http://localhost:18080/kabusapi）
     - DUCKDB_PATH : DuckDB ファイルパス（default: data/kabusys.duckdb）
     - SQLITE_PATH : 監視用 SQLite（default: data/monitoring.db）

   config.Settings クラスでこれらの値にアクセスできます（例: from kabusys.config import settings; settings.jquants_refresh_token）。

5. DuckDB スキーマ初期化  
   デフォルトの DB パス（例: data/kabusys.duckdb）でスキーマを作る例:
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   conn.close()
   ```
   またはコマンドラインで Python を使って同様に実行してください。

---

## 使い方（代表的な例）

- バックテスト（CLI）
  ```
  python -m kabusys.backtest.run \
      --start 2023-01-01 --end 2023-12-31 \
      --cash 10000000 \
      --db data/kabusys.duckdb
  ```

- バックテスト（プログラムから呼び出す）
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.backtest.engine import run_backtest

  conn = init_schema("data/kabusys.duckdb")
  result = run_backtest(conn, start_date, end_date, initial_cash=10_000_000)
  conn.close()

  # result.history, result.trades, result.metrics にアクセス
  ```

- DuckDB スキーマの初期化（スクリプト）
  ```python
  from kabusys.data.schema import init_schema
  init_schema("data/kabusys.duckdb")
  ```

- データ取得 / ETL（概念）
  - J-Quants クライアント:
    - fetch_daily_quotes / save_daily_quotes
    - fetch_financial_statements / save_financial_statements
    - fetch_market_calendar / save_market_calendar
  - ETL の差分処理は kabusys.data.pipeline の run_prices_etl / run_financials_etl 等を利用
  （パイプラインは target_date とバックフィル期間を渡して呼び出します）

- 特徴量構築（戦略側）
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.strategy import build_features

  conn = init_schema("data/kabusys.duckdb")
  count = build_features(conn, target_date)
  conn.close()
  ```

- シグナル生成
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.strategy import generate_signals

  conn = init_schema("data/kabusys.duckdb")
  n = generate_signals(conn, target_date)
  conn.close()
  ```

- ニュース収集（RSS）
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.data.news_collector import run_news_collection

  conn = init_schema("data/kabusys.duckdb")
  results = run_news_collection(conn, sources=None, known_codes=set_of_codes)
  conn.close()
  ```

- 注意点
  - generate_signals / build_features は target_date 時点のデータのみを参照する設計（ルックアヘッドバイアス防止）。
  - DB への書き込みは日付単位の「置換（DELETE -> INSERT）」で冪等性を保っています。
  - API 呼び出しを行う箇所はレート制御・リトライが組み込まれていますが、API トークンや接続先は環境変数で正しく設定してください。

---

## ディレクトリ構成（抜粋）

以下は主要なモジュールと役割です（src/kabusys 配下）:

- kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込みと Settings クラス
  - data/
    - __init__.py
    - jquants_client.py        : J-Quants API クライアント（取得・保存）
    - news_collector.py       : RSS 収集・前処理・DB 保存
    - schema.py               : DuckDB スキーマ定義・初期化
    - stats.py                : zscore_normalize 等の統計ユーティリティ
    - pipeline.py             : ETL パイプライン（差分取得・バックフィル）
  - research/
    - __init__.py
    - factor_research.py      : momentum/volatility/value 等のファクター計算
    - feature_exploration.py  : forward returns / IC / 統計サマリ
  - strategy/
    - __init__.py
    - feature_engineering.py  : features の合成・正規化・保存
    - signal_generator.py     : final_score 計算と signals 生成
  - backtest/
    - __init__.py
    - engine.py               : バックテスト全体ループ（run_backtest）
    - simulator.py            : PortfolioSimulator, 約定ロジック
    - metrics.py              : バックテスト評価指標
    - run.py                  : CLI エントリポイント
    - clock.py                : SimulatedClock（将来拡張用）
  - execution/                : 発注・実行層（空の __init__）
  - monitoring/               : 監視関連（実装に応じて追加）

---

## 開発上のヒント / 注意事項

- 環境変数自動読み込み:
  - パッケージはプロジェクトルート（.git または pyproject.toml を探索）から .env / .env.local を自動読み込みします。テスト等で無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB の利用:
  - 初回は init_schema() でスキーマを作成してください。":memory:" を指定するとインメモリ DB が作成され、バックテストの単体実行に便利です。
- ロギング:
  - 設定は環境変数 LOG_LEVEL で制御します。デバッグ時は DEBUG に設定してください。
- 安全性:
  - news_collector は SSRF 対策や XML 攻撃対策（defusedxml）を行っていますが、外部データを扱う際の一般的な注意（信頼できるソースの利用、タイムアウト設定等）をしてください。

---

以上がこのリポジトリの概要と基本的な使い方です。詳細な設計仕様（StrategyModel.md / DataPlatform.md / BacktestFramework.md 等）がプロジェクト内に別途ある想定ですので、運用時はそれらの設計文書も参照してください。必要であれば README にサンプル .env.example や requirements.txt、起動スクリプトの追加例を追記できます。