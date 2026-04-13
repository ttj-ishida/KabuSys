README
=====

概要
----
KabuSys は日本株向けの自動売買 / 研究 / 監視ユーティリティ群をまとめたパッケージです。本リポジトリには以下の主要機能を持つモジュールが含まれます。

- 発注・実行エンジン（ExecutionEngine、OrderManager、Reconciler など）
- 監視・アラート（SystemMonitor、TradeMonitor、RiskMonitor、AlertManager、KillSwitch、Streamlit ダッシュボード）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算、セクター制限）
- 研究用ファクター計算・特徴量解析（momentum / volatility / value 等）
- ニュース NLP（OpenAI を用いた銘柄別センチメント / レジーム判定）
- ペーパートレード検証ツール（レポート生成スクリプト）

特徴一覧
--------
- モジュール設計：発注・監視・ポートフォリオ構築・研究・AI を責務分離して実装
- DuckDB / SQLite を利用した高速分析・永続化
- Paper Trading 環境を本番 DB と分離（data/paper_trading.db）
- OpenAI（gpt-4o-mini）を利用したニュースセンチメント評価・レジーム判定機能（API キー必要）
- LINE Messaging API による通知（AlertManager）
- Streamlit による監視ダッシュボード
- フェイルセーフ設計：リトライ、バックオフ、冪等操作、部分失敗時の保護等を考慮

セットアップ手順
----------------
1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo-root>

2. 仮想環境（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb psutil requests openai streamlit
   - （プロジェクトに requirements.txt がある場合は pip install -r requirements.txt）

4. データディレクトリを作成
   - mkdir -p data

5. 環境変数 / .env
   - プロジェクトルートに .env / .env.local を置くと自動で読み込まれます（OS 環境変数が優先）。
   - 自動読み込みを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   - 主な環境変数（例）:
     - KABUSYS_ENV=development | paper_trading | live
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - OPENAI_API_KEY=...
     - LINE_CHANNEL_ACCESS_TOKEN=...
     - LINE_USER_ID=...
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - PAPER_FILL_MODE=instant | partial | never | reject
     - PID_FILE_PATH=data/execution.pid
     - KILL_FLAG_PATH=data/kill.flag
     - MONITOR_POLL_INTERVAL=60  (run_monitoring 用。秒、1 以上)

6. 初回実行
   - run_monitoring.py / run_execution.py 実行時に監視 DB のテーブルは自動作成されます（init_monitoring_db が呼ばれます）。

使い方
------
- 実行エンジン（ExecutionEngine）を起動
  - 環境変数 KABUSYS_ENV を設定してから起動します。
  - Paper Trading（モックブローカー）で動かす例:
    - export KABUSYS_ENV=paper_trading
    - python -m kabusys.run_execution
    - Paper Trading 時は settings.paper_sqlite_path（デフォルト data/paper_trading.db）へ記録され、本番 DB と分離されます。
  - 本番 / 開発:
    - export KABUSYS_ENV=live
    - python -m kabusys.run_execution

- 監視ループを起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60）。
  - run_monitoring は Settings によって指定された sqlite_path（monitoring DB）と duckdb を開き、SystemMonitor のポーリングを行います。
  - 監視ループは PID ファイル / kill.flag を利用して ExecutionEngine と連携します（KillSwitch）。

- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - ダッシュボードは monitoring DB を読み取り専用で開き、Overview / Positions / Orders / System タブを表示します。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション --db で DB パスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH でも可）

- AI 関連（ニュース NLP / レジーム判定）
  - OpenAI API キーが必要です（OPENAI_API_KEY 環境変数または関数引数で指定）。
  - ニューススコアリング:
    - kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
  - レジーム判定:
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - 実行時には raw_news / news_symbols / ai_scores / market_regime 等のテーブルが DuckDB に存在している必要があります。

注意事項・運用メモ
-----------------
- MONITOR（run_monitoring）は監視用 DB に対して production sqlite_path を使います（KABUSYS_ENV に関わらず本番 sqlite_path を参照）。
- Paper Trading と本番 DB は分離されています（paper_trading 用 DB パスが用意されています）。
- KillSwitch は data/kill.flag を作成することで ExecutionEngine に停止指示を与えます。ExecutionEngine 側はこのフラグを読み取り停止処理を行う設計です。
- LINE 通知を有効にするには LINE_CHANNEL_ACCESS_TOKEN と LINE_USER_ID を設定してください。未設定時はログのみ出力して通知はスキップされます。
- OpenAI の呼び出しではエラー（429、タイムアウト、5xx 等）に対して指数バックオフでのリトライを行います。失敗時はフェイルセーフとしてスコアをスキップまたは 0 にフォールバックする設計です。
- .env のパースはシェル風（export を許容、クォートやインラインコメントに柔軟対応）ですが、誤設定に注意してください。
- 標準的なログレベルは LOG_LEVEL で制御できます（DEBUG/INFO/WARNING/ERROR/CRITICAL）。

ディレクトリ構成（主要ファイル）
------------------------------
src/
  kabusys/
    __init__.py
    config.py                      # 設定 / 環境変数ローダ
    run_monitoring.py              # SystemMonitor ポーリング起動スクリプト
    run_execution.py               # ExecutionEngine 起動スクリプト
    tools/
      __init__.py
      paper_verification_report.py # Paper Trading 検証レポート CLI
    data/                           # （別モジュール群; DuckDB/パイプライン等）
      ...
    execution/
      broker_api.py
      broker_factory.py
      execution_engine.py
      order_manager.py
      order_repository.py
      order_record.py
      reconciler.py
      risk_manager.py
      ...
    monitoring/
      __init__.py
      monitoring_db.py             # SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
      system_monitor.py
      trade_monitor.py
      risk_monitor.py
      monitoring_engine.py
      kill_switch.py
      alert_manager.py
      streamlit_dashboard.py
    portfolio/
      __init__.py
      portfolio_builder.py
      position_sizing.py
      risk_adjustment.py
    research/
      __init__.py
      factor_research.py
      feature_exploration.py
    ai/
      __init__.py
      news_nlp.py
      regime_detector.py
    utils/
      __init__.py
      process_priority.py

補足（実装上のポイント）
----------------------
- モジュールは可能な限り純粋関数・副作用の少ない設計を志向しています（例：ポートフォリオ計算・研究モジュール）。
- 監視 DB（SQLite）は init_monitoring_db() によりテーブル作成・簡易マイグレーションを行います。スキーマ変更への互換性を意識した移行コードが含まれます。
- プロセス優先度や CPU affinity の設定は utils/process_priority.py で OS に依存しないインターフェースを提供します。権限不足時は警告ログで安全にスキップします。
- LLM 呼び出しや外部 API 呼び出しは失敗時にシステム全体を阻害しないようフェイルセーフ（デフォルト値やスキップ）を採用しています。

ライセンス・貢献
----------------
- 本リポジトリ独自のライセンス情報がある場合はプロジェクトルートの LICENSE を参照してください。
- バグ報告・機能提案は issue にて受け付けます。プルリクエスト歓迎。

以上。必要であれば、導入用の requirements.txt のサンプルや .env.example、起動スクリプト（systemd / supervisor 用）テンプレートも作成します。どれを用意しましょうか？