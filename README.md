# KabuSys

日本株自動売買システムのコアライブラリ群と起動スクリプト集です。  
この README はリポジトリ内の主要スクリプト・ユーティリティの使い方、設定方法、ディレクトリ構成をまとめたものです。

---

## プロジェクト概要

KabuSys は、戦略のリサーチ（DuckDB を用いたファクター算出）、ポートフォリオ構築、発注エンジン（ExecutionEngine）、およびシステム監視（Monitoring）を含む日本株自動売買のためのモジュール群です。  
OpenAI によるニュース NLP を用いたセンチメント評価や、市場レジーム判定などの AI 補助機能も実装されています。

主な設計方針：
- DuckDB / SQLite を用いたオンプレデータ処理
- 環境変数 (.env) による設定管理（自動ロード機能あり）
- Paper Trading（検証用）と Live（本番）を明確に分離
- フェイルセーフ（API失敗時のフォールバック）を重視

---

## 機能一覧

- 環境設定ウィザード（.env 生成）: python -m kabusys.config_setup
- 設定検証 CLI: python -m kabusys.validate_config
- 実行エンジン起動スクリプト（ExecutionEngine）: python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 SQLite に記録
- 監視ループ起動スクリプト（SystemMonitor）: python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL でポーリング間隔を変更可能（デフォルト 60秒）
- Paper Trading 検証レポート生成ツール: python -m kabusys.tools.paper_verification_report
- ポートフォリオ構築ユーティリティ（候補選定、重み計算、ポジションサイジング）
- 監視／リスクロジック（SystemMonitor, TradeMonitor, RiskMonitor, KillSwitch）
- AI 補助機能
  - news_nlp.score_news: ニュース記事を LLM でセンチメントスコア化し ai_scores に保存
  - regime_detector.score_regime: ETF とマクロニュースを合成して市場レジーム判定
- ログ設定ユーティリティ（統一的な Stream + 日次ローテーションファイル出力）
- プロセス優先度設定・CPU affinity ユーティリティ

---

## 要件（推奨）

- Python 3.10+
- 必要と思われるパッケージ（最低限、個別プロジェクトで適宜 requirements を用意してください）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証時に config/*.yaml をパースする場合に任意）
- SQLite（標準ライブラリに同梱）
- （任意）systemd / supervisor / cron などで長時間プロセスを管理

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成・有効化（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .\.venv\Scripts\activate   # Windows
   ```

3. 必要パッケージをインストール（プロジェクトに requirements.txt がある場合はそれを使用）
   例:
   ```
   pip install duckdb psutil openai pyyaml
   ```

4. .env を生成（対話ウィザード）
   ```
   python -m kabusys.config_setup
   ```
   - 対話で J-Quants トークン、kabuAPI パスワード、DB パス、KABUSYS_ENV などを設定します。
   - 生成された .env は絶対に Git にコミットしないでください。

5. 設定を検証
   ```
   python -m kabusys.validate_config
   # 警告も厳密に扱う場合:
   python -m kabusys.validate_config --strict
   ```

6. （必要なら）データディレクトリ作成
   デフォルトで使用されるディレクトリ / ファイル:
   - data/monitoring.db （SQLite 監視 DB）
   - data/paper_trading.db （Paper Trading 用 SQLite）
   - data/kabusys.duckdb （DuckDB）
   - logs/（ログ）
   スクリプト実行時に自動作成されることが多いですが、権限等で失敗する場合は事前に作成してください。

---

## 主要な環境変数（抜粋）

- KABUSYS_ENV: 実行環境（development, paper_trading, live）. default: development
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（default: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイル（default: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（default: data/monitoring.db） — Monitoring は環境に関わらず本番 sqlite_path を使用
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（default: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading 時の約定動作（instant, partial, never, reject）
- LOG_LEVEL: ログレベル（DEBUG, INFO, ...）
- LOG_DIR: ログ格納ディレクトリ（default: logs/）
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、default: 60）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で利用）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリア（0/1、本番では 0 推奨）

.env の自動ロード:
- プロジェクトルート（.git または pyproject.toml を基準）にある `.env` / `.env.local` はプロセス開始時に自動で読み込まれます。
- 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 使い方（コマンド例）

- 環境設定ウィザード（.env の作成）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- 監視ループ起動（SystemMonitor）
  ```
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能。
  - 停止: プロジェクトルート配下の data/stop_requested.flag が存在するとループを終了します。

- 実行エンジン起動（ExecutionEngine）
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 DB に記録され、本番 DB と分離されます。
  - 起動時は data/execution.pid（デフォルト）に PID を書きます。停止は data/stop_requested.flag または Kill Switch（kill.flag）で制御されます。

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を指定する場合:
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI 機能（プログラム経由）
  - news_nlp.score_news(conn, target_date, api_key=None)
  - regime_detector.score_regime(conn, target_date, api_key=None)
  上記は DuckDB 接続を受け取り、内部で OpenAI を呼びます（api_key は引数、または環境変数 OPENAI_API_KEY）。

---

## 停止・Kill Switch 関連

- data/stop_requested.flag
  - run_monitoring / run_execution のポーリングループはこのフラグファイルを検知すると安全に終了します（手動停止用）。
- KillSwitch（data/kill.flag）
  - リスクモニタ等が条件を満たすと kill.flag を書き込むことで ExecutionEngine に停止シグナルを送ります。
  - Settings.kill_flag_clear_on_start が 1 の場合、起動時に自動で kill.flag をクリアする挙動になります（本番では危険なので 0 推奨）。

---

## ログ・DB

- ログ: logs/<app_name>.log（TimedRotatingFileHandler による日次ローテーション、デフォルト30日分保持）
  - app_name 例: "execution", "monitoring"
  - ログディレクトリは環境変数 LOG_DIR または引数で変更可能
- SQLite（監視 DB）
  - デフォルト: data/monitoring.db（Monitoring 用）
  - init_monitoring_db() により必要なテーブルは冪等に作成されます（マイグレーションも一部対応）
- DuckDB（分析用）
  - デフォルト: data/kabusys.duckdb

---

## 主要モジュール（抜粋）

- kabusys.config: 環境変数・設定解決、.env 自動読み込みロジック
- kabusys.config_setup: .env 対話ウィザード
- kabusys.validate_config: 起動前の設定検証 CLI
- kabusys.run_monitoring: SystemMonitor のポーリングループ起動スクリプト
- kabusys.run_execution: ExecutionEngine 起動スクリプト（Paper Trading と本番 DB の分離対応）
- kabusys.utils.logging_setup: ログ設定ユーティリティ
- kabusys.utils.process_priority: プロセス優先度 / CPU affinity 設定
- kabusys.monitoring: SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine / KillSwitch
- kabusys.portfolio: 候補選定・重み計算・ポジションサイジング・リスク調整（純粋関数群）
- kabusys.research: ファクター計算・特徴量探索
- kabusys.ai: news_nlp（ニュース NLP） / regime_detector（市場レジーム判定）
- kabusys.monitoring.monitoring_db: 監視用の永続化レイヤ（SQLite）

---

## ディレクトリ構成（主要ファイル）

以下はリポジトリ内の主要なファイル・ディレクトリ構成の一例です（抜粋）。

- src/
  - kabusys/
    - __init__.py
    - config.py
    - config_setup.py
    - validate_config.py
    - run_monitoring.py
    - run_execution.py
    - utils/
      - __init__.py
      - logging_setup.py
      - process_priority.py
    - monitoring/
      - monitoring_db.py
      - system_monitor.py
      - risk_monitor.py
      - trade_monitor.py         # （開発版では別ファイルとして存在）
      - monitoring_engine.py
      - kill_switch.py
      - alert_manager.py         # （アラート送信用モジュール）
    - execution/
      - execution_engine.py
      - order_manager.py
      - order_repository.py
      - broker_factory.py
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
    - ai/
      - __init__.py
      - news_nlp.py
      - regime_detector.py
    - tools/
      - __init__.py
      - paper_verification_report.py
    - data/                      # 実行時に使用される例: monitoring.db, paper_trading.db, kabusys.duckdb, kill.flag 等

※ 上記は本リポジトリに存在するファイルを基にした抜粋です。実際の追加モジュール（order_manager 等）はそれぞれの役割に沿って実装されています。

---

## 開発メモ / 注意点

- Monitoring は環境（KABUSYS_ENV）に関わらず監視用の sqlite_path（デフォルト data/monitoring.db）を使用します。Execution は paper_trading 時に paper_sqlite_path を使用して本番 DB と分離します。
- .env ファイルは OS 環境変数に優先されません（既存の OS 環境変数を保護）。.env.local は .env より優先して上書きされます。
- OpenAI を利用する処理は API キーの管理に注意してください（OPENAI_API_KEY 環境変数）。
- 本番（KABUSYS_ENV=live）では Kill Switch やログ・通知設定を十分に確認してください。validate_config は live 時に追加の警告を出します。
- DuckDB や SQLite のパスは環境変数で上書きできます。DB ファイルをバックアップしてから運用することを推奨します。

---

## 参考コマンドまとめ

- .env 作成: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config
- 監視起動: python -m kabusys.run_monitoring
- 実行エンジン起動: python -m kabusys.run_execution
- Paper 検証レポート: python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD

---

必要があれば README をさらに詳しく（各設定項目の説明、systemd ユニット例、デバッグ方法、テストの実行方法など）に拡張できます。どの情報を深掘りしたいか教えてください。