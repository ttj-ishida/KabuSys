KabuSys — 日本株自動売買システム
=============================

本ドキュメントはこのリポジトリの概要、主要機能、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめた README です。

プロジェクト概要
----------------
KabuSys は日本株向けの自動売買・研究プラットフォームです。  
主な目的は以下です：
- マーケットデータ（DuckDB）を用いたファクター計算・リサーチ
- 発注／実行エンジン（kabuステーション 等）とのインターフェース
- 監視（システム／注文／リスク）と Kill Switch による安全停止機能
- Paper Trading（模擬発注）を専用 DB に分離して検証可能
- ニュースを LLM（OpenAI）で評価してスコア化する AI モジュール

機能一覧
--------
- 環境設定ウィザード（.env の対話式生成）: kabusys.config_setup.run_wizard
- 設定検証 CLI（.env と config/*.yaml の検証）: kabusys.validate_config
- 実行エンジン起動スクリプト: run_execution (本番 / paper_trading に対応)
- 監視ループ起動スクリプト: run_monitoring（MONITOR_POLL_INTERVAL でポーリング間隔調整可）
- 監視サブシステム:
  - SystemMonitor: CPU/メモリ/ディスク/プロセス／データ鮮度監視
  - TradeMonitor: 発注ログの監視（滞留注文・約定異常等）
  - RiskMonitor: ドローダウン、ポジション上限監視とリスクログ記録
  - KillSwitch: 条件により data/kill.flag を書き込み ExecutionEngine 停止
  - MonitoringEngine: 上記を束ねてポーリング、アラート発行
- DB 層（SQLite）: 監視ログ用テーブル／永続化ユーティリティ（monitoring_db）
- ポートフォリオ構築ユーティリティ: 候補選定・重み付け・ポジションサイズ計算・セクターキャップ
- リサーチ（DuckDB）:
  - ファクター計算（モメンタム、バリュー、ボラティリティ等）
  - 特徴量探索 / IC 計算 / 将来リターン
- AI モジュール:
  - news_nlp: raw_news から OpenAI を使い銘柄別センチメント（ai_scores へ書込）
  - regime_detector: ma200 とマクロニュースを合成して日次の市場レジーム判定
- ツール:
  - paper_verification_report: Paper Trading DB を集計し PASS/FAIL 判定の検証レポートを出力

事前要件
--------
- Python 3.9+（型アノテーションや pathlib を多用）
- 必要と思われる主要ライブラリ（例）:
  - duckdb
  - psutil
  - openai
  - pyyaml（config YAML の検証に必要だが任意）
- OS: Linux / macOS / Windows で動作するよう設計（ただし一部の機能は UNIX 系依存の挙動あり）

（requirements.txt はリポジトリに含まれていないため、必要なライブラリを上記を目安にインストールしてください）

セットアップ手順
--------------
1. リポジトリをクローン・チェックアウト
   - 例: git clone ... && cd <repo>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存ライブラリをインストール
   - pip install duckdb psutil openai pyyaml
   - プロジェクトに requirements.txt があればそれを使用してください。

4. .env の準備（対話式ウィザード推奨）
   - python -m kabusys.config_setup
   - ウィザードで必須の JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等を設定してください。
   - 注意: .env は絶対にリポジトリにコミットしないでください（シークレットを含むため）。

5. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります。
   - config/*.yaml は存在しない・未生成でも warnings が出ます。generate スクリプトがある場合は利用してください（validate_config のメッセージ参照）。

6. DB 初期化
   - 起動スクリプト（run_monitoring / run_execution）が起動時に monitoring 用 SQLite テーブルを作成します（init_monitoring_db）。
   - DuckDB ファイルは環境変数 DUCKDB_PATH（デフォルト data/kabusys.duckdb）で指定。

使い方
------

共通
- 環境変数の自動読み込み:
  - デフォルトでプロジェクトルートの .env と .env.local を読み込みます（OS 環境変数が優先）。
  - 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

主要コマンド
- 設定ウィザード（.env 生成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - Strict モード: python -m kabusys.validate_config --strict

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔を環境変数で指定可能: MONITOR_POLL_INTERVAL=30
  - 監視は常に本番用 sqlite_path を使用する（監視ログは環境に依存しない）

- 実行エンジン起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を指定すると MockBrokerClient を使用し、paper_trading 専用 DB（PAPER_TRADING_SQLITE_PATH）に記録します（本番 DB と完全分離）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで DB パスを指定可能（デフォルトは環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db）

AI 関連
- news_nlp.score_news(conn, target_date, api_key=None)
  - DuckDB 接続と対象日を渡してニューススコアを ai_scores テーブルへ書き込む
  - OPENAI_API_KEY を環境変数または api_key 引数で渡す必要あり

- regime_detector.score_regime(conn, target_date, api_key=None)
  - 市場レジームを計算して market_regime テーブルへ書き込む

停止／Kill フラグ
- ExecutionEngine を停止させる方法:
  - KillSwitch は data/kill.flag を作成してエンジンに停止シグナルを送る
  - run_monitoring / run_execution は data/stop_requested.flag を検知して自身のループを終了する（管理用の停止フラグ）
- 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動クリアする（本番では 0 推奨）

ログ
- ログ設定は kabusys.utils.logging_setup.setup_logging を通じて統一されます。
- デフォルトログディレクトリ: logs/
- 起動時に app_name を渡して logs/<app_name>.log に日次ローテーションで保存（30 日保持）
- 標準出力は stdout に書かれます

主要な環境変数（抜粋）
--------------------
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live（デフォルト development）
- OPENAI_API_KEY: OpenAI API キー（ai モジュールで使用）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 SQLite ファイルパス（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の約定モード（instant|partial|never|reject、デフォルト instant）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR: ログの出力先ディレクトリ（デフォルト logs）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動で消すか（0/1）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）

ディレクトリ構成（主要ファイル）
-----------------------------
以下は src/kabusys 配下の主要モジュールと簡単な説明です（抜粋）:

- kabusys/__init__.py
  - パッケージ定義、__version__

- run_monitoring.py
  - SystemMonitor を初期化してポーリングを実行する起動スクリプト

- run_execution.py
  - ExecutionEngine を組み立てて実行する起動スクリプト（paper_trading と本番を分離）

- config.py
  - 環境変数の読み込み・解釈・Settings クラス

- config_setup.py
  - .env を対話式で生成・更新するウィザード

- validate_config.py
  - .env / config/*.yaml を検証する CLI

- utils/
  - logging_setup.py: ログ一元設定（Stream + TimedRotatingFile）
  - process_priority.py: プロセス優先度／CPU affinity 設定ユーティリティ

- monitoring/
  - monitoring_db.py: SQLite テーブル初期化・永続化 API（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py: システム状態・データ鮮度の監視
  - trade_monitor.py: 発注ログ監視（この README のコード一覧では一部省略）
  - risk_monitor.py: ドローダウン・ポジション上限監視
  - kill_switch.py: data/kill.flag 書込による停止シグナル
  - monitoring_engine.py: 各 monitor を束ねるエンジン
  - alert_manager.py: アラート送信（LINE など） — コード内参照あり

- execution/
  - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py
  - 実行エンジン本体と注文／リスク管理の実装（起動は run_execution）

- portfolio/
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py
  - 候補選定、重み付け、株数算出、セクター制限、レジーム乗数など

- research/
  - factor_research.py, feature_exploration.py
  - DuckDB を使ったファクター計算、将来リターン、IC 計算、統計サマリ等

- ai/
  - news_nlp.py: ニュースセンチメントの LLM スコアリング（ai_scores 書込）
  - regime_detector.py: ma200 とマクロニュースを合成したレジーム判定

- tools/
  - paper_verification_report.py: Paper Trading の検証レポート生成スクリプト

運用上の注意
------------
- 本番環境（KABUSYS_ENV=live）での設定は慎重に扱ってください。validate_config は live 時に追加警告を出します（LINE 通知設定未設定など）。
- .env とシークレット情報は絶対に VCS にコミットしないでください。
- OpenAI 呼び出しは API コストが発生します。テスト時はキーの無い状態・モックでの検証を推奨します。
- Paper Trading は paper_trading 用 DB に完全分離してログを残すため、本番 DB に影響を与えません。

追加情報・開発
---------------
- config/*.yaml（system_config.yaml, data_config.yaml, strategy_config.yaml, risk_config.yaml, execution_config.yaml, monitoring_config.yaml）を使って設定を拡張できます。validate_config はこれらの存在・パースを検証します（PyYAML がある場合）。
- テストや CI では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して環境依存を回避できます。
- 既存 DB スキーマに対する簡易マイグレーションは monitoring_db.init_monitoring_db 内で実施しています（例: カラム追加）。

問い合わせ・貢献
----------------
不具合報告や改善提案は Issue を立ててください。プルリクエスト歓迎です。設計上の注意点や API の変更がある場合は README を更新してください。

以上。各モジュールの詳細な使用方法・API はソースコード内の docstring を参照してください。