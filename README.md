KabuSys — 日本株自動売買システム（README）
====================================

概要
----
KabuSys は日本株向けの自動売買 / 監視 / 研究ユーティリティ群をまとめた Python プロジェクトです。本リポジトリには以下の主要機能が含まれます。

- 注文実行エンジン（ExecutionEngine）※ブローカ抽象化により本番 / Paper Trading 切替可能
- 監視サブシステム（System / Trade / Risk のモニタ、KillSwitch、LINE通知）
- Paper Trading の検証レポート生成ツール
- ポートフォリオ構築（候補選定・重み算出・ポジションサイジング）
- 研究用ファクター計算・特徴量解析モジュール（DuckDB 上で完結）
- ニュース NLP（OpenAI を用いた銘柄別センチメントスコア付与）および市場レジーム判定（LLM と価格指標の合成）
- Streamlit ベースの監視ダッシュボード

主要な設計方針:
- 研究 / 監視処理は DuckDB / SQLite を参照して完結（発注 API に不要なアクセスをしない）
- Paper Trading は本番 DB と分離（デフォルト別ファイル）
- ルックアヘッドバイアス防止の実装方針（日時参照に注意）

機能一覧
--------
- run_execution.py: ExecutionEngine の起動スクリプト（KABUSYS_ENV により paper_trading モードで MockBroker を使用）
- run_monitoring.py: SystemMonitor（ポーリング監視）の起動スクリプト（MONITOR_POLL_INTERVAL で間隔指定可）
- monitoring モジュール:
  - SystemMonitor: CPU/メモリ/ディスク/プロセス状態・データ鮮度の監視
  - TradeMonitor: 注文滞留・約定異常価格の検出
  - RiskMonitor: ドローダウン・ポジション上限の監視とリスクイベント記録
  - KillSwitch: 重大リスク発生時にフラグファイルを書き ExecutionEngine を止める仕組み
  - AlertManager: LINE Push による通知（クールダウン有）
  - streamlit_dashboard.py: 監視ダッシュボード（Streamlit）
- tools.paper_verification_report: Paper Trading DB を解析して稼働率・注文成功率・レイテンシ等の検証レポートを出力
- portfolio モジュール: 候補選定 / 等配分・スコア配分 / セクター制限 / 単元切り捨てによる株数算出
- research モジュール: momentum/value/volatility ファクター計算、将来リターン、IC 計算、統計サマリー
- ai モジュール:
  - news_nlp.score_news: raw_news を集約し OpenAI で銘柄ごとにセンチメントを算出して ai_scores に書き込む
  - regime_detector.score_regime: ETF MA とマクロニュースを組み合わせて日次の market_regime を算出

要件（例）
-----------
Python 3.10+ を想定。主要依存（抜粋）:
- duckdb
- psutil
- requests
- openai
- streamlit（ダッシュボード使用時）
- sqlite3（標準ライブラリ）

※ 実際のパッケージはプロジェクトの requirements.txt / pyproject.toml を参照してください（本コード抜粋では省略）。

環境変数（主なもの）
--------------------
- KABUSYS_ENV: 起動環境。development / paper_trading / live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須とされる箇所あり）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須とされる箇所あり）
- OPENAI_API_KEY: OpenAI API キー（ai.* を使う場合）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: AlertManager（LINE 通知）用
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- PID_FILE_PATH: ExecutionEngine の PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: KillSwitch フラグファイル（デフォルト: data/kill.flag）
- PAPER_FILL_MODE: Paper Trading の約定モード（instant | partial | never | reject）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）。1未満や不正値は 60 秒にフォールバック。

.env 自動読み込み
----------------
- プロジェクトルート（.git または pyproject.toml を起点）にある .env/.env.local を自動読み込みします（OS 環境変数が優先）。
- 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

セットアップ手順（簡易）
----------------------
1. リポジトリをクローン
2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install duckdb psutil requests openai streamlit
   （プロジェクトに requirements.txt/pyproject.toml があればそれを利用）
4. .env を作成（.env.example を参考に必要な環境変数を設定）
   - 例: KABUSYS_ENV=paper_trading, OPENAI_API_KEY=..., PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
5. 必要なら data ディレクトリを作成
   - mkdir -p data

実行方法（代表例）
------------------
- 監視ループ（SystemMonitor 単体起動）
  - MONITOR_POLL_INTERVAL を変更したい場合:
    - export MONITOR_POLL_INTERVAL=30
  - 実行:
    - python -m kabusys.run_monitoring
    （内部で Settings を読み、指定 SQLite に接続して監視ログを書きます）

- 実行エンジン（ExecutionEngine）
  - 環境変数で PAPER トレードを有効化:
    - export KABUSYS_ENV=paper_trading
  - 実行:
    - python -m kabusys.run_execution
  - paper_trading の場合、MockBroker を使い PAPER_TRADING_SQLITE_PATH に記録します（本番 DB とは分離）。

- Streamlit ダッシュボード
  - 起動:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 引数 --db で監視 DB を指定できます（既定: data/monitoring.db）。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - または指定 DB:
    - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

- AI モジュール（プログラム内呼び出し例）
  - from kabusys.ai.news_nlp import score_news
  - score_news(conn, target_date, api_key="...")  # DuckDB 接続を渡す
  - regime_detector は同様に score_regime(conn, target_date, api_key=...)

動作とファイル（運用時の注意）
-----------------------------
- run_monitoring は Settings.env に関わらず監視用 DB に対して本番 sqlite_path を使用します（設計上の意図）。
- run_execution は KABUSYS_ENV=paper_trading の場合、paper_sqlite_path に記録して本番 DB と分離します。
- KillSwitch は data/kill.flag を書き込むことで ExecutionEngine の停止シグナルを送ります。必要に応じて起動時にこのフラグをクリアしてください（Settings.kill_flag_clear_on_start により挙動を制御可能）。
- PID ファイル（Settings.pid_file_path）を用いて実行プロセスの存在チェックを行います。古い PID ファイルは stale と見なされると自動削除されアラート記録されます。
- OpenAI API 呼び出しを行う機能は API 制限や料金が発生します。テスト時はモック（unittest.mock.patch）で _call_openai_api を差し替えることを推奨します。
- DuckDB / SQLite のトランザクションは一部で明示的に BEGIN/COMMIT/ROLLBACK を使用しています。DB ファイルのバックアップ・権限に注意してください。

ディレクトリ構成（抜粋）
-----------------------
src/
  kabusys/
    __init__.py
    config.py                        -- 環境変数 / Settings 管理（.env 自動読み込み）
    run_monitoring.py                -- SystemMonitor ポーリング起動スクリプト
    run_execution.py                 -- ExecutionEngine 起動スクリプト
    ai/
      __init__.py
      news_nlp.py                    -- ニュース NLP（OpenAI）
      regime_detector.py             -- 市場レジーム判定（MA + LLM）
    monitoring/
      __init__.py
      monitoring_db.py               -- SQLite スキーマ / 永続化 API
      system_monitor.py
      trade_monitor.py
      risk_monitor.py
      monitoring_engine.py
      alert_manager.py
      kill_switch.py
      streamlit_dashboard.py
    execution/
      order_manager.py
      reconciler.py
      (その他エンジン/ブローカー関連モジュール...)
    portfolio/
      portfolio_builder.py
      position_sizing.py
      risk_adjustment.py
      __init__.py
    research/
      factor_research.py
      feature_exploration.py
      __init__.py
    tools/
      __init__.py
      paper_verification_report.py
    utils/
      __init__.py
      process_priority.py

開発者向けメモ
---------------
- テスト時に .env 自動読み込みを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を指定してください。
- OpenAI 関連は外部 API に依存するためユニットテストでは API 呼び出しをモックすること（_call_openai_api の patch 等）。
- DuckDB クエリは大量データを扱うため WHERE 範囲を限定する設計になっています。新しいクエリを追加する場合はスキャン範囲を意識してください。
- process_priority.set_process_priority を利用して起動直後にプロセス優先度を上げています。権限のない環境では警告が出力されますが処理は継続します。

ライセンス・貢献
----------------
本 README に含まれるコード断片はプロジェクトの一部を抜粋したものです。実開発では pyproject.toml / LICENSE / CONTRIBUTING を参照してください。

以上。必要ならインストール手順や環境変数のサンプル（.env.example 形式）や各モジュールの API 使用例を追記します。どの情報をより詳しく記載しましょうか？