KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株の自動売買・リサーチ・監視を目的とした Python 製パッケージ群です。
主要な機能は戦略に基づくポートフォリオ構築、注文件数管理・リスク管理、監視（システム／取引／リスク）、
ニュース系 AI スコアリング、ペーパートレード検証レポート生成などです。

本リポジトリはモジュール化されており、
起動スクリプト（ExecutionEngine / SystemMonitor 等）、設定管理、監視周り、ポートフォリオ構築、
リサーチ（DuckDB を用いたファクター計算）や AI（OpenAI を用いたニュースセンチメント）を含みます。

主な特徴（機能一覧）
-------------------
- 起動スクリプト
  - run_execution.py: ExecutionEngine（発注エンジン）起動スクリプト。KABUSYS_ENV=paper_trading のときは MockBroker を使用して paper_trading DB に記録。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL でポーリング間隔を上書き可（デフォルト 60 秒）。
- 設定・検証
  - config_setup.py: .env を対話式に生成・更新するウィザード。
  - validate_config.py: .env と config/*.yaml の基本検証を行う CLI（--strict オプションあり）。
  - config.Settings: 環境変数読み込み・ラッパ（自動 .env ロード、必須チェック等）。
- 監視周り
  - monitoring/monitoring_db.py: SQLite ベースの永続化層（system_status, trade_logs, positions, risk_logs, dashboard）。
  - monitoring/system_monitor.py: CPU/メモリ/Disk/プロセス生存やデータ鮮度のチェック。
  - monitoring/trade_monitor.py, monitoring/risk_monitor.py, monitoring/kill_switch.py, monitoring/monitoring_engine.py: 取引・リスク監視、Kill Switch（flag ファイル）やアラート連携。
  - run_monitoring は監視ループを回して上記を統合。
- 注文・実行関連（execution パッケージ）
  - ブローカークライアントのファクトリ、OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine 等（起動用エンジンが用意）。
- ポートフォリオ構築（portfolio）
  - 候補選定、等重/スコア重み計算、セクター制約・レジーム乗数、ポジションサイズ計算（単元株丸め・aggregation cap）。
- リサーチ（research）
  - ファクター計算（momentum/value/volatility）、forward returns、IC 計算、統計サマリー（DuckDB を使用）。
- AI 機能（ai）
  - news_nlp: raw_news を集約して OpenAI に投げ、銘柄ごとにセンチメント（ai_scores）を書き込む。
  - regime_detector: ma200 とマクロニュース（LLM）を組み合わせて日次の市場レジーム（bull/neutral/bear）を判定して永続化。
- ユーティリティ
  - utils/logging_setup.py: 統一的なログ設定（コンソール + 日次ローテートファイル）。
  - utils/process_priority.py: OS に依存しないプロセス優先度設定 / CPU affinity。

セットアップ手順
----------------
1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo-root>

2. Python 環境（推奨: 仮想環境）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - 必須（実行時に必要なものの一例）:
     - duckdb
     - psutil
     - openai  （AI 機能を使う場合）
     - PyYAML（validate_config の YAML 検証を使う場合）
   - 例:
     - pip install duckdb psutil openai PyYAML

   （requirements.txt があれば pip install -r requirements.txt を使用してください）

4. .env の作成
   - 推奨: 対話式ウィザードを実行して .env を作成
     - python -m kabusys.config_setup
   - 重要: 必須環境変数 JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD を設定してください。
   - KABUSYS_ENV の値: development / paper_trading / live

5. 設定検証
   - python -m kabusys.validate_config
   - 問題があれば修正し、--strict オプションで警告も FAIL 扱いにできます:
     - python -m kabusys.validate_config --strict

6. データディレクトリ作成（必要に応じて）
   - 例: mkdir -p data logs

基本的な使い方
--------------
- 実行エンジン（ExecutionEngine）起動
  - 本番モード（KABUSYS_ENV=live を .env で指定していることが前提）
    - python -m kabusys.run_execution
  - ペーパートレード
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - ペーパートレード時は MockBrokerClient を使用し、デフォルトでは data/paper_trading.db に記録されます（本番 DB と分離）。

- 監視ループ起動（SystemMonitor）
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可（デフォルト 60 秒）。
  - 監視は Settings に基づく sqlite_path（monitoring DB）を使用。Monitoring は常に本番 sqlite_path を用いる設計です。

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  - 環境変数 PAPER_TRADING_SQLITE_PATH でも DB パスを指定可能（デフォルト: data/paper_trading.db）

停止・Kill スイッチ
-------------------
- stop_requested.flag
  - run_execution.py / run_monitoring.py のループはプロジェクトルート/data/stop_requested.flag の存在をチェックしており、ファイルが存在すると安全に終了します。
  - 外部からプロセスを穏やかに停止させたいときはこのファイルを作成してください。

- kill.flag（Kill Switch）
  - 監視（KillSwitch）コンポーネントは条件を満たすと data/kill.flag を書き込んで ExecutionEngine 停止を促します。
  - 本番での誤動作を防ぐため、Settings.kill_flag_clear_on_start の設定により起動時に自動クリアするか制御できます（デフォルトは 0）。

ログ
----
- ログはデフォルトで logs/<app_name>.log に日次ローテーションで出力されます（30日保持）。
- stdout にも出力されます。ログレベルは LOG_LEVEL 環境変数（または .env の設定）で変更できます。

主要な環境変数（概略）
---------------------
- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
  - KABU_API_PASSWORD — kabuステーション API パスワード
- 実行／運用
  - KABUSYS_ENV — execution 環境: development / paper_trading / live
  - LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- DB
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite（デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- AI
  - OPENAI_API_KEY — OpenAI を使う機能（news_nlp / regime_detector）で使用
- 監視・停止
  - MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒）
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（"1" で有効）

ディレクトリ構成（抜粋）
----------------------
リポジトリの主要ファイル・ディレクトリ構成（src/kabusys 配下を中心に）:

- src/kabusys/
  - __init__.py
  - run_execution.py            — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — SystemMonitor 起動スクリプト
  - config.py                  — Settings / .env 自動ロード・必須チェック
  - config_setup.py            — .env ウィザード
  - validate_config.py         — 設定検証 CLI
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py (注: 実装に応じて存在)
  - execution/                  — ExecutionEngine 関連 (broker_factory, order_manager 等)
  - utils/
    - logging_setup.py
    - process_priority.py

実運用上の注意
--------------
- 本番（live）では必須パラメータ・外部サービス設定（LINE 通知設定など）を十分に確認してください。validate_config は本番用チェックも行います。
- データベースのパス設定に注意してください。paper_trading は独立した DB を使う設計になっています（本番 DB と混同しないこと）。
- OpenAI 利用はコストと API レート制限に注意してください。news_nlp / regime_detector はリトライとフェイルセーフを備えていますが、API キー管理は慎重に行ってください。
- ログディレクトリの作成に失敗した場合はコンソール出力のみとなります。logs/ の書き込み権限を確認してください。

開発者向けメモ
----------------
- .env の自動読み込み:
  - プロジェクトルート（.git または pyproject.toml を探索）を起点に .env / .env.local を自動ロードします（OS 環境変数が優先）。テスト等で自動ロードを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- ログ設定:
  - setup_logging(app_name="execution") のように各起動スクリプトから呼び出して統一ログ出力を行います。
- プロセス優先度:
  - 起動時に set_process_priority("high") を呼んでいます。環境によっては権限不足によりスキップされます（警告出力）。

サポート / 追加情報
-------------------
- 各モジュールのドキュメントはソース内の docstring に詳細を記載しています。実装やパラメータの挙動については該当ファイルを参照してください（例: portfolio/position_sizing.py に計算ロジックとパラメータ説明あり）。
- config/*.yaml（system_config.yaml 等）は環境に応じて生成・編集してください（validate_config は存在チェック/パースチェックを行います）。

以上が README の概略です。必要であれば「起動例」「.env の具体的な項目例」「よくあるトラブルシュート」を追加で作成しますか？