# KabuSys

日本株向けの自動売買基盤ライブラリです。データ取得（J‑Quants）、ETL、特徴量作成、シグナル生成、バックテスト、ニュース収集などの主要機能を含み、DuckDB をデータストアとして利用する設計になっています。

---

## プロジェクト概要

KabuSys は以下を目的としたモジュール群を提供します。

- J‑Quants API からの株価 / 財務 / カレンダー取得
- ETL（差分取得・保存・品質チェック）
- 研究用ファクター計算（momentum / volatility / value 等）
- 特徴量の正規化と features テーブルへの保存
- シグナル生成（final_score 計算、BUY/SELL 判定）
- バックテストフレームワーク（シミュレーション、メトリクス算出）
- RSS によるニュース収集と銘柄紐付け

設計上の特徴：
- ルックアヘッドバイアスを避けるため、target_date 時点のデータのみを使用
- DuckDB を用いたローカル一元データベース（:memory: もサポート）
- API 呼び出しはレート制限・リトライ・トークン自動リフレッシュ対応
- DB 操作は冪等性（ON CONFLICT / トランザクション）を意識

---

## 主な機能一覧

- data/
  - jquants_client: J‑Quants API クライアント（ページネーション・リトライ・レート制限対応）
  - pipeline: ETL（差分取得、保存、品質チェックの入口）
  - news_collector: RSS 収集・前処理・DB 保存・銘柄抽出
  - schema: DuckDB スキーマ初期化（init_schema）
  - stats: 汎用統計ユーティリティ（Z スコア正規化等）
- research/
  - factor_research: momentum / volatility / value 等のファクター計算
  - feature_exploration: 将来リターン計算、IC、ファクター統計
- strategy/
  - feature_engineering: 生ファクターを正規化して features テーブルへ保存
  - signal_generator: features と AI スコアを統合して シグナル生成
- backtest/
  - engine: run_backtest（インメモリ DB コピー → 日次ループ → シミュレーション）
  - simulator: PortfolioSimulator（約定ロジック、mark-to-market）
  - metrics: バックテストメトリクス計算
  - run: CLI エントリ（python -m kabusys.backtest.run）
- config: 環境変数管理（.env 自動ロード、必須キー検証）
- execution / monitoring: 発注・モニタリング用の拡張ポイント（実装ベース）

---

## 必要環境 / 依存パッケージ（代表例）

最低限必要な Python パッケージ（本コードベースから明示できるもの）：

- Python 3.9+
- duckdb
- defusedxml

※その他は標準ライブラリのみで多くの処理を実装しています。プロジェクトで使用する場合は pip で必要パッケージを追加してください。

例:
pip install duckdb defusedxml

---

## セットアップ手順

1. Python 仮想環境を作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb defusedxml
   - （プロジェクトで requirements.txt を用意する場合はそちらを使用）

3. DuckDB スキーマ初期化
   - Python REPL またはスクリプトで以下を実行:
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     conn.close()
   - またはメモリ DB:
     conn = init_schema(":memory:")

4. 環境変数設定 (.env)
   - プロジェクトルートに `.env` や `.env.local` を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須環境変数（config.Settings が参照します）:
     - JQUANTS_REFRESH_TOKEN: J‑Quants のリフレッシュトークン
     - KABU_API_PASSWORD: kabu ステーション API のパスワード（発注連携を使用する場合）
     - SLACK_BOT_TOKEN: 通知に Slack を使う場合
     - SLACK_CHANNEL_ID: 同上
   - 任意:
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL: DEBUG/INFO/...
     - DUCKDB_PATH / SQLITE_PATH

   例 .env:
   JQUANTS_REFRESH_TOKEN=your_refresh_token_here
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development
   LOG_LEVEL=INFO

---

## 使い方（代表的な操作例）

1. DuckDB スキーマ初期化
   - 上記のとおり init_schema() を呼び出して DB を初期化します。

2. J‑Quants からデータ取得・保存（例: 日足の差分 ETL）
   - data.jquants_client.fetch_daily_quotes を利用してデータを取得し、save_daily_quotes で保存できます。
   - ETL のラッパー（差分ロジック含む）:
     from kabusys.data.pipeline import run_prices_etl
     result = run_prices_etl(conn, target_date=date.today())
     # run_prices_etl は (fetched, saved) を返します（pipeline 内の API 呼び出しは settings.jquants_refresh_token を使用）

3. ニュース収集（RSS）
   - from kabusys.data.news_collector import run_news_collection
     results = run_news_collection(conn, sources=None, known_codes=set_of_codes)
   - ソースは DEFAULT_RSS_SOURCES を利用するか独自辞書を渡します。

4. 特徴量ビルド（features テーブルに保存）
   - from kabusys.strategy import build_features
     count = build_features(conn, target_date)
   - 内部で research.factor_research の calc_* を呼び、ユニバースフィルタ → Z スコア正規化 → features への UPSERT を行います。

5. シグナル生成
   - from kabusys.strategy import generate_signals
     n = generate_signals(conn, target_date, threshold=0.6, weights=None)
   - ai_scores, features, positions を参照して BUY/SELL を決定し signals テーブルに日付単位で置換保存します。

6. バックテスト実行（CLI）
   - DB を用意して（prices_daily / features / ai_scores / market_regime / market_calendar が必要）:
     python -m kabusys.backtest.run \
       --start 2023-01-01 --end 2023-12-31 \
       --cash 10000000 --db data/kabusys.duckdb
   - run_backtest() は内部で本番 DB からインメモリにデータをコピーしてシミュレーションを実行します。

7. バックテスト API を直接使う
   - from kabusys.backtest.engine import run_backtest
     result = run_backtest(conn, start_date, end_date, initial_cash=10_000_000)
     # result.history, result.trades, result.metrics を利用

---

## 設定 / 注意事項

- .env 自動ロード:
  - kabusys.config はプロジェクトルート（.git または pyproject.toml を基準）を探索し .env/.env.local を自動で読み込みます。テスト等で自動ロードを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- J‑Quants API のレート制限:
  - デフォルトで 120 req/min を守るレートリミッタが実装されています。大量データの取得時は時間をかけて取得してください。
- 冪等性:
  - DuckDB への保存関数は ON CONFLICT やトランザクションを用いて可能な限り冪等に動作するよう設計されています。
- ログレベル:
  - 環境変数 LOG_LEVEL で設定可能（DEBUG/INFO/...）。設定ミスや不正な値があると Settings が例外を出します。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み・Settings クラス（必須キーチェック、.env 自動ロード）
  - data/
    - __init__.py
    - jquants_client.py            # J‑Quants API クライアント（取得/保存ユーティリティ）
    - news_collector.py           # RSS 取得・前処理・DB 保存・銘柄抽出
    - pipeline.py                 # ETL パイプライン（差分取得等）
    - schema.py                   # DuckDB スキーマ定義と init_schema()
    - stats.py                    # zscore 等の統計ユーティリティ
  - research/
    - __init__.py
    - factor_research.py          # momentum/volatility/value の計算
    - feature_exploration.py      # IC / forward returns / summary 等
  - strategy/
    - __init__.py
    - feature_engineering.py      # features テーブル構築（正規化・フィルタ）
    - signal_generator.py         # final_score 計算・BUY/SELL 生成
  - backtest/
    - __init__.py
    - engine.py                   # run_backtest（インメモリコピー + 日次ループ）
    - simulator.py                # PortfolioSimulator（約定ロジック）
    - metrics.py                  # バックテストメトリクス計算
    - run.py                      # CLI エントリポイント
    - clock.py                    # SimulatedClock（将来拡張用）
  - execution/                     # 発注層の拡張ポイント（空の __init__）
  - monitoring/                    # モニタリング用モジュール（拡張ポイント）

---

## 開発 / 貢献

- 型付けとドキュメントストリングが豊富に付与されています。ユニットテストや CI を追加して検証を強化してください。
- DB スキーマを変更する場合は data/schema.py の DDL を更新し、互換性を考慮してください。
- セキュリティ注意:
  - news_collector は SSRF / XML Bomb 等の対策（defusedxml、リダイレクト検査、サイズ制限）を講じています。外部の RSS ソースを追加する際は注意してください。

---

README はここまでです。必要なら以下を作成できます：
- .env.example（テンプレート）
- requirements.txt / pyproject.toml の雛形
- 実行例スクリプト（ETL を順に実行する runner）