# KabuSys

日本株向け自動売買システムのコアライブラリ群および起動スクリプト集です。  
このリポジトリには、監視（Monitoring）、発注実行（Execution）、ポートフォリオ構築、ファクター計算、LLM ベースのニュース解析など、実運用を想定したコンポーネントが含まれます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下を目的としたモジュール化された自動売買フレームワークです。

- 株価データの集約・分析（DuckDB）
- シグナル生成 / ポートフォリオ構築（純粋関数群）
- 発注管理・リスク管理・注文履歴の永続化（SQLite）
- 実行エンジン（本番・ペーパートレード切替）
- システム稼働監視・アラート・Kill Switch
- ニュースの LLM（OpenAI）によるセンチメント解析・レジーム判定
- 運用に必要な CLI ツール類（設定ウィザード・検証・レポート）

設計方針として、外部 API（発注等）へのアクセス部分は抽象化され、本番 DB とペーパートレード DB は分離されるようになっています。

---

## 主な機能一覧

- 起動スクリプト
  - run_monitoring.py: SystemMonitor のポーリングループを起動
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV に応じて Paper/Live 切替）
- 設定管理
  - config_setup.py: 対話式 .env 作成ウィザード
  - validate_config.py: .env と config/*.yaml の検証 CLI
  - config.py: Settings クラスによる環境変数取扱い（自動 .env ロード機能あり）
- 監視（monitoring）
  - system_monitor, trade_monitor, risk_monitor, monitoring_engine, kill_switch
  - MonitoringDB: SQLite による監視ログ・トレードログ永続化
- 発注/実行（execution）
  - ExecutionEngine、OrderManager、RiskManager、Reconciler 等（実装は別ファイル）
  - BrokerClientFactory により mock / real ブローカーを切替可能（paper_trading 用に完全分離された DB を使用）
- ポートフォリオ（portfolio）
  - 銘柄選定、重み計算、ポジションサイズ計算、セクター上限・レジーム乗数適用
- リサーチ（research）
  - ファクター計算（momentum/value/volatility）、forward returns、IC 計算、統計サマリ
- AI（ai）
  - news_nlp: OpenAI を用いた銘柄別ニュースセンチメント評価と ai_scores への書込
  - regime_detector: マクロ + ETF ma200 を使ったレジーム判定
- ユーティリティ
  - logging_setup: 統一ログ設定（stdout + 日次ローテートファイル）
  - process_priority: プロセス優先度 / CPU affinity 設定

---

## 前提・依存関係

- Python 3.10+
  - （コードは型ヒントで | を使用しているため 3.10 以上を想定）
- 必要パッケージ（抜粋）
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証を完全に行いたい場合に推奨）
- その他: SQLite（標準ライブラリで利用可）

インストール例（仮の requirements が存在しない場合）:
```bash
python -m pip install duckdb psutil openai pyyaml
```

---

## セットアップ手順

1. リポジトリをクローン／展開する
2. Python 仮想環境を作成・有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows
   ```
3. 必要パッケージをインストール
   ```bash
   pip install duckdb psutil openai pyyaml
   ```
4. 対話式で .env を生成（推奨）
   ```bash
   python -m kabusys.config_setup
   ```
   - 必須環境変数例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
   - KABUSYS_ENV を設定（development / paper_trading / live）
5. 設定検証（起動前チェック）
   ```bash
   python -m kabusys.validate_config
   # 警告を FAIL 扱いにする場合:
   python -m kabusys.validate_config --strict
   ```
6. データディレクトリの作成（必要に応じて）
   - デフォルトの DB / PID / flag は `data/` 配下に保存されます（例: data/monitoring.db, data/paper_trading.db, data/execution.pid, data/kill.flag）
7. OpenAI を利用する場合は環境変数 OPENAI_API_KEY を設定

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- KABUSYS_ENV: execution モード（development / paper_trading / live）デフォルト: development
  - paper_trading の場合、MockBrokerClient を使用し DB は PAPER_TRADING_SQLITE_PATH に分離されます
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (監視 DB。デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (ペーパートレード専用 DB。デフォルト: data/paper_trading.db)
- LOG_LEVEL (INFO 等、デフォルト: INFO)
- LOG_DIR (ログディレクトリ、デフォルト: logs)
- OPENAI_API_KEY (AI 機能で必要)
- PAPER_FILL_MODE (paper_trading の注文約定振る舞い。instant/partial/never/reject、デフォルト: instant)
- MONITOR_POLL_INTERVAL (run_monitoring のポーリング間隔秒、デフォルト: 60)

注意: run_monitoring は KABUSYS_ENV に依らず sqlite_path（本番 path）を使用して監視ログを残します。run_execution は KABUSYS_ENV=paper_trading の場合、paper_sqlite_path を使用します。

---

## 使い方（起動コマンド例）

- 監視ループを起動
  ```bash
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（秒、デフォルト 60）
  - 停止: プロジェクトルート/data/stop_requested.flag ファイルが存在するとループを終了します

- 実行エンジン（ExecutionEngine）を起動
  ```bash
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、ペーパートレード用 DB に記録されます
  - 停止: data/stop_requested.flag を作成すると稼働中のエンジンに停止を要求します
  - PID ファイル: data/execution.pid（デフォルト）にプロセス情報を保存

- 設定ウィザード
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  ```

- ペーパートレード検証レポート（tools）
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # or
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- AI スコアリング / レジーム判定 等はモジュール関数として利用できます（例）
  - kabusys.ai.score_news(conn, target_date, api_key=...)
  - kabusys.ai.regime_detector.score_regime(duckdb_conn, target_date, api_key=...)

---

## Stop / Kill フラグ

- stop_requested.flag
  - run_monitoring と run_execution の両方で監視される停止フラグ（data/stop_requested.flag）
  - 存在するとループが安全に終了します

- kill.flag
  - KillSwitch が作成するフラグ（data/kill.flag）
  - KillSwitch はドローダウンやポジション上限などの条件で ExecutionEngine 停止を要求します
  - Execution 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると自動でクリアされます（本番では推奨されません）

---

## ログ

- ログは stdout と日次ローテートファイル（logs/<app_name>.log）に出力されます。
- LOG_DIR にてログ出力先を変更可能。ログレベルは LOG_LEVEL で制御。

---

## ディレクトリ構成（抜粋）

リポジトリの主要ファイル構成（src/kabusys 以下）:

- src/kabusys/
  - __init__.py
  - config.py               — 環境変数設定読み取り / Settings
  - config_setup.py         — .env 対話ウィザード
  - validate_config.py      — 設定検証 CLI
  - run_monitoring.py       — SystemMonitor ポーリング起動
  - run_execution.py        — ExecutionEngine 起動
  - utils/
    - logging_setup.py      — ログ設定ユーティリティ
    - process_priority.py   — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py      — SQLite テーブル初期化 / 永続化層
    - system_monitor.py
    - trade_monitor.py      — (コードベース参照)
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - broker_factory.py
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

（上記は主要ファイルの抜粋です。詳細は src/kabusys 以下を参照してください）

---

## 運用上の注意 / ベストプラクティス

- 本番運用では KABUSYS_ENV=live とし、LINE 通知などのアラート設定が正しく行われていることを必ず確認してください。
- .env ファイルは機密情報を含みます。絶対に Git にコミットしないでください（config_setup.py のヘッダも同様に注意喚起しています）。
- ペーパートレード時は DB を本番 DB と分離してください（PAPER_TRADING_SQLITE_PATH）。
- Kill Switch 等の機構により重大インシデント発生時に自動停止できます。KILL_FLAG_CLEAR_ON_START の運用設定は慎重に行ってください（本番では 0 推奨）。
- OpenAI API を利用する機能は API 利用料が発生します。API キーの管理と呼び出し頻度に注意してください（バッチ処理・リトライ設計あり）。

---

## 開発者向けメモ

- DuckDB 接続を渡して純粋関数群（research, portfolio）が計算を行う設計です。ユニットテストは関数単位で行いやすくなっています。
- 外部 API 呼び出しは抽象化され、テスト時はモック差し替えを推奨します（news_nlp._call_openai_api 等を patch する例あり）。
- monitoring_db.init_monitoring_db() は冪等にテーブル・インデックスを作成し、簡単なマイグレーション（カラム追加）処理も行います。

---

README はここまでです。さらに運用手順（systemd / Supervisor 用のサービス定義、バックアップ・監視ツール連携など）や CI/CD、詳細なアーキテクチャ図が必要であれば、目的に合わせて追記できます。必要なら教えてください。