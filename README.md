プロジェクト名: KabuSys — 日本株自動売買システム（パッケージ内コードベースの概要 README）

概要
- KabuSys は日本株向けの自動売買／研究／監視を目的とした Python パッケージ群です。
- 主な機能は「戦略研究（ファクター計算）」「ポートフォリオ構築・ポジションサイズ計算」「注文実行エンジン（paper/live 切替）」「監視・Kill Switch」「ニュース NLP を使った AI スコアリング」「運用補助ツール（設定ウィザード・設定検証・レポート生成）」です。
- 設計上、データ処理は DuckDB、監視・発注ログ等は SQLite を使用します。OpenAI を利用した NLP（ニュース解析）機能も含みます（API キー必須）。

主な機能一覧
- 実行エンジン（ExecutionEngine）
  - 本番/ペーパートレード切替（KABUSYS_ENV）
  - BrokerClientFactory により実運用/モックを選択
  - リスク管理（RiskManager）、注文管理（OrderManager）、Reconciler 組み込み
- 監視（Monitoring）
  - SystemMonitor: CPU/メモリ/ディスク、Execution プロセス監視、データ鮮度チェック
  - TradeMonitor / RiskMonitor: 滞留注文、異常約定、ドローダウン・保有数上限の監視
  - KillSwitch: 条件発生時に data/kill.flag を書き込むことで実行エンジンを停止
  - MonitoringEngine / run_monitoring スクリプトでポーリング実行
- ポートフォリオ構築
  - 候補選定、等配分・スコア配分、リスク調整（セクター上限、レジーム乗数）
  - ポジションサイズ計算（単元株丸め、aggregate cap、スケールダウン）
- 研究 / リサーチ
  - ファクター計算（モメンタム・バリュー・ボラティリティ等）
  - 将来リターン計算、IC（情報係数）計算、統計サマリ
- AI（ニュース NLP / レジーム判定）
  - raw_news を集約して OpenAI（gpt-4o-mini）でセンチメント評価し ai_scores に書き込み
  - ETF の MA 乖離 + マクロニュースセンチメントを合成して市場レジーム（bull/neutral/bear）判定
  - リトライ／バックオフ・レスポンスバリデーション等のフェイルセーフあり
- ツール
  - .env 対話ウィザード（config_setup）
  - 起動前設定検証（validate_config）
  - Paper Trading 検証レポート生成ツール（tools.paper_verification_report）

セットアップ手順（ローカル開発想定）
1. リポジトリをクローン
   - git clone ... && cd <repo>

2. Python 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install duckdb psutil openai
   - optional: PyYAML（config/*.yaml の検証を行う場合）: pip install pyyaml
   - （requirements.txt がある場合は pip install -r requirements.txt）

4. .env を作成
   - 対話式ウィザード: python -m kabusys.config_setup
   - もしくは .env.example を参考に手動作成
   - 自動読み込み: config.py は起動時にプロジェクトルートの .env を自動読み込みします（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）

必須環境変数（少なくとも設定すべきもの）
- JQUANTS_REFRESH_TOKEN （必須）
- KABU_API_PASSWORD （必須）
主要な任意／既定値
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 時に execution が利用）
- LOG_LEVEL: INFO（DEBUG などに変更可）
- LOG_DIR: logs/（ログ出力先）
- OPENAI_API_KEY: OpenAI 呼び出しで必要（AI 機能を使う場合）
- PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1, デフォルト 0）

運用上のファイル・フラグ
- data/stop_requested.flag: 手動で置くと run_monitoring / run_execution の起動ループが検知して終了
- data/kill.flag: KillSwitch が書き込むファイル。ExecutionEngine はこれを検知して停止（または起動時にクリア設定が可能）
- data/execution.pid: 実行エンジンの PID ファイル（run_execution が書き込み）
- デフォルト DB/ログパスは .env で上書き可能

基本的な使い方（コマンド）
- 環境設定ウィザード（.env を作成/更新）
  - python -m kabusys.config_setup

- 設定検証（起動前チェック）
  - python -m kabusys.validate_config
  - 厳格モード（警告を FAIL 扱い）: python -m kabusys.validate_config --strict

- 実行エンジン起動
  - 本番/ペーパートレードは KABUSYS_ENV に依存
  - python -m kabusys.run_execution
  - （KABUSYS_ENV=paper_trading を設定すると MockBrokerClient を使い data/paper_trading.db に記録）

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔を環境変数で上書き: MONITOR_POLL_INTERVAL=30（秒）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を明示する場合: --db path/to/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH でも可）

- AI スコアリング（プログラム的呼び出し）
  - kabusys.ai.score_news を import して利用する（duckdb 接続と target_date, OPENAI_API_KEY が必要）
  - kabusys.ai.regime_detector.score_regime でレジーム判定とテーブル書き込み

ログ
- setup_logging が提供され、各起動用スクリプトはこれを利用します。
- 標準出力（stdout）と日次ローテーションのファイルログ（logs/<app_name>.log）を並行出力
- ローテーション保持日数は 30 日（設定可能）

実行環境注意点
- run_monitoring は監視用 DB（monitoring.db）に本番 sqlite_path を使う（KABUSYS_ENV に無関係）
- run_execution は KABUSYS_ENV=paper_trading の場合、paper_sqlite_path を使って本番 DB と分離
- OpenAI を使う機能は API キー（OPENAI_API_KEY）必須。API 呼び出し失敗時はフェイルセーフ（スコア 0.0 を使う等）で継続する設計ですが、想定通りの結果を得るには正常な API 設定が必要

ディレクトリ構成（src/kabusys 配下の主なファイル/ディレクトリ）
- __init__.py
- config.py: 設定読み込み / Settings クラス（.env 自動ロードロジック含む）
- config_setup.py: .env 対話式ウィザード（CLI）
- validate_config.py: 起動前設定検証 CLI
- run_execution.py: ExecutionEngine 起動スクリプト
- run_monitoring.py: SystemMonitor ポーリング起動スクリプト
- tools/
  - paper_verification_report.py: Paper Trading 検証レポート
- ai/
  - news_nlp.py: ニュース NLP（OpenAI）による銘柄スコアリング
  - regime_detector.py: 市場レジーム判定（MA + マクロセンチメント）
- portfolio/
  - portfolio_builder.py: 候補選定・重み算出
  - position_sizing.py: 株数計算・aggregate cap ロジック
  - risk_adjustment.py: セクター上限・レジーム乗数
- research/
  - factor_research.py: ファクター計算（momentum, value, volatility）
  - feature_exploration.py: 将来リターン計算・IC・統計サマリ
- monitoring/
  - monitoring_db.py: SQLite スキーマ初期化・CRUD ユーティリティ
  - system_monitor.py: システム状態・データ鮮度監視
  - trade_monitor.py: （注文滞留・異常検出、実装ファイルあり）
  - risk_monitor.py: ドローダウン・ポジション上限監視
  - kill_switch.py: kill.flag 管理
  - monitoring_engine.py: 複数モニタの集約・ループ実行
  - alert_manager.py: （アラート送信、LINE などの連携コードがある想定）
- execution/
  - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py（発注処理周辺）
- utils/
  - logging_setup.py: ログ設定
  - process_priority.py: プラットフォーム差分を吸収したプロセス優先度／CPU affinity 設定

開発者向けメモ
- .env の自動読み込みは Settings モジュールで実行される（プロジェクトルートの検出は .git または pyproject.toml を参照）
- テストや CI で .env 自動ロードを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください
- DuckDB 接続は research / ai モジュールで利用するため、prices_daily / raw_news / raw_financials 等のテーブルが想定されます（データ投入は別スクリプトや ETL を用意してください）
- logging_setup.setup_logging を各起動スクリプト最初に呼ぶことで統一的なログ設定（stdout + 日次ファイル）を適用できます

トラブルシューティング（よくある確認項目）
- 設定検証でエラーが出る場合: python -m kabusys.validate_config を実行して不足している環境変数やファイル/ディレクトリを確認
- OpenAI 呼び出しエラー: OPENAI_API_KEY の設定、ネットワーク、または API レート制限に注意
- run_execution がすぐ終了する: data/stop_requested.flag や data/kill.flag、あるいは PID ファイルの存在を確認
- ログファイルが作成されない: LOG_DIR の作成権限やディスク容量、logging_setup の warn メッセージを確認

ライセンス・貢献
- 本 README にライセンス情報は含めていません。リポジトリルートの LICENSE を参照してください。
- 貢献は issue / PR を通じて行ってください。大きな設計変更は事前に issue で相談してください。

補足
- この README はコードベース内の docstring と実装コメントを元に作成しています。実行前に python -m kabusys.validate_config で環境を確認してください。