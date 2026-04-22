# KabuSys

日本株向けの自動売買システム（ライブラリ／実行スクリプト群）。

このリポジトリは、戦略の研究・ファクター計算・ポートフォリオ構築・発注エンジン（ExecutionEngine）・監視（Monitoring）・AI（ニュースセンチメント・レジーム判定）などを含むモジュール群で構成されています。設計方針として「本番向けに安全なフェイルセーフ」「ルックアヘッドバイアスの排除」「環境ごとの DB 分離（paper_trading vs live）」を重視しています。

---

目次
- プロジェクト概要
- 主な機能
- セットアップ手順
- 使い方
  - 環境設定ウィザード（.env）
  - 設定検証
  - 実行エンジン起動（Execution）
  - 監視プロセス起動（Monitoring）
  - ペーパートレード検証レポート
  - AI（ニューススコア・レジーム判定）
- 重要な環境変数
- ファイル・ディレクトリ構成（主要なファイルの説明）
- 監視 / 停止フラグの仕組み
- DB／ログの位置
- 参考（依存パッケージなど）

---

プロジェクト概要
- KabuSys は日本株自動売買に必要なコンポーネント群を提供します。
  - データリサーチ（DuckDB 上のファクター計算）
  - ポートフォリオ構築（候補選定・重み算出・ポジションサイズ計算）
  - ExecutionEngine（ブローカークライアント経由で発注・注文管理・リスク管理）
  - Monitoring（プロセス／データ鮮度／注文異常／リスク監視）
  - AI モジュール（ニュースの NLP スコアリング、レジーム判定）
  - ユーティリティ（.env ウィザード、設定検証、ログ設定等）

主な機能
- 設定ウィザード（config_setup）で .env を対話的に作成
- validate_config による起動前チェック（必須環境変数や config/*.yaml の存在チェック）
- ExecutionEngine（run_execution）：
  - KABUSYS_ENV により paper_trading と本番を分離
  - paper_trading 時は MockBroker を使用して data/paper_trading.db に記録
  - 起動時にプロセス優先度を High に設定するユーティリティを使用
- Monitoring（run_monitoring）：
  - SystemMonitor / TradeMonitor / RiskMonitor を組み合わせたポーリング監視
  - MONITOR_POLL_INTERVAL でポーリング間隔を変更可能（デフォルト 60 秒）
  - 独自の SQLite monitoring DB（system_status, trade_logs, positions, risk_logs, dashboard）
- AI モジュール：
  - news_nlp.score_news: raw_news -> OpenAI で銘柄ごとのセンチメント（ai_scores）を書き込み
  - regime_detector.score_regime: ETF（1321）の MA とマクロニュースを合わせて市場レジーム判定
  - OpenAI 呼び出しはリトライ/バックオフ・レスポンス検証・クリッピング等、安全策あり
- 研究用モジュール（research）：
  - ファクター計算（momentum, volatility, value）・特徴量解析（IC 等）
- ポートフォリオ（portfolio）：
  - 候補選定、等重／スコア重み、リスク調整（セクターキャップ、レジーム乗数）、ポジションサイズ計算

セットアップ手順（ローカル開発向け）
1. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate（Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール
   - 主要依存（例）:
     - duckdb
     - psutil
     - openai
     - PyYAML（設定検証で optional）
   - 例:
     - pip install duckdb psutil openai PyYAML

   （実際の requirements.txt がある場合はそれを使用してください）

3. プロジェクトルートの data, logs など必要ディレクトリを作成（自動作成もされますが手動で行うと安心）
   - mkdir -p data logs

4. .env の準備
   - python -m kabusys.config_setup を実行して対話的に作成するか、
   - ルートに .env を配置（.env.example を参考に）

使い方（主要ワークフロー）

- 環境設定ウィザード（.env）
  - 実行:
    - python -m kabusys.config_setup
  - 対話形式で J-Quants トークン、kabu API パスワード、DB パス、KABUSYS_ENV 等を設定します。
  - .env は Git にコミットしないでください（機密情報を含みます）。

- 設定検証
  - 実行:
    - python -m kabusys.validate_config
    - --strict を付けると警告も失敗扱い（exit 1）
  - 必須環境変数（例）:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
  - PyYAML が無いと config/*.yaml の検証はスキップされます（警告）。

- 実行エンジン起動（Execution）
  - 実行:
    - python -m kabusys.run_execution
  - 挙動:
    - 起動時にプロセス優先度を high に設定
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（既定 data/paper_trading.db）に記録
    - pid ファイル: data/execution.pid（Settings.pid_file_path により変更可）
    - 停止フラグ（data/stop_requested.flag）を検知すると安全停止（フラグ存在時は起動しない・起動中は停止する）

- 監視プロセス起動（Monitoring）
  - 実行:
    - python -m kabusys.run_monitoring
  - 挙動:
    - MONITOR_POLL_INTERVAL 環境変数（秒）でポーリング間隔を変更可能（デフォルト 60）
    - Monitoring は常に本番向け sqlite_path（Settings.sqlite_path）を使用して monitoring DB を初期化/書き込み
    - 日次ログや通知（AlertManager を有効化している場合）に基づくアラート発行が行われます

- ペーパートレード検証レポート
  - 実行:
    - python -m kabusys.tools.paper_verification_report
    - 期間指定例:
      - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    - DB を指定する場合:
      - --db PATH または 環境変数 PAPER_TRADING_SQLITE_PATH
  - 出力:
    - 稼働率、注文成功率（fill rate）、送信率、レイテンシ（P95 など）に基づく PASS/FAIL 判定

- AI 機能（ニュース NLP / レジーム判定）
  - news scoring:
    - 使用 API: kabusys.ai.score_news（モジュール関数）
    - コマンドラインの直接エントリポイントは無いが、score_news(conn, target_date, api_key) を呼んで使用
    - OPENAI_API_KEY または api_key 引数でキーを指定
  - regime detector:
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key)

重要な環境変数（抜粋）
- 必須（起動前に設定が必要）
  - JQUANTS_REFRESH_TOKEN: J-Quants API のリフレッシュトークン（必須）
  - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- 実行環境
  - KABUSYS_ENV: development | paper_trading | live（デフォルト development）
- DB 関連
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH: 監視 DB（monitoring.db）（デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト data/paper_trading.db）
- ロギング
  - LOG_LEVEL: デフォルト INFO
  - LOG_DIR: ログディレクトリ（デフォルト logs/）
- その他
  - OPENAI_API_KEY: OpenAI API キー（AI 機能を使用する場合）
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
  - PAPER_FILL_MODE: paper_trading 時の約定モデル（instant | partial | never | reject、デフォルト instant）
  - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD: =1 にすると .env の自動読み込みを無効化（テスト用）

.env の自動ロード挙動
- デフォルトでプロジェクトルート（.git または pyproject.toml を基準）にある .env と .env.local を自動で読み込みます。
- 既存の OS 環境変数は上書きされません（.env.local は override=True ですが、既存 OS 環境変数は保護）。
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効にできます（テスト時など）。

監視 / 停止フラグの仕組み
- data/stop_requested.flag:
  - run_monitoring と run_execution はこのファイルの存在をポーリングして検知すると安全に停止します（run_execution は起動前にすでにあれば起動せず終了する）。
- data/kill.flag（KillSwitch によるフラグ）:
  - Monitoring の KillSwitch がリスク条件（例: ドローダウン閾値超過やポジション上限超過）を満たすと kill.flag を書き込み、ExecutionEngine に停止シグナルを与えます。
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に自動的にクリアする挙動になります（本番では 0 推奨）。

DB/ログの位置（既定）
- DuckDB: data/kabusys.duckdb
- Monitoring SQLite: data/monitoring.db
- Paper trading SQLite: data/paper_trading.db
- ログ: logs/<app_name>.log（日次ローテーション、30 日分保持）

主要テーブル（monitoring DB）
- system_status: CPU/メモリ/ディスク/プロセス状態のログ
- trade_logs: 発注イベントログ（event_type: Created/Sent/Filled など）
- positions: 現在のポジション
- risk_logs: リスク関連のイベントログ
- dashboard: ダッシュボード集計（portfolio_value, cash, drawdown_pct 等）

ディレクトリ構成（主要ファイル・説明）
- src/kabusys/
  - __init__.py — パッケージ定義（__version__ 等）
  - config.py — 環境変数 / 設定読み込みユーティリティ（.env 自動ロード・Settings クラス）
  - config_setup.py — .env 対話ウィザード（python -m kabusys.config_setup）
  - validate_config.py — 起動前の設定検証 CLI（python -m kabusys.validate_config）
  - run_execution.py — ExecutionEngine 起動スクリプト（python -m kabusys.run_execution）
  - run_monitoring.py — Monitoring ポーリングループ起動スクリプト（python -m kabusys.run_monitoring）
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成（python -m kabusys.tools.paper_verification_report）
  - utils/
    - logging_setup.py — 共通ログ設定（setup_logging）
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ
  - monitoring/
    - monitoring_db.py — monitoring 用 SQLite 操作（初期化・CRUD）
    - system_monitor.py, trade_monitor.py, risk_monitor.py, kill_switch.py, monitoring_engine.py など — 監視コンポーネント
  - execution/ (発注関連モジュール)
    - execution_engine.py, order_manager.py, order_repository.py, broker_factory.py, reconciler.py, risk_manager.py など
  - portfolio/
    - portfolio_builder.py, position_sizing.py, risk_adjustment.py — ポートフォリオ構築ロジック
  - research/
    - factor_research.py, feature_exploration.py — ファクター計算・解析
  - ai/
    - news_nlp.py — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py — 市場レジーム判定（OpenAI + MA）
  - data/（実行時に使われるファイル）
    - stop_requested.flag, kill.flag, *.db, pid ファイルなど（実行環境で生成）

簡単なコマンド例
- .env を作る:
  - python -m kabusys.config_setup
- 設定を検証:
  - python -m kabusys.validate_config
- 実行エンジン起動:
  - python -m kabusys.run_execution
- 監視プロセス起動:
  - python -m kabusys.run_monitoring
- ペーパートレード検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

注意事項 / 運用上のポイント
- .env は機密情報を含むため Git にコミットしないでください。
- 本番（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START を 0 にしておくことを推奨します。
- Monitoring は本番の monitoring DB（Settings.sqlite_path）を使用します。paper_trading でも監視ログは production DB を参照する仕様になっている点に注意してください（Execution は paper_trading 時に専用 DB を使用して分離）。
- OpenAI API を利用する機能は API キー（OPENAI_API_KEY）が必要です。API 呼び出しはリトライやパースチェックで安全策が取られていますが、コスト管理やレートリミットに注意してください。
- DuckDB の SQL は日次バッチ的な集計処理を想定しています。大規模データを扱う場合はストレージやクエリ性能に注意してください。

依存ライブラリ（主なもの）
- Python 標準ライブラリ: sqlite3, logging, threading, argparse, datetime 等
- 外部ライブラリ（少なくとも以下をインストール推奨）:
  - duckdb
  - psutil
  - openai
  - PyYAML（validate_config で YAML 検査を行う場合）
  - その他、実行環境に応じたブローカー API クライアント等

---

以上がこのコードベースの概要と利用方法のまとめです。README に追加したい操作手順（systemd/cron に載せる方法、Docker 化手順、CI での検証など）があれば、その要件に合わせたサンプルやユニットファイルの雛形も作成します。必要であれば教えてください。