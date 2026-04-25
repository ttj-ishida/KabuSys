KabuSys — 日本株自動売買システム（簡易 README）
=================================

概要
----
KabuSys は日本株向けの自動売買システムのパイロット実装です。本リポジトリは以下の責務を持つモジュール群で構成されています。

- 実行エンジン（ExecutionEngine）：発注・注文管理・リスク管理
- 監視（Monitoring）：プロセス／システム状態、注文状況、リスク監視と Kill Switch
- ポートフォリオ構築（Portfolio）：銘柄選定・重み付け・ポジションサイズ計算
- 研究（Research）：ファクター計算・特徴量解析
- AI 補助（AI）：ニュースのセンチメント評価、レジーム検出
- ユーティリティ群：設定読み込み、ログ設定、プロセス優先度など

主な設計方針：
- 本番 DB とペーパートレード DB を分離（KABUSYS_ENV により切替）
- DuckDB を分析用に利用、SQLite を監視／発注ログ用に利用
- LLM（OpenAI）呼び出しはフェイルセーフ・リトライを実装
- ルックアヘッドバイアス回避（date.today() 直接参照を避ける実装）

機能一覧
--------
主要な機能（抜粋）:

- Execution
  - 発注フロー（OrderManager / ExecutionEngine）
  - リスク管理（RiskManager）
  - Reconciler（ブローカー状態とローカル DB の整合維持）
  - Paper Trading モード（MockBrokerClient、専用 DB に記録）
- Monitoring
  - SystemMonitor：CPU/メモリ/Disk、データ鮮度、実行プロセス監視
  - TradeMonitor：注文滞留・約定異常検出（コード略）
  - RiskMonitor：ドローダウン・ポジション上限監視、KillSwitch と連携
  - MonitoringEngine：定周期ポーリングとアラート発行
- Portfolio
  - 銘柄選定（スコア順・上位 N 抽出）
  - 重み計算（等配分・スコア加重）
  - ポジションサイズ決定（リスクベース／等配分）
  - セクターキャップ、レジーム乗数
- Research
  - ファクター計算（モメンタム／ボラティリティ／バリュー）
  - 将来リターン、IC（Information Coefficient）計算等
- AI
  - ニュース NLP（OpenAI）で銘柄毎センチメント算出・ai_scores 書込み
  - レジーム検出（ETF MA200 とマクロニュースの合成）
- ツール
  - 設定ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - ペーパートレード検証レポート生成（paper_verification_report）

セットアップ手順
----------------

前提
- Python 3.10+
- SQLite（標準ライブラリに含まれる）
- システムにより追加で以下パッケージが必要です:
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証のため任意）
インストール例:
  pip install duckdb psutil openai pyyaml

（実際のプロジェクトでは requirements.txt を用意して pip install -r requirements.txt を推奨）

初期設定
1. プロジェクトルートに移動（パッケージはパスから自動で .env を読み込みます）
2. 環境変数を対話式に作成・更新:
   python -m kabusys.config_setup
   - .env を生成します（J-Quants トークン、kabu API パスワード等を設定）
3. 設定検証:
   python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit 1）

重要な環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
  - paper_trading: Mock ブローカーを使用し、紙トレード専用 DB に記録
- DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — paper_trading 時の約定モード（instant | partial | never | reject）
- LOG_LEVEL — ログレベル（DEBUG|INFO|...、デフォルト INFO）
- OPENAI_API_KEY — OpenAI を使用する機能で必要
- KILL_FLAG_CLEAR_ON_START — Execution 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0）

使い方（起動 / 実行例）
-----------------------

設定ウィザード・検証
- .env 作成:
  python -m kabusys.config_setup
- 設定検証:
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

監視プロセス起動（Monitoring）
- 監視ループを起動:
  python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き（デフォルト 60）
  - 監視は常に本番用 sqlite_path を参照（環境にかかわらず monitoring DB は同一）
  - 停止: プロセスに KeyboardInterrupt を送るか、プロジェクト上の data/stop_requested.flag を作成すると監視ループが終了します

実行エンジン起動（Execution）
- エンジンを起動:
  python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録します
  - 起動時に data/stop_requested.flag が存在すると起動せず終了
  - 実行中は data/execution.pid に PID を書きます。停止は stop_requested.flag の作成や kill.flag によって行われます（ExecutionEngine 側で graceful stop）

Paper Trading 検証レポート
- レポートを生成:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で DB パスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH を優先）

AI 機能
- ニューススコア付与（programmatic 呼び出し例）:
  from kabusys.ai.news_nlp import score_news
  score_news(duckdb_conn, target_date, api_key=...)
- レジーム判定:
  from kabusys.ai.regime_detector import score_regime
  score_regime(duckdb_conn, target_date, api_key=...)

ログ
- logging_setup により stdout と日次ローテーションファイルを出力
- デフォルトログディレクトリ: logs/
- アプリ名に基づくログファイル: logs/execution.log, logs/monitoring.log など
- LOG_DIR, LOG_LEVEL で上書き可能

監視・停止フラグ（運用上重要）
- data/stop_requested.flag
  - run_monitoring/run_execution が監視している「停止要求」フラグ。存在すると各ループは終了します（運用上プロセス停止に利用）
- data/kill.flag
  - KillSwitch が条件を満たした際に書き込まれるフラグ。ExecutionEngine 側で参照して停止させる用途（Settings.kill_flag_path でパスを指定可能）
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に自動でクリアされます（本番では 0 推奨）

ディレクトリ構成（主要ファイル）
-------------------------------

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み・自動ロード（.env/.env.local）・Settings クラス
  - config_setup.py
    - .env を対話式に作成するウィザード
  - validate_config.py
    - 起動前の設定チェック CLI
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプト（paper_trading 切替を含む）
  - utils/
    - logging_setup.py — ログ設定ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py — SQLite スキーマ初期化・簡易永続化 API
    - system_monitor.py, trade_monitor.py, risk_monitor.py, kill_switch.py, monitoring_engine.py, alert_manager.py（監視周りの実装）
  - execution/
    - execution_engine.py, order_manager.py, order_repository.py, broker_factory.py, reconciler.py, risk_manager.py（発注系）
  - portfolio/
    - portfolio_builder.py, position_sizing.py, risk_adjustment.py（ポートフォリオ構築）
  - research/
    - factor_research.py, feature_exploration.py（ファクター計算・解析）
  - ai/
    - news_nlp.py（ニュース NLP）, regime_detector.py（レジーム判定）
  - tools/
    - paper_verification_report.py（ペーパートレードの検証レポート）

設計上の注意点 / 運用メモ
-----------------------
- KABUSYS_ENV が live の場合は設定を慎重に管理してください（validate_config では警告が出ます）。
- .env は Git 管理下に置かないでください（config_setup も README に警告あり）。
- OpenAI を呼ぶ機能は API キー（OPENAI_API_KEY）が必要です。API 呼び出しで失敗してもフェイルセーフで処理継続する実装が多いですが、結果欠損に注意してください。
- 監視と実行は別プロセスで運用することを想定しています。監視が KillSwitch を発火すると execution 側で停止する仕組みがあります。
- DuckDB は分析向け・履歴参照用、SQLite は軽量永続化（監視／発注ログ）用途で使い分けられています。

貢献・拡張
----------
- strategy や execution の詳細実装は拡張可能です（BrokerClient の追加、単元株サイズの銘柄別対応など）。
- テストのために OPENAI 呼び出しや外部 API をモックするためのフックがコード中に用意されています。
- 将来的な改善案: 銘柄別 lot_size、手数料モデルの拡張、監視アラートのカスタマイズ機能、Kubernetes / systemd ユニットでの自動起動スクリプトなど。

ライセンス / バージョン
----------------------
- バージョンは src/kabusys/__init__.py の __version__ で管理されています（例: 0.1.0）。
- ライセンス情報はリポジトリルートに LICENSE 等を配置してください（本 README では指定なし）。

以上。運用や実装上の詳細（各モジュールの API や挙動）についてさらに README に追記したい箇所があれば、対象モジュールを指定していただければ追記します。