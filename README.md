# KabuSys — 日本株自動売買システム（README）

概要
- KabuSys は日本株の自動売買・検証・モニタリングを目的とした Python ベースのプロジェクトです。
- 株価データ分析（DuckDB）、注文実行（kabuステーション またはモック）、監視（SQLite）、AI によるニュース解析などのコンポーネントを備えます。
- 本リポジトリはライブラリ・CLI スクリプト群を提供し、ローカル開発、ペーパートレード、本番（live）を切り替えて実行できます。

主な機能
- 環境設定ウィザード（.env の対話的生成）: kabusys.config_setup
- 設定検証 CLI（.env / config/*.yaml の事前チェック）: kabusys.validate_config
- ExecutionEngine 起動スクリプト（実発注 / ペーパートレード切替）: run_execution.py
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、データは data/paper_trading.db に書き込むことで本番 DB と分離
- Monitoring（監視）: SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine、定期ポーリングスクリプト run_monitoring.py
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）
  - 監視用 DB は monitoring.db（Settings.sqlite_path）に永続化
- AI モジュール
  - ニュース NLP（OpenAI）：raw_news を LLM で評価して ai_scores へ保存（kabusys.ai.news_nlp）
  - 市場レジーム判定（regime_detector）：MA とマクロニュースの LLM スコアを合成
  - OpenAI API（OPENAI_API_KEY 必須）を利用するため、適切な API キーの設定が必要
- 研究・リサーチ機能（DuckDB 経由でファクター計算・将来リターン・IC など）
- ポートフォリオ構築ユーティリティ（候補選定、配分重み、ポジションサイズ、セクター制限等）
- ユーティリティ: プロセス優先度設定、CPU affinity 設定 等

セットアップ手順（ローカル開発向け）
1. Python 環境を準備
   - Python 3.10+ を推奨（プロジェクトの pyproject.toml / packaging に準拠）
   - 仮想環境を作成して有効化
     - python -m venv .venv
     - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 依存パッケージをインストール
   - 必要な主要パッケージ（例）:
     - duckdb
     - psutil
     - openai
     - pyyaml（設定検証で YAML をパースしたい場合）
   - 例:
     - pip install duckdb psutil openai pyyaml

3. .env を用意
   - 対話式ウィザードで生成するのが簡単:
     - python -m kabusys.config_setup
   - 必須環境変数（最低限設定が必要なもの）
     - JQUANTS_REFRESH_TOKEN（J-Quants API 用）
     - KABU_API_PASSWORD（kabuステーション API 用）
     - OPENAI_API_KEY（AI モジュールを使う場合）
   - 主要な環境変数（代表例）
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH（DuckDB ファイル、デフォルト data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB、デフォルト data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（ペーパートレード専用 SQLite、デフォルト data/paper_trading.db）
     - LOG_LEVEL（INFO 等）
     - MONITOR_POLL_INTERVAL（監視ポーリング間隔 秒。run_monitoring で読み込む）
     - KILL_FLAG_CLEAR_ON_START（本番環境で自動クリアするか。デフォルト 0 推奨）

4. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 警告を厳格に扱う場合は --strict を付ける（警告があると exit(1)）

使い方（主な CLI / スクリプト）
- 設定ウィザード
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- 実行エンジン（ExecutionEngine）起動
  - python -m kabusys.run_execution
  - 動作モードは KABUSYS_ENV で切替（paper_trading は paper DB に書き込み）
  - エンジンはデーモンスレッドで run_session を実行、data/stop_requested.flag を検知すると停止
- 監視ループ起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL で間隔を上書き（秒）。例: export MONITOR_POLL_INTERVAL=30
  - 監視は常に本番の sqlite_path を参照する（環境に依らず監視 DB を使用）
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で SQLite ファイルを指定可能（デフォルトは data/paper_trading.db）
- AI モジュール（ライブラリ呼び出し）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - OpenAI API キーは引数で渡すか OPENAI_API_KEY 環境変数を使用

停止・Kill Switch
- 停止フラグ:
  - data/stop_requested.flag（run_execution/run_monitoring が参照している停止フラグ）
  - data/kill.flag（KillSwitch が書き込むファイル。ExecutionEngine 停止のために使用）
- KillSwitch 動作:
  - RiskMonitor が閾値超過（ドローダウン・ポジション上限等）を検出すると kill.flag を書き込み、その後 ExecutionEngine は停止される
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動クリアする（本番では推奨しない）

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py
    - Settings クラス（環境変数 / .env 自動ロード）
  - config_setup.py
    - .env を対話的に作成/更新するウィザード
  - validate_config.py
    - 起動前の設定検証 CLI
  - run_execution.py
    - ExecutionEngine 起動スクリプト（paper_trading 用分離処理含む）
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプト
  - utils/
    - process_priority.py
      - プロセス優先度、CPU affinity のユーティリティ（psutil 使用）
  - monitoring/
    - monitoring_db.py
      - SQLite による監視ログ・テーブル定義・操作クラス（MonitoringDB）
    - system_monitor.py
      - システム状態・データ鮮度監視（SystemMonitor）
    - trade_monitor.py
      - 注文滞留・約定異常の監視（TradeMonitor）
    - risk_monitor.py
      - ドローダウン・ポジション上限監視（RiskMonitor）
    - monitoring_engine.py
      - 各 Monitor を束ねるエンジン
    - kill_switch.py
      - kill.flag の書き込み・評価ロジック
    - alert_manager.py
      - （実装ファイル末尾まで含めず省略）
  - execution/         (注文実行関連のコンポーネント群: ExecutionEngine, BrokerFactory 等)
  - portfolio/
    - portfolio_builder.py
    - risk_adjustment.py
    - position_sizing.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - tools/
    - paper_verification_report.py
  - data/               （実行時に使用する SQLite / DuckDB ファイルを配置するディレクトリ）
    - monitoring.db (default)
    - kabusys.duckdb (default)
    - paper_trading.db (paper_trading モード用)

補足・注意点
- .env は絶対にリポジトリへコミットしないこと（シークレットを含む）。
- 本番（KABUSYS_ENV=live）では LINE 通知等の設定を十分に確認してください（validate_config の live ガード参照）。
- OpenAI を使うモジュールは API コスト・レート制限に注意。score_news / score_regime はリトライ・フェイルセーフの仕組みを持ちますが、運用時は API キーの使用量とコストを管理してください。
- ペーパートレードは本番 DB と分離されます。PAPER_TRADING_SQLITE_PATH を活用してください。
- psutil によるプロセス優先度設定や CPU affinity は権限に依存するため、失敗した場合は警告が出てスキップされます。

トラブルシューティングのヒント
- 設定検証でエラーが出る場合は .env.example（プロジェクトに存在する場合）や validate_config の出力を確認してください。
- DuckDB / SQLite のパスに対する親ディレクトリが存在しない場合、起動時に自動作成されることがありますが、権限エラー等がある場合は手動で作成してください。
- run_execution / run_monitoring がすぐに終了する場合は data/stop_requested.flag や data/kill.flag の存在を確認してください。

ライセンス・貢献
- （ここにはプロジェクト固有のライセンス・貢献ガイドラインを追記してください）

以上。必要に応じて README に追記したい点（例: 実行ログの見方、監視アラートの設定方法、詳細な API 使用例 等）があれば指示してください。