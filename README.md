KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買フレームワークです。  
本リポジトリは以下を含むモジュール群で構成されています。

- 発注処理を担う ExecutionEngine（本番 / ペーパートレード対応）
- システム監視・アラート・Kill Switch を実装した Monitoring
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ計算）
- 研究用モジュール（ファクター計算・特徴量解析）
- AI ベースのニュースセンチメント評価 / レジーム判定（OpenAI）
- 運用支援ツール（設定ウィザード・設定検証・レポート生成）
- ロギング / プロセス優先度設定等のユーティリティ

主な特徴
--------
- ExecutionEngine は KABUSYS_ENV に応じて実際のブローカーまたは MockBroker を使い分け（paper_trading モードで本番 DB と分離）
- Monitoring は定期ポーリングでシステム状態／注文ログ／リスク指標を SQLite に永続化し、Kill Switch を発動可能
- ポートフォリオ構築は純粋関数実装（候補選定・等配分・スコア加重・リスク調整・銘柄ごとの株数決定）
- Research モジュールは DuckDB を使った高速集計（ファクター計算、将来リターン、IC 等）
- AI モジュールは OpenAI を呼び、ニュースを銘柄別にスコアリング、market_regime を判定（API エラーはフェイルセーフ）
- 設定ウィザード（config_setup.py）と設定検証 CLI（validate_config.py）で初期設定を対話的 / 自動にサポート
- 日次ローテートのファイルログ（logs/<app>.log）＋コンソール出力を統一的に設定する logging_setup

セットアップ手順
----------------
1. リポジトリをクローン、作業ディレクトリへ移動
   - git clone ...; cd <repo>

2. Python 仮想環境を作成して有効化（例）
   - python -m venv .venv
   - Unix/macOS: source .venv/bin/activate
   - Windows: .venv\Scripts\activate

3. 必要パッケージをインストール
   - 以下をインストールしてください（プロジェクトに requirements.txt が無い場合の主要依存）:
     - duckdb
     - psutil
     - openai
     - PyYAML（config/*.yaml の検証を行う場合）
   - 例:
     - pip install duckdb psutil openai PyYAML

4. データディレクトリの準備（自動作成されることもあるが事前に作ると安心）
   - mkdir -p data logs

5. 環境変数の設定
   - .env を用意する（推奨: python -m kabusys.config_setup でウィザード実行）
   - 最低限必要な環境変数（必須）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - よく使う変数とデフォルト:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH — デフォルト: data/paper_trading.db
     - LOG_LEVEL — デフォルト: INFO
     - OPENAI_API_KEY — OpenAI を使う機能で必要
     - MONITOR_POLL_INTERVAL — 監視ループの間隔（秒、デフォルト 60）

6. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit code=1）

基本的な使い方
--------------

設定作成 / 検証
- 対話的に .env を作る:
  - python -m kabusys.config_setup
- 設定を検証:
  - python -m kabusys.validate_config
  - --strict を付けて厳密チェック

ExecutionEngine（発注エンジン）起動
- 本番相当（KABUSYS_ENV=live）またはローカル開発（development）:
  - KABUSYS_ENV=development python -m kabusys.run_execution
- ペーパートレード（MockBroker を使用、ペーパー専用 DB を使用）:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- 動作概要:
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を用い paper_trading 用 DB (data/paper_trading.db) に記録する。
  - 起動中、data/execution.pid に PID を書き、停止は data/stop_requested.flag を作成して行える。

Monitoring（監視ループ）起動
- python -m kabusys.run_monitoring
- 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き（例: MONITOR_POLL_INTERVAL=30）
- 監視は MonitoringEngine を用いて SystemMonitor / TradeMonitor / RiskMonitor を定期実行し、SQLite（monitoring.db）へログを記録する。
- Monitoring は KABUSYS_ENV にかかわらず本番の sqlite_path（SQLITE_PATH）を参照する点に注意。

運用サポートツール
- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB は data/paper_trading.db。--db で指定可能。
- AI スコア／レジーム判定（ライブラリ API）:
  - from kabusys.ai.news_nlp import score_news
    - score_news(conn, target_date, api_key=None)
  - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, target_date, api_key=None)

停止 / Kill Switch
- kill.flag を書き込むことで ExecutionEngine を停止させる Kill Switch を実装
  - KillSwitch は監視結果（ドローダウンやポジション上限）に応じて data/kill.flag を生成する
- 手動停止フラグ:
  - data/stop_requested.flag を作ると run_execution / run_monitoring のループが検知して安全に停止する

ログ
----
- ログはデフォルトで logs/<app_name>.log に日次ローテート（30 日保持）され、コンソール（stdout）にも出力されます。
- ログ設定は kabusys.utils.logging_setup.setup_logging を通じて統一されています。
- app_name 例: "execution", "monitoring"

環境変数（主要）
----------------
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 任意 / 重要:
  - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
  - DUCKDB_PATH (例: data/kabusys.duckdb)
  - SQLITE_PATH (例: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (例: data/paper_trading.db)
  - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL)
  - OPENAI_API_KEY (AI 機能で必要)
  - MONITOR_POLL_INTERVAL (監視ポーリング間隔 [秒])
  - KILL_FLAG_CLEAR_ON_START (0/1) — 本番で 1 は危険（自動クリア）

ディレクトリ構成（主要ファイル）
----------------------------
src/kabusys/
- __init__.py
- __version__ = "0.1.0"

トップレベルスクリプト
- run_execution.py — ExecutionEngine 起動スクリプト（KABUSYS_ENV で挙動切替）
- run_monitoring.py — SystemMonitor のポーリングループ起動スクリプト
- validate_config.py — 設定検証 CLI
- config_setup.py — .env 対話式作成ウィザード

設定 / 設定関連
- config.py — Settings クラス（.env 自動読み込み、環境変数取得 / 検証）
- config/ *.yaml — 各種設定ファイル（テンプレートは scripts 等で生成想定）

実行・注文関連
- execution/
  - execution_engine.py
  - order_manager.py
  - order_repository.py
  - broker_factory.py
  - reconciler.py
  - risk_manager.py

監視関連
- monitoring/
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - monitoring_db.py — SQLite テーブル定義と単純な永続化層
  - monitoring_engine.py — 各モニタを束ねる
  - kill_switch.py
  - alert_manager.py

ポートフォリオ構築
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py

研究（Research）
- research/
  - factor_research.py — モメンタム / バリュー / ボラティリティ計算（DuckDB）
  - feature_exploration.py — 将来リターン / IC / 統計サマリ

AI（OpenAI 統合）
- ai/
  - news_nlp.py — ニュースを銘柄別に集約し OpenAI でセンチメント算出、DuckDB に書き込み
  - regime_detector.py — マクロ＋ETF MA200 を合成して市場レジーム判定

ユーティリティ
- utils/
  - logging_setup.py — ログの統一設定
  - process_priority.py — プロセス優先度 / CPU affinity 設定

ツール
- tools/
  - paper_verification_report.py — Paper Trading 検証レポート生成

データ / ログ
- data/ (既定の DB 等を置く場所)
  - monitoring.db (デフォルト SQLITE_PATH)
  - paper_trading.db (ペーパートレード用)
  - kabusys.duckdb (デフォルト DUCKDB_PATH)
  - execution.pid, stop_requested.flag, kill.flag などの運用フラグ/PID

追加メモ / 運用上の注意
----------------------
- Monitoring は KABUSYS_ENV に関係なく設定された本番 sqlite_path を使用します。ペーパートレード DB と分離したい場合は run_execution 側で PAPER_TRADING_SQLITE_PATH を使用します。
- OpenAI API を使う機能は API キーの管理（環境変数 OPENAI_API_KEY）に注意してください。API エラーは多くの場合フェイルセーフで 0.0 相当にフォールバックしますが、運用上の通知は確認してください。
- 本番（KABUSYS_ENV=live）での起動前に必ず python -m kabusys.validate_config で設定チェックを行ってください（LINE 通知設定や Kill Switch の動作などを確認）。
- logs/ と data/ は Git にコミットしないでください（.env も同様）。.env は機密情報を含みます。

問い合わせ / 開発
-----------------
- 各モジュールは内部ドキュメント（docstring）で設計意図と使用例が記載されています。ユニットテストや実行ログを参照しながら拡張してください。

以上が本コードベースの README になります。必要ならば「具体的な起動例（systemd / supervisor / docker compose 例）」「requirements.txt の提案」や「CI 用テスト実行手順」などを追加で作成します。どの情報を追加しましょうか？