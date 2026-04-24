# KabuSys

日本株向け自動売買システムの一部（ライブラリ・運用スクリプト群）。  
このリポジトリには、監視・実行エンジンの起動スクリプト、環境設定ウィザード、検証ツール、研究用/AI 用モジュール、ポートフォリオ構築ロジックなどが含まれます。

以下はプロジェクトの簡単な説明、主要機能、セットアップ手順、使い方、ディレクトリ構成の案内です。

---

## プロジェクト概要

- 目的: 日本株自動売買の運用に必要な監視（Monitoring）、注文実行（Execution）、ログ永続化、リスク監視、ファクター計算、ニュースNLP（OpenAI）を統合するためのライブラリ群と起動スクリプトを提供します。
- 設計方針:
  - 環境変数 / .env による設定管理。
  - 本番/ペーパートレードを環境変数 `KABUSYS_ENV` で切り替え（`development` / `paper_trading` / `live`）。
  - SQLite（監視・発注ログ）と DuckDB（分析用）を併用。
  - OpenAI API を用いたニュースセンチメント / レジーム判定機能（オプション）。

---

## 主な機能一覧

- 起動スクリプト
  - run_execution.py — ExecutionEngine 起動（本番 or paper_trading 切替）
  - run_monitoring.py — SystemMonitor のポーリングループ起動
- 設定管理・検証
  - config_setup.py — 対話式 .env 作成ウィザード
  - validate_config.py — .env / config/*.yaml の起動前チェック
- 監視（monitoring）
  - system_monitor / trade_monitor / risk_monitor / kill_switch / monitoring_engine
  - 監視ログの永続化（SQLite via monitoring_db.py）
  - Kill Switch（条件により `data/kill.flag` を書き込み、ExecutionEngine を停止）
- 発注・実行（execution）
  - ExecutionEngine（発注・オーダー管理・リスク管理等） — run_execution.py から起動
  - Paper Trading と本番 DB の分離（`PAPER_TRADING_SQLITE_PATH`）
- 研究・分析（research）
  - ファクター計算（momentum/value/volatility）
  - 特徴量探索（IC 計算等）
- AI（ai）
  - ニュース NLP（OpenAI）による銘柄単位センチメント取得（news_nlp）
  - 市場レジーム判定（regime_detector）
- ポートフォリオ構築（portfolio）
  - 候補選定、重み付け、ポジションサイズ計算、セクター上限・レジーム調整
- ツール
  - tools.paper_verification_report — Paper Trading 検証レポート生成

---

## セットアップ手順（ローカル開発向け）

1. Python 環境準備
   - 推奨: Python 3.10+
   - 仮想環境を作成・有効化:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - 本リポジトリには requirements.txt を明示していませんが、使用されている主要ライブラリは以下です:
     - duckdb, psutil, openai, sqlite3（標準ライブラリ）
     - （必要に応じて PyYAML をインストールすると validate_config の YAML 検証が有効になります）
   - 例:
     - pip install duckdb psutil openai PyYAML

3. .env ファイル作成（推奨: 対話式ウィザードを利用）
   - 対話式生成:
     - python -m kabusys.config_setup
   - もしくは手動でプロジェクトルートに `.env` を作成（`.env.example` を参照してください）。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
   - 重要な設定例:
     - KABUSYS_ENV (development/paper_trading/live)
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (監視 DB, デフォルト: data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (paper_trading の場合の専用 DB)
     - OPENAI_API_KEY (AI 機能を使う場合)
     - LOG_LEVEL / LOG_DIR

4. 設定の検証（任意だが推奨）
   - python -m kabusys.validate_config
   - 警告までエラー扱いにしたい場合:
     - python -m kabusys.validate_config --strict

5. データディレクトリ作成（自動で作られる場合もありますが、手動作成しておくと安全）
   - mkdir -p data logs

---

## 使い方（起動・主要コマンド）

- ログ設定
  - ログは stdout に出力され、日次ローテーションで logs/<app_name>.log に出力されます。
  - 環境変数 `LOG_DIR` / `LOG_LEVEL` が使用可能。

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - 起動時にプロセス優先度を "high" に設定します（set_process_priority）。
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒、デフォルト 60）で上書き可能。
  - 監視ループを速やかに停止するには、プロジェクトルートの `data/stop_requested.flag` を作成してください（存在を検出してループが終了します）。

- 実行エンジン起動（Execution）
  - python -m kabusys.run_execution
  - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を使用し、発注ログ等は `data/paper_trading.db`（または `PAPER_TRADING_SQLITE_PATH`）に記録され、本番 DB と完全分離されます。
  - 実行中に停止するには、`data/stop_requested.flag` を作成するか、Monitoring の Kill Switch が `data/kill.flag` を書き込むと ExecutionEngine が停止します（`KILL_FLAG_CLEAR_ON_START` の設定に注意）。

- .env の作成/更新（対話式）
  - python -m kabusys.config_setup

- 設定の検証
  - python -m kabusys.validate_config
  - --strict を付けると警告を FAIL 扱いにします。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を明示する:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI 機能（ニュース NLP / レジーム）
  - ai モジュールは OpenAI API を使用します。API キーは環境変数 `OPENAI_API_KEY` または関数引数で指定してください。
  - ニューススコアリング: kabusys.ai.score_news（DuckDB 接続を渡して使用）

---

## 運用上の重要なファイル / フラグ

- data/stop_requested.flag
  - run_monitoring.py / run_execution.py のループを優雅に停止させるためのフラグ。ファイルが存在するとループが終了します。

- data/kill.flag
  - KillSwitch が条件を満たしたときに書き込まれるファイル。ExecutionEngine 側で検出して安全に停止するトリガーとして使用。

- data/execution.pid（既定）
  - ExecutionEngine の PID ファイル（Settings.pid_file_path で指定可能）。

- データベース
  - DuckDB: デフォルト `data/kabusys.duckdb`（分析用）
  - SQLite (monitoring): デフォルト `data/monitoring.db`（監視・ログ）
  - SQLite (paper_trading): デフォルト `data/paper_trading.db`（paper_trading 用に分離）

---

## 設定（主な環境変数）

- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- LOG_DIR: ログディレクトリ（デフォルト: logs/）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使用する場合）
- MONITOR_POLL_INTERVAL: SystemMonitor のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に既存の kill.flag を自動クリアするか（"1" でクリア。production では注意）

設定の大半は `kabusys.config.Settings` クラスから参照されます。必須キーが未設定だと起動時にエラーになります。

---

## ディレクトリ構成（主要ファイルの説明）

src/kabusys/
- __init__.py
- config.py
  - 環境変数読み込み・.env 自動読み込みロジック・Settings クラス
- config_setup.py
  - 対話式 .env 作成ウィザード
- validate_config.py
  - 起動前検証 CLI
- run_execution.py
  - ExecutionEngine 起動スクリプト（paper_trading 切替対応）
- run_monitoring.py
  - SystemMonitor ポーリングループ起動スクリプト

サブパッケージ:
- ai/
  - news_nlp.py — ニュースを OpenAI でスコアリング、ai_scores テーブルへ書き込み
  - regime_detector.py — マクロ + ETF MA200 を合成して市場レジーム判定
- monitoring/
  - monitoring_db.py — SQLite 永続化層（system_status / trade_logs / positions / risk_logs / dashboard）
  - system_monitor.py — CPU/Mem/Disk/プロセス状態・データ鮮度監視
  - trade_monitor.py — （発注ログ監視、滞留注文など）
  - risk_monitor.py — ドローダウン / ポジション上限監視
  - kill_switch.py — kill.flag の評価・書き込みロジック
  - monitoring_engine.py — 各 Monitor を束ねてポーリング
  - alert_manager.py —（アラート送信管理 ※コード参照）
- execution/
  - ExecutionEngine, OrderManager, RiskManager, Reconciler, BrokerClientFactory など（発注ロジック）
- portfolio/
  - portfolio_builder.py — 候補選定、等分/スコア重み
  - position_sizing.py — 発注株数決定・スケールダウン・単元丸め
  - risk_adjustment.py — セクターキャップ、レジーム乗数
- research/
  - factor_research.py — momentum/value/volatility の計算（DuckDB を使用）
  - feature_exploration.py — 将来リターン、IC、統計サマリー
- tools/
  - paper_verification_report.py — Paper Trading の検証レポート生成
- utils/
  - logging_setup.py — 統一的なログ設定（stdout + 日次ローテーション）
  - process_priority.py — プロセス優先度 / CPU affinity 設定
  - など

---

## 運用上の注意点

- 本番運用時は `KABUSYS_ENV=live` を使用してください。validate_config は本番時に注意喚起するチェックを行います。
- `KILL_FLAG_CLEAR_ON_START=1` は本番では危険です（自動で kill.flag を消してしまう）。
- Paper Trading は本番 DB と完全分離されるようになっています。`KABUSYS_ENV=paper_trading` を使って安全にテストしてください。
- OpenAI を使う機能は API キーが必要です。API 呼び出しはリトライ/フォールバックを備えていますが、費用とレイテンシには注意してください。
- ログディレクトリや DB パスの親ディレクトリが存在しない場合は警告が出ます。必要なら事前にディレクトリを作成してください。

---

## 参考コマンド一覧（まとめ）

- 環境作成・依存インストール
  - python -m venv .venv
  - source .venv/bin/activate
  - pip install duckdb psutil openai PyYAML

- .env 対話式作成
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 監視起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- 実行エンジン起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- Paper Trading レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

README はここまでです。運用に関する詳しい実装や追加の機能（monitoring/trade_monitor の詳細や ExecutionEngine の設定）は各モジュールの docstring を参照してください。必要であれば、systemd / supervisor 用のサービス定義例やデプロイ手順も作成できますので指示ください。