# KabuSys

日本株自動売買システム（ライブラリ / 実行スクリプト群）

本リポジトリは、戦略・ポートフォリオ構築、発注実行（本番 / ペーパートレード）、監視、リサーチ、AI（ニュース NLP / レジーム判定）を含む自動売買システムのコア実装です。

---

## プロジェクト概要

- 戦略・ファクター計算（research）
- ポートフォリオ構築（portfolio）
- 発注実行エンジン（execution）：本番とペーパートレードを切替可能
- 監視コンポーネント（monitoring）：システム状態・注文・リスク監視、Kill Switch
- AI モジュール（ai）：ニュースのセンチメント評価／レジーム判定（OpenAI）
- ユーティリティ（utils）：ログ設定、プロセス優先度設定 等
- 永続化：DuckDB（分析用）／SQLite（監視・発注ログ）

設計方針の一部：
- 重要な処理は入出力が分かる純粋関数群で実装（テスト容易）
- 本番 DB とペーパートレード DB は明確に分離
- 外部 API（OpenAI 等）呼び出しはリトライ・フォールバックを備えた実装

---

## 主な機能一覧

- Execution
  - ExecutionEngine（本番 / ペーパートレード切替）
  - BrokerClientFactory による broker クライアントの抽象化
  - OrderRepository / OrderManager / Reconciler / RiskManager
- Monitoring
  - SystemMonitor: CPU / メモリ / ディスク / プロセス状態 / データ鮮度
  - TradeMonitor: 注文滞留、約定異常等の検出
  - RiskMonitor: ドローダウン・ポジション上限監視、ダッシュボード更新
  - KillSwitch: 条件により data/kill.flag を書き込み ExecutionEngine を停止
  - MonitoringEngine: 各モニタをまとめて定期実行
- Research / Data
  - factor_research: モメンタム / バリュー / ボラティリティ等のファクター計算（DuckDB）
  - feature_exploration: 将来リターン、IC、統計サマリ
- AI
  - news_nlp: raw_news を集約して OpenAI に投げ、銘柄ごとのセンチメントを ai_scores に保存
  - regime_detector: ETF (1321) の MA とマクロニュースの LLM 判定を合成して market_regime を記録
- Tools
  - paper_verification_report: ペーパートレード DB を集計し検証レポートを出力
- 設定周り
  - config_setup: .env の対話式ウィザード
  - validate_config: .env / config/*.yaml の事前検証 CLI
- Utilities
  - setup_logging: 統一ログ設定（コンソール + 日次ローテートファイル）
  - process_priority: プロセス優先度・CPU affinity 設定

---

## セットアップ手順

前提
- Python 3.10 以上（型ヒント等を利用）
- システムにより追加の依存が必要（例: psutil）

推奨パッケージ（最低限）
- duckdb
- psutil
- openai
- PyYAML（validate_config で YAML 検証を行う場合）

例: 仮想環境作成とパッケージインストール
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb psutil openai PyYAML
```

環境変数 / .env
- プロジェクトルートに `.env` を置くか、環境変数で設定します。
- 主要な必須変数:
  - JQUANTS_REFRESH_TOKEN（必須）
  - KABU_API_PASSWORD（必須）
- その他よく使う変数:
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - DUCKDB_PATH: 分析用 DuckDB パス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
  - OPENAI_API_KEY: OpenAI を使う場合に必要
  - LOG_LEVEL: DEBUG/INFO/...
  - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
  - PAPER_FILL_MODE: ペーパートレード時の約定挙動（instant/partial/never/reject）

.env を対話式に作る:
```bash
python -m kabusys.config_setup
```

設定検証:
```bash
python -m kabusys.validate_config      # 警告は許容
python -m kabusys.validate_config --strict  # 警告も失敗扱い
```

データディレクトリ:
- デフォルトで `data/` 配下に DB / PID / flag 等を作成します。必要に応じて `.env` でパスを変更してください。

---

## 使い方

起動スクリプト（モジュール実行形式）:

- ExecutionEngine（エンジン起動）
  - 本番 / ペーパートレード切り替えは KABUSYS_ENV に依存
  - ペーパートレード時は専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用
  - 起動:
    ```bash
    python -m kabusys.run_execution
    ```
  - 停止:
    - 外部で `data/stop_requested.flag` を作成すると起動中スレッドが検出して停止します
    - KillSwitch により `data/kill.flag` が作られると ExecutionEngine に停止シグナルが送られます

- Monitoring（監視ループ起動）
  - 環境に関わらず monitoring は本番 sqlite_path（SQLITE_PATH）を使用します
  - ポーリング間隔の上書き:
    - 環境変数 MONITOR_POLL_INTERVAL（秒）
  - 起動:
    ```bash
    python -m kabusys.run_monitoring
    ```
  - 停止:
    - `data/stop_requested.flag` を作成することで停止します

- 設定ウィザード / 検証:
  ```bash
  python -m kabusys.config_setup
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート:
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB パスを直接指定する場合
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- AI モジュール（プログラムから利用）
  - news_nlp.score_news(conn, target_date, api_key=None)
  - ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - 注意: OpenAI API キーは引数で渡すか OPENAI_API_KEY 環境変数を設定

ログ
- デフォルトで `logs/` に日次ローテートのログファイルが出力されます（setup_logging）。
- コンソールは stdout に出力されます。

重要なファイル / フラグ
- data/stop_requested.flag: run_monitoring / run_execution が監視している停止フラグ
- data/kill.flag: KillSwitch が書き込む停止要求（ExecutionEngine 側で確認）
- data/execution.pid: 実行エンジンの PID ファイル（デフォルトパス）

---

## ディレクトリ構成

主要なファイル・モジュール（src/kabusys 配下）

- __init__.py
- config.py — 環境変数／設定読み込みロジック、Settings クラス
- config_setup.py — .env 対話式ウィザード
- validate_config.py — 設定検証 CLI

- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト

- ai/
  - news_nlp.py — ニュース NLP スコアリング（OpenAI）
  - regime_detector.py — 市場レジーム判定（MA + LLM）

- monitoring/
  - monitoring_db.py — SQLite 永続化レイヤ（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py — システム状態・データ鮮度監視
  - trade_monitor.py — （注文監視ロジック、該当ソース参照）
  - risk_monitor.py — ドローダウン・ポジション監視
  - monitoring_engine.py — 各モニタを束ねる実行エンジン
  - kill_switch.py — kill.flag 書き込みユーティリティ
  - alert_manager.py — （通知ロジック、該当ソース参照）

- execution/
  - execution_engine.py
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - risk_manager.py
  - broker_factory.py

- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py

- research/
  - factor_research.py
  - feature_exploration.py

- monitoring/
  - tools / その他のユーティリティ群

- utils/
  - logging_setup.py — ログ設定ユーティリティ
  - process_priority.py — プロセス優先度設定ユーティリティ

- tools/
  - paper_verification_report.py — ペーパートレード検証レポート

（上記は代表的ファイル一覧。実装全体は src/kabusys 以下を参照してください。）

---

## 運用上の注意 / ヒント

- 本番実行時（KABUSYS_ENV=live）は特に注意:
  - .env は絶対に Git にコミットしないでください
  - Kill Switch（KILL_FLAG）や監視の設定を慎重に扱ってください
- monitoring は SQLITE_PATH を使用して監視ログを永続化します。監視は本番 DB を参照してアラートを出すため、環境差分に注意してください。
- OpenAI を利用する機能は API キーとコスト、レート制限に注意してください。API 呼び出しはリトライとフォールバックを備えていますが、運用上のポリシーを設けてください。
- ペーパートレード（KABUSYS_ENV=paper_trading）は本番 DB と分離され、PAPER_TRADING_SQLITE_PATH に保存されます。ペーパートレードの挙動は PAPER_FILL_MODE により制御可能です。

---

もし README に追加したい項目（例えばサンプル .env テンプレート、手順のスクリーンショット、より詳細な起動例や systemd / supervisor 用のサービスユニット例）があれば教えてください。必要に応じて追記します。