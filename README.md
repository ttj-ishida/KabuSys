# KabuSys

日本株向け自動売買システムのサンプル実装。シグナル生成・ポートフォリオ構築・発注エンジン・監視・各種レポート生成を含むツール群を提供します。

以下はリポジトリに含まれる主要な機能、セットアップ方法、使い方、ディレクトリ構成の説明です。

注意: 本 README はコードベース（src/kabusys/...）を元に手動で作成しています。実運用前に必ず設定検証とテストを行ってください。

## 概要
KabuSys は以下の要素を含む自動売買支援フレームワークです。

- Execution Engine（発注エンジン）: ブローカークライアント経由で発注を行う（本番 / ペーパートレード対応）。
- Monitoring（監視）: システム稼働状況を定期ポーリングして監視テーブルへ記録。
- レポート生成: Pre-Market / Night Batch / Execution Startup / Signal Queue / Position Reconciliation などのレポートを生成・保存。
- Portfolio コンポーネント: 候補選定、重み計算、リスク調整、ポジションサイズ決定の純粋関数群（DB を参照しない）。
- ユーティリティ: ログ設定、プロセス優先度設定、環境設定ウィザード、設定検証 CLI 等。

設計方針として、レポートやポートフォリオ計算などは可能な限り純粋関数に分離され、テストしやすい構成になっています。

## 主な機能一覧
- 起動スクリプト / CLI:
  - run_execution.py: ExecutionEngine 起動（KABUSYS_ENV により paper_trading モードで MockBroker を使用）
  - run_monitoring.py: SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で間隔変更可）
  - run_pre_market_report.py: Pre-Market レポート生成（--save / --json オプション）
  - run_signal_queue_report.py: Signal Queue 確認ビュー（--date / --save / --json）
  - run_position_reconciliation_report.py: ポジション照合ビュー（--watch / --interval オプション有）
  - validate_config.py: .env / config/*.yaml の設定検証 CLI（--strict 指定で警告も失敗扱い）
  - config_setup.py: 対話式 .env 作成ウィザード
  - tools/paper_verification_report.py: ペーパートレード検証レポート生成ツール

- レポートモジュール（pure functions + formatter + 保存機能）
  - operations/pre_market_report, night_batch_report, execution_startup_report, signal_queue_report, position_reconciliation_report

- Portfolio モジュール（純粋関数）
  - select_candidates, calc_equal_weights, calc_score_weights
  - apply_sector_cap, calc_regime_multiplier
  - calc_position_sizes

- ユーティリティ
  - utils/logging_setup.py: 日次ローテーション付きログ設定
  - utils/process_priority.py: Windows/Linux に対応したプロセス優先度設定
  - config.py: 環境変数読み込み・設定ラッパー（.env 自動読み込み機能含む）

## 必要条件
- Python 3.10 以上（モジュール内の型注釈や union 型表記から）
- 主要な Python パッケージ（例）:
  - duckdb
  - PyYAML
  - psutil
- これらは requirements.txt があればそれを用いてインストールしてください。なければ手動でインストールしてください:
  pip install duckdb pyyaml psutil

（実際の運用ではその他の依存があるかもしれないため、プロジェクトの requirements.txt を参照してください。）

## セットアップ手順（ローカル開発向け）
1. リポジトリをクローン
   git clone <repo-url>
   cd <repo>

2. Python 仮想環境を作成・有効化
   python -m venv .venv
   source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - もし requirements.txt があれば:
     pip install -r requirements.txt
   - なければ最低限:
     pip install duckdb pyyaml psutil

4. データ・ログ・artifacts ディレクトリを作成（必要に応じて）
   mkdir -p data logs artifacts

5. .env の作成
   - 対話式ウィザードを使う:
     python -m kabusys.config_setup
   - またはプロジェクトルートに .env を作成し、必要な環境変数を設定してください（下記「主な環境変数」参照）。

6. 設定検証（任意だが推奨）
   python -m kabusys.validate_config
   --strict を付けると警告もエラー扱いになります:
   python -m kabusys.validate_config --strict

## 主な環境変数（Settings に基づく）
（プロジェクトルートの .env に記載するか、OS 環境変数として設定）
- JQUANTS_REFRESH_TOKEN (必須)
- JQUANTS_BULK_API_KEY (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- KABU_TRADE_PASSWORD (任意)
- LINE_CHANNEL_ACCESS_TOKEN (任意)
- LINE_USER_ID (任意)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — デフォルト: INFO
- KILL_FLAG_CLEAR_ON_START (0|1) — デフォルト: 0
- PAPER_FILL_MODE (instant|partial|never|reject) — paper_trading 時の MockBroker 挙動（デフォルト: instant）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）

注意: config.py はプロジェクトルートにある .env と .env.local を自動で読み込みます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると無効化可能）。

## 使い方（主要なコマンド）
- 実行エンジンを起動（実行中に data/stop_requested.flag を作成すると停止）
  python -m kabusys.run_execution

  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、
    DB は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を使用して本番 DB と分離します。

- 監視ループを起動（ポーリング）
  python -m kabusys.run_monitoring
  - ポーリング間隔を変更するには環境変数:
    export MONITOR_POLL_INTERVAL=30  # 30秒

- Pre-Market レポート（CLI）
  python -m kabusys.run_pre_market_report
  オプション:
    --save   : artifacts/pre_market/{date}/ に保存
    --json   : JSON 出力

- Signal Queue Confirmation
  python -m kabusys.run_signal_queue_report
  オプション:
    --date YYYY-MM-DD
    --save
    --json

- Position Reconciliation（1回実行 または watch モード）
  python -m kabusys.run_position_reconciliation_report
  オプション:
    --date YYYY-MM-DD
    --save
    --json
    --watch    : 定期ポーリングモード
    --interval N  : watch 時の間隔（秒）

- 設定検証
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- 環境設定ウィザード（.env 生成）
  python -m kabusys.config_setup

- ペーパートレード検証レポート
  python -m kabusys.tools.paper_verification_report
  オプション:
    --from YYYY-MM-DD --to YYYY-MM-DD
    --db PATH  # PAPER_TRADING_SQLITE_PATH を上書き

- レポート生成モジュールは個別に import してユニットテスト・組合せで利用可能
  例: operations.pre_market_report.build_report(...) を呼び出して結果を取得

## ファイル / ディレクトリ構成（抜粋）
- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数ラッパー（Settings）
  - config_setup.py               — .env 対話式ウィザード
  - validate_config.py            — 設定検証 CLI
  - run_execution.py              — ExecutionEngine 起動スクリプト
  - run_monitoring.py             — SystemMonitor ポーリングスクリプト
  - run_pre_market_report.py      — Pre-Market レポート CLI
  - run_signal_queue_report.py    — Signal Queue レポート CLI
  - run_position_reconciliation_report.py — Position Reconciliation CLI
  - operations/                    — レポート生成やデータ収集モジュール群
    - pre_market_collector.py
    - pre_market_report.py
    - night_batch_report.py
    - execution_startup_report.py
    - signal_queue_report.py
    - position_reconciliation_report.py
  - portfolio/                     — ポートフォリオ構築ロジック（純粋関数）
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - execution/                     — 発注関連（Engine, OrderManager 等）※実装は別ファイルに存在
  - monitoring/                    — 監視関連（SystemMonitor、DB 初期化等）
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py
    - process_priority.py

- プロジェクトルート（README と同じ階層に）:
  - .env (推奨、Git 管理しない)
  - config/                         — YAML 設定ファイル群（system_config.yaml 等）
  - data/                           — デフォルト DB・フラグファイル等（data/monitoring.db、data/stop_requested.flag 等）
  - logs/                           — ログ（TimedRotatingFileHandler）
  - artifacts/                      — 各種レポート保存先（pre_market, signal_queue, execution_startup, ...）

## 動作の注意点・運用上のポイント
- 本番とペーパートレードの DB 分離
  - Settings により paper_trading モード時は paper_sqlite_path（デフォルト data/paper_trading.db）を使用します。ペーパートレードは本番 DB と完全分離する設計です。

- stop フラグ / kill フラグ
  - 実行中に自動停止したい場合はプロジェクトルートの data/stop_requested.flag を作成すると run_execution / run_monitoring が検知して終了します。
  - kill_flag_path（デフォルト data/kill.flag）や KILL_FLAG_CLEAR_ON_START の挙動も Settings で制御されています。特に本番（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START を 0 にしておくことを推奨します。

- ロギング
  - logging_setup.setup_logging() により stdout 出力と日次ローテーションファイル（logs/<app_name>.log）が設定されます。ログディレクトリ作成に失敗した場合は stdout のみで継続します。

- 実行優先度
  - 起動スクリプトは起動直後に set_process_priority("high") を呼び出してプロセス優先度を設定します。psutil が必要です。

- レポート生成は純粋関数を多用しており、ユニットテストや CI で容易に検証できます。フォーマッタは CLI 表示（format_cli_summary）、JSON（format_json）、Markdown（format_markdown）を提供します。

## よくあるトラブルシューティング
- .env が読み込まれない / 不足している
  - config_setup で生成するか、.env.example を参考に .env を作成してください。validate_config で主要な環境変数の有無を確認できます。

- DuckDB / SQLite ファイルパスが存在しない
  - validate_config は DUCKDB_PATH / SQLITE_PATH の親ディレクトリ存在を警告します。ディレクトリを手動で作成するか、起動時にコードが作成する場合があります。

- PyYAML がない
  - validate_config は PyYAML がない場合 YAML 内容検証をスキップします。config/*.yaml の検証をしたい場合は PyYAML をインストールしてください。

## 開発・拡張のヒント
- レポート生成モジュールは DB 参照部分と純粋関数部が分離されています。collect_* 関数で DB から生データを取得し、build_report 等で純粋関数的にレポートを生成する構造はテストしやすく保守性が高い設計です。
- portfolio の関数群は外部に依存しないため、異なる戦略やテストデータで簡単に検証できます。
- ExecutionEngine 周りはブローカーファクトリや OrderRepository を注入する設計になっており、MockBroker を使えば本番に影響を与えずにロジックを試せます。

---

この README はコード中の docstring / コメントを要約して作成しています。実際にシステムを運用する際は config/*.yaml や .env の内容、各モジュールの仕様を十分に確認し、ステージング環境での動作確認を行ってください。