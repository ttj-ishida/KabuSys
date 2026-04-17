README
======

概要
----
KabuSys は日本株向けの自動売買／リサーチ基盤の骨組みです。  
主な責務は以下の通りです。

- 注文発行・注文管理を行う ExecutionEngine（実運用 / ペーパートレード対応）
- システム稼働状況・注文状況・リスク指標を監視する Monitoring
- ポートフォリオ構築・ポジションサイジング・セクター制約等の純粋関数群（研究・本番で共通）
- DuckDB を用いたファクター計算・研究ユーティリティ
- OpenAI（gpt-4o-mini）を用いるニュース NLP / レジーム判定モジュール
- CLI ツール群（.env ウィザード、設定検証、ペーパートレード検証レポート など）

機能一覧
--------
- 実行エンジン（ExecutionEngine）
  - 本番／ペーパートレード切替（KABUSYS_ENV）
  - MockBroker を用いた paper_trading モード（本番 DB と分離して data/paper_trading.db を使用）
  - プロセス優先度設定、PID ファイル管理、停止フラグ読み取り
- 監視（Monitoring）
  - SystemMonitor: CPU / メモリ / ディスク / データ鮮度 / 実行プロセスチェック
  - TradeMonitor: 滞留注文、約定価格異常検知
  - RiskMonitor: ドローダウン・ポジション上限監視、ダッシュボード更新
  - AlertManager: LINE Messaging API 経由の通知（設定がある場合）
  - KillSwitch: 条件により data/kill.flag を書き込み ExecutionEngine を停止
- ポートフォリオ（pure functions）
  - 候補選定、等配分・スコア加重配分、ポジションサイズ算出、セクター上限、レジーム乗数
- 研究 / データ処理
  - DuckDB ベースのファクター計算（モメンタム、ボラティリティ、バリュー等）
  - 将来リターン、IC 計算、ファクター統計概要
- AI（OpenAI）
  - news_nlp: 生のニュースを集約して LLM に投げ、銘柄別センチメントを ai_scores に書込む
  - regime_detector: ETF の MA200 とマクロニュースセンチメントを合成して market_regime を算出
- ツール
  - .env 対話ウィザード（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）
  - Paper Trading 検証レポート生成（kabusys.tools.paper_verification_report）

セットアップ手順
----------------
1. レポジトリをクローン
   - git clone ... (適宜)

2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール（代表的な依存）
   - pip install duckdb psutil requests openai
   - 開発用途で YAML チェックを使う場合: pip install PyYAML
   - プロジェクトに requirements.txt があればそれを使ってください。

4. .env を作成
   - 対話式ウィザード: python -m kabusys.config_setup
   - もしくは .env.example（存在する場合）を参考に手動で作成
   - 重要な必須環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV（development / paper_trading / live） — デフォルト development
     - OPENAI_API_KEY（AI 機能を使う場合）
     - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH（監視用デフォルト data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用デフォルト data/paper_trading.db）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（通知を有効にする場合）

5. 設定検証（起動前のチェック）
   - python -m kabusys.validate_config
   - 警告をエラー扱いにしたい場合: python -m kabusys.validate_config --strict

6. データディレクトリ準備（必要なら）
   - デフォルトでは data/ 以下に DB・PID・フラグ等を作成します。書き込み権限を確認してください。

使い方
------
- ExecutionEngine の起動（本番または設定された KABUSYS_ENV に従う）
  - python -m kabusys.run_execution
  - 特記事項:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い data/paper_trading.db に記録します（本番 DB と分離）。
    - 実行中は data/execution.pid に PID を書きます。停止には kill.flag/stop_requested.flag を利用できます。
    - 自動的にプロセス優先度を "high" に設定しようとします（権限不足だと警告）。

- Monitoring の起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60）
  - 監視は常に本番用の sqlite_path に対して行います（KABUSYS_ENV に関わらず）

- 停止方法
  - 優雅に停止させるにはプロジェクトルートの data/stop_requested.flag を作成してください（run_* スクリプトで検知して終了します）。
  - 実運用での自動停止条件は KillSwitch により data/kill.flag が書き込まれることがあります。KILL_FLAG_CLEAR_ON_START=1 により起動時に自動クリアできますが、本番では 0 を推奨します。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間を指定: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を指定: --db PATH （環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- AI 機能（スクリプト呼び出し例）
  - news_nlp.score_news を直接呼び出して実行できます（DuckDB 接続と target_date を渡す）。
  - regime_detector.score_regime も同様に呼び出して market_regime を更新します。
  - これらを CLI として実行する簡易ラッパーは用意されていないため、スクリプトや cron・ジョブから Python API を呼んでください。

主要な環境変数（抜粋）
--------------------
- KABUSYS_ENV: development | paper_trading | live（default: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（default: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（AI 機能用）
- DUCKDB_PATH: DuckDB ファイルパス（default: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（default: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 DB（default: data/paper_trading.db）
- PID_FILE_PATH: 実行エンジン PID ファイル（default: data/execution.pid）
- KILL_FLAG_PATH: kill.flag パス（default: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（"1" でクリア）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、default: 60）
- PAPER_FILL_MODE: paper_trading の約定挙動（instant | partial | never | reject）

ディレクトリ構成
----------------
（src/kabusys 以下を中心に抜粋）

- src/kabusys/
  - __init__.py
  - config.py               — 環境変数・.env 自動読み込みロジック、Settings クラス
  - config_setup.py         — .env 対話ウィザード CLI
  - validate_config.py      — 起動前設定検証 CLI
  - run_execution.py        — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成 CLI
  - execution/              — 実行エンジン関連（BrokerFactory, Engine, OrderManager, Reconciler, RiskManager 等）
  - monitoring/
    - monitoring_db.py      — SQLite schema + 永続化 API
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - alert_manager.py
    - kill_switch.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py           — ニュース NLP（OpenAI）
    - regime_detector.py    — レジーム判定（OpenAI）
  - data/ (runtime)
    - monitoring.db         — デフォルト監視 SQLite DB
    - paper_trading.db      — paper_trading 用 DB（存在する場合）
    - kabusys.duckdb        — DuckDB（デフォルト path）
    - execution.pid         — 実行エンジン PID（起動時作成）
    - kill.flag / stop_requested.flag — フラグファイル（停止 / キル条件）

注意事項 / 運用上のヒント
------------------------
- 本番モード（KABUSYS_ENV=live）では kill フラグや設定値を慎重に扱ってください。validate_config は live 時に追加警告を出します。
- ペーパートレードは実 DB と分離されますが、code の整合性やログ収集のため DB のバックアップ/管理を推奨します。
- OpenAI API を利用するワークフローは外部 API 呼び出しに依存するため、レート制限やエラー時のフォールバック（ログ出力・スキップ）を設計に組み込んであります。API キー管理に注意してください。
- プロセス優先度設定や CPU affinity は psutil を利用します。権限によっては設定に失敗する場合があり、その場合は警告が出ますが処理自体は継続します。

貢献
----
バグ報告・機能提案は GitHub issue を利用してください。プルリクは歓迎します。コードの様式は既存のモジュールに倣ってください。

ライセンス
----------
プロジェクトに同梱されている LICENSE を参照してください（本リポジトリには未添付の場合がありますので追加を検討してください）。

------------------------
この README はソースコード（src/kabusys/*.py）からの情報に基づき作成しました。環境や実際の配布パッケージに合わせてパスやコマンドを調整してください。