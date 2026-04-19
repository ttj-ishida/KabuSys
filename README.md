README
======

概要
----
KabuSys は日本株の自動売買・リサーチ・監視を想定した軽量なフレームワークです。本リポジトリには以下の主要コンポーネントが含まれます。

- 実行エンジン（ExecutionEngine）: 発注・リスク管理・注文再整合などの実行系
- 監視（Monitoring）: システム稼働状況・注文ログ・リスク監視・Kill Switch
- ポートフォリオ構築ユーティリティ: 候補選定・重み付け・ポジションサイズ計算・リスク調整
- リサーチ（Research）: ファクター計算・将来リターン・IC 等の解析機能（DuckDB を利用）
- AI 補助モジュール: ニュースのセンチメント評価や市場レジーム判定（OpenAI）
- ユーティリティ: ロギング設定・プロセス優先度設定・設定ウィザード／検証ツール
- 運用ツール: ペーパートレードの検証レポート生成スクリプト 等

主要設計方針の要点:
- DB（監視／発注）と分析用 DuckDB は分離（paper_trading では専用 SQLite を使用）。
- ルックアヘッドバイアスに配慮（date.today()/datetime.now() の不用意な使用を避ける設計）。
- OpenAI 呼び出しはフェイルセーフ（失敗時はフォールバック）かつリトライを実装。

機能一覧
--------
主な機能（抜粋）:

- Execution
  - ExecutionEngine を起動して発注フローを実行
  - paper_trading モードで MockBroker を使用（本番 DB と分離）
  - リスク管理（RiskManager）、注文管理（OrderManager）等を統合
- Monitoring
  - 定期ポーリングでシステム状態・データ鮮度を記録
  - trade_logs / risk_logs / system_status / dashboard の永続化（SQLite）
  - Kill Switch（ドローダウンやポジション上限超過で停止フラグを生成）
  - アラート送信フック（LINE 等と統合可能）
- Portfolio
  - 候補選定（スコア順）、等金額/スコア加重、リスクベースの株数算出
  - セクターキャップ、レジーム乗数
- Research
  - momentum/volatility/value などのファクター計算（DuckDB）
  - forward returns、IC 計算、統計サマリ
- AI
  - news_nlp: raw_news -> OpenAI -> 銘柄毎センチメントを ai_scores に書き込み
  - regime_detector: ETF ma200 乖離 + マクロニュースで日次レジーム判定
- ツール
  - config_setup: 対話式で .env を作成
  - validate_config: 環境変数・config/*.yaml の検証 CLI
  - paper_verification_report: ペーパートレード DB を集計して検証レポート出力

セットアップ手順
----------------

前提
- Python 3.10 以上（PEP 604 の型記法を使用）
- システムに sqlite3 があれば追加の DB は不要
- 推奨: 仮想環境（venv）を利用

1. リポジトリをクローン（既にローカルにある場合は不要）
   - git clone <repo-url>

2. 仮想環境の作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージのインストール
   - 必須パッケージ例:
     - duckdb
     - psutil
     - openai
     - （任意）PyYAML（config/*.yaml の構文チェックに使用）
   - pip install duckdb psutil openai PyYAML

   注: requirements.txt がない場合は上記を個別にインストールしてください。

4. .env の作成
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - あるいは .env.example をコピーして編集する（リポジトリに example がある場合）。

5. 設定検証
   - python -m kabusys.validate_config
   - 本番前には --strict オプションを推奨（警告もエラー扱い）。

6. ディレクトリの準備（ログ/データ）
   - デフォルトで logs/ や data/ にファイルを作ります。必要に応じてパーミッションを確認。

環境変数（主要）
- JQUANTS_REFRESH_TOKEN: J-Quants API のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABUSYS_ENV: 実行環境（development | paper_trading | live）デフォルト: development
  - paper_trading: MockBroker を使用し data/paper_trading.db を使用
- OPENAI_API_KEY: OpenAI を使う機能（news_nlp, regime_detector）の API キー
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL / LOG_DIR
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒。デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に既存の kill.flag を自動で消すか（"1"でクリア）

使い方
------

起動スクリプト
- ExecutionEngine を起動（通常運用）
  - python -m kabusys.run_execution
  - 特記事項:
    - 起動時にプロセス優先度を高（high）に設定します（psutil を使用）。
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して data/paper_trading.db に記録します。
    - 停止は data/stop_requested.flag を作成するか、kill.flag により外部から停止させることができます。

- Monitoring（ポーリングループ）を起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒で上書き可能（デフォルト 60 秒）。
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path（SQLITE_PATH）を使用します。

設定
- .env を作成する:
  - python -m kabusys.config_setup
- 設定チェック:
  - python -m kabusys.validate_config
  - --strict を付けると警告を FAIL 扱いします。

運用上のフラグ / ファイル
- data/kill.flag: KillSwitch によって書き込まれる停止フラグ（Execution 停止要求）
- data/stop_requested.flag: run_execution / run_monitoring が監視する「自動停止」用フラグ
- data/execution.pid: ExecutionEngine が PID を書き込むファイル（プロセス管理用）

ログ
- デフォルト: logs/<app_name>.log（app_name は "execution" / "monitoring" 等）
- ログはコンソール（stdout）にも出力されます。ログ保存ディレクトリは LOG_DIR で変更可能。

ツール
- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - PAPER_TRADING_SQLITE_PATH 環境変数で DB を指定可能
- AI スコアリング（プログラム的に呼び出す）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - OpenAI API キーは引数または環境変数 OPENAI_API_KEY に設定

開発・デバッグ
- 個々のモジュールは関数単位で呼び出してテスト可能（monitoring_engine.run_once など）。
- PyYAML があれば validate_config が config/*.yaml のパースチェックを行います。

ディレクトリ構成
----------------

src/kabusys/
- __init__.py
  - パッケージ定義。バージョン情報等を含む。
- config.py
  - 環境変数 / .env 自動読み込みと Settings クラス。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動読み込みを無効化可能。
- config_setup.py
  - 対話式 .env 生成ウィザード。
- validate_config.py
  - 起動前チェック CLI（必須環境変数、パス、YAML 等）。
- run_execution.py
  - ExecutionEngine 起動スクリプト（プロセス優先度設定・DB 接続・スレッド実行・停止フラグ監視）。
- run_monitoring.py
  - SystemMonitor ポーリングループ起動スクリプト。
- utils/
  - logging_setup.py: 統一的なログ設定（Stream + TimedRotatingFileHandler）
  - process_priority.py: psutil を使った優先度 / CPU affinity 設定ユーティリティ
- monitoring/
  - monitoring_db.py: SQLite スキーマ初期化・永続化 API（MonitoringDB）
  - system_monitor.py: システム・データ鮮度チェック（psutil, DuckDB）
  - trade_monitor.py: （注文ログ監視）※コードベースにより実装あり
  - risk_monitor.py: ドローダウン・ポジション数監視（RiskMonitor）
  - kill_switch.py: kill.flag の書き込み管理
  - monitoring_engine.py: 各 Monitor を束ねるエンジン
  - alert_manager.py: （アラート送信管理）※実装箇所あり
- execution/
  - broker_factory.py: ブローカークライアント生成（Mock/実ブローカー切替）
  - execution_engine.py: ExecutionEngine の本体（run_session 等）
  - order_manager.py, order_repository.py, reconciler.py, risk_manager.py: 実行系サブコンポーネント
- portfolio/
  - portfolio_builder.py: 候補選定・重み計算
  - position_sizing.py: 株数算出・丸め・aggregate cap
  - risk_adjustment.py: セクターキャップ・レジーム乗数
- research/
  - factor_research.py: momentum/volatility/value の計算（DuckDB）
  - feature_exploration.py: forward returns / IC / 統計サマリ
- ai/
  - news_nlp.py: ニュースを OpenAI でスコアリングして ai_scores に書込む
  - regime_detector.py: ma200 + マクロニュースでレジーム判定
- tools/
  - paper_verification_report.py: ペーパートレード検証レポート生成スクリプト
- portfolio/, research/ 等の __init__.py は外部からの import を整理

注意事項 / 運用上のヒント
-----------------------
- 本番実行前に必ず python -m kabusys.validate_config を実行して設定をチェックしてください。
- KABUSYS_ENV=live のときは特に LINE 通知や KILL_FLAG_CLEAR_ON_START の設定を確認してください（validate_config が警告を出します）。
- OpenAI を利用するモジュールは API コスト・レイテンシ・利用制限に注意してください。API 失敗時は多くの処理がフェイルセーフで継続する設計ですが、重要な判断に使用する場合は運用ルールを明確にしてください。
- データベースファイルやログディレクトリはバックアップ・ローテーションを検討してください（DuckDB / SQLite はファイル単位で管理されます）。

ライセンス / 貢献
-----------------
- この README はコードベースから抽出した情報に基づくドキュメントです。実際のライセンスや貢献ガイドラインはリポジトリの LICENSE / CONTRIBUTING を参照してください。

以上。必要であれば、README にサンプル .env の雛形やより詳細な起動例（systemd ユニット、Dockerfile、CI 設定 など）を追加できます。どの情報が欲しいか教えてください。