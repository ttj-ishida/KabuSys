# KabuSys

日本株向けの自動売買システム（モジュール群）。このリポジトリは以下の主要機能を含みます：注文実行エンジン（実発注／ペーパートレード両対応）、監視モジュール（プロセス／データ鮮度／リスク監視）、ポートフォリオ構築・ポジションサイジング、リサーチ（ファクター計算・特徴量解析）、AI 支援（ニュースセンチメント・レジーム判定）、および各種ユーティリティ・ツール。

以下はこのコードベースを使い始めるための README（日本語）です。

---

目次
- プロジェクト概要
- 機能一覧
- 必要要件・依存パッケージ
- セットアップ手順
- 使い方（主要 CLI / API）
- 主要環境変数と設定
- 運用メモ（停止／Kill Switch 等）
- ディレクトリ構成

---

プロジェクト概要
- 名前: KabuSys
- 目的: 日本株の自動売買ワークフローを構成するライブラリおよび起動スクリプト群。取引実行、監視、リスク管理、ポートフォリオ構築、リサーチ、AI ベースのニュース解析などを含む。
- 設計方針: テストしやすく、フェイルセーフ重視（API 失敗はフォールバックして継続）。本番（live）・ペーパートレード（paper_trading）・開発（development）を環境変数で切替可能。

機能一覧
- 実行エンジン (ExecutionEngine)
  - 本番ブローカークライアントとペーパートレード用の MockBrokerClient を切替
  - オーダー管理、リスク管理、リコンシリエーション機能を組み合わせてセッション実行
- 監視（Monitoring）
  - SystemMonitor: CPU/メモリ/ディスク・プロセス生存・データ鮮度を監視し SQLite に記録
  - TradeMonitor: 発注ログの監視（滞留注文・約定異常など）※関連ファイル参照
  - RiskMonitor: ドローダウンやポジション上限を監視しリスクイベントをログ化
  - KillSwitch: 条件に応じて data/kill.flag を書き込み、ExecutionEngine を停止させる仕組み
  - MonitoringEngine: 上記モジュールをまとめてポーリング実行
- ポートフォリオ構築
  - 候補選定、等配分・スコア加重、セクターキャップ、レジームによる乗数適用、株数算出（lot サイズ・コストバッファ考慮）
- リサーチ
  - ファクター計算（モメンタム・ボラティリティ・バリュー等）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリ
- AI モジュール
  - news_nlp: OpenAI を用いたニュース記事の銘柄別センチメント評価（ai_scores テーブルへ書き込み）
  - regime_detector: ETF とマクロニュースを合成して市場レジーム判定（market_regime へ冪等書き込み）
- ユーティリティ
  - ロギングセットアップ（コンソール + 日次ローテーションファイル）
  - プロセス優先度・CPU affinity 設定
  - .env 対話ウィザード、設定検証 CLI
- ツール
  - paper_verification_report: ペーパートレード DB を解析して検証レポートを出力

必要要件・依存パッケージ
- Python 3.10 以上推奨（union types と型注釈を使用）
- 必須ライブラリ（機能に応じて）:
  - duckdb
  - psutil
  - openai (AI 機能利用時)
- 任意 / 推奨:
  - PyYAML（config/*.yaml の検証に使用。無い場合は検証をスキップ）
- 標準ライブラリ: sqlite3, logging, argparse, threading, datetime, pathlib など

セットアップ手順（ローカル開発向け）
1. リポジトリをクローンして、Python 仮想環境を作る
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb psutil openai
   - （開発時は PyYAML を入れると validate_config の YAML 検査が有効化される）: pip install pyyaml

   ※ requirements.txt が無い場合は上記を個別にインストールしてください。

3. .env の作成
   - 対話式で .env を作る:
     - python -m kabusys.config_setup
   - 作成後、.env をプロジェクトルートに保存（.env は絶対に Git にコミットしないこと）

4. 設定検証
   - python -m kabusys.validate_config
   - 警告も FAIL 扱いにする場合: python -m kabusys.validate_config --strict

5. データディレクトリ等の確認
   - デフォルトの DB / PID / ログパス:
     - DuckDB: data/kabusys.duckdb (環境変数 DUCKDB_PATH)
     - SQLite (監視): data/monitoring.db (SQLITE_PATH)
     - Paper trading SQLite: data/paper_trading.db (PAPER_TRADING_SQLITE_PATH)
     - PID ファイル: data/execution.pid (PID_FILE_PATH)
     - Kill flag: data/kill.flag (KILL_FLAG_PATH)
     - ログ: logs/ (LOG_DIR、ファイル名は app_name.log)

使い方（主要 CLI / API）
- 実行（Execution Engine）
  - 本番 / ペーパートレード は KABUSYS_ENV により切替
  - 起動:
    - python -m kabusys.run_execution
    - 実行中に data/stop_requested.flag を作成すると起動済みスレッドが停止シグナルを受け取って終了する
  - ペーパートレード時は専用 DB を使用（PAPER_TRADING_SQLITE_PATH または Settings.paper_sqlite_path）

- 監視（Monitoring）
  - 起動:
    - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（秒、デフォルト 60）
  - run_monitoring は MonitoringDB（SQLite）に状態を記録する。Monitoring は本番 sqlite_path を常に使用する（KABUSYS_ENV に依存しない）
  - run_monitoring/run_execution は共に data/stop_requested.flag を監視して終了する

- .env ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も exit(1) 扱い

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH （環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- AI / プログラム API
  - ニュース NLP スコア作成:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key="...")  # OpenAI APIキーは引数か環境変数 OPENAI_API_KEY
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key="...")

主要環境変数（要点）
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 実行モード:
  - KABUSYS_ENV: development | paper_trading | live（デフォルト development）
- DB / ログ:
  - DUCKDB_PATH (default: data/kabusys.duckdb)
  - SQLITE_PATH (default: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)
  - LOG_DIR (default: logs/)
- ロギング:
  - LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL)
- 監視関連:
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）
  - PID_FILE_PATH (実行エンジン用 PID ファイル)
  - KILL_FLAG_PATH (kill.flag の場所)
  - KILL_FLAG_CLEAR_ON_START (0/1; 1 にすると起動時に kill.flag を自動削除)
- AI:
  - OPENAI_API_KEY（news_nlp / regime_detector 使用時）
- ペーパートレード挙動:
  - PAPER_FILL_MODE: instant | partial | never | reject

運用メモ（停止・Kill Switch・PID）
- 停止:
  - run_monitoring/run_execution はプロジェクトルートの data/stop_requested.flag を監視します。ファイルを作れば安全に停止できます。
- Kill Switch:
  - 条件（ドローダウン閾値超過、ポジション上限超過等）が満たされた場合、KillSwitch が data/kill.flag を書き込みます。ExecutionEngine はこれを検出して発注停止などの措置を取る想定です。
  - kill.flag の削除は KillSwitch.clear() または手動削除で行うか、KILL_FLAG_CLEAR_ON_START 環境変数を 1 にして起動時に自動クリアできます（本番では 0 推奨）。
- PID:
  - ExecutionEngine は PID ファイル（デフォルト data/execution.pid）を扱います。サービス化する場合はこのファイルを監視してデーモンプロセスの管理を行えます。
- プロセス優先度:
  - 起動時に set_process_priority("high") を呼び出します。権限不足（Linux の nice 値変更など）の場合は警告が出ますが処理は継続されます。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理（.env 自動ロード機能含む）
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py            — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py     — 市場レジーム判定（OpenAI）
    - __init__.py
  - monitoring/
    - monitoring_db.py       — SQLite のスキーマ & 永続化 API
    - system_monitor.py
    - trade_monitor.py       — （発注ログ監視：実装ファイルあり）
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py       — （アラート送信管理: 例 LINE 通知 など）
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
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - utils/
    - logging_setup.py
    - process_priority.py
    - __init__.py
  - monitoring/monitoring_db.py (上に示した監視 DB 実装)

（注）上記は実装の主要モジュールを抜粋した構成です。実際のリポジトリにはさらに補助モジュールやテスト用コードが含まれる場合があります。

サンプル .env（最低限の必須キー）
- .env.example を参照して作成してください。最低限必要な環境変数：
  - JQUANTS_REFRESH_TOKEN=your_token_here
  - KABU_API_PASSWORD=your_password_here
  - KABUSYS_ENV=development
  - DUCKDB_PATH=data/kabusys.duckdb
  - SQLITE_PATH=data/monitoring.db
  - LOG_LEVEL=INFO
  - OPENAI_API_KEY=（AI機能を使う場合）

トラブルシューティング / 注意事項
- OpenAI API を利用する機能は API キーと通信回数に応じたコストが発生します。API 呼び出しエラーはリトライやフォールバックを行う設計ですが、運用時はレートやエラーハンドリングの監視を行ってください。
- run_monitoring は常に本番用 sqlite_path を使用するため、テストで隔離したい場合は DB パスを別途設定してください。
- process priority の設定は OS と権限に依存します（通常のユーザー権限では優先度変更できない場合があります）。

---

この README はコードベースの主要点をまとめた簡易ガイドです。実運用に移す前に config/*.yaml（存在する場合）や .env の内容を十分に確認し、validate_config で検証してください。必要があれば追加で運用手順（systemd / supervisor / Docker 化など）を作成してください。