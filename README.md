README
=====

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤のサンプル実装です。  
主に次の責務を持ちます。

- 発注エンジン（ExecutionEngine）とブローカークライアントの抽象化（paper_trading モードあり）
- 監視・アラート（System / Trade / Risk のポーリング監視、Kill Switch）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ決定）
- リサーチ（ファクター計算、将来リターン、IC 計算）
- AI 製品（ニュースの NLP スコアリング / 市場レジーム判定）
- 運用支援ツール（.env 設定ウィザード、設定検証、Paper Trading 検証レポート）

主な特徴
--------
- 実運用を意識した設計（本番/ペーパートレードの DB 分離、Kill Switch、ログローテーション）
- DuckDB を用いた分析処理と SQLite を用いた監視/履歴の永続化
- OpenAI を用いたニュースセンチメント・レジーム検知（API キーで有効化）
- テストしやすい純粋関数群（ポートフォリオ/リスク計算などは副作用なし）
- 起動スクリプト群（monitoring / execution）でデーモン的に動作可能
- .env 対話式ウィザードと事前設定検証 CLI を備える

動作要件
--------
- Python >= 3.10（注: 型ヒントに | を使用）
- 必要な主要ライブラリ（例）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config YAML の検証オプション）
- SQLite は標準ライブラリで利用可能

セットアップ手順
----------------
1. リポジトリをクローン／配置
   - パッケージ構造は src/kabusys 以下にあります。開発環境では src を PYTHONPATH に含めてください。

2. 仮想環境を作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - 例（最低限）:
     - pip install duckdb psutil openai
   - config YAML の検証を使う場合:
     - pip install pyyaml
   - 実運用では requirements.txt / Poetry 等を用意して管理してください。

4. .env を作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - あるいは手動で .env を作成（リポジトリルートに配置）
   - 必須の環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - OPENAI を使う場合:
     - OPENAI_API_KEY を設定

5. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります

使い方（主要コマンド）
---------------------
- 環境選択:
  - KABUSYS_ENV は次のいずれか: development / paper_trading / live
  - paper_trading モードでは MockBrokerClient を使用し、データは data/paper_trading.db に保存します

- 実行エンジン（ExecutionEngine）起動
  - python -m kabusys.run_execution
  - 起動時に data/stop_requested.flag が存在すると起動をスキップします
  - 停止は data/stop_requested.flag を作成して行います（監視プロセス等から判定）

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - デフォルトは 60 秒ごとにポーリング（MONITOR_POLL_INTERVAL 環境変数で秒数を上書き可能）
  - 監視は常に本番用の sqlite_path を使って監視ログを書き込みます

- .env 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict で警告も失敗扱い

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH 環境変数で変更可）

運用上の重要なファイル／フラグ
------------------------------
- data/stop_requested.flag
  - run_execution / run_monitoring のループを止めるための外部停止フラグ（存在を監視）
- data/kill.flag
  - KillSwitch が作成するフラグ。ExecutionEngine に対して即時停止シグナル（永続的な「Kill Switch」）
- data/execution.pid（デフォルト）
  - 実行エンジンの PID を保持するファイル（設定で変更可能）
- DB
  - DuckDB: data/kabusys.duckdb（分析用）
  - SQLite (monitoring): data/monitoring.db
  - SQLite (paper trading): data/paper_trading.db（paper_trading モード）

主な設計／挙動メモ
------------------
- run_monitoring は MONITOR_POLL_INTERVAL（秒、環境変数）で制御可能。0 以下や不正値はデフォルト 60 秒にフォールバックします。
- run_execution は KABUSYS_ENV が paper_trading のとき paper_trading 用の SQLite（paper_sqlite_path）を使用して本番 DB と分離します。
- Logging は kabusys.utils.logging_setup.setup_logging を通して統一設定され、コンソールと日次ローテートファイル（logs/*.log）へ出力します。
- process priority / CPU affinity の設定ユーティリティ（psutil 依存）を提供しますが、権限不足や未対応 OS の場合は警告をログに出してスキップします。
- AI 関連機能（news_nlp, regime_detector）は OpenAI API を利用します。API 呼び出しはリトライ・バックオフや応答検証を備えています。API キーの未設定時は明示的にエラーを出す箇所があります。

ディレクトリ構成（要約）
----------------------
- src/kabusys/
  - __init__.py
  - config.py               — 環境変数/設定管理
  - config_setup.py         — .env 対話式ウィザード
  - validate_config.py      — 起動前の設定検証 CLI
  - run_execution.py        — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — Monitoring ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py (実装あり)
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py (実装あり)
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - risk_manager.py
    - reconciler.py
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
  - data/                   — 実行時に使用するデータ/DB/フラグを置く（デフォルト）
  - logs/                   — ログファイル出力先（デフォルト）

補足：よくある運用手順（例）
--------------------------
1. .env を作成（python -m kabusys.config_setup）
2. 設定検証（python -m kabusys.validate_config）
3. （必要なら）DuckDB にデータをロードしておく
4. 監視プロセスを起動（python -m kabusys.run_monitoring）
5. 実行エンジンを起動（python -m kabusys.run_execution）
6. 異常時は run_monitoring が Kill Switch を書き、ExecutionEngine を止める

ライセンス・貢献
----------------
このドキュメントはコードベースから生成した README です。実際の運用・配布時は LICENSE ファイル・コントリビュート方針をプロジェクトに合わせて追加してください。

以上。必要であればセクションを追加（例: 詳しい環境変数一覧、DB スキーマ、API 使用例、ユニットテストの実行方法）します。どの情報を詳しく記載したいか教えてください。