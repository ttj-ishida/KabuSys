# KabuSys

日本株向けの自動売買 / 研究プラットフォーム用ライブラリ（モジュール群）。
バックテスト、特徴量計算、シグナル生成、データ収集（J-Quants / RSS）、ポートフォリオ構築などの主要機能を含み、DuckDB をデータ層として想定しています。

---

## 概要

KabuSys は以下の目的を持つ純 Python のコードベースです。

- 市場データ（OHLCV・財務・カレンダー）を取得・保存
- 研究環境でのファクター計算・特徴量作成
- ファクターと AI スコアを統合したシグナル生成
- ポートフォリオ構築（候補選定、配分、サイジング、リスク制御）
- バックテストエンジン（擬似約定・手数料・スリッページモデル・評価指標）
- RSS ニュース収集と銘柄紐付け

設計方針として「ルックアヘッドバイアスを防ぐ」「DB への冪等保存」「ネットワーク安全対策（SSRF 等）」などが明示されています。

---

## 主な機能一覧

- 環境設定管理
  - プロジェクトルートの .env / .env.local 自動読み込み（無効化可）
  - 必須環境変数のラッパ（settings オブジェクト）

- データ取得 / 保存
  - J-Quants API クライアント（認証・ページネーション・リトライ・レート制御）
  - DuckDB への保存ユーティリティ（raw_prices / raw_financials / market_calendar など）
  - RSS フィード収集（SSRF対策、gzip/サイズ上限、XML安全パース、記事ID生成）
  - ニュース→銘柄コード抽出・DB保存

- 研究（research）
  - ファクター計算: momentum / volatility / value（prices_daily / raw_financials 参照）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
  - Z スコア正規化ユーティリティの利用

- 特徴量・シグナル（strategy）
  - features の構築（正規化・ユニバースフィルタ・UPSERT）
  - final_score 計算と BUY/SELL シグナル生成（Bear レジーム抑制・SELL 優先ポリシー）
  - signals テーブルへ冪等書き込み

- ポートフォリオ（portfolio）
  - 候補選定（スコア順）
  - 重み計算（等配分、スコア加重）
  - サイジング（risk_based / equal / score、lot丸め、aggregate cap、コストバッファ）
  - セクター集中制限、レジーム乗数

- バックテスト（backtest）
  - run_backtest(): インメモリ DuckDB コピーで安全にバックテスト
  - ポートフォリオシミュレータ（擬似約定、スリッページ、手数料、部分約定）
  - 日次スナップショット / TradeRecord / トレード履歴
  - 指標計算: CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio
  - CLI エントリポイント: python -m kabusys.backtest.run

- ユーティリティ（data / monitoring / execution 等の土台）

---

## セットアップ手順

※ 本リポジトリは DuckDB ベースのスキーマ（tables）を前提にしています。スキーマ初期化関数（例: kabusys.data.schema.init_schema）が想定されており、実行前に DB を準備してください。

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. Python 仮想環境（推奨: 3.10+）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール
   - 本コードベースで明示的に使用されている外部ライブラリ:
     - duckdb
     - defusedxml
   ```
   pip install duckdb defusedxml
   ```
   - （必要に応じて）その他依存を追加してください。

4. 環境変数 / .env の準備
   プロジェクトルートに `.env`（および必要なら `.env.local`）を置くと自動読み込みされます。
   自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   主要な環境変数:
   - JQUANTS_REFRESH_TOKEN         （必須）J-Quants リフレッシュトークン
   - KABU_API_PASSWORD             （必須）kabuステーション API パスワード
   - KABU_API_BASE_URL             （任意, default=http://localhost:18080/kabusapi）
   - SLACK_BOT_TOKEN               （必須）Slack 通知用（本コード中で参照）
   - SLACK_CHANNEL_ID              （必須）Slack 通知先
   - DUCKDB_PATH                   （任意, default=data/kabusys.duckdb）
   - SQLITE_PATH                   （任意, default=data/monitoring.db）
   - KABUSYS_ENV                   （任意, development|paper_trading|live）
   - LOG_LEVEL                     （任意, DEBUG|INFO|WARNING|ERROR|CRITICAL）

   例（.env）
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   KABU_API_PASSWORD=yyyy
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   ```

5. DuckDB スキーマ準備
   - スキーマ初期化関数（例: kabusys.data.schema.init_schema）を呼ぶか、用意済みの DuckDB ファイルを使用してください。
   - バックテスト用 DB は prices_daily, features, ai_scores, market_regime, market_calendar が必要です。

---

## 使い方（抜粋）

- バックテスト（CLI）
  ```
  python -m kabusys.backtest.run \
    --start 2023-01-01 --end 2023-12-31 \
    --cash 10000000 --db path/to/kabusys.duckdb
  ```

  利用可能なオプション（抜粋）:
  - --slippage, --commission, --max-position-pct, --allocation-method, --max-utilization, --max-positions, --risk-pct, --stop-loss-pct, --lot-size

- Python API（例）

  - DuckDB 接続の初期化（実装例は data.schema に存在）
    ```
    from kabusys.data.schema import init_schema
    conn = init_schema("data/kabusys.duckdb")
    ```

  - 特徴量構築
    ```
    from datetime import date
    from kabusys.strategy import build_features

    build_features(conn, target_date=date(2024, 1, 10))
    ```

  - シグナル生成
    ```
    from kabusys.strategy import generate_signals

    generate_signals(conn, target_date=date(2024, 1, 10))
    ```

  - バックテストをプログラムから呼ぶ
    ```
    from kabusys.backtest.engine import run_backtest
    result = run_backtest(conn, start_date, end_date, initial_cash=10_000_000)
    print(result.metrics.cagr, result.metrics.sharpe_ratio)
    ```

  - RSS ニュース収集（記事抽出・保存）
    ```
    from kabusys.data.news_collector import run_news_collection

    known_codes = {"7203", "6758", ...}  # stocks テーブル等から取得する想定
    run_news_collection(conn, sources=None, known_codes=known_codes)
    ```

- 環境自動ロードの無効化（テスト時等）
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```

---

## ディレクトリ構成

以下は主要なファイル/モジュールのツリー（抜粋）です:

- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - jquants_client.py
    - news_collector.py
    - (schema.py, calendar_management.py 等を想定)
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - strategy/
    - feature_engineering.py
    - signal_generator.py
    - __init__.py
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
    - __init__.py
  - execution/            (エグゼキューション層の雛形)
  - monitoring/           (監視・アラート用の雛形)
  - portfolio/            (先述のポートフォリオ関連)
  - research/             (先述の研究関連)

（実際のリポジトリ内にさらに多くのモジュール・補助ユーティリティが含まれる想定です）

---

## 注意点 / 実運用に向けた補足

- DuckDB スキーマ（テーブル定義）は本 README に含まれていません。init_schema 等で DB を初期化してください。
- J-Quants API はレート制限・認証を厳守してください（jquants_refresh_token が必要）。
- ニュース収集は外部 HTTP を行うため SSRF 対策やタイムアウト設定に注意していますが、運用時はネットワークポリシーを確認してください。
- 本コードベースはリサーチとバックテストを重視しており、本番の自動売買（実際の注文送信）にはさらに検証・運用周りの実装（例外処理、再実行性、マルチプロセス対応、監視、取引所制約への対応）が必要です。
- .env の自動ロードはプロジェクトルート（.git または pyproject.toml を基準）を探索して行われます。配布後に動作する設計ですが、CI/テストでは無効化することが推奨されます。

---

## 貢献 / ライセンス

- 実装・設計に関する改善提案や PR を歓迎します。リポジトリ内の CONTRIBUTING.md / LICENSE を参照してください（存在する場合）。

---

README はここまでです。必要であれば、サンプル .env.example、DuckDB スキーマ定義、またはよく使うコマンドの具体例（バックテストのワークフロー、ETL パイプライン例）を追加で作成します。どの情報を優先して追加しますか？