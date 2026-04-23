KabuSys — 日本株自動売買ライブラリ / 実行ユーティリティ
=================================================

概要
----
KabuSys は日本株向けの自動売買（バックテスト・ペーパートレード・本番運用）を想定した
Python コードベースです。主な目的は以下です。

- 戦略のリサーチ（ファクター計算、特徴量解析）
- ポートフォリオ構築（候補選定・重み計算・ポジションサイズ決定）
- 実行エンジン（ExecutionEngine）による発注管理（ペーパートレード時は Mock を使用）
- 監視機能（System / Trade / Risk のポーリング、Kill Switch）
- ニュース NLP（OpenAI を用いた銘柄センチメント評価）やレジーム判定
- ペーパートレード検証レポート生成

設計方針（抜粋）
- DuckDB / SQLite をデータ格納に使用（分析用に DuckDB、監視・発注ログは SQLite）
- 環境設定は .env / 環境変数ベース（自動読み込みあり、config_setup で対話式生成）
- 本番とペーパーは DB を分離（KABUSYS_ENV に依存）
- 外部 API（kabuステーション / J-Quants / OpenAI）は設定により切替可能

主な機能一覧
---------------
- 環境設定管理（kabusys.config, config_setup.py）
  - .env 対話ウィザードと自動ロードロジック
- 設定検証 CLI（kabusys.validate_config）
  - 必須環境変数、YAML 設定ファイル、DB パス等を起動前にチェック
- 実行エンジン起動スクリプト（run_execution.py）
  - KABUSYS_ENV=paper_trading のときはペーパー用 DB / MockBroker を使用
  - 起動時にプロセス優先度を "high" に設定
  - 停止は data/stop_requested.flag や data/kill.flag を用いた外部制御
- 監視ポーリング（run_monitoring.py / monitoring package）
  - SystemMonitor / TradeMonitor / RiskMonitor を定期実行して監視ログを保持
  - KillSwitch による ExecutionEngine 停止フローと AlertManager（通知は実装に依存）
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60s）
- ポートフォリオ構築ユーティリティ（kabusys.portfolio）
  - 候補選定、等配分／スコア加重、セクター制限、ポジションサイズ計算
- リサーチ（kabusys.research）
  - Momentum/Value/Volatility ファクター計算、将来リターン、IC 計算、統計サマリ
  - DuckDB を直接参照して処理を行う（外部 API にはアクセスしない）
- AI 関連（kabusys.ai）
  - news_nlp: OpenAI を使ったニュースの銘柄別センチメント付与（ai_scores へ書き込み）
  - regime_detector: ma200 とマクロニュースの LLM 評価を組み合わせた市場レジーム判定
- ツール（kabusys.tools.paper_verification_report）
  - ペーパートレード履歴から検証レポートを生成（稼働率・約定率・レイテンシ等）

セットアップ手順
----------------
1. Python のバージョン
   - Python 3.9+ を想定（各環境に合わせて調整してください）

2. 依存ライブラリ（例）
   - duckdb
   - psutil
   - openai
   - PyYAML（config YAML 検証を行う場合）
   - （必要に応じて他の依存を追加）

   例:
   pip install duckdb psutil openai PyYAML

   ※ requirements.txt がある場合はそれを使用してください。

3. プロジェクトルートの準備
   - リポジトリをクローンし、カレントディレクトリをプロジェクトルートにします。
   - data/ および logs/ ディレクトリは自動で作成されることが多いですが、必要なら手動で作成してください。

4. .env の作成
   - 対話式ウィザードを使う（推奨）:
     python -m kabusys.config_setup
   - 既存 .env を編集する場合は .env.example を参考にしてください。
   - 主要な環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV (development / paper_trading / live)
     - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（ペーパー時の専用 DB）
     - OPENAI_API_KEY（AI モジュールを使う場合）
     - LOG_LEVEL, LOG_DIR など

5. 設定検証（起動前に実行推奨）
   python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱いになります。

使い方（主要コマンド・スクリプト）
---------------------------------
- 環境ウィザード（.env 生成）
  python -m kabusys.config_setup

- 設定検証
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- 監視プロセス起動（監視ループ）
  python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を指定可能（例: MONITOR_POLL_INTERVAL=30）
  - 監視は monitoring DB（Settings.sqlite_path）にログを記録します
  - 監視プロセスが Execution 停止を検知すると data/kill.flag を作成することがあるため、運用時は取り扱いに注意してください

- 実行エンジン起動（発注 / セッション実行）
  python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient としてペーパートレードを実行し、
    data/paper_trading.db（または PAPER_TRADING_SQLITE_PATH）に記録します
  - 起動前に data/stop_requested.flag が存在すると起動をスキップします
  - 実行中は data/execution.pid に PID を書きます

- ペーパートレード検証レポート
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: data/paper_trading.db（--db で上書き可）

- AI スコア算出（ライブラリ関数）
  - ニューススコア付与:
    from kabusys.ai.news_nlp import score_news
    score_news(conn, target_date, api_key=...)
  - レジーム判定:
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date, api_key=...)

  ※ AI モジュールは OpenAI API キー（OPENAI_API_KEY）を必要とします。
  ※ これらは DuckDB 接続を受け取る関数群です。DB スキーマの整備が必要です。

運用メモ / 注意事項
------------------
- KABUSYS_ENV によって挙動が変わります:
  - development: 開発用（発注抑止等）
  - paper_trading: ペーパートレード（発注は Mock）
  - live: 本番（実発注）
- ペーパートレードは本番 DB と分離されます（PAPER_TRADING_SQLITE_PATH を使用）。
- run_monitoring は MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。1 未満や不正値は無視されデフォルト 60 秒が使われます。
- run_execution/run_monitoring ともに process priority を "high" に設定しようと試みます（実行環境によっては権限不足で失敗することがあります）。
- kill.flag / stop_requested.flag:
  - kill.flag: Kill Switch により作成される停止指示ファイル（ExecutionEngine 停止トリガ）。
  - stop_requested.flag: 手動で作成すると run_execution/run_monitoring のループを停止できます。
- ログ:
  - 共通の setup_logging を使用し、stdout と logs/<app_name>.log（日次ローテーション）に出力します。
  - LOG_DIR 環境変数でログ保存先を変更できます。

ディレクトリ構成（抜粋）
---------------------
以下はコードベースの主要ファイル構造（src/kabusys の下）です。実際のリポジトリに若干の差分がある場合があります。

- src/kabusys/
  - __init__.py
  - run_execution.py            # ExecutionEngine 起動スクリプト
  - run_monitoring.py          # Monitoring ポーリング起動スクリプト
  - config.py                  # Settings（環境変数 / .env 自動ロード）
  - config_setup.py            # .env 対話式ウィザード
  - validate_config.py         # 設定検証 CLI
  - tools/
    - __init__.py
    - paper_verification_report.py
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py        # （実装参照）
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py        # （実装参照）
  - utils/
    - __init__.py
    - logging_setup.py
    - process_priority.py
  - data/                     # デフォルトの SQLite / DuckDB ファイル置き場（実運用で作成される）
  - logs/                     # デフォルトのログ出力先（作成される）

ドキュメント / 参考
------------------
- 各モジュールの docstring に詳細な設計意図や使用例があります。まずは config_setup と validate_config を実行し、.env の整備・検証を行ってください。
- AI 機能を使用する場合は OpenAI API キーの管理・コストに注意し、レスポンスのバリデーションログを必ず確認してください。
- 本番運用時は KABUSYS_ENV=live であることを再確認し、LINE 通知等のアラート経路を整備してください。

ライセンス / 著作権
-----------------
- 本 README はコードベースの説明書きです。リポジトリに LICENSE ファイルがあればそちらを参照してください。

問い合わせ / 貢献
-----------------
- バグ報告や改善提案は Issue または Pull Request を通じてお願いします。README の改善点も歓迎します。

以上。README に記載してほしい追加情報（実行例、requirements.txt、より詳細なディレクトリツリーなど）があれば教えてください。必要に応じて追記します。