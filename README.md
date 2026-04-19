README — KabuSys（日本株自動売買システム）
====================================

概要
----
KabuSys は日本株自動売買システムのコアライブラリ群です。  
戦略（ファクター計算・特徴量解析）、ポートフォリオ構築、発注実行（ExecutionEngine）、監視（MonitoringEngine）、および AI を用いたニュース評価などの主要コンポーネントを含みます。  
設計方針として「本番データとリサーチ/ペーパートレードを分離」「ルックアヘッドバイアスを避ける」「フェイルセーフ（API障害でもシステム継続）」を重視しています。

主な機能
--------
- 発注エンジン（ExecutionEngine）
  - 本番 / ペーパートレードの切替（KABUSYS_ENV）
  - ブローカークライアント抽象化（Mock / 実際のブローカー）
  - リスク管理（ポジション上限、利用率、ドローダウン等）
  - 発注ログの永続化（SQLite）
- 監視（Monitoring）
  - SystemMonitor：CPU/メモリ/ディスク/データ鮮度 / プロセス生存監視
  - TradeMonitor / RiskMonitor：注文滞留・約定異常・ドローダウン監視
  - MonitoringEngine：定期ポーリング、Kill Switch（条件を満たすと停止フラグ書き込み）
  - 監視ログ永続化（SQLite、monitoring_db）
- ポートフォリオ構築（純粋関数）
  - 候補選定、等加重・スコア加重、リスク調整（セクターキャップ、レジーム乗数）、ポジションサイジング（単元株丸め）
- 研究（Research）
  - DuckDB を用いたファクター計算（モメンタム、バリュー、ボラティリティ）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
- AI 関連
  - news_nlp: OpenAI を使ったニュースセンチメントスコアリング（ai_scores テーブル）
  - regime_detector: マクロ記事 + ETF MA200 乖離から市場レジーム判定
- ユーティリティ
  - .env ウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py）
  - ロギング一元設定（utils.logging_setup）
  - プロセス優先度設定 / CPU affinity（utils.process_priority）
  - Paper Trading 検証レポート生成ツール（tools/paper_verification_report.py）

動作に必要な環境変数（主なもの）
--------------------------------
必須（少なくとも設定・確認が必要）
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

任意 / 推奨
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- OPENAI_API_KEY: AI 機能を使う場合に必要
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 DB（デフォルト: data/paper_trading.db）
- LOG_LEVEL, LOG_DIR
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START など

セットアップ手順
----------------
1. レポジトリをクローンし、Python 仮想環境を作成
   - python -m venv .venv
   - source .venv/bin/activate  （Windows は .venv\Scripts\activate）

2. 依存パッケージをインストール
   - 必須ライブラリ（例）:
     - duckdb
     - psutil
     - openai（AI機能を使う場合）
     - PyYAML（設定ファイル検証を行う場合、任意）
   - 例:
     - pip install duckdb psutil openai PyYAML

   （プロジェクトに requirements.txt がある場合はそれを利用してください）

3. 初期設定（.env の作成）
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - もしくは手動でプロジェクトルートに .env を作成する（.env.example を参考）
   - 注意: .env は絶対に Git にコミットしないでください。

4. 設定検証
   - python -m kabusys.validate_config
   - 本番運用前は --strict モードで警告も FAIL 扱いにできます:
     - python -m kabusys.validate_config --strict

5. ディレクトリ作成（必要なら）
   - data/（SQLite 等を置く）
   - logs/（ログ出力）
   多くのスクリプトは起動時にディレクトリを自動作成しますが、権限等に注意してください。

起動・使い方
------------

- ExecutionEngine を起動（通常運用）
  - 環境変数 KABUSYS_ENV により挙動が変わる:
    - paper_trading: MockBroker を使用し、PAPER_TRADING_SQLITE_PATH に記録（本番DBと分離）
    - live: 実際のブローカークライアントを使う（実行前に設定を慎重に確認）
  - 起動コマンド:
    - python -m kabusys.run_execution
  - 停止方法:
    - Kill Switch（データや監視が条件を満たすと data/kill.flag を書き込み）
    - または手動で停止フラグファイルを作成: data/stop_requested.flag（run_execution はこれを検知して安全に停止）

- Monitoring を起動
  - 起動コマンド:
    - python -m kabusys.run_monitoring
  - ポーリング間隔:
    - 環境変数 MONITOR_POLL_INTERVAL で秒数を上書き可能（デフォルト 60 秒）
  - 監視は Settings.sqlite_path（監視用 sqlite）を用いる（KABUSYS_ENV に依らず本番 sqlite_path を使う点に注意）
  - 停止:
    - data/stop_requested.flag を作成すると run_monitoring はループを抜けて終了します

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスを指定する場合:
    - --db PATH または 環境変数 PAPER_TRADING_SQLITE_PATH を使用

- AI 機能（ニューススコア / レジーム判定）
  - OpenAI の API キーを環境変数 OPENAI_API_KEY に設定
  - ニューススコア（ai_scores 追記）:
    - 直接モジュール関数を呼び出す等の運用を想定（例: スケジューラから実行）
  - 実行時に API 呼び出しが失敗してもフェイルセーフで継続する設計

ログ・プロセス管理
------------------
- ログ:
  - utils.logging_setup.setup_logging を使い、stdout と日次ローテートログ（logs/<app_name>.log）へ出力します
  - ログレベルは .env の LOG_LEVEL または引数で制御
- プロセス優先度:
  - スクリプト起動時に set_process_priority("high") を呼んで高優先度へ設定を試みます（権限不足時は警告）
- PID / フラグファイル:
  - 実行時に data/execution.pid（デフォルト）や data/kill.flag / data/stop_requested.flag を使用して制御します

ディレクトリ構成（主要ファイル）
-------------------------------
以下は src/kabusys 配下の主要モジュールと役割の概観です。

- __init__.py
  - パッケージ定義（バージョン等）

- config.py
  - 環境変数・.env ロードと Settings クラス（各設定の取得）

- config_setup.py
  - 対話式 .env 作成ウィザード

- validate_config.py
  - 起動前の設定検証 CLI

- run_execution.py
  - ExecutionEngine 起動スクリプト（スレッドでエンジン実行、停止フラグ監視）

- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL で制御）

- utils/
  - logging_setup.py: ログ設定ユーティリティ
  - process_priority.py: プロセス優先度 / CPU affinity
  - （その他ユーティリティ）

- monitoring/
  - monitoring_db.py: 監視用 SQLite 永続化レイヤ（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py, trade_monitor.py, risk_monitor.py: 各種監視ロジック
  - monitoring_engine.py: 各モニタ統合ポーリング、KillSwitch 連携
  - kill_switch.py, alert_manager.py（アラート処理）

- execution/
  - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py
  - 発注処理・リスク管理・ブローカー抽象等

- portfolio/
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py
  - 候補選定・重み付け・ポジションサイズ計算・セクターキャップ等

- research/
  - factor_research.py, feature_exploration.py
  - ファクター計算、将来リターン、IC、統計サマリ等（DuckDB を使用）

- ai/
  - news_nlp.py: ニュースセンチメント → ai_scores
  - regime_detector.py: マクロ + ETF MA200 で市場レジーム判定

- tools/
  - paper_verification_report.py: ペーパートレード検証レポート生成

運用上の注意
------------
- KABUSYS_ENV を live にする際は設定（特にブローカー資格情報・LINE 通知設定・KILL フラグの扱い）を慎重に確認してください。validate_config の live チェックがガードを出します。
- .env は秘匿情報を含むため厳重に管理してください（.gitignore に登録）。
- OpenAI 等外部 API を使う機能は失敗に対してフォールバック設計がありますが、API キー漏洩・料金発生には注意してください。
- 監視コンポーネントは停止フラグ（data/stop_requested.flag）・kill.flag 等のファイル操作で制御します。CI やオーケストレーション環境での運用時はこれらファイルの扱いに注意してください。

開発・テスト
------------
- 自動環境変数読み込み:
  - プロジェクトルートで .env / .env.local が見つかると自動的に読み込まれます（テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
- YAML 設定の検証は PyYAML がある場合のみ行われます。
- モジュールは可能な限り副作用を抑えた純粋関数設計（research / portfolio 等）を採用しており、ユニットテストがしやすい構造です。

サンプルコマンド一覧
--------------------
- .env を作成:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- Execution 起動:
  - python -m kabusys.run_execution
- Monitoring 起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

ライセンス / 貢献
-----------------
（この README にはライセンス情報は含まれていません。必要に応じてプロジェクトの LICENSE ファイルを参照してください。）

最後に
------
この README はソースコードのコメント・モジュール設計に基づいて作成しました。実運用前に必ずローカルで動作確認（.env の設定、依存パッケージの整備、validate_config の実行）を行ってください。質問や追加のドキュメントが必要であれば教えてください。