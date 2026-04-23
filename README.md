KabuSys — 日本株自動売買システム (README)
=================================================

概要
----
KabuSys は日本株の自動売買を想定したモジュール群です。  
本リポジトリは以下の主要機能を持ち、実行エンジン（ExecutionEngine）と監視（Monitoring）を分離して運用できる設計になっています。

主な特徴
- 実行エンジン（run_execution） — 発注・注文管理・リスク管理を行う（本番 / ペーパートレード対応）
- 監視（run_monitoring / MonitoringEngine） — システム状態、注文・リスク異常を定期チェックしアラート/Kill Switch を操作
- ポートフォリオ構築（portfolio/*） — 候補選定、重み計算、ポジションサイズ決定、セクター制限
- リサーチ（research/*） — ファクター計算・特徴量探索（DuckDB を用いた分析）
- AI モジュール（ai/*） — ニュースの NLP スコアリング、レジーム判定（OpenAI API を利用）
- ツール（tools/*） — ペーパートレード検証レポート生成など
- 設定管理（config_setup, validate_config, config） — .env ウィザード、設定検証、環境変数読み込み

機能一覧
- run_execution: ExecutionEngine を開始（KABUSYS_ENV により paper_trading モードあり）
- run_monitoring: SystemMonitor をポーリングで起動（MONITOR_POLL_INTERVAL で間隔調整）
- config_setup: .env の対話式生成/更新ウィザード
- validate_config: .env と config/*.yaml の事前検証 CLI
- tools.paper_verification_report: ペーパートレード結果の集計・判定レポート生成
- portfolio: 銘柄選定・重み付け・ポジション計算（純粋関数）
- research: DuckDB を用いたファクター計算、IC 計算、統計サマリー
- ai.news_nlp / ai.regime_detector: OpenAI を使ったニュースセンチメント / 市場レジーム判定
- monitoring: SQLite ベースの永続化層、各種モニタ（System/Trade/Risk）、KillSwitch、アラート連携
- utils: ロギング設定、プロセス優先度 / CPU affinity 管理

前提条件（主要依存）
- Python 3.10+
- パッケージ（例）
  - duckdb
  - psutil
  - openai
  - PyYAML（config の詳細検証を行う場合に必要）
- ローカル環境に書き込み可能な data/ および logs/ ディレクトリ

セットアップ手順
1. リポジトリをクローンして作業ディレクトリへ
   python パッケージとして使う前提で src/ がパッケージルートです。

2. 仮想環境の作成（推奨）
   python -m venv .venv
   source .venv/bin/activate  # (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   pip install duckdb psutil openai PyYAML

4. .env の初期作成（ウィザード）
   python -m kabusys.config_setup
   - ウィザードは J-Quants / kabuAPI のトークン、データベースパス、KABUSYS_ENV 等を対話式で設定します。
   - 生成された .env は絶対に Git にコミットしないでください。

5. 設定検証（任意）
   python -m kabusys.validate_config
   - --strict を付けると警告も失敗 (exit 1) 扱いになります。

環境変数（主要なもの）
- KABUSYS_ENV: 実行環境（development / paper_trading / live）。デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API 用パスワード（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...、デフォルト INFO）
- LOG_DIR: ログ保存ディレクトリ（デフォルト logs/）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring で使用。デフォルト 60）
- OPENAI_API_KEY: OpenAI API キー（ai.* 機能を使う場合に必須）
- PID_FILE_PATH / KILL_FLAG_* などのパスは Settings で指定可能（デフォルトは data/ 下）

使い方（代表的コマンド）
- .env を生成
  python -m kabusys.config_setup

- 設定チェック
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- 実行エンジンを起動（本番 / ペーパーは KABUSYS_ENV に依存）
  KABUSYS_ENV=development python -m kabusys.run_execution
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution

  挙動:
  - paper_trading のときは MockBrokerClient を使い、PAPER_TRADING_SQLITE_PATH (data/paper_trading.db がデフォルト) に記録します。
  - 起動時に data/stop_requested.flag（stop フラグ）が存在する場合、起動せず終了。
  - 実行中は data/execution.pid に PID を書きます。停止は stop flag 書き込みで指示できます（Monitoring から KillSwitch により書かれることがある）。

- 監視プロセスを起動
  python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能（デフォルト 60 秒）。
  - 監視は monitoring.db（Settings.sqlite_path）を使用し、環境（KABUSYS_ENV）に依存せず本番用 sqlite_path を参照します。
  - 停止はプロジェクトルート/data/stop_requested.flag を作成することで次回ループで停止します。

- Paper Trading 検証レポート
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で SQLite ファイルを直接指定可能。指定がなければ PAPER_TRADING_SQLITE_PATH 環境変数、さらにデフォルト data/paper_trading.db。

AI 関連
- ai.news_nlp.score_news, ai.regime_detector.score_regime などは OpenAI API を利用します。OPENAI_API_KEY を設定してください。
- レート制限・接続エラー等に対してはリトライ実装・フォールバックが用意されています（失敗時は安全に継続する設計）。

停止と Kill Switch
- kill.flag を書くことで ExecutionEngine に停止命令を伝えます（KillSwitch が自動的に書き込むケースあり）。設定により起動時に Kill flag をクリアすることができます（KILL_FLAG_CLEAR_ON_START=1 がその設定。注意して使ってください）。
- プロセス強制終了以外に、プロセス同士でファイルベースのシグナルを使う設計です：
  - data/kill.flag: ExecutionEngine を停止させるためのフラグ
  - data/stop_requested.flag: run_monitoring / run_execution のループを優雅に止めるためのフラグ

ロギング
- kabusys.utils.logging_setup.setup_logging を通じて統一的に設定されます。
- デフォルトでは stdout に出力し、日次ローテーションで logs/<app_name>.log に出力（30 日分保持）。
- LOG_DIR 環境変数で変更可能。

開発・テスト上の注意
- .env の自動ロードは config モジュールで行われます（プロジェクトルートを .git または pyproject.toml から検出）。テスト等で無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- config_setup により生成した .env は secrets を含むため絶対にリポジトリにコミットしないでください。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py  (バージョン定義)
  - config.py  (環境変数 / Settings)
  - config_setup.py  (.env ウィザード)
  - validate_config.py  (設定検証 CLI)
  - run_execution.py  (ExecutionEngine 起動スクリプト)
  - run_monitoring.py  (SystemMonitor 起動スクリプト)
  - tools/
    - paper_verification_report.py
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
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py  (存在する想定)
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py  (存在する想定)
  - execution/  (発注・エンジン関連コード: ExecutionEngine, BrokerFactory, OrderManager, Reconciler, RiskManager 等)
  - utils/
    - logging_setup.py
    - process_priority.py

補足 / 推奨運用
- 本番運用時は KABUSYS_ENV=live とし、LINE 通知トークン等を設定してください。validate_config は live 環境で追加の警告を出します。
- 本番 DB とペーパートレード DB は完全に分離するため、必ず PAPER_TRADING_SQLITE_PATH を適切に設定してください（paper_trading モード時）。
- ログは定期的にローテーションされますが、ログディレクトリのディスク容量監視も行ってください。

ライセンス / バージョン
- パッケージバージョン: 0.1.0（src/kabusys/__init__.py）

問い合わせ・拡張
- 新しいブローカー実装、モニタ追加、アラート送信先（Slack / LINE 等）追加は既存のファクトリ・AlertManager インターフェースに沿って実装してください。
- DuckDB を使ったリサーチモジュールはデータスキーマ（prices_daily / raw_financials / raw_news 等）に依存します。データ投入パイプラインは kabusys.data.pipeline 側に実装されています（本 README では省略）。

以上が本リポジトリの簡易 README です。必要であれば「導入例」「データスキーマ」「API 使用例（OpenAI プロンプト例）」など、さらに詳細なドキュメントを追加します。どのトピックを優先して展開しますか？