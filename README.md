# KabuSys

日本株向けの自動売買 / リサーチ基盤のコアライブラリ群と起動スクリプト群です。  
このリポジトリには、実行エンジン（ExecutionEngine）、監視 (Monitoring) 周りのユーティリティ、ポートフォリオ構築、ファクター計算、ニュース NLP、各種 CLI ツールが含まれます。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の機能を持つモジュール群から構成されます。

- 実行エンジン（ExecutionEngine）起動スクリプト: 発注・注文管理・リスク管理を統合して市場に発注を行う（本番 / ペーパートレード対応）
- 監視モジュール（Monitoring）: システム稼働状況、注文ログ、リスク監視、Kill Switch（自動停止）等をポーリングして記録・通知
- ポートフォリオ構築: 候補選定、重み計算、ポジションサイズ算出、セクター制約などの純粋関数群
- リサーチ機能: ファクター計算（モメンタム/バリュー/ボラティリティ）、特徴量解析（IC 等）
- AI 関連: ニュースのセンチメント解析（OpenAI を利用）や市場レジーム判定の実装
- ユーティリティ: ログ設定、プロセス優先度や CPU affinity 設定、設定ウィザード / 検証 CLI、Paper Trading レポート生成ツール

設計方針のポイント:
- 実行環境（KABUSYS_ENV）で本番 / ペーパーを切り替え可能
- DB 層は SQLite（監視ログなど）と DuckDB（分析用）を併用
- AI 呼び出しは失敗時にフォールバックするなどフェイルセーフ設計
- 時刻取得におけるルックアヘッドバイアス回避を考慮（datetime.today() を直接参照しない等）

---

## 主な機能一覧

- run_execution.py
  - ExecutionEngine を起動。KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、ペーパートレード用 DB に記録。
  - 起動時にプロセス優先度を上げ、pid ファイルを出力。
  - data/stop_requested.flag が存在すると起動を中止または実行中に停止。

- run_monitoring.py
  - SystemMonitor のポーリングループを起動。
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - monitoring は常に本番 sqlite_path を使用して監視ログを記録。

- config_setup.py
  - .env を対話式に作成 / 更新するウィザード。必須環境変数（J-Quants/ kabu API 等）を設定するのに便利。

- validate_config.py
  - .env と config/*.yaml の存在・基本的な妥当性をチェックする CLI（--strict で警告も失敗扱い）。

- tools/paper_verification_report.py
  - ペーパートレード DB を集計して運用の合否（PASS/FAIL）を判定するレポート生成スクリプト。

- monitoring.*
  - MonitoringDB（SQLite テーブルの初期化 / 永続化層）
  - SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine
  - KillSwitch / AlertManager（通知は設定による）

- ai.*
  - news_nlp: OpenAI を使ったニュースの銘柄別センチメント算出と ai_scores テーブルへの書込み（バッチ・リトライ・検証つき）
  - regime_detector: ma200 とマクロニュースの LLM スコアを合成して日次レジーム判定

- portfolio.*
  - 候補選定、重み計算、ポジションサイズ計算、セクターキャップ適用、レジーム乗数

- utils.*
  - logging_setup: stdout + 日次ローテートファイルハンドラの統一設定
  - process_priority: Windows / POSIX を吸収したプロセス優先度 / CPU affinity 設定

---

## セットアップ手順（開発向け）

前提: Python 3.10+ を想定（| 型注釈を使用しています）。必要な外部ライブラリは下記参照。

1. リポジトリをクローン・作業ディレクトリへ移動
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # Unix/macOS
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール
   ※ requirements.txt がない場合は主要依存をインストールしてください:
   - duckdb
   - psutil
   - openai
   - PyYAML（config 検証で任意）

   例:
   ```
   pip install duckdb psutil openai PyYAML
   ```

4. .env の作成
   - 対話式ウィザードを使う:
     ```
     python -m kabusys.config_setup
     ```
   - または .env.example を参考に手動で .env を作成（.env は絶対に Git にコミットしないこと）。

5. 設定検証
   ```
   python -m kabusys.validate_config
   python -m kabusys.validate_config --strict
   ```

6. データディレクトリや DB ファイルを作成しておく（ログディレクトリや data/ 等）
   - ログはデフォルトで logs/ 以下に保存されます（ログディレクトリは環境変数 LOG_DIR で変更可能）。

---

## 環境変数（主要）

- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 実行環境
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
    - paper_trading: ペーパートレード専用 DB を使用
    - live: 本番モード（設定を慎重に）

- データベース / ファイルパス
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (監視用、デフォルト: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (ペーパートレード DB、デフォルト: data/paper_trading.db)
  - PID_FILE_PATH (デフォルト: data/execution.pid)
  - KILL_FLAG_PATH (デフォルト: data/kill.flag)
  - LOG_DIR (デフォルト: logs/)

- ログ
  - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL

- 監視ループ
  - MONITOR_POLL_INTERVAL: SystemMonitor のポーリング間隔（秒、デフォルト: 60）

- Paper Trading 動作
  - PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）

- OpenAI
  - OPENAI_API_KEY（ai.news_nlp / regime_detector で使用）

- 起動制御
  - KILL_FLAG_CLEAR_ON_START: 1 にすると起動時に kill.flag を自動クリア（本番では 0 推奨）

---

## 使い方（主要コマンド）

- 環境設定ウィザード（.env 作成）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- 実行エンジン起動（ExecutionEngine）
  - 本番 / ペーパーは KABUSYS_ENV に依存
  - 起動:
    ```
    python -m kabusys.run_execution
    ```
  - 注意:
    - 起動時に data/stop_requested.flag があれば起動を中止します。
    - エンジンは pid ファイル（デフォルト data/execution.pid）を作成します。
    - 停止させるには data/stop_requested.flag を作成する、または ExecutionEngine 側の停止ロジックに従う。

- 監視ループ起動（SystemMonitor）
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔を変更する場合:
    ```
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    ```

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - DB パスを指定:
    ```
    python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
    ```

- AI モジュール（プログラムから呼び出す例）
  - news NLP（プログラム内で OpenAI キーを設定して実行）:
    ```python
    from kabusys.ai.news_nlp import score_news
    import duckdb
    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, target_date=date(2026,4,1), api_key="sk-...")
    ```
  - regime_detector も同様に programmatic API を使って呼べます。

---

## 停止 / Kill Switch の仕組み

- data/stop_requested.flag
  - run_monitoring.py / run_execution.py が監視している停止フラグ。存在するとループを終了します。
- data/kill.flag
  - KillSwitch（監視の一部）が条件を満たすとこのファイルを書き込み、ExecutionEngine に停止を要求します。
  - KILL_FLAG_CLEAR_ON_START=1 の場合は起動時に自動でクリアされます（本番では無効化推奨）。
- execution.pid
  - 実行エンジンの PID を格納するファイル（停止・プロセス管理に利用）。

---

## ロギング

- 共通の setup_logging を利用して stdout とファイル（logs/<app>.log）へ出力します。
- 日次ローテーション・30日分保持がデフォルト。
- LOG_DIR / LOG_LEVEL により挙動を制御できます。

---

## ディレクトリ構成（主要部分）

以下はソースツリーの概観（src/kabusys 以下）。実際のファイル数はさらに多い可能性があります。

- src/
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
    - monitoring/
      - monitoring_db.py
      - monitoring_engine.py
      - system_monitor.py
      - risk_monitor.py
      - trade_monitor.py (参照用)
      - kill_switch.py
      - alert_manager.py (参照用)
    - portfolio/
      - __init__.py
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - utils/
      - __init__.py
      - logging_setup.py
      - process_priority.py
    - execution/
      - execution_engine.py (参照)
      - order_manager.py (参照)
      - order_repository.py (参照)
      - broker_factory.py (参照)
      - reconciler.py (参照)
      - risk_manager.py (参照)
    - data/ (ランタイムで作成する想定)
      - monitoring.db (デフォルト SQLITE_PATH)
      - kabusys.duckdb (デフォルト DUCKDB_PATH)
      - paper_trading.db (ペーパートレード用)
      - stop_requested.flag / kill.flag / execution.pid

（注）実際のサブモジュール・ファイルはリポジトリによって多少の差異があります。上は提供コードから抽出した概観です。

---

## 開発・運用上の注意

- .env は機密情報を含むため絶対に Git にコミットしないでください。
- 本番環境（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START を 0 に設定してください。誤って Kill Switch を自動クリアすると危険です。
- AI 呼び出しは API コスト・レート制限を考慮して実装されていますが、API キーの管理には注意してください（OPENAI_API_KEY）。
- ログディレクトリ作成に失敗しても stdout ログは出力されるようフォールバックしています。
- DuckDB / SQLite のパスや構造が異なる場合は .env で適切に設定してください。

---

## よく使うコマンドまとめ

- .env 作成:
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
- 監視ループ起動:
  ```
  python -m kabusys.run_monitoring
  ```
- ペーパートレード検証レポート:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

必要であれば、README にサンプル .env テンプレートや systemd / supervisord 用の起動ユニット例、より詳細な API 使用例（ai.score_news / ai.regime_detector / portfolio API）を追記します。どの情報を優先して追加しますか？