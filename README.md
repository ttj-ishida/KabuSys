KabuSys — 日本株自動売買システム
=================================

概要
----
KabuSys は日本株の自動売買・運用を支援する内部ライブラリ兼起動スクリプト群です。特徴は以下の通りです。
- 発注エンジン（ExecutionEngine）、監視コンポーネント（Monitoring）を備えた運用向け構成
- ポートフォリオ構築（候補選定・重み付け・株数決定）やリスク調整の純粋関数群
- DuckDB / SQLite を用いたデータ分析・監視ログ永続化
- ニュースを LLM（OpenAI）でスコアリングする AI モジュール（news_nlp）や市場レジーム判定
- ペーパートレード用モード（本番 DB と完全分離）と各種運用ツール（検証レポート等）

主な機能
-------
- 実行エンジン起動: run_execution.py
  - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し、data/paper_trading.db に記録
  - プロセス優先度を High に設定、PID ファイル管理、停止フラグ監視
- 監視ループ起動: run_monitoring.py
  - SystemMonitor / TradeMonitor / RiskMonitor を定期実行し、アラートや Kill Switch を評価
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）
  - 監視は環境に関わらず本番 sqlite_path を使用（監視ログは production DB へ）
- ポートフォリオ構築
  - 候補選定（スコア / signal_rank ベース）、等金額・スコア重み配分、リスクベースの株数決定
  - セクターキャップ適用・レジーム乗数計算
- リサーチ（research）
  - ファクター計算（Momentum / Volatility / Value）、将来リターン / IC 計算、統計サマリ
  - DuckDB 接続を受け取り SQL + Python で計算（外部 API 非依存）
- AI モジュール（ai）
  - news_nlp: raw_news を集約して OpenAI に投げ、銘柄ごとのセンチメント ai_score を ai_scores テーブルへ書き込み
  - regime_detector: ETF（1321）MA200 乖離 + マクロニュースの LLM スコアで market_regime を判定
- ユーティリティ
  - ロギング設定（logs/ 日次ローテーション）・プロセス優先度 / CPU affinity 設定
  - .env 対話式ウィザード（config_setup.py）、設定検証 CLI（validate_config.py）
- ツール
  - paper_verification_report: ペーパートレード DB から稼働率・成功率・レイテンシ等の検証レポート生成

セットアップ手順
--------------
前提
- Python 3.10+ を推奨（型ヒント等を利用）
- 必要パッケージ（最低限）:
  - duckdb
  - psutil
  - openai（AI 機能を使う場合）
  - PyYAML（config YAML 検証を使う場合）
- インストール例:
  - pip install duckdb psutil openai PyYAML

環境変数（最低限設定が必要なもの）
- JQUANTS_REFRESH_TOKEN — J-Quants API（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- OPENAI_API_KEY — OpenAI を使う機能を使う場合（news_nlp / regime_detector）
- KABUSYS_ENV — 実行環境（development / paper_trading / live）。デフォルトは development
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード DB（デフォルト data/paper_trading.db）
- LOG_LEVEL, LOG_DIR 等（任意）

.env ファイル作成
1. 対話式ウィザードで .env を作成:
   - python -m kabusys.config_setup
2. 作成後に検証:
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit 1）

自動 .env ロード
- パッケージ初期化時にプロジェクトルート（.git または pyproject.toml）を探索して .env(.local) を自動で環境変数に読み込みます。
- 自動ロードを無効化する場合:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

使い方（起動 / CLI）
------------------
主要エントリポイント（プロジェクトルート直下で実行する想定）:

- 実行エンジン起動（本番 / ペーパー判定は KABUSYS_ENV に依存）:
  - python -m kabusys.run_execution
  - 実行中に data/stop_requested.flag を作ると安全に停止
  - PID ファイル: data/execution.pid（settings.pid_file_path で上書き可）
- 監視ループ起動:
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更: export MONITOR_POLL_INTERVAL=30
  - 停止フラグ: src/.../stop_requested.flag を検出すると監視ループを終了
- .env 設定ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
- ペーパートレード検証レポート:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を明示する場合:
    - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

AI 機能についての注意
- news_nlp / regime_detector は OpenAI API を利用します。OPENAI_API_KEY を .env に設定するか、api_key 引数で渡してください。
- API 呼び出しは再試行ロジックを持ちますが、失敗時はフェイルセーフ（スコアを 0 にフォールバック、処理継続）します。

監視と停止
- Kill Switch:
  - RiskMonitor の評価により KillSwitch が data/kill.flag を書き込むと ExecutionEngine に停止シグナルを送れます。
  - Kill flag を自動クリアする設定: KILL_FLAG_CLEAR_ON_START（本番では 0 を推奨）
- 停止フラグ:
  - data/stop_requested.flag を配置すると run_execution/run_monitoring のループが終了します。

ログ
---
- デフォルトは logs/ ディレクトリにアプリ名ごとの日次ローテーションログを出力
- 環境変数で変更可能:
  - LOG_DIR: ログディレクトリ
  - LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- setup_logging() を各起動スクリプトで呼んで統一的に設定

ディレクトリ構成（主要ファイル）
---------------------------
src/kabusys/
- __init__.py
- config.py — 環境変数 / Settings 管理、.env 自動読み込みロジック
- config_setup.py — .env 対話式作成ウィザード
- validate_config.py — 起動前の設定検証 CLI
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — SystemMonitor ポーリング起動スクリプト

サブパッケージ（要約）
- execution/
  - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py
  - 実行エンジン本体とブローカクライアントの抽象化（paper_trading は MockBroker を使用）
- monitoring/
  - monitoring_db.py — SQLite による永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py — CPU/メモリ/ディスク/プロセス PID・データ鮮度監視
  - trade_monitor.py, risk_monitor.py, kill_switch.py, alert_manager.py, monitoring_engine.py
- portfolio/
  - portfolio_builder.py — 候補選定・スコアソート
  - position_sizing.py — 株数決定・単元丸め・aggregate cap
  - risk_adjustment.py — セクター上限・レジーム乗数
- research/
  - factor_research.py — Momentum/Volatility/Value 計算
  - feature_exploration.py — forward returns / IC / 統計サマリ
- ai/
  - news_nlp.py — ニュースセンチメントスコアリング（OpenAI）
  - regime_detector.py — レジーム判定（ETF MA200 + マクロニュース）
- utils/
  - logging_setup.py — ログ初期化（Stream + TimedRotatingFileHandler）
  - process_priority.py — プロセス優先度 / CPU affinity 設定（psutil 使用）
- tools/
  - paper_verification_report.py — ペーパートレード検証レポート生成ツール

運用時の注意点・ベストプラクティス
---------------------------------
- 本番（KABUSYS_ENV=live）では .env の内容を十分に確認してください（validate_config の警告を重視）。
- Kill Switch の自動クリア（KILL_FLAG_CLEAR_ON_START=1）は本番では危険です。開発専用にしてください。
- ペーパートレードは paper_trading 用 DB に完全分離されます。運用時の誤発注リスクを避けるため、環境変数の確認を習慣化してください。
- OpenAI を使う機能は API コストとレイテンシに注意してください。API キーの管理は慎重に。

追加情報
---------
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）を環境変数で上書き（デフォルト 60 秒）
- PAPER_FILL_MODE: paper_trading 時の MockBroker の約定挙動（instant / partial / never / reject）
- ローカルでのテストや CI では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動 .env 読み込みを抑止できます

質問やドキュメントへの追記希望があれば教えてください。README を用途（開発者向け / 運用手順書 / デプロイ手順）に合わせて拡張できます。