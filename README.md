# KabuSys

日本株向け自動売買システムの軽量ライブラリ / 実行スクリプト群。

バージョン: 0.1.0

本リポジトリは、戦略の研究（ファクター計算）、ポートフォリオ構築、発注実行（本番 / ペーパートレード）、監視・アラート、そして一部 AI 支援機能（ニュースセンチメント等）を含むモジュール群で構成されています。

---

## 概要

- DuckDB を分析用 DB、SQLite を監視・発注ログ用 DB として利用します（デフォルトのパスは data ディレクトリ配下）。
- 実行エンジンは KABUSYS_ENV により動作モードを切り替えます（development / paper_trading / live）。
  - paper_trading モードでは MockBroker を利用し、発注履歴は paper_trading 用の専用 SQLite に記録して本番 DB と分離します。
- 監視コンポーネントはシステム・注文・リスクの定期チェックを行い、Kill Switch により必要に応じて ExecutionEngine を停止します。
- News NLP / Regime Detector は OpenAI API（gpt-4o-mini 等）を利用してニュースのセンチメントや市場レジームを評価できます（API キー必要）。

---

## 主な機能一覧

- 実行
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - ペーパートレード時は MockBroker を使用して本番 DB と分離
- 監視
  - System / Trade / Risk の監視、Kill Switch の判定、アラート送信（run_monitoring.py）
  - MONITOR_POLL_INTERVAL によるポーリング間隔変更（デフォルト 60 秒）
- 設定管理
  - .env 対話式ウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py）
- 研究用ツール
  - ファクター計算（momentum / volatility / value 等）
  - 特徴量探索・IC 計算
- ポートフォリオ構築
  - 候補選定、等ウェイト・スコア加重、ポジションサイジング、セクター制限、レジーム乗数
- AI 支援
  - ニュースセンチメント（news_nlp.py）
  - 市場レジーム判定（regime_detector.py）
- ユーティリティ
  - ログ設定（utils/logging_setup.py）
  - プロセス優先度設定（utils/process_priority.py）
- ツール
  - Paper Trading 検証レポート生成（tools/paper_verification_report.py）

---

## セットアップ手順

1. Python 環境準備
   - Python 3.10+ を推奨。
   - 必要パッケージ（例）:
     - duckdb, psutil, openai（AI 機能を使う場合）, PyYAML（設定ファイル検証を行う場合）など。
   - 例（pip）:
     ```
     pip install duckdb psutil openai
     # オプション
     pip install pyyaml
     ```

2. リポジトリのプロジェクトルートで .env を作成
   - 対話式ウィザードを利用:
     ```
     python -m kabusys.config_setup
     ```
   - もしくは .env を手動作成（例）:
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_token
     KABU_API_PASSWORD=your_kabu_password
     KABU_API_BASE_URL=http://localhost:18080/kabusapi
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     KILL_FLAG_CLEAR_ON_START=0
     ```

3. 設定検証（任意）
   ```
   python -m kabusys.validate_config
   # 警告を厳格に扱う場合:
   python -m kabusys.validate_config --strict
   ```

4. データディレクトリ等の自動作成
   - ログディレクトリや data ディレクトリは起動時に自動作成を試みますが、適切な権限を確認してください。

---

## 環境変数（主なもの）

- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 実行モード
  - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
- DB パス
  - DUCKDB_PATH (default: data/kabusys.duckdb)
  - SQLITE_PATH (default: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (paper_trading 用, default: data/paper_trading.db)
- ログ
  - LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL)
  - LOG_DIR (既定: logs/)
- 監視
  - MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔秒、デフォルト 60）
- OpenAI
  - OPENAI_API_KEY（news_nlp, regime_detector を使う場合）
- その他
  - PID_FILE_PATH / KILL_FLAG_PATH 等は Settings 経由で参照、デフォルトは data/ 以下

（詳しくは src/kabusys/config.py の Settings を参照）

---

## 使い方

- ExecutionEngine 起動（発注エンジン）
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合、MockBroker を使い発注は paper_trading DB（PAPER_TRADING_SQLITE_PATH）へ記録され、本番 DB に影響しません。
  - 起動時に data/stop_requested.flag が存在すると起動をスキップします。
  - 実行中は data/execution.pid に PID を書きます。停止は stop flag（監視側から）や kill.flag により行われます。

- Monitoring 起動（監視ループ）
  ```
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒で指定できます（デフォルト 60 秒）。
    ```
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    ```
  - 監視は本番 sqlite_path を使用します（KABUSYS_ENV に依らず）。
  - 監視ループ内で data/stop_requested.flag を検知するとループを終了します。

- 設定ウィザード
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report
  # 期間指定
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB 指定
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI 機能（ニューススコア等）
  - OPENAI_API_KEY を環境変数に設定しておく必要があります。
  - プログラムからは kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime を呼び出します。

---

## 停止 / Kill Switch

- 監視がリスク判定（ドローダウン超過等）を検知すると data/kill.flag を書き込み、Execution 側で検出して停止処理を実行します。
- 手動で停止したい場合や起動制御を行いたい場合は以下のファイルを操作します:
  - data/stop_requested.flag — run_* スクリプトは存在を見て早期終了します（run_execution/run_monitoring 両方で利用）。
  - data/kill.flag — KillSwitch が書き込む停止フラグ。Execution 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定していると起動時に自動クリアされる挙動になります（本番では 0 推奨）。

---

## ロギング

- ログは標準出力（StreamHandler）とファイル（TimedRotatingFileHandler、日次ローテーション・30 日保持）に出力されます。
- デフォルトログディレクトリ: logs/
- ログファイル名: <app_name>.log（例: logs/execution.log, logs/monitoring.log）
- 環境変数 LOG_DIR / LOG_LEVEL で上書き可能。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 配下の主要モジュール一覧と簡単な説明です。

- kabusys/
  - __init__.py — パッケージ定義（__version__）
  - config.py — 環境変数・.env の自動読み込み / Settings 定義
  - config_setup.py — .env 対話ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 発注株数計算
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py — 将来リターン計算・IC・統計
  - ai/
    - news_nlp.py — ニュースセンチメント取得（OpenAI)
    - regime_detector.py — レジーム判定（MA + マクロセンチメント合成）
  - monitoring/
    - monitoring_db.py — SQLite テーブル初期化 / 永続化 API
    - system_monitor.py — システム状態監視・データ鮮度チェック
    - trade_monitor.py —（注文監視ロジック — ファイル内にあり）
    - risk_monitor.py — ドローダウン / ポジション数監視
    - kill_switch.py — kill.flag の評価・操作
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
    - alert_manager.py —（アラート送信管理）
  - execution/
    - execution_engine.py — 発注エンジン本体（EngineConfig 等）
    - order_manager.py, order_repository.py, reconciler.py, risk_manager.py — 実行周りのコンポーネント
    - broker_factory.py — ブローカクライアント生成（Mock / 実実装切替）
  - utils/
    - logging_setup.py — ログ設定ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity
  - data/ （実行時に作成されることが多い）
    - monitoring.db（または指定の SQLITE_PATH）
    - paper_trading.db（paper_trading 用）
    - kill.flag, stop_requested.flag, execution.pid など

（上記はソースベースの抜粋要約です。詳細は該当モジュールの docstring / ソースを参照してください）

---

## 開発メモ / 注意点

- .env は絶対にリポジトリへコミットしないでください（秘密情報を含むため）。
- OpenAI を用いるモジュールは API 利用料が発生します。実行前に API キーとコストを確認してください。
- run_monitoring は監視用 DB（monitoring.db）に常にアクセスします。テスト時でも本番の DB を誤って上書きしないよう注意してください。
- validate_config は PyYAML がない場合、config/*.yaml の中身検証をスキップしますが、存在チェックは行います。
- process priority / cpu affinity の設定はプラットフォーム依存で失敗する可能性があり、失敗時は警告に留まります。

---

## よく使うコマンドまとめ

- 環境設定ウィザード:
  ```
  python -m kabusys.config_setup
  ```
- 設定検証:
  ```
  python -m kabusys.validate_config
  ```
- 実行エンジン起動:
  ```
  python -m kabusys.run_execution
  ```
- 監視起動:
  ```
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```
- ペーパートレード検証レポート:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

README の内容はソース内の docstring をもとに要点をまとめています。必要があれば各モジュール（特に execution_engine、order_manager、alert_manager 等）の詳細仕様や設定例を別ドキュメントとして追加できます。