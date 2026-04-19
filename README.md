KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買システム用ライブラリ／起動スクリプト群です。
主な機能は以下の通りです:

- ExecutionEngine による注文発行（実環境 / ペーパートレード切替対応）
- 監視（MonitoringEngine / SystemMonitor / TradeMonitor / RiskMonitor）
- Kill Switch（閾値超過時に Execution を停止する旗ファイル）
- ポートフォリオ構築（銘柄選定・重み・ポジションサイズ計算）
- 研究用モジュール（ファクター計算・将来リターン・IC 等）
- AI 支援モジュール（ニュース NLP による銘柄センチメント、レジーム判定）
- 運用補助ツール（.env ウィザード、設定検証、Paper Trading 検証レポート生成）
- 共通ユーティリティ（ロギング設定、プロセス優先度設定など）

主な機能一覧
-------------
- 実行・監視
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV による paper/live 切替）
  - run_monitoring.py: SystemMonitor のポーリングループを起動（MONITOR_POLL_INTERVAL で間隔調整可能）
- 環境設定 / 検証
  - config_setup.py: .env の対話式作成・更新ウィザード
  - validate_config.py: .env と config/*.yaml の起動前チェック（--strict オプション有）
- ポートフォリオ構築
  - portfolio.select_candidates / calc_equal_weights / calc_score_weights
  - portfolio.calc_position_sizes（リスクベース等の株数計算）
  - portfolio.apply_sector_cap / calc_regime_multiplier（セクター制限・レジーム補正）
- 研究（research）
  - factor_research: momentum / volatility / value 等のファクター計算（DuckDB 使用）
  - feature_exploration: forward returns / IC / 統計サマリ等
- AI（OpenAI）
  - ai.news_nlp.score_news: ニュース記事を LLM でスコアリングして ai_scores に書込
  - ai.regime_detector.score_regime: マクロ＋ETF MA を合わせて市場レジームを判定して書込
- 監視永続化
  - monitoring.monitoring_db.MonitoringDB: SQLite ベースの監視ログ読み書き
  - risk_monitor / kill_switch / monitoring_engine: 監視とアラートの統合
- ツール
  - tools.paper_verification_report: ペーパートレード結果の検証レポート生成

前提・依存
-----------
主に以下のパッケージが使用されます（環境や目的に応じて追加してください）:

- Python 3.9+
- duckdb
- psutil
- openai (AI 機能を利用する場合)
- PyYAML（config/*.yaml のパース検証を行いたい場合）
- sqlite3（標準ライブラリ）
- その他（環境に応じて必要なパッケージを追加）

例: 仮想環境作成と最低限パッケージのインストール
- python -m venv .venv
- source .venv/bin/activate
- pip install duckdb psutil openai PyYAML

セットアップ手順
----------------
1. リポジトリをクローンしてソースのルートへ移動
2. 仮想環境を作成して有効化（上記参照）
3. 必要なパッケージをインストール（上記参照）
4. .env を作成
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - あるいは .env を直接作成し、必須変数を設定する:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - 必要に応じて: KABUSYS_ENV, DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL, OPENAI_API_KEY, PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH など
   - 注意: .env は決してリポジトリにコミットしないでください。

5. 設定検証（任意）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります

環境変数（主なもの）
--------------------
- KABUSYS_ENV: 実行環境（development / paper_trading / live）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用
- KABU_API_PASSWORD: kabuステーション API パスワード
- OPENAI_API_KEY: OpenAI API キー（AI 機能利用時）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（paper_trading 時に使用）
- PAPER_FILL_MODE: ペーパー注文の約定モード（instant / partial / never / reject）
- LOG_LEVEL / LOG_DIR: ログ出力設定
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag をクリアするか（1=クリア）

起動／操作方法
--------------
- .env の作成・編集
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - Strict モード: python -m kabusys.validate_config --strict

- ExecutionEngine（注文実行）起動
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い data/paper_trading.db に発注情報を記録（本番 DB と分離）
    - 停止: プロジェクトルート/data/stop_requested.flag を作成するとエンジンが停止します
    - PID ファイル: data/execution.pid（設定により変更可能）

- Monitoring 起動（常駐）
  - python -m kabusys.run_monitoring
  - 挙動:
    - MONITOR_POLL_INTERVAL によりポーリング間隔を変更可（デフォルト 60 秒）
    - 実行中に data/stop_requested.flag が存在するとループを抜けて終了
    - 監視ログは sqlite_path（デフォルト data/monitoring.db）へ永続化

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - オプションで期間指定: --from YYYY-MM-DD --to YYYY-MM-DD
  - DB を指定する場合: --db PATH（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- AI 機能（プログラム呼び出し例）
  - ニューススコアリング:
    - from kabusys.ai import score_news
    - score_news(duckdb_conn, target_date, api_key="...")
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key="...")

停止・Kill Switch
-----------------
- 運用中に重大リスク（ドローダウン超過、ポジション数上限超過）が検出された場合、KillSwitch により data/kill.flag が書き込まれ、ExecutionEngine は停止シグナルを受けます。
- 起動時に KILL_FLAG_CLEAR_ON_START=1 にすると kill.flag を自動クリアします（本番では 0 推奨）。
- 手動で停止したい場合はプロジェクトルート/data/stop_requested.flag を作成してください（monitoring / execution 両方がチェックします）。

ログ
---
- デフォルトのログディレクトリ: logs/
- ログローテート: 日次（30日分保持）
- ログ設定ユーティリティ: kabusys.utils.logging_setup.setup_logging(app_name="execution" など)
- 環境変数 LOG_DIR / LOG_LEVEL でカスタマイズ可能

ディレクトリ構成（主要ファイル）
-------------------------------
src/kabusys/
- __init__.py — パッケージ定義（バージョンなど）
- config.py — 環境変数読み込み・Settings クラス（.env 自動ロード機能含む）
- config_setup.py — .env 対話式ウィザード
- validate_config.py — 設定検証 CLI
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — SystemMonitor ポーリング起動スクリプト

サブパッケージ（抜粋）
- execution/  — BrokerFactory / ExecutionEngine / OrderManager 等（発注系）
- monitoring/
  - monitoring_db.py — SQLite スキーマ初期化と MonitoringDB（読み書き層）
  - system_monitor.py, trade_monitor.py, risk_monitor.py, kill_switch.py, monitoring_engine.py
- portfolio/
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py
- research/
  - factor_research.py, feature_exploration.py（DuckDB を受け取り計算）
- ai/
  - news_nlp.py, regime_detector.py（OpenAI と連携する NLP 機能）
- utils/
  - logging_setup.py — 標準化されたログ設定
  - process_priority.py — プロセス優先度 / CPU affinity 設定
- tools/
  - paper_verification_report.py — ペーパートレード検証レポート生成

運用上の注意
-------------
- .env は機密情報を含むため Git に含めないでください。
- KABUSYS_ENV=live のときは設定を慎重に確認してください（LINE 通知設定や Kill Switch の取扱い等）。
- OpenAI API を使う機能は API キーが必要で、コスト・レイテンシに注意してください。AI 呼び出しはリトライ・フォールバック設計（失敗時は安全にスキップ）になっていますが、運用ポリシーに沿ってください。
- paper_trading モードは本番 DB と完全分離するよう設計されています。ペーパートレード時の DB は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）です。

開発者向けメモ
----------------
- DuckDB 接続を受け取る関数群（research / ai 等）はデータベースを直接参照しない設計（テストしやすい純粋関数を目指す）。
- logging_setup.setup_logging() を早期に呼び出して一貫したログ出力を行ってください。
- process_priority.set_process_priority("high") を各起動スクリプト先頭で呼び出し、運用プロセスの優先度を高めています（プラットフォーム依存のフォールバックロジックあり）。
- monitoring.monitoring_db.init_monitoring_db(conn) は冪等でスキーマを準備します。既存 DB の簡易マイグレーションも実装済みです。

ライセンス・貢献
----------------
- 現在のパッケージにライセンス記載がない場合は、プロジェクト方針に従って LICENSE を追加してください。
- バグ修正や機能追加は PR を歓迎します。機能追加時は設定検証・ログ・エラーパスを忘れずに実装してください。

お問い合わせ
------------
実装や運用に関する質問があれば、リポジトリの issue に記載してください。