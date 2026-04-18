README — KabuSys（日本株自動売買システム）
======================================

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤を想定した Python パッケージです。
主な目的は以下です。
- 発注実行エンジン（ExecutionEngine）の起動・管理（実口座 / ペーパートレード対応）
- システム監視（モニタリングループ、Kill Switch、アラート連携）
- ポートフォリオ構築（候補選定・重み算出・ポジションサイズ算出）
- ファクター計算・リサーチユーティリティ（DuckDB を用いた時系列計算）
- ニュースの NLP スコアリング（OpenAI を用いたセンチメント集約）
- 各種 CLI ツール（.env ウィザード、設定検証、Paper Trading 検証レポート）

主な機能
--------
- Execution 起動スクリプト（run_execution.py）
  - KABUSYS_ENV に応じて本番 / ペーパートレード DB を切替
  - ブローカークライアントのファクトリ、Order 管理、Risk 管理を組み立てて実行
  - data/stop_requested.flag による安全停止、PIDファイル出力

- Monitoring 起動スクリプト（run_monitoring.py）
  - SystemMonitor を定期ポーリングして system_status 等を記録
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）
  - 監視 DB（SQLite）への永続化、duckdb 連携

- monitoring サブモジュール
  - monitoring_db: SQLite スキーマ作成・読み書き API（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor: CPU/メモリ/DISK、データ鮮度、実行プロセス生存をチェック
  - risk_monitor: ドローダウン・ポジション上限監視とリスクログ記録
  - kill_switch: 条件により data/kill.flag を書き込み Execution を止める仕組み
  - monitoring_engine: 各 Monitor をまとめてポーリングし、アラート送信を行う（AlertManager は別実装想定）

- portfolio サブモジュール（純粋関数）
  - 銘柄選定: select_candidates（スコア順で上位を選択）
  - 重み計算: calc_equal_weights, calc_score_weights
  - ポジションサイズ算定: calc_position_sizes（risk_based / equal / score）
  - セクター制約・レジーム乗数: apply_sector_cap, calc_regime_multiplier

- research サブモジュール（DuckDB 前提）
  - calc_momentum / calc_volatility / calc_value: prices_daily/raw_financials からファクターを計算
  - calc_forward_returns, calc_ic, factor_summary: 特徴量評価・IC 計算・統計要約

- ai サブモジュール
  - news_nlp.score_news: raw_news を集約して OpenAI に投げ、ai_scores を書き込む（スコア ±1.0）
  - regime_detector.score_regime: ETF 1321 の MA とマクロニュースを組み合わせて市場レジーム判定（bull/neutral/bear）
  - API 呼び出しはリトライ・フォールバック設計（失敗時は安全値で継続）

- ツール
  - config_setup: .env 作成/更新の対話ウィザード（python -m kabusys.config_setup）
  - validate_config: .env と config/*.yaml の事前チェック（python -m kabusys.validate_config）
  - paper_verification_report: ペーパートレード DB から検証レポートを生成（python -m kabusys.tools.paper_verification_report）

セットアップ手順
----------------
前提: Python 3.10 以上を推奨（型記法や構文に依存）

1. リポジトリを取得
   - git clone ... またはソースを展開

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  または  .venv\Scripts\activate

3. 依存パッケージをインストール
   - 必要最低限:
     - duckdb
     - psutil
     - openai
   - 任意（設定検証で YAML を検証したい場合）:
     - PyYAML
   - 例:
     - pip install duckdb psutil openai PyYAML

4. .env の作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - もしくは .env.example を参考に手動作成
   - 必須環境変数（最低限設定が必要）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 主要な環境変数（一部）:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用）
     - LOG_LEVEL: DEBUG / INFO / ...
     - OPENAI_API_KEY: OpenAI を使う場合必須
     - PAPER_FILL_MODE: instant | partial | never | reject（ペーパートレード挙動）
     - MONITOR_POLL_INTERVAL: 監視ループの秒間隔（run_monitoring 実行時に参照）
     - KILL_FLAG_CLEAR_ON_START: 1 にすると起動時に data/kill.flag を自動クリア（本番では 0 推奨）

5. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - 警告を厳格に扱う場合: python -m kabusys.validate_config --strict

6. データディレクトリの準備
   - data/ 以下に SQLite / PID / フラグファイル等が作成されます。通常は自動作成されますがディレクトリ権限に注意してください。

基本的な使い方
---------------
- Execution（発注エンジン）起動
  - KABUSYS_ENV によって本番/ペーパーが切り替わります（paper_trading は専用 DB に記録）
  - 実行:
    - python -m kabusys.run_execution
  - 停止:
    - data/stop_requested.flag を作成すると安全に停止します（スクリプトは定期的にこのフラグを監視）

- Monitoring（監視ループ）起動
  - 実行:
    - python -m kabusys.run_monitoring
  - ポーリング間隔変更:
    - 環境変数 MONITOR_POLL_INTERVAL=30 などで秒数を上書き
  - 停止:
    - data/stop_requested.flag を作成、または KeyboardInterrupt（Ctrl+C）

- .env ウィザード
  - python -m kabusys.config_setup
  - 生成・更新後は必ず git にコミットしない（.env は秘密情報を含む）

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も終了コード 1 にする

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH または 環境変数 PAPER_TRADING_SQLITE_PATH

注意事項 / 運用メモ
------------------
- ログ:
  - デフォルトで logs/<app_name>.log（TimedRotatingFileHandler、日次ローテーション 30 日保持）と stdout に出力されます。
  - setup_logging(app_name="execution") でファイル名が決まります。LOG_DIR 環境変数で保存先を変更できます。

- プロセス優先度:
  - 起動スクリプトは set_process_priority("high") を呼び出します。psutil の権限により失敗することがあります（警告ログのみ）。

- DB:
  - monitoring は常に settings.sqlite_path（デフォルト data/monitoring.db）を使用します。paper_trading モードでは paper_sqlite_path を使用して本番 DB と完全に分離します。
  - DuckDB（data/kabusys.duckdb）はリサーチ・ファクター計算用途です。

- Kill / Stop フラグ:
  - 実行中の安全停止は data/stop_requested.flag（スクリプト監視）および data/kill.flag（KillSwitch が Execution を停止するために使用）を利用します。
  - KILL_FLAG_CLEAR_ON_START を 1 にすると起動時に自動で kill.flag をクリアしますが、本番では危険なので 0 推奨。

- OpenAI:
  - news_nlp.score_news と regime_detector.score_regime は OpenAI API を使用します。API キーは OPENAI_API_KEY 環境変数か引数で渡してください。
  - API 呼び出しはリトライ設計がありますが、API 料金やレート制限に注意してください。

ディレクトリ構成（抜粋）
---------------------
- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数 / 設定読み込みロジック
  - config_setup.py               — .env ウィザード CLI
  - validate_config.py            — 設定検証 CLI
  - run_execution.py              — ExecutionEngine 起動スクリプト
  - run_monitoring.py             — Monitoring ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - execution/                     — 実行エンジン関連（broker, engine, order_manager 等）※詳細実装は省略
  - monitoring/
    - monitoring_db.py            — SQLite スキーマ + 永続化 API
    - system_monitor.py
    - risk_monitor.py
    - trade_monitor.py            — (参照あり、コードベースに存在)
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py            — （AlertManager を差し替えて通知を実装）
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

サンプルコマンドまとめ
---------------------
- .env 作成:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
- Execution 起動:
  - python -m kabusys.run_execution
- Monitoring 起動:
  - python -m kabusys.run_monitoring
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

ライセンス / セキュリティ
-----------------------
- .env は API キーやパスワードを含みます。絶対に Git 等で公開リポジトリにコミットしないでください。
- 本リポジトリのコードは参考実装です。実際の自動売買を行う際は入念なテスト、バックテスト、リスク審査を行ってください。

補足
----
この README はコードベースの主要なモジュールから情報を抜粋して作成しています。実際の運用では各サブモジュール（ExecutionEngine や BrokerClient 等）の実装・設定を確認のうえ環境を整備してください。質問があればどの部分の説明を詳しく出力するか指示してください。