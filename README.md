README
=====

概要
----
KabuSys は日本株の自動売買 / リサーチ / 監視を目的とした小規模なフレームワークです。本リポジトリは以下の主要機能を持ちます。

- 実行エンジン（ExecutionEngine）: 発注・リスク管理・注文管理（本番 / ペーパートレード切替対応）
- 監視（Monitoring）: システム状態、注文挙動、リスク指標を定期的にチェックしてログ・アラート・Kill Switch を管理
- ポートフォリオ構築ロジック: 候補選定、重み付け、ポジションサイズ計算、セクター制約などの純粋関数群
- リサーチ機能: ファクター（モメンタム/バリュー/ボラティリティ）計算、特徴量解析（IC 等）
- AIユーティリティ: ニュースの NLP スコアリング（OpenAI API を利用）・市場レジーム検出
- 運用ツール: .env 設定ウィザード、設定検証、ペーパートレード検証レポート生成

主要な設計方針:
- 環境変数で設定を切替（.env 対応）
- DuckDB / SQLite を使ったローカルデータ処理
- 本番とペーパートレードは DB を分離
- ロジックの多くは副作用のない純関数として設計（テストしやすい）

機能一覧
--------
- 実行系
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV により本番 / ペーパートレード切替）
  - ブローカー抽象化（BrokerClientFactory）により mock / 実ブローカーを差し替え
  - リスク管理 (RiskManager)、注文管理 (OrderManager)、再整合 (Reconciler)

- 監視系
  - run_monitoring.py: SystemMonitor のポーリングループ起動 (MONITOR_POLL_INTERVAL で間隔変更可)
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - MonitoringDB: SQLite に system_status / trade_logs / positions / risk_logs / dashboard を保持
  - KillSwitch: 条件に応じた data/kill.flag の作成で ExecutionEngine を停止

- ポートフォリオ
  - 銘柄候補選定、等配分/スコア加重、リスクベースのポジションサイズ計算
  - セクター上限やレジーム乗数の適用処理

- リサーチ
  - DuckDB を用いたファクター計算（mom/vol/value）
  - 将来リターン、IC（Spearman rank）や統計サマリー

- AI（LLM）
  - ニュース記事を OpenAI に投げて銘柄ごとのセンチメントを計算（kabusys.ai.news_nlp.score_news）
  - マクロ記事 + ETF MA200 乖離を使った市場レジーム判定（kabusys.ai.regime_detector.score_regime）

- ユーティリティ / ツール
  - config_setup.py: 対話式に .env を生成 / 更新
  - validate_config.py: .env と config/*.yaml のチェック（--strict オプション）
  - tools/paper_verification_report.py: ペーパートレード結果の検証レポート生成

セットアップ手順
----------------

1. Python の準備
   - 推奨: Python 3.9+（プロジェクトで明示されていない場合でも DuckDB / psutil / openai に対応した最新近辺を推奨）

2. 必要パッケージをインストール
   - 最低限必要な外部依存:
     - duckdb
     - psutil
     - openai
     - PyYAML（設定検証で config/*.yaml を検査する場合）
   - 例:
     pip install duckdb psutil openai PyYAML

3. 環境変数（.env）設定
   - 対話式ウィザードで .env を作成:
     python -m kabusys.config_setup
   - 重要な必須変数:
     - JQUANTS_REFRESH_TOKEN（J-Quants API）
     - KABU_API_PASSWORD（kabuステーション API）
   - AI 機能を使う場合:
     - OPENAI_API_KEY を環境変数に設定（news_nlp / regime_detector の引数からも渡せます）
   - DB / ログパス（必要に応じて上書き）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視用、デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（ペーパートレード用：data/paper_trading.db）
     - LOG_DIR（ログディレクトリ、デフォルト: logs/）

4. 設定検証（起動前推奨）
   python -m kabusys.validate_config
   - --strict をつけると警告もエラー扱いで exit(1) になります。

5. ディレクトリ・ファイルの初期化
   - ログは自動で logs/ に作成（ログディレクトリが作成できない場合はコンソール出力のみ）
   - data/ 以下に SQLite / PID / フラグファイル等を格納する想定

基本的な使い方
--------------

実行エンジン（Execution）
- 本番 / ペーパートレードの切替:
  - 本番: KABUSYS_ENV=live
  - ペーパー: KABUSYS_ENV=paper_trading
  - 開発: KABUSYS_ENV=development（デフォルト）
- 起動:
  python -m kabusys.run_execution
  - ExecutionEngine は PID ファイル (data/execution.pid) を使います。
  - ペーパートレード時は settings.is_paper により PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を使用し、MockBrokerClient で実行します。
  - 停止:
    - data/stop_requested.flag を作成すると run_execution のループは検知して終了します。
    - KillSwitch が条件を満たすと data/kill.flag が書き込まれ、ExecutionEngine 側で検出して停止します。
  - 注意:
    - Settings.kill_flag_clear_on_start を 1 にすると起動時に kill.flag を自動クリアします（本番では 0 推奨）。

監視プロセス（Monitoring）
- 起動:
  python -m kabusys.run_monitoring
  - デフォルトのポーリング間隔は 60 秒。環境変数 MONITOR_POLL_INTERVAL で秒単位の間隔を指定可能。
  - 監視は常に settings.sqlite_path（本番監視 DB）を使用します（KABUSYS_ENV に依存しない）。
  - run_monitoring は data/stop_requested.flag を検知するとループを終了します。

ペーパートレード検証レポート
- 期間指定で結果を出力:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- DB 指定:
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

AI 機能（ニュース NLP / レジーム判定）
- ニューススコアリング:
  - 使用関数: kabusys.ai.score_news(conn, target_date, api_key=None)
  - api_key が None の場合は環境変数 OPENAI_API_KEY を参照
- レジーム判定:
  - 使用関数: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
- 注意:
  - API キー未設定だと ValueError を送出するケースがあります
  - API 呼び出しはリトライ・フォールバックが実装されていますが、コストに注意してください

ログ / DB / フラグ
- ログ: logs/<app_name>.log（例: logs/execution.log, logs/monitoring.log）
- 監視 DB（SQLite）: data/monitoring.db（Settings.sqlite_path）
  - テーブル: system_status, trade_logs, positions, risk_logs, dashboard
- DuckDB: data/kabusys.duckdb（分析用）
- フラグ / PID:
  - data/stop_requested.flag: run_* スクリプトが外部から停止要求を検出するためのファイル
  - data/kill.flag: KillSwitch によって書き込まれる停止フラグ（ExecutionEngine 側で検出）
  - data/execution.pid: ExecutionEngine の PID ファイル

ディレクトリ構成（抜粋）
----------------------
以下はソース内の主要ファイル / モジュール構成（src/kabusys 以下）です。括弧内は目的の簡単な説明。

- __init__.py (パッケージ定義)
- config.py (Settings クラス: 環境変数/.env 読み込み・検証)
- config_setup.py (対話式 .env ウィザード)
- validate_config.py (起動前チェック CLI)
- run_execution.py (ExecutionEngine 起動スクリプト)
- run_monitoring.py (SystemMonitor ポーリング起動スクリプト)

- ai/
  - news_nlp.py (ニュースを LLM でスコアリングして ai_scores に書込む)
  - regime_detector.py (ETF MA200 + マクロニュースで市場レジームを判定)
  - __init__.py

- monitoring/
  - monitoring_db.py (SQLite のスキーマ初期化・読み書き)
  - system_monitor.py (システム監視・データ鮮度チェック)
  - trade_monitor.py (注文関連の監視)  ←（実装ファイルが他にある想定）
  - risk_monitor.py (ドローダウン・ポジション上限監視）
  - kill_switch.py (Kill Switch 管理)
  - monitoring_engine.py (複数 Monitor の調整)
  - alert_manager.py (アラート送信管理) ←（実装ファイルが他にある想定）

- portfolio/
  - portfolio_builder.py (候補選定・重み計算)
  - position_sizing.py (株数決定・aggregate cap)
  - risk_adjustment.py (セクター制約・レジーム乗数)
  - __init__.py

- research/
  - factor_research.py (mom/vol/value の計算)
  - feature_exploration.py (IC / 将来リターン / 統計サマリー)
  - __init__.py

- tools/
  - paper_verification_report.py (ペーパートレード検証レポート)
  - __init__.py

- utils/
  - logging_setup.py (統一的なログ設定)
  - process_priority.py (プロセス優先度 & CPU affinity のユーティリティ)
  - __init__.py

補足・運用上の注意
-----------------
- 本番環境では KABUSYS_ENV=live に設定し、LINE などの通知設定を確認してください（validate_config の live チェック参照）。
- kill.flag / stop_requested.flag の挙動を理解した上で自動クリア設定（KILL_FLAG_CLEAR_ON_START）を変更してください。誤設定は意図せぬ停止につながります。
- DuckDB・SQLite のファイルはバックアップを取りつつ運用してください。特に本番データは適切に保護してください。
- OpenAI 等の外部 API 利用はコストが発生します。テストは小さなデータセットで行ってください。

よく使うコマンド例
------------------
- .env を作る（対話式ウィザード）
  python -m kabusys.config_setup

- 設定を検証する
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- 監視プロセスを起動する（デフォルト 60s ポーリング）
  python -m kabusys.run_monitoring
  # ポーリング間隔を変更
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- 実行エンジンを起動する
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  KABUSYS_ENV=live python -m kabusys.run_execution

- ペーパートレード検証レポート
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

ライセンス / 貢献
-----------------
（この README にはライセンス情報が含まれていません。プロジェクトに適したライセンスを追加してください。）

問い合わせ
----------
実行時に不明点があれば、該当モジュール（例: monitoring/system_monitor.py、ai/news_nlp.py、config.py）を参照して実装仕様・引数・戻り値を確認してください。README に載せきれない運用ルールや注意点はソースコード内の docstring / コメントに多数記載しています。