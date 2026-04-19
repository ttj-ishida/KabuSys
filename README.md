# KabuSys

日本株自動売買システムのコードベース README（日本語）

短い概要
- KabuSys は日本株の自動売買・研究・モニタリングを行うためのモジュール群です。
- 主な機能：実行エンジン（ExecutionEngine）、監視モニタ（Monitoring）、ポートフォリオ構築、ファクター計算／リサーチ、AI を使ったニュースセンチメント評価などを提供します。
- 本リポジトリはライブラリ的にモジュールをまとめており、起動スクリプトと CLI ツールを通じて運用できます。

機能一覧
- Execution
  - 実際の発注を行う ExecutionEngine（KABU API クライアント経由）
  - KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用して本番 DB と分離（data/paper_trading.db）
  - リスク管理（RiskManager）、オーダー管理、リコンシリエーション等のコンポーネントを備える
- Monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor を組み合わせた監視エンジン（MonitoringEngine）
  - SQLite に監視ログを保存（monitoring_db.py）
  - Kill Switch（しきい値超過時に data/kill.flag へ書き込みして ExecutionEngine を停止）
  - run_monitoring.py でポーリングループ起動（MONITOR_POLL_INTERVAL で間隔変更可）
- Portfolio
  - 候補選定 / 重み計算（等金額・スコア加重）
  - セクターキャップ適用、レジーム乗数、ポジションサイズ計算（単元株丸め・集計キャップ）
- Research
  - DuckDB を利用したファクター計算（モメンタム/ボラティリティ/バリュー 等）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリ
- AI
  - ニュース NLP（OpenAI）による銘柄センチメント評価（news_nlp）
  - マクロニュースと ETF（1321）の MA200 を組み合わせた市場レジーム判定（regime_detector）
  - OpenAI API 呼び出しはリトライ・検証ロジックあり（フェイルセーフ設計）
- ツール
  - .env 対話式ウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py）
  - Paper Trading 検証レポート生成ツール（tools/paper_verification_report.py）
- ユーティリティ
  - 統一的なログ設定（utils/logging_setup.py）
  - プロセス優先度 / CPU affinity 設定ユーティリティ（utils/process_priority.py）
  - 設定読み込み / Settings（config.py）

前提（Prerequisites）
- Python 3.10 以上（型アノテーションに PEP 604 の union 演算子 (|) 等を使用）
- SQLite（Python 標準ライブラリに含む）
- 主要外部パッケージ（例）
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証でオプション）
- ネットワークアクセス（kabuステーション API / OpenAI API を利用する場合）

インストール（簡易）
1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
2. 必要パッケージをインストール
   - pip install duckdb psutil openai pyyaml
   - （実運用向けに requirements.txt があれば pip install -r requirements.txt を推奨）

環境変数と .env
- .env を作成するには対話式ウィザードを利用できます：
  - python -m kabusys.config_setup
  - このウィザードは .env を生成し、`.env` は絶対に Git にコミットしない旨が注釈されています。
- 重要な環境変数（抜粋）
  - JQUANTS_REFRESH_TOKEN（必須）
  - KABU_API_PASSWORD（必須）
  - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
  - OPENAI_API_KEY（AI 機能利用時に必要）
  - KABUSYS_ENV（development / paper_trading / live。デフォルト: development）
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（paper_trading 用デフォルト: data/paper_trading.db）
  - LOG_LEVEL（デフォルト: INFO）
  - KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするフラグ。デフォルト: 0）
  - MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔秒。デフォルト: 60）
- .env の自動読み込み
  - config.py はプロジェクトルート（.git または pyproject.toml が存在する場所）を探索して .env/.env.local を自動で読み込みます。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込みを無効化できます。

設定検証
- 生成後に設定を検証する:
  - python -m kabusys.validate_config
  - 厳密モード（警告を FAIL 扱い）: python -m kabusys.validate_config --strict
  - validate_config は必須環境変数や config/*.yaml の存在／基本パースをチェック（PyYAML がない場合は YAML チェックをスキップして警告）

使い方（起動例）
- ExecutionEngine を起動（通常はサーバでデーモン起動）
  - python -m kabusys.run_execution
  - 特記事項:
    - プロセス開始時に優先度を "high" に設定します（utils.process_priority）。
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient が使われ、DB は data/paper_trading.db に分離されます。
    - 実行中に data/stop_requested.flag が作成されると安全に停止します。
    - kill.flag（Settings.kill_flag_path に対応）によって外部から停止シグナルを送る運用設計があります（KillSwitch）。
- Monitoring を起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60）
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用して監視データを永続化します
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション: --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
  - 簡易的に稼働率／注文成功率／レイテンシ等をまとめたレポートを stdout に出力します

停止 / Kill Switch
- ExecutionEngine の停止は以下のいずれかで行います:
  - Monitoring の KillSwitch による data/kill.flag 書き込み（条件は RiskMonitor 等で判定）
  - 管理者が手動で data/stop_requested.flag を作成すると run_execution/run_monitoring が検知して終了します
- kill.flag は起動時に自動クリア（KILL_FLAG_CLEAR_ON_START=1 を設定している場合のみ）されることがありますが、本番では 0 を推奨します

ログ
- ログは utils/logging_setup.setup_logging により標準出力（stdout）と日次ローテートファイルに出力されます
- デフォルトログディレクトリ: logs/
- アプリ名ごとにログファイルが作成されます（例: logs/execution.log, logs/monitoring.log）
- LOG_DIR 環境変数でログ保存先を変更可能

主要モジュールの説明（簡略）
- kabusys.config
  - Settings クラスにより環境変数をラップ。必須変数は _require() によりバリデーション。
  - 自動 .env ロード機能あり
- kabusys.execution
  - ExecutionEngine / OrderManager / RiskManager / Reconciler など（発注周りの実装）
  - BrokerClientFactory により環境に応じて本番／モッククライアントを生成
- kabusys.monitoring
  - monitor 用 DB 層 monitoring_db.py（シンプルな CRUD）
  - SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch / MonitoringEngine
- kabusys.portfolio
  - portfolio_builder.py / position_sizing.py / risk_adjustment.py（純粋関数群）
- kabusys.research
  - factor_research.py（モメンタム等）、feature_exploration.py（IC 等）
  - DuckDB を利用して時系列系の処理を SQL と Python で実行
- kabusys.ai
  - news_nlp.py（ニュースセンチメント集約 → OpenAI でスコアリング）
  - regime_detector.py（MA200 + マクロセンチメントで市場レジーム判定）
  - OpenAI 呼び出しは堅牢性（リトライ／検証）を考慮して実装
- kabusys.tools
  - paper_verification_report.py（ペーパートレードの検証レポート）

ディレクトリ構成（抜粋）
- src/
  - kabusys/
    - __init__.py
    - config.py
    - config_setup.py
    - validate_config.py
    - run_execution.py
    - run_monitoring.py
    - execution/...
    - monitoring/
      - monitoring_db.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - monitoring_engine.py
      - kill_switch.py
      - alert_manager.py
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
    - tools/
      - paper_verification_report.py
    - utils/
      - logging_setup.py
      - process_priority.py
- data/  （実行時に作成されることが多い）
  - monitoring.db（デフォルト SQLite）
  - paper_trading.db（paper_trading 用）
  - kabusys.duckdb（DuckDB ファイル）
  - kill.flag / stop_requested.flag / execution.pid などの制御ファイル

運用上の注意
- .env を絶対にリポジトリにコミットしないでください（README と .env.example のみを共有）
- 本番環境（KABUSYS_ENV=live）では LINE 通知や kill flag 設定等を慎重に確認してください（validate_config に本番時の警告チェックあり）
- OpenAI や外部 API を利用する処理はネットワークエラーやレート制限を考慮した設計になっていますが、API キーや料金管理は運用側で行ってください
- Monitoring は production SQLite を直接参照するため、監視が監視対象データに影響を与えないよう設計されています（ただし DB ファイルのバックアップ等は運用で確保してください）

開発者向けメモ
- duckdb 接続を多用するため、ローカルでの大きな DB ファイルは I/O を消費します。実験時は小さいサンプル DB を用意してください
- AI 関連機能は OpenAI の SDK（openai）に依存します。テスト時は _call_openai_api をモックする設計になっています
- monitoring_db.init_monitoring_db は冪等的にテーブルと簡易マイグレーションを実施します

よく使うコマンドまとめ
- .env の対話式作成:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- 実行エンジン起動:
  - python -m kabusys.run_execution
- 監視ループ起動:
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

以上が README の概要です。必要であれば各モジュールごとの詳細使用例や API 仕様（関数引数・戻り値）を補足したドキュメントを作成できます。どの部分を詳細化するか教えてください。