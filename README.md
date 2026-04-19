# KabuSys

日本株向け自動売買システムのリファレンス実装（モジュール群）。  
このリポジトリは以下の機能を持つコンポーネント群を含みます：実行エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、リサーチ／ファクター計算、ニュース NLP（OpenAI を利用したセンチメント評価）、および各種ユーティリティ／スクリプト。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買運用を支援するためのモジュール群です。設計方針としては：

- 本番とペーパートレードを明確に分離（KABUSYS_ENV により切替）。
- DuckDB を分析用 DB、SQLite を監視・発注ログ用に使用。
- OpenAI（gpt-4o-mini）を用いたニュースセンチメントやレジーム判定の統合（オプション）。
- システム稼働監視、リスク監視、Kill Switch（停止フラグ）などの運用安全機構を搭載。
- ポートフォリオ構築・ポジションサイジングは純粋関数として実装され、テストしやすい。

---

## 主な機能一覧

- Execution
  - ExecutionEngine による売買セッションの実行（実口座 / ペーパートレード切替）
  - BrokerClientFactory によるブローカークライアントの抽象化（paper_trading では Mock を使用）
  - OrderRepository / OrderManager / RiskManager / Reconciler 等の発注制御周り

- Monitoring
  - SystemMonitor: CPU / メモリ / ディスク / データ鮮度 / Execution プロセス監視
  - TradeMonitor: 発注・約定ログ解析（滞留注文・異常約定検出 等）
  - RiskMonitor: ドローダウン・ポジション上限監視
  - KillSwitch: 条件成立時に data/kill.flag を書き込み ExecutionEngine に停止を促す
  - MonitoringEngine: 上記監視コンポーネントのポーリング実行

- Portfolio Construction
  - 候補選定（score / rank 基準）
  - 等配分・スコア加重配分
  - 単元株丸め・リスクベースのポジションサイジング
  - セクター集中制限、レジームに応じた投資量調整

- Research
  - ファクター計算 (momentum / volatility / value)
  - 将来リターン計算、IC（Information Coefficient）等の解析ユーティリティ

- AI (OpenAI)
  - news_nlp: 生のニュース記事を集約して LLM に投げ、銘柄ごとのセンチメントを ai_scores テーブルへ書込
  - regime_detector: ma200 とマクロセンチメントを合成して市場レジームを判定・記録

- Tools
  - paper_verification_report: ペーパートレード DB を解析して検証レポート生成

- 設定 / ユーティリティ
  - config_setup: .env を対話的に生成・更新するウィザード
  - validate_config: .env および config/*.yaml の事前検証 CLI
  - logging_setup: 統一的なログ設定（コンソール + 日次ローテーション）
  - process_priority: プロセス優先度や CPU affinity の設定ユーティリティ

---

## セットアップ手順（開発／ローカル実行向け）

以下は一般的なセットアップ手順です。実行環境に応じてパッケージや Python バージョンを調整してください。

1. Python 環境を用意
   - 推奨: Python 3.9+（コードは型アノテーション等を利用）
   - 仮想環境の作成例:
     ```
     python -m venv .venv
     source .venv/bin/activate  # macOS / Linux
     .venv\Scripts\activate     # Windows
     ```

2. 依存パッケージをインストール
   - 必要な主なライブラリ:
     - duckdb
     - openai
     - psutil
     - PyYAML（検証で YAML を使う場合）
   - 例（pip）:
     ```
     pip install duckdb openai psutil PyYAML
     ```
   - 実際には requirements.txt を用意している場合はそれを利用してください。

3. .env の準備
   - 対話式ウィザードで生成:
     ```
     python -m kabusys.config_setup
     ```
   - または手動でプロジェクトルートに .env を作成。主な環境変数（必須 / デフォルト）:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - KABUSYS_ENV (development / paper_trading / live) — デフォルト: development
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH — デフォルト: data/paper_trading.db
     - LOG_LEVEL — デフォルト: INFO
     - OPENAI_API_KEY — OpenAI を使う機能を有効にする場合に必要
     - KILL_FLAG_CLEAR_ON_START — 本番での自動クリアは非推奨（デフォルト 0）

4. 設定検証
   ```
   python -m kabusys.validate_config
   # strict モード（警告も失敗扱い）
   python -m kabusys.validate_config --strict
   ```

5. ログディレクトリ
   - デフォルトは `logs/`。権限に問題があれば環境変数 LOG_DIR で変更可能。

---

## 使い方（主なエントリポイント）

- 実行エンジン起動（ExecutionEngine）
  - 本番 / ペーパートレードは KABUSYS_ENV に依存。
  - 実行:
    ```
    python -m kabusys.run_execution
    ```
  - 停止:
    - プロセスは data/stop_requested.flag の検出でシャットダウンします（手動で停止フラグを作成するか、プロセスを SIGINT などで終了）。
    - Kill Switch によって `data/kill.flag` が書き込まれると ExecutionEngine によって停止がトリガーされます。

- 監視プロセス起動（SystemMonitor のポーリング）
  - 実行:
    ```
    python -m kabusys.run_monitoring
    ```
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（秒、デフォルト 60）。
  - 監視は常に（KABUSYS_ENV にかかわらず）本番用の sqlite_path を参照します（監視ログの一元管理のため）。

- Paper Trading 検証レポート
  - 実行:
    ```
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    ```
  - `--db` オプションで DB パスを指定するか、PAPER_TRADING_SQLITE_PATH 環境変数で指定します。

- 設定ウィザード / 検証
  - .env 作成:
    ```
    python -m kabusys.config_setup
    ```
  - 設定検証:
    ```
    python -m kabusys.validate_config
    ```

注意: KABUSYS_ENV=live（本番）での起動は実際に発注が行われます。権限・設定・トークン・資金管理を十分に確認してください。

---

## 重要な運用ファイル・フラグ

- data/stop_requested.flag
  - run_monitoring.py と run_execution.py がチェックする停止フラグ。存在するとポーリングループを終了します。

- data/kill.flag
  - KillSwitch が書込む停止フラグ（ExecutionEngine 停止指示用）。存在するかどうかで Kill 状態を判定します。
  - KILL_FLAG_CLEAR_ON_START=1 の場合は起動時に自動でクリアされるように設定可能（本番では 0 推奨）。

- data/execution.pid
  - ExecutionEngine の PID ファイル（起動時に生成）。pid_file のパスは Settings.pid_file_path から取得。

---

## 環境変数（主な一覧）

- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 運用 / デフォルト
  - KABUSYS_ENV (development | paper_trading | live) — default: development
  - DUCKDB_PATH — default: data/kabusys.duckdb
  - SQLITE_PATH — default: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH — default: data/paper_trading.db
  - LOG_LEVEL — default: INFO
  - LOG_DIR — default: logs/
  - OPENAI_API_KEY — OpenAI 機能利用時に必要
  - MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒）、デフォルト 60
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0 / 1）

（詳細は `src/kabusys/config.py` の Settings クラスのプロパティ注釈を参照してください）

---

## ディレクトリ構成（主要ファイル）

以下はリポジトリ内の主要なディレクトリ／ファイル構成（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py
  - config_setup.py
  - validate_config.py
  - run_execution.py
  - run_monitoring.py
  - data/ (データ格納ディレクトリ、実行環境で自動生成される)
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py (実装がある想定)
  - execution/
    - execution_engine.py
    - broker_factory.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - tools/
    - __init__.py
    - paper_verification_report.py
  - utils/
    - __init__.py
    - logging_setup.py
    - process_priority.py

注: 上記はこのリポジトリに含まれる主要なモジュール群を要約したものです。細かなファイルは実際のツリーを参照してください。

---

## 開発・運用上の注意点

- 本番（KABUSYS_ENV=live）での稼働は実際の資金を動かします。必ず設定・権限・Kill Switch の挙動を確認してください。
- OpenAI を使う機能（news_nlp / regime_detector）は API キーと通信が必要です。コストとレイテンシに注意してください。API 呼び出しはリトライロジックを備えていますが、ネットワーク障害時はフォールバック動作になります。
- 監視プロセスは監視用 SQLite DB（SQLITE_PATH）へログを残します。バックアップや運用監視を検討してください。
- ペーパートレード（paper_trading）はペーパーデータベース（PAPER_TRADING_SQLITE_PATH）に記録され、本番 DB と分離されています。検証やレポートに利用してください。
- ロギングは `kabusys.utils.logging_setup.setup_logging` で統一的に設定され、デフォルトで `logs/<app_name>.log` に日次ローテーションで保存されます。

---

## 追加情報 / 参考

- 設定検証: python -m kabusys.validate_config
- 環境設定ウィザード: python -m kabusys.config_setup
- 監視ループ（ポーリング間隔変更）: MONITOR_POLL_INTERVAL 環境変数で秒数を指定
- 重要: .env ファイルは絶対にリポジトリにコミットしないこと（シークレットを含むため）

---

この README はコードベースの主要な説明を目的とした概要ドキュメントです。各モジュールの詳細な API / パラメータはソース内の docstring を参照してください。必要であれば、各コンポーネントの運用手順やデプロイ手順（systemd / supervisor / Docker など）を追記します。