KabuSys — 日本株自動売買システム（簡易 README）  
（以下はこのリポジトリの主要なコンポーネントと使い方を簡潔にまとめた日本語 README です）

プロジェクト概要
- KabuSys は日本株の自動売買・研究・監視を目的とした Python パッケージ群です。
- ファクター計算、ポートフォリオ構築、ポジションサイジング、監視・アラート、ペーパートレード検証、LLM を使ったニュースセンチメントやレジーム判定など複数の機能をモジュール化しています。
- 設定は .env ファイルまたは環境変数で行い、DuckDB / SQLite を内部データや監視ログに使用します。

主な機能一覧
- 環境設定ウィザード（config_setup）: .env の対話的作成/更新を支援
- 設定検証 CLI（validate_config）: .env と config/*.yaml の事前検証
- 実行エンジン起動スクリプト（run_execution）:
  - KABUSYS_ENV により paper_trading（MockBroker）/live を切替
  - Paper Trading 時は data/paper_trading.db に完全分離して記録
  - プロセス優先度設定、PID ファイル管理、停止フラグ監視
- 監視ループ起動スクリプト（run_monitoring）:
  - SystemMonitor 等をポーリングして監視ログを SQLite に保存
  - MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60s）
  - 監視は常に本番用 sqlite_path を使用（KABUSYS_ENV に依存しない）
- 監視サブシステム:
  - SystemMonitor: CPU/メモリ/ディスク、プロセス生存、データ鮮度の監視
  - TradeMonitor / RiskMonitor / KillSwitch / AlertManager（監視統合）
  - MonitoringDB: system_status / trade_logs / positions / risk_logs / dashboard の永続化
- ポートフォリオ構築（portfolio）:
  - 候補選定、等金額・スコア加重、セクター制限、レジーム乗数、ポジションサイズ決定
- 研究（research）:
  - ファクター計算（モメンタム、ボラティリティ、バリュー等）
  - 将来リターン計算、IC 計算、統計サマリー
- AI 関連（ai）:
  - news_nlp: OpenAI を用いたニュースセンチメント集約と ai_scores への書き込み
  - regime_detector: ETF 指標 + マクロニュースで日次レジーム判定
- ツール:
  - paper_verification_report: ペーパートレードの検証レポート出力（期間指定可）

前提 / 必須環境
- Python >= 3.10（| 型注釈等を使用しているため）
- 推奨 / 必須ライブラリ（最小限）:
  - duckdb
  - psutil
  - openai（AI 機能を利用する場合）
  - PyYAML（validate_config で YAML 検証を行う場合、任意）
- インストール例:
  - pip install duckdb psutil openai pyyaml

セットアップ手順
1. リポジトリをクローンしてワークディレクトリをプロジェクトルートにする。
2. 仮想環境の作成（推奨）:
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 必要パッケージをインストール:
   - pip install duckdb psutil openai pyyaml
4. .env の作成:
   - 対話式ウィザードを使用（推奨）:
     - python -m kabusys.config_setup
   - もしくは手動で .env を作成。必須 env:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
   - .env の主な設定（デフォルトを示す）:
     - KABUSYS_ENV=development|paper_trading|live  （デフォルト: development）
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - LOG_LEVEL=INFO
     - OPENAI_API_KEY（AI 機能使用時に必要）
5. 設定検証（任意だが推奨）:
   - python -m kabusys.validate_config
   - 警告を FAIL 扱いにする場合: python -m kabusys.validate_config --strict
6. データディレクトリ/ログディレクトリの確認:
   - デフォルトで data/ と logs/ を使用します。必要に応じて作成されます。

使い方（主要なコマンド）
- 実行エンジン（ExecutionEngine）起動:
  - python -m kabusys.run_execution
  - 特記事項:
    - KABUSYS_ENV=paper_trading の場合は MockBroker が使用され、data/paper_trading.db に書き込まれます。
    - 起動時に data/stop_requested.flag が存在すると起動を中止します。
    - 実行中に stop を要求するには data/stop_requested.flag を作成することでループを止められます。
    - PID ファイル: デフォルト data/execution.pid（設定で変更可能）
- 監視ループ起動:
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を指定可能（デフォルト 60）。
  - 監視は settings.sqlite_path（デフォルト data/monitoring.db）を使用します（KABUSYS_ENV にかかわらず）。
  - 監視を停止するには data/stop_requested.flag を作成してください。
- .env の作成/更新（対話式）:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
- ペーパートレード検証レポート:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - --from YYYY-MM-DD --to YYYY-MM-DD
  - DB 指定:
    - --db PATH  または 環境変数 PAPER_TRADING_SQLITE_PATH を使用

重要な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live（デフォルト development）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- OPENAI_API_KEY: OpenAI を使う機能で必要
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング秒数（デフォルト 60）
- LOG_DIR / LOG_LEVEL: ログ設定に影響

停止・キルスイッチについて
- 実行エンジンはファイルベースのフラグで停止を受け付けます:
  - data/stop_requested.flag: ループを安全に停止させるフラグ（run_execution, run_monitoring がチェック）
  - data/kill.flag: KillSwitch が書き込むことで ExecutionEngine に停止を促す（監視 -> 書込み）
- KillSwitch は監視結果に基づき条件を満たした場合に kill.flag を書き込みます（例: ドローダウン閾値超過 等）。
- KILL_FLAG_CLEAR_ON_START が 1 の場合、起動時に kill.flag を自動でクリアします（本番では 0 推奨）。

ログ
- 共通ログ設定ユーティリティ: kabusys.utils.logging_setup.setup_logging
  - stdout（StreamHandler）と日次ローテートファイル（logs/<app>.log）を設定
  - デフォルトログディレクトリ: logs/
  - ログファイルは日次ローテーションで 30 日分保持

主要ディレクトリ構成（src 配下）
- src/kabusys/
  - __init__.py — パッケージ定義
  - config.py — 環境変数・設定の読み込み/検証ユーティリティ（Settings クラス）
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 起動前設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成スクリプト
  - ai/
    - news_nlp.py — ニュースを LLM でスコアリングして ai_scores に書き込む
    - regime_detector.py — レジーム判定（ETF MA + マクロニュース）
  - monitoring/
    - monitoring_db.py — 監視ログの永続化クラス（MonitoringDB）
    - system_monitor.py — システム状態・データ鮮度監視
    - trade_monitor.py, risk_monitor.py, kill_switch.py, monitoring_engine.py, alert_manager.py など（監視統合）
  - portfolio/
    - portfolio_builder.py, position_sizing.py, risk_adjustment.py — ポートフォリオ構築ロジック
  - research/
    - factor_research.py, feature_exploration.py — ファクター / 研究用ユーティリティ
  - utils/
    - logging_setup.py — 共通ログ初期化
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ
  - その他（execution 関連モジュール、データパイプライン等）

コード利用上の注意 / 動作ポリシー
- 日次の判定や AI 呼び出しは明示的な target_date を受け取り、内部で datetime.today() を安易に参照しない設計（ルックアヘッドバイアスを防止）。
- AI（OpenAI）呼び出しはリトライやバリデーションを含む防御的実装。API キーは OPENAI_API_KEY で供給。
- Paper Trading は本番 DB と分離（PAPER_TRADING_SQLITE_PATH）。ペーパートレード中は MockBrokerClient を使い、実際の発注は行いません。
- 監視（monitoring）系は環境にかかわらず本番 sqlite_path を使う点に注意（run_monitoring の挙動）。

サンプル .env（最小）
# .env.example に基づく最小例（実運用では秘密情報は必ず適切に管理する）
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
# OPENAI_API_KEY=sk-...

よくある運用フロー（例）
1. .env を作成（python -m kabusys.config_setup）
2. 設定検証（python -m kabusys.validate_config）
3. データ投入 / DuckDB 初期化（外部スクリプトにより prices_daily, raw_financials 等を用意）
4. 監視プロセス起動（python -m kabusys.run_monitoring）
5. 実行エンジン起動（python -m kabusys.run_execution）
6. 必要に応じて paper_verification_report で結果確認

追加情報・開発者向けメモ
- YAML 検証は PyYAML インストール時のみ有効（validate_config）
- logging_setup は既存ハンドラをクリアしてから設定するため、複数回呼んでも二重出力を避ける
- process_priority はプラットフォームに応じて psutil を使い適切に設定し、権限不足時は警告でスキップします
- DB マイグレーション（監視 DB の列追加等）は monitoring_db.init_monitoring_db 内で冪等的に処理されます

問題報告 / 貢献
- バグや改善要望は Issue を立ててください。テストやドキュメント改善の PR は歓迎します。

以上。プロジェクト特有の詳細（ExecutionEngine の内部、OrderManager, BrokerClient 等）は該当モジュールの docstring やコードコメントを参照してください。必要であれば各サブモジュール向けの詳細 README を追加で生成します。