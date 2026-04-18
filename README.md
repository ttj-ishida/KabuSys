KabuSys
=======

日本株向けの自動売買システム（ライブラリ兼起動スクリプト群）。  
戦略・ポートフォリオ構築、リスク管理、取引実行（本番 / ペーパートレード分離）、監視・アラート、News ベースの AI スコアリングなどの機能を含みます。

主な設計方針
- 実行環境（development / paper_trading / live）に応じた挙動切替
- ペーパートレードは本番 DB と完全分離（data/paper_trading.db）
- DuckDB を分析（研究）用に使用、SQLite を監視・ログ用に使用
- LLM（OpenAI）を利用したニュースセンチメント評価・レジーム判定（オプション）
- CLI で設定ウィザード / 検証 / レポート出力を提供

機能一覧
- ExecutionEngine 起動スクリプト（run_execution.py）
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用して data/paper_trading.db に記録
  - リスク管理（RiskManager）、注文管理（OrderManager）、調整（Reconciler）等を組み合わせて実行
- Monitoring（run_monitoring.py / MonitoringEngine）
  - SystemMonitor / TradeMonitor / RiskMonitor を定期ポーリングして監視ログを記録
  - Kill Switch（データドリブンで ExecutionEngine 停止）とアラート連携
- コンフィグ管理・ウィザード（config_setup.py）
  - .env の対話的生成・更新
- 設定検証 CLI（validate_config.py）
  - 必須環境変数・ファイル・YAML 構文等の事前チェック（--strict オプションあり）
- Paper Trading 検証レポート（tools/paper_verification_report.py）
  - ペーパートレード DB を集計して PASS/FAIL 判定を出力
- 研究・分析モジュール（research）
  - ファクター計算（モメンタム / バリュー / ボラティリティ等）、IC 計算、統計サマリ等
- ポートフォリオ構築（portfolio）
  - 候補選定、重み計算、ポジションサイズ計算、セクターキャップ適用、レジーム乗数
- AI モジュール（ai）
  - news_nlp: OpenAI を使ったニュースセンチメント -> ai_scores テーブル書込
  - regime_detector: ETF MA とマクロニュースで市場レジーム判定
- ユーティリティ
  - ロギング設定ユーティリティ（utils.logging_setup）
  - プロセス優先度 / CPU affinity 設定（utils.process_priority）
  - 監視 DB 永続化層（monitoring.monitoring_db）

必要要件（主な Python パッケージ）
- Python 3.9+
- duckdb
- psutil
- openai (OpenAI API を使う場合)
- PyYAML（config ファイルチェックを行う場合に推奨）

インストール例（仮想環境推奨）
- リポジトリをクローンして仮想環境を作成後、必要パッケージをインストールしてください。
  - 例:
    - python -m venv .venv
    - source .venv/bin/activate
    - pip install --upgrade pip
    - pip install duckdb psutil openai pyyaml

セットアップ手順
1. リポジトリをクローン
   - git clone <repo-url>
2. Python 仮想環境作成・有効化
3. 必要パッケージをインストール
4. .env の作成
   - 対話ウィザードで作成するのが簡単です:
     - python -m kabusys.config_setup
   - 必須環境変数（最低限設定が必要）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 重要: .env は絶対にリポジトリにコミットしないでください。
5. 設定検証
   - python -m kabusys.validate_config
   - 警告も厳密に扱う場合は --strict を付けて実行
6. ディレクトリ作成（多くは実行時に自動作成されますが、必要なら手動で）
   - data/ （データベース・フラグファイル用）
   - logs/ （ログ出力用）

主な環境変数（代表的なもの、デフォルト値を含む）
- KABUSYS_ENV: execution 環境
  - 有効値: development, paper_trading, live
  - デフォルト: development
- JQUANTS_REFRESH_TOKEN: （必須）J-Quants API 用トークン
- KABU_API_PASSWORD: （必須）kabuステーション API パスワード
- KABU_API_BASE_URL: デフォルト http://localhost:18080/kabusapi
- DUCKDB_PATH: data/kabusys.duckdb（分析用 DuckDB）
- SQLITE_PATH: data/monitoring.db（監視用 SQLite）
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（ペーパートレード専用）
- LOG_LEVEL: INFO（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR: logs/
- OPENAI_API_KEY: OpenAI を使う場合の API キー
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）

使い方（代表的なコマンド）
- 設定ウィザード
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- 実行エンジン起動（本番/ペーパーを .env の KABUSYS_ENV で切り替え）
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - KABUSYS_ENV=live python -m kabusys.run_execution
  - 注意: ペーパートレード時は data/paper_trading.db に記録され、本番 DB とは分離されます。
- 監視ループ起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒で上書きできます（例: MONITOR_POLL_INTERVAL=30）
  - 監視は KABUSYS_ENV に関わらず Settings.sqlite_path（本番 sqlite_path）を使います
- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
- AI スコアリング / レジーム評価（ライブラリ関数として利用）
  - kabusys.ai.score_news(conn, target_date, api_key=...)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=...)

停止・フラグ管理
- 実行停止要求（stop）
  - プロジェクトルートの data/stop_requested.flag ファイルを作成すると run_monitoring / run_execution のループが検知して終了または停止処理を行います。
- Kill Switch
  - KillSwitch は data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送ります（監視→リスク判定→kill.flag 書込）。
  - ExecutionEngine 起動時に KILL_FLAG_CLEAR_ON_START=1 にすると自動クリアされますが、本番では 0 を推奨。

ログ
- デフォルト: logs/<app_name>.log（例: logs/execution.log, logs/monitoring.log）
- ログは stdout への StreamHandler と日次ローテーションファイルハンドラ（30日保持）を使用します。
- LOG_DIR 環境変数で変更可能

注意点 / 運用上のヒント
- 本番環境（KABUSYS_ENV=live）に切り替える際は必須環境変数・LINE 通知設定等を十分に確認してください。validate_config は本番用の追加ガードを持ちます。
- ペーパートレードは本番と完全分離されるよう設計されています。デフォルトでも data/paper_trading.db が使用されます。
- Monitoring 系は常に Settings.sqlite_path を参照するため、監視 DB とペーパートレード DB は別ファイルにしておくことを推奨します。
- OpenAI を用いる機能はネットワーク・API レートに依存します。API キーとコスト管理を確認してください。
- DuckDB への書き込み・スキーマはユーティリティやマイグレーションで管理されますが、初回実行時にテーブルが作成されない場合は DB ファイルのパスや権限を確認してください。

ディレクトリ構成（抜粋）
- src/
  - kabusys/
    - __init__.py
    - config.py                 — 環境変数 / 設定管理
    - config_setup.py           — .env 対話ウィザード
    - validate_config.py        — 設定検証 CLI
    - run_execution.py          — ExecutionEngine 起動スクリプト
    - run_monitoring.py         — SystemMonitor ポーリング起動スクリプト
    - utils/
      - logging_setup.py        — ロギング設定ユーティリティ
      - process_priority.py     — プロセス優先度設定ユーティリティ
    - monitoring/
      - monitoring_db.py        — 監視ログ用 SQLite 永続化層
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - monitoring_engine.py
      - alert_manager.py
    - execution/
      - execution_engine.py
      - order_manager.py
      - order_repository.py
      - broker_factory.py
      - reconciler.py
      - risk_manager.py
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
    - data/                      — 実行時生成（データベース / フラグファイル等）
    - logs/                      — 実行時生成（ログファイル）

サンプル .env（抜粋）
- JQUANTS_REFRESH_TOKEN=your_token_here
- KABU_API_PASSWORD=your_password_here
- KABUSYS_ENV=development
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
- LOG_LEVEL=INFO
- OPENAI_API_KEY=（必要に応じて）

追加情報 / 開発者向けメモ
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行われます。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- monitoring_db.init_monitoring_db は冪等でテーブルを作成し、必要なマイグレーション（カラム追加）も実行します。
- AI モジュールはレスポンスバリデーション・リトライ・バックオフや JSON モードの利用などフェイルセーフ設計を行っていますが、API 仕様変更に注意してください。
- テスト時は OpenAI 呼び出し等をモックして実行してください（コード内にモックの想定ポイントがあります）。

---

疑問点や README に追加してほしい内容（例: サンプル設定、運用チェックリスト、systemd ユニットの例など）があれば教えてください。必要に応じて追記します。