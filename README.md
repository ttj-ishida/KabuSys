# KabuSys

日本株自動売買システム（軽量な実行・監視・リサーチユーティリティ群）

このリポジトリは、取引実行エンジン、監視コンポーネント、ファクター計算／リサーチツール、AI を使ったニュースセンチメント評価などを含む自動売買基盤の一部実装を提供します。シンプルなファイルベースの DB（SQLite / DuckDB）を用い、実運用（live）／ペーパートレード（paper_trading）／開発（development）を切り替え可能です。

主な特徴
- ExecutionEngine：ブローカークライアントを用いた発注・注文管理（paper_trading 時は MockBroker）
- Monitoring：システム状態・注文状況・リスクをポーリングしてログ保存・アラート生成・Kill Switch を実行
- Portfolio construction：候補選定、重み付け、株数算出（等金額・スコア加重・リスクベース）
- Research：DuckDB を用いたファクター計算（Momentum / Volatility / Value 等）と特徴量解析ツール
- AI モジュール：ニュース記事のセンチメント評価（OpenAI）・市場レジーム判定
- CLI ツール：.env 対話的生成（config_setup）、設定検証（validate_config）、ペーパートレード検証レポート生成

最低限の機能一覧
- run_execution.py: ExecutionEngine の起動（KABUSYS_ENV による paper/live 切替）
- run_monitoring.py: SystemMonitor をポーリングして監視ログを記録
- config_setup.py: .env を対話的に生成 / 更新するウィザード
- validate_config.py: .env / config/*.yaml の事前検証ツール
- tools/paper_verification_report.py: ペーパートレード検証レポート生成
- ai/news_nlp.py: raw_news から LLM を呼んで銘柄ごとの ai_score を作成して ai_scores に保存
- ai/regime_detector.py: ETF とマクロニュースを組合せた市場レジーム判定
- monitoring/*: モニタリング関連（system/trade/risk/kill switch/engine）
- portfolio/*: 銘柄選定・配分・リスク調整・ポジションサイズ計算
- research/*: ファクター計算・特徴量探索

前提（推奨環境）
- Python 3.10+
- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML（config 検証で YAML 内容を検査する場合）
- SQLite（標準ライブラリに同梱）
- ネットワーク接続（実際に API を呼ぶ場合）

セットアップ手順（ローカル開発向け）
1. リポジトリをクローン
   - git clone <repo-url>
2. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - （もし requirements.txt がある場合）
     - pip install -r requirements.txt
   - 無ければ最低限：
     - pip install duckdb psutil openai pyyaml
4. ディレクトリ作成（必要に応じて）
   - mkdir -p data logs
   - SQLite / DuckDB のデフォルトパス:
     - data/monitoring.db (監視用 SQLite)
     - data/paper_trading.db (paper_trading 用 SQLite)
     - data/kabusys.duckdb (DuckDB)
5. .env の作成（対話ウィザード推奨）
   - python -m kabusys.config_setup
   - もしくは手動で .env を作成（下記「主な環境変数」を参照）
6. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告でも exit(1) になります

主な環境変数（代表例）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabuステーションのベース URL（デフォルト: http://localhost:18080/kabusapi）
- KABUSYS_ENV: 実行環境（development / paper_trading / live、デフォルト: development）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- OPENAI_API_KEY: OpenAI を利用する場合の API キー
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR）
- LOG_DIR: ログ出力先（デフォルト: logs/）
- KILL_FLAG_CLEAR_ON_START: ExecutionEngine 起動時に kill.flag を自動クリアするか（1 = yes、0 = no）

使い方（主なコマンド）
- 環境設定ウィザード（.env を生成）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- ExecutionEngine 起動
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - KABUSYS_ENV=live python -m kabusys.run_execution
  - 実行中は data/execution.pid に PID を書く / data/stop_requested.flag で停止
  - paper_trading 環境は MockBrokerClient を使い、PAPER_TRADING_SQLITE_PATH に記録（本番 DB と分離）
- Monitoring 起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き（デフォルト 60 秒）
  - 監視は常に本番 sqlite_path を使用（環境にかかわらず）
  - 停止は data/stop_requested.flag を作成
- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション: --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
  - 簡易的な稼働率・注文成功率・レイテンシ指標を出力
- AI スコアリング（ニュース）
  - OpenAI API キーを設定（OPENAI_API_KEY 環境変数）
  - プログラムから呼び出す:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key=None)
  - 注意: API エラー時にはリトライやフォールバックが組み込まれていますが、API キーは必須

監視・Kill Switch の振る舞い（概略）
- Monitoring は SystemMonitor / TradeMonitor / RiskMonitor を順次実行してログを SQLite に保存
- RiskMonitor は drawdown（高値からの下落）・ポジション数上限などを評価し必要なら risk_logs に記録
- KillSwitch は一定条件（例: drawdown が閾値超過 等）に合致すると data/kill.flag を書き込み、ExecutionEngine を停止させる
- ExecutionEngine は起動時に KILL_FLAG_CLEAR_ON_START を見て自動クリアを行うかを判断（本番では 0 推奨）
- 停止フラグ（stop_requested.flag）を作成すると run_execution / run_monitoring のループを安全に抜けます

ログとローテーション
- ロギングは kabusys.utils.logging_setup.setup_logging により統一
- stdout（StreamHandler）と日次ローテートするファイルハンドラ（logs/<app_name>.log）を設定
- LOG_DIR 環境変数で保存先を変更可能。デフォルトは logs/

データベース
- DuckDB: 分析・リサーチ用（data/kabusys.duckdb）
- SQLite:
  - 監視ログ: data/monitoring.db（MonitoringDB。system_status, trade_logs, positions, risk_logs, dashboard テーブル等）
  - ペーパートレード: data/paper_trading.db（paper_trading 用に本番 DB と分離）
- init_monitoring_db() は必要なテーブルと簡単なマイグレーションを行います（冪等）

開発上の注意
- KABUSYS_ENV が live の場合は実際に発注が行われるため十分に設定を確認してください（LINE 通知・kill flag 設定など）
- .env は絶対にリポジトリにコミットしない（config_setup が警告を出します）
- OpenAI を利用する機能は API コストが発生します。API 呼び出しの頻度・バッチサイズに注意してください
- process priority は起動時に高優先度（"high"）に設定しようとします（権限がない場合は警告）

ディレクトリ構成（主要部分）
- src/kabusys/
  - __init__.py
  - config.py               — 環境変数 / .env 自動ロード・Settings
  - config_setup.py         — .env 対話ウィザード
  - validate_config.py      — 起動前検証 CLI
  - run_execution.py        — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py           — ニュース NLP（OpenAI）で ai_scores を作成
    - regime_detector.py    — 市場レジーム判定
  - monitoring/
    - monitoring_db.py      — SQLite 永続化層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py      (アラート送信の実装がある想定)
  - execution/              — Execution 周りのモジュール（broker, order_manager 等）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - data/                   — 実行時に使うファイル（DB, pid, flag 等）を置くことが想定される
  - logs/                   — ログ出力先（デフォルト）

よくある運用コマンド例
- .env を作って検証する
  - python -m kabusys.config_setup
  - python -m kabusys.validate_config
- ペーパートレードでエンジンを起動
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- 監視プロセスを起動（別プロセスで）
  - python -m kabusys.run_monitoring
- ペーパートレードの検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

補足 / トラブルシュート
- SQLite / DuckDB のファイルパスに指定した親ディレクトリがない場合、validate_config は警告を出します。起動時に自動作成されることがありますが、権限等で失敗する場合は手動でディレクトリを作成してください。
- ログディレクトリ作成に失敗した場合はファイルハンドラを無効化しコンソール出力のみになります。ERROR/CRITICAL はまず stdout を確認してください。
- OpenAI 関連の呼び出しはレート制限や一時的な接続障害を考慮してリトライ実装がありますが、API キー・クォータ・課金に注意してください。

ライセンス / 責務
- 本 README はコードのコメントと構造に基づいて作成されています。実運用前に config/*.yaml（存在する場合）や外部依存の設定を必ず確認してください。

この README はコードベースの主要な使い方と構成をまとめたものです。詳細な実装や更なる設定項目は各モジュール内のドキュメント文字列（docstring）および config/*.yaml（存在する場合）を参照してください。