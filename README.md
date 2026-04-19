KabuSys — 日本株自動売買システム（抜粋）
==================================

このリポジトリは日本株向けの自動売買システム用ライブラリ／起動スクリプト群を含みます。  
ここではコードベースの主要コンポーネント、セットアップ手順、実行方法、ディレクトリ構成を簡潔にまとめます。

概要
----
KabuSys は次の主要な責務を持ちます。

- 注文実行（ExecutionEngine）: 実際のブローカーへの発注（本番 / ペーパートレード）を行う。
- 監視（Monitoring）: システム状態・注文状況・リスク指標を定期ポーリングしてログ・アラート・Kill Switch を管理。
- ポートフォリオ構築: シグナルから候補選定、重み付け、ポジションサイズ決定を行う純粋関数群。
- リサーチ: DuckDB 上の時系列データを使ったファクター計算・特徴量解析。
- AI 支援: ニュースの NLP 評価・市場レジーム判定（OpenAI API を使用するモジュール）。
- ユーティリティ: ログ設定、プロセス優先度設定、.env ウィザード、設定検証 CLI、ツール（検証レポート生成）など。

主な機能一覧
--------------
- ExecutionEngine 起動スクリプト（src/kabusys/run_execution.py）
  - KABUSYS_ENV により paper_trading / live / development を切り替え
  - paper_trading 時は MockBrokerClient を使用して data/paper_trading.db に記録（本番 DB と分離）
  - 停止フラグと PID 管理（data/stop_requested.flag, data/execution.pid）
- Monitoring 起動スクリプト（src/kabusys/run_monitoring.py）
  - SystemMonitor をポーリングして system_status / risk_logs / trade_logs 等へ永続化
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）
  - 監視は常に本番 sqlite_path を使用（環境に依存しない）
- Monitoring 内の主要コンポーネント
  - MonitoringDB: SQLite を使った永続化層（冪等なテーブル作成・マイグレーション含む）
  - SystemMonitor: CPU/メモリ/ディスク/プロセス状態・データ鮮度チェック
  - RiskMonitor: ドローダウン・ポジション上限の監視とダッシュボード更新
  - KillSwitch: 条件成立時に data/kill.flag を書いて ExecutionEngine を止める
  - MonitoringEngine: 各モニタを組み合わせたポーリング実行ループ
- ポートフォリオ構成モジュール（kabusys.portfolio）
  - 候補選定（score 降順）、等配分／スコア重み、リスクベース配分、セクターキャップ、レジーム乗数など
- リサーチ（kabusys.research）
  - DuckDB を前提にファクター（momentum / volatility / value）や forward returns を計算
  - IC 計算、統計サマリなど
- AI モジュール（kabusys.ai）
  - news_nlp: OpenAI を使ったニュースの銘柄単位センチメント算出（ai_scores へ書き込み）
  - regime_detector: ETF + マクロニュースを組み合わせて日次レジーム判定（market_regime テーブルへ保存）
  - OpenAI 呼び出しはリトライ/バックオフやレスポンスバリデーションを備える
- ツール
  - config_setup: 対話式 .env 生成ウィザード（src/kabusys/config_setup.py）
  - validate_config: .env と config/*.yaml の事前検証 CLI（src/kabusys/validate_config.py）
  - paper_verification_report: ペーパートレード DB から検証レポートを生成（src/kabusys/tools/paper_verification_report.py）
- ユーティリティ
  - logging_setup: stdout + 日次ローテートファイルで統一ログを設定
  - process_priority: Windows / POSIX を吸収したプロセス優先度・CPU affinity 設定

前提条件（依存ライブラリの例）
------------------------------
実行には少なくとも以下のパッケージが必要です（プロジェクトの requirements.txt を参照してください）:
- Python 3.9+（コードで型ヒントなどを利用）
- duckdb
- psutil
- openai （AI 機能を使う場合）
- PyYAML（config YAML 検証を行う場合、任意）

セットアップ手順
---------------
1. リポジトリをクローンしてソースを配置
2. 仮想環境を作成して依存をインストール
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate
     - pip install -r requirements.txt
3. .env を作成（環境変数設定）
   - 対話式ウィザードを使うのが簡単:
     - python -m kabusys.config_setup
   - もしくは .env を手動で作成し、少なくとも必須キーを設定:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
   - 主要な環境変数（代表）
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
     - SQLITE_PATH: data/monitoring.db（監視 DB、デフォルト）
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（ペーパートレード専用 DB）
     - LOG_LEVEL: DEBUG|INFO|...（デフォルト INFO）
     - OPENAI_API_KEY: OpenAI を利用する場合は必須（AI 機能）
     - PAPER_FILL_MODE: instant|partial|never|reject（ペーパートレードの約定モード）
     - KILL_FLAG_CLEAR_ON_START: 0|1（本番では 0 推奨）
4. 設定検証（推奨）
   - python -m kabusys.validate_config
   - 警告をエラーとして扱う strict モード:
     - python -m kabusys.validate_config --strict

起動・使い方
------------

ログ設定
- setup_logging がログを初期化します。デフォルトは logs/<app_name>.log に日次ローテーション（30 日保持）と stdout 出力。
- LOG_DIR 環境変数でログディレクトリを指定可。

ExecutionEngine（発注エンジン）起動
- 実行:
  - python -m kabusys.run_execution
- 動作:
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録。本番 DB（SQLITE_PATH）とは分離。
  - 起動時に data/stop_requested.flag が既に存在する場合は起動せず終了。
  - 実行中は data/execution.pid に PID ファイルを書き込みます。停止は stop_requested.flag（run の親ディレクトリ data/stop_requested.flag）作成で指示できます。

Monitoring（監視）起動
- 実行:
  - python -m kabusys.run_monitoring
- オプション / 環境変数:
  - MONITOR_POLL_INTERVAL: ポーリング間隔（秒）。デフォルト 60。1 未満や不正値は無視され 60 秒を採用します。
- 動作:
  - SystemMonitor / TradeMonitor / RiskMonitor 等を定期実行し monitoring DB（settings.sqlite_path, デフォルト data/monitoring.db）へログを残します。
  - 監視は常に本番 sqlite_path を使用（環境変数に依らず）。
  - data/stop_requested.flag を検知すると監視ループを終了します。

Kill Switch（自動停止）
- RiskMonitor 等の評価で条件を満たすと KillSwitch が data/kill.flag を書き込み、ExecutionEngine 側で検知して安全に停止します。
- 本番で KILL_FLAG_CLEAR_ON_START=1 にしておくと起動時に自動クリアされますが、危険（本番では 0 推奨）です。

Paper Trading 検証レポート
- 実行:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH または環境変数 PAPER_TRADING_SQLITE_PATH
- 出力:
  - 注文成功率、送信率、稼働率、レイテンシ（P95）などを算出して PASS/FAIL を判定します。

AI 機能（news_nlp / regime_detector）
- OpenAI API を使用します。必ず OPENAI_API_KEY を設定してください（引数でも指定可）。
- 大量 API 呼び出しではバッチ処理・リトライ・バリデーションが実装されています。
- AI 機能は外部 API に依存するため、API キーの設定とコスト管理に注意してください。

停止・デバッグ・ファイル
- 停止フラグ:
  - data/stop_requested.flag: run_execution / run_monitoring が監視している停止フラグ（存在で停止）。
  - data/kill.flag: KillSwitch が書き込む停止フラグ（ExecutionEngine 側で検知）。
- PID ファイル:
  - data/execution.pid を ExecutionEngine が使用します。
- ログ:
  - デフォルト logs/<app_name>.log（stdout も標準出力されます）
- DB:
  - DuckDB: data/kabusys.duckdb
  - Monitoring SQLite: data/monitoring.db
  - Paper Trading SQLite: data/paper_trading.db

設定・動作上の注意
-----------------
- 本番環境（KABUSYS_ENV=live）では LINE 通知設定（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）等の確認や Kill Switch の設定に注意してください。validate_config はライブ向けガードチェックを行います。
- .env は決してリポジトリにコミットしないでください（config_setup は注記あり）。
- OpenAI 等外部 API キーは安全に管理してください。
- Paper Trading と本番 DB は分離されていますが、設定ミスで上書きしないよう paths を確認してください。

ディレクトリ構成（主要ファイル）
----------------------------
src/kabusys/
- __init__.py
- config.py                — 環境変数 / Settings 管理（自動で .env 読込を行う）
- config_setup.py          — .env 対話式ウィザード
- validate_config.py       — 設定検証 CLI
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — Monitoring 起動スクリプト
- tools/
  - paper_verification_report.py
- utils/
  - logging_setup.py       — ルートロギング設定
  - process_priority.py    — クロスプラットフォームでのプロセス優先度設定
- monitoring/
  - monitoring_db.py       — SQLite テーブル定義 / MonitoringDB
  - system_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - monitoring_engine.py
  - trade_monitor.py       — （参照あり。注文周りの監視を実装）
  - alert_manager.py       — （アラート送信の実装ポイント）
- execution/
  - execution_engine.py
  - order_manager.py
  - order_repository.py
  - broker_factory.py
  - reconciler.py
  - risk_manager.py
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

（注）リストはこの README 作成時点での主要ファイルを抜粋しています。詳細はソースツリーを参照してください。

よく使うコマンド例
-----------------
- .env を対話式で作る:
  - python -m kabusys.config_setup
- 設定を検証する:
  - python -m kabusys.validate_config
  - 厳密モード（警告も失敗）: python -m kabusys.validate_config --strict
- Execution を起動する:
  - python -m kabusys.run_execution
- Monitoring を起動する:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- OpenAI キーを一時的に指定して regime_detector を実行する（開発用関数呼び出し）:
  - 実行時に環境変数 OPENAI_API_KEY を設定

開発・拡張のヒント
------------------
- DuckDB 接続を受け取る設計になっており、研究用モジュールは DB に依存しているためローカルで DuckDB ファイルを準備してからテストしてください。
- AI 呼び出しはテスト時に差し替え可能（各モジュールの _call_openai_api を patch する等）。
- logging_setup はすべての起動ポイントから呼び出してログを統一できます。
- MonitoringDB は冪等なテーブル作成と簡単なマイグレーションロジックを持ちます。スキーマ変更時は注意して増分マイグレーションを実装してください。

最後に
------
この README はソースコードの主要な使用法と構成を説明するためのものです。実行前に必ず validate_config で環境設定をチェックし、.env の内容を慎重に確認してください。質問や補足の希望があれば教えてください。