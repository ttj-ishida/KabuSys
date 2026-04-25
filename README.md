KabuSys — 日本株自動売買システム
================================

この README はソースツリー（src/kabusys）に含まれる主要スクリプト・モジュールの概要、セットアップ方法、使い方、ディレクトリ構成を日本語でまとめたものです。

概要
----
KabuSys は日本株の自動売買（バックテスト／ペーパートレード／本番運用）を想定したモジュール群です。  
主な機能は以下の通りです。

- ExecutionEngine（発注実行エンジン）: ブローカークライアントを使った注文発行／管理
- Monitoring（監視）: システム状態・発注状況・リスク（ドローダウンなど）を定期監視し、アラート・Kill Switch を生成
- Portfolio construction: 候補選定、重み付け、発注株数計算（等重み・スコア重み・リスクベース）
- Research: ファクター計算（モメンタム・バリュー・ボラティリティ等）と特徴量解析ユーティリティ
- AI 製品群: ニュースを LLM でセンチメント評価し ai_scores に保存、レジーム判定など（OpenAI API）
- ユーティリティ: ロギング設定、プロセス優先度設定、.env ウィザード、設定検証ツール、レポートツール 等

主な機能一覧
-------------
- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動。KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し paper_trading DB に書き込み。
  - run_monitoring.py: SystemMonitor のポーリングループを起動。MONITOR_POLL_INTERVAL 環境変数で間隔指定可（デフォルト 60 秒）。

- 設定関連
  - config_setup.py: 対話式ウィザードで .env を生成 / 更新
  - validate_config.py: .env と config/*.yaml の存在・妥当性を検証（--strict オプションあり）

- モニタリング
  - monitoring/monitoring_db.py: SQLite を使った監視ログ永続化（テーブル作成・マイグレーション含む）
  - monitoring/system_monitor.py / trade_monitor.py / risk_monitor.py / monitoring_engine.py: 個別監視ロジックとエンジン
  - monitoring/kill_switch.py: 条件に応じて data/kill.flag を書いて ExecutionEngine を停止させる

- ポートフォリオ構築（純粋関数）
  - portfolio/portfolio_builder.py: 候補選定・重み計算
  - portfolio/position_sizing.py: 株数決定（単元丸め、リスク制限）
  - portfolio/risk_adjustment.py: セクターキャップ、レジーム乗数

- 研究（Research）
  - research/factor_research.py: モメンタム/バリュー/ボラティリティ等の計算（DuckDB を使用）
  - research/feature_exploration.py: 将来リターン計算、IC 計算、統計サマリ等

- AI（OpenAI）
  - ai/news_nlp.py: raw_news を LLM（gpt-4o-mini 等）に送って銘柄別センチメントを ai_scores に書き込み
  - ai/regime_detector.py: ETF（1321）MA とマクロニュース LLM を合成して market_regime を算出

- ツール
  - tools/paper_verification_report.py: ペーパートレード DB から検証レポートを出力（稼働率・成立率・遅延等）

セットアップ手順
----------------

前提
- Python 3.9+（型注釈の書式や一部ライブラリの依存を考慮）
- SQLite（OS 標準で利用可能）
- DuckDB（Python パッケージをインストールすることで利用可能）

推奨パッケージ（最低限）
- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML（validate_config の YAML 検証を行う場合）

例: 仮想環境作成と依存関係インストール
- venv を作成して有効化
  - python -m venv .venv
  - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
- pip install
  - pip install duckdb psutil openai PyYAML

.env の準備（対話式）
- python -m kabusys.config_setup
  - 対話式で .env を生成します（デフォルトはプロジェクトルート/.env）。
  - 生成後は python -m kabusys.validate_config で検証してください。

必須環境変数（最小セット）
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

その他主な環境変数（デフォルト値）
- KABUSYS_ENV: development | paper_trading | live （default: development）
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- LOG_LEVEL: INFO（"DEBUG","INFO","WARNING","ERROR","CRITICAL"）
- OPENAI_API_KEY: OpenAI API を使う場合に必須

使い方（起動・実行）
--------------------

実行スクリプト（パッケージ経由でモジュールを実行）

- ExecutionEngine（発注エンジン）起動
  - python -m kabusys.run_execution
  - 挙動:
    - 設定により paper_trading モードでは MockBroker を使用し paper_trading DB に書き込む
    - 起動時に data/stop_requested.flag が存在する場合は起動せず終了
    - 実行中に data/stop_requested.flag が作成されるとエンジン停止をトリガー

- Monitoring 起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き（デフォルト: 60）
  - 監視は本番 sqlite_path（Settings.sqlite_path）を使用（環境に関係なく本番 DB を参照）

- .env 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗として exit(1) を返す

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定: --from YYYY-MM-DD --to YYYY-MM-DD
  - DB 指定: --db PATH（省略時は環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db）

停止・Kill Flag
- 監視ループ・ExecutionEngine の停止にはフラグファイルを利用します:
  - 監視の停止: data/stop_requested.flag（run_monitoring/run_execution はこのファイルの存在をチェック）
  - Execution 停止（Kill Switch）: data/kill.flag（KillSwitch が条件を満たしたときに書き込む）
- kill.flag の自動クリアは Settings.kill_flag_clear_on_start による（.env で設定）

ログ
- ログはデフォルトで logs/<app_name>.log に日次ローテーションで出力（30日保管）
- ログレベルは LOG_LEVEL 環境変数または setup_logging の引数で調整可能
- コンソール出力は stdout に出力されます

設定と DB の分離（本番とペーパー）
- KABUSYS_ENV=paper_trading の場合、ExecutionEngine は PAPER_TRADING_SQLITE_PATH（既定 data/paper_trading.db）を使用して本番 DB と完全に分離されます
- monitoring は KABUSYS_ENV に依らず Settings.sqlite_path（既定 data/monitoring.db）を使用します

主要ファイル・ディレクトリ構成
-----------------------------

以下は src/kabusys 配下の主要ファイルと簡単な説明です。

- src/kabusys/
  - __init__.py
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - config.py — Settings クラス（.env / 環境変数読み込み・検証）
  - config_setup.py — 対話式 .env 生成ウィザード
  - validate_config.py — 設定検証 CLI
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート出力
  - portfolio/
    - portfolio_builder.py — 候補選定 / 重み計算
    - position_sizing.py — 発注株数決定（単元丸め・リスク対応）
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — Momentum/Value/Volatility 等の計算（DuckDB）
    - feature_exploration.py — 将来リターン・IC・統計サマリ等
  - ai/
    - news_nlp.py — ニュースを LLM でセンチメント評価し ai_scores に書き込む
    - regime_detector.py — MA + マクロニュースで市場レジーム判定
  - monitoring/
    - monitoring_db.py — SQLite テーブル作成・MonitoringDB ラッパー
    - system_monitor.py — システム状態・データ鮮度の監視
    - trade_monitor.py — 発注ログの監視（滞留注文・異常約定など）
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag 管理
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
    - alert_manager.py — （アラート送信のラッパー。実装を参照）
  - utils/
    - logging_setup.py — ルートロガー設定（Stream + TimedRotatingFile）
    - process_priority.py — プロセス優先度 / CPU affinity 設定
  - data/ (実行時に使用される想定のディレクトリ)
    - monitoring.db (デフォルト SQLITE_PATH)
    - paper_trading.db (ペーパー用 DB)
    - kabusys.duckdb (デフォルト DUCKDB_PATH)
    - stop_requested.flag, kill.flag, execution.pid などのフラグ / pid ファイル

サンプル .env（最小）
--------------------
以下は .env に設定する主なキーの例です（実際には config_setup.py で生成してください）。

JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_api_password
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
LOG_LEVEL=INFO
OPENAI_API_KEY=your_openai_api_key  # AI 機能を使用する場合

運用上の注意
------------
- KABUSYS_ENV=live のときは本番リスクに十分注意してください。validate_config は live 時にいくつかの警告を出します。
- .env は絶対にバージョン管理にコミットしないでください。
- OpenAI やブローカー API のキーは厳格に管理してください。
- monitoring は環境に依らず本番の monitoring DB を参照します。テスト用に分離したい場合はパスを変更してください。
- process_priority や CPU affinity の設定は権限により失敗することがあります（警告をログに出してスキップ）。

FAQ / トラブルシュート
-----------------------
- ログディレクトリが作れない・ファイル出力できない:
  - LOG_DIR 環境変数で書き込み可能なディレクトリを指定するか、ログ用ディレクトリの権限を確認してください。ファイル出力できない場合でもコンソール出力は行われます。
- OpenAI 呼び出しで 429 / タイムアウトが発生する:
  - AI モジュールはリトライと指数バックオフを行います。API レート・キー制限を確認してください。
- monitoring/run_execution がフラグで止まらない／起動しない:
  - data/stop_requested.flag（または kill.flag）の存在を確認し、不要であれば削除してください。KILL_FLAG_CLEAR_ON_START が 1 の場合は起動時に自動クリアされますが、本番では 0 を推奨します。

最後に
------
この README はコード内のドキュメント文字列（docstring）や設計コメントに基づいて作成しています。実行環境や運用ポリシーに合わせて .env やパス、ログ／DB 設定を適切に調整してください。追加の質問や README の補足を希望される場合は、どの部分を詳しく知りたいか教えてください。