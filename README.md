KabuSys
=======

日本株向けの自動売買 / 調査プラットフォームの一部を実装した Python パッケージ群です。
このリポジトリには、実行エンジン起動スクリプト、監視（Monitoring）機能、ポートフォリオ構築ロジック、
リサーチ／ファクター計算、LLM を使ったニュース NLP / レジーム判定などのモジュールが含まれます。

この README はローカルでのセットアップ・起動、主要機能、ディレクトリ構成などの概要をまとめたものです。

前提
----
- Python 3.10 以上（型ヒントに | 演算子を使用）
- SQLite は Python 標準ライブラリで利用
- 外部ライブラリ（用途に応じて必要）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証で任意）
- 推奨: 仮想環境（venv, pipenv, poetry など）を利用してください

主な機能
--------
- 実行エンジン（ExecutionEngine）起動スクリプト（run_execution）
  - 本番 / ペーパートレード切替（KABUSYS_ENV）
  - Paper Trading 時は MockBrokerClient を使い、data/paper_trading.db に記録（本番 DB と分離）
  - プロセス優先度設定・PID ファイル制御・停止フラグ監視
- 監視プロセス起動スクリプト（run_monitoring）
  - SystemMonitor をポーリングして system_status 等を記録
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可（デフォルト 60 秒）
- 監視レイヤ（monitoring）
  - SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch / MonitoringDB
  - ダッシュボード・リスクイベントの記録、Kill Switch（data/kill.flag）書き込み
- ポートフォリオ構築（portfolio）
  - 候補選定、等配分・スコア加重・ポジションサイズ計算（単元株丸め含む）
  - セクター上限適用・レジーム乗数適用
- リサーチ（research）
  - DuckDB を利用したファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC（Information Coefficient）などの統計ユーティリティ
- AI モジュール（ai）
  - news_nlp: OpenAI を用いたニュースセンチメント集約 → ai_scores テーブルへ格納
  - regime_detector: MA200 とマクロニュースの LLM 評価を合成して market_regime を書き込み
- ユーティリティ
  - logging_setup: 統一的なログ設定（コンソール stdout + 日次ローテートファイル）
  - process_priority: プロセス優先度・CPU affinity 設定ユーティリティ
- 開発支援ツール
  - config_setup: 対話式 .env 作成ウィザード
  - validate_config: .env / config/*.yaml の起動前検証 CLI
  - tools/paper_verification_report: ペーパートレード結果から検証レポートを生成

セットアップ手順
----------------

1. リポジトリをクローンして仮想環境を作成
   - 例:
     python -m venv .venv
     source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - 代表的なパッケージ:
     pip install duckdb psutil openai
   - 開発・検証に PyYAML を使う場合:
     pip install PyYAML
   - 必要に応じて requirements.txt / pyproject.toml を用意して管理してください。

3. .env を作成
   - 対話式ウィザードを利用:
     python -m kabusys.config_setup
   - あるいは手動でルートに .env を作成（.env.example を参考に）
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - よく使う環境変数（例）:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト development
     - DUCKDB_PATH — デフォルト data/kabusys.duckdb
     - SQLITE_PATH — デフォルト data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH — Paper 用 DB（paper_trading の場合使用）
     - LOG_LEVEL — DEBUG/INFO/...
     - OPENAI_API_KEY — AI 機能を使う場合必須

4. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いで exit(1)

使い方（起動・各ツール）
-----------------------

- 実行エンジン（ExecutionEngine）起動
  - 本番 / ペーパートレードは KABUSYS_ENV で切替
  - 例（通常起動）:
    python -m kabusys.run_execution
  - 注意:
    - paper_trading の場合は MockBrokerClient が使われ、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録されます。
    - 実行前に data フォルダや DB の親ディレクトリが存在することを確認してください（validate_config が警告します）。
    - プロセスは data/execution.pid を利用します。停止は data/stop_requested.flag / data/kill.flag 等で制御されます。

- 監視プロセス起動
  - 例:
    python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を指定可能（デフォルト 60）
    - 0 以下や非数値は無視され、デフォルトにフォールバックします。
  - 監視は MonitoringDB（SQLite）に system_status, trade_logs, positions, risk_logs, dashboard を永続化します。

- Kill Switch / 停止フラグ
  - KillSwitch は data/kill.flag に理由テキストを書き込みます。ExecutionEngine はこのフラグを検出して停止します。
  - 停止直後に再起動させたくない場合は data/kill.flag を残してください。必要に応じて消去できます（KillSwitch.clear()／手動削除）。

- Paper Trading 検証レポート
  - 例:
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

- AI 機能
  - news_nlp.score_news / regime_detector.score_regime を利用するには OpenAI API キーが必要
  - 例（モジュールとして）:
    from kabusys.ai.news_nlp import score_news
    score_news(conn, target_date, api_key=os.environ["OPENAI_API_KEY"])

ログ
----
- 共通ロギング設定: kabusys.utils.logging_setup.setup_logging
  - コンソール stdout と日次ローテートファイル（logs/<app_name>.log）を設定
  - 環境変数 LOG_DIR でログ保存先を変更可
  - LOG_LEVEL でレベル指定（引数で上書き可）

設定・挙動の注意点
-----------------
- KABUSYS_ENV:
  - development: 開発用（発注なしなど）
  - paper_trading: ペーパートレード（MockBroker を使用し DB を分離）
  - live: 本番（実取引）
- PAPER_FILL_MODE (paper_trading 時)
  - instant | partial | never | reject（デフォルト instant）
- DB パス:
  - duckdb: DUCKDB_PATH（デフォルト data/kabusys.duckdb）
  - monitoring sqlite: SQLITE_PATH（デフォルト data/monitoring.db）
  - paper sqlite: PAPER_TRADING_SQLITE_PATH（paper_trading 用）
- 実行前に validate_config を実行すると、足りない環境変数や不整合を発見できます。
- process_priority.set_process_priority を起動時に呼ぶため、権限不足で優先度設定に失敗しても警告ログを出して継続します。

ディレクトリ構成（主要ファイル）
--------------------------------
src/kabusys/
- __init__.py
- config.py                — 環境変数 / .env 自動ロード・Settings クラス
- config_setup.py          — .env 対話ウィザード
- validate_config.py       — 設定検証 CLI
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — Monitoring 起動スクリプト

- ai/
  - news_nlp.py            — ニュース NLP スコアリング（OpenAI）
  - regime_detector.py     — レジーム判定（MA200 + LLM）
  - __init__.py

- monitoring/
  - monitoring_db.py       — SQLite テーブル定義・Persistent レイヤ
  - system_monitor.py      — システム・データ鮮度監視
  - risk_monitor.py        — ドローダウン / ポジション上限監視
  - kill_switch.py         — kill.flag 管理
  - monitoring_engine.py   — 各 Monitor を束ねるエンジン
  - (その他 TradeMonitor / AlertManager 等)

- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
  - __init__.py

- research/
  - factor_research.py
  - feature_exploration.py
  - __init__.py

- utils/
  - logging_setup.py       — 一貫したログ設定
  - process_priority.py    — プロセス優先度 / CPU affinity
  - __init__.py

- tools/
  - paper_verification_report.py

データ / フラグファイル（実行時に生成・利用）
- data/kabusys.duckdb (デフォルト)
- data/monitoring.db (監視ログ SQLite)
- data/paper_trading.db (paper_trading 用、KABUSYS_ENV=paper_trading)
- data/execution.pid
- data/stop_requested.flag
- data/kill.flag

開発メモ / ベストプラクティス
------------------------------
- .env は決してリポジトリにコミットしないでください（config_setup.py のヘッダにも注意書きがあります）。
- 本番（KABUSYS_ENV=live）での運用時は validate_config の警告・設定を慎重に確認してください（LINE 通知等の設定が重要）。
- DuckDB は分析用途に最適化されているため、リサーチモジュールは DuckDB を前提に設計されています。
- AI（OpenAI）呼び出しは失敗時にフェイルセーフを取る設計です。API キーやレート制限に注意してください。

付録: よく使うコマンド例
-----------------------
- 対話式 .env を作る:
  python -m kabusys.config_setup

- 設定チェック:
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- Execution 起動:
  python -m kabusys.run_execution

- Monitoring 起動（間隔 30 秒）:
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Paper レポート:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

最後に
------
この README はコードベースの主要点をまとめたものです。各モジュールには docstring と実装コメントが充実していますので、詳細は該当ファイル（src/kabusys/**）を参照してください。必要であれば、README に追記する内容（デプロイ手順、systemd ユニット例、CI 設定例 など）を教えてください。