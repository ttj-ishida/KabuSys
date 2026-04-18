README
======

概要
----
KabuSys は日本株の自動売買・リサーチ・監視を目的とした Python パッケージです。本リポジトリは以下の主要機能を含みます:

- 執行エンジン（ExecutionEngine）と監視プロセス（Monitoring）
- ペーパートレード用の分離された DB サポート
- ファクター計算・リサーチ（DuckDB 利用）
- ニュース NLP / レジーム判定（OpenAI を利用）
- ポートフォリオ構築（候補選定、重み付け、株数決定、セクター/レジーム調整）
- 監視用 DB 層（SQLite）と各種モニタ（システム / 注文 / リスク）
- 設定ウィザード・検証ツール、レポート生成ツール

主な特徴
--------
- 環境変数ベースの設定（.env をサポート）。config_setup による対話式生成。
- KABUSYS_ENV による実行モード切替（development / paper_trading / live）。
- Paper Trading モードでは Mock Broker を利用し、本番 DB と分離（data/paper_trading.db）。
- 監視 (monitoring) は環境に依らず本番用の sqlite_path を使用（監視データの一元化）。
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント・レジーム判定機能（API キー必須）。
- ログはコンソール出力と日次ローテートファイルに出力（logs/<app_name>.log、デフォルト: logs/）。
- Kill Switch によるフラグファイルでの安全停止制御（data/kill.flag）。

セットアップ手順
--------------
1. Python 環境を作る（推奨: 3.10+）
   - 仮想環境を作成・有効化:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存ライブラリをインストール
   - requirements.txt はリポジトリにないため、主な依存は次のとおり:
     - duckdb, psutil, openai, (PyYAML があれば config 検証で YAML チェックを行う)
   - 例:
     - pip install duckdb psutil openai

3. .env の準備（対話式ウィザード推奨）
   - python -m kabusys.config_setup
   - これにより .env を生成・更新できます。重要な環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV（development | paper_trading | live、デフォルト: development）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
     - LOG_LEVEL（DEBUG/INFO/...）
     - OPENAI_API_KEY（AI 機能を使用する場合必須、環境変数名は OPENAI_API_KEY）

4. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります。

使い方
------
実行スクリプトはパッケージモジュールとして起動できます（各スクリプトは if __name__ == "__main__" を持ちます）。

- 監視ループを起動（SystemMonitor のポーリング）
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト: 60）
  - 実行:
    - python -m kabusys.run_monitoring

  - 停止方法:
    - data/stop_requested.flag ファイルを作成すると監視ループは検知して終了します
    - または Ctrl+C（KeyboardInterrupt）

- 執行エンジン起動（ExecutionEngine）
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い data/paper_trading.db に記録されます
  - 実行:
    - python -m kabusys.run_execution

  - 停止方法:
    - data/stop_requested.flag を作成すると起動中のエンジンを停止します
    - KillSwitch（監視側）による data/kill.flag の作成でエンジンに対して停止信号を送れます

- 設定ウィザード・検証
  - python -m kabusys.config_setup
  - python -m kabusys.validate_config [--strict]

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

- AI 関連（ニュース NLP / レジーム判定）
  - OPENAI_API_KEY を設定して使用します
  - ニューススコアリング: kabusys.ai.score_news（スクリプトエントリは本 README に含まれませんが、モジュール経由で利用可能）
  - レジーム判定: kabusys.ai.regime_detector.score_regime

重要な環境変数（抜粋）
--------------------
- KABUSYS_ENV: 実行環境（development | paper_trading | live）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（monitoring.db）（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 DB（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル
- LOG_DIR: ログ出力先ディレクトリ（デフォルト: logs）
- OPENAI_API_KEY: OpenAI API キー（ニュース NLP / レジーム判定に必要）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト: 60）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動クリアするか（0/1）

停止・フラグの運用
-----------------
- 「停止要求」: data/stop_requested.flag を作成すると run_execution/run_monitoring はそれを検知して終了します（これにより安全にプロセスを停止できます）。
- 「Kill Switch」: KillSwitch は監視で閾値超過等を検出した場合に data/kill.flag を書き込みます。ExecutionEngine は起動時に kill.flag の有無を確認します（KILL_FLAG_CLEAR_ON_START=1 を設定しない限り自動クリアはされません）。
- PID ファイル: デフォルトで data/execution.pid を使用します。プロセス優先度変更や PID 管理に利用されます。

ディレクトリ構成（主なファイル）
--------------------------------
src/kabusys/
- __init__.py
- config.py
  - 環境変数読み込み・Settings クラス
- config_setup.py
  - 対話式 .env 生成ウィザード
- validate_config.py
  - 起動前チェック CLI
- run_execution.py
  - ExecutionEngine 起動スクリプト
- run_monitoring.py
  - SystemMonitor ポーリングループ起動スクリプト

src/kabusys/ai/
- news_nlp.py
  - ニュースを OpenAI でスコアリングし ai_scores に書き込む処理
- regime_detector.py
  - ETF とニュースから市場レジームを判定し market_regime に保存

src/kabusys/monitoring/
- monitoring_db.py
  - SQLite スキーマ初期化・永続化 API（system_status, trade_logs, positions, risk_logs, dashboard）
- system_monitor.py
  - CPU/メモリ/ディスク、データ鮮度、プロセス監視
- trade_monitor.py
  - (注文/約定モニタ, ファイル内に詳細)
- risk_monitor.py
  - ドローダウン・ポジション上限監視
- kill_switch.py
  - kill.flag の管理
- monitoring_engine.py
  - 複数モニタの統合とアラート通知

src/kabusys/execution/
- BrokerClientFactory, ExecutionEngine, OrderManager, OrderRepository, Reconciler, RiskManager など（エンジンと注文処理）

src/kabusys/portfolio/
- portfolio_builder.py, position_sizing.py, risk_adjustment.py（銘柄選定とサイズ決定の純粋関数群）

src/kabusys/research/
- factor_research.py, feature_exploration.py（DuckDB を使ったファクター計算・IC 解析等）

src/kabusys/tools/
- paper_verification_report.py（ペーパートレード検証レポート生成）

src/kabusys/utils/
- logging_setup.py（統一ログ設定）
- process_priority.py（プロセス優先度 / CPU affinity のユーティリティ）

注意事項 / 運用上のポイント
--------------------------
- 監視用 DB（SQLITE_PATH）は監視コンポーネントで必ず使われるため、環境に依らず正しい本番 DB パスを設定してください。
- Paper Trading は本番 DB と分離されます（PAPER_TRADING_SQLITE_PATH を使用）。
- OpenAI API を利用する機能は API キーが必須です。API 呼び出しの失敗は基本的にフェイルセーフ（スコア 0 やスキップ）で処理されますが、運用時は API リクエスト数とエラー監視に注意してください。
- ログディレクトリ作成に失敗した場合はコンソール出力のみで継続します（エラーにはなりません）。
- run_execution / run_monitoring は内部でプロセス優先度を "high" に設定しようとしますが、権限や OS により失敗する場合があります（警告ログのみ）。

サンプルコマンド一覧
-------------------
- .env 対話式作成:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 監視起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- 執行エンジン起動:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - python -m kabusys.tools.paper_verification_report --db ./data/paper_trading.db

開発 / 貢献
-----------
- コードは機能単位でモジュール分割されています。ユニットテストを追加する際は各純粋関数（portfolio/*、research/*）から始めると良いです。
- OpenAI 呼び出し部はテスト容易性のために呼び出し関数を切り出しており、単体テストではモック置換が可能です（例: unittest.mock.patch）。

以上がプロジェクトの概要・セットアップ・運用方法の要点です。README に記載のない追加の運用ルールや自動デプロイ手順がある場合は、別途運用ドキュメントを整備してください。