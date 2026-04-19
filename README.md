KabuSys — 日本株自動売買システム
================================

このリポジトリは日本株向けの自動売買／研究／監視ユーティリティ群を含むパッケージです。
本READMEはコードベース（src/kabusys 配下）をもとに導入・実行方法、主要機能、
ディレクトリ構成の概要を日本語でまとめたものです。

前提
----
- Python 3.10+（ファイル内で「|」型ヒント等を使用しているため）
- 基本的な外部依存例（環境によって追加が必要）:
  - duckdb
  - psutil
  - openai（AI モジュールを使う場合）
  - PyYAML（config 検証で YAML 内容チェックを行う場合）
- データ・ログ等はリポジトリルートの data/ と logs/ に配置される想定

プロジェクト概要
---------------
KabuSys は、以下の主要領域を持つモジュール群で構成されています。

- execution: 発注エンジン、注文管理、リスク管理等の実運用ロジック（ExecutionEngine 等）
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を用い、本番 DB と分離して data/paper_trading.db に記録
- monitoring: システム状態・注文状況・リスク監視、Kill Switch（停止フラグ）やアラート連係
  - 監視は本番 sqlite_path を環境に関わらず使用する設計の部分あり
- portfolio: 銘柄選定、重み付け、ポジションサイズ決定、セクター制約などの純粋関数群
- research: DuckDB を用いたファクター計算、将来リターン・IC 計算等の研究用モジュール
- ai: ニュース NLP / レジーム判定など、OpenAI API を使った補助機能
- tools: ペーパートレードの検証レポート生成など CLI ツール
- utils: ログ設定、プロセス優先度設定などのユーティリティ

主な機能一覧
-------------
- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動（スレッドで実行 / stop フラグで終了）
  - run_monitoring.py: SystemMonitor のポーリングループを起動（MONITOR_POLL_INTERVAL で間隔指定可）
- 設定管理
  - config_setup.py: 対話式ウィザードで .env を生成／更新
  - validate_config.py: .env や config/*.yaml の事前検証（--strict で警告も FAIL 扱い）
- 監視
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine（ポーリング・アラート連動）
  - KillSwitch: 条件により data/kill.flag を書いて ExecutionEngine を停止
  - MonitoringDB: SQLite を使った監視ログ永続化（テーブル作成は冪等）
- 取引関連
  - OrderRepository / OrderManager / RiskManager / Reconciler など（実装は execution 以下）
  - Paper Trading：paper_trading 用の専用 SQLite DB（data/paper_trading.db）
- 研究 / ツール
  - research.calc_momentum / calc_volatility / calc_value 等（DuckDB 接続を受ける）
  - tools.paper_verification_report: Paper Trading の性能レポートを生成（稼働率・約定率・レイテンシ等）
- AI 支援
  - ai.news_nlp.score_news: raw_news を OpenAI に送って銘柄ごとのスコアを ai_scores テーブルに保存
  - ai.regime_detector.score_regime: ETF の MA とマクロニュースを組み合わせて market_regime を決定

セットアップ手順
----------------
1. リポジトリをクローンして作業ディレクトリをプロジェクトルートに移動する。

2. Python 仮想環境を作成・有効化（例: venv）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - 代表的なパッケージ:
     - pip install duckdb psutil openai PyYAML
   - 実際には requirements.txt を用意している場合はそれを利用してください（本コードベースでは仮定例）。

4. データ・ログディレクトリ準備（多くのコードが自動作成しますが事前に作ると権限エラーを防げます）
   - mkdir -p data logs

5. .env の準備
   - 対話的に作る: python -m kabusys.config_setup
     - J-Quants トークン、kabu API パスワード、KABUSYS_ENV などを入力
   - もしくは手動で .env を作成（.env.example を参考に）

6. 設定検証（必須項目が揃っているか確認）
   - python -m kabusys.validate_config
   - 警告も厳格に扱いたい場合は --strict を付ける

注意: OpenAI を用いる機能（ai モジュール）を使う場合は OPENAI_API_KEY を環境変数に設定してください（または関数呼び出し時に渡す）。

使い方（主要スクリプト）
-----------------------

- 環境変数の基本
  - 主要な環境変数（.env に設定）
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
    - SQLITE_PATH（デフォルト: data/monitoring.db）
    - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB）
    - LOG_LEVEL（デフォルト: INFO）
    - OPENAI_API_KEY（AI 機能を使う場合）
    - MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔 秒、デフォルト 60）

- 実行エンジン（ExecutionEngine）を起動
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い paper_trading 用 DB を使用
    - 起動時に data/stop_requested.flag がある場合は起動しない
    - 実行中に data/stop_requested.flag を作成するとエンジン停止をリクエスト
    - PID ファイル: data/execution.pid（設定で変更可能）

- 監視ループを起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可（例: MONITOR_POLL_INTERVAL=30）
  - 監視は monitoring DB（Settings.sqlite_path）にログを保存（環境にかかわらず本番 sqlite_path を使用）
  - 停止はプロジェクトルート/data/stop_requested.flag を作成することでループを終了

- 設定ウィザード
  - python -m kabusys.config_setup
  - .env を対話式に作成・更新します（生成後は python -m kabusys.validate_config で検証を推奨）

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い（exit 1）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db
  - 出力: 稼働率、注文成功率、送信率、P95 レイテンシなど。合否判定（PASS/FAIL）を表示

- AI モジュール（プログラムから使用）
  - news scoring:
    - from kabusys.ai import score_news
    - score_news(conn, target_date, api_key=None)  — DuckDB 接続と target_date を渡す
    - api_key を None にすると環境変数 OPENAI_API_KEY を参照
  - regime detector:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key=None)

ログとローテーション
-------------------
- ログはデフォルトで logs/ に出力され、アプリ名ごとに日次ローテーションされます（logs/<app_name>.log）。
- setup_logging() を各起動スクリプトが呼び出して統一的に設定している（stdout とファイルを同時出力）。

停止・Kill Switch
-----------------
- Graceful stop:
  - run_monitoring/run_execution はプロジェクトルート/data/stop_requested.flag の存在を監視して正常終了する設計。
- Kill Switch:
  - リスク条件（ドローダウン閾値、ポジション数超過など）を満たすと monitoring 側で data/kill.flag を生成し、ExecutionEngine 側で停止判定に使うことができる。
  - Settings.kill_flag_clear_on_start=1 を設定すると起動時に kill.flag を自動クリアする（本番では 0 推奨）。

設定ファイル（config/*.yaml）
----------------------------
- config ディレクトリ下に各種 YAML 設定ファイルが想定されています（system_config.yaml、data_config.yaml、strategy_config.yaml、risk_config.yaml、execution_config.yaml、monitoring_config.yaml）。
- validate_config はこれらのファイルの存在と（PyYAML がインストールされている場合）パースをチェックします。

ディレクトリ構成（主要ファイル）
------------------------------
以下は src/kabusys 配下の主要なファイル／モジュール構成（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py (参照あり)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - data/ (実行時に作成される想定)
  - logs/ (ログ保存先)

補足 / 実運用上の注意
--------------------
- 環境変数の自動ロード:
  - config.py はプロジェクトルートに .env / .env.local があれば自動でロードします（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
- DB 分離:
  - Execution の paper_trading モードは paper_sqlite_path を使い、本番監視 DB は Monitoring で共通に使う点に注意してください（run_monitoring は環境にかかわらず Settings.sqlite_path を使います）。
- 権限・ファイル I/O:
  - logs/ や data/ を作成するための権限が必要です。Docker や systemd などで運用する際は適切な権限設定を行ってください。
- OpenAI API:
  - ai モジュールは外部 API 呼び出しを行います。API のエラーやレート制限に対するリトライ実装はありますが、キーと課金・利用規約に注意してください。

よく使うコマンドまとめ
---------------------
- .env を作成:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- 監視起動:
  - MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
- 実行エンジン起動:
  - python -m kabusys.run_execution
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

ライセンス・貢献
----------------
- 本 README ではライセンス情報を含めていません。実プロジェクトでは LICENSE ファイルを追加してください。
- 開発・テストの際は .env を絶対に Git にコミットしないでください（config_setup でも注意書きあり）。

問い合わせ / 開発メモ
-------------------
- 開発者向け: 各モジュールは可能な限り副作用を排した純粋関数（portfolio など）と、DB/外部 API を扱う I/O 部分（ai、monitoring_db など）を分離しています。テストが書きやすい設計を意図しています。
- 不明点や追加の README 要望があれば、利用ケース（ローカル開発 / Docker / systemd での運用等）を教えてください。運用手順や systemd ユニット例などを追記できます。