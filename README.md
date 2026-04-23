# KabuSys

日本株自動売買システムのサンプル実装リポジトリ（ライブラリ兼実行スクリプト群）。  
このREADME はソースツリー（src/kabusys）に含まれる主要なモジュールの概要、セットアップ方法、基本的な使い方、ディレクトリ構成をまとめたものです。

---

## プロジェクト概要

KabuSys は次の役割を持つコンポーネント群から構成されます。

- ExecutionEngine: 発注・注文管理・リスク管理を行うエンジン（本番 / ペーパートレード切替あり）
- Monitoring: システム状態・注文状態・リスクを定期監視し、Kill Switch（停止フラグ）やアラートを管理
- Research / Portfolio: ファクター計算、ポートフォリオ構築・リスク調整、ポジションサイジング用の純粋関数群
- AI 補助: ニュースを LLM（OpenAI）で評価しスコアを生成、レジーム判定など
- ユーティリティ: 設定読み込み、対話式 .env ウィザード、ログ設定、プロセス優先度制御 等

設計上の特徴:
- 環境変数 / .env による設定管理
- DuckDB（分析用）＋SQLite（監視・発注ログ等）を使用
- 本番（live）/ ペーパー（paper_trading）/ 開発（development）を切替可能
- OpenAI（gpt-4o-mini 等）を利用した NLP 処理を一部に採用（API キー必須）

---

## 主な機能一覧

- Execution
  - ExecutionEngine 起動スクリプト（python -m kabusys.run_execution）
  - Broker クライアントの抽象化（本番・Mock／ペーパートレード対応）
  - OrderManager / RiskManager / Reconciler 等による発注フロー管理
- Monitoring
  - SystemMonitor：CPU/メモリ/ディスク・データ鮮度・実行プロセスの監視
  - TradeMonitor：注文の滞留・約定異常の検出（trade_logs 等）
  - RiskMonitor：ドローダウン・ポジション上限の監視とアラート／Kill Switch のトリガ
  - MonitoringEngine：上記を束ねてポーリング
- Research / Portfolio
  - ファクター計算（Momentum / Value / Volatility）
  - 将来リターン計算・IC（Information Coefficient）等の解析ツール
  - 候補選定、重み付け、ポジションサイズ計算、セクター制限、レジーム乗数
- AI
  - news_nlp: ニュース記事集合を LLM に投げ、銘柄別センチメントを ai_scores に永続化
  - regime_detector: ma200 とマクロニュースの LLM スコアを合成して市場レジーム判定
- ツール
  - 対話式 .env 設定ウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py）
  - Paper Trading 検証レポート生成（tools/paper_verification_report.py）
- ユーティリティ
  - logging_setup: 一貫したログ設定（コンソール + 日次ローテーション）
  - process_priority: 優先度 / CPU affinity 設定

---

## セットアップ手順（ローカル開発向け）

前提
- Python 3.10 以上（ソース内で PEP 604 の型 | を使用）
- Git リポジトリのルートに合わせて動作する（.env 自動ロードはプロジェクトルート検出に .git / pyproject.toml を使用）

1. 仮想環境を作成・有効化（推奨）
   - Unix/macOS:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows:
     ```
     python -m venv .venv
     .venv\Scripts\activate
     ```

2. 必要なパッケージをインストール
   - 最低限の依存例:
     ```
     pip install duckdb psutil openai
     ```
   - 設定検証で YAML を検証したい場合:
     ```
     pip install PyYAML
     ```
   - （パッケージ管理ファイルがない場合は上記を個別導入）

3. 環境変数の初期設定
   - 対話式ウィザードで .env を作成するのが簡単です:
     ```
     python -m kabusys.config_setup
     ```
   - もしくはリポジトリに .env.example がある場合はそれを参考に .env を作成してください。
   - 主要な必須環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV（development / paper_trading / live）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 時の専用 DB、デフォルト: data/paper_trading.db）
     - PAPER_FILL_MODE（paper_trading の埋め方: instant|partial|never|reject）
     - LOG_LEVEL（INFO 等）
   - 自動ロードを無効にする場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

4. 設定検証
   - 基本検証:
     ```
     python -m kabusys.validate_config
     ```
   - 警告も失敗にしたい（--strict）:
     ```
     python -m kabusys.validate_config --strict
     ```

5. データディレクトリの準備
   - デフォルトの DB / log ディレクトリ等は起動時に自動生成される場合がありますが、明示的に用意することを推奨します:
     ```
     mkdir -p data logs
     ```

---

## 使い方（主要エントリポイント）

- ExecutionEngine（発注エンジン）を起動
  - 本番 / ペーパーは KABUSYS_ENV に依存。paper_trading の場合は MockBrokerClient を使用し、Paper 用 DB（PAPER_TRADING_SQLITE_PATH）に記録されます。
  - 起動:
    ```
    python -m kabusys.run_execution
    ```
  - 停止:
    - 外部から停止させる場合はプロジェクトルートの data/stop_requested.flag を作成するとエンジンが検知して終了します。
    - Execution が PID を書き込むファイル: data/execution.pid（設定によりパス変更可能）

- Monitoring（監視ループ）を起動
  - 起動:
    ```
    python -m kabusys.run_monitoring
    ```
  - ポーリング間隔は環境変数で上書き可能:
    ```
    export MONITOR_POLL_INTERVAL=30  # 秒
    python -m kabusys.run_monitoring
    ```
  - 注意:
    - Monitoring は環境にかかわらず本番 sqlite_path（SQLITE_PATH）を使用して監視ログを記録します。
    - 停止フラグ: run_monitoring では data/stop_requested.flag の存在でループ終了します。

- .env 設定ウィザード
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート出力
  - default DB パスは環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - または指定:
  ```
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI 機能（ニュース NLP / レジーム判定）
  - OPENAI_API_KEY を設定し、該当モジュール関数を呼び出すことでスコアリングを行います（スクリプト単体の CLI はありませんが、ライブラリ関数を使って呼び出せます）。
  - 例: kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime

---

## 重要なファイル・挙動メモ

- stop / kill フラグ
  - data/stop_requested.flag: run_* スクリプトが存在をチェックして安全にループを終了します
  - data/kill.flag: Monitoring の KillSwitch により ExecutionEngine 停止命令として書き込まれる（存在するかを Execution 起動前にチェック）
- Paper Trading
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して data/paper_trading.db に取引ログを記録し、本番 DB と完全に分離されます
  - PAPER_FILL_MODE で約定動作を制御（instant / partial / never / reject）
- ロギング
  - 共通の logging_setup を使い stdout と日次ローテートファイル（logs/<app_name>.log）へ出力します
- プロセス優先度
  - 起動時に set_process_priority("high") を呼び出し、可能な限り高優先度で実行しようとします（失敗しても警告で継続）

---

## ディレクトリ構成（主なファイルの説明）

トップレベル（src/kabusys）:

- __init__.py
  - パッケージ初期化、バージョン等

- run_execution.py
  - ExecutionEngine 起動スクリプト（スレッドでエンジンを起動し stop フラグを監視）

- run_monitoring.py
  - SystemMonitor のポーリングループを起動するスクリプト（MONITOR_POLL_INTERVAL で間隔指定可）

- config.py
  - Settings クラス: 環境変数の読み込み・検証・デフォルトを提供（.env 自動読み込み機能あり）

- config_setup.py
  - 対話式 .env 作成ウィザード

- validate_config.py
  - 起動前の設定検証 CLI（必須環境変数・ファイルパス・YAML パース等）

- monitoring/
  - monitoring_db.py: SQLite による監視ログの永続化層（テーブル作成・CRUD）
  - system_monitor.py: CPU/メモリ/ディスク/プロセス/データ鮮度監視
  - trade_monitor.py: 発注ログの監視（滞留注文、約定異常など）
  - risk_monitor.py: ドローダウン・ポジション数のチェック
  - kill_switch.py: Kill Switch の評価・書き込み
  - monitoring_engine.py: 各 Monitor を束ねる実行ループ
  - alert_manager.py: （アラート送信機能がある場合）LINE などへの通知管理

- execution/
  - execution_engine.py: ExecutionEngine 実装（ターゲット日・セッションの実行）
  - broker_factory.py: BrokerClient の生成（本番 or Mock）
  - order_manager.py / order_repository.py: 注文管理・DB 永続化
  - risk_manager.py: 発注前リスク評価
  - reconciler.py: ブローカー状態と DB の整合性保持

- portfolio/
  - portfolio_builder.py: 候補選定・重み付け
  - position_sizing.py: 株数算出・資金配分・単元丸め
  - risk_adjustment.py: セクター制限・レジーム乗数

- research/
  - factor_research.py: Momentum / Volatility / Value 等ファクター計算（DuckDB 利用）
  - feature_exploration.py: 将来リターン・IC・統計サマリ等の解析ユーティリティ

- ai/
  - news_nlp.py: ニュース記事を LLM でスコアリングして ai_scores に書き込む
  - regime_detector.py: ma200 とマクロニュースを合成して market_regime を算出・永続化

- tools/
  - paper_verification_report.py: Paper Trading の検証レポート生成（稼働率・約定率・レイテンシ等）

- utils/
  - logging_setup.py: ログ初期化ユーティリティ
  - process_priority.py: 優先度 / CPU affinity 設定
  - （その他ユーティリティ関数）

---

## よく使う環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN — J-Quants API（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABUSYS_ENV — execution モード（development / paper_trading / live）
- OPENAI_API_KEY — OpenAI API キー（AI 機能で必要）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（default: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（default: data/paper_trading.db）
- PAPER_FILL_MODE — ペーパートレード埋め方（instant/partial/never/reject）
- MONITOR_POLL_INTERVAL — monitoring のポーリング秒間隔（default: 60）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）

---

## 運用上の注意

- 本番運用時は KABUSYS_ENV=live に設定し、LINE通知や Kill Switch の設定を確認してください。validate_config の警告を無視しないでください。
- .env は機密情報を含むため絶対に Git にコミットしないでください（config_setup でも注記あり）。
- OpenAI API を利用する処理は API コストとレート制限に注意してください（内部でリトライとバッチ処理を実装していますが、運用上の制約は別途検討してください）。
- プロセス優先度や CPU affinity の設定はプラットフォーム依存で失敗する可能性があるため、ログで警告が出た場合は権限等を確認してください。

---

以上がソースツリーと主要な実行フローの概要です。具体的な API やブローカー実装（本番接続）はプロジェクトに依存するため、利用前に .env と config/*.yaml を整え、validate_config で検証してから起動してください。必要があれば、README を利用方法に合わせてさらに追記します。