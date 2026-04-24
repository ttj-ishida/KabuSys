README — KabuSys（日本株自動売買システム）
=============================

概要
---
KabuSys は日本株の自動売買・リサーチ・監視を目的とした Python パッケージです。  
主な機能は以下の通りです:

- 発注処理を行う ExecutionEngine（本番 / ペーパートレード対応）
- システム稼働状況・注文ログ等を記録する監視コンポーネント（Monitoring）
- ポートフォリオ構築（候補選定・重み計算・ポジションサイズ計算）
- ファクター計算・特徴量探索（DuckDB を使ったリサーチ）
- ニュースの LLM ベースセンチメント評価（OpenAI 経由）
- ペーパートレード検証レポート生成ツール
- 環境設定ウィザードと設定検証ツール

主要な設計方針:
- DuckDB / SQLite をデータ永続化に利用（分析用 / 監視用を分離）
- ペーパートレードは本番 DB と分離（PAPER_TRADING_SQLITE_PATH）
- LLM 呼び出しはフェイルセーフでリトライ処理を備える
- 実運用を想定したログ・プロセス優先度・Kill Switch 機構を提供

機能一覧
---
- Execution
  - run_execution.py: ExecutionEngine の起動スクリプト
  - Paper trading（KABUSYS_ENV=paper_trading）時は MockBroker を使用し専用 SQLite に記録

- Monitoring
  - run_monitoring.py: SystemMonitor のポーリングループ起動
  - MonitoringEngine / SystemMonitor / RiskMonitor / TradeMonitor / KillSwitch
  - 監視ログ永続化（SQLite）: system_status, trade_logs, positions, risk_logs, dashboard

- Portfolio
  - 銘柄候補選定、等重 / スコア重みの計算
  - ポジションサイズ算出（lot 単位丸め、aggregate cap、リスクベースなど）
  - セクター上限適用、レジーム乗数計算

- Research
  - DuckDB 経由のファクター計算（momentum, volatility, value）
  - 将来リターン計算、IC（Information Coefficient）、factor summary

- AI（OpenAI）
  - news_nlp.score_news: raw_news をまとめて LLM に送り銘柄別センチメントを ai_scores に書込
  - regime_detector.score_regime: ma200 瞬きとマクロニュースで市場レジームを判定して記録

- ツール
  - config_setup.py: 対話式 .env 作成ウィザード
  - validate_config.py: .env や config/*.yaml の事前検証 CLI
  - tools.paper_verification_report: ペーパートレード検証レポート生成

セットアップ手順
---
1. リポジトリをクローン
   - git clone <repo>

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install -r requirements.txt
   - 必要な主なライブラリ:
     - duckdb
     - openai
     - psutil
     - （オプション）PyYAML（config/*.yaml の検証に使用）

   ※ requirements.txt がない場合は上記パッケージを個別にインストールしてください。

4. 環境変数の初期設定
   - 対話式ウィザードで .env を生成:
     - python -m kabusys.config_setup
   - 生成後、設定を検証:
     - python -m kabusys.validate_config
     - --strict を付けると警告も失敗扱いになります

主な環境変数（抜粋）
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 運用環境:
  - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
- DB パス:
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (監視用／デフォルト: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (ペーパートレード用 DB のパス)
- ログ:
  - LOG_LEVEL (デフォルト: INFO)
  - LOG_DIR (デフォルト: logs/)
- OpenAI:
  - OPENAI_API_KEY（news_nlp / regime_detector が必要な場合）
- その他:
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
  - KILL_FLAG_CLEAR_ON_START: ExecutionEngine 起動時に kill.flag を自動クリア（0/1）

使い方
---
起動・ユーティリティの例:

- .env 作成（対話式）:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine 起動:
  - python -m kabusys.run_execution
  - 概要:
    - KABUSYS_ENV=paper_trading の場合、MockBroker を使い data/paper_trading.db に記録
    - 起動時にプロセス優先度を "high" に設定
    - 停止は data/stop_requested.flag を作成するか、ExecutionEngine が内部で検出して停止

- Monitoring 起動:
  - python -m kabusys.run_monitoring
  - 概要:
    - SystemMonitor のポーリングループを開始（MONITOR_POLL_INTERVAL で制御）
    - 監視ログは sqlite_path（デフォルト data/monitoring.db）へ書き込む
    - 停止は data/stop_requested.flag を作成することで行う

- Paper Trading 検証レポート生成:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db でデータベースパス指定も可（PAPER_TRADING_SQLITE_PATH 環境変数が優先されます）

- AI モジュール呼び出し（プログラム内から）
  - from kabusys.ai import score_news
  - score_news(conn, target_date, api_key=None)  # api_key を与えるか OPENAI_API_KEY を設定

ログ・プロセス
- 共通ログ設定: kabusys.utils.logging_setup.setup_logging(app_name="...") を各起動スクリプトで呼んでいます
  - デフォルトは logs/<app_name>.log へ日次ローテーション（30日分）
  - コンソール出力は stdout（StreamHandler）
- プロセス優先度:
  - 起動スクリプトは set_process_priority("high") を実行して優先度を上げます（psutil に依存）
- Kill / Stop フラグ:
  - デフォルトファイル: data/kill.flag（KillSwitch）、data/stop_requested.flag（停止リクエスト）
  - KillSwitch はリスク条件（ドローダウンやポジション上限）で kill.flag を書き、ExecutionEngine 側で検出して停止できます

ディレクトリ構成（主要ファイル）
---
src/kabusys/
- __init__.py
- config.py
  - .env 自動読み込みロジック、Settings クラス（環境変数のラッパー）
- config_setup.py
  - 対話式 .env 生成ウィザード
- validate_config.py
  - 起動前の設定検証 CLI
- run_execution.py
  - ExecutionEngine 起動スクリプト
- run_monitoring.py
  - SystemMonitor ポーリング起動スクリプト

パッケージ群:
- kabusys/utils/
  - logging_setup.py (ログ設定)
  - process_priority.py (プロセス優先度 / CPU affinity)
- kabusys/monitoring/
  - monitoring_db.py (SQLite スキーマ + DB ラッパー)
  - system_monitor.py, trade_monitor.py, risk_monitor.py, kill_switch.py, monitoring_engine.py, alert_manager.py（監視関連）
- kabusys/execution/
  - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, broker_factory.py, risk_manager.py（発注関連）
- kabusys/portfolio/
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py（ポートフォリオ構築）
- kabusys/research/
  - factor_research.py, feature_exploration.py（ファクター・リサーチ）
- kabusys/ai/
  - news_nlp.py, regime_detector.py（LLM を使ったニュース / レジーム判定）
- kabusys/tools/
  - paper_verification_report.py（ペーパートレード検証レポート）
- data/
  - （ランタイムで生成される: monitoring.db / paper_trading.db / kill.flag / execution.pid / stop_requested.flag 等）
- logs/
  - （ログファイルが保存されるディレクトリ）

データベース（既定）
- DuckDB: data/kabusys.duckdb（分析用）
- SQLite（監視）: data/monitoring.db
- SQLite（ペーパートレード）: data/paper_trading.db（KABUSYS_ENV=paper_trading 時に使用）

追加メモ / 運用上の注意
---
- 本番運用時は KABUSYS_ENV=live に設定すると慎重なチェックが行われます（validate_config で警告が出ます）。
- .env は絶対にバージョン管理にコミットしないでください（config_setup のヘッダにも注意書きあり）。
- OpenAI API を使う機能（news_nlp, regime_detector）は API キーの管理とコストに注意してください。
- psutil による優先度設定は権限や OS によって失敗する場合があります（ログに警告が出ます）。
- monitoring 側は設定に関係なく sqlite_path（本番）を参照する実装箇所があるため、監視 DB の運用には注意してください。

ライセンス・貢献
---
- (ここにプロジェクトのライセンスやコントリビュート方法を追記してください)

問題報告・問い合わせ
---
- バグ報告や改善提案は Issue を作成してください。実運用に関わる変更は事前に議論を推奨します。

以上。README の補足や特定コマンド・モジュールの詳細な使用例や API ドキュメントが必要であれば教えてください。