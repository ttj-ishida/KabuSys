# KabuSys

日本株向けの自動売買 / 研究フレームワーク（モジュール群）。  
本リポジトリは発注エンジン、監視、ポートフォリオ構築、ファクター計算、AIベースのニュースセンチメント等のコンポーネントで構成されています。

## 概要
- 発注（ExecutionEngine）と監視（MonitoringEngine）を分離して実装。
- DuckDB を分析用 DB、SQLite を監視・トレードログ用 DB として利用。
- 「paper_trading」モードでは MockBroker を用い、本番 DB と分離された専用 SQLite（data/paper_trading.db）に記録。
- ニュースセンチメントやレジーム判定は OpenAI（gpt-4o-mini 想定）で計算可能（APIキー必要）。
- 設定は .env ファイルまたは環境変数で管理。`.env.local` が優先して読み込まれます（OS 環境変数が最優先）。

## 主な機能一覧
- Execution
  - ExecutionEngine（発注、リスク管理、注文管理、整合処理）
  - BrokerClientFactory（本番/モック切替）
- Monitoring
  - SystemMonitor（プロセス生存・リソース・データ鮮度監視）
  - TradeMonitor（注文滞留・約定異常監視）
  - RiskMonitor（ドローダウン・ポジション上限監視）
  - KillSwitch（条件に応じて ExecutionEngine 停止フラグを書き込む）
  - MonitoringEngine（各 Monitor のポーリング統合）
- Portfolio Construction
  - 銘柄選定、重み付け、ポジションサイズ計算、セクター上限調整、レジーム乗数
- Research
  - ファクター計算（モメンタム／ボラティリティ／バリュー）
  - 将来リターン、IC 計算、統計サマリ
- AI
  - ニュース NLP（raw_news -> ai_scores）
  - レジーム判定（ETF ma200 とマクロニュースの合成）
- CLI / ユーティリティ
  - 設定ウィザード（config_setup）
  - 設定検証（validate_config）
  - Paper Trading 検証レポート（tools.paper_verification_report）
  - ログセットアップ・プロセス優先度設定ユーティリティ 等

## 必要環境 / 依存パッケージ（概略）
- Python 3.10+
- 推奨パッケージ（少なくとも実行に必要なもの）:
  - duckdb
  - psutil
  - openai
  - (オプション) PyYAML（config/*.yaml の検証に使用）
- 実行時に必要な OS 権限: プロセス優先度変更や CPU affinity を行う場合は管理権限が必要になることがあります。

requirements.txt がない場合は適宜インストールしてください:
pip install duckdb psutil openai PyYAML

## セットアップ手順（ローカル開発向け）
1. リポジトリをクローン
   - git clone ... && cd <repo>
2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install duckdb psutil openai PyYAML
4. .env を作成
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - または .env.example を参考に手動作成（.env は絶対に Git にコミットしないでください）
5. 設定検証（任意）
   - python -m kabusys.validate_config
   - --strict を付けると warning も FAIL 扱いになります

## 主要な環境変数（代表）
- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 実行環境選択
  - KABUSYS_ENV: development | paper_trading | live  （デフォルト: development）
- DB / ファイルパス
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (デフォルト: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (paper_trading 用、デフォルト: data/paper_trading.db)
  - PID_FILE_PATH (execution の PID ファイル、デフォルト: data/execution.pid)
  - KILL_FLAG_PATH (デフォルト: data/kill.flag)
- ログ
  - LOG_LEVEL (例: INFO)
  - LOG_DIR (ログ保存先、デフォルト: logs/)
- Paper Trading
  - PAPER_FILL_MODE: instant | partial | never | reject （デフォルト: instant）
- Monitoring
  - MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）
- OpenAI
  - OPENAI_API_KEY（AI モジュール利用時必須）
- その他
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env の自動読み込みを無効化

.env 自動読み込みの挙動:
- OS 環境変数 > .env.local > .env の優先順位で読み込まれます。
- プロジェクトルートは .git または pyproject.toml を基準に自動検出されます。

## 使い方（主要コマンド）
- 設定ウィザード
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- 実行エンジン起動（Execution）
  - python -m kabusys.run_execution
  - KABUSYS_ENV が paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db に記録されます。
  - 起動時に data/stop_requested.flag が存在すると起動せず終了します。
  - 停止: data/stop_requested.flag を作成すると稼働中のエンジンが停止処理を開始します。
- 監視ループ起動（Monitoring）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更できます（例: export MONITOR_POLL_INTERVAL=30）
  - 監視は常に本番用 sqlite_path を使用して監視テーブル（monitoring.db）を操作します（環境に依らず）。
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH（PAPER_TRADING_SQLITE_PATH より優先）
- AI / 研究モジュール（ライブラリとして利用）
  - 例: ニューススコアリングをプログラムから呼ぶ
    - from kabusys.ai import score_news
    - score_news(duckdb_conn, target_date, api_key="...")
  - レジーム判定
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key="...")

## 停止 / キルフラグ
- data/stop_requested.flag
  - run_execution / run_monitoring のループを安全に停止させるために監視スクリプト等が確認します。
  - このファイルが存在すると start 時・ループ内で停止動作を行います。
- data/kill.flag
  - KillSwitch が条件を満たした際に書き込まれるフラグで、ExecutionEngine の停止を誘発します。
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に自動でクリアします（本番では 0 推奨）。

## ログ
- ロギングは kabusys.utils.logging_setup.setup_logging を介して初期化されます。
- デフォルトで console (stdout) と日次ローテートのファイル出力（logs/<app_name>.log、30 日保持）を行います。
- ログレベルは LOG_LEVEL または引数で制御可能。

## データベース（デフォルトパス）
- DuckDB: data/kabusys.duckdb
- SQLite（監視）: data/monitoring.db
- SQLite（ペーパートレード）: data/paper_trading.db

## 開発者向けメモ
- 多くのモジュールは「純粋関数」または DB 接続を渡して動作する形で設計されています。ユニットテストしやすい構成です。
- AI まわりは API 呼び出しをラップしているため、ユニットテスト時は _call_openai_api のパッチやモックが可能です。
- DB マイグレーションは monitoring_db.init_monitoring_db で最小限の互換性対応をしています（カラム追加等）。
- config モジュールは .env を自動ロードしますが、テストや CI では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを無効化できます。

## ディレクトリ構成
（主要ファイルに絞った階層）
- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数・設定管理
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor 起動スクリプト
  - utils/
    - logging_setup.py
    - process_priority.py
  - execution/                — 発注関連（Engine, OrderManager, BrokerFactory 等）
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - tools/
    - paper_verification_report.py
  - data/                     — 実行時に使用するファイル群（DB・flag・pid 等）
- logs/                       — ログファイル（出力先、実行時に作成）

（実際のツリーはリポジトリの内容に従います）

## よくある運用フロー（例）
1. .env を作成（config_setup を利用）
2. python -m kabusys.validate_config で設定を検証
3. start Execution:
   - python -m kabusys.run_execution （paper_trading は専用 DB に記録）
4. start Monitoring (別プロセス / コンテナ):
   - export MONITOR_POLL_INTERVAL=60
   - python -m kabusys.run_monitoring
5. 異常検出時に Monitoring が kill.flag を書き、Execution が停止する等の自動保護が有効になります。

---

README に記載のない詳細な実装や設定ファイル（config/*.yaml、データマスタ等）はリポジトリ内の該当ファイルを参照してください。ご希望があれば、README にサンプル .env や運用手順のテンプレート（systemd / docker-compose 用）を追記します。どの情報を追加しますか？