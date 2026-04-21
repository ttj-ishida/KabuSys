KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買・研究・監視を目的とした Python パッケージです。  
主な役割は以下の通りです。

- 実行エンジン（ExecutionEngine）: ブローカークライアントを介した発注管理・リスク制御
- 監視（Monitoring）: システム稼働状況、注文・リスクのチェック、Kill Switch の生成
- 研究（Research）: ファクター計算・将来リターン・IC 解析などの分析モジュール（DuckDB を利用）
- ポートフォリオ構築（Portfolio）: 候補選定・重み付け・ポジションサイズ計算・リスク調整
- AI（news_nlp / regime_detector）: OpenAI を用いたニュースセンチメント評価・市場レジーム判定
- ツール類（tools）: ペーパートレード検証レポート等の補助スクリプト
- 設定ユーティリティ: .env 対話型ウィザード、設定検証 CLI

特徴
----
- 本番／ペーパートレードの明確な分離（KABUSYS_ENV による切替）。ペーパートレード時は MockBrokerClient を使用し、別 SQLite（data/paper_trading.db）に記録されます。
- DuckDB を用いた高速な時系列ファクター計算（prices_daily / raw_financials 等を対象）。
- OpenAI（gpt-4o-mini 等）を用いたニュースのセンチメント解析・レジーム判定（API 呼び出しはフェイルセーフ設計）。
- 監視機構（Monitoring）による稼働率・滞留注文・ドローダウン監視と、必要時に kill.flag を作成して ExecutionEngine を停止可能。
- ログはコンソール出力＋日次ローテーション（logs/<app>.log）で運用。

前提 / 推奨環境
----------------
- Python >= 3.10（型注釈に | 演算子を使用）
- 推奨パッケージ（例）:
  - duckdb
  - psutil
  - openai
  - PyYAML（設定検証で YAML をチェックする場合）
- データフォルダ: data/、ログフォルダ: logs/（自動作成されます）

セットアップ手順
----------------
1. リポジトリをクローンし、仮想環境を作成・有効化します。
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要なパッケージをインストールします（requirements.txt がある場合はそれを使用）。
   - pip install duckdb psutil openai pyyaml

3. 初期設定ファイル（.env）を作成します（対話式ウィザード）。
   - python -m kabusys.config_setup
   ウィザードは .env の初期作成／更新を支援します。

4. 設定を検証します。
   - python -m kabusys.validate_config
   --strict オプションを付けると警告も失敗扱いになります。

5. 必要に応じてデータディレクトリを作成します（多くのスクリプトが自動作成しますが確認推奨）。
   - mkdir -p data logs

主要環境変数（抜粋）
-------------------
（詳しいデフォルトや説明は kabusys.config.Settings を参照してください）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード

重要なオプション:
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視 DB）パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — ペーパートレードの約定モード（instant|partial|never|reject、デフォルト: instant）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- LOG_DIR — ログ保存ディレクトリ（デフォルト: logs/）
- OPENAI_API_KEY — OpenAI API キー（AI モジュール利用時）

監視・停止関連:
- PID ファイル: data/execution.pid（Settings.pid_file_path）
- Kill Flag: data/kill.flag（Settings.kill_flag_path）
- stop_requested.flag: 起動スクリプトが検出する停止フラグ（data/stop_requested.flag を生成すると起動ループが終了します）
- MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒、デフォルト: 60）

使い方（主要スクリプト / CLI）
---------------------------

- 設定ウィザード
  - python -m kabusys.config_setup
    対話式で .env を作成・更新します。

- 設定検証
  - python -m kabusys.validate_config [--strict]

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して data/paper_trading.db に記録します。
    - 起動前に data/stop_requested.flag が存在すると起動をスキップします。
    - 停止は data/stop_requested.flag を作成するか、Kill Switch（kill.flag）等で制御します。

- 監視プロセス起動（SystemMonitor のポーリング）
  - python -m kabusys.run_monitoring
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）。
    - 監視は本番 sqlite_path（Settings.sqlite_path）を使用します（環境に関係なく本番 DB を参照する設計）。
    - 監視ループは data/stop_requested.flag を検出すると終了します。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
    - デフォルト DB: env または data/paper_trading.db
    - 出力: 標準出力に期間内の稼働率・注文成功率・レイテンシ等を集計し PASS/FAIL 判定を提示します。

ライブラリ利用例
----------------
- ポートフォリオ構築:
  - from kabusys.portfolio import select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes
- 研究モジュール:
  - from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic
- AI:
  - from kabusys.ai import score_news
    - score_news(conn, target_date, api_key=None)
- 監視・DB ユーティリティ:
  - from kabusys.monitoring.monitoring_db import init_monitoring_db, MonitoringDB

挙動・運用上のポイント
-------------------
- ペーパートレードは本番 DB から切り離されます（PAPER_TRADING_SQLITE_PATH を利用）。
- OpenAI を利用する処理は API キーが必須です。API 呼び出し失敗時は安全側にフォールバックするよう実装されていますが、API キーの設定を忘れないでください。
- ログは stdout と logs/<app>.log（日次ローテーション）に出ます。LOG_DIR で変更可能。
- 監視と実行エンジンの停止は主に以下の仕組みで行います:
  - stop_requested.flag (data/stop_requested.flag): 起動ループを優雅に終了させるために使用
  - kill.flag (data/kill.flag): KillSwitch が閾値到達時に作成し ExecutionEngine に停止シグナルを送ります
- init_monitoring_db は既存 DB に対するマイグレーション（カラム追加など）を含み、冪等に実行できます。

ディレクトリ構成（抜粋）
-----------------------
src/kabusys/
- __init__.py                   — パッケージ定義, __version__
- config.py                     — 環境変数 / Settings 管理（.env 自動ロード機能含む）
- config_setup.py               — .env 対話式ウィザード
- validate_config.py            — 起動前設定検証 CLI
- run_execution.py              — ExecutionEngine 起動スクリプト
- run_monitoring.py             — SystemMonitor 起動スクリプト

subpackages:
- ai/
  - news_nlp.py                 — ニュースセンチメント (OpenAI)
  - regime_detector.py          — 市場レジーム判定 (OpenAI + MA)
- monitoring/
  - monitoring_db.py            — SQLite 監視 DB の永続化レイヤ
  - system_monitor.py           — システム状態・データ鮮度チェック
  - trade_monitor.py            — （滞留注文等の）注文監視
  - risk_monitor.py             — ドローダウン / ポジション上限チェック
  - kill_switch.py              — kill.flag の生成 / 管理
  - monitoring_engine.py        — 各 Monitor を束ねる
  - alert_manager.py            — （通知機構: LINE 等）※実装参照
- execution/
  - execution_engine.py         — ExecutionEngine 本体（EngineConfig 等）
  - broker_factory.py           — ブローカークライアントの生成（Mock/実ブローカー）
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - risk_manager.py
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- monitoring/ (前述)
- tools/
  - paper_verification_report.py
- utils/
  - logging_setup.py            — ログ設定ユーティリティ（Stream + TimedRotatingFile）
  - process_priority.py         — クロスプラットフォームのプロセス優先度設定
- data/                         — デフォルトのデータファイル（.gitignore 推奨）

追加情報 / 運用注意
-------------------
- .env はセキュアに管理し、決してバージョン管理にコミットしないでください（config_setup.py の出力ヘッダにも警告あり）。
- validate_config.py は運用前に必ず実行し、KABUSYS_ENV=live の場合は特に注意を払ってください（LINE 通知設定や kill flag の挙動などに関する警告を出します）。
- OpenAI や外部 API の呼び出しは料金・レート制限が発生します。production で利用する場合はレート管理・コスト管理を行ってください。

そのほか
--------
この README はコードベースから抽出した主要な使い方・設計方針をまとめたものです。各モジュールには docstring と実装コメントが比較的詳細に記載されていますので、個別機能の詳細は該当ファイルを参照してください。必要ならば README に追記する点（例: より詳しい運用手順、systemd/cron 用の起動例、テスト手順など）を教えてください。