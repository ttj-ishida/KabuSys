# KabuSys

日本株向けの自動売買システム（ライブラリ / 起動スクリプト群）

このリポジトリは取引エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、リサーチ、AI ベースのニュース解析などを含むモジュール群で構成されています。本 README はローカルセットアップ、主要コンポーネントの使い方、ディレクトリ構成をまとめたものです。

---

## プロジェクト概要

KabuSys は以下を目的としたモジュール群を提供します。

- 株取引の ExecutionEngine（実取引 / ペーパートレード対応）
- システム稼働監視・アラート・Kill Switch
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ算出）
- ファクター計算 / リサーチ（DuckDB を用いた時系列分析）
- ニュース NLP（OpenAI を用いた銘柄別センチメント評価）
- ペーパートレード検証レポート生成ツール

設計上の注意点：
- 設定は環境変数 / .env ファイルから読み込みます（自動ロード機構あり）。
- KABUSYS_ENV により動作モードを変更（development / paper_trading / live）。
- paper_trading モードは本番 DB と分離され、MockBrokerClient を使用します。

---

## 主な機能一覧

- ExecutionEngine 起動スクリプト（run_execution.py）
  - KABUSYS_ENV=paper_trading のときは MockBroker を使い data/paper_trading.db に記録
  - PID ファイル管理・停止フラグ検出（data/execution.pid, data/stop_requested.flag）
  - 高優先度でプロセスを起動（process priority 設定）
- Monitoring（run_monitoring.py）
  - System / Trade / Risk 各種モニタを定期ポーリング
  - MONITOR_POLL_INTERVAL で間隔を変更可能（デフォルト 60 秒）
  - kill.flag の生成（KillSwitch）による ExecutionEngine 停止トリガ
- ポートフォリオ構築
  - 候補選定（スコア降順）、等配分・スコア重み付け、リスク調整（セクター上限等）、ポジションサイズ計算
- リサーチ
  - Momentum, Volatility, Value 等のファクター計算（DuckDB ベース）
  - 将来リターン・IC（情報係数）計算など
- AI
  - ニュース記事を LLM（OpenAI）でスコアリングして ai_scores に保存
  - 市場レジーム判定（ma200 + LLM マクロセンチメントの合成）
- ユーティリティ
  - .env 対話式ウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py）
  - Paper Trading 検証レポート生成スクリプト（tools/paper_verification_report.py）

---

## 前提 / 依存関係

- Python 3.9+（型記法より）
- 以下は主なランタイム依存（用途により不要なモジュールあり）
  - duckdb
  - psutil
  - openai（AI 機能を使う場合）
  - PyYAML（設定 YAML 検証時に推奨）
- SQLite（標準ライブラリ）
- 環境に応じて .env を用意（詳細は下記）

---

## セットアップ手順

1. リポジトリをクローンし、仮想環境を作成・有効化します。
   (例)
   ```
   python -m venv .venv
   source .venv/bin/activate   # Unix/macOS
   .venv\Scripts\activate.bat  # Windows
   ```

2. 依存パッケージをインストールします（プロジェクトの requirements.txt がある場合はそれを使用）。
   例:
   ```
   pip install duckdb psutil openai PyYAML
   ```

3. .env を作成します。簡単な流れ：
   - 対話式ウィザードを使う（推奨）
     ```
     python -m kabusys.config_setup
     ```
   - 生成後、設定内容を検証する：
     ```
     python -m kabusys.validate_config
     ```
   - 自動ロードを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します（テスト用途）。

4. 必要に応じてデータディレクトリを作成：
   ```
   mkdir -p data logs
   ```

---

## 環境変数（主なもの）

以下は重要な環境変数とデフォルト値・説明です。

- KABUSYS_ENV: 実行環境 ("development" / "paper_trading" / "live")。デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabuステーションのベース URL。デフォルト: http://localhost:18080/kabusapi
- DUCKDB_PATH: DuckDB ファイルパス。デフォルト: data/kabusys.duckdb
- SQLITE_PATH: 監視用 SQLite（monitoring DB）パス。デフォルト: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: ペーパートレード時の SQLite（分離 DB）。デフォルト: data/paper_trading.db
- PAPER_FILL_MODE: ペーパートレードの約定モード ("instant" | "partial" | "never" | "reject")。デフォルト: instant
- LOG_LEVEL: ログレベル ("DEBUG"/"INFO"/"WARNING"/"ERROR"/"CRITICAL")。デフォルト: INFO
- LOG_DIR: ログ出力先ディレクトリ。デフォルト: logs/
- OPENAI_API_KEY: OpenAI を使う機能向けの API キー

注意: .env は絶対にリポジトリにコミットしないでください。

---

## 実行方法（主要スクリプト）

- 設定ウィザード（.env を対話生成）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict   # 警告も失敗扱い
  ```

- ExecutionEngine 起動（取引エンジン）
  ```
  python -m kabusys.run_execution
  ```
  動作ポイント:
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して data/paper_trading.db に記録します（本番 DB と分離）。
  - 起動時にプロセス優先度を "high" に設定します。
  - 停止フラグ: data/stop_requested.flag を監視。存在する場合は起動しない / 停止します。
  - PID ファイル: data/execution.pid（Settings.pid_file_path から変更可能）

- Monitoring 起動（定期監視）
  ```
  python -m kabusys.run_monitoring
  ```
  動作ポイント:
  - デフォルトのポーリング間隔は 60 秒。環境変数で上書き可能：
    ```
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    ```
  - 監視は本番 sqlite_path（Settings.sqlite_path）を使用します（環境に依存せず）。
  - 停止フラグ: data/stop_requested.flag を検出するとループを抜けます。

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を明示する場合:
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI 系（プログラム的に利用）
  - ニューススコアリング（ai.news_nlp.score_news）やレジーム判定（ai.regime_detector.score_regime）は DuckDB 接続と target_date を渡して呼び出します。OpenAI API キーは環境変数 OPENAI_API_KEY または引数で渡します。

---

## ログ / DB / フラグファイル

- ログ:
  - デフォルトは logs/ ディレクトリに出力され、ファイルは日次ローテーションされます（30日保持）。ログ名は起動アプリ名（例: execution.log, monitoring.log）。
- SQLite / DuckDB:
  - デフォルト: data/monitoring.db（SQLite）, data/kabusys.duckdb（DuckDB）
  - ペーパートレード専用 DB: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH で上書き可）
- フラグ / PID:
  - 停止全般フラグ（スクリプト間で共有）: data/stop_requested.flag
  - Kill Switch（Execution の停止を指示する）: data/kill.flag（KillSwitch が書き込み）
  - Execution PID ファイル: data/execution.pid

---

## 開発 / テスト時の便利な点

- .env 自動ロード:
  - プロジェクトルートに .env / .env.local があれば自動でロードされます（OS 環境変数が優先）。
  - 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- ロギングの初期化:
  - すべての起動スクリプトは `kabusys.utils.logging_setup.setup_logging(app_name=...)` を呼び出して統一した出力を行います。
- プロセス優先度:
  - `kabusys.utils.process_priority.set_process_priority("high")` により Windows/Linux で概ね高優先度へ設定を試みます（権限により失敗する場合あり）。
- DB スキーママイグレーション:
  - monitoring_db.init_monitoring_db() はテーブル作成と簡易マイグレーション（カラム追加）を行います（冪等）。

---

## ディレクトリ構成

リポジトリの主要なファイル/ディレクトリと役割:

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数の読み込み / Settings クラス
  - config_setup.py
    - .env 対話式ウィザード
  - validate_config.py
    - 設定検証 CLI
  - run_execution.py
    - ExecutionEngine 起動スクリプト
  - run_monitoring.py
    - Monitoring 起動スクリプト
  - data/ (実行時に生成される)
    - monitoring.db（デフォルトの SQLite）
    - paper_trading.db（ペーパートレード用）
    - execution.pid, kill.flag, stop_requested.flag
  - logs/ (ログ出力先)
  - utils/
    - logging_setup.py
    - process_priority.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
  - execution/
    - broker_factory.py
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
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
  - tools/
    - paper_verification_report.py

（上記はコアファイルを抜粋したものです。実際の実装ではさらに細分化されたモジュールが存在します）

---

## よくある運用上の注意

- 本番環境（KABUSYS_ENV=live）では kill.flag、KILL_FLAG_CLEAR_ON_START、LINE 通知等の設定を慎重に扱ってください。validate_config は live 時のガードチェックを行います。
- ペーパートレードと本番 DB は物理的に分離することを強く推奨します（デフォルト設計もそのようになっています）。
- OpenAI など外部 API を使う機能は API キーと課金が必要です。失敗時のフェイルセーフ（0.0 フォールバック等）が実装されていますが、利用ポリシーに注意してください。
- ログディレクトリや DB の親ディレクトリが存在しない場合、validate_config が警告を出しますが実行時に自動作成されることもあります。権限について注意してください。

---

## 参考コマンド一覧

- .env ウィザード
  ```
  python -m kabusys.config_setup
  ```
- 設定検証
  ```
  python -m kabusys.validate_config
  ```
- Execution 起動
  ```
  python -m kabusys.run_execution
  ```
- Monitoring 起動（ポーリング間隔 30 秒にする例）
  ```
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```
- Paper Trading レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

必要であれば、README に含める具体的な .env のサンプルや、各モジュール（ExecutionEngine、MonitoringEngine、AI モジュール）の詳細な API 使用例も追加できます。どの辺りを詳しく載せたいか教えてください。