KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株の自動売買・リサーチ・監視を想定した小規模なフレームワークです。本リポジトリには次の主要機能を提供するモジュール群が含まれます。

- 発注エンジン（ExecutionEngine）とブローカークライアントの抽象化（paper/live 切替対応）
- 監視（Monitoring）：システム状態、取引ログ、リスク監視、Kill Switch
- ポートフォリオ構築（候補選定・重み付け・株数決定・セクター制限）
- リサーチ（ファクター計算・将来リターン・IC 等）
- AI 補助モジュール（ニュース NLP によるセンチメント、レジーム判定）
- ユーティリティ（ログ設定、プロセス優先度、設定ウィザード、設定検証、ツール）

主な特徴
--------
- 環境変数/.env ベースの設定管理（config モジュール）
- paper_trading（ペーパートレード）と live（本番）を明確に分離
- DuckDB（時系列・ファクタ計算用）と SQLite（監視／発注ログ用）を併用
- OpenAI API を使ったニュースセンチメントおよびマクロセンチメント評価（任意）
- ログはコンソール + 日次ローテーションファイル（logs/）で管理
- フラグファイルでプロセス間制御（stop/kill）

セットアップ手順
----------------

1. クローン / ソース配置
   - 本リポジトリのルートがプロジェクトルートになります（.git / pyproject.toml により自動検出）。

2. Python 環境
   - Python 3.10+ 推奨。
   - 必要なパッケージをインストール（例）
     - duckdb
     - psutil
     - openai（AI 機能使用時）
     - PyYAML（config 検証で YAML をチェックする場合）
   - 例（pip）:
     pip install duckdb psutil openai pyyaml

3. .env の作成（対話式ウィザード推奨）
   - 次のコマンドで対話式に .env を作成・更新できます:
     python -m kabusys.config_setup
   - 主要な環境変数（必須）:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
   - 主な任意変数:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
     - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
     - OPENAI_API_KEY: OpenAI を使う場合に指定
     - PAPER_FILL_MODE: instant | partial | never | reject（paper_trading 時の約定モード）
     - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag をクリアするか（1=クリア, 0=クリアしない。production は 0 推奨）
     - MONITOR_POLL_INTERVAL: 監視ループの秒間隔（デフォルト: 60）

4. 設定検証
   - 生成した .env と config/*.yaml をチェック:
     python -m kabusys.validate_config
   - --strict を付けると警告も失敗として扱います。

5. 初期ディレクトリ／ファイル
   - data/ ディレクトリや logs/ ディレクトリは起動時自動作成されますが、権限に注意してください。

基本的な使い方
--------------

- Execution（発注エンジン）起動
  - 本番/ペーパーの切替は KABUSYS_ENV で制御します。
  - ペーパートレード時は MockBrokerClient を使い、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録します。
  - 起動:
    python -m kabusys.run_execution

  - 停止:
    - 実行中に data/stop_requested.flag を作成すると、run_execution は検知して終了します。
    - KillSwitch（監視が条件を満たした場合）は data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送ります。

- Monitoring（監視）起動
  - 監視は KABUSYS_ENV に依らず本番 sqlite_path を使用して監視データを格納します。
  - 起動:
    python -m kabusys.run_monitoring
  - モニターポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で秒数を指定（デフォルト 60）。
  - 停止:
    - data/stop_requested.flag を作成すると run_monitoring は終了します。

- 設定ウィザード
  python -m kabusys.config_setup

- 設定検証（起動前チェック）
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- Paper Trading 検証レポート
  - ペーパートレード DB から集計レポートを出力します。
  - 例:
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: data/paper_trading.db（--db で指定可）
  - 判定基準（ソース内定数）:
    - 稼働率 >= 99%
    - 注文成功率 >= 90%
    - 送信率 >= 95%
    - P95 レイテンシ <= 200 ms

注意点 / 動作方針
-----------------
- ペーパートレードと本番は DB を明確に分離しています（paper_trading は専用 SQLite）。
- モジュールの多くは外部状態（現在時刻や将来データ）を直接参照しないよう設計され、ルックアヘッドバイアス対策が施されています（target_date を引数で与える等）。
- OpenAI（ニュース NLP / レジーム判定）を使う機能は API キーが必要です（OPENAI_API_KEY 環境変数または関数引数）。
- ロギングは kabusys.utils.logging_setup.setup_logging を介して統一的に設定されます。ログは stdout と logs/<app_name>.log（日次ローテーション）に出力されます。
- プロセス優先度や CPU affinity は kabusys.utils.process_priority で制御します（psutil が必要）。

主なファイルとディレクトリ構成
------------------------------

- src/
  - kabusys/
    - __init__.py
    - config.py
      - 環境変数の読み込み・検証ロジック（自動 .env ロード機能含む）
    - config_setup.py
      - .env を対話式に生成・更新するウィザード
    - validate_config.py
      - 起動前の設定検証 CLI
    - run_execution.py
      - ExecutionEngine の起動スクリプト（KABUSYS_ENV による paper/live 切替）
    - run_monitoring.py
      - SystemMonitor のポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL で間隔調整）
    - utils/
      - logging_setup.py
        - ルートロガー設定（stdout + 日次ファイルローテーション）
      - process_priority.py
        - プラットフォーム差分を吸収するプロセス優先度設定ユーティリティ
    - execution/
      - broker_factory.py, execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py
      - 発注ロジック、ブローカー抽象（MockBroker を含む想定）
    - monitoring/
      - monitoring_db.py
        - SQLite に対する永続化（system_status, trade_logs, positions, risk_logs, dashboard 等）
      - system_monitor.py
        - システム状態・データ鮮度チェック
      - trade_monitor.py
        - 発注関連の監視（滞留注文・約定異常など）
      - risk_monitor.py
        - ドローダウン・ポジション上限監視
      - kill_switch.py
        - kill.flag の作成 / 評価
      - alert_manager.py
        - （アラート送信ロジック）
      - monitoring_engine.py
        - 各 Monitor を束ねるエンジン
    - portfolio/
      - portfolio_builder.py
        - 候補選定・等重/スコア重み化
      - position_sizing.py
        - 株数決定（risk_based / equal / score）
      - risk_adjustment.py
        - セクター制限・レジーム乗数
    - research/
      - factor_research.py
        - Momentum / Volatility / Value などのファクター計算（DuckDB 経由）
      - feature_exploration.py
        - 将来リターン算出・IC / 統計サマリー等
    - ai/
      - news_nlp.py
        - raw_news を LLM でスコアリングして ai_scores に書き込む
      - regime_detector.py
        - ETF (1321) の MA とマクロセンチメントを合成して regime を判定
    - tools/
      - paper_verification_report.py
        - Paper Trading の品質検証レポート生成ツール

よく使うコマンドまとめ
---------------------
- .env 対話式作成:
  python -m kabusys.config_setup

- 設定検証:
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- Execution 起動:
  python -m kabusys.run_execution

- Monitoring 起動:
  python -m kabusys.run_monitoring

- Paper Trading レポート:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

運用上の注意
------------
- 本番運用時は KABUSYS_ENV=live、KILL_FLAG_CLEAR_ON_START=0 を強く推奨します。
- .env は絶対にバージョン管理に含めないでください（README 生成ツール等で .env.example を配布してください）。
- OpenAI 利用はコストとレイテンシに注意してください。API エラーはフェイルセーフで扱っているものの運用ポリシーを検討してください。
- 権限が不十分な環境ではログディレクトリ作成やプロセス優先度設定が失敗する場合があります（その場合は WARN ログが出力され、処理は継続します）。

貢献 / 開発メモ
----------------
- DuckDB をローカルで初期化し prices_daily / raw_financials / raw_news 等のテーブルを投入すると、research / ai 機能のローカル検証が可能です。
- unit テストは各純粋関数（portfolio/*.py, research/*.py など）に対して作成しやすい設計を心掛けています（外部 I/O を最小化）。
- LLM 呼び出し部はテスト時にパッチしやすい構造になっています（_call_openai_api の差し替え等）。

ライセンス
---------
（必要に応じてここにライセンス情報を記載してください）

---

この README はコードベースの主要点をまとめたものです。さらに細かい使用方法や設計ドキュメント（PortfolioConstruction.md, StrategyModel.md 等）が別途ある場合は合わせて参照してください。必要なら README の英文版や手順のスクリーンショット、運用手順書を追加します。