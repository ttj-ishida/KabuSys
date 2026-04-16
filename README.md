# KabuSys

日本株向け自動売買システムのコアライブラリ群（リサーチ、ポートフォリオ構築、実行・発注、監視、AI 補助処理など）。

この README はコードベース（src/kabusys 以下）に基づいた概要・セットアップ・使い方・ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は以下の主要機能を持つモジュール群から構成されます。

- リサーチ（ファクター計算・特徴量解析）
- ポートフォリオ構築（候補選定・重み計算・ポジションサイズ算出）
- 実行エンジン（ブローカーへの発注や注文状態管理、再同期／リコンシリエーション）
- 監視（システム状態、注文滞留、リスク監視、Kill Switch）
- AI 補助（ニュースの NLP によるセンチメントスコア、レジーム判定）
- ツール（Paper Trading 検証レポート生成、Streamlit ベースの監視ダッシュボード）
- 各種ユーティリティ（プロセス優先度など）

設計上の方針として、リサーチ／ポートフォリオモジュールは副作用のない純粋関数群を目指しており、データアクセスは DuckDB / SQLite 経由で行います。Paper Trading (模擬発注) は本番 DB と分離されます。

---

## 機能一覧（主要コンポーネント）

- src/kabusys/research
  - calc_momentum / calc_volatility / calc_value：DuckDB の prices_daily/raw_financials を使ったファクター計算
  - calc_forward_returns / calc_ic / factor_summary：特徴量評価・IC 計算
- src/kabusys/portfolio
  - select_candidates / calc_equal_weights / calc_score_weights：銘柄選定・重み計算
  - calc_position_sizes：株数算出・リスク制約・単元丸め
  - apply_sector_cap / calc_regime_multiplier：セクター制約・レジーム乗数
- src/kabusys/execution
  - ExecutionEngine（起動スクリプトから起動）
  - OrderManager / OrderRepository / Reconciler：発注と起動時の再同期（リコン）
  - BrokerClientFactory（環境に応じたブローカークライアント生成）
- src/kabusys/monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor：各種チェック
  - MonitoringEngine：監視ループの統括
  - MonitoringDB：監視ログの永続化（SQLite）
  - KillSwitch：kill.flag によるエンジン強制停止
  - AlertManager：LINE push による通知
  - streamlit_dashboard：監視ダッシュボード（Streamlit）
- src/kabusys/ai
  - news_nlp.score_news：ニュース記事を OpenAI でスコアリングして ai_scores に保存
  - regime_detector.score_regime：MA と LLM を合成した市場レジーム判定
- src/kabusys/tools
  - paper_verification_report：Paper Trading DB から検証レポートを生成
- src/kabusys/utils
  - process_priority：プロセス優先度・CPU affinity 設定ユーティリティ

---

## 要件（主な依存パッケージ）

- Python 3.9+
- duckdb
- psutil
- requests
- openai
- streamlit（ダッシュボードを使う場合）
- その他（標準ライブラリ）

※ 実際のインストールはプロジェクト側の requirements.txt / pyproject.toml に従ってください（本コードサンプルには明示されていません）。

---

## セットアップ手順

1. リポジトリをクローンし、仮想環境を作成・有効化する
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストールする
   - pip install duckdb psutil requests openai streamlit

3. 環境変数設定
   - プロジェクトルートに `.env`（または `.env.local`）を置くと自動ロードされます（自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。
   - 必須環境変数（少なくとも本番で動かす場合）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - AI 機能を使う場合:
     - OPENAI_API_KEY
   - LINE 通知を使う場合:
     - LINE_CHANNEL_ACCESS_TOKEN（任意）
     - LINE_USER_ID（任意）
   - 主要な設定は `src/kabusys/config.py` の Settings クラスで解説（デフォルト値あり）。主なデフォルト:
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
     - PID_FILE_PATH: data/execution.pid
     - KILL_FLAG_PATH: data/kill.flag
     - CPU/MEM/DISK 閾値や KABUSYS_ENV（development/paper_trading/live）など

4. データディレクトリの作成
   - mkdir -p data

5. 初期 DB 作成
   - 実行スクリプト（run_monitoring / run_execution）が起動時に monitoring DB の初期化（テーブル作成）を行います。手動で行う必要はありません。

---

## 使い方

以下は代表的な起動・利用方法です。実行はプロジェクトルートから行ってください。

- 監視ループを起動（Monitoring）
  - デフォルトのポーリング間隔は 60 秒です。環境変数 MONITOR_POLL_INTERVAL で上書き可能（秒）。
    - 例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視は Settings.env に関係なく本番の sqlite_path を使用します（run_monitoring の仕様）。
  - 停止方法: data/stop_requested.flag にファイルが存在するとループが終了します（または Ctrl+C）。

- 実行エンジンを起動（Execution）
  - Paper Trading（模擬）で起動する場合:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - paper_trading 環境では MockBrokerClient が使用され、DB は data/paper_trading.db に記録されます（本番 DB と完全分離）。
  - 本番（ライブ）: KABUSYS_ENV=live python -m kabusys.run_execution
  - 起動時、プロセス優先度を high に設定し、PID ファイル (data/execution.pid など) を利用します。
  - 停止方法:
    - data/stop_requested.flag を作成すると起動中ループが停止します。
    - KillSwitch（監視側）の判定により data/kill.flag が書き込まれると ExecutionEngine は停止シグナルを受けます。
    - 明示的に .kill ファイルを消す/クリアするユーティリティも実装されています（KillSwitch.clear）。

- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 監視 DB を read-only モードで開いてダッシュボードを表示します。MonitoringEngine が先に起動していることが前提です。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH  (PAPER_TRADING_SQLITE_PATH 環境変数で代替可能)

- AI 機能
  - kabusys.ai.score_news(conn, target_date, api_key=None)：raw_news から銘柄別センチメントを計算して ai_scores テーブルに書き込む
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)：市場レジーム判定を market_regime テーブルへ書き込む
  - どちらも OPENAI_API_KEY を環境変数または引数で設定する必要があります。

- 監視（MonitoringEngine）について（テスト用）
  - MonitoringEngine.run_once() を呼ぶと 1 サイクルだけ各モニタを実行します（ユニットテストで利用可能）。

---

## 設定（主な環境変数）

- KABUSYS_ENV: 起動環境（development | paper_trading | live）。デフォルト: development
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring 用）。デフォルト: 60
- SQLITE_PATH: 監視 DB パス。デフォルト: data/monitoring.db
- DUCKDB_PATH: DuckDB パス。デフォルト: data/kabusys.duckdb
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（paper_trading 環境で使用）。デフォルト: data/paper_trading.db
- PAPER_FILL_MODE: Paper Trading のマッチング動作（instant|partial|never|reject）。デフォルト: instant
- OPENAI_API_KEY: OpenAI API キー（AI 機能に必要）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須設定）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須設定）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用（任意）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env の自動読み込みを無効にできます。

設定の詳細は src/kabusys/config.py の Settings クラスの docstring／プロパティを参照してください。

---

## 停止・フラグ機構

- data/stop_requested.flag
  - run_monitoring / run_execution のループを優雅に終了させるためのファイル。存在を確認してループを抜けます。

- data/kill.flag
  - KillSwitch が判定した際に書き込まれるファイル。ExecutionEngine に対する強制停止トリガーとして利用されます。path は Settings.kill_flag_path で指定可能。

- PID ファイル
  - data/execution.pid（デフォルト）は ExecutionEngine 実行中の PID を記載するために使用され、SystemMonitor はこれを参照してプロセス生存チェックを行います。

---

## 開発・テスト上の注意

- 多くの関数は純粋関数（副作用なし）や、明確に DB 接続/duckdb 接続を受け取る設計になっています。ユニットテストはモック接続や一時 DB を使って容易に行えます。
- 外部 API 呼び出し（OpenAI / ブローカー / LINE）はフェイルセーフが実装され、失敗時にシステム全体が停止しないよう配慮されています（バックオフ・フォールバック値等）。
- 自動で .env を読み込む機能があり、プロジェクトルートは .git または pyproject.toml を基準に探索します。

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 以下の主要なファイルをツリー風に抜粋）

- src/kabusys/
  - __init__.py
  - config.py
  - run_execution.py            — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — SystemMonitor ポーリング起動スクリプト
  - utils/
    - __init__.py
    - process_priority.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - execution/
    - order_manager.py
    - order_repository.py       (参照あり)
    - reconciler.py
    - execution_engine.py      (参照あり)
    - broker_factory.py        (参照あり)
    - broker_api.py            (参照あり)
    - order_record.py          (参照あり)
  - monitoring/
    - __init__.py
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
    - streamlit_dashboard.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - tools/
    - __init__.py
    - paper_verification_report.py

※ リポジトリ全体の完全なファイル一覧はプロジェクトルートを参照してください。上は主要なモジュールのみ抜粋。

---

## よく使うコマンド例

- 監視開始（ポーリング 60 秒）
  - python -m kabusys.run_monitoring

- 監視開始（ポーリング 30 秒）
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- 実行エンジン（Paper Trading）起動
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading レポート（過去期間指定）
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

## 補足

- セキュリティ: 環境変数やシークレット（APIキー等）は .env に平文で置かない運用、あるいは運用環境のシークレット管理を推奨します。
- 本リポジトリに含まれるドキュメント（PortfolioConstruction.md, StrategyModel.md 等）やコード内 docstring を合わせて参照すると設計意図が理解しやすくなります。

---

ご希望があれば、README に
- インストール用 requirements.txt の例
- より詳細な環境変数一覧表（キー / 必須/デフォルト / 説明）
- 起動フローチャート（図的説明）
を追記します。どれを優先して追加しますか？