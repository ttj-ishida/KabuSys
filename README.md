KabuSys — 日本株自動売買システム（README）
======================================

概要
----
KabuSys は日本株の自動売買／リサーチ／モニタリングを支援する Python パッケージです。
このリポジトリは以下の主要機能を持ち、実運用（live）・ペーパートレード（paper_trading）
・開発（development）に対応する構成になっています。

主な設計方針：
- DuckDB / SQLite を使ったデータ処理・永続化
- OpenAI（gpt-4o-mini 等）を用いたニュース NLP / レジーム判定（任意）
- モジュール分離（monitoring, execution, research, portfolio, ai, utils 等）
- .env による設定管理と対話式ウィザード / 検証ツールの提供

機能一覧
--------
- 実行エンジン起動スクリプト
  - run_execution.py: ExecutionEngine を起動。KABUSYS_ENV=paper_trading の場合は MockBroker 使用・専用 DB に記録
- 監視エンジン起動スクリプト
  - run_monitoring.py: SystemMonitor をポーリングして監視ログを記録。MONITOR_POLL_INTERVAL で間隔変更可
- 設定関連ツール
  - config_setup.py: 対話式 .env 作成ウィザード
  - validate_config.py: .env と config/*.yaml の検証 CLI（--strict オプションあり）
- Paper Trading レポート
  - tools/paper_verification_report.py: ペーパートレード履歴の検証レポート生成
- ポートフォリオ構築ロジック（純粋関数群）
  - portfolio/*: 候補選定、重み計算、リスク調整、ポジションサイズ計算
- リサーチ / ファクター計算
  - research/*: Momentum, Volatility, Value 等のファクター計算、IC / フォワードリターン等
- AI（ニュース NLP / レジーム判定）
  - ai/news_nlp.py: ニュースを集約して LLM でセンチメントスコアを算出し DB に保存
  - ai/regime_detector.py: ETF MA とマクロセンチメントを合成して市場レジーム判定
- 監視サブシステム
  - monitoring/*: MonitoringDB（SQLite）、SystemMonitor、TradeMonitor、RiskMonitor、KillSwitch、Alert 管理
- ユーティリティ
  - utils/logging_setup.py: 統一的なログ設定（stdout + 日次ローテーション）
  - utils/process_priority.py: プロセス優先度 / CPU affinity 設定

セットアップ手順
----------------
※ 実行には Python 3.10 以上を推奨します（typing 機構に依存）。

1. リポジトリをチェックアウト
   git clone <repo>
   cd <repo>

2. 仮想環境作成・有効化（任意）
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows (PowerShell)

3. 必要パッケージをインストール
   本リポジトリに requirements.txt がない場合は概ね下記パッケージを用意してください。
   pip install duckdb psutil openai

   追加（YAML 検証を使う場合）:
   pip install PyYAML

4. 環境変数（.env）の作成
   推奨: 対話式ウィザードを使用
   python -m kabusys.config_setup

   主要な必須環境変数:
   - JQUANTS_REFRESH_TOKEN （必須）
   - KABU_API_PASSWORD     （必須）

   任意 / 既定値:
   - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
   - DUCKDB_PATH: data/kabusys.duckdb
   - SQLITE_PATH: data/monitoring.db
   - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用 DB）
   - LOG_LEVEL: INFO（DEBUG 等も可）
   - OPENAI_API_KEY: OpenAI を用いる場合に必要

   自動読み込み:
   - プロジェクトルートに .env(.local) があれば、OS 環境変数より低い優先度で自動ロードされます。
   - 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。

5. 設定検証（起動前推奨）
   python -m kabusys.validate_config
   警告も失敗扱いにするには --strict を付ける

使い方
------
起動スクリプト例（パッケージをモジュールとして実行）:

- ExecutionEngine（注文実行）
  python -m kabusys.run_execution

  挙動:
  - KABUSYS_ENV=paper_trading の場合、MockBroker を使い data/paper_trading.db にログを残します（本番 DB と分離）。
  - 起動時に data/stop_requested.flag が存在すると起動を中止します。
  - 実行中は data/execution.pid に PID を書き込みます。停止すると削除されます。

- Monitoring（監視）
  python -m kabusys.run_monitoring

  挙動:
  - システム指標（CPU/MEM/DISK）、プロセス稼働、データ鮮度等をチェックして monitoring DB（default: data/monitoring.db）に記録します。
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（秒、デフォルト 60）。
  - 停止は data/stop_requested.flag を作成することで行えます。

- 設定ウィザード（.env 作成）
  python -m kabusys.config_setup

- 設定検証
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- Paper Trading 検証レポート出力
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  オプション --db で SQLite ファイルを明示的に指定可能（環境変数 PAPER_TRADING_SQLITE_PATH の優先度より高い）。

停止・ Kill Switch
- ExecutionEngine の停止には data/stop_requested.flag を作成するか、KillSwitch によって data/kill.flag が書き込まれることでトリガできます。
- KillSwitch の条件（例: ドローダウン超過、ポジション上限超過）は monitoring サブシステムで評価されます。
- KillSwitch は冪等で、既に kill.flag が存在する場合は再書き込みしません。Settings.kill_flag_clear_on_start=1 を設定すると起動時に自動でクリアする挙動になります（本番では 0 を推奨）。

ログ
----
- ログは kabusys.utils.logging_setup.setup_logging を通じて統一的に設定されます。
- デフォルトでは stdout（コンソール）と logs/<app_name>.log（日次ローテーション、30日保持）に出力します。
- LOG_DIR 環境変数や setup_logging の引数でログ出力先を変更できます。

主要な環境変数（抜粋）
--------------------
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD     (必須)
- KABUSYS_ENV           (development | paper_trading | live) — デフォルト: development
- DUCKDB_PATH           (例: data/kabusys.duckdb)
- SQLITE_PATH           (例: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB、例: data/paper_trading.db)
- LOG_LEVEL             (DEBUG/INFO/WARNING/ERROR/CRITICAL)
- OPENAI_API_KEY        (AI 機能を使う場合に必要)
- MONITOR_POLL_INTERVAL (監視ループの間隔（秒）、デフォルト 60)
- PAPER_FILL_MODE       (paper_trading の MockBroker 挙動: instant|partial|never|reject)

ディレクトリ構成（抜粋）
---------------------
src/kabusys/
- __init__.py
- config.py               : .env 自動読み込み / Settings 抽象化
- config_setup.py         : .env 対話式ウィザード
- validate_config.py      : 起動前チェック CLI
- run_execution.py        : ExecutionEngine 起動スクリプト
- run_monitoring.py       : SystemMonitor ポーリング起動スクリプト

サブパッケージ / 主要ファイル
- ai/
  - news_nlp.py           : ニュース NLP スコアリング（OpenAI 経由）
  - regime_detector.py    : 市場レジーム判定（MA + マクロセンチメント合成）
- monitoring/
  - monitoring_db.py      : SQLite テーブル作成・CRUD ラッパー
  - system_monitor.py     : システム状態・データ鮮度監視
  - risk_monitor.py       : ドローダウン・ポジション上限監視
  - kill_switch.py        : kill.flag 管理
  - monitoring_engine.py  : 各 Monitor を束ねるエンジン
  - (その他: trade_monitor, alert_manager 等)
- portfolio/
  - portfolio_builder.py   : 候補選定・重み計算
  - position_sizing.py     : 発注株数計算
  - risk_adjustment.py     : セクター上限・レジーム乗数
- research/
  - factor_research.py     : ファクター計算（momentum, volatility, value）
  - feature_exploration.py : 将来リターン / IC / 統計サマリ
- tools/
  - paper_verification_report.py : Paper Trading 検証レポート
- utils/
  - logging_setup.py      : ログ設定
  - process_priority.py   : プロセス優先度 / affinity 設定

データ / 実行フラグ
- data/
  - monitoring.db (default: SQLITE_PATH)
  - kabusys.duckdb (default: DUCKDB_PATH)
  - paper_trading.db (PAPER_TRADING_SQLITE_PATH)
  - stop_requested.flag  : 管理用フラグ（起動スクリプトが監視）
  - kill.flag            : Kill Switch による停止フラグ
  - execution.pid        : 実行エンジンの PID（run_execution が作成）

開発・テストのヒント
-------------------
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml がある場所）を基準に行われます。パッケージ配布後などで自動検出できない場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを無効化してください。
- AI 機能（news_nlp / regime_detector）をテストする際は OPENAI_API_KEY を用意するか、該当モジュールの API 呼び出し部分をモックしてください（コード内で _call_openai_api を patch 可能）。
- validate_config.py は起動前に設定漏れやパス問題、YAML 構文エラー等を検出するため便利です。--strict モードで警告も失敗扱いにできます。

ライセンス・貢献
----------------
（この README では省略しています。必要に応じて LICENSE ファイルを追加してください。）

以上。必要があれば、README にサンプル .env のテンプレート、systemd / supervisor 用の起動スクリプト例、運用手順（バックアップ・監視・復旧手順）なども追記します。どの情報を追加したいか教えてください。