KabuSys — 日本株自動売買システム
================================

このリポジトリは日本株向けの自動売買・検証・監視フレームワーク「KabuSys」のコア実装です。
README はコードベース（src/kabusys 以下）に含まれる主要モジュールの使い方・セットアップ手順・ディレクトリ構成をまとめたものです。

要点（サマリ）
- Python 3.10+ を想定（PEP 604 の union types 等を使用）
- 永続化: SQLite（監視/注文ログ等）と DuckDB（時系列 / 分析用）
- 実行モード: development / paper_trading / live（KABUSYS_ENV）
- Paper Trading: 実際のブローカー呼び出しは行わず専用 DB を使用して完全に分離
- OpenAI 連携（ニュース NLP / レジーム判定）には OPENAI_API_KEY が必要

主な機能
- ExecutionEngine 起動スクリプト（run_execution.py）
  - 実運用 / ペーパーそれぞれに対応
  - BrokerClientFactory 経由で本番ブローカー or Mock を切替
  - リスク管理・注文管理・リコンシリエーションを組み合わせてセッション実行
  - data/execution.pid（PID ファイル）および data/stop_requested.flag に対応

- Monitoring（run_monitoring.py / monitoring パッケージ）
  - SystemMonitor: CPU / メモリ / ディスク / データ鮮度 / Execution プロセス検出
  - TradeMonitor: 発注ログの監視（滞留注文・異常約定など）
  - RiskMonitor: ドローダウン監視、ポジション上限監視
  - KillSwitch: 条件に基づいて data/kill.flag を書き込み ExecutionEngine を停止させる
  - MonitoringEngine: 各 Monitor を定期実行しアラートを通知（AlertManager 経由）

- ポートフォリオ構築（portfolio パッケージ）
  - 候補選定、等配分 / スコア加重、ポジションサイズ計算、セクターキャップ、レジーム乗数など
  - すべて純粋関数（DB 参照なし）でユニットテストしやすい設計

- リサーチ / ファクター計算（research パッケージ）
  - モメンタム・ボラティリティ・バリュー等のファクターを DuckDB 上の prices_daily/raw_financials から算出
  - 将来リターン計算、IC（Spearman）や統計サマリーツール

- AI（ai パッケージ）
  - news_nlp.score_news: OpenAI を使ってニュースを銘柄ごとにスコアリングし ai_scores に書込
  - regime_detector.score_regime: ETF の MA やマクロニュースの LLM 評価を合成して市場レジーム判定
  - OpenAI の API エラーに対するリトライや JSON バリデーションなど堅牢化済み

- ユーティリティ
  - config_setup.py: 対話式 .env 作成ウィザード
  - validate_config.py: 起動前チェック（.env・config/*.yaml 等）
  - tools/paper_verification_report.py: ペーパートレードの検証レポート生成
  - utils/logging_setup.py: 一貫したログ設定（コンソール + 日次ローテート）
  - utils/process_priority.py: クロスプラットフォームでプロセス優先度設定

セットアップ手順（開発環境向け）
1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo-root>

2. Python 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール（最低限）
   - pip install duckdb psutil openai
   - （開発用）PyYAML があれば validate_config の YAML 検証が有効になります: pip install pyyaml

   補足: requirements.txt がある場合は pip install -r requirements.txt を使用してください。

4. パッケージ参照方法
   - 開発時はプロジェクトルートに移動し、python -m でモジュールを実行するか、pip install -e .（setup がある場合）を検討してください。
   - もしくは PYTHONPATH=src を設定して実行できます。

環境変数（主要）
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 実行環境:
  - KABUSYS_ENV: development | paper_trading | live
- DB / ログ:
  - DUCKDB_PATH (default: data/kabusys.duckdb)
  - SQLITE_PATH (default: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)
  - LOG_LEVEL (default: INFO)
  - LOG_DIR (default: logs/)
- Paper Trading:
  - PAPER_FILL_MODE: instant | partial | never | reject (default: instant)
- モニタリング:
  - MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、run_monitoring で使用。デフォルト 60）
  - KILL_FLAG_PATH (Settings.kill_flag_path)
  - KILL_FLAG_CLEAR_ON_START: 1 にすると起動時に kill.flag を自動クリア（本番では 0 推奨）
- OpenAI:
  - OPENAI_API_KEY（ai.* を使う場合必須）

.env の作成・検証
- 対話式ウィザード:
  - python -m kabusys.config_setup
  - これによりプロンプト形式で .env を作成・更新できます。
- 検証:
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗（exit code 1）扱いになります。

実行方法（主要スクリプト）
- 監視ループ（Monitoring）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL で秒間隔を変更可能（デフォルト 60）
  - 監視は本番 sqlite_path を用いる（KABUSYS_ENV に関係なく）

- 実行エンジン（ExecutionEngine）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH に書き込みます（本番 DB と分離）
  - 起動時に data/stop_requested.flag が存在する場合は起動しません
  - 停止信号は data/stop_requested.flag または data/kill.flag の書込みで通知可能（Monitoring の KillSwitch が生成）

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション: --from YYYY-MM-DD --to YYYY-MM-DD --db PATH

- AI / リサーチ関数（プログラム的に使用）
  - from kabusys.ai import score_news
    - score_news(conn, target_date, api_key=None) など
  - from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary

ログ / PID / フラグファイル
- ログ:
  - デフォルトは logs/<app_name>.log（TimedRotatingFileHandler で日次ローテート、30日保持）
  - ログ設定は kabusys.utils.logging_setup.setup_logging を各起動スクリプトが呼び出します
- PID / フラグ:
  - data/execution.pid: ExecutionEngine が書き込む PID（Settings.pid_file_path）
  - data/stop_requested.flag: 起動/監視ループを外部から停止するためのフラグ（run_* が監視）
  - data/kill.flag: KillSwitch が書き込む停止フラグ（ExecutionEngine に停止を促す）

注意点 / 運用上のヒント
- 本番（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START を 0 にしておくことを推奨します（間違って Kill Switch を消してしまうのを防ぐため）。
- OpenAI キーは環境変数に設定し、API 呼び出しにはレートリミット・再試行が組み込まれていますが、コストとレイテンシに注意してください。
- DuckDB / SQLite ファイルは適切なバックアップやボリューム管理を行ってください（特に本番での破損対策）。
- process_priority モジュールで起動直後に優先度を high に設定しますが、権限不足等で設定できない場合は警告でスキップされます。

ディレクトリ構成（主なファイル）
- src/kabusys/
  - __init__.py
  - __version__ = "0.1.0"
  - config.py                     — 環境変数・設定管理（自動 .env 読込含む）
  - config_setup.py               — .env 対話式ウィザード
  - validate_config.py            — 設定検証 CLI
  - run_monitoring.py             — Monitoring 起動スクリプト
  - run_execution.py              — ExecutionEngine 起動スクリプト

  - utils/
    - __init__.py
    - logging_setup.py            — ルートロガー設定（console + file）
    - process_priority.py         — プロセス優先度 / CPU affinity

  - monitoring/
    - monitoring_db.py            — SQLite 用永続化層（テーブル初期化 + MonitoringDB クラス）
    - system_monitor.py           — SystemMonitor（リソース・データ鮮度監視）
    - trade_monitor.py            — TradeMonitor（発注ログ監視）※（実装ファイルはここにある想定）
    - risk_monitor.py             — RiskMonitor（ドローダウン・ポジション上限）
    - kill_switch.py              — KillSwitch（kill.flag 制御）
    - alert_manager.py            — Alert 発行（LINE 等）※（実装ファイルはここにある想定）
    - monitoring_engine.py        — MonitoringEngine（各 Monitor を束ねる）

  - execution/
    - execution_engine.py         — ExecutionEngine（セッション実行ロジック）
    - broker_factory.py           — BrokerClientFactory（本番 / mock 切替）
    - order_manager.py            — Order 管理
    - order_repository.py         — DB 操作
    - reconciler.py               — 発注リコンシリエーション
    - risk_manager.py             — RiskManager（発注前チェック）

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
    - news_nlp.py                 — ニュース NLP スコアリング（OpenAI 連携）
    - regime_detector.py          — 市場レジーム判定（OpenAI 連携）
    - __init__.py

  - monitoring/ (先述)
  - monitoring_db.py (先述)
  - tools/
    - __init__.py
    - paper_verification_report.py

主要な SQL / DB 初期化
- monitoring_db.init_monitoring_db(conn)
  - system_status, trade_logs, positions, risk_logs, dashboard テーブルを作成
  - 既存 DB に対する簡易マイグレーション（列追加）も含む

開発者向けヒント
- モジュール単位でテスト可能な純粋関数が多く含まれている（portfolio, research 等）。ユニットテストを書きやすい設計。
- DuckDB 接続を引数で受け取る関数群 (research, ai) はローカル分析やバッチ処理に便利。
- AI 部分は外部 API 呼び出し箇所をラップした関数にまとめてあり、テスト時はそれらをモックする設計になっています（例: _call_openai_api の差し替え）。

よくある操作例
- .env を作って内容確認:
  - python -m kabusys.config_setup
  - python -m kabusys.validate_config
- 監視をデバッグで1回だけ実行:
  - Python REPL から MonitoringEngine をインスタンス化して run_once() を呼ぶ、もしくは unit-test 用に各 Monitor の check_once() を直接呼ぶ
- ペーパートレード検証レポート出力:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11 --db data/paper_trading.db

最後に
- 本 README はリポジトリ内の主要スクリプト／モジュール構成に基づく概要です。具体的な運用やデプロイ方法（systemd / Docker / Kubernetes 等）は環境に合わせて追加してください。
- 実稼働前に必ず python -m kabusys.validate_config で設定を確認し、監視・Kill Switch の動作を理解したうえで運用してください。

必要なら、実行例（systemd ユニット、Dockerfile、より詳細な env.example、運用チェックリスト）を追記した README の拡張版を作成します。どの内容を優先して追加しますか？