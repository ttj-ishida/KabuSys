KabuSys
=======

日本株向けの自動売買システム（KabuSys）の簡易リポジトリ説明書です。  
この README はソースツリー（src/kabusys 以下）の主要コンポーネント、セットアップ手順、実行方法、ディレクトリ構成を日本語でまとめたものです。

プロジェクト概要
---------------
KabuSys は日本株の自動売買に必要な以下の機能群を持つモジュール群です。

- ExecutionEngine：発注・注文管理・リスク管理を行う実行エンジン
- Monitoring：システム稼働監視・注文ログ監視・リスク監視・Kill Switch
- Portfolio Construction：銘柄選定、重み付け、ポジションサイズ計算
- Research：DuckDB を使ったファクター計算・特徴量探索（モメンタム／バリュー／ボラティリティ等）
- AI ユーティリティ：ニュースを LLM（OpenAI）でスコアリングする news_nlp、レジーム判定
- ユーティリティ：ログ設定、プロセス優先度設定、設定ウィザード／検証、レポート生成ツール

設計上のポイント：
- 設定は .env ファイル（または環境変数）で管理。config_setup により対話式で .env を生成可能。
- paper_trading モードでは発注はモック化され、本番 DB と分離（data/paper_trading.db）。
- ログは stdout と日次ローテートファイル（logs/<app>.log）へ出力。
- Kill Switch は data/kill.flag を書くことで ExecutionEngine 停止をトリガ。

機能一覧
---------
主な機能（抜粋）：

- 実行
  - ExecutionEngine 起動（run_execution.py）
  - paper_trading（モックブローカー・専用 SQLite）対応
  - OrderManager / Reconciler / RiskManager を備えた発注フロー
- 監視
  - SystemMonitor：CPU/メモリ/ディスク・データ鮮度・プロセス生存を定期チェック
  - TradeMonitor：注文滞留・約定異常等の検知（trade_logs）
  - RiskMonitor：ドローダウン・ポジション上限の監視、Dashboard 更新
  - KillSwitch：条件に応じた data/kill.flag の書き込み
  - MonitoringEngine：複数モニタをまとめてポーリング
- ポートフォリオ
  - 銘柄選定（スコア順・上位 N）
  - 重み付け（等金額 / スコア加重）
  - ポジションサイズ計算（単元丸め、リスクベース等）
  - セクターキャップ適用、レジーム乗数
- リサーチ
  - DuckDB を使ったファクター計算（mom/vol/value 等）
  - forward returns / IC 計算 / 基本統計
- AI
  - news_nlp: OpenAI（gpt-4o-mini）によるニュースセンチメント集計・ai_scores 更新
  - regime_detector: ETF の MA とマクロニュースで市場レジーム判定
- ツール
  - config_setup：.env を対話式で作成
  - validate_config：.env と config/*.yaml の事前チェック
  - paper_verification_report：ペーパートレード検証レポート生成

セットアップ手順
----------------

前提
- Python 3.10 以上（ソースで | 型注釈を使用）
- OS: Linux / macOS / Windows（ただし process priority / CPU affinity の具合は OS に依存）
- DuckDB、psutil、openai 等のサードパーティライブラリ

仮想環境の作成（例）
- Unix/macOS:
  python -m venv .venv
  source .venv/bin/activate
- Windows (PowerShell):
  python -m venv .venv
  .\.venv\Scripts\Activate.ps1

必要パッケージのインストール（最小）
- 必要パッケージ例:
  pip install duckdb psutil openai

- 便利パッケージ（任意）
  pip install PyYAML

（注）プロジェクトに requirements.txt がない場合は上記パッケージを手動でインストールしてください。

初期設定 (.env)
1. 対話式ウィザードで .env を作成:
   python -m kabusys.config_setup

2. 設定検証:
   python -m kabusys.validate_config
   --strict オプションを付けると警告もエラーとして扱います。

重要な環境変数（抜粋）
- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 動作モード
  - KABUSYS_ENV: development | paper_trading | live
    - paper_trading 時は MockBrokerClient を使い data/paper_trading.db に記録
    - live は本番（実際の発注）

- DB / ファイルパス
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (監視用: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (ペーパートレード DB: data/paper_trading.db)
  - PID_FILE_PATH (デフォルト: data/execution.pid)
  - KILL_FLAG_PATH (デフォルト: data/kill.flag)

- ログ
  - LOG_LEVEL（例: INFO）
  - LOG_DIR（デフォルト: logs）

- AI
  - OPENAI_API_KEY（news_nlp / regime_detector で必要）

使い方
-------

基本的な実行例（すべて仮想環境内で実行）

1) 設定作成・検証
- 対話式で .env を生成:
  python -m kabusys.config_setup

- 設定検証:
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

2) 監視ループの起動（Monitoring）
- 簡単起動:
  python -m kabusys.run_monitoring

- ポーリング間隔を変更する:
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  （環境変数 MONITOR_POLL_INTERVAL に秒数を指定。1秒以上で整数。デフォルト: 60）

- 停止方法:
  - 監視ループは data/stop_requested.flag の存在を検知して終了します。
  - 監視プロセスを手で止める場合は Ctrl+C。

3) 実行エンジンの起動（Execution）
- 起動:
  python -m kabusys.run_execution

- paper_trading モードで起動（モックブローカー・専用 DB）:
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- 停止 / 起動拒否
  - 起動前に data/stop_requested.flag が存在するとエンジンは起動せず終了します。
  - 実行中に data/stop_requested.flag を作成するとエンジンを停止するよう指示されます。
  - Kill Switch による停止は data/kill.flag を生成してトリガする仕組みです（自動生成は Monitoring 内の KillSwitch が行います）。

4) ペーパートレード検証レポート
- 実行例:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- DB の指定:
  --db PATH を使うか、環境変数 PAPER_TRADING_SQLITE_PATH を設定します。
  デフォルト: data/paper_trading.db

5) AI（ニュース NLP / レジーム判定）
- OpenAI の API キーが必要:
  export OPENAI_API_KEY="sk-..."
- モジュール関数をプログラムから呼ぶ例:
  from kabusys.ai.news_nlp import score_news
  score_news(conn, target_date, api_key=...)
- コマンドライン用スクリプトは同梱されていませんが、score_news / score_regime は DuckDB 接続を受け取り呼び出せます。

運用上のファイル（簡単メモ）
- data/stop_requested.flag — run_monitoring / run_execution が監視する停止フラグ。ファイルを作ると各ループが検知して終了または停止要求を行う。
- data/kill.flag — KillSwitch の書き込み先。ExecutionEngine 停止のためのフラグ（意図的に生成される）。
- data/execution.pid — ExecutionEngine の PID を記録するファイル（Engine 起動時に設定）。

ログ
- デフォルトは logs/ ディレクトリに日次ローテートで出力（例: logs/execution.log, logs/monitoring.log）。
- ログ出力のレベルとディレクトリは環境変数 LOG_LEVEL / LOG_DIR で上書き可能。

ディレクトリ構成
-----------------
主要ファイル・ディレクトリ（src/kabusys 以下）：

- kabusys/
  - __init__.py
  - config.py                    — 環境変数 / 設定読み込み
  - config_setup.py              — .env 対話式ウィザード
  - validate_config.py           — 設定検証 CLI
  - run_monitoring.py            — Monitoring の起動スクリプト
  - run_execution.py             — ExecutionEngine の起動スクリプト
  - utils/
    - logging_setup.py           — ログ設定ユーティリティ
    - process_priority.py        — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py           — SQLite 永続化層（system_status / trade_logs / ...）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
  - execution/                    — 発注関連（Engine, BrokerFactory, OrderManager 等）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py                 — ニュースセンチメント（OpenAI）
    - regime_detector.py          — 市場レジーム判定（OpenAI + MA）
  - tools/
    - paper_verification_report.py
  - data/ (実行時に生成)
    - monitoring.db (SQLite)
    - paper_trading.db (SQLite, paper_trading 用)
    - kabusys.duckdb (DuckDB)
    - kill.flag / stop_requested.flag / execution.pid

注意事項・運用上のヒント
-----------------------
- 本番環境（KABUSYS_ENV=live）では .env の内容・LINE 通知設定などを十分に確認してください（validate_config が警告を出します）。
- OpenAI 連携機能は API コストとレイテンシを考慮して運用してください。API キーは安全に管理してください。
- データベースパス（DUCKDB_PATH / SQLITE_PATH）はデフォルトだと data/ 以下に作られます。バックアップや権限に注意してください。
- process priority / cpu affinity の設定では権限不足で失敗する場合があります（スキップされるだけで致命ではありません）。
- .env は絶対にバージョン管理にコミットしないでください（config_setup のヘッダにも注意書きあり）。

トラブルシューティング
-----------------------
- PyYAML がないと validate_config の YAML 検証がスキップされますが、それ以外は動作します（警告が出ます）。
- DuckDB / sqlite 接続でテーブルがない等の例外は各ツールでハンドリングされていますが、想定されるスキーマが存在するか確認してください（monitoring_db.init_monitoring_db で初期化可能）。
- OpenAI 呼び出しで RateLimit や一時的なネットワークエラーが発生した場合、news_nlp/regime_detector は指数バックオフでリトライしますが、全失敗時はスコアを 0.0 として継続する等フェイルセーフ設計になっています。

ライセンス・貢献
----------------
この README はソースコードの説明を目的とした簡易ドキュメントです。実際のライセンスやコントリビュート手順はリポジトリの LICENSE / CONTRIBUTING ファイルを参照してください（プロジェクトに含まれていれば）。

---

必要であれば、各モジュール（ExecutionEngine の起動フロー、OrderRepository の詳細、AI のプロンプト仕様、DB スキーマ詳細など）について別途詳しいドキュメントを追加できます。どの項目を展開したいか教えてください。