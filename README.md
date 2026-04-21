# KabuSys

日本株向けの自動売買システム（ライブラリ部分）。シグナル生成、ポートフォリオ構築、発注エンジン、監視・アラート、AI を用いたニュース解析、リサーチ用ユーティリティなどを含みます。

以下はコードベースから生成した README です。実行スクリプトはモジュールとして起動できます（例: `python -m kabusys.run_execution`）。

---

目次
- プロジェクト概要
- 主な機能
- 前提（依存関係）
- セットアップ手順
- 環境変数（.env）と重要な設定
- 実行方法（コマンド例）
- 主要コンポーネント説明
- ディレクトリ構成

---

プロジェクト概要
- KabuSys は日本株の自動売買に必要な機能群（データ処理、ファクター計算、ポートフォリオ構築、発注エンジン、監視、AIベースのニュース解析、レポート生成）をまとめた Python パッケージです。
- 実際の取引は kabuステーション API を使用し、ペーパートレード用モード（完全分離された SQLite DB に記録）もサポートします。
- 監視コンポーネントはシステム稼働状況や注文状況を定期的にチェックし、条件に応じて Kill Switch（フラグファイル）を作成して発注エンジンを安全に停止できます。

主な機能（機能一覧）
- 設定管理
  - .env ファイルの自動読み込み（プロジェクトルートから）
  - 対話式設定ウィザード（python -m kabusys.config_setup）
  - 設定検証 CLI（python -m kabusys.validate_config）
- 実行エンジン
  - ExecutionEngine（発注処理、リスク管理、注文管理） — run_execution 起動
  - Paper trading モード（KABUSYS_ENV=paper_trading）では MockBroker を使い、data/paper_trading.db にデータを保存
- 監視（Monitoring）
  - SystemMonitor（CPU/メモリ/ディスク、データ鮮度、Execution プロセス存在監視）
  - TradeMonitor（滞留注文・約定異常検出など）
  - RiskMonitor（ドローダウン / ポジション上限監視）
  - KillSwitch（条件成立時に data/kill.flag を書き込み ExecutionEngine を停止）
  - Polling ループ起動スクリプト（run_monitoring）
- ポートフォリオ構築（pure functions）
  - 銘柄選定（select_candidates）
  - 配分重み算出（等金額、スコア重み）
  - リスク制約（セクターキャップ、レジーム乗数）
  - ポジションサイズ計算（単元株丸め、集約キャップ対応）
- リサーチ / ファクター
  - モメンタム・ボラティリティ・バリュー等のファクター計算（DuckDB 経由）
  - 将来リターン・IC（Information Coefficient）計算、統計サマリー
- AI（OpenAI 統合）
  - ニュース NLP（ニュースを LLM でセンチメント化し ai_scores に保存）
  - レジーム検出（ETF の MA とマクロニュースを組み合わせて判定）
- ユーティリティ
  - ログ設定（コンソール + 日次ローテートファイル）
  - プロセス優先度 / CPU affinity 設定
  - Paper trading 検証レポート生成ツール

前提（依存関係）
- Python 3.10+（型注釈等に依存）
- 実行時に必要な外部パッケージ（一部は optional）:
  - duckdb
  - psutil
  - openai（AI 機能を使う場合）
  - PyYAML（validate_config の YAML 検証に利用、未インストールでも実行は可能）
- SQLite 標準ライブラリは組み込み

（例）インストール
- 仮想環境作成・有効化
  - python -m venv .venv
  - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
- 必要パッケージのインストール（requirements.txt がある場合はそちらを利用）
  - pip install duckdb psutil openai PyYAML

セットアップ手順
1. リポジトリをクローンして作業ディレクトリへ移動
2. 仮想環境を作成して有効化
3. 必要パッケージをインストール（上記参照）
4. .env の作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - あるいは手動でプロジェクトルートに .env を作成（重要な環境変数は下記参照）
5. 設定検証:
   - python -m kabusys.validate_config
   - 警告も失敗にしたい場合: python -m kabusys.validate_config --strict
6. データディレクトリ/ログディレクトリの確認
   - デフォルト DB: data/monitoring.db（Monitoring）、data/kabusys.duckdb（DuckDB）、data/paper_trading.db（Paper Trading）
   - ログ: logs/<app_name>.log（デフォルト）

重要な環境変数（要/任意）
- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
  - KABU_API_PASSWORD — kabuステーション API パスワード
- 選択 / 推奨
  - KABUSYS_ENV — 実行環境: development | paper_trading | live （デフォルト: development）
    - paper_trading: MockBroker を使い paper_db に記録
    - live: 本番（実発注）
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — SQLite (monitoring) パス（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
  - LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
  - LOG_DIR — ログ出力先ディレクトリ（デフォルト: logs）
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — LINE 通知設定（任意）
  - OPENAI_API_KEY — OpenAI を利用する機能（news_nlp, regime_detector）で必須
  - MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒、run_monitoring で使用、デフォルト 60）
  - PAPER_FILL_MODE — Paper Trading の約定モード: instant | partial | never | reject（デフォルト: instant）
  - KILL_FLAG_CLEAR_ON_START — ExecutionEngine 起動時に kill.flag を自動クリアするか（0/1）

簡易 .env 例（テンプレート）
- .env.example を参考に作成してください。最低限必須は JQUANTS_REFRESH_TOKEN と KABU_API_PASSWORD。

使い方（実行例）
- 設定ウィザード（対話式）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
- ExecutionEngine を起動（発注エンジン）
  - python -m kabusys.run_execution
  - メインは ExecutionEngine.run_session を別スレッドで実行し、stop フラグ（data/stop_requested.flag）や data/kill.flag によって停止を制御します。
  - KABUSYS_ENV=paper_trading を設定すると、MockBrokerClient が使われ paper_trading DB（デフォルト data/paper_trading.db）に記録されます。
- Monitoring（監視ループ）を起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）
  - 監視は常に本番 sqlite_path（SQLITE_PATH）を使用します（環境に依らず）
- Paper Trading 検証レポート出力
  - python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD
  - オプション --db で SQLite ファイルパスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH でも指定可）
- AI 系（ニューススコア / レジーム判定）
  - kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime を呼び出す。OpenAI API キーが必要（OPENAI_API_KEY）。

ログ & 運用メモ
- ログは stdout と logs/<app_name>.log（日次ローテート、30日保持）に出力されます。
- ログディレクトリ作成に失敗した場合はファイル出力をスキップして stdout のみで動作します（警告出力あり）。
- デーモン運用する場合、PID ファイル（デフォルト data/execution.pid）やフラグファイル（data/kill.flag, data/stop_requested.flag）を運用方針に合わせて管理してください。
- Process priority 設定（起動時に high に設定）および CPU affinity の設定ユーティリティがありますが、権限不足などでスキップすることがあります。

主要コンポーネント（簡単な説明）
- kabusys.config
  - Settings クラスで環境変数をラップして提供。自動的に .env を読み込む仕組みあり（プロジェクトルートが見つからない場合はスキップ可能）。
- kabusys.run_execution
  - ExecutionEngine の起動スクリプト。paper_trading モード時は専用 DB を使用。
- kabusys.run_monitoring
  - SystemMonitor を中心としたポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL で間隔変更可能。
- kabusys.monitoring
  - monitoring_db: SQLite テーブルの初期化・読み書きラッパー
  - system_monitor / trade_monitor / risk_monitor / monitoring_engine / kill_switch / alert_manager 等
- kabusys.execution
  - ブローカークライアント生成、ExecutionEngine、OrderManager、OrderRepository、Reconciler、RiskManager（詳細は execution パッケージ内）
- kabusys.portfolio
  - ポートフォリオ選定・重み算出・リスク補正・サイズ計算の純粋関数群
- kabusys.research
  - ファクター計算（momentum/value/volatility）、特徴量探索（forward returns / IC / summary）
- kabusys.ai
  - news_nlp: ニュースを LLM でスコア化して ai_scores に書き込む
  - regime_detector: MA とマクロニュースを組み合わせて市場レジームを判定して DB に書き込む
- kabusys.tools
  - paper_verification_report: Paper Trading の検証レポート生成
- kabusys.utils
  - logging_setup: 統一ログ設定
  - process_priority: OS 横断でプロセス優先度 / affinity 設定

ディレクトリ構成（主要ファイル抜粋）
- src/kabusys/
  - __init__.py
  - config.py
  - config_setup.py
  - validate_config.py
  - run_execution.py
  - run_monitoring.py
  - execution/
    - (ExecutionEngine, broker_factory, order_manager, order_repository, reconciler, risk_manager, ...)
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
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
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - data/ (実行時に作成されることが多い)
    - monitoring.db (デフォルト)
    - paper_trading.db (paper_trading モード)
    - kill.flag / stop_requested.flag / execution.pid など

運用上の注意（要点）
- 本番（KABUSYS_ENV=live）では設定ミスが致命的になり得るため validate_config の実行を強く推奨します。
- kill.flag / stop_requested.flag による停止は冪等であり意図しない消去（KILL_FLAG_CLEAR_ON_START=1）には注意してください（本番では 0 推奨）。
- OpenAI API を使用する処理は外部通信を伴い課金が発生するため、API キーとコール回数の管理に注意してください。
- Paper trading では本番 DB と完全に分離されるよう設計されています（PAPER_TRADING_SQLITE_PATH を確認してください）。

ライセンス / バージョン
- パッケージバージョン: src/kabusys/__init__.py の __version__ = "0.1.0"
- ライセンス情報はリポジトリ内の LICENSE ファイルを参照してください（存在する場合）。

---

追加サポート
- どの機能をどう運用したいか（例: デプロイ手順、systemd ユニット、Docker 化、CI テスト設計など）を教えていただければ、README を運用手順付きに拡張できます。