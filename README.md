KabuSys — 日本株自動売買システム
=============================

概要
----
KabuSys は日本株の自動売買 / 研究用ツール群をまとめたパッケージです。  
主な機能は以下のとおりです。

- 発注エンジン（ExecutionEngine） — 実口座 / ペーパートレードを切替可能
- 監視コンポーネント（Monitoring） — システム稼働・注文状態・リスクを定期監視
- ポートフォリオ構築（Portfolio） — 候補選定、重み計算、ポジションサイズ算出
- 研究用モジュール（Research） — ファクター計算・将来リターン・IC 等の解析
- AI モジュール（AI） — ニュースの NLP スコアリング / レジーム判定（OpenAI）
- 運用支援ツール — 設定ウィザード・設定検証・ペーパートレード検証レポート 等

主な機能一覧
--------------
- 環境設定ウィザード: python -m kabusys.config_setup で .env を対話式生成
- 設定検証: python -m kabusys.validate_config（--strict オプションあり）
- 実行エンジン起動: python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を用い、data/paper_trading.db に記録
- 監視ループ起動: python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔上書き（デフォルト 60 秒）
  - 監視は常に production 用 sqlite_path（デフォルト data/monitoring.db）を使用
- AI:
  - ニュース NLP スコア: kabusys.ai.news_nlp.score_news
  - レジーム判定: kabusys.ai.regime_detector.score_regime
  - OpenAI API（OPENAI_API_KEY）が必要
- ペーパートレード検証レポート: python -m kabusys.tools.paper_verification_report
- ロギング: 統一的なセットアップ（kabusys.utils.logging_setup）

前提・依存
-----------
- Python 3.10+
- 必須（利用する機能に応じて）:
  - duckdb
  - psutil
  - openai
- 任意:
  - pyyaml（config/*.yaml の中身検証に使用）
- データディレクトリ（デフォルト）:
  - DuckDB: data/kabusys.duckdb
  - Monitoring DB (SQLite): data/monitoring.db
  - Paper trading DB (SQLite): data/paper_trading.db

セットアップ手順
----------------
1. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb psutil openai
   - 開発・検証用に PyYAML を使う場合: pip install pyyaml

   （プロジェクトに requirements.txt がない場合は上記パッケージを個別にインストールしてください）

3. .env の作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
   - ウィザードは J-Quants、kabu API、DBパス、ログレベル、Kill Switch の設定等を案内します

4. 設定検証
   - python -m kabusys.validate_config
   - 問題があれば表示される ERROR / WARNING を確認して修正してください
   - --strict を付けると WARNING も失敗扱い（exit 1）

主な環境変数（抜粋）
-------------------
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- OPENAI_API_KEY: AI 機能を使う場合は必須
- DUCKDB_PATH（デフォルト data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（ペーパートレード DB、デフォルト data/paper_trading.db）
- PAPER_FILL_MODE（paper_trading 時の約定モード: instant|partial|never|reject）
- LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- MONITOR_POLL_INTERVAL（監視のポーリング間隔秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START（本番での自動クリア防止設定）

使い方（よく使うコマンド）
-------------------------
- .env を作る（対話式）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード: python -m kabusys.validate_config --strict

- 実行エンジン（ExecutionEngine）起動
  - python -m kabusys.run_execution
  - ペーパートレードで起動する例:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - この場合は MockBrokerClient を用い、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録されます
  - 停止:
    - data/stop_requested.flag を作成するとループが検知して停止します
    - 実運用の停止信号としては kill.flag（KILL_FLAG_PATH、デフォルト data/kill.flag）も利用されます

- 監視プロセス起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更する場合:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視は監視用 SQLite（settings.sqlite_path）にログを書きます（監視は常にその sqlite_path を参照）

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH を使うか環境変数 PAPER_TRADING_SQLITE_PATH を設定

- AI 関連（プログラムから呼び出す）
  - ニュース NLP スコア生成:
    - kabusys.ai.news_nlp.score_news(conn, target_date, api_key=...)
  - レジーム判定:
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=...)

停止・Kill Switch
-----------------
- 停止フラグ:
  - data/stop_requested.flag: run_monitoring / run_execution のループを止めるために監視されます
- Kill Switch:
  - data/kill.flag（デフォルト）に理由を文字列で書き込むと、ExecutionEngine に停止シグナルを送る仕様
  - KillSwitch.evaluate により条件（ドローダウンやポジション上限など）で自動生成されます

ログ
----
- ログ設定ユーティリティ: kabusys.utils.logging_setup.setup_logging(app_name="execution" 等)
- デフォルト出力先:
  - コンソール（stdout）
  - 日次ローテートファイル: logs/<app_name>.log（30日分保持）
- ログディレクトリは環境変数 LOG_DIR で上書き可能

主要なディレクトリ構成
---------------------
（プロジェクトルートに src/ を置いた構成を前提）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py  (※実装はコードベース参照)
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - broker_factory.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - data/ (ランタイムで作成されることが多い)
    - monitoring.db (SQLite)
    - paper_trading.db (SQLite)
    - kabusys.duckdb (DuckDB)
    - stop_requested.flag, kill.flag, execution.pid などのフラグ/状態ファイル
- config/
  - system_config.yaml, data_config.yaml, strategy_config.yaml ... （運用用 YAML 設定）

開発メモ / 実装上の注意
-----------------------
- Settings クラスは .env を自動ロードします（プロジェクトルートの判定は .git または pyproject.toml に基づく）
  - 自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
- run_execution は KABUSYS_ENV=paper_trading の場合、発注先を完全に分離してペーパートレード用 DB に記録します
- Monitoring は production（監視）DB を使用する設計で、環境に依存せず同じ sqlite_path を参照します
- AI 機能を利用するには OPENAI_API_KEY が必要です（API 呼び出しはリトライ・フェイルセーフ実装あり）
- DuckDB を使う研究・AI 向け処理は大量データ処理を想定しており、適切な DB ファイルパスとディスク容量を確保してください

ライセンス／バージョン
---------------------
- パッケージバージョン: src/kabusys/__version__ = "0.1.0"
- ライセンス情報はリポジトリのルートにある LICENSE を参照してください（存在する場合）

お問い合わせ / 追加情報
---------------------
- 実装の詳細や運用ルール（例: 単元株数、手数料・スリッページ想定、リスク閾値など）はリポジトリ内の設計ドキュメント（README、PortfolioConstruction.md、StrategyModel.md 等）を参照してください。
- 本 README でカバーしていない運用手順（デプロイ、systemd / supervisor 用設定、バックアップ等）は別途ドキュメント化することを推奨します。