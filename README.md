KabuSys
======

日本株向けの自動売買・リサーチ基盤の一部をまとめた Python コードベースです。  
本リポジトリはトレード実行エンジン、監視/アラート、ポートフォリオ構築、ファクター/研究モジュール、AI を使ったニュース解析等の機能を含みます。

概要
----
KabuSys は以下の主要コンポーネントで構成されています。

- ExecutionEngine: ブローカークライアントを通じた発注ロジック、リスク管理、注文管理を行う実行エンジン（run_execution.py から起動）。
- Monitoring: システム/注文/リスクのポーリング監視とアラート、Kill Switch（run_monitoring.py から起動）。
- Portfolio: 候補選定、配分（等重・スコア重み）、ポジションサイズ計算などの純粋関数群。
- Research: DuckDB 上の価格・財務データを用いたファクター計算・特徴量探索。
- AI: ニュースのセンチメント集約（OpenAI）や市場レジーム判定モジュール。
- Tools: ペーパートレード検証レポート等のユーティリティスクリプト。
- Utils: ロギング設定、プロセス優先度設定、設定読み込み等の共有ユーティリティ。

主な機能
--------
- 実行エンジン（ExecutionEngine）起動/停止制御、ペーパートレード（環境切替）対応
- 監視ポーリング（CPU/メモリ/ディスク、プロセス監視、データ鮮度チェック）
- Kill Switch: 監視から閾値超過等で停止フラグ（data/kill.flag）を書き、実行エンジンを安全に停止
- リスク監視（ドローダウン、ポジション数上限）とリスクログ永続化
- ポートフォリオ構築ロジック（候補選定、等比配分、スコア重み、ポジションサイズ計算）
- DuckDB を用いたファクター計算（Momentum / Volatility / Value 等）
- OpenAI を用いたニュース NLP（ニュース -> 銘柄ごとのセンチメントスコア）
- ペーパートレード結果の検証レポート生成

セットアップ手順
----------------

1. Python と依存パッケージ（例）
   - Python 3.9+ を想定
   - 必要なパッケージ（例）:
     - duckdb
     - psutil
     - openai (AI 機能を使う場合)
     - PyYAML（config ファイル検証を使う場合）
   - 例: pip install duckdb psutil openai PyYAML

   （プロジェクトに requirements.txt があればそちらを使ってください）

2. プロジェクトルートに移動し、.env を作成
   - 対話式ウィザードで .env を生成:
     python -m kabusys.config_setup

   - あるいは .env.example を参考に手動作成（.env は絶対に Git にコミットしないこと）。

   自動ロード:
   - kabusys.config モジュールはプロジェクトルート（.git または pyproject.toml を基準）を検出すると .env/.env.local を自動読み込みします。
   - 自動ロードを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

3. 設定検証
   - 作成後に検証を実行:
     python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります。

4. データディレクトリ作成（必要に応じて）
   - デフォルトでは data/ 配下に DB や flag ファイルを作成します。権限や場所を適切に確認してください。

主要環境変数（抜粋）
-------------------
（Settings クラスに定義されているものの主要項目）

必須:
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）

任意（デフォルトを示す）:
- KABUSYS_ENV: 実行環境。development | paper_trading | live（デフォルト: development）
  - paper_trading: MockBrokerClient が使われ、ペーパートレード専用 DB（PAPER_TRADING_SQLITE_PATH）に記録される
  - live: 本番モード（注意深く設定を確認すること）
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- LOG_LEVEL: INFO（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR: logs/（ログ保存先ディレクトリ）
- PID_FILE_PATH: data/execution.pid
- KILL_FLAG_PATH: data/kill.flag
- KILL_FLAG_CLEAR_ON_START: 0（起動時に kill.flag を自動クリアするか）
- PAPER_FILL_MODE: instant | partial | never | reject（ペーパートレードの約定挙動）

監視周り:
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
  - 0 や負数を指定すると無効扱いで 60 にフォールバック

ログ
---
- ログ設定は kabusys.utils.logging_setup.setup_logging を通じて統一的に行われます。
- デフォルトで stdout に出力しつつ、logs/<app_name>.log に日次ローテーションで保存（30日分保管）。
- LOG_LEVEL / LOG_DIR で調整可能。

起動・使い方
------------

1. .env を用意・検証したら各コンポーネントを起動します。

- ExecutionEngine（発注エンジン）を起動:
  python -m kabusys.run_execution

  挙動のポイント:
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient が使用され、データは PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録され本番 DB と分離されます。
  - 起動時に data/stop_requested.flag が存在すると起動せず終了します。
  - 実行中は PID を PID_FILE_PATH（デフォルト data/execution.pid）に書きます。
  - 停止は監視からの kill.flag（data/kill.flag）や stop_requested.flag で制御します。

- Monitoring（監視ループ）を起動:
  python -m kabusys.run_monitoring

  挙動のポイント:
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（秒、デフォルト 60）。
  - 監視は monitoring DB（Settings.sqlite_path）へ永続化します（init_monitoring_db を自動実行）。
  - 監視は常に本番 sqlite_path を使用して監視データを記録します（環境にかかわらず本番 DB を参照する設計）。

- Paper Trading 検証レポート:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で DB パスを直接指定可能（デフォルトは環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db）。

停止方法 / Kill Switch
---------------------
- 監視経由で条件を満たすと KillSwitch が data/kill.flag を書き込み、ExecutionEngine はこれを検知して安全に停止します。
- 手動で全システムを停止したい場合はプロジェクトの data/stop_requested.flag を作成すると run_* スクリプトが起動中のループを止めます（run_execution / run_monitoring 両方で参照）。
- 実行中の PID 管理には PID_FILE_PATH（デフォルト data/execution.pid）を使用します。

DB とマイグレーション
--------------------
- monitoring 用軽量 SQLite: data/monitoring.db（Settings.sqlite_path）
  - init_monitoring_db により監視用テーブル群を冪等に作成します。
- 分析用 DuckDB: data/kabusys.duckdb（Settings.duckdb_path）
- ペーパートレード用 SQLite: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH）
- 既存 DB に必要カラムが無い場合、init_monitoring_db にて簡単なマイグレーション（ALTER TABLE ADD COLUMN）を行います。

AI 機能
-------
- kabusys.ai.news_nlp / kabusys.ai.regime_detector は OpenAI API（gpt-4o-mini など）を用います。
- 利用には OPENAI_API_KEY を環境変数に設定する必要があります。
- API 呼び出しはリトライ・バックオフ・レスポンスバリデーション等の堅牢化が組み込まれています。
- API キー未設定時は明示的な例外を投げます（呼び出し側でキャッチしてフォールバックも可能）。

開発ノート / その他
------------------
- kabusys.config は .env/.env.local の自動読み込みロジックを持ち、CWD に依存しないプロジェクトルート検出を行います。
- 設定検証スクリプト（validate_config）は .env と config/*.yaml の存在と整合性チェックを行います（PyYAML が無ければ YAML 内容検証はスキップして警告）。
- ロギングはルートロガーを統一して設定するため、すべての起動スクリプトで setup_logging を呼び出してください。
- process_priority ユーティリティで Windows / POSIX の差分を吸収してプロセス優先度や CPU affinity を設定できます（権限不足時は警告でスキップ）。

ディレクトリ構成（主要ファイル）
--------------------------------
src/kabusys/
- __init__.py
- config.py                — 環境変数 / Settings 管理
- config_setup.py          — .env 対話ウィザード
- validate_config.py       — 設定検証 CLI
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — Monitoring 起動スクリプト

subpackages:
- ai/
  - news_nlp.py            — ニュース NLP（OpenAI）により ai_scores を作成
  - regime_detector.py     — 市場レジーム判定（MA + マクロセンチメント）
- data/
  - (pipeline / stats 等 — DuckDB 関連ユーティリティ想定)
- execution/
  - execution_engine.py    — 実行エンジン本体
  - broker_factory.py      — ブローカ クライアント生成
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - risk_manager.py
- monitoring/
  - monitoring_db.py       — SQLite 永続化層
  - monitoring_engine.py
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - alert_manager.py
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- tools/
  - paper_verification_report.py
- utils/
  - logging_setup.py       — ログ設定ユーティリティ
  - process_priority.py    — プロセス優先度ユーティリティ

よくある操作例
--------------
- .env 作成:
  python -m kabusys.config_setup

- 設定検証:
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- 監視の手動実行（1回）:
  from kabusys.monitoring.monitoring_engine import MonitoringEngine
  # テストコードで MonitoringEngine.run_once() を使うなど

- ペーパートレード検証レポート:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

注意事項
--------
- .env に機密情報（API キー・パスワード）を含めるため、絶対にリポジトリへコミットしないでください。
- KABUSYS_ENV=live の場合は本番環境向けの挙動に変わるため、設定を慎重に確認してください（validate_config がライブガードをチェックします）。
- OpenAI 等外部 API を使う機能は API 利用料金やレート制限に注意してください。

この README はコードベースの主要点をまとめた要約です。詳細実装や追加の使い方は個々のモジュール（src/kabusys 以下の各ファイル）の docstring を参照してください。