# KabuSys

日本株向け自動売買システムのライブラリ群・実行スクリプト群です。  
このリポジトリは、シグナル作成 → ポートフォリオ構築 → 発注ロジック → 監視・アラート → 研究用分析・AI スコアリングまで、一連の機能をモジュール化しています。

バージョン: 0.1.0

---

## プロジェクト概要

主な目的は以下です。

- 株式投資アルゴリズム（ファクター計算、シグナル生成、ポートフォリオ構築）を提供
- 発注実行エンジン（ExecutionEngine）と発注管理（OrderManager / RiskManager）を提供
- 監視モジュール（SystemMonitor / TradeMonitor / RiskMonitor）による運用時の健全性チェックと Kill Switch
- ニュース NLP（OpenAI）を用いたセンチメントスコアリングと市場レジーム判定
- Paper Trading 用の分離された DB と検証レポート生成ツール
- 開発者支援ツール：.env 対話式ウィザード、設定検証 CLI、ログ設定ユーティリティ など

設計上の特徴:

- DuckDB（分析用）、SQLite（監視 / 注文ログ）を併用
- 環境に応じて本番 / ペーパートレード DB を分離
- LLM（OpenAI）との連携はオプション（API キーが必要）
- 主要機能は純粋関数（テストしやすい）と DB 永続化層で明確に分離

---

## 機能一覧

- 設定管理
  - .env の自動ロード（.env / .env.local）、config ウィザード（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）

- 実行 / 発注
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - BrokerClientFactory から実口座 or MockBroker を切替（KABUSYS_ENV=paper_trading）
  - RiskManager / OrderManager / Reconciler

- 監視 / アラート
  - SystemMonitor: CPU / メモリ / ディスク / プロセスヘルス / データ鮮度
  - TradeMonitor: 注文滞留・約定異常監視（trade_logs）
  - RiskMonitor: ドローダウン・ポジション上限検出 + dashboard 更新
  - KillSwitch: 条件トリガで data/kill.flag を作成して ExecutionEngine に停止シグナル
  - MonitoringEngine / run_monitoring.py による定期ポーリングとログ永続化

- ポートフォリオ構築
  - 候補選定（select_candidates）
  - 重み計算（等金額 / スコア加重）
  - セクター制約, レジーム乗数（apply_sector_cap, calc_regime_multiplier）
  - 株数決定（calc_position_sizes） — 単元株・リスクベース配分・aggregate キャップ処理

- 研究（Research）
  - ファクター計算（momentum / volatility / value）
  - 将来リターン・IC 計算・統計サマリ（feature_exploration）

- AI（任意）
  - ニュース NLP スコアリング（ai.news_nlp: score_news）
  - 市場レジーム判定（ai.regime_detector: score_regime）
  - OpenAI（gpt-4o-mini）を用いた JSON 出力想定。API キー必須。

- ツール
  - Paper Trading 検証レポート生成（tools/paper_verification_report.py）

- ロギング / 実行環境
  - 統一的ログ設定ユーティリティ（utils.logging_setup）
  - プロセス優先度設定 / CPU affinity ヘルパ（utils.process_priority）

---

## セットアップ手順

前提
- Python 3.9+ 推奨（typing, pathlib 等を使用）
- システムに sqlite3 は組み込み（Python 標準）
- 必要パッケージ（最低限）:
  - duckdb
  - psutil
  - openai（AI 機能利用時）
  - （任意）PyYAML（validate_config の YAML 検証を行う場合）

例（venv 使用）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb psutil
# OpenAI 機能を使う場合:
pip install openai
# PyYAML は任意（設定 YAML 検証）
pip install pyyaml
```

.env の準備
- 対話式ウィザードを使って .env を作成できます:
  ```bash
  python -m kabusys.config_setup
  ```
- 主要な必須環境変数:
  - JQUANTS_REFRESH_TOKEN（必須）
  - KABU_API_PASSWORD（必須）
- AI 機能を使う場合:
  - OPENAI_API_KEY を環境変数に設定（または呼び出し時に API キーを渡す）

自動ロードについて
- パッケージの import 時にプロジェクトルート（.git または pyproject.toml）から .env/.env.local を自動読み込みします。
- 自動ロードを無効にするには環境変数:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1

ログディレクトリ
- デフォルトは `logs/`。`LOG_DIR` 環境変数で変更可。

---

## 主要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- OPENAI_API_KEY (AI 機能を使用する場合)
- KABUSYS_ENV (development | paper_trading | live) — default: development
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL)
- LOG_DIR (ログ保存先)
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (監視 DB, default: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB, default: data/paper_trading.db)
- PAPER_FILL_MODE (instant|partial|never|reject) — paper_trading の約定モード
- PID_FILE_PATH (default: data/execution.pid)
- KILL_FLAG_PATH (default: data/kill.flag)
- KILL_FLAG_CLEAR_ON_START (0|1)
- MONITOR_POLL_INTERVAL (run_monitoring のポーリング間隔秒, default: 60)

config/load の優先順:
- OS 環境変数 > .env.local > .env

---

## 使い方（実行例）

1. 設定検証（起動前チェック）
   ```bash
   python -m kabusys.validate_config
   # 警告も失敗扱いにする場合:
   python -m kabusys.validate_config --strict
   ```

2. 実行環境の初期設定（.env の作成）
   ```bash
   python -m kabusys.config_setup
   ```

3. 実行エンジンの起動
   - 本番 / 開発 / ペーパートレードは KABUSYS_ENV によって振る舞いが変わります。
   - Paper Trading の場合、MockBrokerClient が使用され `data/paper_trading.db` に書き込まれます。
   ```bash
   # 例: ペーパートレード
   export KABUSYS_ENV=paper_trading
   python -m kabusys.run_execution
   ```
   - 実行中に停止させたい場合は `data/stop_requested.flag` を作成するか、Execution 側の kill.flag を使ってください（KillSwitch が動作する設定の場合）。

4. 監視ループの起動
   ```bash
   # ポーリング間隔を環境変数で上書き（秒）
   export MONITOR_POLL_INTERVAL=30
   python -m kabusys.run_monitoring
   ```
   - 監視スクリプトは `MONITOR_POLL_INTERVAL`（デフォルト 60 秒）で各 Monitor を定期実行し、SQLite にログを書き込みます。
   - 監視は常に本番用の sqlite_path（Settings.sqlite_path）を使用します（環境に依らず）。

5. Paper Trading 検証レポート
   ```bash
   # デフォルト DB: data/paper_trading.db
   python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   # 別 DB を指定する場合
   python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
   ```

6. AI 機能
   - OpenAI API キーが必要です（OPENAI_API_KEY 環境変数または関数引数）。
   - 例（モジュール呼び出し）:
     ```python
     from kabusys.ai.news_nlp import score_news
     import duckdb
     conn = duckdb.connect("data/kabusys.duckdb")
     score_news(conn, target_date=datetime.date(2026,4,10))
     ```

注意:
- 実行スクリプトはプロセス優先度を "high" に設定しようとします（権限がないと警告になります）。
- stop フラグのファイル名:
  - run_execution/run_monitoring ともにプロジェクト内 `data/stop_requested.flag` を参照して直ちに終了します（ファイル存在チェック）。
  - KillSwitch は `Settings.kill_flag_path`（デフォルト data/kill.flag）を使用します。

---

## ディレクトリ構成

主要なファイル / モジュールの簡易ツリー:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring ポーリングループ起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py
  - execution/               — 発注実行関連（Engine, OrderManager, BrokerFactory 等）
    - (ExecutionEngine, OrderManager, BrokerClientFactory, RiskManager, Reconciler, ...)
  - monitoring/
    - monitoring_db.py       — SQLite 永続化レイヤ
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - utils/
    - logging_setup.py
    - process_priority.py
    - __init__.py
  - data/                    — 実行時に使用するファイル（DB / pid / flag 等）
    - monitoring.db (default SQLite)
    - paper_trading.db (paper trading 用)
    - kabusys.duckdb (DuckDB)
    - execution.pid
    - kill.flag / stop_requested.flag

（実際のリポジトリには上記以外の補助ファイルや module が存在する場合があります）

---

## 運用上の注意 / ベストプラクティス

- 本番運用前に必ず `python -m kabusys.validate_config --strict` を実行して設定を検証してください。
- 本番（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START を `0` にすることを推奨します。
- OpenAI を利用する機能は外部 API 呼び出しを伴いコストが発生します。API キーの権限と課金に注意してください。
- ログは `logs/<app_name>.log` に日次ローテーションで出力されます。十分なディスク容量を確保してください。
- psutil によるプロセス優先度設定や CPU affinity 設定は権限に依存します。権限不足の場合は警告でスキップされます。

---

この README はコードベースの主要モジュールをカバーしています。詳細な実装や追加の CLI、設定ファイルテンプレートは各モジュールの docstring / コメントを参照してください。必要であれば、特定モジュール（例: ExecutionEngine の設定例、ポートフォリオチューニングパラメータ）の詳しいドキュメントを追加します。