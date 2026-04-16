KabuSys — 自動売買システム（README）
=================================

概要
----
KabuSys は日本株向けの自動売買システム向けライブラリ群・ランタイムです。  
主な機能は以下のとおりです。

- 注文発行・状態管理（ExecutionEngine / OrderManager）
- リコンシリエーション（起動時の注文・ポジション同期）
- リスク監視（ドローダウン・ポジション数上限等）
- システム監視（プロセス生存・CPU/メモリ/ディスク・データ鮮度）
- 監視ダッシュボード（Streamlit）
- Paper Trading 用検証ツール（レポート生成）
- 研究用ファクター計算・特徴量探索（DuckDB ベースの純関数群）
- ニュース NLP / レジーム判定（OpenAI によるセンチメント評価）
- ユーティリティ（プロセス優先度設定、PID / フラグファイル制御 等）

重要な設計方針（抜粋）
- DuckDB / SQLite を用いたローカル DB 中心の処理（外部口座 API への依存は限定）
- ルックアヘッドバイアスの回避（target_date に対するクエリ設計）
- Paper Trading 環境は本番 DB と明確に分離（環境変数で切替）
- 外部 API 呼び出し（OpenAI など）はフェイルセーフ設計（失敗時は継続）

機能一覧
--------
主要コンポーネントと担当範囲:

- kabusys.run_execution
  - ExecutionEngine の起動スクリプト。KABUSYS_ENV=paper_trading のときは Mock Broker を使用し、paper_trading 用 SQLite に記録します。
- kabusys.run_monitoring
  - SystemMonitor のポーリングループ起動スクリプト。ポーリング間隔は MONITOR_POLL_INTERVAL で変更可能（デフォルト 60 秒）。
- kabusys.monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine / AlertManager / KillSwitch 等。監視ログは SQLite（monitoring.db）に永続化。
- kabusys.execution
  - 注文管理（OrderManager）、リコンシリエーション（Reconciler）、注文リポジトリ 等。
- kabusys.portfolio
  - 候補選定・重み計算・ポジションサイズ算出・セクター制限等の純粋関数群。
- kabusys.research
  - ファクター計算（momentum/value/volatility）、forward returns、IC 計算、統計サマリ。
- kabusys.ai
  - news_nlp（ニュースのセンチメント -> ai_scores） / regime_detector（市場レジーム判定）。
  - OpenAI を用いる部分は API キー必須（OPENAI_API_KEY）。
- ツール
  - kabusys.tools.paper_verification_report：Paper Trading DB を読み取り検証レポートを生成。
  - Streamlit ダッシュボード（monitoring/streamlit_dashboard.py）

セットアップ手順
--------------
1. Python バージョン
   - Python 3.10 以上を想定（型シンタックスに | を使用）。

2. 依存パッケージ（代表例）
   - duckdb
   - psutil
   - requests
   - streamlit (ダッシュボード利用時)
   - openai (AI 機能利用時)
   - その他（テスト/開発用）  
   実プロジェクトでは requirements.txt / Poetry / Pipenv を用意してインストールしてください。
   例:
     pip install duckdb psutil requests streamlit openai

3. 環境変数 / .env
   - プロジェクトルートに .env / .env.local を置くと自動的に読み込まれます（既存の OS 環境変数は上書きされません）。自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
   - 主要な環境変数（抜粋）:
     - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
     - JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
     - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
     - OPENAI_API_KEY: OpenAI API キー（ai.news_nlp / ai.regime_detector を使う場合必須）
     - DUCKDB_PATH: duckdb ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: monitoring SQLite（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
     - PAPER_FILL_MODE: paper_trading 時の約定挙動（instant|partial|never|reject）
     - PID_FILE_PATH, KILL_FLAG_PATH 等のパス指定
     - MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、run_monitoring 用）
     - LOG_LEVEL: ログレベル（DEBUG|INFO|...）

4. データディレクトリ
   - デフォルトで data/ 下に DB やフラグファイルを置きます（例: data/monitoring.db, data/kabusys.duckdb, data/execution.pid, data/kill.flag, data/stop_requested.flag）。
   - 実稼働時はパーミッションやバックアップ/監視を適切に行ってください。

使い方（主要コマンド）
--------------------

1. Execution（実行エンジン）起動
   - 本番 / 開発 / PaperTrading 切替:
     - KABUSYS_ENV=paper_trading を設定すると paper_trading 専用の MockBroker と data/paper_trading.db が使用され、本番 SQLite は使われません。
   - 起動コマンド:
     - python -m kabusys.run_execution
   - 停止方法:
     - プロジェクトルートの data/stop_requested.flag を作成するとスクリプトは検出して安全に停止します。
     - KillSwitch による停止要求は data/kill.flag が書き込まれます（ExecutionEngine は起動時に kill.flag をクリアするオプションがあります設定で管理）。

2. Monitoring（監視ループ）起動
   - ポーリング間隔（秒）:
     - 環境変数 MONITOR_POLL_INTERVAL を指定可能（デフォルト 60）。
   - 起動コマンド:
     - python -m kabusys.run_monitoring
   - 特記事項:
     - Monitoring は KABUSYS_ENV に関わらず本番の sqlite_path（Settings.sqlite_path）を使用します（意図的な設計）。

3. Streamlit ダッシュボード
   - 起動コマンド（例: monitoring.db を読み取り専用で開く）:
     - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - ダッシュボードでは dashboard / positions / recent orders / system status / recent risk logs を参照できます。

4. Paper Trading 検証レポート
   - コマンド:
     - python -m kabusys.tools.paper_verification_report
     - オプション: --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
   - 使用例:
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

5. AI 機能（news_nlp / regime_detector）
   - OpenAI API キーが必要（OPENAI_API_KEY 環境変数または関数引数で指定）。
   - news_nlp.score_news(conn, target_date, api_key=None) — raw_news をまとめて LLM でスコア化し ai_scores に書き込み。
   - ai.regime_detector.score_regime(conn, target_date, api_key=None) — ETF ma200 とマクロセンチメントを合成して market_regime に書き込み。
   - API 呼び出し失敗時はフェイルセーフで継続（多くのケースで 0.0 などにフォールバックし例外を上位へ投げない挙動が設計に組み込まれています）。

設定・ファイル
--------------
主なパス・フラグ（デフォルト値）:

- data/kabusys.duckdb (DUCKDB_PATH= data/kabusys.duckdb)
- data/monitoring.db (SQLITE_PATH= data/monitoring.db)
- data/paper_trading.db (PAPER_TRADING_SQLITE_PATH= data/paper_trading.db)
- data/execution.pid (PID_FILE_PATH= data/execution.pid)
- data/kill.flag (KILL_FLAG_PATH= data/kill.flag)
- data/stop_requested.flag （run_* スクリプトが存在をチェックして終了するための外部停止フラグ）

注意点
-------
- Settings は起動時に .env / .env.local を自動ロードします。OS 環境変数を保護するため .env の上書き挙動は制御されています。
- Paper Trading と本番 DB は分離されます。Paper 環境で本番 DB を誤って上書きしないよう KABUSYS_ENV の設定に注意してください。
- OpenAI や外部 API 呼び出しはレート制限/ネットワーク障害を考慮してリトライ／フェイルセーフ設計がなされていますが、API キーの漏洩管理・コスト管理は利用者側で行ってください。
- プロセス優先度設定（set_process_priority）はプラットフォーム差分を吸収しますが、権限不足時はスキップされます（ログに warning）。

ディレクトリ構成（主要ファイル）
--------------------------------
（src/kabusys 以下の主要ファイル・パッケージを抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                — 環境変数/設定ローダ
    - run_execution.py         — ExecutionEngine 起動スクリプト
    - run_monitoring.py       — SystemMonitor ポーリング起動スクリプト
    - tools/
      - __init__.py
      - paper_verification_report.py
    - monitoring/
      - __init__.py
      - monitoring_db.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - monitoring_engine.py
      - kill_switch.py
      - alert_manager.py
      - streamlit_dashboard.py
    - execution/
      - order_manager.py
      - reconciler.py
      - (その他注文/ブローカー周り実装)
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
    - utils/
      - process_priority.py

付録（運用に役立つヒント）
-------------------------
- ログ出力:
  - Settings.log_level（LOG_LEVEL 環境変数）で調整できます。デフォルトは INFO。
- 開発・テスト:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env の自動ロードを無効化できるため、ユニットテストで環境を制御しやすくなります。
- 停止手順:
  - 長時間実行する run_execution/run_monitoring は data/stop_requested.flag を作成することで外部から安全に停止できます。kill.flag は KillSwitch が書き込み、ExecutionEngine に対する停止シグナルとして使用されます。

最後に
------
この README はコードベースの主要設計・実行方法のサマリです。実運用にあたっては環境変数（特に認証情報）や DB のバックアップ、監視・アラート設計を十分に行ってください。追加のドキュメント（API 仕様書 / PortfolioConstruction.md / StrategyModel.md 等）がプロジェクトに含まれている場合はそちらも参照してください。