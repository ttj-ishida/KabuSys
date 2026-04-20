# KabuSys

日本株自動売買システムのコアライブラリ / ツール群です。  
このリポジトリは、戦略研究（ファクター算出・特徴量解析）、ポートフォリオ構築、発注エンジン（ExecutionEngine）および運用監視（Monitoring）に必要なユーティリティ群を含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下を目的としたモジュール群を提供します。

- ファクター計算・研究：DuckDB 上の価格・財務データからファクター（Momentum / Value / Volatility 等）を算出。
- ポートフォリオ構築：候補選定、重み付け、セクター制約、ポジションサイジング。
- 実行エンジン起動スクリプト：ExecutionEngine を起動し、ブローカークライアント経由で発注を行う（paper_trading モードあり）。
- 監視：System/Trade/Risk の監視、Kill Switch によるエンジン停止シグナル、監視ログ保存（SQLite）。
- AI 補助：ニュースの NLP スコアリング、レジーム判定（OpenAI を利用）。
- 運用ツール：.env ウィザード、設定検証、Paper Trading 検証レポート生成等。

設計方針として、DB（DuckDB/SQLite）をデータ層として利用し、外部 API 呼び出しや本番発注は環境設定（KABUSYS_ENV）により切り替え可能です。

---

## 機能一覧

- config
  - 環境変数の読み込みと Settings クラス（.env 自動ロード機能）
  - .env 対話式ウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py）

- execution
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - paper_trading モード（MockBrokerClient を使用、専用 SQLite）

- monitoring
  - System/Trade/Risk の監視コンポーネント群
  - MonitoringEngine（ポーリングループ）
  - KillSwitch（data/kill.flag による停止）
  - 監視ログ永続化（SQLite via monitoring_db.py）
  - run_monitoring.py：監視ポーリングの起動スクリプト（MONITOR_POLL_INTERVAL 環境変数対応）

- portfolio
  - 候補選定、等重／スコア加重、ポジション決定（単元株丸め、上限・資金配分考慮）
  - セクター制限・レジーム乗数適用

- research
  - ファクター計算（momentum, volatility, value）
  - 特徴量探索（forward returns, IC, summary）

- ai
  - ニュース NLP による銘柄別センチメント（OpenAI 使用）
  - 市場レジーム判定（MA200 とマクロセンチメントの合成）

- tools
  - paper_verification_report.py：Paper Trading 検証レポートの生成

- utils
  - logging_setup.py：統一ログ設定（stdout + 日次ローテートファイル）
  - process_priority.py：プロセス優先度 / CPU affinity 設定ユーティリティ

---

## セットアップ手順

1. Python 環境を用意（推奨: 3.10+）

2. 仮想環境作成（例）
   - Unix/macOS:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (PowerShell):
     ```
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

3. 依存関係をインストール
   - 必須（例）:
     ```
     pip install duckdb psutil openai
     ```
   - optional:
     - PyYAML（config/*.yaml のパース検証に使用）
       ```
       pip install pyyaml
       ```
   - （パッケージ配布形式がある場合は `pip install -e .` 等を利用）

4. .env を作成
   - 対話ウィザードで作成:
     ```
     python -m kabusys.config_setup
     ```
   - もしくはプロジェクトルートに `.env` を置く（.env.example を参考に）。

5. DB 初期化
   - 監視用 SQLite（デフォルト: data/monitoring.db）や DuckDB（data/kabusys.duckdb）は、各起動スクリプトが必要に応じてテーブルを作成します（init_monitoring_db が冪等で対応）。

6. OpenAI を利用する場合
   - 環境変数 `OPENAI_API_KEY` を設定するか、各関数呼び出しに api_key を渡してください。

---

## 環境変数（主な項目とデフォルト）

- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 実行環境
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）

- DB 関連
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用）

- ログ / 制御
  - LOG_LEVEL: INFO
  - LOG_DIR: logs/
  - PID_FILE_PATH: data/execution.pid
  - KILL_FLAG_PATH: data/kill.flag
  - KILL_FLAG_CLEAR_ON_START: 0|1

- 監視関連
  - MONITOR_POLL_INTERVAL: ポーリング間隔（秒、run_monitoring で参照、デフォルト 60）
  - CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT: 監視閾値（%）

- AI / OpenAI
  - OPENAI_API_KEY

- Paper trading
  - PAPER_FILL_MODE: instant | partial | never | reject

※ 詳細は `kabusys.config.Settings` を参照してください（バリデーションが組み込まれています）。

---

## 使い方（主要コマンド）

プロジェクトルートで実行してください。`python -m kabusys.<module>` 形式で利用できます。

- 環境設定ウィザード（.env 作成）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- 監視ループ起動（ローカルで監視を走らせる）
  ```
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を変更可能（例: 30 秒）
    ```
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    ```
  - 監視は data/stop_requested.flag が作成されると終了します。

- 実行エンジン起動
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し paper_trading 用 DB（デフォルト: data/paper_trading.db）へ記録します。
  - 実行停止は data/stop_requested.flag を作成するか、ExecutionEngine 側の Kill Switch 等で制御されます。

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - デフォルト DB は環境変数 `PAPER_TRADING_SQLITE_PATH` または `data/paper_trading.db`

- AI スコアリング（ライブラリ関数）
  - `kabusys.ai.score_news` / `kabusys.ai.regime_detector.score_regime` を呼び出して利用（OpenAI API キー必須）

- ログ
  - デフォルトは `logs/<app_name>.log`（日次ローテート）と stdout の両方に出力されます。

---

## 停止・Kill Switch

- 実行エンジン / 監視ループは以下のファイルによる制御を想定しています。
  - data/stop_requested.flag: 起動スクリプトがこれを検知すると優雅に終了します。
  - data/kill.flag: KillSwitch によって書き込まれると ExecutionEngine が停止するトリガーになります（本番停止スイッチ）。
- Kill Switch は RiskMonitor 等の監視結果に基づき `kill.flag` を書き込みます。起動時に `KILL_FLAG_CLEAR_ON_START=1` が設定されていると自動でクリアされます（本番では 0 推奨）。

---

## ディレクトリ構成

概略（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py
  - config_setup.py
  - validate_config.py
  - run_execution.py
  - run_monitoring.py
  - tools/
    - __init__.py
    - paper_verification_report.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py (参照：TradeCheckResult を定義するモジュールが存在)
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py (存在する想定のアラート管理モジュール)
  - utils/
    - __init__.py
    - logging_setup.py
    - process_priority.py
  - portfolio/, research/, ai/ の各モジュール群

その他トップレベル:
- data/         （デフォルトDBファイルやフラグファイルを置くディレクトリ）
- logs/         （ログファイル保管ディレクトリ）
- config/       （system_config.yaml 等の設定テンプレートが置かれる想定）

（実際のファイル構成はリポジトリ全体を参照してください。上は主要モジュールの一覧です）

---

## 備考 / 運用注意

- 本番運用前に必ず `python -m kabusys.validate_config` で設定を検証してください（`--strict` で警告も失敗にできます）。
- .env は絶対にリポジトリへコミットしないでください（credential 保護）。
- OpenAI 等外部 API を利用する機能は API キーの管理・コストに注意してください。API 呼び出しはリトライ・バックオフ等の耐障害設計が施されていますが、運用側でのレート制御が必要です。
- process_priority / CPU affinity 設定は OS 権限に依存します。権限不足時は警告のみでスキップされます。
- DuckDB / SQLite のファイルパスは環境変数で変更可能です。paper_trading は専用 DB に切り離す設計です。

---

必要であれば、セットアップ用の requirements.txt や systemd / cron 用の起動ユニット例、さらに各モジュールの API ドキュメント（関数引数一覧や返り値仕様）を追加で作成します。どの補足が必要か教えてください。