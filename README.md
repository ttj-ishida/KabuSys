KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買システムのコードベースです。売買ロジック（シグナル生成・ポートフォリオ構築・サイズ決定）や取引実行、監視、リスク管理、リサーチ用のファクター計算、ニュースの自然言語処理（OpenAI を用いたセンチメント評価）などを含みます。モジュール構成は軽量な依存関係で設計されており、本番・ペーパートレード・開発モードをサポートします。

主な機能
--------
- ExecutionEngine（発注実行）
  - 本番・ペーパートレード切替（KABUSYS_ENV=paper_trading で MockBroker 使用）
  - 別ファイルの SQLite（ペーパートレード時）によるデータ分離
  - リスク管理（ポジション上限・資金利用率等）
  - PID / stop フラグ連携（data/execution.pid, data/stop_requested.flag）

- Monitoring（システム・注文・リスク監視）
  - SystemMonitor: CPU/メモリ/ディスク・データ鮮度・プロセス生存監視
  - TradeMonitor: 注文の滞留/約定異常検出
  - RiskMonitor: ドローダウン・ポジション数監視と kill switch トリガー
  - MonitoringEngine: 上記を束ねたポーリングループ
  - 監視ログ永続化（SQLite — monitoring.db）

- Portfolio Construction
  - 候補選定、等重・スコア加重、リスクベースの株数決定
  - セクター制限、レジームに基づく乗数

- Research / Factor Modules
  - momentum / volatility / value ファクター計算（DuckDB を使用）
  - forward returns / IC / 統計サマリー等の分析ユーティリティ

- AI（OpenAI を利用した機能）
  - news_nlp: ニュース記事を LLM でセンチメント評価して ai_scores に保存
  - regime_detector: ETF の MA やマクロニュースの LLM センチメントで市場レジーム判定

- CLI / ユーティリティ
  - 環境設定ウィザード: kabusys.config_setup（対話式で .env を生成）
  - 設定検証: kabusys.validate_config（環境変数・config YAML のチェック）
  - Paper Trading レポート生成ツール: kabusys.tools.paper_verification_report
  - ログ設定ユーティリティ、プロセス優先度設定ユーティリティなど

前提・インストール
------------------
推奨: Python 3.10+

主な依存パッケージ（最低限）
- duckdb
- psutil
- openai
- PyYAML（config YAML 検証に任意）
インストール例:
- pip install duckdb psutil openai pyyaml

（プロジェクトに requirements.txt がある場合はそちらを利用してください）

環境変数（代表）
----------------
主な環境変数（.env に設定）:
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- OPENAI_API_KEY（AI 機能を使う場合必須）
- KABUSYS_ENV (development | paper_trading | live) — 実行モード
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db） — Monitoring は常にこの本番パスを使用します
- PAPER_TRADING_SQLITE_PATH（ペーパートレード用 SQLite、デフォルト: data/paper_trading.db）
- LOG_LEVEL（DEBUG/INFO/…）
- PAPER_FILL_MODE（ペーパートレードの約定挙動: instant|partial|never|reject）
- KILL_FLAG_CLEAR_ON_START（本番での安全設定: 0 推奨）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔（秒）; デフォルト 60）

注意: .env は絶対に Git にコミットしないでください。

セットアップ手順
----------------
1. リポジトリをクローンし、Python 環境を用意する。
2. 依存パッケージをインストール:
   - pip install duckdb psutil openai pyyaml
3. 対話式で .env を作成（推奨）:
   - python -m kabusys.config_setup
   - 作成後、必要に応じて値を編集してください。
4. 設定検証:
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱いになります。
5. 必要なディレクトリを作成（通常スクリプトが自動で作成しますが手動でも可）:
   - data/
   - logs/

基本的な使い方
--------------
- 実行エンジン（ExecutionEngine）を起動:
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBroker を使用し PAPER_TRADING_SQLITE_PATH に記録します。
  - 起動時に data/stop_requested.flag が存在すると起動せず終了します。
  - 実行中は data/execution.pid を作成します。停止は data/stop_requested.flag を作成するか ExecutionEngine の API を使います。

- 監視ループを起動:
  - python -m kabusys.run_monitoring
  - デフォルトのポーリング間隔は 60 秒。環境変数 MONITOR_POLL_INTERVAL で上書き可能（秒）。
  - 監視プロセスは Settings.sqlite_path（デフォルト data/monitoring.db）に接続します（環境にかかわらず本番 sqlite_path を使用）。
  - 監視停止: data/stop_requested.flag を作成すると監視は次回ループで終了します。

- 環境設定ウィザード（.env 作成）:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート出力:
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH （PAPER_TRADING_SQLITE_PATH より優先）

- AI 関連（プログラムから呼ぶ）:
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - いずれも OPENAI_API_KEY を環境変数、または api_key 引数で指定する必要があります。

ログ / ファイル / フラグ
-----------------------
- ログ: logs/<app_name>.log（デフォルト: 日次ローテーション、30日保持）
  - setup_logging で統一的に設定（Stream と FileHandler）
- データベース:
  - DuckDB: data/kabusys.duckdb（デフォルト）
  - Monitoring SQLite: data/monitoring.db（監視ログ）
  - Paper Trading SQLite: data/paper_trading.db（ペーパー時に使用）
- PID / Stop / Kill:
  - data/execution.pid — ExecutionEngine の PID（run_execution で使用）
  - data/stop_requested.flag — run_monitoring / run_execution の外部停止フラグ（存在すると監視/実行ループを終了）
  - data/kill.flag — KillSwitch（Risk により ExecutionEngine を停止させるために書かれる可能性あり）
  - Settings.kill_flag_clear_on_start が 1 の場合、起動時に kill.flag を自動クリアします（本番では 0 推奨）

ディレクトリ構成（抜粋）
---------------------
src/
  kabusys/
    __init__.py                -- パッケージメタ情報（__version__ 等）
    config.py                  -- 環境変数 / Settings 管理（.env 自動ロードロジック含む）
    config_setup.py            -- .env 対話式ウィザード
    validate_config.py         -- 設定検証 CLI
    run_execution.py           -- ExecutionEngine 起動スクリプト
    run_monitoring.py          -- SystemMonitor 起動スクリプト
    utils/
      logging_setup.py         -- ログ設定ユーティリティ
      process_priority.py      -- プロセス優先度 / CPU affinity 設定
    execution/                  -- 発注関連モジュール（Engine, OrderManager, BrokerFactory 等）
    monitoring/
      monitoring_db.py         -- SQLite 永続層（テーブル初期化・ラッパー）
      system_monitor.py
      trade_monitor.py
      risk_monitor.py
      kill_switch.py
      monitoring_engine.py
      alert_manager.py
    portfolio/
      portfolio_builder.py
      position_sizing.py
      risk_adjustment.py
    research/
      factor_research.py
      feature_exploration.py
    ai/
      news_nlp.py              -- ニュース NLP（OpenAI 呼び出し）
      regime_detector.py       -- 市場レジーム検出
    tools/
      paper_verification_report.py

設計上の注意点 / 運用上の注意
---------------------------
- 環境分離:
  - paper_trading モードは本番 DB と完全分離される設計（PAPER_TRADING_SQLITE_PATH を使用）。
- 監視 DB は run_monitoring が使用するため、環境に関係なく Settings.sqlite_path を参照します（運用上の注意）。
- kill.flag / stop_requested.flag の取り扱いに注意。KILL_FLAG_CLEAR_ON_START を本番で 1 にするのは危険（自動クリアにより Kill Switch が無効化される恐れ）。
- OpenAI を使う機能は API 呼び出しに失敗してもフェイルセーフ（0.0 戻し等）するよう設計されていますが、API キーは必須です。
- ログディレクトリ作成やプロセス優先度設定は OS / 権限に依存します。psutil を利用しており、権限不足の場合は警告を出して継続します。

サンプル .env の抜粋
-------------------
（python -m kabusys.config_setup で生成されますが参考として）
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_password_here
KABU_API_BASE_URL=http://localhost:18080/kabusapi
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0
OPENAI_API_KEY=sk-...

トラブルシューティング（簡易）
------------------------------
- モジュールが見つからない:
  - 必要なパッケージがインストールされているか確認（duckdb, psutil, openai, pyyaml 等）。
- SQLite / DuckDB への接続エラー:
  - 指定したパスの親ディレクトリが存在するか、ファイルにアクセス権があるか確認。
- OpenAI 呼び出し失敗:
  - OPENAI_API_KEY が正しく設定されているか、ネットワーク制限がないか確認。

バージョン情報
---------------
- パッケージバージョンは kabusys.__version__ で参照できます（現行コード: 0.1.0）。

最後に
------
- .env は機密情報を含むため絶対にコミットしないでください。
- 本番稼働前に python -m kabusys.validate_config を実行して設定を検証してください。
- 何か追加で README に載せたい操作（例: デプロイ手順や systemd / Supervisor 用のサービス定義）があれば教えてください。必要に応じて追記します。