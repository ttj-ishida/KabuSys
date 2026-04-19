README
=====

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤です。  
市場環境検知、ファクター計算、ポートフォリオ構築、発注エンジン（ExecutionEngine）、監視（Monitoring）や AI ベースのニュース評価などのコンポーネントを含むモジュール群で構成されています。  
本リポジトリは純粋関数的なポートフォリオ構築・リサーチ関数群と、実行・監視用のランチャースクリプト・ユーティリティを提供します。

主な特徴
--------
- ExecutionEngine（発注エンジン）
  - 本番 / ペーパートレード切り替え（KABUSYS_ENV）
  - BrokerClientFactory 経由でブローカー抽象化（paper_trading 時は MockBrokerClient を使用）
  - リスク管理（RiskManager）、オーダー管理（OrderManager）等の組み合わせ
- Monitoring（監視）
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - Kill Switch（条件満たすと data/kill.flag を書き込み Execution を停止）
  - ログ・メトリクスを SQLite（monitoring.db）へ永続化
- Research / Data
  - DuckDB を用いたファクター計算（momentum / volatility / value）
  - 将来リターン・IC（Information Coefficient）や統計サマリ機能
- AI モジュール
  - news_nlp: OpenAI を使ったニュースセンチメント評価（ai_scores テーブルへ書き込み）
  - regime_detector: ETF とマクロニュースを組み合わせた市場レジーム判定
- ユーティリティ
  - 環境設定ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading の検証レポート出力スクリプト（tools/paper_verification_report）
  - ロギング設定・プロセス優先度設定ユーティリティ

必須依存（概要）
----------------
主な Python パッケージ（環境に応じてインストールしてください）:
- python >= 3.9（ソースは型注釈で互換）
- duckdb
- psutil
- openai
- sqlite3（標準ライブラリ）
- PyYAML（config 検証を行う場合に推奨）

セットアップ手順
----------------
1. リポジトリをクローンし、仮想環境を作成して有効化します。
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストールします（requirements.txt 等がある場合はそちらを利用）。
   - 例:
     - pip install duckdb psutil openai pyyaml

3. .env の作成（推奨: 対話式ウィザード）
   - 実行:
     - python -m kabusys.config_setup
   - ウィザードで J-Quants トークンや kabuAPI パスワード、KABUSYS_ENV（development / paper_trading / live）などを設定します。
   - 手動で作成する場合の主要なキー:
     - JQUANTS_REFRESH_TOKEN=
     - KABU_API_PASSWORD=
     - KABUSYS_ENV=development
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - LOG_LEVEL=INFO
     - OPENAI_API_KEY=...  （AI 機能を使う場合）
   - 自動読み込み: 起動時にプロジェクトルート（.git または pyproject.toml）を検出できれば .env(.local) を自動読み込みします。OS 環境変数が優先されます。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

4. 設定検証
   - python -m kabusys.validate_config
   - --strict オプションで警告も失敗扱いにできます。

5. DB・ディレクトリの準備
   - デフォルトで以下のファイルパスを使用します（必要に応じて .env で変更可）:
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper trading SQLite: data/paper_trading.db
   - ログは logs/ ディレクトリに出力されます（ログは日次ローテーション、30 日保持）。

基本的な使い方
--------------
- ExecutionEngine を起動する（デフォルトは settings に従う）
  - python -m kabusys.run_execution
  - 起動時にプロセス優先度を "high" に設定します。
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して data/paper_trading.db に記録します（本番 DB と分離）。
  - 起動前に data/stop_requested.flag が存在する場合は起動をスキップします。
  - 実行中に停止させたい場合は data/stop_requested.flag を作成するか、監視側で Kill Switch を通じて data/kill.flag を作成します。

- Monitoring を起動する（ポーリングによる監視ループ）
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60 秒）。
  - 監視は常に本番 sqlite_path（SQLITE_PATH）を参照します（環境にかかわらず）。
  - 停止フラグ: プロジェクトルート/data/stop_requested.flag を検知すると監視ループは終了します。

- 設定検証
  - python -m kabusys.validate_config [--strict]

- .env ウィザード
  - python -m kabusys.config_setup

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - DB パスは --db または 環境変数 PAPER_TRADING_SQLITE_PATH で指定できます。デフォルトは data/paper_trading.db。

- AI / Regime / News スコアリング
  - kabusys.ai.score_news（プログラムから呼び出す API）
    - DuckDB 接続と target_date を渡して ai_scores テーブルへ書き込みます。
    - OPENAI_API_KEY が必要です（引数でキーを渡すことも可能）。
  - kabusys.ai.regime_detector.score_regime も同様に使用可能。

重要な環境変数（抜粋）
---------------------
- JQUANTS_REFRESH_TOKEN: J-Quants API（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABUSYS_ENV: execution 動作モード（development / paper_trading / live）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- OPENAI_API_KEY: OpenAI API キー（AI 機能使用時に必要）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: 本番で Kill Flag を自動クリアする設定（0 推奨）

停止 / Kill スイッチ
-------------------
- Kill Switch は条件（ドローダウン超過やポジション上限超過など）に応じて data/kill.flag に理由を書き込みます。ExecutionEngine はこの kill.flag を検知して安全に停止できます。
- 手動で停止したい場合は data/stop_requested.flag を作成してください（run_execution/run_monitoring はこれを監視して終了します）。

ロギング
--------
- ログ設定は kabusys.utils.logging_setup.setup_logging で統一されます。
- 出力先:
  - コンソール (stdout)
  - ファイル logs/<app_name>.log（日次ローテーション、30日分保持）
- LOG_DIR 環境変数でログディレクトリを指定可能。

プロセス優先度 / CPU affinity
----------------------------
- 起動スクリプトは set_process_priority("high") により優先度を高めようとします（psutil を利用）。
- set_cpu_affinity 関数で CPU コア数固定も可能（権限により失敗する場合があります）。

ディレクトリ構成（ソース内の主要ファイル）
----------------------------------------
以下は src/kabusys ディレクトリ配下の主要ファイル一覧（抜粋）。

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / 設定管理（.env 自動読み込みロジック）
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — Monitoring 起動スクリプト

- src/kabusys/execution/
  - execution_engine.py
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - risk_manager.py
  - broker_factory.py

- src/kabusys/monitoring/
  - monitoring_engine.py
  - monitoring_db.py
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - alert_manager.py

- src/kabusys/portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
  - __init__.py

- src/kabusys/research/
  - factor_research.py
  - feature_exploration.py
  - __init__.py

- src/kabusys/ai/
  - news_nlp.py
  - regime_detector.py
  - __init__.py

- src/kabusys/tools/
  - paper_verification_report.py

- src/kabusys/utils/
  - logging_setup.py
  - process_priority.py
  - __init__.py

補足 / 運用上の注意
-------------------
- 本番稼働（KABUSYS_ENV=live）の場合は env 設定（LINE 通知設定等）や Kill Switch の取扱いを慎重に行ってください。validate_config の live 向け追加チェックを参照してください。
- データ鮮度チェックやプロセス死活監視は SystemMonitor が担当します。監視は常に monitoring 用 SQLite（SQLITE_PATH）に記録されます。
- ai モジュールを動かす場合は OpenAI API のレートリミットやコストに注意してください。news_nlp.py / regime_detector.py はリトライとフェイルセーフ（失敗時は 0 相当）を備えていますが、運用時にリトライ設定やバッチサイズを調整してください。
- .env は機密情報を含むため絶対にリポジトリにコミットしないでください（config_setup のヘッダにも記載）。

ライセンス / 貢献
----------------
- （ここにプロジェクトのライセンス情報を書く）

以上。必要であればサンプル .env のテンプレート、起動時のデバッグ手順、各モジュールの詳細ドキュメント（関数説明や API 仕様）を追加で作成します。どの項目を詳しく書いてほしいか教えてください。