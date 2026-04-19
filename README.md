README
=====

概要
----
KabuSys は日本株向けの自動売買／リサーチ基盤のサンプル実装です。本リポジトリは以下の主要機能を持ちます。

- 実行エンジン（ExecutionEngine）による発注フロー（本番・ペーパートレード対応）
- システム監視（Monitoring）: プロセス・リソース・データ鮮度・リスク監視
- Kill Switch（フラグファイル）による強制停止
- ポートフォリオ構築（候補選定・重み付け・ロット丸め）
- リサーチ（ファクター計算・将来リターン・IC 等）
- ニュース NLP / レジーム判定（OpenAI を用いたセンチメント評価）
- 各種ユーティリティ（設定ウィザード、設定検証、ログ設定、プロセス優先度設定）
- ペーパートレードの検証レポート生成ツール

設計方針の要点:
- 環境変数/.env を用いた設定管理（自動ロード機能あり）
- 本番 DB とペーパートレード DB の分離
- LLM 呼び出しは API キー依存（OpenAI）
- 監視と実行はファイルフラグで連携（data/kill.flag, data/stop_requested.flag）

主要機能一覧
--------------
- 環境設定ウィザード: python -m kabusys.config_setup で .env を対話的に作成/更新
- 設定検証: python -m kabusys.validate_config で必須環境変数・ファイルのチェック
- 実行エンジン起動: python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBroker を使用し data/paper_trading.db に記録
- 監視起動: python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL（秒）でポーリング周期を上書き可能（デフォルト 60 秒）
  - 監視は環境にかかわらず本番 sqlite_path を使用して記録
- Paper Trading 検証レポート: python -m kabusys.tools.paper_verification_report
- ポートフォリオ構築ユーティリティ:
  - 候補選定、等重配分・スコア加重、リスク調整（セクターキャップ・レジーム乗数）
  - ポジションサイズ計算（単元株丸め、aggregate cap）
- AI 機能:
  - news_nlp.score_news: OpenAI でニュースをスコアリングして ai_scores テーブルに書き込み
  - regime_detector.score_regime: ETF とマクロニュースを組み合わせて市場レジームを判定
- 監視コンポーネント:
  - SystemMonitor, TradeMonitor, RiskMonitor, KillSwitch, MonitoringEngine
- ユーティリティ:
  - ログ設定（kabusys.utils.logging_setup）
  - プロセス優先度 / CPU affinity（kabusys.utils.process_priority）

セットアップ手順
----------------
1. Python 環境（推奨: 3.10+）を用意します。

2. 依存パッケージをインストールします。主要なパッケージ例:
   - duckdb
   - psutil
   - openai
   - PyYAML（config 検証をフルチェックする場合）
   実際は requirements.txt がある想定で:
     pip install -r requirements.txt
   または必要に応じて個別インストール:
     pip install duckdb psutil openai PyYAML

3. プロジェクトルートに .env を作成します（.env.example を参考にしてください）。
   - 対話式で作成する:
       python -m kabusys.config_setup
   - 自動読み込み:
     - デフォルトで .env/.env.local をプロジェクトルートから自動ロードします。
     - 自動ロードを無効化する場合:
         export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

4. 必須環境変数の例（.env に設定）:
   - JQUANTS_REFRESH_TOKEN=...
   - KABU_API_PASSWORD=...
   - KABUSYS_ENV=development|paper_trading|live
   - DUCKDB_PATH=data/kabusys.duckdb
   - SQLITE_PATH=data/monitoring.db
   - (ペーパートレード用) PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
   - OPENAI_API_KEY=...（AI 機能を使う場合）

5. 設定検証:
     python -m kabusys.validate_config
   警告も致命的に扱う場合:
     python -m kabusys.validate_config --strict

6. データディレクトリ/ログディレクトリの作成は多くのモジュールが自動で行いますが、必要に応じて手動作成してください:
     mkdir -p data logs

使い方
-------
基本的なコマンド:

- 環境設定ウィザード（.env の生成/更新）
    python -m kabusys.config_setup

- 設定検証
    python -m kabusys.validate_config
    python -m kabusys.validate_config --strict

- 実行エンジン起動（ExecutionEngine）
    python -m kabusys.run_execution
  注意:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient が使われ、記録は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ行われます。
    - 起動中に data/stop_requested.flag が作成されるとエンジンは停止します。
    - 実行中の PID は data/execution.pid に書き込まれます。

- 監視プロセス起動（Monitoring）
    python -m kabusys.run_monitoring
  オプション:
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を指定可能（デフォルト 60）。
    - 監視は環境に関係なく本番 sqlite_path（SQLITE_PATH）へ記録します。
    - 監視停止は data/stop_requested.flag を作成するか Ctrl+C。

- ペーパートレード検証レポート
    python -m kabusys.tools.paper_verification_report
  期間指定例:
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  DB 指定:
    python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI 機能（ニューススコアリング / レジーム判定）
  これらは duckdb 接続を受ける関数として提供されています。実行には OPENAI_API_KEY が必要です。
  例（スクリプトから呼び出す場合）:
    from kabusys.ai.news_nlp import score_news
    score_news(conn, target_date, api_key="...")

環境変数（主なもの）
---------------------
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視用）ファイルパス（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- LOG_DIR: ログ出力先ディレクトリ（デフォルト logs/）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を利用する場合）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒）。run_monitoring で使用。
- KILL_FLAG_CLEAR_ON_START: 本番で危険な設定（0 推奨）

監視・停止
-----------
- Kill Switch:
  - kill.flag（デフォルト: data/kill.flag）を作成すると ExecutionEngine に停止シグナルが送られます（KillSwitch がフラグを書き込む実装）。
  - KillSwitch は drawdown やポジション上限などのリスク条件で発動します。
- stop_requested.flag:
  - run_monitoring/run_execution は data/stop_requested.flag をチェックし、存在すれば安全に終了します。
- PID ファイル:
  - 実行中のエンジンは data/execution.pid 等に PID を書きます。

ディレクトリ構成
-----------------
以下は主要ファイル・パッケージの概要（src/kabusys 以下を想定）:

- __init__.py
  - パッケージ定義・バージョン

- config.py
  - 環境変数/.env の読み込み・Settings クラス（各種設定プロパティ）

- config_setup.py
  - .env の対話式ウィザード

- validate_config.py
  - 起動前チェック CLI（必須環境変数・ファイル・YAML 構文など）

- run_execution.py
  - ExecutionEngine 起動スクリプト（KABUSYS_ENV に応じて挙動変更）

- run_monitoring.py
  - SystemMonitor ポーリング起動スクリプト（MONITOR_POLL_INTERVAL 指定可）

- utils/
  - logging_setup.py: ログの統一設定（コンソール + 日次ローテートファイル）
  - process_priority.py: プロセス優先度 / CPU affinity 設定
  - その他ユーティリティ

- monitoring/
  - monitoring_db.py: SQLite による永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py: CPU/MEM/DISK/プロセス/データ鮮度チェック
  - trade_monitor.py: （注文監視 — 省略されているが設計上存在）
  - risk_monitor.py: ドローダウン / ポジション上限の監視
  - kill_switch.py: フラグファイル書き込みロジック
  - monitoring_engine.py: 監視コンポーネントの Orchestrator
  - alert_manager.py: （通知機能: LINE などを想定）

- execution/
  - execution_engine.py, order_manager.py, order_repository.py, broker_factory.py, reconciler.py, risk_manager.py
  - 発注フロー、ブローカー抽象化、リスク管理、注文再調整等（実運用ロジック）

- portfolio/
  - portfolio_builder.py: 候補選定・重み付け
  - position_sizing.py: 発注株数計算（ロット丸め・aggregate cap）
  - risk_adjustment.py: セクター上限・レジーム乗数

- research/
  - factor_research.py: モメンタム/ボラティリティ/バリューの計算（DuckDB）
  - feature_exploration.py: 将来リターン / IC / 統計サマリ

- ai/
  - news_nlp.py: ニュースを OpenAI で評価して ai_scores に書き込み
  - regime_detector.py: ETF MA とマクロニュースでレジーム判定

- tools/
  - paper_verification_report.py: ペーパートレード DB を解析して検証レポートを出力

注意事項 / ベストプラクティス
-----------------------------
- .env は絶対にリポジトリにコミットしないでください（機密情報を含む）。
- KABUSYS_ENV=live の場合は設定を慎重に確認してください（本番では自動クリア等の設定は危険）。
- AI 機能を使用する場合、API レート制限やエラーに備えたリトライ・フォールバック処理がありますが、API キー管理は慎重に行ってください。
- 監視は production の sqlite_path を使用して記録します。テスト目的で監視を変更したい場合は設定を確認してください。
- ログ: logs/<app_name>.log に日次ローテーションで出力されます。LOG_DIR 環境変数で変更可能。

ライセンス・貢献
----------------
（ここにライセンス表記や貢献方法を追記してください）

以上。プロジェクトの構造や主要な実行方法は上記の通りです。README に追加したい具体的なコマンド例や依存関係リスト（requirements.txt）などがあれば教えてください。