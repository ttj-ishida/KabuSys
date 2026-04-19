README
======

概要
----
KabuSys は日本株向けの自動売買/リサーチ基盤です。本リポジトリには以下の主要機能が含まれます。

- 実行エンジン（ExecutionEngine）: ブローカーと連携して発注・約定管理を行う（本番 / ペーパートレード対応）。
- 監視コンポーネント（Monitoring）: システム稼働状況、注文ログ、リスク指標などを定期的に収集・永続化し、Kill Switch を発動可能。
- ポートフォリオ構築ユーティリティ: 候補選定、重み計算、ポジションサイズ算出、セクター制限など純粋関数群。
- リサーチ / ファクター計算: DuckDB を使ったファクター計算、将来リターン / IC 計算など。
- AI 補助機能: ニュースセンチメント解析（OpenAI）や市場レジーム判定を行うモジュール。
- ユーティリティ: .env 対話ウィザード、設定検証 CLI、ログ設定ユーティリティ 等。

特徴
----
- 開発/ペーパー/本番（development / paper_trading / live）環境を environment 変数で切替可能
- Paper Trading は本番 DB と分離（data/paper_trading.db がデフォルト）
- DuckDB を分析用途に利用、SQLite を監視・発注ログ用に使用
- OpenAI を使ったニュースNLP（任意）とレジーム判定（任意）
- 標準的なログ設定（コンソール + 日次ローテートファイル）
- Kill Switch（data/kill.flag）による安全停止機構
- テストしやすい純粋関数設計（ポートフォリオ・リサーチモジュール）

必要な依存パッケージ（主要）
- Python 3.10+
- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML（設定 YAML の内容検証を行う場合）
（requirements.txt がある場合はそれを利用してください）

セットアップ手順
----------------

1. リポジトリをクローンして仮想環境を作成・有効化します。
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate  (Unix)
     - .venv\Scripts\activate     (Windows)

2. 依存パッケージをインストールします。
   - 例（requirements.txt がない場合）:
     - pip install duckdb psutil openai pyyaml

3. .env の作成（対話ウィザード推奨）
   - python -m kabusys.config_setup
   - 主要な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN=your_jquants_token_here
     - KABU_API_PASSWORD=your_kabu_password_here
     - KABUSYS_ENV=development|paper_trading|live
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - OPENAI_API_KEY=sk-... (AI 機能を利用する場合)
     - LOG_LEVEL=INFO

   補足:
   - 自動で .env を読み込む仕組みが有効です（プロジェクトルートに .env/.env.local があると自動読み込み）。
   - 自動読み込みを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

4. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗（exit 1）になります。

使い方
----

基本的な起動・実行例を示します。いずれもプロジェクトルート（pyproject.toml か .git がある場所）から実行してください。

1. 監視ループを起動（Monitoring）
   - python -m kabusys.run_monitoring
   - 環境変数:
     - MONITOR_POLL_INTERVAL: ポーリング間隔（秒、デフォルト 60）
   - 監視は常に監視用の sqlite_path（Settings.sqlite_path）を使用します。
   - 停止方法:
     - data/stop_requested.flag を作成するとループが安全終了します（stop フラグファイル）。
     - Ctrl+C（KeyboardInterrupt）でも停止可能。

2. 実行エンジン（ExecutionEngine）起動
   - python -m kabusys.run_execution
   - KABUSYS_ENV が paper_trading の場合、MockBrokerClient を使い PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録し本番 DB と分離します。
   - 起動時、data/stop_requested.flag が既に存在する場合は起動せずに終了します。
   - 実行中に停止させたい場合は data/stop_requested.flag を作成するとエンジンが stop() を呼んで安全停止します。
   - ExecutionEngine は PID ファイル（Settings.pid_file_path。デフォルト data/execution.pid）を管理します。

3. Paper Trading 検証レポート生成
   - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
   - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db
   - 出力: 稼働率、注文成功率、送信率、レイテンシ（P95）等のサマリと PASS/FAIL 判定

4. AI 関連（ニュースNLP / レジーム判定）
   - OPENAI_API_KEY 環境変数を設定してください（もしくは各関数に api_key を渡す）。
   - ニューススコア付与:
     - 呼び出し API: kabusys.ai.score_news(conn, target_date, api_key=None)
     - DuckDB 接続（conn）を渡して実行します。コマンドラインの専用エントリはありません（バッチ実行スクリプト等で利用）。
   - レジーム判定:
     - 呼び出し API: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

5. 設定・ファイルの注意点
   - Kill Switch: Settings.kill_flag_path（デフォルト data/kill.flag）により ExecutionEngine に強制停止シグナルを送ることができます（KillSwitch が書き込む）。
   - ログ: kabusys.utils.logging_setup.setup_logging を各起動スクリプトで呼び出しています。ログファイルは LOG_DIR（デフォルト logs/）に app_name.log として日次ローテートで保存されます。
   - DB マイグレーション: monitoring の初期化関数 init_monitoring_db が簡単なテーブル作成・カラム追加マイグレーションを行います（冪等）。

主要ファイル / ディレクトリ構成
---------------------------

（src/kabusys 以下をプロジェクトの主要ソースと想定）

- kabusys/
  - __init__.py
  - config.py
    - 環境変数取り扱い・Settings クラス（.env 自動ロード、必須変数チェック等）
  - config_setup.py
    - 対話式 .env 作成ウィザード
  - validate_config.py
    - 起動前チェック CLI（環境変数・パス・config/*.yaml の存在チェック）
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプト（paper_trading モード対応）
  - monitoring/
    - monitoring_db.py
      - monitoring 用 SQLite スキーマ作成と永続化ラッパー（MonitoringDB）
    - system_monitor.py
      - システムリソース・データ鮮度・プロセス状態を監視する SystemMonitor
    - trade_monitor.py
      - （ソース内にあり）注文ログの監視・滞留検出等
    - risk_monitor.py
      - ドローダウン・ポジション数などを監視する RiskMonitor
    - kill_switch.py
      - Kill Switch ロジック（flag を書き込む）
    - monitoring_engine.py
      - 複数 Monitor を束ねる Engine（run / run_once）
    - alert_manager.py
      - （アラート送信の抽象化。LINE などへ通知を行う想定）
  - execution/
    - broker_factory.py, execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py
      - 実行エンジン、ブローカー抽象、注文管理、リスク管理等（本体）
  - portfolio/
    - portfolio_builder.py
    - risk_adjustment.py
    - position_sizing.py
    - 純粋関数群で候補選定・重み・サイズ算出・セクター制限を実装
  - research/
    - factor_research.py
      - モメンタム/ボラティリティ/バリュー等のファクター計算（DuckDB 接続を受ける）
    - feature_exploration.py
      - 将来リターン計算、IC（情報係数）、統計サマリ等
  - ai/
    - news_nlp.py
      - OpenAI を用いたニュースセンチメント解析と ai_scores 書き込みロジック
    - regime_detector.py
      - ETF MA とマクロニュースから市場レジーム判定（OpenAI を利用）
  - tools/
    - paper_verification_report.py
      - ペーパートレード結果の検証レポート出力スクリプト
  - utils/
    - logging_setup.py
      - ログ設定ユーティリティ（コンソール + 日次ファイルローテーション）
    - process_priority.py
      - psutil を使ったプロセス優先度 / CPU affinity 設定ユーティリティ

補足・運用上の注意
-----------------
- production（KABUSYS_ENV=live）では LINE の通知設定（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）等を必ず確認してください。validate_config は live に対して追加の警告を出します。
- Kill Switch（data/kill.flag）を不用意に自動クリアする設定（KILL_FLAG_CLEAR_ON_START=1）は本番で危険です。デフォルトは 0（クリアしない）。
- OpenAI など外部 API を使う機能は API キーが必要です。API 呼び出しはリトライ・フォールバックロジックを備えていますが、失敗時は機能がスキップされます（フェイルセーフ設計）。
- ログディレクトリ作成に失敗するとファイル出力は無効化され、コンソール出力のみになります。

貢献 / 開発
-----------
- まずは .env を対話ウィザードで作成し、python -m kabusys.validate_config で問題がないことを確認してください。
- 単体モジュールは純粋関数で設計されている箇所が多く、ユニットテストを書きやすい構成になっています。
- DuckDB を使う関数群は基本的に prices_daily / raw_financials 等のテーブルを前提としています。テスト用に小さな DuckDB を作成してテストデータを投入してください。

ライセンス / バージョン
-----------------------
- パッケージバージョンは kabusys.__version__ = "0.1.0"

以上。必要であれば README にサンプルの .env テンプレートや起動スクリプト（systemd / supervisor）サンプル、詳細なログ・DB スキーマ説明を追加できます。どの情報を拡張したいか教えてください。