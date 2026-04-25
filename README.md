# KabuSys — 日本株自動売買システム（README）

このドキュメントは、リポジトリ内のコードベース（src/kabusys 配下）を対象とした README.md です。プロジェクトの概要、機能、セットアップ手順、主要な使い方、ディレクトリ構成を日本語でまとめています。

---

概要
- KabuSys は日本株向けの自動売買フレームワークです。  
  主な役割はシグナル生成 → ポートフォリオ構築 → 発注（ExecutionEngine） → 監視（Monitoring） → レポーティング／リサーチ です。
- モジュール設計により、Paper Trading（ペーパートレード）と Live（実取引）を切り替えて動作させられます。  
  Paper Trading 時は MockBrokerClient を使用し、本番 DB と分離して動作します。

主な特徴（機能一覧）
- ExecutionEngine：注文発行・注文管理・リスク管理・再整合（reconciler）を行う実行エンジン
- Monitoring：システム稼働・発注ログ・リスク（ドローダウン・ポジション上限）をポーリング監視、Kill Switch による強制停止
- Portfolio 枠組み：候補選定、重み付け（等配分・スコア配分）、ポジションサイジング、セクター上限・レジーム調整
- Research：DuckDB を用いたファクター計算（モメンタム、ボラティリティ、バリュー）および特徴量解析ユーティリティ
- AI モジュール：OpenAI を用いたニュースセンチメント（news_nlp）、市場レジーム判定（regime_detector）
- ユーティリティ：設定自動読み込み（.env）、対話式設定ウィザード、設定検証 CLI、ロギング設定、プロセス優先度設定
- ツール：Paper Trading の検証レポート生成スクリプト等
- 永続化：SQLite（監視用）および DuckDB（分析用）

セットアップ手順（ローカル開発向け）
1. リポジトリをクローンし、Python 環境（推奨: venv）を用意する
   - python3 -m venv .venv
   - source .venv/bin/activate

2. 依存パッケージをインストールする
   - requirements.txt 等が存在すればそれに従う（本リポジトリには明示されていないため、必要に応じて以下をインストール）
     - pip install duckdb psutil openai
     - （任意）PyYAML（config/*.yaml の検証時に必要）：pip install pyyaml

3. .env を作成する（対話式ウィザード推奨）
   - python -m kabusys.config_setup
   - ウィザードで J-Quants / kabuステーション / DB パス / KABUSYS_ENV などを入力
   - 注意: .env は絶対に Git にコミットしないこと

4. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit(1)）になります

5. データディレクトリ等の作成
   - デフォルトでは以下のようなファイル・ディレクトリを使用します。必要に応じて作成してください。
     - data/（SQLite / PID / フラグファイルなど）
     - logs/（ログファイル）

主要環境変数（デフォルト含む）
- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API リフレッシュトークン
  - KABU_API_PASSWORD — kabuステーション API パスワード
- 実行環境選択
  - KABUSYS_ENV — development | paper_trading | live（デフォルト: development）
    - paper_trading: MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に書き込み
    - live: 本番運用モード（実際に発注）
- DB パス
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（paper_trading 用データベース、デフォルト: data/paper_trading.db）
- ロギング
  - LOG_LEVEL（デフォルト: INFO）
  - LOG_DIR（デフォルト: logs/）
- AI
  - OPENAI_API_KEY — OpenAI 呼び出しに使用（news_nlp / regime_detector）
- Monitoring 関連
  - MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）
  - KILL_FLAG_CLEAR_ON_START — 実行時に kill.flag を自動クリアするか（開発用、デフォルト 0）
  - KILL_FLAG_PATH（デフォルト: data/kill.flag）
- その他
  - PID_FILE_PATH（デフォルト: data/execution.pid）
  - PAPER_FILL_MODE（paper_trading の約定モード: instant | partial | never | reject）

使い方（主要コマンド）
- 環境ウィザード（.env の作成）
  - python -m kabusys.config_setup

- 設定検証（起動前に実行推奨）
  - python -m kabusys.validate_config
  - 厳格モード（警告も失敗扱い）: python -m kabusys.validate_config --strict

- ExecutionEngine（発注エンジン）起動
  - python -m kabusys.run_execution
  - 振る舞い:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し paper_trading 専用 DB に記録（本番 DB と分離）
    - プロセス優先度を高に設定（utils.process_priority）
    - 停止: data/stop_requested.flag を作成すると起動中のループが停止

- Monitoring（監視ループ）起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔は MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60 秒）
  - Monitoring は環境にかかわらず本番 sqlite_path を使用して監視ログを記録
  - 停止: data/stop_requested.flag の検出でループを終了

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

ログ / トラブルシューティング
- ログはデフォルト logs/<app_name>.log に日次ローテーションで出力されます（logs/ 配下）
- ログレベルは .env の LOG_LEVEL または setup_logging の引数で制御
- 実行停止するには data/stop_requested.flag を作成する（run_execution/run_monitoring が検知）
- Kill Switch（kill.flag）:
  - RiskMonitor + KillSwitch によりドローダウンやポジション上限超過時に data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送る設計
  - 本番運用時は KILL_FLAG_CLEAR_ON_START=0 を推奨

ディレクトリ構成（主要ファイル／モジュール）
- src/kabusys/
  - __init__.py (パッケージ情報)
  - config.py （.env 自動読み込み、Settings クラス）
  - config_setup.py （対話式 .env ウィザード）
  - validate_config.py （設定検証 CLI）
  - run_execution.py （ExecutionEngine 起動スクリプト）
  - run_monitoring.py （SystemMonitor ポーリングループ起動スクリプト）
  - tools/
    - paper_verification_report.py （Paper Trading 検証レポート）
  - ai/
    - news_nlp.py （ニュースセンチメント取得・ai_scores 書き込み）
    - regime_detector.py （市場レジーム判定、market_regime 書き込み）
  - portfolio/
    - portfolio_builder.py （候補選定、スコア/等配分）
    - position_sizing.py （株数計算、上限・集約キャップ）
    - risk_adjustment.py （セクター上限、レジーム乗数）
    - __init__.py
  - research/
    - factor_research.py （モメンタム / ボラティリティ / バリュー計算）
    - feature_exploration.py （将来リターン、IC、統計サマリー）
    - __init__.py
  - monitoring/
    - monitoring_db.py （SQLite テーブル定義・永続化 API）
    - system_monitor.py （CPU/メモリ/ディスク/プロセス/データ鮮度監視）
    - trade_monitor.py （trade_logs の監視）※ファイルは存在（本 README では主要な役割を説明）
    - risk_monitor.py （ドローダウン / ポジション上限監視）
    - monitoring_engine.py （複数 Monitor を束ねてポーリング）
    - kill_switch.py （kill.flag の作成 / 管理）
    - alert_manager.py （LINE などへの通知管理）※実装参照
  - execution/
    - execution_engine.py （ExecutionEngine の本体）
    - broker_factory.py （ブローカークライアントの生成、MockBroker の切替）
    - order_manager.py, order_repository.py, reconciler.py, risk_manager.py など
  - utils/
    - logging_setup.py （共通ログ設定）
    - process_priority.py （優先度 / CPU affinity 設定）
    - __init__.py
  - portfolio/, ai/, research/, monitoring/ etc. （上記参照）

注意事項 / 運用上のポイント
- .env は機密情報を含むため絶対にリポジトリにコミットしないでください。
- 本番環境（KABUSYS_ENV=live）では LINE 通知設定（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）を必ず確認してください。validate_config は本番向けのガードを含んでいます。
- Paper Trading では実際の発注は発生しませんが、発注ロジックの挙動検証に用いる DB（PAPER_TRADING_SQLITE_PATH）は本番 DB と分離して運用してください。
- AI（OpenAI）を利用する機能は API 呼び出しに失敗した場合でもフェイルセーフで継続する設計ですが、API キーの設定とコスト管理に注意してください。

開発／テストのヒント
- 個別モジュール（portfolio 関数群、research の関数）は純粋関数として設計され、外部副作用を持たないものが多いためユニットテストがしやすいです。
- Monitoring の run_once / MonitoringEngine.run_once を使うと一回限りのチェック実行が可能で、ユニットテストや手動検証に便利です。
- OpenAI への実際の API 呼び出しは、テスト時に _call_openai_api をモック（unittest.mock.patch）して差し替える設計が用意されています。

参考（よく使うコマンド例）
- .env 作成（対話式）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
- ExecutionEngine 起動
  - python -m kabusys.run_execution
- Monitoring 起動
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Paper Trading レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

この README はコードベースの主要ポイントをまとめたものです。細かな挙動や設定項目は各モジュール（config.py、monitoring/、execution/、ai/、portfolio/、research/）の docstring や関数のコメントを参照してください。必要であれば、特定モジュール向けの詳細ドキュメント（使用例、API 仕様、テストガイド）を別途作成します。