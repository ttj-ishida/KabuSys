# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ（KabuSys）。  
データ取得・ETL、特徴量生成、シグナル生成、バックテスト、ニュース収集など、アルゴリズムトレーディングに必要な主要コンポーネントを含みます。

- パッケージ名: kabusys
- バージョン: 0.1.0（src/kabusys/__init__.py）


## プロジェクト概要

KabuSys は日本株アルゴリズム取引のための内部ライブラリ群です。主な目的は以下です。

- J-Quants API から市場データ・財務データ・カレンダーを取得して DuckDB に格納する（差分取得・冪等性を重視）
- 研究（research）で算出した生ファクターを加工して特徴量（features）を作成
- 特徴量と AI スコアを統合して売買シグナルを生成（BUY / SELL）
- シグナルを用いたメモリ内バックテスト（約定・スリッページ・手数料モデルを含む）
- RSS 取得によるニュース収集と銘柄抽出
- DuckDB スキーマ定義と各種ユーティリティ

設計上のポイント:
- ルックアヘッドバイアスを避ける（target_date 時点のデータのみ使用）
- 冪等操作（DB 保存は ON CONFLICT 等を使用）
- 外部依存を最小限にし、テスト容易性を考慮


## 主な機能一覧

- 環境変数／設定管理（kabusys.config）
  - .env/.env.local の自動読み込み（プロジェクトルート検出）
  - 必須環境変数の検査

- データ取得・ETL（kabusys.data）
  - J-Quants API クライアント（rate limit, retry, token refresh 対応）
  - raw_prices / raw_financials / market_calendar の保存関数
  - ETL パイプラインの一部（差分取得・品質チェック連携）

- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得、XML の堅牢パース（defusedxml）
  - 記事 ID 正規化、銘柄コード抽出、DB 保存

- ファクター計算・特徴量（kabusys.research, kabusys.strategy.feature_engineering）
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - Zスコア正規化・ユニバースフィルタ適用・features テーブルへの保存

- シグナル生成（kabusys.strategy.signal_generator）
  - 複数コンポーネントを重み付けして final_score を算出
  - Bear レジーム抑制、BUY/SELL の生成、signals テーブルへの書込

- バックテスト（kabusys.backtest）
  - run_backtest による日次ループシミュレーション
  - PortfolioSimulator（擬似約定、スリッページ・手数料モデル）
  - メトリクス計算（CAGR, Sharpe, Max Drawdown, Win rate 等）
  - CLI エントリーポイント（kabusys.backtest.run）


## 必要条件

- Python 3.10 以上（型ヒントに | 記法を使用）
- 主な依存ライブラリ（最低限）
  - duckdb
  - defusedxml
- その他、標準ライブラリ（urllib, logging, datetime 等）

開発用に追加パッケージが必要な場合はプロジェクト側で requirements.txt / pyproject の extras を参照してください（このリポジトリ断片には明示的な依存ファイルが含まれていません）。


## セットアップ手順

1. Python と pip の用意（3.10 以上）

2. 仮想環境の作成（推奨）
   - macOS / Linux:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (PowerShell):
     ```
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

3. 必要パッケージのインストール（例）
   ```
   pip install duckdb defusedxml
   ```
   （プロジェクト配布時に requirements.txt / pyproject がある場合はそちらを利用してください）
   
4. ソースコードをインストール（開発モード）
   ```
   pip install -e .
   ```
   （プロジェクトルートで行ってください。setup/pyproject が必要です）

5. DuckDB スキーマ初期化
   Python REPL またはスクリプトで:
   ```python
   from kabusys.data.schema import init_schema
   init_schema("data/kabusys.duckdb")   # ファイルパスを指定（:memory: でインメモリ）
   ```

6. 環境変数設定
   プロジェクトルートに .env を置くと自動読み込みされます（.git または pyproject.toml を基準に探索）。

   主要な環境変数（必須）
   - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
   - SLACK_BOT_TOKEN: Slack ボットのトークン（必須）
   - SLACK_CHANNEL_ID: Slack 送信先チャンネル ID（必須）

   任意／デフォルトあり
   - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
   - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
   - SQLITE_PATH (デフォルト: data/monitoring.db)
   - KABUSYS_ENV (development | paper_trading | live)（デフォルト: development）
   - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL)（デフォルト: INFO）

   .env の例:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   ```

   自動読み込みを無効にしたい場合:
   ```
   export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   ```


## 使い方

いくつかの代表的な操作を示します。

- DuckDB スキーマ作成（再掲）
  ```python
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")
  conn.close()
  ```

- J-Quants から株価を取得して保存（簡易例）
  ```python
  from kabusys.data import jquants_client as jq
  import duckdb

  conn = duckdb.connect("data/kabusys.duckdb")
  records = jq.fetch_daily_quotes(date_from=..., date_to=...)
  jq.save_daily_quotes(conn, records)
  conn.close()
  ```

- 特徴量の構築（build_features）
  ```python
  from kabusys.strategy import build_features
  from kabusys.data.schema import init_schema
  from datetime import date

  conn = init_schema("data/kabusys.duckdb")
  n = build_features(conn, target_date=date(2024, 1, 4))
  print(f"features upserted: {n}")
  conn.close()
  ```

- シグナル生成（generate_signals）
  ```python
  from kabusys.strategy import generate_signals
  from kabusys.data.schema import init_schema
  from datetime import date

  conn = init_schema("data/kabusys.duckdb")
  count = generate_signals(conn, target_date=date(2024, 1, 4))
  print(f"signals written: {count}")
  conn.close()
  ```

- バックテスト実行（CLI）
  DuckDB に事前に prices_daily, features, ai_scores, market_regime, market_calendar が揃っていることが前提です。

  コマンド例:
  ```
  python -m kabusys.backtest.run \
    --start 2023-01-01 --end 2023-12-31 \
    --cash 10000000 --db data/kabusys.duckdb
  ```

  実行後、CAGR / Sharpe / Max Drawdown 等の結果がコンソールに表示されます。

- ニュース収集の実行（API）
  ```python
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  results = run_news_collection(conn)  # デフォルト RSS ソースを使用
  print(results)
  conn.close()
  ```

- ETL パイプラインの一部（例: prices ETL）
  （run_prices_etl などが提供されています）
  ```python
  from kabusys.data.pipeline import run_prices_etl
  from kabusys.data.schema import init_schema
  from datetime import date

  conn = init_schema("data/kabusys.duckdb")
  fetched, saved = run_prices_etl(conn, target_date=date.today())
  print(f"fetched={fetched}, saved={saved}")
  conn.close()
  ```

注: 上記の呼び出しはそれぞれ事前に必要なテーブルやデータ（market_calendar など）が存在することや、環境変数（J-Quants トークン等）が適切に設定されていることが前提です。


## ディレクトリ構成（主要ファイル）

（src/kabusys 以下の主要モジュールを抜粋）

- kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py        # J-Quants API クライアント、保存関数
    - news_collector.py       # RSS 収集、記事保存、銘柄抽出
    - schema.py               # DuckDB スキーマ定義 & init_schema()
    - stats.py                # 統計ユーティリティ（zscore_normalize）
    - pipeline.py             # ETL パイプライン（差分取得・保存等）
  - research/
    - __init__.py
    - factor_research.py      # モメンタム / ボラ / バリュー計算
    - feature_exploration.py  # IC / forward returns / 統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py  # features 作成フロー
    - signal_generator.py     # final_score 計算・signals 生成
  - backtest/
    - __init__.py
    - engine.py               # run_backtest（全体ループ）
    - simulator.py            # PortfolioSimulator（約定・時価評価）
    - metrics.py              # バックテスト評価指標計算
    - run.py                  # CLI エントリポイント
    - clock.py                # SimulatedClock（将来拡張）
  - execution/                # 発注 / 実行関連（空の __init__ あり）
  - monitoring/               # 監視・アラート関連（今後の拡張想定）
  - backtest/                 # バックテスト関連（上記）
  - その他ユーティリティ群


## 開発・貢献

- コードはモジュール単位でユニットテストを追加すると良いです（特にデータ変換ロジック、ETL、シミュレータ）。
- 外部 API 呼び出し部分（jquants_client.fetch_* など）はモック化してテストすることを推奨します。
- SQL を扱うコードは DuckDB の in-memory 接続を使ったテストが容易です（init_schema(":memory:") を利用）。

バグ報告やプルリクエストは README のあるリポジトリに対して行ってください（この断片ではリポジトリ管理情報は含まれていません）。


## ライセンス

この README はコードベースの断片から生成した説明です。元のリポジトリのライセンス表記を参照してください。