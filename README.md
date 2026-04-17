README
======

概要
----
KabuSys は日本株向けの自動売買／リサーチ基盤のユーティリティ群です。  
主に以下の責務を持つモジュールを含みます。

- 戦略（ファクター計算・特徴量探索）とポートフォリオ構築（weights, position sizing）
- Execution（注文管理、リスク管理、発注エンジン起動スクリプト）
- Monitoring（システム稼働・注文・リスク監視、アラート・Kill Switch）
- AI モジュール（ニュースの NLP スコアリング、レジーム判定）
- 各種ツール（.env ウィザード、設定検証、Paper Trading 検証レポート）

本リポジトリは純粋関数的なポートフォリオロジックや DuckDB を用いたリサーチ処理、
SQLite を用いた監視ログ永続化、外部 API（kabuステーション / J-Quants / OpenAI）連携を含みます。

主な機能
--------
- 環境設定ウィザード（.env 自動生成）
- 設定検証 CLI（必須環境変数、ファイルの存在、YAML 構文チェック）
- ExecutionEngine 起動（本番 / ペーパートレード分離）
- Monitoring（SystemMonitor / TradeMonitor / RiskMonitor を組み合わせたポーリング）
- Kill Switch（ドローダウンやポジション上限到達時に停止フラグを書き込み）
- AI: ニュースのセンチメントスコアリング（OpenAI）、市場レジーム判定
- Paper Trading 向け検証レポート生成（SQLite を集計して PASS/FAIL 判定）
- ポートフォリオ構築ユーティリティ（候補選定、重み計算、ポジションサイズ算出）
- DuckDB を使ったファクター計算・研究用ユーティリティ

前提・依存パッケージ
--------------------
（少なくとも本リポジトリで直接利用されているライブラリ）

- Python 3.9+
- duckdb
- psutil
- openai
- requests
- (オプション) PyYAML — config/*.yaml の構文チェックに使用

インストール例（仮）
- 仮想環境作成
  python -m venv .venv
  source .venv/bin/activate
- 必要パッケージをインストール
  pip install duckdb psutil openai requests pyyaml

セットアップ手順
----------------

1. リポジトリをクローンしてワークディレクトリに移動。

2. .env を作成
   - 対話形式ウィザードを使う（推奨）:
     python -m kabusys.config_setup
   - 手動で作成する場合は .env.example を参考に必要な環境変数を設定してください。

   重要な環境変数（抜粋）
   - JQUANTS_REFRESH_TOKEN（必須）
   - KABU_API_PASSWORD（必須）
   - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
   - OPENAI_API_KEY（AI 機能を使う場合に必須）
   - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH（監視用、デフォルト: data/monitoring.db）
   - PAPER_TRADING_SQLITE_PATH（KABUSYS_ENV=paper_trading 時の DB、デフォルト: data/paper_trading.db）
   - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（アラート送信用、任意）
   - LOG_LEVEL（デフォルト: INFO）
   - MONITOR_POLL_INTERVAL（監視ポーリング間隔（秒）、デフォルト 60）

3. 設定検証（起動前に実行推奨）
   python -m kabusys.validate_config
   --strict を付けると警告も失敗扱いになります。

4. DB 初期化
   - Monitoring 用のテーブルは run_monitoring / run_execution 内で自動作成（init_monitoring_db）されます。
   - DuckDB のテーブル（prices_daily, raw_news など）は別途データ投入処理が必要です（本 README では省略）。

使い方（主要スクリプト）
-----------------------

- 環境ウィザード（.env 作成）
  python -m kabusys.config_setup

- 設定検証
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- ExecutionEngine 起動（本番 or paper_trading は KABUSYS_ENV で切替）
  python -m kabusys.run_execution

  動作概要:
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db に記録（本番 DB と分離）。
  - 起動前に data/stop_requested.flag が存在すると起動をスキップします。
  - 実行中に stop_requested.flag を作成するとエンジン停止処理が行われます。
  - Engine は data/execution.pid に PID を書きます（プロセス生存確認に使用）。

- Monitoring 起動
  python -m kabusys.run_monitoring

  オプション:
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き（デフォルト 60）。
  動作概要:
  - SystemMonitor / TradeMonitor / RiskMonitor を周期的に実行し、MonitoringDB（SQLite）にログを永続化します。
  - 監視は本番 sqlite_path を使用（KABUSYS_ENV に依らず同一の monitoring DB を使います）。
  - data/stop_requested.flag が存在するとループを抜けて終了します。

- Paper Trading 検証レポート
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  オプション: --db で SQLite ファイルを指定しない場合は PAPER_TRADING_SQLITE_PATH 環境変数、さらに無ければ data/paper_trading.db を参照します。

停止・Kill Switch
-----------------
- 優雅な停止（手動）
  - 監視/実行プロセスの停止要求ファイル:
    - data/stop_requested.flag — run_monitoring/run_execution が監視しているフラグ。作成するとループを抜ける。
  - Kill Switch（自動）
    - RiskMonitor / KillSwitch によって条件（ドローダウン、ポジション上限など）が満たされると data/kill.flag（Settings.kill_flag_path）へ理由を書き込みます。
    - kill.flag が書かれると ExecutionEngine 側で停止処理が行われます（実装に合わせた監視を行ってください）。
  - 手動で kill.flag をクリアする:
    - 実行前にクリアする場合は単にファイルを削除してください。Settings.kill_flag_clear_on_start=1 の場合、起動時に自動クリアされますが本番では 0 を推奨します。

設定と挙動のポイント
-------------------
- Paper Trading 分離: KABUSYS_ENV=paper_trading の場合、paper_sqlite_path（デフォルト data/paper_trading.db）を使用して発注ログを保存し、本番 DB と完全分離します。
- MONITOR_POLL_INTERVAL（秒）で監視ループ間隔を調整可能。0 以下の設定は無効でデフォルトにフォールバックします。
- プロセス優先度: run_monitoring/run_execution は起動時に set_process_priority("high") を呼びます。psutil の権限により失敗する場合は警告でスキップされます。
- DB マイグレーション: init_monitoring_db() は冪等でテーブルを作成し、必要に応じてカラム追加（migration）を行います。
- LINE アラート: AlertManager は channel token / user id が空の場合は送信を行わずログに記録します。クールダウン機構あり。

ディレクトリ構成（抜粋）
----------------------
src/kabusys/
- __init__.py
- config.py                 — 環境変数読み込み・Settings
- config_setup.py           — .env 対話式ウィザード
- validate_config.py        — 設定検証 CLI
- run_execution.py          — ExecutionEngine 起動スクリプト
- run_monitoring.py         — Monitoring ポーリングループ起動スクリプト
- tools/
  - paper_verification_report.py
- ai/
  - news_nlp.py
  - regime_detector.py
- monitoring/
  - monitoring_db.py
  - monitoring_engine.py
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - alert_manager.py
- execution/                 — Execution エンジン関連（OrderRepository 等）
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- utils/
  - process_priority.py

（プロジェクトルート）
- .env, .env.local（任意）
- data/                      — デフォルト DB / PID / flag ファイルを配置する想定
  - kabusys.duckdb (default)
  - monitoring.db (default)
  - paper_trading.db (paper trading 用)
  - execution.pid
  - kill.flag
  - stop_requested.flag

補足・運用上の注意
-----------------
- OpenAI（news_nlp, regime_detector）を利用する場合は OPENAI_API_KEY を設定してください。API 呼び出しはレート制限やネットワーク障害に備えリトライ・フォールバックが組み込まれていますが、API コストとレイテンシに注意してください。
- 設定検証（validate_config）は起動前に必ず実行し、特に KABUSYS_ENV=live の場合は警告項目を慎重に確認してください（LINE トークン未設定や KILL_FLAG_CLEAR_ON_START の危険設定など）。
- DuckDB / prices_daily 等のデータは別途パイプラインで投入する前提です。Research モジュールはこれらのテーブルを参照します。
- ログレベルは環境変数 LOG_LEVEL で設定できます（DEBUG/INFO/...）。production では INFO 以上を推奨します。

フィードバック / 開発
-------------------
- モジュールはできるだけ副作用を避ける設計（純関数的部分と外部依存部分の分離）がされています。単体テストやモックによるテストが容易です。
- 追加のインストール／実行スクリプトや CI 設定がある場合は README を更新してください。

以上。必要に応じて README の特定セクション（例: デプロイ手順、サンプル .env）を追記します。どの形式（Markdown ファイルや別言語）での出力が良いか教えてください。