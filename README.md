README（日本語）
============

概要
----
KabuSys は日本株向けの自動売買 / 研究 / 監視を目的とした Python コードベースです。本リポジトリには以下の主要コンポーネントが含まれます。

- ExecutionEngine（発注/注文管理/リスク管理）
- Monitoring（システム状態監視・アラート・Kill Switch）
- Portfolio 構築・ポジションサイズ算出ロジック
- Research（ファクター計算・特徴量探索）
- AI モジュール（OpenAI を用いたニュースセンチメント / レジーム判定）
- CLI ツール（.env ウィザード、設定検証、ペーパートレード検証レポート等）

主な特徴
--------
- 実行環境切替: KABUSYS_ENV により development / paper_trading / live を選択可能
- Paper Trading: paper_trading 用に発注を模擬する MockBroker を用意し、専用 DB（data/paper_trading.db）で完全分離
- 監視: SystemMonitor / TradeMonitor / RiskMonitor を統合する MonitoringEngine。kill.flag による安全停止
- ポートフォリオ構築: 候補選定、等重・スコア重み付け、セクター制約、リスクベースのポジション算出
- 研究機能: DuckDB を利用したファクター計算（モメンタム / ボラティリティ / バリュー）と IC 計算等
- AI サポート: OpenAI（gpt-4o-mini 等）を利用したニュース NLP / マクロセンチメントでのレジーム判定
- ロギング: 統一的ログ設定（コンソール + 日次ローテートファイル）

セットアップ手順
----------------
1. システム要件
   - Python 3.10+（型アノテーションで | を使用しているため）
   - SQLite（Python に同梱）
   - 推奨パッケージ（例）:
     - duckdb
     - psutil
     - openai
     - PyYAML（config 検証で任意）
   - 実際のインストール方法はプロジェクトの requirements.txt があればそれを使用してください:
     - pip install -r requirements.txt
   - ない場合は最低限:
     - pip install duckdb psutil openai

2. プロジェクトルートに移動
   - この README はパッケージの top-level がプロジェクトルート（.git または pyproject.toml を含む場所）であることを前提とします。

3. 環境変数 (.env) の準備
   - 対話式ウィザードで .env を作成/更新できます:
     - python -m kabusys.config_setup
   - 主要な必須環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
   - AI を利用する場合:
     - OPENAI_API_KEY（OpenAI 呼び出しに必要）
   - 重要なオプション / デフォルト:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH — デフォルト: data/paper_trading.db
     - LOG_LEVEL — デフォルト: INFO
     - PAPER_FILL_MODE — instant | partial | never | reject（paper_trading の動作）
     - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか (0/1)
     - MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒、デフォルト 60）

4. 設定の検証
   - .env と config/*.yaml（存在する場合）を検証できます:
     - python -m kabusys.validate_config
   - 警告もエラー扱いにする厳格モード:
     - python -m kabusys.validate_config --strict

5. データディレクトリ / ログディレクトリ
   - デフォルトの DB / フラグ / PID / ログは project_root/data と project_root/logs に作成されます。必要に応じて環境変数で上書きしてください（例 DUCKDB_PATH, SQLITE_PATH, LOG_DIR）。

使い方（起動 / CLI）
-------------------
- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict をつけると警告があっても exit(1)

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBroker を利用し data/paper_trading.db を使います
  - 起動時に data/stop_requested.flag が既にあると起動せず終了します
  - 停止は監視側から stop flag（data/stop_requested.flag）を置くことで実行できます
  - 実行中は PID ファイル（デフォルト data/execution.pid）を作成します

- 監視ループ起動（SystemMonitor）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60）
  - 監視は KABUSYS_ENV に関わらず本番 sqlite_path（Settings.sqlite_path）を使います（監視ログは単一の monitoring DB に蓄積）
  - 停止はプロジェクトルート/data/stop_requested.flag を作成することで行えます

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to   YYYY-MM-DD
    - --db PATH （PAPER_TRADING_SQLITE_PATH より優先）

- AI モジュール（プログラム内 API）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - conn: DuckDB 接続
    - api_key を None にすると環境変数 OPENAI_API_KEY を参照
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

停止 / Kill Switch
------------------
- Kill Switch は監視コンポーネント（RiskMonitor 等）により data/kill.flag に理由を書き込むことで ExecutionEngine に停止シグナルを送ります。KillSwitch は冪等に動作し、既存 flag がある場合は上書きしません。
- run_execution/run_monitoring の手動停止は KeyboardInterrupt（Ctrl+C）またはプロジェクトルート/data/stop_requested.flag を作成することで行えます。

ログ
----
- ログは標準出力（stdout）と日次ローテートファイル（logs/<app_name>.log）に出力されます。ログディレクトリは環境変数 LOG_DIR で指定可能（デフォルト logs/）。ログレベルは LOG_LEVEL で指定。

ディレクトリ構成（主要ファイル）
------------------------------
以下はソースルート src/kabusys 以下の主要なモジュールと説明です（プロジェクトルートからの相対パスは src/kabusys/...）。

- __init__.py
  - パッケージ定義（バージョン等）

- config.py
  - 環境変数/.env の読み込みと Settings クラス（アプリ設定）を提供

- config_setup.py
  - .env 作成 / 更新の対話式ウィザード

- validate_config.py
  - 起動前の環境・設定検証 CLI

- run_execution.py
  - ExecutionEngine 起動スクリプト（PID 管理、paper_trading 切替）

- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL）

- utils/
  - logging_setup.py — ログ設定ユーティリティ
  - process_priority.py — プロセス優先度 / CPU affinity 設定
  - （その他ユーティリティ）

- monitoring/
  - monitoring_db.py — SQLite を用いた監視ログ永続化層（テーブル作成・読み書き）
  - system_monitor.py — システム状態・データ鮮度監視
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - trade_monitor.py — 注文ログ監視（該当ファイルあり）
  - monitoring_engine.py — Monitor を束ねるエンジン
  - kill_switch.py — kill.flag 書き込みユーティリティ
  - alert_manager.py — アラート送信管理（実装による）

- execution/
  - execution_engine.py — ExecutionEngine 本体（スレッドで実行）
  - order_manager.py, order_repository.py, risk_manager.py, reconciler.py など（注文・リスク管理）

- portfolio/
  - portfolio_builder.py — 候補選定 / 重み計算
  - position_sizing.py — 発注株数算出（単元丸め・aggregate cap 等）
  - risk_adjustment.py — セクター制約・レジーム乗数

- research/
  - factor_research.py — モメンタム / ボラティリティ / バリュー等のファクター計算（DuckDB）
  - feature_exploration.py — 将来リターン計算 / IC / 統計サマリー

- ai/
  - news_nlp.py — ニュース記事を OpenAI でセンチメント評価し ai_scores に書き込むロジック
  - regime_detector.py — マクロ + ETF MA200 を用いた日次レジーム判定

- tools/
  - paper_verification_report.py — ペーパートレード結果の検証レポート生成スクリプト

補足 / 注意事項
--------------
- 本番運用時は KABUSYS_ENV=live に設定して慎重に運用してください。validate_config は本番時の追加チェック（LINE 通知設定など）を行います。
- AI（OpenAI）利用部分は API キー必須です。API 呼び出しはリトライやフェイルセーフを含む実装になっていますが、API 利用料やレート制限に注意してください。
- Paper Trading は実運用 DB と分離されるよう設計されています（PAPER_TRADING_SQLITE_PATH）。paper_trading を利用する場合は該当パスを確認してください。
- monitoring モジュールは監視データを単一の SQLite（Settings.sqlite_path）に永続化します。監視は環境に関係なく本番の sqlite_path を参照する点に注意してください。
- デフォルトのデータ/ログフォルダはプロジェクトルート/data と project_root/logs です。必要に応じて権限やバックアップを設定してください。

問い合わせ・開発メモ
------------------
- 各モジュールに詳細な docstring と設計ノートが含まれており、コード中に注記があります。実装や拡張を行う際はまず該当ファイルの docstring を参照してください。
- テストや CI のセットアップはこの README では触れていません。ユニットテストを追加する際は各 pure function（portfolio/*、research/* など）から着手すると良いです。

以上。必要であれば README にインストールの具体的な pip コマンド一覧やサンプル .env テンプレート、起動/停止のユースケース例（systemd サービス定義や Dockerfile 例）を追加で作成します。どの情報が必要か教えてください。