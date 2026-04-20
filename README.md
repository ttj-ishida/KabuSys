KabuSys
======

日本株向けの自動売買 / リサーチ基盤ライブラリ群です。  
このリポジトリは、ExecutionEngine（発注実行）、Monitoring（システム/取引監視）、ポートフォリオ構築・サイズ決定、ファクター計算、AI（ニュースNLU／レジーム判定）など複数コンポーネントで構成されています。

概要
----
- プロジェクト名: KabuSys
- 目的: 日本株の自動売買システムとそれを支える監視・リサーチ機能の提供
- バージョン: 0.1.0（src/kabusys/__init__.py）
- 主な技術スタック: Python、SQLite、DuckDB、OpenAI（オプション）、psutil

主な特徴（機能一覧）
-----------------
- ExecutionEngine
  - 本番／ペーパートレード切替（KABUSYS_ENV により挙動を変更）
  - ブローカークライアント抽象化（モック／実ブローカーの切替）
  - 注文管理、リスク管理、リコンシリエーション機能を統合してセッション実行

- Monitoring
  - システム稼働・データ鮮度監視（CPU、メモリ、ディスク、プロセス生存確認）
  - 取引ログ／滞留注文／約定異常検出
  - リスク監視（ドローダウン、ポジション上限）
  - Kill Switch（条件により data/kill.flag を書き込み、Execution を停止）
  - SQLite ベースの監視DB（初回起動時にスキーマ自動作成・マイグレーション）

- Portfolio（ポートフォリオ構築）
  - 候補選定（スコア順）
  - 等金額・スコア加重の重み計算
  - セクター上限適用、レジーム乗数
  - 発注株数決定（リスクベース / 等配分 / スコア配分、単元株丸め、aggregate cap）

- Research
  - Momentum / Volatility / Value 等のファクター計算（DuckDB 経由）
  - 将来リターン計算、IC（スピアマン）計算、ファクター統計サマリ

- AI（任意）
  - ニュースのセンチメント分析（OpenAI を用いたニュースNLU -> ai_scores）
  - マクロニュース＋MA200乖離を合成した市場レジーム判定
  - OpenAI API 呼び出し部はリトライ・バリデーション等の堅牢化あり

- 便利ツール
  - .env 対話式ウィザード（python -m kabusys.config_setup）
  - 設定検証 CLI（python -m kabusys.validate_config）
  - Paper Trading 検証レポート生成（python -m kabusys.tools.paper_verification_report）

セットアップ手順
----------------

1. Python 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存ライブラリのインストール
   - 必要最低限（例）:
     - duckdb
     - psutil
     - openai (AI 機能を使う場合)
     - PyYAML (validate_config の YAML 検証を有効化する場合)
   - 例:
     - pip install duckdb psutil openai PyYAML

   ※ requirements.txt がある場合はそれを利用してください（本リポジトリには同梱されていない場合があります）。

3. プロジェクトルートに .env を配置
   - 対話式ウィザード:
     - python -m kabusys.config_setup
     - これにより .env が生成されます（.env は絶対に Git 管理下に置かないでください）。
   - 必須環境変数（例）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - （OpenAI を使う場合）OPENAI_API_KEY を環境変数に設定

4. 設定の検証（任意）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります。

5. データ / ログ ディレクトリ
   - デフォルトで以下を使用します（.env で上書き可）
     - data/        （SQLite, pid, flag 等）
     - logs/        （ログファイル）
   - ログディレクトリは環境変数 LOG_DIR で変更できます。

実行方法（使い方）
-----------------

- ExecutionEngine 起動
  - 本番・開発・ペーパーは KABUSYS_ENV で制御:
    - KABUSYS_ENV=development
    - KABUSYS_ENV=paper_trading
    - KABUSYS_ENV=live
  - 起動:
    - python -m kabusys.run_execution
  - ペーパートレード:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient が使用され、デフォルトで data/paper_trading.db に記録します（本番 DB と完全分離）。
  - 実行開始前に data/stop_requested.flag が存在すると起動をスキップします（停止フラグ）。
  - 実行中に停止したい場合は data/stop_requested.flag を作成すると、ループ検出後に安全停止します。

- Monitoring 起動
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を設定可能（デフォルト 60 秒）。
    - 例: export MONITOR_POLL_INTERVAL=30
  - 起動:
    - python -m kabusys.run_monitoring
  - 監視は Settings.sqlite_path の DB（monitoring DB）を用います（run_monitoring は環境にかかわらず sqlite_path を使用する点に注意）。
  - Monitoring はシステム状態・取引・リスクを定期チェックし、条件に応じて data/kill.flag を生成して Execution を停止させる仕組みがあります。

- Kill Switch / 停止
  - KillSwitch は監視により data/kill.flag を書き込み、ExecutionEngine に停止指示を与えます。
  - 手動で停止させたい場合:
    - data/stop_requested.flag を作成すると run_execution/run_monitoring のループが検出して終了します。
  - kill.flag を起動時に自動クリアしたい場合は .env の KILL_FLAG_CLEAR_ON_START を 1 に設定できます（本番では 0 推奨）。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

環境変数（主なもの）
-------------------
（.env で設定、.env.local で上書き可能。OS 環境変数が優先されます）

- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- システム / DB
  - KABUSYS_ENV: development | paper_trading | live
  - DUCKDB_PATH: デフォルト data/kabusys.duckdb
  - SQLITE_PATH: 監視 DB（monitoring.db）デフォルト data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード用 DB（デフォルト data/paper_trading.db）
  - PID_FILE_PATH: 実行 PID ファイル（デフォルト data/execution.pid）
  - KILL_FLAG_PATH: kill.flag のパス（デフォルト data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアする (0/1)

- ロギング
  - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）
  - LOG_DIR: ログ出力先ディレクトリ（デフォルト logs/）

- Monitoring
  - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring 用。1 以上。デフォルト 60）

- Paper Trading 挙動
  - PAPER_FILL_MODE: instant | partial | never | reject（ペーパートレードの約定挙動。デフォルト "instant"）

- OpenAI
  - OPENAI_API_KEY: AI 機能（news_nlp, regime_detector）を使う場合に必要

注意点 / 実装上の挙動
--------------------
- run_monitoring は KABUSYS_ENV にかかわらず Settings.sqlite_path（監視 DB）を使用します（監視ログは常に本番向け DB）。
- run_execution は KABUSYS_ENV=paper_trading の場合、paper_sqlite_path を使ってペーパートレード DB として完全分離します。
- ログ設定は kabusys.utils.logging_setup.setup_logging を通じて共通化されています。ファイル出力は logs/<app_name>.log に日次ローテーションで出力されます（デフォルト 30 日保持）。
- process priority の設定（高優先度化）を起動時に行います（psutil に依存し権限不足時は警告でスキップされます）。
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml を探索）を基準に行われます。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1。

ディレクトリ構成（抜粋）
---------------------
プロジェクト内主要ファイル・ディレクトリの例（src/kabusys をベースに記載）:

- src/
  - kabusys/
    - __init__.py
    - config.py                # 環境変数読み込み / Settings
    - config_setup.py          # .env 対話式ウィザード
    - validate_config.py       # 設定検証 CLI
    - run_execution.py         # ExecutionEngine 起動スクリプト
    - run_monitoring.py        # Monitoring 起動スクリプト
    - tools/
      - paper_verification_report.py
    - execution/
      - execution_engine.py
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - risk_manager.py
      - broker_factory.py
    - monitoring/
      - monitoring_db.py
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
    - ai/
      - news_nlp.py
      - regime_detector.py
    - utils/
      - logging_setup.py
      - process_priority.py

- data/   （実行時に使用される SQLite / flag / pid などの保存先）
- logs/   （ログファイル出力先、デフォルト）

サンプル .env（最低限）
---------------------
以下は参考例です。必ず自身の機密値で置き換えてください。

JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_api_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-...

便利なコマンドまとめ
-------------------
- .env を作る（ウィザード）
  - python -m kabusys.config_setup

- 環境設定を検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行エンジン起動
  - python -m kabusys.run_execution

- 監視プロセス起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL を環境変数で調整可能

- Paper Trading レポート
  - python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD
  - --db で DB パスを指定可能

運用上の注意
------------
- .env には機密情報を含むため、必ず .gitignore に設定して Git にコミットしないでください。
- 本番運用時は KABUSYS_ENV=live とし、LINE 通知等の本番向け設定を確認してください（validate_config に本番ガードあり）。
- kill.flag / stop_requested.flag の取り扱いに注意してください。自動クリアは危険（本番では無効化推奨）。

サポート / 開発者向けメモ
-------------------------
- DuckDB を用いたリサーチ（prices_daily / raw_financials 等）実行時は DuckDB のテーブルスキーマに合わせてデータを用意してください。
- AI 機能（news_nlp, regime_detector）は OpenAI API を使用します。API レートや料金に注意してください。失敗時はフォールバック動作（スコア 0.0 等）しますが、挙動を理解した上で利用してください。
- YAML 検証を有効にするには PyYAML をインストールしてください（validate_config が config/*.yaml のパースチェックを行います）。

以上が本リポジトリの README です。必要であれば起動スニペット、CI 用設定例、さらに詳細な API リファレンス（各モジュールの公開関数/クラス）を付け加えられます。どの部分を詳述したいか教えてください。