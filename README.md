README
======

概要
----
KabuSys は日本株向けの自動売買システム（研究→シグナル→ポートフォリオ構築→発注→監視）向けの Python パッケージ群です。本リポジトリは以下の主要機能を持ちます。

- バックテスト/リサーチ用のファクター計算（DuckDB ベース）
- ポートフォリオ構築（候補選定・重み付け・株数決定）
- ExecutionEngine（発注エンジン）と Broker クライアントの抽象化（paper/live 切替）
- 監視コンポーネント（System / Trade / Risk）と Kill Switch
- AI 補助モジュール（ニュース NLP によるセンチメント、レジーム判定）
- 運用支援ツール（.env ウィザード、設定検証、Paper Trading レポート生成）

機能一覧
--------
主な機能の要約：

- execution
  - ExecutionEngine 起動スクリプト（python -m kabusys.run_execution）
  - BrokerClientFactory による paper_trading / live の切替
  - 発注履歴・position の永続化（SQLite）

- monitoring
  - SystemMonitor：CPU/Mem/Disk、データ鮮度、プロセス存否チェック
  - TradeMonitor / RiskMonitor：滞留注文・約定異常・ドローダウン監視
  - MonitoringEngine：各 Monitor を束ねるポーリングループ
  - KillSwitch：条件に応じた停止フラグ書き込み（data/kill.flag）

- research
  - ファクター計算（モメンタム・ボラティリティ・バリュー等）
  - 将来リターン計算、IC（Information Coefficient）、ファクター統計

- portfolio
  - 候補選定、等重/スコア重み、ポジションサイズ計算、セクターキャップ適用

- ai
  - news_nlp.score_news：OpenAI を使った銘柄別ニュースセンチメントの算出・DB 書込み
  - regime_detector.score_regime：ETF とマクロニュースを合成した市場レジーム判定

- tools
  - config_setup ウィザード（.env 生成/更新）
  - validate_config（環境/設定検証）
  - paper_verification_report（Paper Trading の検証レポート生成）

要求事項 / 依存パッケージ
-----------------------
推奨 Python バージョン: 3.10+

主要依存（代表）:
- duckdb
- psutil
- openai (AI 機能利用時)
- PyYAML（config/*.yaml の内容検証に任意で使用）
- sqlite3（標準ライブラリ）

※ 実際の開発環境では requirements.txt を用意して pip install してください（本リポジトリに要求ファイルがない場合は上記パッケージを個別にインストール）。

セットアップ手順
--------------
1. リポジトリ取得
   - git clone <repo-url>
   - cd <repo-root>

2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージインストール
   - pip install duckdb psutil openai pyyaml

4. .env の作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
     - ウィザードで J-Quants トークンや kabuAPI パスワード等を設定して .env を生成します。
   - もしくは .env を手動で作成（.env.example を参照）

5. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱いになります。

6. データディレクトリ確認
   - デフォルトの SQLite / DuckDB ファイルは data/ 配下に置かれます。必要に応じて .env で上書きしてください。

主要な環境変数（抜粋）
---------------------
必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

運用関連:
- KABUSYS_ENV: environment。値は development / paper_trading / live（デフォルト: development）
  - paper_trading: MockBroker を使用し paper DB（data/paper_trading.db）へ記録
  - live: 本番発注を行います（注意）
- OPENAI_API_KEY: AI 機能（news_nlp / regime_detector）で必要
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 sqlite（デフォルト data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...、デフォルト INFO）
- PAPER_FILL_MODE: paper_trading の注文執行モード（instant/partial/never/reject、デフォルト instant）
- KILL_FLAG_CLEAR_ON_START: ExecutionEngine 起動時に kill.flag を自動削除するか（0/1、デフォルト 0）

ランタイム制御関連:
- MONITOR_POLL_INTERVAL: monitoring ポーリング間隔（秒、デフォルト 60）
- data/kill.flag: KillSwitch により書き込まれる停止フラグ
- data/stop_requested.flag: run_monitoring/run_execution の外部停止トリガー（存在するとループを抜けます）
- data/execution.pid: ExecutionEngine の PID ファイル（起動時に作成されます）

使い方
------

. 簡単な起動例
- 実行エンジン起動（paper_trading もしくは live は .env の KABUSYS_ENV に依存）
  - python -m kabusys.run_execution

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数で秒数を上書き可能（例: MONITOR_POLL_INTERVAL=30）

. 設定ウィザード / 検証
- 対話式で .env を作る:
  - python -m kabusys.config_setup
- 起動前の構成チェック:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

. Paper Trading 検証レポート
- デフォルトの paper DB（data/paper_trading.db）を使う:
  - python -m kabusys.tools.paper_verification_report
- 期間指定:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- DB を明示する:
  - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

. AI 機能（プログラム的利用）
- ニューススコアを算出して DB に書き込む:
  - from kabusys.ai.news_nlp import score_news
  - score_news(conn, target_date, api_key="YOUR_OPENAI_KEY")
- レジーム判定:
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(conn, target_date, api_key="YOUR_OPENAI_KEY")

停止と制御
----------
- 外部から実行を停止したい場合は data/stop_requested.flag を作成すると run_monitoring / run_execution のループが検出して終了します。
- 運用上の自動停止条件（Kill Switch）が発動すると data/kill.flag が書き込まれ、ExecutionEngine 側で検出され停止します。
- ExecutionEngine の PID は data/execution.pid に保存されます。

開発者向け注記
----------------
- ロギングは kabusys.utils.logging_setup.setup_logging を各起動スクリプトが呼び出します。logs/ に日次ローテートで出力します（デフォルト）。
- プロセス優先度は起動時に High に設定されます（psutil を使用。権限によって無視されることがあります）。
- monitoring/monitoring_db.init_monitoring_db は起動時に必要なテーブル・マイグレーションを冪等に作成します。

ディレクトリ構成
----------------
（主要ファイル / モジュールのサンプルツリーと説明）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数の自動読み込み、Settings クラス
  - config_setup.py
    - .env を対話的に作成するウィザード
  - validate_config.py
    - 起動前チェック CLI
  - run_execution.py
    - ExecutionEngine 起動スクリプト
  - run_monitoring.py
    - SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py
      - Paper Trading レポート生成ツール
  - execution/
    - (ExecutionEngine, BrokerFactory, OrderManager, RiskManager, Reconciler など)
  - monitoring/
    - monitoring_db.py
      - SQLite DB の初期化と永続化用ラッパー
    - system_monitor.py
      - システム状態・データ鮮度監視
    - trade_monitor.py
      - 発注/約定の監視（ソースに依存）
    - risk_monitor.py
      - ドローダウン・ポジション上限監視
    - kill_switch.py
      - 停止フラグ管理
    - monitoring_engine.py
      - 各種 Monitor を統合するエンジン
    - alert_manager.py
      - LINE などへ通知（実装箇所）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - data/
    - pipeline.py (prices の取得・最終日取得等)
  - utils/
    - logging_setup.py
    - process_priority.py
    - __init__.py

ライセンス / 貢献
----------------
- 本リポジトリのライセンス情報や貢献ガイドラインはプロジェクトルートの LICENSE / CONTRIBUTING 等を参照してください（本 README 内には含まれていません）。

補足
----
- 実運用（KABUSYS_ENV=live）では kill_flag 等の設定を慎重に行ってください。validate_config の警告をよく確認してください。
- AI 機能を利用する場合、OpenAI API キーの管理とコスト・レイテンシの評価を事前に行ってください。

以上。必要であれば README に含めるコマンドの具体例や .env.example のテンプレートを追加します。どの情報を追記しますか？