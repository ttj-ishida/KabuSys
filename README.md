KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買 / リサーチ / モニタリング基盤を想定した Python パッケージです。
主な機能としてシグナル生成・ポートフォリオ構築・発注実行（実稼働／ペーパートレード切替）、
システム監視・リスク監視・Kill Switch、ニュース NLP によるセンチメント評価、各種研究ユーティリティを含みます。

主な特徴
--------
- 実行環境切替（development / paper_trading / live）に対応
- 実行エンジン（ExecutionEngine）と監視プロセス（Monitoring）を分離
- ペーパートレード時は本番 DB と分離して data/paper_trading.db を使用
- DuckDB を用いたリサーチ / ファクター計算機能
- OpenAI（gpt-4o-mini）を利用したニュースセンチメント評価（AI モジュール）
- モジュール化されたポートフォリオ構築（候補選定・重み計算・ポジションサイジング）
- ログは標準出力 + 日次ローテーション（logs/<app>.log）で管理
- .env 対話式ウィザード・設定検証 CLI を提供

機能一覧
--------
- 環境設定
  - .env ウィザード: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config
- 実行 / 監視
  - 実行エンジン起動: python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading のときは MockBroker を使用し data/paper_trading.db に記録
  - 監視ループ起動: python -m kabusys.run_monitoring
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）
- 監視コンポーネント
  - SystemMonitor: CPU/メモリ/ディスク・プロセス・データ鮮度の監視
  - TradeMonitor: 発注/約定関連の監視（stale order / anomaly fills 等）
  - RiskMonitor: ドローダウン・ポジション上限の監視とアラート／ログ記録
  - KillSwitch: 条件を満たしたら data/kill.flag を作成して ExecutionEngine に停止指示
  - MonitoringDB: SQLite に監視ログ（system_status / trade_logs / risk_logs / dashboard / positions）を永続化
- 研究 / AI
  - research: ファクター計算（momentum / volatility / value）、将来リターン・IC 計算
  - ai.news_nlp: raw_news を OpenAI に送って銘柄別センチメントを ai_scores に保存
  - ai.regime_detector: ETF の MA200 乖離 + マクロニュースの LLM センチメントで市場レジーム判定
- ポートフォリオ
  - 候補選定（select_candidates）、重み付け（等配分 / スコア加重）
  - セクターキャップ適用、レジーム乗数計算
  - ポジションサイズ計算（リスクベース／等分配／スコアベース）
- ツール
  - paper_verification_report: ペーパートレード DB を集計して検証レポートを作成

セットアップ手順
----------------
1. リポジトリをクローン / 展開
   - プロジェクトルートに src/ 以下が存在する想定です。

2. Python 環境を用意
   - 推奨: Python 3.10+
   - 仮想環境を作成して有効化してください。

3. 必要パッケージをインストール
   - requirements.txt がある場合:
     - pip install -r requirements.txt
   - 最低限必要な外部ライブラリ（コード上参照）
     - duckdb, psutil, openai, (PyYAML は設定検証で任意)
   - 注: 実際の requirements はプロジェクトの配布物に従ってください。

4. .env を作成
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - または .env.example を参考に .env を作成
   - 主要な環境変数（必須）
     - JQUANTS_REFRESH_TOKEN — J-Quants API 用
     - KABU_API_PASSWORD — kabuステーション API パスワード
   - 重要な環境変数（任意・説明）
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
     - OPENAI_API_KEY: OpenAI API キー（AI 機能を利用する場合）
     - LOG_LEVEL, LOG_DIR など

5. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱いになります。

基本的な使い方
--------------
- 監視プロセス起動
  - デフォルト（60 秒間隔）:
    - python -m kabusys.run_monitoring
  - ポーリング間隔を指定する:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視は .env の sqlite_path（SQLITE_PATH）を使って monitoring DB を開きます（環境に依らず本番 sqlite_path を使用）。

- 実行エンジン起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading のとき：
    - Broker は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録します。
  - 実行中に停止させるには data/stop_requested.flag を作成（run_execution/run_monitoring は同名の stop flag を監視してグレースフルに終了）。
  - Kill Switch（監視側）がトリガーすると data/kill.flag を作成し、ExecutionEngine に停止シグナルを送ります。
  - 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると自動的に kill.flag をクリアしますが、本番では 0 を推奨します。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パス指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI / レジーム判定（プログラム的利用）
  - news_nlp.score_news(duckdb_conn, target_date, api_key=None)
    - api_key を None にすると環境変数 OPENAI_API_KEY を参照
  - ai.regime_detector.score_regime(duckdb_conn, target_date, api_key=None)

環境変数（まとめ）
-----------------
- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 推奨 / よく使う
  - KABUSYS_ENV (development | paper_trading | live)
  - DUCKDB_PATH (デフォルト data/kabusys.duckdb)
  - SQLITE_PATH (デフォルト data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (デフォルト data/paper_trading.db)
  - OPENAI_API_KEY (AI 機能を使う場合)
  - LOG_LEVEL, LOG_DIR
  - MONITOR_POLL_INTERVAL (run_monitoring 固有、秒単位)
  - KILL_FLAG_CLEAR_ON_START (0/1)
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env の自動読み込みを無効化

ログとファイル
--------------
- ログ:
  - デフォルト logs/<app_name>.log（TimedRotatingFileHandler、日次ローテーション、30 日分保管）
  - コンソールは stdout に出力されます。
- フラグ / PID:
  - data/stop_requested.flag — run_* スクリプトのグレースフル終了用フラグ（外部から停止要求を出す際に使用）
  - data/kill.flag — KillSwitch が発動した際に書き込む（ExecutionEngine 側で読み取り停止）
  - data/execution.pid — ExecutionEngine の pid ファイルとして使用される想定
- データベース:
  - monitoring.db（SQLite）: system_status / trade_logs / risk_logs / dashboard / positions 等
  - paper_trading.db（SQLite）: ペーパートレード時のトレードログ等（完全に本番 DB と分離）
  - DuckDB: 分析用（prices_daily / raw_financials / raw_news 等）

典型的な運用フロー
------------------
1. .env を作成して設定を検証する
2. DuckDB / SQLite ファイルの置き場所を確認
3. 監視プロセスを起動（常駐）
4. ExecutionEngine を起動（手動またはスケジューラ・systemd）
5. 監視が KillSwitch 条件を満たしたら kill.flag を生成 → ExecutionEngine を停止
6. ペーパートレード結果は paper_verification_report で評価

ディレクトリ構成（主なファイル）
-------------------------------
- src/kabusys/
  - __init__.py
  - config.py                  — 環境変数 / Settings 管理（自動 .env ロードなど）
  - config_setup.py            — .env 対話ウィザード
  - validate_config.py         — 設定検証 CLI
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — SystemMonitor ポーリング起動スクリプト
  - monitoring/
    - monitoring_db.py         — SQLite 永続化層（初期化・CRUD）
    - system_monitor.py        — システム状態・データ鮮度監視
    - trade_monitor.py         — 発注/約定監視（存在）
    - risk_monitor.py          — ドローダウン・ポジション上限監視
    - kill_switch.py           — kill.flag 制御
    - monitoring_engine.py     — 各 Monitor を束ねる実行ループ
    - alert_manager.py         — （存在）アラート送信責務
  - execution/
    - order_manager.py         — 注文管理（存在）
    - order_repository.py      — 注文永続化（存在）
    - reconciler.py            — ブローカ状態整合
    - execution_engine.py      — 発注エンジン（存在）
    - broker_factory.py        — BrokerClient の作成（Mock / 実装切替）
    - risk_manager.py          — 実行時のリスク管理
  - portfolio/
    - portfolio_builder.py     — 候補選定 / 重み計算
    - position_sizing.py       — 発注株数決定・上限・丸め
    - risk_adjustment.py       — セクター制限・レジーム乗数
  - research/
    - factor_research.py       — モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py   — 将来リターン / IC / 統計サマリー
  - ai/
    - news_nlp.py              — ニュース NLP（OpenAI 経由）スコアリング
    - regime_detector.py       — レジーム判定（MA200 + マクロ NLP）
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - utils/
    - logging_setup.py         — ロギング統一セットアップ
    - process_priority.py      — プロセス優先度 / CPU affinity 設定

運用上の注意 / トラブルシューティング
------------------------------------
- process priority 設定は OS 権限を要する場合があり、psutil から AccessDenied が発生することがあります（警告が出るだけで処理は継続します）。
- kill.flag / stop_requested.flag の扱いに注意してください。特に本番（KABUSYS_ENV=live）で KILL_FLAG_CLEAR_ON_START=1 を使うと危険です。
- OpenAI API を使用する機能は料金・レート制限の対象です。OPENAI_API_KEY を適切に管理してください。
- DuckDB / SQLite ファイルは同時アクセスでロック競合する場面があります。DB ファイルの配置やバックアップを運用ルールとして定めてください。
- .env は機密情報を含みます。絶対にリポジトリにコミットしないでください。

開発者向けメモ
---------------
- Settings クラスは実行時に環境変数を参照します。テストでは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを無効化できます。
- news_nlp / regime_detector の OpenAI 呼び出し部分はテストで差し替えやすいように実装されています（関数単位で patch 可能）。
- MonitoringDB.init_monitoring_db は冪等でテーブルを作成し、必要に応じてマイグレーション（カラム追加）を行います。

ライセンス
---------
プロジェクト配布物に従ってください（ここでは省略）。

---

この README はコードベースの要点をまとめたものです。プロジェクトの追加ドキュメント（PortfolioConstruction.md、StrategyModel.md 等）がある場合はそちらも参照してください。必要に応じて導入・運用手順書や systemd / コンテナ化のサンプルを追加できます。