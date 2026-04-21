KabuSys — 日本株自動売買システム
================================

このリポジトリは、バックテスト／ポートフォリオ構築／注文実行／監視を含む
日本株自動売買システムの一部実装です。モジュールはできるだけ純粋関数／依存注入
で設計され、運用スクリプトとライブラリ機能が混在しています。

本 README ではプロジェクト概要、機能一覧、セットアップ手順、主要な使い方、
およびディレクトリ構成を日本語でまとめます。

プロジェクト概要
----------------
- 名称: KabuSys
- 目的: 日本株向けの自動売買システム（戦略計算・ポートフォリオ構築・発注・監視・運用補助）
- 設計方針:
  - ランタイム設定は環境変数（.env）で管理
  - DuckDB を分析用 DB、SQLite を監視・注文ログ用 DB に使用
  - 実運用向けの監視・Kill Switch 機構を備える
  - Paper Trading モードで実際の発注を分離（専用 SQLite を使用）
  - AI（OpenAI）を用いたニュースセンチメントやレジーム判定機能を含む

主な機能一覧
-------------
- 実行（Execution）
  - ExecutionEngine を用いた注文実行フロー（risk manager / order manager / reconciler 等）
  - KABUSYS_ENV=paper_trading で MockBrokerClient と専用 DB によるペーパートレード
- 監視（Monitoring）
  - SystemMonitor: CPU/メモリ/ディスク・データ鮮度・プロセス生存確認
  - TradeMonitor / RiskMonitor: 注文滞留、約定異常、ドローダウン・ポジション上限監視
  - KillSwitch: ドローダウン等の条件で data/kill.flag にフラグを書き実行エンジンを停止
  - MonitoringEngine / run_monitoring スクリプトでポーリング監視
- ポートフォリオ構築（Portfolio）
  - 候補選定、重み計算（等分配・スコア重み）、ポジションサイジング、セクター制約、レジーム乗数
- 研究・ファクター計算（Research）
  - モメンタム、ボラティリティ、バリュー等のファクター計算（DuckDB を利用）
  - 将来リターン・IC・統計サマリ等のユーティリティ
- AI 機能
  - news_nlp: raw_news をまとめて OpenAI に投げセンチメントスコアを ai_scores に保存
  - regime_detector: ETF (1321) の MA とマクロニュースの LLM 評価を組み合わせ市場レジーム判定
- 運用補助ツール
  - config_setup: 対話式で .env を生成・更新するウィザード
  - validate_config: .env や config/*.yaml の存在・基本整合性チェック
  - tools/paper_verification_report: ペーパートレード DB から検証レポートを生成

前提・依存関係
--------------
- Python 3.9+（typing | union 演算子等を使用）
- 必須パッケージ（代表例）:
  - duckdb
  - psutil
  - openai
- 任意（機能により）:
  - PyYAML（config/*.yaml の構文チェックに使用。未インストールでも動作）
- 標準ライブラリ: sqlite3, logging, threading, datetime, pathlib など

簡単なセットアップ手順
---------------------
1. リポジトリをクローンし、作業ディレクトリに移動
   - 実行例:
     - git clone <repo>
     - cd <repo>

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - 重要: 実リポジトリに requirements.txt がない場合、少なくとも以下を入れると主要機能が動きます:
     - pip install duckdb psutil openai
   - 開発時に PyYAML を使う場合:
     - pip install PyYAML

4. .env の作成（対話型ウィザード推奨）
   - python -m kabusys.config_setup
   - ウィザードに従って J-Quants トークン、Kabu API パスワード、DB パス 等を入力してください
   - 生成された .env は絶対に Git にコミットしないでください

5. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告でも exit(1) になります

6. ディレクトリの準備（任意）
   - data/ と logs/ はスクリプトが自動作成しますが、権限等で問題がある場合は事前作成してください

環境変数（主要）
----------------
- 必須（最低限）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 運用関連
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
    - paper_trading の場合、ExecutionEngine は MockBrokerClient を使用し data/paper_trading.db に記録
  - SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
  - DUCKDB_PATH: 分析 DB（デフォルト: data/kabusys.duckdb）
  - PAPER_TRADING_SQLITE_PATH: paper_trading 用 DB（デフォルト: data/paper_trading.db）
  - OPENAI_API_KEY: OpenAI を使う機能で必要（news_nlp / regime_detector）
  - LOG_LEVEL: ログレベル（DEBUG/INFO/...）
  - LOG_DIR: ログ保存先（デフォルト: logs/）
  - KILL_FLAG_CLEAR_ON_START: ExecutionEngine 起動時に kill.flag を自動クリアするか（0/1、本番は 0 推奨）
- 監視関連
  - MONITOR_POLL_INTERVAL: run_monitoring がポーリング間隔（秒）をオーバーライド（デフォルト: 60）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1: 自動で .env を読み込む機能を無効化（テスト用）

主要な使い方（コマンド）
-----------------------
- 環境ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - オプション: 環境変数 MONITOR_POLL_INTERVAL=30 などでポーリング間隔を変更
  - 監視は常に本番用の sqlite_path（settings.sqlite_path）を参照する設計です

- 実行エンジン起動（発注）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient と data/paper_trading.db を使用し本番 DB と分離
  - 実行はバックグラウンドスレッドで行われ、data/execution.pid を PID ファイルとして書きます
  - 停止: data/stop_requested.flag を作成するとスレッドは終了処理を行って停止します

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH  （PAPER_TRADING_SQLITE_PATH 環境変数またはデフォルトを上書き）

ライブラリ（プログラム的利用例）
--------------------------------
- 研究・ファクター計算（DuckDB 接続を渡す）
  - from kabusys.research import calc_momentum
  - conn = duckdb.connect("data/kabusys.duckdb")
  - results = calc_momentum(conn, date(2026,4,1))

- AI スコアリング（news_nlp）
  - from kabusys.ai import score_news
  - conn = duckdb.connect("data/kabusys.duckdb")
  - n = score_news(conn, date(2026,4,1), api_key="sk-...")  # or set OPENAI_API_KEY

- レジーム判定
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(conn, date(2026,4,1), api_key="...")

- ポートフォリオ／サイジング
  - from kabusys.portfolio import select_candidates, calc_equal_weights, calc_position_sizes
  - candidates = select_candidates(buy_signals, max_positions=10)
  - weights = calc_equal_weights(candidates)
  - shares = calc_position_sizes(weights, candidates, portfolio_value, available_cash, ...)

停止／Kill の仕組み
-------------------
- run_monitoring.py / run_execution.py はプロジェクト内の data/stop_requested.flag を監視しており、
  ファイルが存在すると安全にループを抜けて終了します（daemon 環境での安全停止に使用）。
- KillSwitch (監視側) は条件を満たすと data/kill.flag を書き込み、ExecutionEngine 側でこの kill.flag の存在を検出して停止するような運用に適しています。
- 実行時の起動前に kill.flag を自動クリアしたい場合は Settings.kill_flag_clear_on_start を活用できます（ただし本番では無効を推奨）。

ログ
----
- ログはデフォルトで stdout（StreamHandler）と logs/<app_name>.log（日次ローテート）に出力されます。
- ログディレクトリは環境変数 LOG_DIR で変更可能。作成できない場合はファイル出力をスキップしてコンソール出力のみになります。

重要な注意点
------------
- .env は機密情報を含むため絶対に Git にコミットしないでください
- KABUSYS_ENV=live のときは実際に発注が行われます。必須環境変数や通知設定（LINE）を十分に確認してください
- OpenAI API を使用する機能は API キーの使用量や応答内容に依存するため、運用前にレート制限や費用を確認してください
- DB マイグレーションやスキーマ変化は init_monitoring_db 等で一部自動対応しますが、本番移行時はバックアップを取ることを推奨します

ディレクトリ構成（主要ファイル）
-------------------------------
プロジェクトの src/kabusys 以下の主要なファイル／パッケージは以下の通りです（一部抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings 管理（.env 自動読み込みロジック含む）
  - config_setup.py           — .env 対話型ウィザード
  - validate_config.py        — 起動前設定検証 CLI
  - run_monitoring.py         — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - utils/
    - logging_setup.py        — 共通ログ設定ユーティリティ
    - process_priority.py     — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py        — SQLite スキーマと永続化 API
    - system_monitor.py
    - trade_monitor.py        — （存在／実装に依存）
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py        — （存在／実装に依存）
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
  - tools/
    - paper_verification_report.py

（実際のリポジトリにはさらに execution, data, strategy 等のサブパッケージや追加モジュールが含まれます。）

補足
----
- 開発時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を指定して自動 .env ロードを無効化できます（テスト等で便利）。
- YAML ベースの config/ ファイルの生成はスクリプトが用意されている場合があるため、validate_config は PyYAML があると中身のパースチェックも行います。
- ライブラリ API は docstring に使用法が多く記載されています。関数やクラスの詳細は該当モジュール内の docstring を参照してください。

以上。セットアップや実行中に不明点があれば、どのコマンド／機能について知りたいかを教えてください。さらに具体例（環境変数のサンプル .env、実行ログの確認方法、DuckDB の簡単なクエリ例など）を用意します。