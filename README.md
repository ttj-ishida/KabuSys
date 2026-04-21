README
======

概要
----
KabuSys は日本株自動売買システムのコアライブラリ群です。本リポジトリは以下の主要機能を提供します。

- 実売買向け ExecutionEngine（本番 / ペーパートレード切替）
- 監視（Monitoring）コンポーネント（システム状態、発注ログ、リスク監視、Kill Switch）
- ポートフォリオ構築・銘柄選定・株数計算（純粋関数群）
- 研究用ユーティリティ（ファクター計算、特徴量探索）
- AI ベースのニュース NLP（OpenAI を用いた銘柄別センチメント）と市場レジーム判定
- 運用支援ツール（.env ウィザード、設定検証、Paper Trading 検証レポート）
- ロギング・プロセス優先度設定などのユーティリティ

主要機能
--------
- ExecutionEngine
  - KABUSYS_ENV により paper_trading / live / development を切替可能
  - paper_trading の場合は MockBrokerClient を使い data/paper_trading.db に記録（本番 DB と分離）
  - リスク管理・オーダーマネージャ・リコンサイラを組み合わせた発注実行ループ

- Monitoring
  - SystemMonitor: CPU/Mem/Disk、Execution プロセス生存確認、データ鮮度チェック
  - TradeMonitor: 発注ログの監視（滞留注文や異常約定の検出）
  - RiskMonitor: ドローダウン・ポジション上限監視と alert / kill switch の発動
  - MonitoringEngine: 各 Monitor を束ねて定期ポーリングしアラートを通知

- Portfolio（純粋関数）
  - 候補選定、等配分/スコア配分、ポジションサイズ計算、セクター上限・レジーム乗数

- Research
  - ファクター計算（Momentum, Volatility, Value 等）、将来リターン、IC 計算、統計サマリー

- AI モジュール
  - news_nlp: raw_news を集約して OpenAI に投げ、銘柄ごとに -1.0〜1.0 のスコアを生成
  - regime_detector: ETF（1321）MA200 とマクロニュースの LLM センチメントを合成して market_regime を判定

- 運用ツール
  - config_setup: 対話式に .env を作成 / 更新するウィザード
  - validate_config: .env と config/*.yaml の事前検証 CLI
  - paper_verification_report: ペーパートレード結果から検証レポートを生成

セットアップ手順
----------------

1. Python 環境準備
   - Python 3.9+ を推奨（プロジェクトでの厳密なバージョン要件は別途 requirements.txt を参照してください）

2. 依存パッケージをインストール
   - 代表的な依存パッケージ:
     - duckdb, psutil, openai, PyYAML（YAML 検証用、任意）
   - 例:
     - pip install -r requirements.txt
     - または最低限: pip install duckdb psutil openai

3. プロジェクトルートの環境変数設定
   - .env を作成する方法（対話式ウィザード推奨）:
     - python -m kabusys.config_setup
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - AI 機能を使う場合:
     - OPENAI_API_KEY を設定

4. 設定の事前検証（必須ではないが推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱い（exit 1）

5. ディレクトリ作成（logs / data 等）
   - 通常は起動スクリプトで自動作成されますが、手動で準備してもよい:
     - mkdir -p data logs

使い方
------

- ExecutionEngine を起動（本番 / ペーパートレードを KABUSYS_ENV で切替）
  - デフォルト（開発）:
    - python -m kabusys.run_execution
  - ペーパートレード:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - この場合は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を使用し、本番 DB と分離されます。

  動作の概略:
  - 起動時にプロセス優先度を "high" に設定
  - BrokerClientFactory により適切なブローカークライアントを生成
  - OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を開始
  - 停止制御は data/stop_requested.flag と data/kill.flag（KillSwitch）で行います

- Monitoring を起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒、デフォルト 60）を上書き可能
  - 監視は Settings の sqlite_path（監視 DB）を使用。Monitoring は KABUSYS_ENV に関係なく本番 sqlite_path を参照します

- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート出力
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB パスは PAPER_TRADING_SQLITE_PATH 環境変数または data/paper_trading.db

- AI 機能（プログラム的に呼び出す）
  - OpenAI キーを渡して実行:
    - from kabusys.ai.news_nlp import score_news
    - from kabusys.ai.regime_detector import score_regime
  - どちらも api_key 引数または環境変数 OPENAI_API_KEY を利用

- テスト用ユーティリティ
  - MonitoringEngine.run_once() を使って単発実行（ユニットテスト用）

環境変数（代表例・デフォルト）
--------------------------------
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: （必須）
- KABU_API_PASSWORD: （必須）
- OPENAI_API_KEY: AI 機能で必要
- DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
- SQLITE_PATH: data/monitoring.db（監視 DB、デフォルト）
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（ペーパートレード DB）
- LOG_LEVEL: INFO（デフォルト）
- LOG_DIR: logs/
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START 等（詳細は Settings クラス参照）
- PAPER_FILL_MODE: ペーパートレードでの Fill 動作（instant|partial|never|reject、デフォルト instant）

停止・Kill Switch
-----------------
- モジュールはファイルフラグで外部から停止を受け取ります:
  - data/stop_requested.flag: run_execution/run_monitoring が検出して丁寧に終了
  - data/kill.flag: KillSwitch が書き込むことで ExecutionEngine に即時停止シグナルを送る運用パターン
- Settings.kill_flag_clear_on_start が 1 の場合、起動時に自動で kill.flag をクリアする（本番では推奨しない）

監視 DB スキーマ
----------------
- monitoring_db.init_monitoring_db() により以下テーブルを作成します（冪等）:
  - system_status (CPU/MEM/DISK/プロセス正常フラグ)
  - trade_logs (発注イベントログ、latency_ms カラムあり)
  - positions
  - risk_logs
  - dashboard (1行のみの集計)

ディレクトリ構成（主なファイル）
------------------------------
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理（.env 自動読み込み含む）
  - config_setup.py          — .env 対話型ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - utils/
    - logging_setup.py       — 共通ロギング設定
    - process_priority.py    — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層（テーブル作成・CRUD）
    - monitoring_engine.py   — 各 Monitor を束ねるループ
    - system_monitor.py      — システム状態・データ鮮度監視
    - trade_monitor.py       — （発注監視、コード内に参照あり）
    - risk_monitor.py        — ドローダウン / ポジション上限監視
    - kill_switch.py         — Kill Switch 実装（flag ファイル書き込み）
    - alert_manager.py       — （通知管理、コード内に参照あり）
  - execution/
    - execution_engine.py    — ExecutionEngine 本体（起動・セッション管理）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py            — ニュースのセンチメント scoring（OpenAI）
    - regime_detector.py     — 市場レジーム判定（MA200 + マクロセンチメント）
  - data/                    — 実行時に生成されるデータファイル（data/kabusys.duckdb, data/monitoring.db, ...）
  - logs/                    — ログ出力先（デフォルト）

設計上の注意点・運用メモ
-----------------------
- 自動 .env 読み込み
  - プロジェクトルート（.git または pyproject.toml を基準）にある .env/.env.local をプロセス起動時に自動ロードします。
  - テストなどで自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- Monitoring の DB
  - Monitoring（run_monitoring）は KABUSYS_ENV にかかわらず Settings.sqlite_path（本番監視 DB）を使用します。開発時は別 DB を指定するなど注意してください。

- ペーパートレード分離
  - paper_trading モードでは発注関連データは PAPER_TRADING_SQLITE_PATH（data/paper_trading.db がデフォルト）に記録され、本番 DB と完全分離されます。

- OpenAI API 呼び出し
  - news_nlp / regime_detector は OPENAI_API_KEY を必要とする。API のレートリミットやエラー時は再試行・フォールバックロジックが組み込まれていますが、キーの取り扱いやコストに注意してください。

- ロギング
  - 共通の logging_setup を使用して stdout 出力 + 日次ローテーションログ（logs/<app_name>.log）を設定。LOG_DIR 環境変数で変更可。ログディレクトリ作成に失敗した場合はコンソールのみの出力になります。

- 標準的な起動コマンド例
  - 実行:
    - KABUSYS_ENV=live python -m kabusys.run_execution
  - 監視:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - .env 作成:
    - python -m kabusys.config_setup
  - 設定検証:
    - python -m kabusys.validate_config --strict
  - Paper レポート:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

最後に
------
この README はコードベースに含まれるモジュールとエントリポイントを中心にまとめた概要です。より詳細な仕様や設計は各モジュールの docstring やソースコメントを参照してください。必要であれば、起動スクリプトの systemd / supervisor 用ユニット例や docker-compose 設定のテンプレートも作成できます。希望があれば教えてください。