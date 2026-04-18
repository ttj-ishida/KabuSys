README
=====

概要
----
KabuSys は日本株自動売買システムのコアライブラリ群です。  
ポートフォリオ構築、ポジションサイズ計算、監視（モニタリング）、ペーパートレード分離、AI を使ったニュースセンチメント評価など、取引エンジン周辺のユーティリティを提供します。

主な設計方針：
- 本番（live） / ペーパートレード（paper_trading） / 開発（development）を環境変数で切替
- SQLite（監視ログ等）と DuckDB（研究・分析用）を併用
- 外部 API 呼び出し（kabuステーション、J-Quants、OpenAI）は明示的に設定して使用
- フェイルセーフ設計（API 失敗はフォールバック、部分失敗でも既存データを保護）

機能一覧
--------
- 環境設定ウィザード（.env 生成 / 更新）
  - python -m kabusys.config_setup
- 設定検証 CLI（.env / config/*.yaml の整合性チェック）
  - python -m kabusys.validate_config
- ExecutionEngine 起動スクリプト
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、data/paper_trading.db を使用して本番 DB と分離
- Monitoring（System / Trade / Risk の監視）起動スクリプト
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き（デフォルト 60 秒）
  - 監視は環境にかかわらず本番 sqlite_path を使用
- Kill Switch（条件に応じて data/kill.flag を作成してエンジン停止）
- Paper Trading 検証レポート生成ツール
  - python -m kabusys.tools.paper_verification_report
- ポートフォリオ構築（候補選定・重み付け）、リスク調整、ポジションサイズ計算（単元株丸め含む）
- 研究用モジュール（DuckDB 経由のファクター計算、IC 計算、統計サマリー）
- AI モジュール（ニュースの NLP スコアリング、レジーム判定） — OpenAI API で LLM を利用

セットアップ手順
----------------

1. リポジトリルートに移動
   - パッケージは src/ 配下にあるため、実行時はプロジェクトルートをカレントにするか PYTHONPATH を調整してください。

2. Python 依存関係をインストール
   - 主要な依存例:
     - duckdb
     - psutil
     - openai
     - PyYAML（設定検証で optional）
   - 例（pip）:
     - pip install duckdb psutil openai PyYAML

3. .env の作成（対話式ウィザード）
   - python -m kabusys.config_setup
   - 生成された .env を絶対に Git にコミットしないでください。

4. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も FAIL 扱い（exit code 1）

5. データディレクトリの準備
   - デフォルトでは data/ 以下を使用します（SQLite、DuckDB、pid/flag ファイルなど）。
   - 必要に応じて .env の DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH を変更してください。

主な環境変数（抜粋）
- KABUSYS_ENV: 実行環境（development | paper_trading | live） デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（paper_trading 環境用）
- LOG_LEVEL: ログレベル（DEBUG, INFO, ...）
- LOG_DIR: ログ出力先ディレクトリ（デフォルト logs/）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール利用時）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: ペーパートレード時の約定挙動 (instant|partial|never|reject)

使い方（主要コマンド）
--------------------

1. .env 作成（対話式）
   - python -m kabusys.config_setup

2. 設定検証
   - python -m kabusys.validate_config
   - 失敗した場合は出力を確認して .env や config/*.yaml を修正

3. 実行エンジン起動（Execution）
   - シンプル実行:
     - python -m kabusys.run_execution
   - ペーパートレードで起動する例:
     - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
     - この場合 broker の実装は MockBrokerClient になり、DB は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を使用

   - 実行時の挙動:
     - 起動時にプロセス優先度を "high" に設定しようとします（set_process_priority）
     - data/stop_requested.flag が存在すると起動せず終了します
     - data/execution.pid に PID を書き込む（Engine の実装に依存）

4. 監視ループ起動（Monitoring）
   - python -m kabusys.run_monitoring
   - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を指定できます（例: MONITOR_POLL_INTERVAL=30）
   - 監視は Settings.sqlite_path を使用（環境にかかわらず本番用 sqlite_path を参照）

5. Paper Trading 検証レポート
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - --db で SQLite ファイルを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

6. AI モジュール（ニュース・レジーム）
   - OpenAI API キーが必要です（OPENAI_API_KEY または関数引数で渡す）
   - kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime などを呼び出して使用

ログ
----
- ログはデフォルトで stdout と logs/<app_name>.log（日次ローテーション）に出力されます。
- LOG_DIR 環境変数でログディレクトリを指定できます。
- ログレベルは LOG_LEVEL 環境変数または setup_logging の引数で制御。

停止・Kill Switch（運用）
-----------------------
- ExecutionEngine を安全に停止するための仕組み:
  - KillSwitch は監視結果に応じて data/kill.flag を書き込みます（Execution が flag を検出して停止する想定）
  - 管理者が直接停止したい場合は data/stop_requested.flag を作成すると run_execution/run_monitoring が検出して終了します
- 設定項目:
  - Settings.kill_flag_path（デフォルト data/kill.flag）
  - Settings.kill_flag_clear_on_start による自動クリア（本番では 0 推奨）

ディレクトリ構成（主要ファイル）
------------------------------
以下は src/kabusys 以下の主要モジュールと簡単な説明です。

- kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み・Settings クラス。.env 自動ロード機能を備える。
  - config_setup.py
    - 対話式 .env ウィザード
  - validate_config.py
    - 起動前の設定検証 CLI
  - run_execution.py
    - ExecutionEngine の起動スクリプト（プロセス優先度設定、DB接続、スレッド実行、停止監視）
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL で間隔指定）
  - utils/
    - logging_setup.py
      - ログ設定ユーティリティ（Stream + TimedRotatingFileHandler）
    - process_priority.py
      - プロセス優先度 / CPU affinity 設定（psutil を利用）
  - monitoring/
    - monitoring_db.py
      - SQLite テーブル作成・永続化 API（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py
      - システム・データ鮮度監視。MonitoringDB へログ追記
    - trade_monitor.py (※ソース省略)
      - 発注・約定に関する監視（滞留注文・約定異常など）
    - risk_monitor.py
      - ドローダウン、ポジション上限監視（dashboard を参照）
    - kill_switch.py
      - kill.flag 書き込みロジック
    - monitoring_engine.py
      - 各モニタを束ねるループ
    - alert_manager.py (※ソース省略)
      - 通知（LINE など）管理
  - execution/
    - execution_engine.py (※エンジン本体)
    - broker_factory.py (ブローカークライアント生成)
    - order_manager.py / order_repository.py / reconciler.py / risk_manager.py
  - portfolio/
    - portfolio_builder.py
      - 候補選定・重み計算 (select_candidates, calc_equal_weights, calc_score_weights)
    - position_sizing.py
      - 株数計算・aggregate cap・単元丸め
    - risk_adjustment.py
      - セクター上限適用・レジーム乗数
  - research/
    - factor_research.py
      - momentum/value/volatility 等のファクター計算（DuckDB ベース）
    - feature_exploration.py
      - forward returns / IC / 統計サマリー等
  - ai/
    - news_nlp.py
      - raw_news を集約して OpenAI に投げ、ai_scores を書き込む
    - regime_detector.py
      - ETF MA とマクロニュースの LLM 評価を合成して market_regime を記録
  - tools/
    - paper_verification_report.py
      - Paper Trading の検証レポートを生成

注意事項 / 運用上のポイント
--------------------------
- .env は絶対にリポジトリにコミットしないでください（機密情報を含みます）。
- validate_config を使って起動前に必須変数の設定を確認してください。
- 本番（KABUSYS_ENV=live）では LINE の通知設定（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）を必ず確認してください。validate_config は live 環境時に追加警告を出します。
- ペーパートレードは本番 DB と分離されます（PAPER_TRADING_SQLITE_PATH）。ペーパーデータが本番 DB を汚染しないよう配慮されています。
- AI モジュール実行時は OpenAI のレートや料金に注意してください。リトライ・バックオフは実装されていますが、API 利用は管理者の責任で行ってください。

ライセンス / バージョン
-----------------------
- パッケージバージョン: __version__ = "0.1.0"（src/kabusys/__init__.py）

付録：よく使うコマンド例
-----------------------
- .env ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Execution 起動（ペーパートレード）
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- Monitoring 起動（ポーリング間隔 30 秒）
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Paper Trading レポート（DB 指定）
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11 --db data/paper_trading.db

以上。運用中に README に追記したい点や、各モジュールの詳細ドキュメント（API 仕様やエンジンの挙動）を追加したい場合は教えてください。