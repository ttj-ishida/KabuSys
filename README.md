# KabuSys

日本株向けの自動売買システム基盤ライブラリ（研究・データパイプライン・戦略・バックテスト・発注レイヤーの骨組み）。

このリポジトリは DuckDB をデータストアに用い、J-Quants API や RSS ニュースを取り込み、ファクター計算・シグナル生成・バックテストを行えるように設計されています。各モジュールは「ルックアヘッドバイアス防止」「冪等性」「堅牢なネットワーク処理」「テスト容易性」を念頭に実装されています。

主な設計方針・特徴
- DuckDB ベースのスキーマ定義とインメモリバックテスト対応
- J-Quants API クライアント（レート制御・リトライ・トークン自動更新）
- RSS ベースのニュース収集（SSRF 対策・トラッキング除去・重複排除）
- ファクター計算（モメンタム／ボラティリティ／バリュー等）
- 特徴量正規化 → シグナル生成（BUY/SELL）→ 発注シミュレータ（バックテスト）
- ETL / 品質チェックのためのパイプラインユーティリティ

---

## 機能一覧

- data/
  - jquants_client: J-Quants API から OHLCV / 財務 / カレンダーを取得・保存
  - news_collector: RSS からニュースを収集し raw_news / news_symbols に保存
  - schema: DuckDB スキーマ定義と init_schema(), get_connection()
  - stats: Z スコア正規化等の統計ユーティリティ
  - pipeline: 差分 ETL のユーティリティ（差分取得・バックフィル等）
- research/
  - factor_research: momentum / volatility / value 等のファクター計算（DuckDB SQL ベース）
  - feature_exploration: 将来リターン計算・IC（Spearman）・統計サマリ
- strategy/
  - feature_engineering: raw factor を正規化して features テーブルへ保存
  - signal_generator: features と ai_scores を統合して BUY/SELL シグナルを生成
- backtest/
  - engine: run_backtest による日次バックテストループ（インメモリ DB コピー）
  - simulator: PortfolioSimulator（擬似約定、スリッページ・手数料モデル）
  - metrics: バックテスト評価指標（CAGR, Sharpe, MaxDD, WinRate, Payoff 等）
  - run: CLI エントリポイント（python -m kabusys.backtest.run）
- config: 環境変数読み込み・設定管理（.env 自動読み込み・必須変数チェック）
- execution/ monitoring/ (発注・監視レイヤーのためのプレースホルダ)

---

## セットアップ手順

前提
- Python 3.9+（型アノテーションや一部の記法を利用）
- Git リポジトリをクローン済み

1. 仮想環境の作成（推奨）
   - venv または pyenv/conda 等を使用してください。
   - 例:
     ```
     python -m venv .venv
     source .venv/bin/activate  # macOS / Linux
     .venv\Scripts\activate     # Windows
     ```

2. 必要パッケージのインストール
   - 本コードベースでは少なくとも以下が必要です:
     - duckdb
     - defusedxml
   - pip でインストール:
     ```
     pip install duckdb defusedxml
     ```
   - 開発用にその他パッケージがあれば requirements.txt を用意している場合はそれに従ってください（本リポジトリでは省略）。

3. パッケージを開発モードでインストール（任意）
   ```
   pip install -e .
   ```

4. 環境変数の設定
   - プロジェクトルートに `.env` または `.env.local` を配置すると自動的に読み込まれます（config.py の自動ロード）。
   - 自動ロードを無効化する場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 必須の環境変数（config.Settings に基づく）
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
     - SLACK_BOT_TOKEN: Slack 通知用 BOT トークン（必須）
     - SLACK_CHANNEL_ID: Slack 通知先チャンネル ID（必須）
   - 任意・デフォルト
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）

   - 例 `.env`（プロジェクトルート）:
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     DUCKDB_PATH=data/kabusys.duckdb
     ```

5. DuckDB スキーマ初期化
   - Python REPL もしくはスクリプトから:
     ```python
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     conn.close()
     ```
   - インメモリ DB を試す場合:
     ```python
     conn = init_schema(":memory:")
     ```

---

## 使い方（主要な操作）

1. J-Quants データ取得 / 保存
   - ID トークンの取得:
     ```python
     from kabusys.data.jquants_client import get_id_token
     token = get_id_token()  # settings.jquants_refresh_token が使われる
     ```
   - 日足取得 & 保存:
     ```python
     from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
     rows = fetch_daily_quotes(date_from=..., date_to=...)
     saved = save_daily_quotes(conn, rows)
     ```

2. ニュース収集
   - RSS を取得して DB に保存:
     ```python
     from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
     results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=set_of_codes)
     ```

3. ファクター計算・特徴量構築
   - research のファクター計算（DuckDB 接続と日付を渡す）:
     ```python
     from kabusys.research import calc_momentum, calc_volatility, calc_value
     mom = calc_momentum(conn, target_date)
     vol = calc_volatility(conn, target_date)
     val = calc_value(conn, target_date)
     ```
   - features テーブル作成:
     ```python
     from kabusys.strategy import build_features
     n = build_features(conn, target_date)
     ```

4. シグナル生成
   - features / ai_scores / positions を参照して signals を生成:
     ```python
     from kabusys.strategy import generate_signals
     num = generate_signals(conn, target_date)
     ```

5. バックテスト
   - CLI 実行（DuckDB ファイルに必要なテーブルが存在することが前提）:
     ```
     python -m kabusys.backtest.run \
       --start 2023-01-01 --end 2023-12-31 \
       --cash 10000000 --db data/kabusys.duckdb
     ```
   - Python から run_backtest を直接呼ぶ:
     ```python
     from kabusys.data.schema import init_schema
     from kabusys.backtest.engine import run_backtest
     conn = init_schema("data/kabusys.duckdb")
     result = run_backtest(conn, start_date, end_date)
     conn.close()
     # result.history, result.trades, result.metrics を利用
     ```

6. ETL パイプライン（差分取得）
   - data.pipeline に差分 ETL 用ユーティリティが用意されています（run_prices_etl 等）。ETL 実行例:
     ```python
     from kabusys.data.pipeline import run_prices_etl
     fetched, saved = run_prices_etl(conn, target_date)
     ```
   - 詳細は pipeline モジュールのドキュメント文字列を参照してください。

---

## ディレクトリ構成

（主要ファイル抜粋）

- src/kabusys/
  - __init__.py
  - config.py  — 環境変数管理（.env 自動ロード・必須チェック）
  - data/
    - __init__.py
    - jquants_client.py
    - news_collector.py
    - schema.py
    - stats.py
    - pipeline.py
    - (その他: quality.py など想定)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - strategy/
    - __init__.py
    - feature_engineering.py
    - signal_generator.py
  - backtest/
    - __init__.py
    - engine.py
    - simulator.py
    - metrics.py
    - clock.py
    - run.py  — CLI エントリポイント
  - execution/  — 発注関連（現状プレースホルダ）
  - monitoring/ — 監視関連（プレースホルダ）

---

## 注意事項 / 実運用への留意点

- 環境変数は機密情報を含むため、`.env` はバージョン管理しないこと（.gitignore に追加）。
- J-Quants API レート制限を順守するため、fetch は内部でレート制御が入っています。大量取得時は注意。
- ニュース収集では外部 URL を扱うため SSRF 対策やサイズ制限を実装していますが、運用環境ではプロキシやネットワークポリシーも考慮してください。
- live での発注処理（execution 層）は本リポジトリのコードを拡張して実装する必要があります。現行コードはバックテスト・戦略生成・ETL を中心に提供します。
- DuckDB スキーマは将来的な互換性のためマイグレーション方針を別途策定してください。

---

## 補足

- config.py はプロジェクトルート（.git または pyproject.toml）を基準に .env/.env.local を自動ロードします。テスト等で自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
- 多くの関数は「DuckDB 接続を引数に取る」設計で、テスト時にインメモリ DB (":memory:") を使いやすくしてあります。
- 仕様書（StrategyModel.md、DataPlatform.md、BacktestFramework.md 等）が参照されています。実装の詳細や数値パラメータはそれらのドキュメントに合わせて調整してください。

---

必要であれば以下も作成します
- .env.example のテンプレートファイル
- 具体的な ETL の実行スクリプト例（cron / Airflow / Prefect 等向け）
- 各モジュールの API リファレンス（関数一覧と引数説明）の自動生成手順

ご希望があれば続けて追加で作成します。