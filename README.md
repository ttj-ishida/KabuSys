# KabuSys

日本株向け自動売買システムの一部コンポーネント群（ライブラリ & 起動スクリプト）。  
本リポジトリには、実行エンジン・監視（Monitoring）・リサーチ/ファクター計算・AI 補助モジュールなどが含まれます。

## 概要

- ExecutionEngine（run_execution.py）: 発注ロジック・リスク管理・Order 管理を組み合わせて取引セッションを実行するエントリポイント。
  - `KABUSYS_ENV=paper_trading` のときは MockBrokerClient を使用し、paper_trading 用の SQLite（デフォルト: `data/paper_trading.db`）へ記録します（本番 DB と分離）。
- Monitoring（run_monitoring.py）: System / Trade / Risk の各監視をポーリングしてログ・アラート・Kill Switch を評価する監視プロセス。
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒、デフォルト 60）で上書き可能。
  - Monitoring は常に本番 `sqlite_path` を使用して監視 DB に記録します（`KABUSYS_ENV` に依存しない）。
- 設定関連 CLI:
  - `config_setup.py`: 対話式ウィザードで `.env` を作成/更新。
  - `validate_config.py`: `.env` や `config/*.yaml` の事前検証（`--strict` で警告を FAIL 扱い）。
- ツール:
  - `tools/paper_verification_report.py`: ペーパートレード履歴から検証レポートを生成。
- リサーチ / ポートフォリオ構築:
  - `research/*`, `portfolio/*`: ファクター計算、ポートフォリオ構築、サイズ決定、リスク調整などの純粋関数群（DB 参照箇所あり）。
- AI:
  - `ai/news_nlp.py`, `ai/regime_detector.py`：OpenAI を使ったニュースのセンチメント評価 / レジーム判定。API キーが必要。

## 主な機能一覧

- 起動スクリプト
  - run_execution (ExecutionEngine 起動)
  - run_monitoring (監視ループ起動)
- 設定管理
  - 対話式 `.env` ウィザード（config_setup）
  - 起動前チェック（validate_config）
- 監視
  - システム稼働 / データ鮮度監視（SystemMonitor）
  - 注文・約定ログ / 異常検知（TradeMonitor）
  - ドローダウン・ポジション上限監視（RiskMonitor）
  - Kill Switch（条件に応じて `data/kill.flag` を書き込み ExecutionEngine を停止）
- ロギング
  - 統一的な logging 設定（コンソール + 日次ローテーションファイル）
- リサーチ / ポートフォリオ
  - モメンタム・ボラティリティ・バリューなどのファクター計算（DuckDB を想定）
  - 候補選定、重み付け、ポジションサイジング、セクター上限適用
- AI 支援（OpenAI）によるニューススコアリングとレジーム判定（オプション）

## 必要環境 / 依存

- Python 3.10+（型ヒントの `|` を使用）
- 推奨パッケージ（例）:
  - duckdb
  - psutil
  - openai
  - PyYAML（`validate_config` の YAML 検証を有効にする場合）
- その他: sqlite3（標準）、logging（標準）

インストール例:
```bash
python -m pip install duckdb psutil openai PyYAML
```
（requirements.txt がある場合は `pip install -r requirements.txt` を使用）

## セットアップ手順

1. リポジトリルートに移動（`src` はパッケージソース）
2. `.env` の作成（対話式）
   ```bash
   python -m kabusys.config_setup
   ```
   ウィザードで以下の主要な環境変数を設定します（必須は明示）:
   - JQUANTS_REFRESH_TOKEN（必須）
   - KABU_API_PASSWORD（必須）
   - KABUSYS_ENV（development / paper_trading / live） — デフォルト: development
   - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH（デフォルト: data/monitoring.db）
   - PAPER_TRADING_SQLITE_PATH（ペーパートレード用 DB。paper_trading 時に使用）
   - OPENAI_API_KEY（AI 機能を使う場合）
   - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（通知用、任意）
   - LOG_LEVEL（INFO 等）
   - PAPER_FILL_MODE（paper_trading 用: instant / partial / never / reject）

3. 設定検証（起動前チェック）
   ```bash
   python -m kabusys.validate_config
   # 警告も失敗扱いにする場合
   python -m kabusys.validate_config --strict
   ```

4. データディレクトリ作成
   - `.env` で指定したパスの親ディレクトリ（例: `data/`, `logs/`）を作成します。`setup_logging` は自動で `logs/` を作成しようとしますが、権限等で失敗する可能性があります。

注意: Monitoring は本番の `SQLITE_PATH` を使います。ペーパートレードと本番 DB を混同しないよう `.env` を適切に設定してください。

## 実行方法（使い方）

- ExecutionEngine を起動（通常実行、本番では `KABUSYS_ENV=live`）
  ```bash
  # 本番・開発・ペーパーは KABUSYS_ENV で切り替え
  export KABUSYS_ENV=development   # or paper_trading / live
  python -m kabusys.run_execution
  ```
  特記事項:
  - `paper_trading` の場合は MockBrokerClient を使い、`PAPER_TRADING_SQLITE_PATH`（デフォルト `data/paper_trading.db`）に記録されます。
  - 実行中、プロセス優先度が `high` に設定されます（可能な範囲で）。
  - 停止シグナルは `data/stop_requested.flag` または監視側の `data/kill.flag` によって与えられます（フラグを作成するとエンジンは安全に停止します）。
  - 実行時は `data/execution.pid` に PID を書きます。

- Monitoring を起動（監視ポーリング）
  ```bash
  # ポーリング間隔を秒で指定（任意）
  export MONITOR_POLL_INTERVAL=60
  python -m kabusys.run_monitoring
  ```
  特記事項:
  - デフォルトポーリング間隔は 60 秒。`MONITOR_POLL_INTERVAL` で上書きできます（1 以上の整数）。
  - Monitoring は常に `.env` の `SQLITE_PATH`（本番監視 DB）を使用して監視情報を記録します。
  - Monitoring は `data/stop_requested.flag` を検知するとループを終了します。

- Paper Trading 検証レポート出力
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # デフォルト DB は 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db
  ```

- AI 機能（ニュース NLP / レジーム判定）
  - `OPENAI_API_KEY` を `.env` に設定するか、関数呼び出し時に `api_key` を渡します。
  - これらの関数は DuckDB 接続と target_date を受け取り、DB に結果を書き込みます（OpenAI 呼び出しを行います）。

## 主要ファイル・実行モジュール

- 起動スクリプト
  - src/kabusys/run_execution.py
  - src/kabusys/run_monitoring.py
- 設定 / ユーティリティ
  - src/kabusys/config.py
  - src/kabusys/config_setup.py
  - src/kabusys/validate_config.py
  - src/kabusys/utils/logging_setup.py
  - src/kabusys/utils/process_priority.py
- 監視（monitoring）
  - src/kabusys/monitoring/monitoring_db.py
  - src/kabusys/monitoring/system_monitor.py
  - src/kabusys/monitoring/trade_monitor.py (参照)
  - src/kabusys/monitoring/risk_monitor.py
  - src/kabusys/monitoring/kill_switch.py
  - src/kabusys/monitoring/monitoring_engine.py
  - src/kabusys/run_monitoring.py
- 実行（execution）関連（主要クラスは参照）
  - src/kabusys/execution/* (Engine, OrderManager, BrokerFactory, RiskManager, Reconciler, Repository 等)
  - src/kabusys/run_execution.py
- ポートフォリオ / リサーチ
  - src/kabusys/portfolio/*
  - src/kabusys/research/*
- AI
  - src/kabusys/ai/news_nlp.py
  - src/kabusys/ai/regime_detector.py
- ツール
  - src/kabusys/tools/paper_verification_report.py

## ディレクトリ構成 (抜粋)

- src/
  - kabusys/
    - __init__.py
    - run_execution.py
    - run_monitoring.py
    - config.py
    - config_setup.py
    - validate_config.py
    - utils/
      - logging_setup.py
      - process_priority.py
    - monitoring/
      - monitoring_db.py
      - system_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - monitoring_engine.py
      - trade_monitor.py
      - alert_manager.py (参照)
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
    - data/ (実行時に生成されることが多い)
      - monitoring.db (デフォルト)
      - paper_trading.db (paper_trading 用)
      - kill.flag
      - stop_requested.flag
      - execution.pid
    - logs/
      - execution.log
      - monitoring.log

## 運用上の注意 / 補足

- Kill Switch:
  - RiskMonitor 等が条件を満たした場合、`data/kill.flag` を生成して ExecutionEngine に停止シグナルを送ります。`KILL_FLAG_CLEAR_ON_START` が `1` の場合、起動時に自動クリアされる設定がありますが、本番では `0` を推奨します。
- DB：
  - Monitoring 用の SQLite（`SQLITE_PATH`）と Paper Trading 用の SQLite（`PAPER_TRADING_SQLITE_PATH`）は目的に応じて分離してください。Monitoring は常に `SQLITE_PATH` を使用します。
- ロギング：
  - `kabusys.utils.logging_setup.setup_logging` が標準化されたログ出力（stdout + 日次ローテーション）を行います。ログディレクトリは `LOG_DIR` 環境変数または `logs/` が使われます。
- セキュリティ：
  - `.env` は機密情報（API トークン・パスワード）を含みます。絶対にリポジトリへコミットしないでください（config_setup のヘッダにも注意書きがあります）。
- テスト / 開発：
  - 自動環境ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化できます（テスト時に便利）。

---

何か追加したい項目（例: 具体的な config/*.yaml の説明、execution の詳細な起動オプション、テストの実行方法 など）があれば教えてください。README に追記します。