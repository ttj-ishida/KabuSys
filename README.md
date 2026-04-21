# KabuSys — 日本株自動売買システム（README）

このドキュメントは、付属するコードベース（src/kabusys 以下）の概要、セットアップ、実行方法、重要設定やディレクトリ構成を日本語でまとめた README です。

注意: 本リポジトリは複数のコンポーネント（ExecutionEngine / Monitoring / Research / AI 等）で構成されています。実行前に .env を正しく設定し、必要な外部ライブラリをインストールしてください。

---

目次
- プロジェクト概要
- 主な機能一覧
- 必要条件・依存ライブラリ
- セットアップ手順
- 環境変数 / .env（重要な設定）
- 使い方（主要スクリプト、CLI）
- 停止・Kill Switch の仕組み
- ディレクトリ構成（主要ファイル説明）
- よくある注意点 / トラブルシュート

---

プロジェクト概要
- KabuSys は日本株の自動売買フレームワーク（プロトタイプ）です。
- データ取得・ファクター計算（research）、ポートフォリオ構築（portfolio）、発注/発注管理（execution）、監視（monitoring）、AI を使ったニュース NLP（ai）などのコンポーネントで構成されます。
- 設定は環境変数（.env）で行い、DuckDB と SQLite をデータストアとして利用します。
- Paper Trading（模擬発注）と Live（実取引）を環境変数で切り替え可能です。

主な機能一覧
- Execution Engine
  - 実際のブローカー／モックブローカーでの注文送信（kabuステーション想定）
  - 発注リスク管理（RiskManager）、オーダー管理、約定・ログ永続化
  - Paper Trading 時は MockBrokerClient を使用し、本番 DB と切り離して data/paper_trading.db に記録
- Monitoring
  - システム稼働監視（CPU / メモリ / ディスク / プロセス生存）
  - 注文ログ監視（滞留注文、異常約定など）
  - リスク監視（ドローダウン、ポジション上限）
  - Kill Switch（条件に応じて Execution 停止用フラグを書き出す）
- Research
  - ファクター計算（Momentum / Volatility / Value 等）
  - 特徴量探索・IC 計算・将来リターン計算
  - DuckDB 上の prices_daily / raw_financials テーブルを使用
- AI
  - ニュースのセンチメントを OpenAI（gpt-4o-mini 等）で評価し ai_scores に格納
  - 市場レジーム判定（ETF の MA200 やマクロニュースを LLM で評価）
- ツール
  - .env 対話式ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading 検証レポート生成（tools/paper_verification_report）

必要条件・依存ライブラリ（代表例）
- Python 3.10+ を想定（typing: 型注釈や新しい文法が利用されています）
- 必要なパッケージ（例）:
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML（validate_config で YAML 検証をする場合、オプション）
- インストール例:
  - pip install duckdb psutil openai PyYAML

セットアップ手順（概要）
1. リポジトリをクローン / 配置する
2. 仮想環境を作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install duckdb psutil openai PyYAML
4. .env を作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - あるいは .env.example を参照して手動で .env を作成
5. 設定検証（推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱いになります
6. データディレクトリおよびログディレクトリを準備（多くは自動作成されます）
   - デフォルト DB / ファイルパス: data/kabusys.duckdb, data/monitoring.db
   - logs/ ディレクトリはデフォルトで作られます

環境変数 / 重要な設定
- 必須（システム起動に必須）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 重要（挙動に影響）
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
    - paper_trading: Execution は MockBroker を使用し paper DB に記録
    - live: 実発注モード（慎重に設定すること）
  - DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
  - OPENAI_API_KEY: OpenAI を使う場合に必須
  - LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
  - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
  - PAPER_FILL_MODE: paper_trading 時のモック約定挙動（instant / partial / never / reject）
  - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリア（1=クリア, 0=クリアしない）
- ファイルパス（デフォルト）
  - PID ファイル: data/execution.pid
  - Kill flag: data/kill.flag
  - Stop flag used by run scripts: data/stop_requested.flag

使い方（主要スクリプト / CLI）
- 環境セットアップウィザード（.env 作成）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - 実行中は data/execution.pid が作成されます。
  - KABUSYS_ENV=paper_trading の場合、paper_trading 専用 DB に記録され、本番 DB と分離されます。
  - 起動前に data/stop_requested.flag が存在すると起動をスキップします（安全策）。
- 監視ループ起動（Monitoring）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL を環境変数で秒数指定できます（例: MONITOR_POLL_INTERVAL=30）
  - 監視は常に settings.sqlite_path（本番 monitoring.db）を使用します（環境に依らず）。
  - 監視は SystemMonitor / TradeMonitor / RiskMonitor を定期実行し、KillSwitch を評価します。
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で SQLite のパスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH より優先）
- 研究 / AI 機能（ライブラリとして利用）
  - kabusys.research.calc_momentum / calc_volatility / calc_value などを DuckDB 接続を渡して呼び出す
  - kabusys.ai.score_news(conn, target_date, api_key=None) — OpenAI API キーが必要
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
- ログ
  - ログは標準出力（stdout）とファイル（logs/<app_name>.log）に出力されます。ログは日次ローテーション（30日保持）。
  - LOG_DIR を設定するとログ保存先を変更できます。

停止・Kill Switch の仕組み
- 外部からの「即時停止要求」（実行スクリプトの優雅な終了）:
  - data/stop_requested.flag を作成すると run_monitoring / run_execution が検知して終了手順を実行します。
  - 例: touch data/stop_requested.flag
- Kill Switch（監視により自動で停止を促す）:
  - Monitoring の評価で危険（ドローダウン超過、ポジション数上限等）と判断した場合、KillSwitch が data/kill.flag を書き込みます。
  - ExecutionEngine は起動時に kill_flag_clear_on_start の設定に基づき kill.flag をクリアできます（デフォルトではクリアしないことを推奨）。
  - Kill Switch 書き込みは冪等（既存ファイルがあれば上書きしない）です。

ディレクトリ構成（主要ファイルの説明）
- src/kabusys/
  - __init__.py — パッケージ定義、バージョン
  - config.py — Settings クラス（環境変数/.env 読み込み・検証）
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — Monitoring ポーリングループ起動スクリプト
  - utils/
    - logging_setup.py — ログ下部共通設定（コンソール + ファイル）
    - process_priority.py — プロセス優先度 / CPU affinity のユーティリティ
  - monitoring/
    - monitoring_db.py — SQLite ベースの永続化・API（テーブル作成／読み書き）
    - system_monitor.py — CPU/メモリ/ディスク/データ鮮度/プロセスをチェック
    - trade_monitor.py — （注文ログの監視。コードベース内に実装あり）
    - risk_monitor.py — ドローダウン／ポジション制限監視
    - kill_switch.py — kill.flag の生成/評価
    - monitoring_engine.py — 複数モニタのまとめ実行
    - alert_manager.py —（通知：LINE など。コードベース内に実装あり）
  - execution/ (発注周りの実装: broker, engine, order_manager, risk_manager 等)
  - portfolio/
    - portfolio_builder.py — 候補選定・重み付け
    - position_sizing.py — 株数計算・資金配分
    - risk_adjustment.py — セクター上限・レジーム乗数
  - research/
    - factor_research.py — Momentum / Volatility / Value 等の計算
    - feature_exploration.py — 将来リターン / IC / 統計サマリー
  - ai/
    - news_nlp.py — ニュースを LLM で評価し ai_scores に保存
    - regime_detector.py — マクロ + ETF MA を使ったレジーム判定
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成ツール
  - data/（実行時に使用されるファイル／DB を置く想定）
    - monitoring.db（デフォルト SQLite）
    - paper_trading.db（paper_trading 用）
    - kabusys.duckdb（DuckDB）
    - stop_requested.flag / kill.flag / execution.pid など

（簡易ツリー）
- src/
  - kabusys/
    - run_execution.py
    - run_monitoring.py
    - config.py
    - config_setup.py
    - validate_config.py
    - utils/
    - monitoring/
    - execution/
    - portfolio/
    - research/
    - ai/
    - tools/
    - data/ (ランタイムで出現)

よくある注意点 / トラブルシュート
- 必須環境変数未設定で起動に失敗する場合は、python -m kabusys.config_setup で .env を作成後に python -m kabusys.validate_config で検証してください。
- OpenAI を使う機能（news_nlp, regime_detector）は OPENAI_API_KEY が必要です。テスト時はモック関数で差し替え可能です。
- validate_config は PyYAML がない場合、config/*.yaml の内容検証をスキップします（警告）。
- run_monitoring は常に settings.sqlite_path（本番の monitoring DB）を使います。monitoring は環境に関わらず本番 DB を参照する仕様です。
- Paper Trading（KABUSYS_ENV=paper_trading）は発注系の DB を分離します（デフォルト data/paper_trading.db）。
- ログディレクトリの作成に失敗した場合、コンソールのみでログが出力されます（警告が出ます）。
- プロセス優先度設定は OS に依存します。必要な権限がない場合は警告が出て無視されます。

付記
- この README はコードベースの主要な設計意図や使用法をまとめたものです。実際の運用に当たっては config/*.yaml（存在する場合）、.env の内容、及びブローカー API の仕様（kabuステーション等）を必ず確認してください。
- セキュリティ: .env（API トークン、パスワード等）をリポジトリにコミットしないでください。

---

必要であれば、README に含めるコマンド例（systemd サービス、Dockerfile、CI 用コマンド、より詳細な設定項目説明など）を追加で作成します。どの部分を詳細化したいか教えてください。