README
=====

プロジェクト概要
----------------
KabuSys は日本株の自動売買（アルゴリズム売買）を目的とした小規模なシステム群です。
主な責務は以下のとおりです。

- 発注エンジン（ExecutionEngine）による注文管理・リスク制御
- 監視（Monitoring）によるシステム稼働状況・注文状況のチェックと Kill Switch（緊急停止）
- ポートフォリオ構築 / ポジションサイズ計算（純粋関数）
- 研究用モジュール（ファクター計算・特徴量解析）
- ニュースを用いた NLP（OpenAI）によるセンチメント評価・レジーム判定
- ペーパートレード検証用レポート生成 等

バージョン: 0.1.0（パッケージ定義: src/kabusys/__init__.py）

主な機能一覧
--------------
- 実行エンジン起動スクリプト: run_execution.py
  - KABUSYS_ENV=paper_trading のときは MockBrokerClient を用い、本番 DB と分離して data/paper_trading.db を使用
  - プロセス優先度を高く設定し、別スレッドで ExecutionEngine を動作させる
  - 停止は data/stop_requested.flag を置くことで行う
- 監視ループ起動スクリプト: run_monitoring.py
  - SystemMonitor, TradeMonitor, RiskMonitor をポーリングしてログ・アラート・Kill Switch 評価を行う
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可（デフォルト 60 秒）
  - 監視は本番 sqlite_path を常に使用（環境に依らず）
- 監視 DB 永続化層: monitoring_db.py
  - system_status, trade_logs, positions, risk_logs, dashboard テーブルを含む
  - マイグレーション（カラム追加）に対応
- リスク監視（ドローダウン・ポジション上限）: risk_monitor.py
- Kill Switch 実装: kill_switch.py（data/kill.flag を書き込む）
- ポートフォリオ構築:
  - 候補選定、等重/スコア加重ウェイト、セクター制限、レジーム乗数、ポジションサイズ決定（lot 単位丸め）
- 研究用:
  - ファクター計算（momentum / volatility / value）
  - 将来リターン・IC・統計サマリ等
- AI 機能（OpenAI）:
  - news_nlp: raw_news を LLM で評価し ai_scores に書き込む（OpenAI API キー必須）
  - regime_detector: ETF とマクロニュースを組み合わせ市場レジーム判定
- ユーティリティ:
  - 対話式 .env 作成ウィザード（config_setup.py）
  - 起動前設定検証 CLI（validate_config.py）
  - Paper Trading 検証レポート生成ツール（tools/paper_verification_report.py）
- ログ設定ユーティリティ: utils/logging_setup.py（stdout と日次ローテートファイル出力）

前提 / 必要パッケージ（想定）
----------------------------
※ 実際は requirements.txt を用意してください。最低限の想定依存:

- Python 3.9+
- duckdb
- psutil
- openai
- （オプション）PyYAML（validate_config の YAML 検証に使用）

セットアップ手順
----------------

1. リポジトリをクローンし、仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. パッケージをインストール
   - pip install -r requirements.txt
   - ない場合は少なくとも: pip install duckdb psutil openai

3. 環境変数の準備
   - 対話ウィザードで .env を作成:
     - python -m kabusys.config_setup
   - または手動で .env を作成（プロジェクトルート）し、少なくとも次を設定:
     - JQUANTS_REFRESH_TOKEN=<your_token>
     - KABU_API_PASSWORD=<your_password>
     - KABUSYS_ENV=development|paper_trading|live
     - OPENAI_API_KEY=<required for AI features>
   - 自動 .env ロードを無効にするには:
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1

4. 設定の検証（必須の環境変数等をチェック）
   - python -m kabusys.validate_config
   - 厳密に警告も失敗扱いする: python -m kabusys.validate_config --strict

5. データディレクトリの作成（通常自動作成されますが事前に準備する場合）
   - デフォルト SQLite / DuckDB / PID / フラグのパス:
     - data/kabusys.duckdb（DUCKDB_PATH デフォルト）
     - data/monitoring.db（SQLITE_PATH デフォルト）
     - data/paper_trading.db（PAPER_TRADING_SQLITE_PATH デフォルト）
     - data/execution.pid（PID_FILE_PATH デフォルト）
     - data/kill.flag（KILL_FLAG_PATH デフォルト）
     - data/stop_requested.flag（スクリプト停止用フラグ）
   - ログディレクトリ: logs/（LOG_DIR またはデフォルト）

使い方
-------

共通:
- ロギング: すべての起動スクリプトは kabusys.utils.logging_setup.setup_logging を呼び出します。LOG_LEVEL / LOG_DIR で挙動を調整できます。

設定管理:
- 環境変数の対話式作成:
  - python -m kabusys.config_setup
- 起動前検証:
  - python -m kabusys.validate_config [--strict]

実行エンジン（発注）:
- 通常起動:
  - python -m kabusys.run_execution
- ペーパートレード:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - この場合は MockBrokerClient を使い、別 SQLite (data/paper_trading.db) に記録されます
- 停止:
  - data/stop_requested.flag を作成するとループは停止します
  - Kill Switch（自動停止）: monitoring の判定で data/kill.flag が書かれると ExecutionEngine に通知されます
- PID:
  - 実行時に data/execution.pid を使用（デフォルト）。設定は Settings.pid_file_path

監視（Monitoring）:
- 起動:
  - python -m kabusys.run_monitoring
- ポーリング間隔:
  - MONITOR_POLL_INTERVAL 環境変数（秒）で上書き可（デフォルト 60）
- 停止:
  - data/stop_requested.flag で監視ループを終了
- 監視は常に本番 sqlite_path を使います（環境に依らず）

AI 機能（ニュース NLP / レジーム判定）:
- 環境変数 OPENAI_API_KEY が必要
- news_nlp.score_news / regime_detector.score_regime を使用して ai_scores / market_regime に書き込み
- 大量リクエスト時のリトライや JSON 検証などフェイルセーフ実装あり

ペーパートレード検証レポート:
- レポート生成:
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
- デフォルト DB: data/paper_trading.db
- レポートは稼働率・注文成功率・レイテンシ等を計算して PASS/FAIL 判定を出力

主要な設定項目（主な環境変数）
--------------------------------
- JQUANTS_REFRESH_TOKEN — 必須
- KABU_API_PASSWORD — 必須
- KABUSYS_ENV — development | paper_trading | live（デフォルト development）
- DUCKDB_PATH — デフォルト data/kabusys.duckdb
- SQLITE_PATH — デフォルト data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — デフォルト data/paper_trading.db
- OPENAI_API_KEY — AI 機能で必須
- LOG_LEVEL / LOG_DIR
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒）
- PAPER_FILL_MODE — paper_trading のモック約定挙動（instant/partial/never/reject）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1、本番は 0 推奨）

ディレクトリ構成（主要ファイル）
-------------------------------
プロジェクトルート配下（src/kabusys を主要パッケージとして記載）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数・.env ロードロジック / Settings クラス
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 起動前検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor 起動スクリプト
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層（schema / MonitoringDB）
    - system_monitor.py      — システム状態・データ鮮度チェック
    - trade_monitor.py       — （注文監視ロジック）
    - risk_monitor.py        — ドローダウン / ポジション数監視
    - kill_switch.py         — kill.flag の書込み・評価
    - monitoring_engine.py   — 各 Monitor を束ねる実行ループ
    - alert_manager.py       — （アラート送信の抽象化）
  - execution/
    - execution_engine.py    — ExecutionEngine（注文実行の本体）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py
  - portfolio/
    - portfolio_builder.py   — 候補選定・重み計算
    - position_sizing.py     — 株数・丸め・aggregate cap
    - risk_adjustment.py     — セクター制限・レジーム乗数
  - research/
    - factor_research.py     — momentum/volatility/value 等
    - feature_exploration.py — forward returns / IC / summary
  - ai/
    - news_nlp.py            — ニュース NLP（OpenAI）による ai_scores 書込
    - regime_detector.py     — レジーム判定
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート
  - data/ （実行時に生成されることが多い）
    - monitoring.db (SQLITE_PATH)
    - kabusys.duckdb (DUCKDB_PATH)
    - paper_trading.db (PAPER_TRADING_SQLITE_PATH)
    - execution.pid / kill.flag / stop_requested.flag

注意事項・運用メモ
------------------
- 本番（KABUSYS_ENV=live）での運用は十分な検証が必要です。validate_config の注意メッセージを必ず確認してください。
- kill.flag（KILL_FLAG_PATH）により自動停止が行われるため、起動時の KILL_FLAG_CLEAR_ON_START の設定は慎重に扱ってください（本番では 0 を推奨）。
- run_monitoring は監視用途で sqlite_path（監視 DB）として本番 DB を常に使用します。monitoring の DB は本番データを参照する設計です。
- OpenAI API を使う機能は API のレート制限や課金に注意してください。API キーは .env で管理し、外部に漏洩しないよう注意してください。
- ログ・DB のディレクトリ作成に失敗した場合、ロギングや永続化が限定される可能性があります。権限とディスク容量を確認してください。

トラブルシューティング
----------------------
- 設定が読み込まれない/ .env が効かない:
  - .env はプロジェクトルート（.git や pyproject.toml を探索して決定）から自動ロードされます。自動ロードを無効化している場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を確認してください。
- DB ファイルが見つからない:
  - デフォルトパスは data/*.db です。環境変数で上書きするか、--db オプション（ツール）を指定してください。
- OpenAI 呼び出しで JSON パースエラー等が出る:
  - LLM の応答が想定 JSON と異なる場合、スキップしてログに記録されます。API のレスポンスやモデル設定、トークン制限を確認してください。

ライセンス・貢献
----------------
- （ここにライセンス情報を記載してください）

問い合わせ
----------
- 開発者向けドキュメントや詳細設計は repo 内の Markdown（例: PortfolioConstruction.md, StrategyModel.md）を参照してください（該当ファイルが存在する場合）。

以上。README の補足や追加してほしいセクションがあれば教えてください。