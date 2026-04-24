README
=====

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤です。価格データ集計（DuckDB）、ポートフォリオ構築、発注実行、監視（Monitoring）、
および AI を活用したニュースセンチメント／レジーム判定などのコンポーネントを備えます。設計方針としては本番/ペーパートレードの分離、
ルックアヘッドバイアス回避、冪等な DB 書き込み、外部 API 呼び出しのフェイルセーフ化を重視しています。

主な機能一覧
--------------
- 実行エンジン（ExecutionEngine）
  - 本番 / ペーパートレードの切替（KABUSYS_ENV）
  - ブローカークライアントの抽象化（MockBrokerClient をサポート）
  - リスク管理（ポジション上限、ドローダウン等）
- 監視（Monitoring）
  - システムリソース監視（CPU/メモリ/ディスク）
  - データ鮮度チェック（DuckDB の prices_daily 参照）
  - 発注ログ・リスクログの永続化（SQLite）
  - Kill Switch（条件により ExecutionEngine を停止するフラグ）
- ポートフォリオ構築
  - 候補選定、等金額 / スコア重み、リスクベースのポジションサイズ計算
  - セクターキャップ / レジーム乗数の適用
- 研究（Research）
  - ファクター計算（Momentum / Volatility / Value 等）
  - 将来リターン計算、IC（Information Coefficient）計算、特徴量サマリ
- AI（OpenAI）
  - ニュースを LLM でスコアリングし ai_scores に格納（news_nlp）
  - マクロニュースと ETF MA200 を組み合わせた市場レジーム判定（regime_detector）
- ツール
  - Paper Trading の検証レポート生成スクリプト（tools.paper_verification_report）
- 設定ユーティリティ
  - .env の対話式ウィザード（config_setup）
  - 設定検証 CLI（validate_config）

セットアップ手順
----------------
1. リポジトリをクローンし、仮想環境を作成する（例: venv, pyenv-virtualenv 等）。
   - python -m venv .venv
   - source .venv/bin/activate

2. 依存関係をインストールする
   - (可能であれば) requirements.txt を用意している場合:
     - pip install -r requirements.txt
   - 最低限必要なパッケージ（例）:
     - pip install duckdb psutil openai PyYAML
   - SQLite は標準ライブラリに含まれます。

3. .env の作成
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - 必須環境変数（例）:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
   - 重要: .env をリポジトリにコミットしないでください（secrets が含まれるため）。

4. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 警告を厳格に扱う場合は --strict を付ける:
     - python -m kabusys.validate_config --strict

5. DB ディレクトリ作成（必要に応じて）
   - デフォルトの DB パス:
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper trading DB: data/paper_trading.db

使い方（主要コマンド）
--------------------
- Execution エンジン起動
  - ペーパートレード（MockBroker を使用）:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - 本番実行:
    - KABUSYS_ENV=live python -m kabusys.run_execution
  - 補足:
    - 起動時に PID ファイルを data/execution.pid に書き込みます（Settings.pid_file_path で変更可能）。
    - run_execution は data/stop_requested.flag の存在を監視し、存在する場合は起動しない／停止します。

- Monitoring 起動（ポーリング）
  - python -m kabusys.run_monitoring
  - 環境変数で間隔を上書き:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    - デフォルト 60 秒。
  - 補足:
    - Monitoring は本番 sqlite_path を常に使用して監視ログを保存します（Settings.sqlite_path）。
    - 停止はプロジェクトルート/data/stop_requested.flag を作成すると検知して終了します。

- .env 作成ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い（exit code 1）になります。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  - デフォルト DB は data/paper_trading.db（PAPER_TRADING_SQLITE_PATH 環境変数で上書き可）

- AI 関連（OpenAI）
  - news_nlp.score_news / regime_detector.score_regime を呼び出すコード経由で実行
  - 必須: OPENAI_API_KEY 環境変数（または関数引数で渡す）
  - 大量 API 呼び出しにはレート制限対策（リトライ）を実装済み

環境変数の主な一覧
-------------------
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 任意 / デフォルトあり:
  - KABUSYS_ENV: development | paper_trading | live （default: development）
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
  - LOG_LEVEL: INFO（DEBUG/INFO/WARNING/ERROR/CRITICAL）
  - LOG_DIR: ログ保存先（デフォルト logs/）
  - OPENAI_API_KEY: OpenAI を使用する機能で必要
  - PAPER_FILL_MODE: paper_trading 時の約定モード（instant|partial|never|reject）
  - KILL_FLAG_CLEAR_ON_START: 起動時に data/kill.flag を自動クリアするか（'1'で有効、デフォルト '0'）

停止 / Kill Switch
------------------
- ExecutionEngine 停止フラグ:
  - data/stop_requested.flag を作成すると実行中のエンジンが停止します（run_execution/run_monitoring が使用）。
- Kill Switch:
  - RiskMonitor 等で重大な条件が検出された場合、data/kill.flag に理由を書き込み ExecutionEngine に停止を促します。
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag が自動クリアされますが、本番では 0 を推奨します。

ログ
----
- ログは setup_logging により stdout とファイル（logs/<app_name>.log）に出力されます。
- 日次ローテーション（30世代保持）が設定されています。
- LOG_DIR 環境変数や setup_logging の引数で変更可能です。

ディレクトリ構成（主要ファイル）
------------------------------
以下は主要モジュールの簡略ツリー（src/kabusys 配下）です。重要な役割を併記します。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py  — ペーパートレ検証レポート
  - ai/
    - __init__.py
    - news_nlp.py            — ニュースセンチメント（OpenAI）
    - regime_detector.py     — 市場レジーム判定（OpenAI + ETF MA）
  - monitoring/
    - monitoring_db.py      — SQLite の監視 DB 永続層
    - monitoring_engine.py  — 複数モニタの統合ループ
    - system_monitor.py     — システム / データ鮮度監視
    - trade_monitor.py      — （発注ログチェック）※実装参照
    - risk_monitor.py       — ドローダウン・ポジション上限監視
    - kill_switch.py        — kill.flag 制御
    - alert_manager.py      — （通知管理）※実装参照
  - execution/
    - execution_engine.py   — ExecutionEngine 本体（起動/セッション管理）
    - broker_factory.py     — ブローカークライアント生成
    - order_manager.py
    - order_repository.py
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
    - logging_setup.py      — ログ設定ユーティリティ
    - process_priority.py   — プロセス優先度 / CPU affinity 設定
    - __init__.py
  - data/ (実行時に生成される想定)
    - monitoring.db (default)
    - paper_trading.db (paper)
    - stop_requested.flag
    - kill.flag
    - execution.pid

注意事項 / 運用のヒント
-----------------------
- 本番環境（KABUSYS_ENV=live）では設定（LINE 通知など）を慎重に確認してください。validate_config で警告が出ます。
- .env は機密情報を含むため、Git 管理下に置かないでください。
- OpenAI API 呼び出しはコストとレート制限に注意して運用してください（news_nlp と regime_detector はリトライ・バッチ化を実装）。
- ログディレクトリの作成に失敗した場合はファイル出力が無効化され、標準出力のみになります。
- データ鮮度チェックや Kill Switch は自動発動のリスクがあるため、本番では監視と通知設定（LINE 等）を整備してください。

貢献 / 開発
------------
- ローカルでは KABUSYS_ENV=development を使い、ペーパートレードや AI 呼び出しは限定してテストしてください。
- モジュール単位で実行できるように設計されています。ユニットテストは各モジュールの純粋関数群（portfolio/*.py, research/*.py など）に対して書きやすい構造です。

以上。必要があれば特定コマンドの詳細、.env.example のサンプル、あるいは依存関係の正確な一覧を追加します。どの情報を追加しますか？