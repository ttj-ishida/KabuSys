KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買システム用ライブラリ兼ランタイムツール群です。
本リポジトリは、注文実行エンジン（ExecutionEngine）、監視コンポーネント（Monitoring）、
ポートフォリオ構築/ポジションサイジング、リサーチ用ファクター計算、AI を使ったニュース
センチメント解析などを含むモジュール群で構成されています。

主な設計方針
- 本番／ペーパートレード（分離された SQLite DB）をサポート
- DuckDB を分析用 DB として利用
- SQLite を監視・トレースログ用に利用
- OpenAI（gpt-4o-mini など）を用いたニュース NLP / レジーム判定をサポート（APIキー必須）
- ログや .env の自動読み込み / ウィザード、設定検証 CLI を提供

機能一覧
--------
- Execution
  - ExecutionEngine / OrderManager / RiskManager / Reconciler による発注・リスク管理パイプライン
  - paper_trading（モックブローカー）モードで本番 DB と完全分離された data/paper_trading.db に記録
- Monitoring
  - SystemMonitor: CPU/Mem/Disk、プロセス生存、データ鮮度監視
  - TradeMonitor: 注文滞留・約定異常などの検出
  - RiskMonitor: ドローダウン・ポジション上限監視、ダッシュボードの永続化
  - KillSwitch: 条件に応じて data/kill.flag を書き込み ExecutionEngine を停止
  - MonitoringEngine: 監視ループとアラート管理
- Portfolio construction
  - 候補選定、等配分／スコア配分、セクターキャップ、レジーム乗数適用、株数計算（単元丸め）
- Research
  - ファクター計算（Momentum/Value/Volatility 等）
  - forward return, IC, 統計サマリなどの解析ユーティリティ
- AI モジュール
  - news_nlp: ニュース記事を集約して OpenAI に送り銘柄毎のセンチメントを算出・保存
  - regime_detector: ma200 等と LLM によるマクロセンチメントを合成して市場レジームを判定・保存
- ユーティリティ
  - 設定ウィザード（.env 作成）: config_setup.py
  - 設定検証 CLI: validate_config.py（--strict オプションあり）
  - paper_trading の検証レポート生成ツール: tools/paper_verification_report.py
  - ロギング設定ユーティリティ、プロセス優先度設定ユーティリティ等
- データ永続化
  - DuckDB: prices_daily / raw_financials / raw_news 等の分析テーブル
  - SQLite: 監視・トレードログ・ポジション・リスクログ・ダッシュボード（monitoring_db.py）

前提・依存
-----------
主な依存（環境によってバージョン指定が必要）
- Python 3.9+
- duckdb
- psutil
- openai (AI 機能を使う場合)
- pyyaml（config の YAML 検証を行う場合に必要）
※ requirements.txt がない場合は上記を適宜 pip install してください。

セットアップ手順
----------------
1. リポジトリをクローン
   - git clone ... && cd <repo>

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存関係をインストール
   - pip install duckdb psutil openai pyyaml
   - （必要に応じて他のライブラリを追加）

4. .env の作成
   - 対話式に作る（推奨）
     - python -m kabusys.config_setup
       → ウィザードに従って J-Quants トークン、Kabu API パスワード、DB パス等を設定
   - もしくは .env.template/.env.example を参考に手動で作成してプロジェクトルートに配置する

5. 設定の検証
   - python -m kabusys.validate_config
   - 本番用に厳密チェックを行う場合:
     - python -m kabusys.validate_config --strict

6. データディレクトリ・ログディレクトリの確認
   - デフォルトの DB / ログパス:
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper Trading SQLite: data/paper_trading.db
     - ログ: logs/
   - ログディレクトリは LOG_DIR 環境変数で変更可能

主な環境変数（抜粋）
-------------------
- JQUANTS_REFRESH_TOKEN : J-Quants API 用（必須）
- KABU_API_PASSWORD     : kabuステーション API パスワード（必須）
- KABU_API_BASE_URL     : kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
- OPENAI_API_KEY        : OpenAI API キー（AI 機能を使う場合）
- KABUSYS_ENV           : 実行環境（development | paper_trading | live） デフォルト: development
  - paper_trading: MockBroker を使用し data/paper_trading.db に記録（本番 DB と分離）
- DUCKDB_PATH           : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH           : 監視 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH : ペーパートレード専用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE       : ペーパートレード時の約定モード（instant|partial|never|reject）
- LOG_LEVEL             : ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- MONITOR_POLL_INTERVAL : run_monitoring のポーリング間隔（秒。デフォルト 60）
- KILL_FLAG_CLEAR_ON_START : 起動時に kill.flag を自動クリア（0/1。デフォルト 0：本番は 0 推奨）
- LOG_DIR               : ログファイル保存先（デフォルト logs/）

使い方 (よく使うコマンド)
-------------------------
- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証（起動前チェック）
  - python -m kabusys.validate_config
  - 厳密モード（警告も失敗扱い）: python -m kabusys.validate_config --strict

- ExecutionEngine 起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を設定すると MockBroker を使用して data/paper_trading.db に記録され、本番 DB に影響しません
  - ExecutionEngine は data/stop_requested.flag を検知すると安全に停止します
  - 実行時に PID ファイル（data/execution.pid）が作成されます

- Monitoring 起動（ポーリング）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で変更可能（例: MONITOR_POLL_INTERVAL=30）
  - 監視は Settings に依存せず常に本番 sqlite_path を使用します（監視 DB は production 用 path）
  - 停止は data/stop_requested.flag を置くことで次のループで終了

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH（PAPER_TRADING_SQLITE_PATH 環境変数が優先されます）

- AI 系（OpenAI）機能
  - ニューススコア付与: kabusys.ai.score_news（プログラムから呼び出し）
  - レジーム判定: kabusys.ai.regime_detector.score_regime
  - OpenAI API キーが必要。キーは OPENAI_API_KEY 環境変数または引数で渡す

運用に関する注意
----------------
- 本番環境（KABUSYS_ENV=live）では設定・トークン管理、LINE 通知設定等を慎重に行ってください
- KILL_SWITCH（data/kill.flag）は ExecutionEngine を即停止させる重要な仕組みです。KILL_FLAG_CLEAR_ON_START の設定に注意
- ログは logs/<app_name>.log（daily rotation）に保存されます。ログディレクトリの権限・容量を監視してください
- Paper Trading は実際の注文を行いませんが、アルゴリズム検証に有用です。DB は本番 DB と分離されています

ディレクトリ構成
----------------
以下は主要ファイル・モジュールの抜粋です（src/kabusys 以下）。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor 起動スクリプト
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity
  - execution/
    - (ExecutionEngine, OrderManager, BrokerFactory, RiskManager, Reconciler, OrderRepository など)
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
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
  - data/                    — 実行時に使う data/ 以下の DB / フラグ（例: data/monitoring.db, data/paper_trading.db, data/kill.flag）
  - tools/
    - paper_verification_report.py

補足: 主要な実装ポイント
- Settings クラス（config.py）で環境変数を集中管理。自動的にプロジェクトルートの .env / .env.local を読み込み（必要に応じて無効化可能）。
- monitoring_db.init_monitoring_db() により監視用テーブル・マイグレーション（冪等）を担保。
- ロギングは setup_logging() 経由で統一。StreamHandler は stdout を使用（cron 等で stdout/stderr を管理しやすくするため）。
- ペーパートレードは settings.is_paper により専用 SQLite を使用し本番 DB と分離。

貢献・拡張
----------
- strategy や execution の実装は拡張可能（新しい Risk ルールや Broker クライアントの追加等）
- YAML 設定ファイルを用いた詳細設定や、各種メトリクスの可視化ダッシュボードへの出力等を追加できます

問い合わせ
----------
不明点や追加したい機能があれば issue を立ててください。

以上。README の改善要望や追加してほしい利用手順（例: systemd サービス化、Docker 化など）があれば教えてください。