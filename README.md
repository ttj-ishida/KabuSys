# KabuSys

バージョン: 0.1.0

日本株向け自動売買システムのモジュール群（発注エンジン、監視、ポートフォリオ構築、ファクター研究、AI ツール等）を含むコードベースの README です。

## プロジェクト概要
KabuSys は日本株の自動売買を支援するライブラリ／実行環境です。  
主な目的は次のとおりです：

- 発注・注文管理・リコンシリエーションを行う Execution Engine
- システム稼働性・注文異常・リスク（ドローダウン・ポジション上限）を監視する Monitoring
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算）
- ファクター計算・特徴量探索（DuckDB に保存された価格・財務データを用いる）
- ニュースの NLP（OpenAI を用いた銘柄センチメント）や市場レジーム判定
- 開発／検証用ツール（Paper Trading 検証レポート、Streamlit ダッシュボード等）

本 README ではセットアップ手順、実行方法、主要コンポーネントの挙動とディレクトリ構成を説明します。

---

## 主な機能一覧
- Execution
  - 発注フロー（OrderManager、OrderRepository、BrokerClientFactory）
  - 再起動時のリコンシリエーション（Reconciler）
  - Paper Trading モード（本番 DB と分離された data/paper_trading.db を使用、MockBrokerClient）
- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク、プロセス生存、データ鮮度の監視
  - TradeMonitor: 注文滞留、約定異常価格検出
  - RiskMonitor: ドローダウン監視、ポジション上限監視
  - KillSwitch: 監視から停止指示（data/kill.flag）を発行
  - AlertManager: LINE Messaging API による通知（クールダウン管理あり）
  - Streamlit ダッシュボード（監視結果の可視化）
- Portfolio
  - 候補選定（スコア順ソート）
  - 重み計算（等金額・スコア加重）
  - セクター分散制約、レジーム乗数適用
  - ポジションサイズ計算（単元株、リスクベース、cash上限スケール）
- Research
  - Momentum/Volatility/Value ファクター計算（DuckDB）
  - 将来リターン、IC（情報係数）、統計サマリ
- AI 関連
  - ニュースのセンチメントスコアリング（OpenAI を利用）
  - 市場レジーム判定（MA + マクロセンチメントの合成）
- 開発ツール
  - Paper Trading 検証レポート出力（kabusys.tools.paper_verification_report）
  - DB スキーマ自動初期化（monitoringDB の init）

---

## 動作要件（主要パッケージ）
最低限必要なパッケージ（推奨は仮想環境を利用）:

- Python 3.10+
- duckdb
- psutil
- requests
- openai
- streamlit (ダッシュボード利用時)

例（pip）:
pip install duckdb psutil requests openai streamlit

※ 実環境では必要に応じてバージョン固定や追加パッケージがある場合があります。

---

## セットアップ手順（ローカル開発向け）
1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo-root>

2. Python 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb psutil requests openai streamlit

4. 環境変数の設定
   - プロジェクトルートに `.env` または `.env.local` を置いて設定できます。
   - 自動ロードはデフォルトで有効（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 代表的な環境変数（.env.example を参照してください）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - OPENAI_API_KEY
     - LINE_CHANNEL_ACCESS_TOKEN
     - LINE_USER_ID
     - KABUSYS_ENV (development | paper_trading | live)
     - LOG_LEVEL (DEBUG | INFO | ...)
     - DUCKDB_PATH (デフォルト data/kabusys.duckdb)
     - SQLITE_PATH (監視 DB デフォルト data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB デフォルト data/paper_trading.db)
     - PAPER_FILL_MODE (instant | partial | never | reject)
     - PID_FILE_PATH, KILL_FLAG_PATH 等（必要に応じて）

5. ディレクトリの準備
   - data ディレクトリを作成（DB 保管やフラグファイル用）
   - mkdir -p data

---

## 実行方法（代表例）
実行はモジュールとして Python -m で行うことを想定しています。

1. Execution Engine を起動
   - 本番／開発:
     - KABUSYS_ENV によって動作モードが変わります（development, paper_trading, live）。
     - Paper Trading の場合は MockBrokerClient が使用され、DB は PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）に分離されます。
   - 実行例:
     - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
     - python -m kabusys.run_execution

   注意:
   - 実行時に data/stop_requested.flag が存在すると起動を中止します。
   - 実行中は data/execution.pid に PID を書きます（Process 管理用）。

2. Monitoring を起動
   - ポーリングループ: MONITOR_POLL_INTERVAL 環境変数で秒数を上書き可能（デフォルト 60 秒）。
   - 実行例:
     - python -m kabusys.run_monitoring
     - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

   備考:
   - 監視は Settings.sqlite_path（monitoring DB）を使用します（KABUSYS_ENV に関係なく本番 sqlite_path）。
   - 停止は data/stop_requested.flag を置くことで行えます（監視ループが検知して終了）。

3. Streamlit ダッシュボード（監視画面）
   - 起動例:
     - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - 読み取り専用で SQLite を開き、Positions / Orders / System / Overview を表示します。

4. Paper Trading 検証レポート生成
   - usage:
     - python -m kabusys.tools.paper_verification_report
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
     - オプション --db で PAPER_TRADING_SQLITE_PATH を上書き可能
   - 出力: 稼働率、注文成功率、送信率、レイテンシ（P95）などの集計と PASS/FAIL 判定

5. AI 関連（ニューススコア／レジーム判定）
   - OpenAI API キー (OPENAI_API_KEY) が必須です。
   - ニューススコア:
     - from kabusys.ai.news_nlp import score_news
     - score_news(conn, target_date, api_key=...)
   - レジーム判定:
     - from kabusys.ai.regime_detector import score_regime
     - score_regime(conn, target_date, api_key=...)

---

## 重要な挙動・注意点
- Settings（kabusys.config）
  - プロジェクトルートを .git / pyproject.toml で自動検出し、.env / .env.local をロードします。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できます（テスト等で便利）。

- Paper Trading
  - KABUSYS_ENV=paper_trading の場合、broker は MockBrokerClient を使用し、paper 用 SQLite（PAPER_TRADING_SQLITE_PATH）に完全分離して記録します。

- 監視と停止
  - KillSwitch は監視が検出した致命的な事象（ドローダウン超過等）で data/kill.flag を書き込み、ExecutionEngine 側で読んで停止する仕組みです。
  - run_execution/run_monitoring は data/stop_requested.flag を監視して自発停止できます（外部から停止要求を出す用途）。

- プロセス優先度
  - 実行開始時に set_process_priority("high") が呼ばれます。psutil を使って OS に応じた優先度と CPU affinity を設定します。権限の問題で失敗することがありますが、失敗時は警告ログを出して続行します。

- DB スキーマ
  - monitoring DB 用のテーブルとインデックスは init_monitoring_db() で冪等に作成されます。既存 DB に対するマイグレーション（カラム追加など）も組み込まれています。

- ロギング
  - 標準的に logging.basicConfig(level=logging.INFO) が使われます。LOG_LEVEL 環境変数で変更可能。

- OpenAI 呼び出し
  - リトライ（指数バックオフ）やレスポンスのバリデーションが組み込まれています。API キー未設定時は ValueError を送出します。

---

## 簡易コマンド例
- 開発用（paper trading）:
  - KABUSYS_ENV=paper_trading OPENAI_API_KEY=xxx python -m kabusys.run_execution
- 監視起動（60 秒間隔）:
  - python -m kabusys.run_monitoring
- 監視ダッシュボード:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

## ディレクトリ構成（主要ファイル）
（ src/kabusys 以下を抜粋）

- src/kabusys/
  - __init__.py
  - config.py
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリング起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py — Paper Trading 検証レポート
  - execution/
    - order_manager.py
    - reconciler.py
    - order_repository.py (実装ファイルはコードベースに応じて存在)
    - execution_engine.py
    - broker_factory.py
    - broker_api.py
    - order_record.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
    - streamlit_dashboard.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - utils/
    - process_priority.py
  - data/ (実行時に使用する DB / フラグファイル等を配置)
    - monitoring.db (デフォルト)
    - paper_trading.db (paper_trading として使用)
    - kabusys.duckdb (DuckDB ファイル)
    - execution.pid
    - stop_requested.flag
    - kill.flag

---

## 開発者向けメモ
- テストや CI 環境では KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して .env 自動ロードを無効化すると再現性が高まります。
- DuckDB 接続は read / write の両方で使われます。AI モジュールやリサーチモジュールは主に DuckDB 内の prices_daily / raw_financials / raw_news 等を参照します。
- エラーハンドリング: 多くの外部呼び出し（OpenAI、Broker API、ファイル I/O）はフェイルセーフに設計されており、失敗時にスキップしてログ出力する実装が多く含まれています。

---

必要であれば、.env.example のテンプレートやサンプル docker-compose / systemd サービス定義、requirements.txt の生成を含めた追加ドキュメントを作成します。どの形式が良いか教えてください。