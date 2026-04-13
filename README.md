KabuSys — README
=================

概要
----
KabuSys は日本株自動売買システムのコアライブラリです。銘柄選定・ポジションサイズ算出、発注実行（ExecutionEngine）、監視（MonitoringEngine）、リサーチ（ファクター計算・特徴量探索）、および AI を用いたニュースセンチメント／レジーム判定などの機能を提供します。  
本リポジトリはライブラリ／バッチ／CLI 形態で利用でき、ローカルの SQLite / DuckDB をデータ永続化層として想定しています。

主な特徴
--------
- ポートフォリオ構築
  - シグナル候補選定（スコア順）、等金額／スコア重み付け配分
  - リスク調整（セクター上限、レジーム乗数）
  - 株数（lot）丸め、リスクベースのポジション算出、アグリゲートキャップ処理
- 発注・実行
  - OrderManager / ExecutionEngine（ブローカーファクトリ経由でブローカーと連携）
  - 起動時リコンシリエーション（Reconciler）による自動復旧
  - paper_trading モードでの Mock ブローカー（本番 DB と分離）
- 監視（Monitoring）
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - 監視ログの永続化（SQLite）と Streamlit ダッシュボード表示
  - Kill switch（フラグファイルによる ExecutionEngine 停止シグナル）
  - LINE Push によるアラート通知（AlertManager）
- リサーチ
  - DuckDB を使ったファクター計算（Momentum / Volatility / Value 等）
  - 将来リターン・IC 計算、特徴量サマリー
- AI 機能（OpenAI）
  - ニュースを LLM（gpt-4o-mini）でセンチメント評価して ai_scores に書込む
  - ETF MA とマクロニュースの LLM 評価を合成して市場レジーム（bull/neutral/bear）を判定
- 付帯ツール
  - paper_trading の検証レポート生成スクリプト
  - Streamlit ベースの監視ダッシュボード

セットアップ
------------
前提
- Python 3.9+（ソースは typing | match を想定）
- OS: Linux / macOS / Windows（ただし一部機能（CPU affinity 等）は OS により動作差分あり）

1. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージ（例）
   - pip install duckdb psutil requests openai streamlit
   - 必要に応じてその他のライブラリを追加してください

3. 環境変数（.env）
   - プロジェクトルートの .env / .env.local に必要な設定を置けます。
   - 自動読み込みはデフォルトで有効（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化）。
   - 主要な環境変数例:
     - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
     - JQUANTS_REFRESH_TOKEN: （必須；J-Quants API 用）
     - KABU_API_PASSWORD: （必須；kabuステーション API 用）
     - OPENAI_API_KEY: OpenAI API キー（AI 機能利用時）
     - DUCKDB_PATH: DuckDB のパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH: 監視ログ DB（デフォルト data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH: paper_trading 用 DB（デフォルト data/paper_trading.db）
     - PID_FILE_PATH / KILL_FLAG_PATH: PID 管理・kill flag のパス
     - PAPER_FILL_MODE: instant | partial | never | reject（paper_trading の約定挙動）
     - MONITOR_POLL_INTERVAL: 監視ループの秒間隔（デフォルト 60）
     - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL
     - CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT: 監視閾値

使い方（実行方法）
-----------------

- 監視ループ（Monitoring）
  - 目的: SystemMonitor を定期的に実行し、監視ログを SQLite に保存。kill.flag 等を管理。
  - コマンド:
    - python -m kabusys.run_monitoring
  - オプション:
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可（1 以上）。

  注意: Monitoring は KABUSYS_ENV にかかわらず sqlite_path（デフォルト data/monitoring.db）を使用します。

- 実行エンジン（Execution）
  - 目的: ExecutionEngine を起動してトレード実行セッションを行う。
  - コマンド:
    - python -m kabusys.run_execution
  - 動作:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し、paper_trading 用 DB（data/paper_trading.db）に記録します。本番 DB と完全分離されます。
  - 起動時に set_process_priority("high") を呼び出し優先度を上げます（権限が必要な場合は失敗しても継続）。

- Streamlit 監視ダッシュボード
  - 起動:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - read-only URI を使って SQLite を開き、ポジション／注文／システム情報を可視化します。

- Paper Trading 検証レポート
  - 使い方:
    - python -m kabusys.tools.paper_verification_report
    - 期間指定例: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    - DB 指定: --db PATH（環境変数 PAPER_TRADING_SQLITE_PATH でも指定可）
  - 出力: 稼働率、注文成功率、送信率、P95 レイテンシ、リスク却下数 等を表示し PASS/FAIL を判定します。

- AI 機能（ニュース NLP / レジーム判定）
  - 前提: OPENAI_API_KEY を設定
  - ニュースセンチメント書込:
    - 呼び出し例（ライブラリ API）:
      - from kabusys.ai.news_nlp import score_news
      - score_news(conn, target_date, api_key="…")
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, target_date, api_key="…")
  - 実際のバッチは DuckDB 接続を作り、対象日を与えて実行します。API エラーは適切にリトライ／フォールバックされます。

主要な設計と運用メモ
-------------------
- 設定は Settings クラス（kabusys.config）を経由して取得します。プロジェクトルートの .env / .env.local が自動ロードされます（但し OS 環境変数が優先される）。
- Paper Trading モードは本番 DB を汚さないように専用 SQLite を使う設計です。
- 監視データベース（monitoring_db）には system_status / trade_logs / positions / risk_logs / dashboard が定義されており、起動時にテーブル作成・マイグレーションを行います。
- Process priority / CPU affinity は utils/process_priority.py に抽象化されています（psutil を使用）。権限不足時はログを出してスキップします。
- DuckDB はリサーチ系の高速集計に利用されます（prices_daily / raw_financials テーブル等）。

ディレクトリ構成
----------------
（src/kabusys 以下を抜粋）

- src/kabusys/
  - __init__.py (パッケージ定義)
  - config.py (環境変数 / Settings)
  - run_monitoring.py (SystemMonitor のポーリング起動スクリプト)
  - run_execution.py (ExecutionEngine 起動スクリプト)
  - tools/
    - paper_verification_report.py (paper_trading 検証レポート)
  - ai/
    - news_nlp.py (ニュース NLP → ai_scores 書き込み)
    - regime_detector.py (市場レジーム判定)
  - monitoring/
    - monitoring_db.py (SQLite 永続化層)
    - system_monitor.py (システム・データ鮮度監視)
    - trade_monitor.py (注文滞留・約定異常検出)
    - risk_monitor.py (ドローダウン・ポジション上限監視)
    - kill_switch.py (kill.flag 管理)
    - alert_manager.py (LINE Push)
    - monitoring_engine.py (各 Monitor を束ねる)
    - streamlit_dashboard.py (Streamlit ダッシュボード)
  - execution/
    - order_manager.py (Order 管理)
    - reconciler.py (起動時リコンシリエーション)
    - ...（ブローカー関連・order_repository 等が含まれる想定）
  - portfolio/
    - portfolio_builder.py (候補選定・重み付け)
    - position_sizing.py (株数算出・aggregate cap)
    - risk_adjustment.py (セクターキャップ・レジーム乗数)
    - __init__.py
  - research/
    - factor_research.py (momentum/volatility/value)
    - feature_exploration.py (forward returns / IC / summary)
    - __init__.py
  - utils/
    - process_priority.py (プロセス優先度 / CPU affinity)
    - __init__.py
  - monitoring_db, ai, research 等のモジュールコメントに運用方針や注意事項が詳述されています。

開発・貢献
----------
- 静的型付け・ユニットテストの追加を推奨します（特に finance 計算・API 呼び出し周り）。
- OpenAI API 呼び出し部分は外部依存（レート制限・料金）であるため、開発時はモック（unittest.mock）で置き換えてください。
- データベーススキーマ変更時は monitoring_db.init_monitoring_db にマイグレーション処理を追記してください。

ライセンス
----------
- 本リポジトリのライセンス表記が別途ない場合は運用ポリシーに従ってください（README に明記が無ければ管理者に確認してください）。

補足（よくある質問）
-------------------
Q. 監視と実行の DB は同じですか？  
A. 監視（Monitoring）は常に sqlite_path（デフォルト data/monitoring.db）を使用します。ExecutionEngine は KABUSYS_ENV=paper_trading の場合に paper_sqlite_path（デフォルト data/paper_trading.db）を使用し、本番と分離されます。

Q. モデル呼び出しの API キーはどこで設定しますか？  
A. OPENAI_API_KEY を環境変数または関数引数で指定します。未設定だとエラー（ValueError）となります（ただし一部の呼び出しはフォールバックして継続する設計です）。

Q. MONITOR_POLL_INTERVAL の最小値は？  
A. 1 秒未満や 0/負値は無効と見なしデフォルト（60秒）にフォールバックします。

以上。必要であればインストール用 requirements.txt のサンプルや、よく使うコマンド集（systemd ユニット例、Dockerfile、CI 設定例）も作成します。どれが必要か教えてください。