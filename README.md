# KabuSys

KabuSys は日本株向けの自動売買・リサーチ基盤です。データ取得（J-Quants / RSS）、ファクター計算、特徴量生成、シグナル生成、ポートフォリオ構築、バックテストシミュレータなどをモジュール化して提供します。設計はルックアヘッドバイアス回避・冪等性・明示的なトランザクション設計を重視しています。

主な目的：
- 研究（ファクター探索・検証）と運用（シグナル生成・執行）を分離
- DuckDB を中核にした効率的なデータ処理
- バックテストと実運用ロジックの整合性を保った設計

---

## 機能一覧

- 環境設定管理
  - .env / .env.local からの自動読み込み（プロジェクトルート検出）、必須環境変数のラップ
- データ取得・ETL
  - J-Quants API クライアント（ページネーション、リトライ、レート制限、トークンリフレッシュ）
  - RSS ニュース収集（SSRF 対策、gzip 対応、トラッキングパラメータ除去、記事ID生成）
  - DuckDB への冪等的な保存ユーティリティ（ON CONFLICT/トランザクション）
- 研究（research）
  - Momentum / Volatility / Value 等の定量ファクター計算
  - ファクター探索用ユーティリティ（forward returns、IC、統計サマリー）
- 特徴量エンジニアリング（strategy.feature_engineering）
  - ファクターの正規化・ユニバースフィルタ・features テーブルへの UPSERT
- シグナル生成（strategy.signal_generator）
  - features + ai_scores を統合して final_score を算出
  - Bear レジーム検出による BUY 抑制、SELL（エグジット）判定
  - signals テーブルへの冪等書き込み
- ポートフォリオ構築（portfolio）
  - 候補選定、等配分/スコア配分、リスクベースのポジションサイズ計算
  - セクター集中制限、レジーム乗数
- バックテストフレームワーク（backtest）
  - インメモリ DuckDB の構築、バックテストループ、擬似約定（スリッページ・手数料）、メトリクス計算
  - CLI からの実行エントリポイント（python -m kabusys.backtest.run）
- 実運用（execution）・監視（monitoring）
  - パッケージ API をエクスポート（将来的な実装ポイント）

---

## セットアップ手順

前提
- Python 3.9+（コードは型ヒントで 3.10 以降を想定している部分あり）
- DuckDB が利用可能な環境

1. リポジトリをクローンして作業ディレクトリへ移動
   - 例:
     - git clone <repo-url>
     - cd <repo-root>

2. 仮想環境を作成し有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. パッケージをインストール（プロジェクトに requirements.txt がある場合はそれを利用）
   - 例（最小依存）:
     - pip install duckdb defusedxml
   - 開発時は editable インストール:
     - pip install -e .

4. 環境変数設定
   - プロジェクトルート（.git または pyproject.toml の存在するディレクトリ）に `.env` または `.env.local` を配置すると自動的に読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

   - 必須となる主な環境変数（コード中で _require によって参照されるもの）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID

   - 推奨設定 / オプション:
     - KABUSYS_ENV (development | paper_trading | live) — default: development
     - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — default: INFO
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1（テスト用途にて自動ロードを無効化）

   - .env のサンプル:
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
     KABU_API_PASSWORD=your_kabu_password_here
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

---

## 使い方（主要な例）

- DuckDB スキーマ初期化 / DB 操作
  - コード内の `kabusys.data.schema.init_schema`（プロジェクト内に存在）を使って DuckDB 接続を作成します。
    - 例:
      ```python
      from kabusys.data.schema import init_schema
      conn = init_schema("data/kabusys.duckdb")
      ```

- J-Quants からデータ取得して保存
  - 例: 日足をフェッチして保存
    ```python
    from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
    from kabusys.config import settings
    from kabusys.data.schema import init_schema
    conn = init_schema(settings.duckdb_path)
    records = fetch_daily_quotes(date_from=date(2023,1,1), date_to=date(2023,12,31))
    save_daily_quotes(conn, records)
    conn.close()
    ```

- RSS ニュース収集
  - 例:
    ```python
    from kabusys.data.news_collector import run_news_collection
    from kabusys.data.schema import init_schema
    conn = init_schema("data/kabusys.duckdb")
    # known_codes は銘柄抽出に使う有効コード集合（任意）
    results = run_news_collection(conn, sources=None, known_codes={"7203","6758"})
    conn.close()
    ```

- 特徴量構築（features）
  - 例:
    ```python
    from datetime import date
    import duckdb
    from kabusys.strategy.feature_engineering import build_features
    conn = duckdb.connect("data/kabusys.duckdb")
    cnt = build_features(conn, target_date=date(2024,1,31))
    print(f"features upserted: {cnt}")
    conn.close()
    ```

- シグナル生成
  - 例:
    ```python
    from datetime import date
    import duckdb
    from kabusys.strategy.signal_generator import generate_signals
    conn = duckdb.connect("data/kabusys.duckdb")
    total = generate_signals(conn, target_date=date(2024,1,31))
    print(f"signals written: {total}")
    conn.close()
    ```

- バックテスト（CLI）
  - DuckDB に prices_daily / features / ai_scores / market_regime / market_calendar が準備されていることが前提です。
  - 例:
    ```
    python -m kabusys.backtest.run \
      --start 2023-01-01 --end 2024-12-31 \
      --cash 10000000 --db data/kabusys.duckdb \
      --allocation-method risk_based --lot-size 100
    ```
  - 実行後、CAGR / Sharpe / Max Drawdown / Win Rate / Payoff Ratio / Total Trades が標準出力に表示されます。

- バックテストをコードから呼ぶ
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.backtest.engine import run_backtest
  conn = init_schema("data/kabusys.duckdb")
  result = run_backtest(conn, start_date=date(2023,1,1), end_date=date(2023,12,31))
  # result.history, result.trades, result.metrics を利用
  conn.close()
  ```

---

## ディレクトリ構成

主要ファイル・モジュールのツリー（src/kabusys 以下の抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py            — J-Quants API クライアント（取得 + 保存）
    - news_collector.py            — RSS ニュース収集・保存・銘柄抽出
    - schema.py                    — (DB スキーマ初期化: プロジェクトに実装あり)
    - calendar_management.py       — 取引日取得等（参照されるユーティリティ）
    - stats.py                     — 正規化等ユーティリティ
  - research/
    - __init__.py
    - factor_research.py           — ファクター計算（momentum/vol/val）
    - feature_exploration.py       — IC / forward returns / summary
  - strategy/
    - __init__.py
    - feature_engineering.py       — features テーブル生成
    - signal_generator.py          — final_score 計算・signals 生成
  - portfolio/
    - __init__.py
    - portfolio_builder.py         — 候補選定、等配分/スコア配分
    - position_sizing.py           — 発注株数算出（risk_based 等）
    - risk_adjustment.py           — セクターキャップ・レジーム乗数
  - backtest/
    - __init__.py
    - engine.py                    — バックテストのメインロジック
    - simulator.py                 — 擬似約定・ポートフォリオ管理
    - metrics.py                   — バックテスト評価指標
    - run.py                       — CLI エントリポイント
    - clock.py                     — 将来拡張用の模擬時計
  - execution/                      — 実運用執行ロジック（プレースホルダ / 拡張点）
  - monitoring/                     — 監視・メトリクス収集（拡張点）

各モジュールは可能な限り「DB非依存（純粋関数）」「冪等」「ルックアヘッド防止（target_date ベース）」を守る実装方針です。

---

## 開発メモ / 注意点

- 環境変数の自動ロードはプロジェクトルート（.git または pyproject.toml）から .env / .env.local を読み込みます。テスト時やカスタム起動時に自動ロードを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- J-Quants API はレート制限（120 req/min）や 401 リフレッシュ処理、リトライが組み込まれています。実行時は API 利用ルールに従ってください。
- DuckDB のスキーマやテーブル（prices_daily, raw_prices, raw_financials, features, ai_scores, signals, positions, market_regime, market_calendar など）はプロジェクト内の schema 実装に従って初期化してください。
- NewsCollector は外部ネットワークアクセスを行うため、SSRF/サイズ上限/XML 脆弱性対策が組み込まれています。fetch_rss/_urlopen をテスト用にモック可能です。

---

何か追加したい情報（例: 詳細な schema 定義、依存パッケージの完全な一覧、具体的な実行例のスクリプトなど）があれば教えてください。README をその内容に合わせて拡張します。