KabuSys — 日本株自動売買システム
================================

このリポジトリは日本株向けの自動売買システムのコンポーネント群（実行エンジン、監視、ポートフォリオ構築、リサーチ、AI 活用 など）をまとめたものです。ここにあるモジュール群は小さな独立コンポーネントで構成され、ローカル開発／ペーパートレード／本番運用を想定した設計になっています。

主な特徴
--------
- 実行エンジン（ExecutionEngine）と監視プロセス（Monitoring）を分離して運用可能
- Paper Trading モードでは MockBrokerClient を用いて、本番 DB と分離された専用 SQLite に記録
- 監視機能（SystemMonitor / TradeMonitor / RiskMonitor）による自動アラート & Kill Switch
- DuckDB を用いたリサーチ／ファクター計算（価格・財務データ参照）
- OpenAI（gpt-4o-mini）を利用したニュース NLP（銘柄センチメント）と市場レジーム判定
- ログは stdout と日次ローテーションファイル（logs/<app>.log）に出力
- 設定ウィザード（.env の対話式作成）と設定検証 CLI を同梱

セットアップ手順
----------------
1. リポジトリをクローンして、Python 仮想環境を作成・有効化します。
   例:
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストールします。
   - requirements.txt を用意している場合は pip install -r requirements.txt
   - 主要な外部ライブラリ（例）:
     - duckdb
     - psutil
     - openai
     - PyYAML（設定検証で YAML 検証を行う場合）
   （実際の requirements はプロジェクトの配布物に従ってください）

3. 環境変数 (.env) を準備します（プロジェクトルートに .env を置く）。
   - 対話式ウィザードで作成:
     python -m kabusys.config_setup
   - ウィザードで作成した .env を手動で編集して必要な値を設定してください。

4. 設定を検証します:
   python -m kabusys.validate_config
   - 問題があればメッセージに従って .env または config/*.yaml を修正します。
   - --strict オプションを付けると警告も失敗扱いになります。

主要な環境変数（デフォルト/意味）
---------------------------------
- KABUSYS_ENV: 実行環境 (development | paper_trading | live)。デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（monitoring）パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...、デフォルト: INFO）
- LOG_DIR: ログ出力ディレクトリ（デフォルト: logs/）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール利用時に必要）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト: 60）
- PAPER_FILL_MODE: ペーパートレード時の約定モード（instant/partial/never/reject）

使い方（コマンド例）
--------------------

- 環境設定ウィザード（.env の作成・更新）:
  python -m kabusys.config_setup

- 設定検証:
  python -m kabusys.validate_config
  （--strict を付けると警告も失敗扱い）

- 実行エンジン（ExecutionEngine）起動:
  python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録します。
  - 実行中は data/execution.pid が作成されます。
  - 停止: 実行プロセスに対して SIGINT（Ctrl-C）するか、プロジェクトルート/data/stop_requested.flag を作成すると監視ループ・実行スレッドが安全に終了します。

- 監視プロセス起動:
  python -m kabusys.run_monitoring
  - デフォルトで Settings.sqlite_path（例: data/monitoring.db）に監視ログを記録します（KABUSYS_ENV に依存せず本番 sqlite_path を使用する仕様）。
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能（例: MONITOR_POLL_INTERVAL=30）。
  - 停止: data/stop_requested.flag を作成するとループを抜けます。

- Paper Trading 検証レポート作成:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで別 DB を指定可能。環境変数 PAPER_TRADING_SQLITE_PATH も参照します。

- AI 関連（ニュース NLP / レジーム判定）:
  - OpenAI API キー（OPENAI_API_KEY）が必要です。
  - モジュール関数を呼び出して使用します（例: kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime）。
  - 実行スクリプトは用意されていませんが、DuckDB 接続を渡して日次処理を行います。

停止フラグ / Kill Switch
------------------------
- run_monitoring と run_execution はプロジェクトルート/data/stop_requested.flag を監視しており、存在するとプロセスを終了します（明示的な「停止要求」用）。
- KillSwitch はリスク条件（ドローダウンやポジション上限など）に応じて data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送る仕組みです。KillSwitch のトリガーは監視エンジン側で評価されます。

ログ
---
- 共通のロギングセットアップ (kabusys.utils.logging_setup.setup_logging) により、stdout (StreamHandler) と日次ローテーションログファイル（logs/<app_name>.log）に出力します。
- ログディレクトリは環境変数 LOG_DIR または引数で上書き可能。ディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみで出力します。

主要モジュール（抜粋）
---------------------
- run_execution.py: ExecutionEngine 起動スクリプト。KABUSYS_ENV=paper_trading の場合は paper DB を使用。
- run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL で間隔を変更可能。
- config_setup.py: .env を対話式に作成・更新するウィザード。
- validate_config.py: 起動前の設定検証 CLI。
- monitoring/:
  - monitoring_db.py: 監視用 SQLite のスキーマ初期化・読み書き。
  - system_monitor.py: CPU/メモリ/ディスク・データ鮮度・Execution プロセス生存監視。
  - risk_monitor.py: ドローダウン・ポジション上限監視。
  - kill_switch.py: kill.flag 管理。
  - monitoring_engine.py: 個別モニターを束ねてポーリング・アラート評価。
- portfolio/: 候補選定・重み計算・リスク調整・株数決定ロジック（純粋関数群）。
- research/: DuckDB を用いたファクター計算（momentum/value/volatility）や特徴量探索。
- ai/:
  - news_nlp.py: raw_news を OpenAI で解析して ai_scores へ書き込み。
  - regime_detector.py: ETF MA とマクロニュースを合わせた市場レジーム判定。
- tools/:
  - paper_verification_report.py: ペーパートレード検証レポート生成スクリプト。
- utils/:
  - logging_setup.py: ログ統一セットアップ。
  - process_priority.py: プロセス優先度や CPU affinity 設定ユーティリティ。

ディレクトリ構成（主要ファイル）
----------------------------
（プロジェクトルート内、src/kabusys を想定）

- src/kabusys/
  - __init__.py
  - config.py
  - config_setup.py
  - validate_config.py
  - run_execution.py
  - run_monitoring.py
  - tools/
    - __init__.py
    - paper_verification_report.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - (trade_monitor.py, alert_manager.py などはプロジェクト内に存在する想定)
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - utils/
    - __init__.py
    - logging_setup.py
    - process_priority.py
  - monitoring (SQLite/duckdb の初期化や実行を行うファイル群)
  - その他: execution、data、strategy などのサブパッケージ（実行・戦略・データパイプライン用）

運用上の注意
-------------
- 本番（KABUSYS_ENV=live）では Kill Switch / LINE 通知などの設定を必ず確認してください。validate_config の live 向けチェックが警告を出します。
- .env は機密情報を含むため絶対に Git にコミットしないでください（config_setup.py でも注意喚起あり）。
- Paper Trading モードは本番 DB と分離されますが、設定ミスに注意してください（PAPER_TRADING_SQLITE_PATH を明示することを推奨）。
- OpenAI API の呼び出しは失敗やレート制限に備えたリトライ実装が入っていますが、API キーやコスト管理に留意してください。
- process priority / CPU affinity の設定は OS に依存します。権限不足での失敗は警告でスキップされます。

貢献・拡張
-----------
- 設定ファイル（config/*.yaml）や戦略プラグインを追加して拡張できます。
- DuckDB のスキーマや AI のプロンプト調整、ログ出力フォーマットのカスタマイズも容易です。
- 単体テストや CI を追加して各モジュールの動作を検証することを推奨します。

以上。必要であれば、README に含める具体的な .env サンプル、起動スクリプトの systemd / Supervisor 用 unit サンプル、または各モジュールの API 使用例を追記します。どの情報を優先して追加しますか？