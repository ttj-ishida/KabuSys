KabuSys — 日本株自動売買システム
=============================

概要
----
KabuSys は日本株の自動売買／リサーチ／監視を行うための軽量なフレームワークです。  
主な目的は以下の通りです。

- 戦略のリサーチ（ファクター計算、特徴量解析）
- ポートフォリオ構築（銘柄選定、重み付け、株数決定）
- 発注実行（本番・ペーパートレードの分離）
- 監視・アラート（システム健全性、注文滞留、リスク制御）
- AI 補助（ニュース NLP によるセンチメント、マーケットレジーム判定）
- 検証用ツール（ペーパートレードの検証レポート生成）

機能一覧
--------
主要機能の概観：

- 設定管理
  - .env 自動読み込み（プロジェクトルート検出）、config_setup による対話式 .env 作成
  - validate_config による起動前チェック
- 実行エンジン
  - ExecutionEngine（run_execution 起動スクリプト）
  - Paper trading モードは MockBroker を使用し DB を分離（data/paper_trading.db）
- 監視
  - SystemMonitor, TradeMonitor, RiskMonitor を束ねる MonitoringEngine（run_monitoring 起動）
  - kill.flag による安全停止（KillSwitch）
  - 監視ログ永続化（SQLite：monitoring.db）
- ポートフォリオ構築
  - 候補選定、等重・スコア加重、リスク調整（セクターキャップ、レジーム乗数）、ポジションサイズ算出
- リサーチ
  - ファクター計算（モメンタム、ボラティリティ、バリュー等）
  - 将来リターン、IC（スピアマンランク相関）、統計サマリー
- AI（OpenAI）
  - ニュース NLU による銘柄別センチメント（ai/news_nlp.py）
  - マクロニュース + ETF MA200 を使ったレジーム判定（ai/regime_detector.py）
- ツール
  - Paper Trading 検証レポート生成（kabusys.tools.paper_verification_report）
- ユーティリティ
  - プロセス優先度・CPU affinity 設定（psutil ベース）
  - DuckDB 接続を使った分析処理

動作前提（簡易）
----------------
- Python 3.10 以上（構文に | 型注釈等を使用）
- 推奨パッケージ（代表例）
  - duckdb
  - psutil
  - openai
  - PyYAML（config ファイル検証に任意）
- データディレクトリ（デフォルト）: data/
  - monitoring DB 等は data/ 配下を想定

セットアップ手順
----------------

1. リポジトリ取得・仮想環境作成
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージインストール
   - 代表的な依存:
     - pip install duckdb psutil openai PyYAML
   - 実プロジェクトでは requirements.txt を用意している場合はそれを使用してください。

3. .env 作成（対話式ウィザード）
   - python -m kabusys.config_setup
   - 対話に従い JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等を設定してください。
   - 重要: .env は決して Git にコミットしないでください。

4. 設定検証
   - python -m kabusys.validate_config
   - --strict オプションで警告も FAIL として扱えます。

5. AI 機能を使う場合
   - 環境変数 OPENAI_API_KEY を設定してください（score_news / score_regime が必要とします）。

基本的な使い方
--------------

1. 実行エンジン（Execution）
   - 本番（live）/ 開発/ ペーパートレードは .env の KABUSYS_ENV で切り替え。
   - ペーパートレードでは MockBroker を使い DB を分離（PAPER_TRADING_SQLITE_PATH、デフォルト data/paper_trading.db）。
   - 起動:
     - python -m kabusys.run_execution
   - 停止リクエスト:
     - run_execution はプロジェクトルート/data/stop_requested.flag の存在を監視。停止するにはこのファイルを作成します。
     - また、KillSwitch（kill.flag）を使うと ExecutionEngine に安全停止を促せます（監視側が生成）。

2. 監視ループ（Monitoring）
   - 起動:
     - python -m kabusys.run_monitoring
   - ポーリング間隔:
     - 環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可（デフォルト 60 秒）。
   - 監視は monitoring DB（Settings.sqlite_path）にログを書きます（Monitoring は環境に関わらず本番 sqlite_path を使います）。

3. ペーパートレード検証レポート
   - python -m kabusys.tools.paper_verification_report
   - 期間指定:
     - --from YYYY-MM-DD --to YYYY-MM-DD
   - DB 指定:
     - --db PATH または環境変数 PAPER_TRADING_SQLITE_PATH

4. 設定値（主な環境変数）
   - 必須:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - オプション / デフォルト:
     - KABUSYS_ENV (development | paper_trading | live) — default: development
     - DUCKDB_PATH — default: data/kabusys.duckdb
     - SQLITE_PATH — default: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH — default: data/paper_trading.db
     - LOG_LEVEL — default: INFO
     - OPENAI_API_KEY — OpenAI を用いる場合必須
     - MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒）
     - PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START なども Settings で扱います。

停止・セーフガード
-----------------
- stop_requested.flag（data/stop_requested.flag）:
  - run_execution / run_monitoring のループを安全に終了させるためにチェックされています。
- kill.flag（Settings.kill_flag_path、デフォルト data/kill.flag）:
  - KillSwitch が条件を満たすと書き込まれ、ExecutionEngine 側で検出して停止します（本番での緊急停止用）。
- PID ファイル:
  - ExecutionEngine は pid ファイルを作成します。system_monitor は PID の古い残骸を検出して削除できます。

ディレクトリ構成（主要ファイル）
------------------------------
以下は src/kabusys 配下の主なモジュールと簡単な説明です。

- kabusys/
  - __init__.py — パッケージ情報
  - config.py — 環境変数/.env 読み込み、Settings クラス
  - config_setup.py — .env を対話式で作るウィザード
  - validate_config.py — 起動前チェック CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - utils/
    - __init__.py
    - process_priority.py — psutil を使ったプロセス優先度 / CPU affinity ユーティリティ
  - execution/ (発注関連の主要モジュール) — Engine, BrokerFactory, OrderManager, Reconciler, RiskManager, OrderRepository, order_record 等（実装ファイルはこの README のコード抜粋に含まれていませんが存在を想定）
  - monitoring/
    - monitoring_db.py — SQLite 監視 DB 用ラッパー（初期化・CRUD）
    - system_monitor.py — システム状態・データ鮮度監視
    - trade_monitor.py — 注文滞留・約定異常監視
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag 制御
    - monitoring_engine.py — 各 Monitor を束ねる
    - alert_manager.py — 通知管理（LINE 等、実装に依存）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数決定と各種上限・丸め処理
    - risk_adjustment.py — セクターキャップ・レジーム乗数
    - __init__.py
  - research/
    - factor_research.py — momentum/volatility/value 等のファクター計算（DuckDB 使用）
    - feature_exploration.py — 将来リターン計算・IC・統計サマリー
    - __init__.py
  - ai/
    - news_nlp.py — ニュースを OpenAI に送り銘柄別センチメントを算出・保存
    - regime_detector.py — ETF MA200 + マクロニュースでレジーム判定
    - __init__.py
  - tools/
    - paper_verification_report.py — ペーパートレードの検証レポート生成 CLI
    - __init__.py
  - monitoring、data 等の外部ディレクトリ（data は runtime に作成）

補足・運用上の注意
-----------------
- DB の切り分け:
  - Paper trading モードは paper_trading 用の SQLite を使用し、本番 DB と分離します（安全設計）。
  - DuckDB は分析用に利用します（デフォルト data/kabusys.duckdb）。
- リソースと権限:
  - set_process_priority は OS と権限に依存し、失敗した場合は警告を出してスキップします。
- AI 関連:
  - OPENAI_API_KEY は外部サービス料金が発生するため注意して管理してください。
  - レスポンスのバリデーションやリトライロジックが実装されていますが、LLM の応答は常に完全には保証されません（結果のログ確認を推奨）。
- テスト:
  - config_setup / validate_config を使い起動前に環境を整備・検証してください。
  - news_nlp、regime_detector の OpenAI 呼び出し部分はテスト用にモックしやすい設計になっています。

よく使うコマンド例
-----------------
- .env 作成:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
- Execution 起動:
  - python -m kabusys.run_execution
  - ペーパートレード: KABUSYS_ENV=paper_trading を .env に設定
- Monitoring 起動（デフォルト 60s 間隔）:
  - python -m kabusys.run_monitoring
  - 例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

ライセンス / 貢献
-----------------
この README はコードベースの説明目的に自動生成されています。実際のリポジトリに含まれる LICENSE や CONTRIBUTING を参照してください。

最後に
------
この README はプロジェクトの主要な利用フローと構成を簡潔にまとめたものです。詳細な設計意図（PortfolioConstruction.md、StrategyModel.md 等）や実装の詳細は各ドキュメント・ソースコード内の docstring・コメントを参照してください。必要であれば、各コンポーネント（ExecutionEngine、MonitoringEngine、AI モジュール等）の詳しい運用ガイドを別途作成できます。