KabuSys — 日本株自動売買システム
=================================

概要
----
KabuSys は日本株向けの自動売買／リサーチ基盤です。銘柄選定・ポジションサイズ算出・発注管理・監視・ペーパートレード検証・AI を使ったニュースセンチメント評価など、取引戦略運用に必要なコンポーネント群を含みます。

主な設計方針
- 本番 DB（monitoring.db）とペーパートレード DB（paper_trading.db）を分離
- DuckDB を分析用に使用、SQLite を稼働ログ・発注ログ用に使用
- OpenAI（GPT）を用いたニュース NLP / レジーム判定はオプション（API キー必須）
- .env を利用した環境変数管理、対話式ウィザードと検証ツールあり

機能一覧
---------
- 実行エンジン起動: run_execution.py
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、data/paper_trading.db を使用して本番 DB と分離
  - プロセス優先度設定・PID 管理・停止フラグ監視
- 監視ループ起動: run_monitoring.py
  - システム状況（CPU/メモリ/ディスク）、データ鮮度、発注ログなどのポーリングと永続化
  - MONITOR_POLL_INTERVAL によるポーリング間隔上書き
- 設定関連
  - 対話式 .env ウィザード: kabusys.config_setup
  - 設定検証 CLI: kabusys.validate_config
- ポートフォリオ構成
  - 候補選定 / 重み計算 / セクター上限 / レジーム乗数 / ポジションサイズ算出
- 監視
  - MonitoringDB（SQLite）による永続化、RiskMonitor、TradeMonitor、KillSwitch、AlertManager（通知周り）
- AI 関連
  - ニュース NLP（raw_news → ai_scores）: kabusys.ai.news_nlp
  - 市場レジーム判定（ma200 + macro sentiment）: kabusys.ai.regime_detector
- ツール
  - ペーパートレード検証レポート生成: kabusys.tools.paper_verification_report

セットアップ手順
-----------------
前提
- Python 3.10 以上
- SQLite（標準ライブラリ）とファイルシステム権限
- 必要パッケージ（例）:
  - duckdb, psutil, openai, PyYAML（validate_config で YAML 検証する場合）
  - 例: pip install duckdb psutil openai PyYAML

1. リポジトリをチェックアウトして Python 仮想環境を作成
   - python -m venv .venv
   - source .venv/bin/activate もしくは .venv\Scripts\activate

2. 必要パッケージをインストール
   - pip install duckdb psutil openai PyYAML
   - （プロジェクトに requirements.txt がある場合は pip install -r requirements.txt）

3. .env の作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
   - ウィザードは J-Quants トークンや kabu API パスワード等の必須項目を案内します
   - 生成後、python -m kabusys.validate_config で検証してください

4. データディレクトリ等の作成（通常は自動作成されますが確認）
   - data/（デフォルトの SQLite/DuckDB 保存先）
   - logs/（ログ出力先。LOG_DIR で変更可）

主な環境変数（抜粋）
- 必須
  - JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン
  - KABU_API_PASSWORD: kabuステーション API パスワード
- 主要設定
  - KABUSYS_ENV: execution モード（development / paper_trading / live）。デフォルト: development
  - DUCKDB_PATH: デフォルト data/kabusys.duckdb
  - SQLITE_PATH: 監視 DB（monitoring.db）デフォルト data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード DB（data/paper_trading.db）上書き可
  - PAPER_FILL_MODE: paper_trading の約定モード（instant|partial|never|reject）。デフォルト instant
  - LOG_LEVEL: ログレベル（DEBUG|INFO|...）。デフォルト INFO
  - LOG_DIR: ログ出力先（デフォルト logs/）
  - OPENAI_API_KEY: OpenAI を使う場合に必要
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒。デフォルト 60）
  - KILL_FLAG_CLEAR_ON_START: ExecutionEngine 起動時に kill.flag を自動クリアするか（0/1。デフォルト 0）
  - PID_FILE_PATH / KILL_FLAG_PATH: PID・kill flag のパス（デフォルト data/）

使い方（コマンド例）
-------------------
1. 環境変数の準備
   - python -m kabusys.config_setup で .env を用意
   - .env を編集したら: python -m kabusys.validate_config

2. 監視プロセスの起動
   - デフォルトのポーリング（60秒）で起動:
     - python -m kabusys.run_monitoring
   - ポーリング間隔を環境変数で変更:
     - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
   - 停止:
     - data/stop_requested.flag を作成するとループが検出して終了します

3. 実行（ExecutionEngine）起動
   - python -m kabusys.run_execution
   - KABUSYS_ENV=paper_trading の場合、MockBroker を使い data/paper_trading.db に記録されます
   - 起動時に data/stop_requested.flag が既に存在すると起動を行わず終了します
   - 実行中に停止させるには data/stop_requested.flag を作るか KillSwitch（kill.flag）を利用

4. ペーパートレード検証レポート
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - 環境変数 PAPER_TRADING_SQLITE_PATH で DB パスを指定可能（--db オプションもあり）

5. AI 関連（プログラム内呼び出し）
   - ニューススコアリング:
     - from kabusys.ai.news_nlp import score_news
     - score_news(duckdb_conn, target_date, api_key="...")
   - レジーム判定:
     - from kabusys.ai.regime_detector import score_regime
     - score_regime(duckdb_conn, target_date, api_key="...")

停止フラグ / Kill Switch
-----------------------
- data/stop_requested.flag:
  - run_execution / run_monitoring のループを終了させるための外部停止フラグ（存在を監視）
- data/kill.flag:
  - KillSwitch により作成され、ExecutionEngine に「注文停止（Kill）」を指示する目的で使用
  - Settings.kill_flag_clear_on_start が 1 の場合は起動時に自動クリアされます（本番では 0 推奨）
- PID ファイル:
  - 実行中のプロセス情報は data/execution.pid 等に記録される（設定可能）

ログ
---
- ロギングは kabusys.utils.logging_setup.setup_logging を通して初期化されています
- デフォルトは stdout と logs/<app_name>.log（日次ローテート、30日保持）
- LOG_DIR 環境変数でログ保存先を変更可能

ディレクトリ構成（主要ファイル）
--------------------------------
（src/kabusys 以下を想定）

- run_monitoring.py
  - SystemMonitor を初期化してポーリングループを回す起動スクリプト
- run_execution.py
  - ExecutionEngine を組み立てて実行する起動スクリプト
- config.py
  - Settings クラス: 環境変数の解決・妥当性チェック、デフォルト値
- config_setup.py
  - .env を対話式で生成/更新するウィザード
- validate_config.py
  - 起動前チェック用 CLI（必須環境変数や config/*.yaml の存在などを検証）
- __init__.py
  - パッケージ定義（__version__ 等）
- tools/
  - paper_verification_report.py: ペーパートレード検証レポート生成 CLI
- ai/
  - news_nlp.py: ニュースを LLM に投げて銘柄別スコアを生成して ai_scores に書き込む
  - regime_detector.py: 市場レジーム判定（ma200 + マクロセンチメント）
- monitoring/
  - monitoring_db.py: SQLite スキーマ初期化・永続化ユーティリティ
  - system_monitor.py: システム・データ鮮度監視
  - risk_monitor.py: ドローダウン・ポジション数監視
  - kill_switch.py: kill.flag 制御
  - monitoring_engine.py: 複数 Monitor の起動ループ管理
- portfolio/
  - portfolio_builder.py: 候補選定、重み計算
  - position_sizing.py: 株数決定・スケーリング
  - risk_adjustment.py: セクターキャップ・レジーム乗数
- research/
  - factor_research.py: モメンタム/ボラ/バリュー等の計算（DuckDB）
  - feature_exploration.py: 将来リターン計算、IC 計算、統計サマリ
- utils/
  - logging_setup.py: ログ初期化ユーティリティ
  - process_priority.py: プロセス優先度・CPU affinity 設定ユーティリティ
- monitoring/（DB スキーマ・監視ロジックなど）
  - monitoring_db.py, risk_monitor.py, trade_monitor.py, ...

注意点 / 運用上のヒント
-----------------------
- 本番（KABUSYS_ENV=live）では kill.flag や KILL_FLAG_CLEAR_ON_START の設定に特に注意してください
- OpenAI を使う機能は API コストやレート制限に注意。API キーは OPENAI_API_KEY に設定
- validate_config を起動前に実行して設定不備を検出する運用を推奨します
- ログディレクトリの作成に失敗するとファイル出力は無効化され、コンソールのみになります
- DB マイグレーションは init_monitoring_db で一部自動追加（例: latency_ms, peak_value）

ライセンス・貢献
----------------
- この README はコードベースに基づく要約ドキュメントです。ライセンス情報やコントリビュート方法はリポジトリの LICENSE / CONTRIBUTING を参照してください（存在する場合）。

問い合わせ
----------
実行時の問題や設定に関する問い合わせは、リポジトリの issue に記載するか、運用チーム内のドキュメントに従ってください。

以上。必要であれば各コマンドの具体的な実行例や systemd / supervisor 用のデプロイ手順、運用チェックリスト（ローテーション、バックアップ、モニタリング閾値など）を追記します。どの情報がさらに必要か教えてください。