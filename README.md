# KabuSys

日本株自動売買システム（ライブラリ / 実行スクリプト群）

このリポジトリは、シグナル生成・ポートフォリオ構築・発注（実/ペーパー）・監視・研究ツール・AI によるニュース解析などを含む自動売買プラットフォームの一部実装です。README はソースコード（src/kabusys 以下）から主要な使い方・セットアップ手順・ディレクトリ構成をまとめたものです。

---

## プロジェクト概要

- 目的: 日本株の自動売買を支援するための総合フレームワーク。
- 主な役割:
  - シグナル / ファクター計算（research）
  - ポートフォリオ構築・株数決定（portfolio）
  - 発注エンジン（execution） — 本番 / ペーパートレード対応
  - 実行・システム監視（monitoring）とキルスイッチ管理
  - ニュースの NLP によるセンチメント評価（AI）
  - 運用支援ツール（設定ウィザード、設定検証、レポート生成）

---

## 機能一覧（主なコンポーネント）

- config / config_setup / validate_config
  - .env の対話的生成（python -m kabusys.config_setup）
  - 起動前の環境検証（python -m kabusys.validate_config）
- execution
  - ExecutionEngine による発注ループ
  - BrokerClientFactory により本番/ペーパーの切替
  - risk_manager / reconciler / order_manager 等の発注制御
- monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor のポーリング
  - MonitoringDB: SQLite に監視ログを永続化
  - KillSwitch: 条件に応じた停止フラグ（data/kill.flag）作成
  - monitoring_engine: 各 Monitor をまとめて運用
- portfolio
  - 銘柄選定・重み計算（等配分、スコア加重）
  - セクターキャップ、レジーム乗数
  - ポジションサイズ計算（単元丸め、aggregate cap）
- research
  - ファクター計算（momentum / volatility / value 等）
  - 将来リターン計算・IC（Info Coef）・統計サマリー
- ai
  - news_nlp: OpenAI を使ったニュースセンチメント評価（ai_scores へ書き込み）
  - regime_detector: MA200 とマクロニュースを使った市場レジーム判定
- tools
  - paper_verification_report: ペーパートレードの検証レポート生成

ユーティリティ:
- logging_setup: 統一的なログ設定（コンソール + 日次ローテーションファイル）
- process_priority: プロセス優先度 / CPU affinity 設定

---

## セットアップ手順

1. Python 仮想環境作成（推奨）
   - python3 -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージのインストール（主要パッケージ例）
   - duckdb
   - psutil
   - openai
   - (必要に応じて) PyYAML
   例:
   ```
   pip install duckdb psutil openai PyYAML
   ```
   ※ requirements.txt は本リポジトリに含まれていないため、プロジェクトで必要なパッケージを上記のように個別にインストールしてください。

3. プロジェクトルートに移動（README と同じ階層に src/ がある想定）

4. .env の作成
   - 対話ウィザードで作成:
     ```
     python -m kabusys.config_setup
     ```
   - または手動で .env を作成（.env.example を参照する想定）。必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - OpenAI を使う機能を利用する場合:
     - OPENAI_API_KEY を設定

5. 設定検証（起動前推奨）
   ```
   python -m kabusys.validate_config
   ```
   必要に応じて `--strict` を付けると警告も失敗扱いになります。

6. データディレクトリ等の作成
   - デフォルトの DB / フラグ / ログ パス:
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper SQLite: data/paper_trading.db
     - ログディレクトリ: logs/
     - kill.flag / stop_requested.flag: data/kill.flag, data/stop_requested.flag
   - ログディレクトリや data/ は起動時に自動作成されることが多いですが、権限等に注意してください。

---

## 使い方

基本はパッケージモジュールを実行して各コンポーネントを起動します。プロジェクトルートから以下を実行してください。

- 監視プロセス（SystemMonitor のポーリングループ）を起動
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔の上書き: 環境変数 MONITOR_POLL_INTERVAL（秒）
    例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視は MonitoringDB（SQLite）に記録します。注意: monitoring は KABUSYS_ENV に関わらず本番 sqlite_path を使用します。
  - 停止: プロジェクトルート/data/stop_requested.flag を作成するとループが安全に終了します。

- 発注エンジン（ExecutionEngine）を起動
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV が `paper_trading` の場合、MockBrokerClient を使用して data/paper_trading.db を使用します（本番 DB と完全分離）。
  - 実行中にプロセスを止めたい場合:
    - data/stop_requested.flag を作成するとエンジンは停止処理を行います。
  - 起動時、data/execution.pid に PID が書き込まれます（PID ファイル位置は Settings.pid_file_path に従います）。

- .env の生成・変更
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - DB を指定する場合:
    ```
    python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
    ```

- AI 機能（ニュース NLP / レジーム検出）
  - OPENAI_API_KEY を .env に設定するか関数呼び出し時に api_key を指定してください。
  - 例: kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime を呼び出して実行します（通常は運用スクリプトから呼ぶ）。

- ログ
  - ログはデフォルトで stdout とファイル（logs/<app_name>.log）に出力されます。
  - 環境変数で LOG_DIR / LOG_LEVEL を設定可能です。
  - ログ設定は各スクリプトで setup_logging(app_name=...) を呼び出して初期化されます。

---

## 環境変数（主なもの）

- 必須（最低限）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 動作モード
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
    - paper_trading: 発注はモック、データ分離
    - live: 本番運用（注意して設定すること）
- DB / ログ
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (デフォルト: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db)
  - LOG_DIR (デフォルト: logs/)
  - LOG_LEVEL (DEBUG/INFO/...)
- 監視関連
  - MONITOR_POLL_INTERVAL (run_monitoring 用のポーリング間隔秒)
  - PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START
- AI
  - OPENAI_API_KEY
- Paper trading の挙動
  - PAPER_FILL_MODE: instant | partial | never | reject

詳細は src/kabusys/config.py の Settings クラスのプロパティを参照してください。

---

## 停止・キルスイッチ

- ディレクトリ data/ に以下のファイルを配置することでプロセスの制御を行います。
  - data/stop_requested.flag
    - run_monitoring / run_execution はこのファイルがあると安全にループを終了します。
  - data/kill.flag
    - KillSwitch が評価条件を満たした場合に書き込まれ、ExecutionEngine を停止するフラグとして運用されます。
  - data/execution.pid
    - ExecutionEngine 実行時に PID を書き込みます。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要なファイル / パッケージ構成（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                  — 環境変数/設定取得
  - config_setup.py            — .env 対話ウィザード
  - validate_config.py         — 設定検証スクリプト
  - run_monitoring.py          — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - utils/
    - logging_setup.py         — ログ設定ユーティリティ
    - process_priority.py      — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py         — SQLite 永続化（schema / API）
    - system_monitor.py
    - trade_monitor.py         — (存在する想定)
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py         — (存在する想定)
  - execution/
    - execution_engine.py      — (主要処理)
    - broker_factory.py
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

（注）一部ファイルは本 README 作成時点で抜粋しています。詳細はソースツリーを参照してください。

---

## 運用上の注意・ベストプラクティス

- 本番運用時は KABUSYS_ENV=live を使用しますが、設定ミスによる誤発注を防ぐため validate_config を必ず実行してください。
- .env ファイルは決して Git にコミットしないでください。
- OpenAI 等の外部 API を使用する機能は API キー・呼び出しコスト・レート制限に注意して利用してください。AI 呼び出しはリトライやフォールバックを備えていますが、運用設計を慎重に行ってください。
- Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path（settings.sqlite_path）を使用する点に注意してください（監視ログは別 DB に分離したい場合は設定を変更してください）。
- process_priority の設定は権限により適用されない場合があります（警告ログが出ます）。

---

## 参考コマンドまとめ（例）

- .env 作成
  ```
  python -m kabusys.config_setup
  ```
- 設定検証
  ```
  python -m kabusys.validate_config
  ```
- 監視起動（ポーリング間隔 60 秒）
  ```
  MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
  ```
- 発注エンジン起動
  ```
  python -m kabusys.run_execution
  ```
- Paper Trading レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

もし README に追加したいセクション（例: 詳細な設定例、運用手順書、CI/デプロイ手順、開発用のテスト/カバレッジ実行方法 等）があれば教えてください。必要に応じて追記・整備します。