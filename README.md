# KabuSys

日本株自動売買システムのライブラリ・起動スクリプト群。取引エンジン（ExecutionEngine）、監視（Monitoring）、研究用ファクター計算、ポートフォリオ構築、AI（ニュースセンチメント・レジーム判定）などを含むモジュール群を提供します。

---

## 概要

KabuSys は以下の主要な責務を持つモジュールで構成されています。

- Execution: 発注エンジン、オーダー管理、リスク管理（本番 / ペーパートレード切替対応）
- Monitoring: システム稼働監視、トレード監視、リスク監視、Kill Switch（停止フラグ）
- Research: DuckDB 上でのファクター計算・特徴量解析
- Portfolio: 候補選定、重み計算、ポジションサイズ算出、セクター制限・レジーム調整
- AI: ニュース NLP による銘柄センチメント算出、マクロセンチメントによるレジーム判定
- Utils: ロギング設定、プロセス優先度設定、設定管理（.env 読み込み等）
- Tools: Paper Trading の検証レポート生成などのユーティリティスクリプト

各起動スクリプトはパッケージとして直接実行可能です（例: python -m kabusys.run_execution）。

---

## 機能一覧

主な機能を抜粋します。

- Execution
  - 本番（live）とペーパートレード（paper_trading）切替
  - BrokerClientFactory によるブローカークライアント生成
  - OrderManager / RiskManager / Reconciler による発注制御
  - ExecutionEngine によるセッション実行と PID 管理

- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク、データ鮮度、Execution プロセス存在監視
  - TradeMonitor: 注文滞留・約定異常などの検出（trade_logs 参照）
  - RiskMonitor: ドローダウンや保有銘柄数上限の監視、ダッシュボード更新
  - KillSwitch: kill.flag による ExecutionEngine 強制停止
  - MonitoringEngine: 定期ポーリング・アラート送出

- Research / Portfolio
  - ファクター計算（モメンタム、ボラティリティ、バリュー）
  - 将来リターン計算、IC（Information Coefficient）算出
  - 候補選定 / 等金額・スコア重み / リスクベース資金配分
  - セクター集中制限、レジームに応じた乗数

- AI
  - ニュース記事を集約して OpenAI に送信し、銘柄ごとのセンチメント（ai_scores テーブルへ）を生成
  - マクロニュース + ETF MA200 乖離に基づく市場レジーム判定（market_regime テーブルへ）

- ツール
  - .env 対話生成ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading の検証レポート生成（tools.paper_verification_report）

---

## セットアップ手順

前提: Python 3.9+（DuckDB / psutil / OpenAI SDK 等の互換性を満たすバージョンを使用してください）

1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo-root>

2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Linux/macOS)
   - .venv\Scripts\activate     (Windows)

3. 必須依存パッケージをインストール
   - pip install duckdb psutil openai
   - 推奨: PyYAML（config YAML 検証用）: pip install pyyaml

   （プロジェクトに requirements.txt がない場合は上記を目安にインストールしてください）

4. 設定ファイル（.env）の作成
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - 生成後、次のコマンドで検証:
     - python -m kabusys.validate_config
     - 問題がある場合は表示されるメッセージに従って修正してください

5. データディレクトリの準備
   - デフォルトでは data/ 下に各種 DB やフラグファイルを配置します（例: data/monitoring.db, data/kabusys.duckdb, data/paper_trading.db）
   - 必要に応じて .env の DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH を設定してください

---

## 必須・主要環境変数（抜粋）

以下は Settings クラス（kabusys/config.py）で参照される主な環境変数とデフォルト値です。

必須:
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)

任意・デフォルト:
- KABUSYS_ENV: 実行環境（development / paper_trading / live） — デフォルト: development
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- LOG_LEVEL: INFO
- LOG_DIR: logs/ （logging_setup が参照）
- PID_FILE_PATH: data/execution.pid
- KILL_FLAG_PATH: data/kill.flag
- KILL_FLAG_CLEAR_ON_START: 0（1 にすると起動時に kill.flag を自動クリア）
- PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）

注意:
- OPENAI_API_KEY は AI モジュール（news_nlp / regime_detector）で必要です（関数呼び出し時に引数でも指定可）。
- MONITOR_POLL_INTERVAL (秒): run_monitoring のポーリング間隔上書き（デフォルト 60 秒）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動で .env を読み込む挙動を無効化できます。

---

## 起動・使い方

主要な起動スクリプトはパッケージモジュールとして実行します。

- ExecutionEngine（取引エンジン）起動
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して data/paper_trading.db に記録（本番 DB と分離）
    - 起動前に data/stop_requested.flag が存在すると起動せず終了
    - 停止は data/stop_requested.flag を作成することで実行可能（監視プロセスや手動で作成）

- Monitoring（監視ループ）起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を変更可能（例: MONITOR_POLL_INTERVAL=30）
  - 監視は本番 sqlite_path（Settings.sqlite_path）を使用（env に依存せず）

- 設定ウィザード
  - python -m kabusys.config_setup  （.env を対話式に作成）

- 設定検証
  - python -m kabusys.validate_config [--strict]

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - 環境変数 PAPER_TRADING_SQLITE_PATH で DB パスを指定可能

- AI モジュール（関数呼び出し）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは DuckDB 接続（duckdb.connect(...).cursor()）を受け取るためスクリプト内で呼び出して利用します。OpenAI API キーは引数で渡すか OPENAI_API_KEY 環境変数を設定してください。

停止・制御関連:
- data/stop_requested.flag: run_execution / run_monitoring の起動ループを停止させるために利用（存在を検知するとループ終了）
- data/kill.flag: KillSwitch により ExecutionEngine の強制停止を伝えるために書き込まれる（ExecutionEngine 起動時に KILL_FLAG_CLEAR_ON_START=1 の場合は自動クリアされる設定を注意）

ログ:
- ログは logging_setup によって stdout と logs/<app_name>.log（日次ローテーション、30日保持）に出力されます。
- 環境変数 LOG_DIR や LOG_LEVEL を変更して挙動を調整可能です。

---

## よく使う開発コマンド例

- .env を生成:
  - python -m kabusys.config_setup

- 設定を検証:
  - python -m kabusys.validate_config
  - 厳密モード（警告があれば失敗）:
    - python -m kabusys.validate_config --strict

- ペーパートレードの検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

- DuckDB コンソールを使って研究用クエリ実行（例）:
  - python -c "import duckdb; conn=duckdb.connect('data/kabusys.duckdb'); print(conn.execute('SELECT COUNT(*) FROM prices_daily').fetchall())"

---

## ディレクトリ構成

主要ファイル・ディレクトリ（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 監視ループ起動スクリプト
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ
  - execution/
    - broker_factory.py
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - data/                    — 実行時に使用する SQLite / DuckDB / フラグファイル等（デフォルト）
  - logs/                    — ログ出力先（デフォルト）

注: 上記はリポジトリ内の主要モジュールを抜粋した構成です。実際のファイル一覧はリポジトリを参照してください。

---

## 運用上の注意

- 本番（KABUSYS_ENV=live）で運用する前に validate_config で設定を十分確認してください（LINE 通知設定や Kill Flag の自動クリア設定など）。
- OpenAI API を使う機能は API 利用料が発生します。API キーの管理と利用コストにご注意ください。
- ペーパートレード用 DB は paper_trading 環境で本番 DB とは分離されています（PAPER_TRADING_SQLITE_PATH）。
- ローカルで cron / systemd 等を使って常駐実行する場合、logs/ や data/ のパーミッション、ディスク容量に注意してください。
- プロセス優先度・CPU affinity の設定はプラットフォーム差分を吸収しますが、権限不足で設定できない場合は警告が出ます（処理は継続します）。

---

必要であれば、README の英語版、詳細なデプロイ手順（systemd ユニットファイル例・Dockerfile 例）、テスト手順や CI 設定のテンプレートも作成できます。どれを優先しますか？