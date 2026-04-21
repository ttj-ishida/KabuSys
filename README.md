KabuSys — 日本株自動売買システム（README）
======================================

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤です。本リポジトリは以下の主要機能を含みます。

- 発注エンジン（ExecutionEngine）：ブローカークライアント経由で発注管理・リスク管理を行う。paper_trading モードでは MockBrokerClient を使用し、本番 DB と分離された専用 SQLite に記録します。
- 監視（Monitoring）：システム健全性、注文ログ、リスク（ドローダウン・ポジション上限）を監視し、Kill Switch（停止フラグ）やアラートを発行します。
- ポートフォリオ構築：候補選定、重み付け、リスク調整、株数算出（単元株丸め）など純粋関数群を提供します。
- リサーチ：DuckDB 上の時系列データからファクター（モメンタム／バリュー／ボラティリティ等）や特徴量解析を行うモジュール。
- AI モジュール：OpenAI（gpt-4o-mini）を用いたニュース NLP による銘柄センチメント算出、マーケットレジーム判定。
- 運用ユーティリティ：ログ設定、プロセス優先度設定、設定ウィザード・検証 CLI、ペーパートレード検証レポートなど。

機能一覧
--------
主なコンポーネントと提供機能（抜粋）:

- run_execution.py
  - ExecutionEngine の起動スクリプト
  - KABUSYS_ENV=paper_trading の場合は専用 SQLite (data/paper_trading.db) を使用
  - 停止フラグ（data/stop_requested.flag）や PID ファイル (data/execution.pid) を使用した制御

- run_monitoring.py
  - SystemMonitor のポーリングループ起動（デフォルト 60 秒、環境変数 MONITOR_POLL_INTERVAL で上書き可）
  - 監視ログは本番 sqlite_path を常に使用

- monitoring/
  - monitoring_db.py: SQLite による永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py: CPU/メモリ/ディスク/プロセス/データ鮮度の監視
  - risk_monitor.py: ドローダウン・ポジション上限監視とイベントログ記録
  - kill_switch.py: data/kill.flag を作成して ExecutionEngine に停止シグナルを送るロジック
  - monitoring_engine.py: 各 Monitor を束ねてポーリング・アラート/kill 判定を実行

- portfolio/
  - portfolio_builder.py: 候補選定・重み計算（等配分・スコア加重）
  - position_sizing.py: 株数決定（risk_based / equal / score）、単元株丸め、aggregate cap スケーリング
  - risk_adjustment.py: セクターキャップ、レジーム乗数

- research/
  - factor_research.py: momentum/value/volatility の計算（DuckDB 上で実行）
  - feature_exploration.py: 将来リターン、IC、統計サマリ等

- ai/
  - news_nlp.py: raw_news を LLM でセンチメントスコア化して ai_scores に書き込み
  - regime_detector.py: ETF (1321) の MA200 等とマクロニュースセンチメントを合成して市場レジーム判定

- utils/
  - logging_setup.py: 一貫したログ設定（stdout + 日次ローテートファイル）
  - process_priority.py: クロスプラットフォームでプロセス優先度 / CPU affinity を設定

- tools/
  - paper_verification_report.py: ペーパートレード実績の検証レポート生成 CLI

セットアップ手順
----------------
前提
- Python 3.10+（typing の | 演算子等を使用）
- systemwide: SQLite は標準ライブラリで OK
- 必要な Python パッケージ（例）
  - duckdb
  - psutil
  - openai（AI 機能を使う場合）
  - PyYAML（config 検証を行う場合に推奨）

例（venv を使ったセットアップ）
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール（例）
   - pip install duckdb psutil openai PyYAML

3. 初期設定（.env）
   - 対話式ウィザードで .env を作成:
     - python -m kabusys.config_setup
   - もしくは .env を手動作成（.env.example を参照）.
   - 重要な必須環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
   - AI 機能を使う場合:
     - OPENAI_API_KEY を設定

4. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit(1)）

5. ディレクトリ作成（必要に応じて）
   - data/ と logs/ は通常スクリプトが自動作成しますが、権限等で問題がある場合は手動で作成してください。

主要な環境変数（代表）
- KABUSYS_ENV: development | paper_trading | live（デフォルト development）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（paper_trading 時の専用 DB）
- LOG_LEVEL: ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL）
- OPENAI_API_KEY: OpenAI API キー（AI 機能で必須）
- PAPER_FILL_MODE: paper_trading の約定挙動（instant|partial|never|reject）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- LOG_DIR: ログ保存ディレクトリ（デフォルト logs/）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START: 停止制御関連

使い方
------
起動スクリプト（例）
- 監視ループ起動（バックグラウンドで実行する場合はプロセスマネージャで実行）
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変える: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- ExecutionEngine 起動
  - python -m kabusys.run_execution
  - paper_trading モードで起動する場合は KABUSYS_ENV=paper_trading を指定するか .env で設定

- 設定ウィザード（.env 生成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を別パスで指定: python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

- AI モジュール（スクリプトまたはインタラクティブで呼び出し）
  - ニュース NLP（例、Python スクリプト内）:
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news
    conn = duckdb.connect('data/kabusys.duckdb')
    score_news(conn, target_date=date(2026,4,10), api_key='YOUR_OPENAI_KEY')

  - レジーム判定:
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date=date(2026,4,10), api_key='YOUR_OPENAI_KEY')

停止・制御
- run_execution/run_monitoring はプロジェクトルートの data/stop_requested.flag を使って優雅に停止できます（該当ファイルを作成するとループが検出して終了）。
- Execution の強制停止（運用停止）用に kill.flag を使う KillSwitch があります（kill.flag を書くと ExecutionEngine に停止シグナルを送る設計）。
- PID ファイル: data/execution.pid（run_execution が使用）。運用ツールからプロセス参照に利用します。
- KILL_FLAG_CLEAR_ON_START 環境変数が 1 の場合、ExecutionEngine 起動時に kill.flag を自動でクリアします（本番では 0 推奨）。

ディレクトリ構成
----------------
（主要ファイルのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                    — 環境変数 / 設定ロード・Settings
    - config_setup.py              — .env 対話式ウィザード
    - validate_config.py           — 設定検証 CLI
    - run_execution.py             — ExecutionEngine 起動スクリプト
    - run_monitoring.py            — SystemMonitor 起動スクリプト
    - tools/
      - paper_verification_report.py
    - utils/
      - logging_setup.py
      - process_priority.py
    - monitoring/
      - monitoring_db.py
      - system_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - monitoring_engine.py
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
    - execution/                    — 発注関連の実装（BrokerFactory, ExecutionEngine 等）
    - data/                         — （ランタイムで生成される）data/monitoring.db, data/paper_trading.db など
    - logs/                         — デフォルトのログ出力先

開発・運用上の注意
-----------------
- .env は機密情報を含むため絶対に VCS にコミットしないでください（config_setup.py のヘッダにも注意書きがあります）。
- production (KABUSYS_ENV=live) の場合は特に LINE 通知や kill flag の設定を慎重に行ってください（validate_config は本番時のガードチェックを含みます）。
- AI 機能を使う場合は OpenAI のコストやレートリミットに注意してください。news_nlp と regime_detector はリトライ/バックオフや部分失敗時のフォールバックを備えていますが、運用時には API キーや呼び出し頻度を管理してください。
- run_monitoring は MONITOR_POLL_INTERVAL 環境変数でインターバルを変更できます。値が不正（0 以下・非整数）の場合はデフォルト 60 秒にフォールバックします。

トラブルシュート（よくある項目）
--------------------------------
- ログが出ない / ファイルローテートできない
  - 権限や LOG_DIR 設定を確認。ディレクトリ作成に失敗するとコンソールのみ出力になります。
- Execution がすぐ停止する
  - data/stop_requested.flag や data/kill.flag が存在していないか確認してください。KILL_FLAG_CLEAR_ON_START 設定の影響も確認。
- DB（DuckDB/SQLite）接続エラー
  - パスに対するファイル権限、あるいは DUCKDB_PATH / SQLITE_PATH の設定ミスを確認してください。
- AI 呼び出しエラー
  - OPENAI_API_KEY の有無、ネットワーク、パッケージバージョンを確認してください。

ライセンス / バージョン
------------------------
- パッケージバージョンは kabusys.__version__ = "0.1.0"
- ライセンス情報はリポジトリのトップレベルに含めてください（本 README には記載していません）。

最後に
------
この README はコードベースのソースを基に作成した概要ドキュメントです。各モジュールにはより詳細な docstring / コメントが含まれているため、実装の詳細や追加オプションは該当ファイルを参照してください。質問や追加のドキュメント出力（例: API 使用例、運用 Runbook、設計ドキュメント）を希望される場合は教えてください。