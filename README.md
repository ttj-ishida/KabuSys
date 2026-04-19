README — KabuSys（日本株自動売買システム）
=================================

概要
----
KabuSys は日本株の自動売買／リサーチを目的とした軽量なフレームワークです。  
設計方針として「プロダクション志向」「フェイルセーフ」「ルックアヘッドバイアス対策」を採用しており、以下の主要機能を備えます。

主な特徴 / 機能一覧
-----------------
- 実行エンジン（ExecutionEngine）起動スクリプト（run_execution）
  - 本番 / ペーパートレードを環境変数で切替（KABUSYS_ENV）
  - Paper Trading 時は MockBrokerClient を使用し、専用の SQLite（data/paper_trading.db）に記録
  - 停止フラグ（data/stop_requested.flag / data/kill.flag）による安全停止
  - PID ファイル管理（data/execution.pid）
- 監視ループ（SystemMonitor / MonitoringEngine）（run_monitoring）
  - CPU/メモリ/ディスク/プロセス生存確認、データ鮮度検査
  - ポーリング間隔を環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）
  - 監視ログは SQLite（data/monitoring.db）に永続化
- 監視永続化層（monitoring.monitoring_db）
  - system_status, trade_logs, positions, risk_logs, dashboard テーブルおよびマイグレーション対応
- リスク監視（RiskMonitor）
  - ドローダウン警告、ポジション上限検知、ダッシュボード更新とリスクログ出力
- Kill Switch（kill_switch）
  - 指定条件成立時に data/kill.flag を書き込み、実行エンジンを停止させる
- ポートフォリオ構築ユーティリティ（portfolio）
  - 候補選定、等配分 / スコア配分、ポジションサイズ計算、セクターキャップ、レジーム乗数
- リサーチモジュール（research）
  - ファクター計算（momentum / volatility / value）、将来リターン、IC 計算、統計サマリ
  - DuckDB を用いた高速な分析処理
- AI モジュール（ai）
  - ニュース NLP（OpenAI）による銘柄別センチメント付与（ai_scores へ書き込み）
  - 市場レジーム判定（ma200 + マクロセンチメントの合成）
  - API 呼び出しはリトライ・フェイルセーフあり
- ユーティリティ
  - ロギング設定（utils.logging_setup）: stdout + 日次ローテートファイル出力
  - プロセス優先度 / CPU affinity 設定（utils.process_priority）
  - 環境設定ウィザード（config_setup）と設定検証 CLI（validate_config）
- 運用ツール
  - ペーパートレード検証レポート生成スクリプト（tools/paper_verification_report）

セットアップ手順
---------------
1. 必要条件
   - Python 3.9+（パッケージの型注釈に合わせて適宜）
   - pip
   - 推奨パッケージ（代表例）:
     - duckdb
     - psutil
     - openai
     - PyYAML（config 検証で任意）
   - 例:
     pip install duckdb psutil openai PyYAML

2. プロジェクト配置
   - リポジトリをクローンし、プロジェクトルート（pyproject.toml または .git がある階層）で操作してください。

3. 環境変数設定（.env）
   - 対話式ウィザードで .env を生成できます:
     python -m kabusys.config_setup
   - 生成後、内容を確認・必要項目（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD など）を設定してください。
   - 最低限必要な環境変数（例）:
     KABUSYS_ENV=development
     JQUANTS_REFRESH_TOKEN=your_token_here
     KABU_API_PASSWORD=your_password_here
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     LOG_LEVEL=INFO
     KILL_FLAG_CLEAR_ON_START=0
   - メモ:
     - KABUSYS_ENV により動作モードを切替（development / paper_trading / live）
     - PAPER_FILL_MODE（paper_trading の振る舞い）: instant | partial | never | reject

4. 設定検証
   - 自動ロードされた .env と config/*.yaml を検査する:
     python -m kabusys.validate_config
   - 警告を FAIL 扱いにする:
     python -m kabusys.validate_config --strict

5. データディレクトリ
   - スクリプトはデフォルトで data/ 以下に DB やフラグファイル、logs/ ディレクトリにログを出力します。必要に応じて .env のパスを変更してください。

使い方（主要コマンド）
-------------------
- 環境設定ウィザード
  - python -m kabusys.config_setup
    - .env を対話的に生成・更新します。

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 DB を使用（PAPER_TRADING_SQLITE_PATH またはデフォルト data/paper_trading.db）
    - 起動時に data/stop_requested.flag が存在すると起動せず終了します。
    - 実行中に停止させるには data/stop_requested.flag を作成するか、Kill Switch（data/kill.flag）を利用します。

- 監視プロセス起動（SystemMonitor）
  - python -m kabusys.run_monitoring
    - MONITOR_POLL_INTERVAL 環境変数でポーリング秒数を指定可能（例: MONITOR_POLL_INTERVAL=120）
    - 監視は本番 sqlite_path を常に使用（環境に依らず monitoring DB に書き込み）

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  - 判定基準（README 内定義）:
    - 稼働率 >= 99%
    - 注文成立率 >= 90%
    - 送信率 >= 95%
    - P95 レイテンシ <= 200 ms

- AI モジュール（ライブラリ的に利用）
  - ニューススコアリング:
    from kabusys.ai.news_nlp import score_news
    score_news(duckdb_conn, target_date, api_key=None)
  - レジーム判定:
    from kabusys.ai.regime_detector import score_regime
    score_regime(duckdb_conn, target_date, api_key=None)
  - 注意: OpenAI API キーは引数で渡すか OPENAI_API_KEY 環境変数を設定してください。

運用のポイント / ファイル・フラグ
--------------------------------
- データ / フラグ類（デフォルト）
  - data/monitoring.db         — 監視用 SQLite DB（init_monitoring_db でテーブル作成）
  - data/paper_trading.db      — ペーパートレード用 SQLite DB（paper_trading モード）
  - data/kabusys.duckdb        — DuckDB ファイル（分析用）
  - data/execution.pid         — 実行エンジンの PID ファイル（ExecutionEngine により管理）
  - data/stop_requested.flag   — 停止要求（run_execution / run_monitoring が監視）
  - data/kill.flag             — Kill Switch が書き込む停止フラグ（手動または自動）
- ログ
  - デフォルト: logs/<app_name>.log（日次ローテート、30日保持）
  - LOG_DIR 環境変数または setup_logging の引数で変更可能
- プロセス優先度
  - 起動スクリプトは set_process_priority("high") を呼び出します。権限不足や OS 非対応時は警告を出力してスキップします。

ディレクトリ構成（主要ファイル）
--------------------------------
（プロジェクト src/kabusys 配下の主要ファイルを抜粋）

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数/.env の自動ロードと Settings クラス
  - config_setup.py               — .env 対話式ウィザード
  - validate_config.py            — 設定検証 CLI
  - run_execution.py              — ExecutionEngine 起動スクリプト
  - run_monitoring.py             — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py            — ログ設定ユーティリティ
    - process_priority.py         — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py            — SQLite 永続化層
    - system_monitor.py
    - trade_monitor.py            — （取引異常検出ロジック）
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py            — （アラート送信ロジック）
  - execution/
    - execution_engine.py         — 実行エンジン本体
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

設計上の注意事項 / 運用上の注意
------------------------------
- 本リポジトリは本番発注（live）を想定したコードを含みます。KABUSYS_ENV=live の設定時は十分に注意してください。
- .env は機密情報（API トークンなど）を含むため Git 等へは絶対にコミットしないでください。
- OpenAI を用いる処理はネットワークエラーやレート制限を考慮したリトライ実装が入っていますが、API キーの管理とコスト管理に注意してください。
- DuckDB / SQLite への書き込みはファイル単位の排他等に注意して運用してください（バックアップ・パーミッション管理）。

補足 / よく使うコマンドサマリ
---------------------------
- .env 作成: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config [--strict]
- 実行開始: python -m kabusys.run_execution
- 監視開始: python -m kabusys.run_monitoring
- レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

ライセンス・貢献
----------------
- 本 README はコードベースの説明を目的としています。ライセンスやコントリビュートポリシーはリポジトリルートの LICENSE / CONTRIBUTING を参照してください（ない場合はプロジェクトオーナーに確認してください）。

問題報告・改善提案
-----------------
- 使い方や動作に疑問がある場合は、issue を立ててください。小さな修正やドキュメント改善は歓迎します。

以上。必要であれば README に含める具体的な .env.example の全文や、各コンポーネント（ExecutionEngine / MonitoringEngine / RiskManager）のより詳細な動作フロー図を追加できます。どのレベルの詳細を追加しますか？