KabuSys
=======

日本株向けの自動売買 / 研究プラットフォーム（モジュール群）のコードベース向け README（日本語）。
本ドキュメントはプロジェクト全体の概要、機能、セットアップ手順、基本的な使い方、主要ファイル・ディレクトリ構成を説明します。

プロジェクト概要
--------------
KabuSys は日本株の自動売買エンジン・監視・ポートフォリオ構築・研究ツール群からなるモジュール化されたシステムです。  
主な目的は以下です。

- 日次 / リアルタイムのトレード実行（ExecutionEngine）
- システム稼働監視・アラート・Kill Switch（Monitoring）
- ポートフォリオ構築・ポジションサイズ算出（Portfolio）
- ファクター計算・特徴量探索（Research）
- ニュースを用いた NLP スコアリング・市場レジーム判定（AI）
- ペーパートレード検証レポート生成ツール（tools）

モード
- KABUSYS_ENV により挙動が変わる:
  - development: 開発用（発注なし等）
  - paper_trading: ペーパートレード（MockBroker を使用し、本番 DB と分離）
  - live: 本番（実際の発注を伴う想定）

主な機能一覧
----------------
- Execution
  - ExecutionEngine（発注管理、OrderManager、RiskManager、Reconciler 等）
  - paper_trading モードでは MockBrokerClient を使用し data/paper_trading.db に記録
- Monitoring
  - SystemMonitor: CPU / メモリ / ディスク / データ鮮度 / Execution プロセス生存監視
  - TradeMonitor / RiskMonitor: 滞留注文・約定異常・ドローダウン・ポジション上限監視
  - MonitoringEngine: 定期ポーリング・アラート発行・Kill Switch 制御
  - MonitoringDB: SQLite を用いた監視ログ格納（system_status, trade_logs, positions, risk_logs, dashboard）
- Portfolio
  - 候補選定、等分配・スコア加重、リスクベースのポジションサイズ計算
  - セクターキャップ適用、レジーム乗数適用
- Research
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン・IC 計算・統計サマリー
  - DuckDB を使った高速集計
- AI
  - news_nlp: OpenAI（gpt-4o-mini）でニュースセンチメントを算出し ai_scores に書き込み
  - regime_detector: ETF MA とマクロニュースの LLM スコアを組合せて市場レジーム判定・書き込み
- ユーティリティ
  - 環境設定ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading 検証レポート生成（tools/paper_verification_report）
  - 統一ロギング設定・プロセス優先度調整ユーティリティ等

セットアップ手順
----------------

1. Python 環境
   - 推奨: Python 3.9+（コードは型注釈等を使用）
2. 必要パッケージ（主要）
   - duckdb
   - psutil
   - openai
   - （任意）PyYAML（config/*.yaml の解析に使用）
   - その他：標準ライブラリ外のパッケージは requirements.txt が無ければ pip で個別インストール
     例:
       pip install duckdb psutil openai PyYAML
3. ソース取得
   - リポジトリをクローンし、プロジェクトルートを確認
4. .env の作成（推奨）
   - 対話式ウィザードを使う:
       python -m kabusys.config_setup
     ウィザードで J-Quants トークン、Kabu API パスワード、データベースパス、KABUSYS_ENV 等を設定します。
   - 生成後、必須環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）が設定されていることを確認
5. 設定の検証
   - validate_config を実行して設定不備を検出:
       python -m kabusys.validate_config
   - 警告も致命扱いにする場合:
       python -m kabusys.validate_config --strict
6. データディレクトリの作成
   - デフォルトで data/ や logs/ を使用します。自動作成されますが、権限等を事前に確認しておくと良いです。
7. OpenAI API キー（AI 機能を使う場合）
   - 環境変数 OPENAI_API_KEY を設定してください（score_news / score_regime で必須）。
8. DuckDB / SQLite
   - デフォルトパス:
     - DuckDB: data/kabusys.duckdb
     - Monitoring SQLite: data/monitoring.db
     - Paper trading SQLite: data/paper_trading.db（paper_trading モード）
   - 必要に応じて環境変数で上書き可能（DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH）

使い方（よく使うコマンド）
-------------------------

- 環境設定ウィザード（.env 作成）
    python -m kabusys.config_setup

- 設定検証
    python -m kabusys.validate_config
    python -m kabusys.validate_config --strict

- 監視ループ起動（Monitoring）
  - デフォルトは MONITOR_POLL_INTERVAL=60 秒でループ
    環境変数で変更可能（例: 30秒）:
      MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視は production sqlite_path（Settings.sqlite_path）を常に使用します
  - 停止はプロジェクトルート/data/stop_requested.flag を作成するか Ctrl+C

- 実行エンジン起動（Execution）
    python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBroker を使用し PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録されます
  - 実行中に停止させるにはプロジェクトルート/data/stop_requested.flag を作成します
  - エンジンの PID ファイルは data/execution.pid（Settings.pid_file_path）に保存されます

- Paper Trading 検証レポート（コマンドライン）
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスを指定する場合:
    python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI スコアリング / レジーム判定（プログラム呼び出し）
  - news_nlp.score_news(conn, target_date, api_key=None)
  - regime_detector.score_regime(conn, target_date, api_key=None)
  - OpenAI API キーは api_key 引数か環境変数 OPENAI_API_KEY を使用

ログ・監視について
-----------------
- ログ設定は kabusys.utils.logging_setup.setup_logging を経由して統一的に行われます。
- デフォルトのログディレクトリ: logs/
- 環境変数 LOG_LEVEL（既定: INFO）でログ出力レベルを制御
- Monitoring は monitoring DB（SQLite）に監視ログを永続化します（init_monitoring_db がテーブルを作成）

重要な環境変数（主なもの）
-------------------------
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- OPENAI_API_KEY: AI 機能利用時に必要
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用, デフォルト: data/paper_trading.db）
- LOG_LEVEL（デフォルト: INFO）
- MONITOR_POLL_INTERVAL（run_monitoring でポーリング間隔を上書き、秒単位、デフォルト 60）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START（Kill Switch 関連）

Kill Switch（安全停止）について
-------------------------------
- KillSwitch は監視結果に応じて data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送ります。
- KillSwitch の書き込み条件はドローダウン超過・ポジション上限超過など。
- Execution 起動時に KILL_FLAG_CLEAR_ON_START=1 が設定されていると自動クリアする設定が可能（※本番では 0 推奨）。

ディレクトリ構成（主要ファイル）
-------------------------------

src/kabusys/
- __init__.py
- config.py
  - 環境変数読み込み・Settings クラス（.env 自動ロード機能含む）
- config_setup.py
  - .env 対話式生成ウィザード
- validate_config.py
  - 起動前設定検証 CLI
- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト
- run_execution.py
  - ExecutionEngine の起動スクリプト（paper_trading は MockBroker）
- utils/
  - logging_setup.py: 一元的なログ設定
  - process_priority.py: プロセス優先度 / CPU affinity 設定
- monitoring/
  - monitoring_db.py: SQLite スキーマ初期化・永続化層
  - system_monitor.py, trade_monitor.py, risk_monitor.py, monitoring_engine.py, kill_switch.py, alert_manager.py
- execution/
  - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, broker_factory.py, risk_manager.py
- portfolio/
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py
- research/
  - factor_research.py, feature_exploration.py
- data/
  - pipeline.py, stats.py 等（DuckDB 関連ユーティリティ）
- ai/
  - news_nlp.py, regime_detector.py
- tools/
  - paper_verification_report.py

（上記は主要モジュールの抜粋です。プロジェクトにはさらに詳細な実装ファイルがあります。）

補足・運用上の注意
-----------------
- 本番運用（KABUSYS_ENV=live）では設定を厳重に確認してください（validate_config の警告を要確認）。
- .env は機密情報を含むため絶対に Git にコミットしないでください。
- AI 機能は OpenAI API に依存します。API 呼び出しはレート制限やエラーを考慮したリトライ実装を行っていますが、API キーとコスト管理を行ってください。
- Paper trading は本番 DB と分離して動作するよう設計されています。ペーパートレードの記録・分析は data/paper_trading.db を使用します。
- DuckDB / SQLite のバージョン互換性に注意（executemany の空リスト等に対応した実装上の注意あり）。

開発・拡張案内
----------------
- 研究用ファクター追加、ポートフォリオ最適化手法の導入、AI プロンプト改善など拡張ポイント多数
- BrokerClientFactory を拡張して別ブローカー連携を追加可能
- ロギングやメトリクス収集を Prometheus / Grafana に接続する拡張も想定可能

問い合わせ / 貢献
-----------------
- この README はソースコード（src/kabusys 以下）から要点を抜粋して作成しています。実装の詳細は各モジュールの docstring / コメントを参照してください。  
- 変更やバグ修正を行う場合はユニットテスト（存在する場合）と validate_config を使って整合性を確認してください。

以上。プロジェクトを始める際に不明点があれば、どの機能について知りたいかを教えてください。必要に応じて起動スクリプトの実行例や .env のテンプレート例も作成します。