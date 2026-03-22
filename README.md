# KabuSys — 日本株自動売買システム

概要
----
KabuSys は日本株のデータ取得、特徴量作成、シグナル生成、バックテスト、ETL パイプラインを含む自動売買システムのコアライブラリです。  
主に以下の役割を持つモジュールで構成されています。

- データ取得・保存（J-Quants API クライアント、RSS ニュース収集）
- データスキーマ（DuckDB）と ETL パイプライン
- 研究用ファクター計算 / 特徴量生成
- 戦略（特徴量の正規化、シグナル生成）
- バックテスト実行器（ポートフォリオシミュレータ、メトリクス）
- ニュース / AI スコア連携用のテーブル群

主な機能
--------
- J-Quants API クライアント
  - レート制限・リトライ・トークン自動更新を備えた堅牢な HTTP クライアント
  - 日足（OHLCV）、財務データ、マーケットカレンダー取得
  - DuckDB への冪等保存（ON CONFLICT 処理）
- ニュース収集
  - RSS フィードからの記事取得、前処理、記事ID生成（URL 正規化 + SHA-256）
  - SSRF 対策、サイズ制限、XML の安全パース（defusedxml）
  - raw_news / news_symbols への冪等保存
- データスキーマ（DuckDB）
  - Raw / Processed / Feature / Execution 層のテーブル定義とインデックス
  - init_schema() で初期化、:memory: もサポート
- 研究用ファクター計算
  - Momentum / Volatility / Value 等を prices_daily / raw_financials から計算
  - Forward returns / IC / factor summary 等の探索ユーティリティ
- 特徴量エンジニアリングとシグナル生成
  - Z スコア正規化、ユニバースフィルタ、スコア合成、Bear レジーム抑制
  - signals テーブルへの冪等書き込み
- バックテストフレームワーク
  - 日次ループでの売買シミュレーション（スリッページ・手数料モデル）
  - ポジション書き戻し、シミュレータ、評価指標（CAGR, Sharpe, MaxDD, WinRate, Payoff）
  - CLI から実行可能（python -m kabusys.backtest.run）

セットアップ手順
----------------
前提
- Python 3.10 以上（PEP 604 の型表記を使用）
- DuckDB、defusedxml などの依存パッケージ

1. リポジトリをクローン（またはソースを取得）
   - 例: git clone ...（プロジェクトルートに pyproject.toml / .git があることを想定）

2. 仮想環境を作成して有効化
   - python -m venv .venv
   - Windows: .venv\Scripts\activate
   - macOS/Linux: source .venv/bin/activate

3. 必要パッケージをインストール
   - 必須パッケージ（例）:
     - duckdb
     - defusedxml
   - 具体的な requirements はプロジェクト側で管理してください。最低限:
     - pip install duckdb defusedxml

4. パッケージを開発モードでインストール（任意）
   - pip install -e .

5. 環境変数設定
   - プロジェクトルートに .env または .env.local を置くと自動で読み込まれます（自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - 任意（デフォルトあり）:
     - KABUSYS_ENV (development|paper_trading|live) デフォルト: development
     - LOG_LEVEL (DEBUG|INFO|...)
     - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH（監視用 DB パス、デフォルト data/monitoring.db）

   - .env の例:
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     KABU_API_PASSWORD=your_kabu_api_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     DUCKDB_PATH=data/kabusys.duckdb
     ```

使い方（主要な API と CLI）
-------------------------

1. DuckDB スキーマの初期化
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")  # ファイルを作成してスキーマを初期化
   # or
   mem_conn = init_schema(":memory:")
   ```

2. J-Quants からデータ取得と保存
   ```python
   from kabusys.data import jquants_client as jq
   from kabusys.data.schema import init_schema

   conn = init_schema("data/kabusys.duckdb")
   records = jq.fetch_daily_quotes(date_from=..., date_to=...)
   saved = jq.save_daily_quotes(conn, records)
   ```

3. ETL（差分取得）の実行（プログラム的に）
   - data.pipeline には差分算出や backfill を備えた ETL 関数があります。例:
   ```python
   from kabusys.data.pipeline import run_prices_etl, ETLResult
   from kabusys.data.schema import init_schema
   from datetime import date

   conn = init_schema("data/kabusys.duckdb")
   fetched, saved = run_prices_etl(conn, target_date=date.today())
   ```

4. 特徴量作成とシグナル生成
   ```python
   from kabusys.strategy import build_features, generate_signals
   from kabusys.data.schema import init_schema
   from datetime import date

   conn = init_schema("data/kabusys.duckdb")
   # 特徴量作成
   count = build_features(conn, target_date=date(2024, 1, 31))
   # シグナル生成
   signals_written = generate_signals(conn, target_date=date(2024, 1, 31))
   ```

5. バックテスト（プログラム実行）
   ```python
   from kabusys.backtest.engine import run_backtest
   from kabusys.data.schema import init_schema
   from datetime import date

   conn = init_schema("data/kabusys.duckdb")
   result = run_backtest(conn, start_date=date(2023,1,1), end_date=date(2023,12,31))
   print(result.metrics)
   ```

6. バックテスト CLI
   - コマンド例:
     ```
     python -m kabusys.backtest.run \
       --start 2023-01-01 --end 2023-12-31 \
       --cash 10000000 --db data/kabusys.duckdb
     ```
   - 事前条件: 指定 DB に prices_daily, features, ai_scores, market_regime, market_calendar が必要。

7. ニュース収集の実行
   ```python
   from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
   from kabusys.data.schema import init_schema

   conn = init_schema("data/kabusys.duckdb")
   known_codes = {"7203", "6758", ...}  # 有効銘柄コードセット
   results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
   ```

設定・デバッグのヒント
--------------------
- 環境変数は .env/.env.local から自動読み込みされます。テスト時などで自動読み込みを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- ログレベルは LOG_LEVEL 環境変数で制御できます（デフォルト INFO）。
- DuckDB のファイルはデフォルトで data/kabusys.duckdb に作成されます（DUCKDB_PATH で変更可）。
- news_collector や jquants_client は外部ネットワークにアクセスするため、テスト時には該当関数をモックしてください（コード内にもモック用フックがコメントとして示されています）。

ディレクトリ構成
----------------
（主要なファイルのみを抜粋）

- src/kabusys/
  - __init__.py
  - config.py                       — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py              — J-Quants API クライアント（取得 + 保存）
    - news_collector.py              — RSS ニュース収集・保存
    - schema.py                      — DuckDB スキーマ定義と init_schema()
    - stats.py                       — Z スコア正規化など統計ユーティリティ
    - pipeline.py                    — ETL 差分更新 / ラッパー処理
  - research/
    - __init__.py
    - factor_research.py             — Momentum / Volatility / Value 計算
    - feature_exploration.py         — forward returns / IC / summary
  - strategy/
    - __init__.py
    - feature_engineering.py         — features テーブル作成（正規化・ユニバースフィルタ）
    - signal_generator.py            — final_score 計算と signals 書き込み
  - backtest/
    - __init__.py
    - engine.py                      — run_backtest の実装（全体ループ）
    - metrics.py                     — バックテスト指標計算
    - simulator.py                   — PortfolioSimulator（約定・評価）
    - run.py                         — CLI 用エントリポイント
    - clock.py                       — 将来拡張用の模擬時計
  - execution/                        — 発注 / 実行レイヤ（現在はモジュール空の初期化）
  - monitoring/                       — 監視関連（監視DB等の実装場所）

貢献・開発
----------
- コードスタイル・型付けを維持してください（PEP8, typing）。
- 外部 API を叩く箇所は可能な限りインターフェースを分離し、モックしやすくしてください（既存コードにもその配慮があります）。
- テストはネットワーク依存を避け、HTTP クライアントや時間依存処理はモックで分離してください。

ライセンス
---------
リポジトリに含まれるライセンスファイルを参照してください（本 README にはライセンス記載がありません）。

補足
----
- 本ドキュメントはリポジトリ内のソースコード（docstrings / コメント）を基に要点をまとめたものです。より詳細な仕様（StrategyModel.md、DataPlatform.md、BacktestFramework.md 等）はプロジェクト内ドキュメントをご参照ください。