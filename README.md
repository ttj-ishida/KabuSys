KabuSys
=======

日本株向け自動売買・リサーチ基盤のサブモジュール群を含むリポジトリのドキュメントです。  
本READMEはコードベースの主要スクリプト・モジュールの概要、起動手順、使い方、ディレクトリ構成を日本語でまとめたものです。

概要
----
KabuSys は日本株の自動売買／リサーチ基盤を想定した Python パッケージ群です。  
主要な役割は次のとおりです。

- 実行エンジン（ExecutionEngine）による発注制御（本番 / ペーパートレード切替対応）
- 監視（Monitoring）: システム状態、注文ログ、リスク（ドローダウン・保有上限）監視、Kill Switch
- ポートフォリオ構築・ポジションサイジング・セクター制限等の純粋関数ライブラリ
- DuckDB を使ったファクター計算 / 研究ツール
- OpenAI を用いたニュースNLP / レジーム検出（オプション）
- 運用ユーティリティ（設定ウィザード、設定検証、ペーパートレード検証レポート等）

主な機能
--------
- 実行（run_execution.py）
  - KABUSYS_ENV に応じて本番ブローカまたは MockBrokerClient を選択
  - 本番と paper_trading の SQLite DB を分離（PAPER_TRADING_SQLITE_PATH）
  - リスク管理（Rate limit / drawdown / position cap 等）を組み込んだ ExecutionEngine 起動
- 監視（run_monitoring.py / monitoring package）
  - SystemMonitor / TradeMonitor / RiskMonitor を組み合わせたポーリング監視
  - kill.flag による ExecutionEngine 停止（Kill Switch）
  - 監視ログを SQLite に永続化（monitoring_db）
- ポートフォリオ構築（portfolio package）
  - 候補選定、等重・スコア重み付け、ポジションサイズ計算、セクター制限、レジーム乗数
- 研究（research package）
  - DuckDB を用いたファクター計算（Momentum / Volatility / Value 等）
  - 将来リターン計算、IC（Information Coefficient）等
- AI（ai package）※オプション
  - news_nlp: OpenAI を用いたニュースセンチメント集約＆ai_scores 書込
  - regime_detector: ETF MA 乖離＋マクロニュースで市場レジーム判定
- ユーティリティ
  - 環境設定ウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py）
  - Paper Trading 検証レポート生成（tools/paper_verification_report.py）
  - ロギング設定 / プロセス優先度ユーティリティ 等

要件
----
- Python 3.10+（型ヒントに | を使用しているため）
- 必要な Python パッケージ（例）
  - duckdb
  - psutil
  - openai (AI 機能を使用する場合)
  - PyYAML（config 検証で YAML 検査を行う場合、任意）
- SQLite は標準モジュールで利用
- OS に応じてプロセス優先度設定は権限が必要な場合があります

セットアップ手順
---------------
1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo-root>

2. 仮想環境（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - requirements.txt があれば: pip install -r requirements.txt
   - なければ最小例:
     - pip install duckdb psutil
     - pip install openai  # AI 機能を使う場合
     - pip install pyyaml  # validate_config で YAML 検証を行う場合

4. 初期環境変数（.env）を作成
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - 重要な必須環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
   - 主要なオプション:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（ペーパートレード用 DB、デフォルト: data/paper_trading.db）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - LOG_LEVEL（例: INFO）

5. 設定検証（起動前推奨）
   - python -m kabusys.validate_config
   - 警告も FAIL にする場合: python -m kabusys.validate_config --strict

基本的な使い方
--------------
- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - 動作: Settings に基づいて DB を開き、BrokerClient を生成して Engine をスレッドで起動します。
  - ペーパートレード: KABUSYS_ENV=paper_trading とすると MockBrokerClient を使い、PAPER_TRADING_SQLITE_PATH に記録します。
  - 停止フラグ:
    - 起動時 / 実行中に data/stop_requested.flag が存在すると起動を停止／実行中は停止処理を行います。
    - Kill Switch による停止要求は data/kill.flag に書き込まれます。

- 監視プロセス起動（Monitoring）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60）
    - 例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視は常に Settings.sqlite_path（本番監視 DB）を使用します（paper_trading の有無に関わらず）。

- 設定ウィザード
  - python -m kabusys.config_setup
  - .env を対話式に生成・更新できます。

- 設定検証
  - python -m kabusys.validate_config
  - .env と config/*.yaml の存在や主要値の妥当性をチェックします（PyYAML 未インストール時は YAML 検査をスキップ）。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD --to YYYY-MM-DD で集計期間を指定
    - --db PATH で DB パス指定（優先順位: --db > 環境変数 PAPER_TRADING_SQLITE_PATH > デフォルト data/paper_trading.db）

- AI 機能（ニュース NLP / レジーム）
  - プログラムから呼び出す想定（CLI エントリは用意されていません）
  - 例（Python REPL / スクリプト）:
    - from datetime import date
      import duckdb
      from kabusys.ai.news_nlp import score_news
      conn = duckdb.connect("data/kabusys.duckdb")
      score_news(conn, date(2026,4,1), api_key="sk-...")

運用上の注意
--------------
- Kill Switch / Stop フラグ:
  - KillSwitch はデータベース上の監視結果を評価して data/kill.flag を書き込みます。ExecutionEngine はこのファイルの存在を検知して安全に停止します。
  - 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると kill.flag を自動クリアします（本番では 0 を推奨）。
- ログ:
  - kabusys.utils.logging_setup.setup_logging を各起動スクリプトから呼んで統一的にログ出力（コンソール + 日次ローテーションファイル）を行います。LOG_DIR 環境変数でログ保存先を変更できます。
- プロセス優先度:
  - 起動スクリプトは set_process_priority("high") を呼びます。権限不足で警告が出る場合があります。
- Paper Trading:
  - paper_trading 環境では MockBrokerClient を使用し、本番 DB と完全分離して data/paper_trading.db に記録します。

ディレクトリ構成（主要ファイル）
-------------------------------
src/kabusys/
- __init__.py
- config.py
  - Settings クラス: 環境変数読み込み、自動 .env ロード（.env / .env.local）
- config_setup.py
  - .env 対話式ウィザード
- validate_config.py
  - 起動前チェック CLI（--strict あり）
- run_execution.py
  - ExecutionEngine 起動スクリプト（KABUSYS_ENV による切替）
- run_monitoring.py
  - SystemMonitor のポーリング起動スクリプト（MONITOR_POLL_INTERVAL）
- monitoring/
  - monitoring_db.py: SQLite スキーマ＋永続化 API（MonitoringDB）
  - system_monitor.py: システム状態・データ鮮度監視
  - trade_monitor.py: （注文滞留・約定異常などの検知）※コード内に存在（今回は省略）
  - risk_monitor.py: ドローダウン／ポジション上限監視
  - kill_switch.py: kill.flag の書き込み・管理
  - monitoring_engine.py: 各 Monitor を束ねる実行エンジン
  - alert_manager.py: （通知管理、LINE 連携等）※コード内に存在（今回は省略）
- execution/
  - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py（発注・リスク制御等）
- portfolio/
  - portfolio_builder.py: 候補選定・重み計算
  - position_sizing.py: 発注株数計算（lot 単位丸め、aggregate cap）
  - risk_adjustment.py: セクターキャップ・レジーム乗数
- research/
  - factor_research.py: Momentum/Value/Volatility ファクター計算（DuckDB）
  - feature_exploration.py: 将来リターン・IC・統計サマリ等
- ai/
  - news_nlp.py: OpenAI を使ったニュース集約スコアリング（ai_scores テーブル書込）
  - regime_detector.py: MA + マクロニュースで市場レジーム判定
- tools/
  - paper_verification_report.py: Paper Trading の検証レポート生成スクリプト
- utils/
  - logging_setup.py: ログ設定ユーティリティ
  - process_priority.py: プロセス優先度・CPU affinity 設定ユーティリティ
  - （その他ユーティリティ）

補足
----
- 環境変数自動読み込み:
  - config.py はプロジェクトルート（.git または pyproject.toml）を探索して .env / .env.local を自動読み込みします。自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト時など）。
- DB マイグレーション:
  - monitoring_db.init_monitoring_db は idempotent（既存テーブルに対して安全に実行可能）で、必要なカラムがない場合は ALTER TABLE による簡易マイグレーション処理を行います。
- PyYAML が無い場合、validate_config は YAML ファイルの内容検証をスキップします（警告表示）。

問い合わせ / 追加ドキュメント
-------------------------
- 各モジュールには docstring が付与されています。詳細を参照したい場合は該当モジュールの docstring を参照してください。
- StrategyModel.md / PortfolioConstruction.md 等の設計ドキュメントがリポジトリに含まれている場合はそちらも参照してください（コード内コメントで参照されています）。

以上がこのコードベースの概要と利用手順です。具体的な運用フローやブローカ実装、Order/Engine の詳細は execution パッケージ内の実装をご確認ください。必要なら起動コマンド例や .env のサンプルを追記します。どの部分をさらに詳しく説明しましょうか？