# KabuSys

日本株向け自動売買システム（ライブラリ＋実行スクリプト群）です。  
本リポジトリは以下の主要機能を含みます：発注エンジン（ExecutionEngine）、監視 / Kill Switch、ポートフォリオ構築ユーティリティ、リサーチ（ファクター計算／特徴量探索）、ニュース NLP（OpenAI を用いたセンチメント）、ペーパートレード検証ツールなど。

バージョン: 0.1.0

---

## 主な特徴

- ExecutionEngine
  - live / paper_trading / development の実行モード対応
  - ブローカークライアントは環境に応じて実装が切り替わり、ペーパートレードは本番 DB と分離（`data/paper_trading.db`）
  - リスク管理（Rate limit・最大ポジション・ドローダウン等）

- Monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor を統合する MonitoringEngine
  - Kill Switch（条件を満たすと `data/kill.flag` を書き込み、Execution を停止）
  - 監視ログを SQLite（`monitoring.db`）に永続化

- ポートフォリオ構築（純粋関数）
  - 候補選定、等金額／スコア加重配分、単元株丸め、リスク調整（セクターキャップ、レジーム乗数）

- リサーチ
  - DuckDB を用いたファクター計算（Momentum / Volatility / Value 等）
  - 将来リターン、IC（Information Coefficient）等の統計解析ユーティリティ

- AI（OpenAI）
  - ニュース記事の銘柄別センチメントスコア化（`kabusys.ai.news_nlp.score_news`）
  - マクロ＋ETF（1321）MA200 を用いた市場レジーム判定（`kabusys.ai.regime_detector.score_regime`）
  - API呼び出しはリトライ／フォールバック設計

- 開発者向けツール
  - .env 対話式ウィザード（`python -m kabusys.config_setup`）
  - 設定検証 CLI（`python -m kabusys.validate_config`）
  - ペーパートレード検証レポート（`python -m kabusys.tools.paper_verification_report`）

---

## 必要要件（例）

- Python 3.9+
- 必須パッケージ（代表）
  - duckdb
  - psutil
  - openai
  - （任意）PyYAML（`validate_config` で config/*.yaml を検証する場合）
- SQLite（組み込み）
- ネットワーク（kabuステーション API / OpenAI を使う場合）

※requirements.txt は本リポジトリに含まれていないため、環境に合わせてインストールしてください。

例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```

---

## セットアップ手順（概略）

1. リポジトリをチェックアウトし、仮想環境を作成／有効化
2. 依存パッケージをインストール（上記参照）
3. `.env` を作成
   - 対話式ウィザード:
     ```bash
     python -m kabusys.config_setup
     ```
   - または手動で `.env` を作成（下記に主要変数を記載）
4. 設定検証:
   ```bash
   python -m kabusys.validate_config
   ```
5. 必要なディレクトリ（`data/`, `logs/` 等）が自動生成されますが、権限等を確認してください。

---

## 主な環境変数（抜粋）

- 認証系
  - JQUANTS_REFRESH_TOKEN (必須)
  - KABU_API_PASSWORD (必須)
  - OPENAI_API_KEY (AI 機能を使う場合)

- 実行環境
  - KABUSYS_ENV: `development` | `paper_trading` | `live`（default: development）
  - LOG_LEVEL: `DEBUG` | `INFO` | `WARNING` | `ERROR` | `CRITICAL`（default: INFO）
  - LOG_DIR: ログ保存ディレクトリ（default: logs/）

- DB 関連
  - DUCKDB_PATH（default: data/kabusys.duckdb）
  - SQLITE_PATH（監視 DB, default: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB, default: data/paper_trading.db）

- Paper Trading / Broker
  - PAPER_FILL_MODE: `instant` | `partial` | `never` | `reject`（default: instant）

- Kill Switch / 起動制御
  - KILL_FLAG_CLEAR_ON_START: `0` | `1`（本番では `0` 推奨）
  - KILL_FLAG_PATH（default: data/kill.flag）
  - PID_FILE_PATH（default: data/execution.pid）

- Monitoring
  - MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒, default: 60）

---

## 使い方（起動 / CLI）

- ExecutionEngine を起動
  - 実行:
    ```bash
    python -m kabusys.run_execution
    ```
  - 備考:
    - `KABUSYS_ENV=paper_trading` の場合、MockBrokerClient を使用し、`PAPER_TRADING_SQLITE_PATH` の DB に記録します（本番 DB と完全分離）。
    - 起動時に `data/stop_requested.flag` が既に存在する場合は起動せず終了します。
    - `data/execution.pid` が作成されます。

- Monitoring を起動
  - 実行:
    ```bash
    python -m kabusys.run_monitoring
    ```
  - 環境変数でポーリング間隔を上書き:
    ```bash
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    ```
  - 備考:
    - Monitoring は実行環境にかかわらず本番の `SQLITE_PATH` を使用して監視ログを記録します（監視データは production path に保存される仕様）。
    - 停止は `data/stop_requested.flag` を作成（または SIGINT）で行えます。

- 設定検証
  ```bash
  python -m kabusys.validate_config
  # 警告を失敗扱いにする:
  python -m kabusys.validate_config --strict
  ```

- .env 対話式作成
  ```bash
  python -m kabusys.config_setup
  ```

- ペーパートレード検証レポート
  ```bash
  # デフォルト DB (data/paper_trading.db) を使う
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

  # 別 DB を指定
  python -m kabusys.tools.paper_verification_report --db /path/to/db.sqlite
  ```

---

## 停止 / Kill Switch

- ExecutionEngine を外部から停止する方法:
  - Monitoring の KillSwitch が条件を満たすと `data/kill.flag` を作成します。Execution 側はこのフラグを検知して安全に停止します。
  - 手動停止: `data/stop_requested.flag` を作成すると、run_execution / run_monitoring の起動ループが終了します。
- `KILL_FLAG_CLEAR_ON_START=1` を設定すると ExecutionEngine 起動時に `kill.flag` を自動で削除します（本番では `0` 推奨）。

---

## ライブラリ API（開発者向け）

- ポートフォリオ:
  - select_candidates / calc_equal_weights / calc_score_weights
  - calc_position_sizes
  - apply_sector_cap / calc_regime_multiplier

- リサーチ:
  - calc_momentum(conn, target_date)
  - calc_volatility(conn, target_date)
  - calc_value(conn, target_date)
  - calc_forward_returns, calc_ic, factor_summary, rank

- AI:
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

- Monitoring DB:
  - MonitoringDB(conn) — system_status / trade_logs / positions / risk_logs / dashboard の読み書き

- ユーティリティ:
  - setup_logging(app_name, log_dir, level)
  - set_process_priority(level), set_cpu_affinity(n)

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / Settings クラス（自動 .env ロード機能含む）
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
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
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - (その他 alert_manager, trade_monitor 等のモジュール)
  - execution/
    - (broker_factory, execution_engine, order_manager, order_repository, reconciler, risk_manager 等)
  - utils/
    - logging_setup.py
    - process_priority.py

---

## 注意事項 / 運用上のヒント

- 本番運用時は `KABUSYS_ENV=live` とし、`KILL_FLAG_CLEAR_ON_START=0` を推奨します。
- Monitoring は常に production の sqlite（`SQLITE_PATH`）を参照するため、監視ログとペーパートレードログが混同しないように `PAPER_TRADING_SQLITE_PATH` を明確に設定してください。
- OpenAI や外部 API のキーは `.env` に保存せず、運用環境のシークレット管理（Vault 等）を検討してください。
- `logs/` に出力されるログは日次ローテーションされます（デフォルト 30 日保持）。
- SQLite / DuckDB のファイルパスに注意し、バックアップやスナップショットを検討してください。
- `validate_config` は PyYAML が無ければ YAML 検査をスキップする点に注意（警告が出ます）。

---

## サポート / 追加情報

- 仕様や設計文書（例: PortfolioConstruction.md, StrategyModel.md）が参照されている箇所があります。実装の理解や拡張時はそれらを参照してください（本 README には含まれていません）。
- この README はコードベースの主要ポイントを簡潔にまとめたものです。詳細は各モジュールの docstring を参照してください。

---

最小限の導入フロー（例）
1. 仮想環境を作成・有効化
2. パッケージをインストール
3. python -m kabusys.config_setup で .env を作成
4. python -m kabusys.validate_config で確認
5. python -m kabusys.run_execution を起動（paper_trading を使う場合は KABUSYS_ENV=paper_trading を設定）
6. python -m kabusys.run_monitoring を別プロセスで起動

問題や拡張の相談があれば、実行環境とログを添えて問い合わせてください。