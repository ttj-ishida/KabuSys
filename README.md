README
=====

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤のモジュール群です。  
主な機能は以下を含みます。

- 実行エンジン（ExecutionEngine）および監視プロセス（Monitoring）
- ポートフォリオ構築（銘柄選定／配分／ポジションサイズ計算）
- リサーチ用ファクター計算（モメンタム・ボラティリティ・バリュー等）
- AI を使ったニュースセンチメント（OpenAI）によるスコアリング／レジーム判定
- 監視ログ永続化（SQLite）・アラート／Kill Switch ロジック
- 開発支援ツール（.env ウィザード、設定検証、ペーパートレード検証レポート）

主な設計方針
- ランタイム設定は環境変数（.env）で管理。config_setup のウィザードで .env を生成できます。
- Paper Trading（KABUSYS_ENV=paper_trading）は本番 DB と分離（data/paper_trading.db）。
- AI 呼び出しは堅牢さ優先（リトライ、フェイルセーフ、入力/出力バリデーション）。
- DuckDB をリサーチ用データベース、SQLite を監視・注文ログ用に利用。

機能一覧
----------
- 実行スクリプト
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV により実ブローカー / モックを切替）
  - run_monitoring.py: SystemMonitor をポーリングして監視ログを蓄積

- 設定管理
  - config.py: Settings クラス（環境変数/.env の自動読み込み・検証）
  - config_setup.py: 対話式 .env 作成ウィザード
  - validate_config.py: 起動前の設定検証 CLI（--strict オプション有り）

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py: 候補選定、等分配・スコア加重配分
  - portfolio/position_sizing.py: 発注株数計算（Lot 単位、リスクベース等）
  - portfolio/risk_adjustment.py: セクター上限・レジーム乗数

- リサーチ
  - research/factor_research.py: momentum / volatility / value のファクター計算（DuckDB）
  - research/feature_exploration.py: 将来リターン / IC / 統計サマリー等

- AI
  - ai/news_nlp.py: ニュース記事を OpenAI でスコアリングして ai_scores に保存
  - ai/regime_detector.py: MA200 とマクロニュースセンチメントの合成でレジーム判定

- 監視
  - monitoring/monitoring_db.py: SQLite スキーマ初期化・読み書きユーティリティ
  - monitoring/system_monitor.py: システム状態・データ鮮度チェック
  - monitoring/trade_monitor.py, risk_monitor.py, kill_switch.py, monitoring_engine.py: 各種監視ロジックと Kill Switch
  - tools/paper_verification_report.py: ペーパートレードの検証レポート生成

- ユーティリティ
  - utils/logging_setup.py: 共通ログ設定（コンソール + 日次ローテーションファイル）
  - utils/process_priority.py: プロセス優先度 / CPU affinity 設定ユーティリティ

セットアップ手順
----------------

前提
- Python 3.10 以上（コード中に | 型ヒント等を使用）
- sqlite3 は標準、以下追加パッケージが必要です

推奨パッケージ（pip でインストール）
- duckdb
- psutil
- openai
- pyyaml（validate_config で YAML パースをしたい場合のみ）

例:
  python -m venv .venv
  source .venv/bin/activate
  pip install duckdb psutil openai pyyaml

.env の準備
1. 対話ウィザードで作成（推奨）
   python -m kabusys.config_setup

2. 作成後、設定を検証
   python -m kabusys.validate_config
   （警告をエラー扱いにする場合）
   python -m kabusys.validate_config --strict

主要な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE（paper_trading 時の約定モード: instant|partial|never|reject、デフォルト instant）
- LOG_LEVEL（DEBUG/INFO/...）
- OPENAI_API_KEY（AI 機能使用時に必要）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔秒、デフォルト 60 秒）
- LOG_DIR（ログ出力先、デフォルト logs/）

使い方
--------

起動スクリプト
- 実行エンジン（ExecutionEngine）を起動:
  python -m kabusys.run_execution

  備考:
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を用い、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録します。本番 DB と分離されます。
  - 起動時に data/stop_requested.flag が存在するとエンジンは起動しません。
  - 起動中は data/execution.pid に PID を書きます。

- 監視プロセスを起動:
  python -m kabusys.run_monitoring

  備考:
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で指定可能（例: MONITOR_POLL_INTERVAL=30）。
  - 監視プロセスは常に設定の sqlite_path（監視用 DB）を使用します。
  - 終了は data/stop_requested.flag を作成するか Ctrl+C。

停止・Kill Switch
- Kill Switch（kill.flag）:
  - RiskMonitor / KillSwitch の評価で条件を満たすと data/kill.flag が作成され、ExecutionEngine に停止シグナルを送ります。
  - KillSwitch は既存の flag を上書きせず冪等です。
  - 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると自動クリアされます（本番では 0 推奨）。

ログ
- デフォルトでコンソール出力（stdout）とファイル出力（logs/<app_name>.log）を併用します。
- ログファイルは日次ローテーション（30 日保持）。
- ログ設定は kabusys.utils.logging_setup.setup_logging で統一されています。

ツール
- ペーパートレード検証レポート:
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db --from 2026-04-01 --to 2026-04-11

設定検証
- .env や config/*.yaml（存在する場合）を事前にチェック:
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

ディレクトリ構成（抜粋）
----------------------

プロジェクトルート（src/kabusys を想定）

- src/kabusys/
  - __init__.py
  - config.py
  - config_setup.py
  - validate_config.py
  - run_execution.py
  - run_monitoring.py
  - tools/
    - __init__.py
    - paper_verification_report.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - trade_monitor.py  (取引監視ロジック)
    - alert_manager.py  (アラート送信ロジック: LINE 等)
  - execution/
    - (ExecutionEngine, BrokerFactory, OrderManager, Reconciler, RiskManager, OrderRepository 等)
  - utils/
    - __init__.py
    - logging_setup.py
    - process_priority.py
  - data/ (実行時に生成される想定: DB、PID、フラグファイル、logs/ 等)

注意事項 / 補足
----------------
- Python バージョンは 3.10 以上を想定（| 型ヒントを使用）。
- OpenAI API を使う機能（ai/news_nlp.py, ai/regime_detector.py）を利用する際は OPENAI_API_KEY を設定してください。
- validate_config は PyYAML がインストールされている場合に config/*.yaml の中身も検証します。未インストールでも実行は可能ですが YAML 検証はスキップされます。
- ローカル開発時は KABUSYS_ENV=development を利用してください（発注を行わない設定等で安全に動作する想定）。
- Paper Trading を用いるときは PAPER_FILL_MODE の値（instant|partial|never|reject）に注意してください（モックの約定挙動を制御します）。
- データベースファイル・ログディレクトリ等の親ディレクトリが存在しない場合は起動時に自動作成されることがありますが、validate_config により事前確認することを推奨します。

貢献 / 開発
------------
- 既存の .env は絶対にリポジトリにコミットしないでください（README 内にもその旨が .env ヘッダに書かれています）。
- 新しい設定項目を追加したら config_setup.py と validate_config.py を更新してください。
- AI 呼び出し周りは外部 API の仕様変更を考慮して抽象化／テストしやすい設計が意図されています。ユニットテストで _call_openai_api をモックすることを推奨します。

以上。必要であれば各モジュールの API 使用例や設定例（.env.example 形式）を付けた拡張版 README を作成します。