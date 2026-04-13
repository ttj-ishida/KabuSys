README
=====

概要
----
KabuSys は日本株向けの自動売買フレームワークです。  
本リポジトリには、発注・実行エンジン（ExecutionEngine）、監視コンポーネント（MonitoringEngine）、ポートフォリオ構築ユーティリティ、リサーチ用ファクター計算、LLM を用いたニュースセンチメント／市場レジーム判定、各種ツール類が含まれます。  
設計方針として「本番データへの不要なアクセスを避ける」「ルックアヘッドバイアスを回避する」「フェイルセーフ（API失敗時は安全側フォールバック）」を重視しています。

主な機能
--------
- ExecutionEngine: ブローカー API 経由での注文送信、リスク管理、リコンシリエーション（再起動後の同期）を行います。
- MonitoringEngine: システム状態（CPU/メモリ/ディスク/プロセス）・注文の滞留・約定異常・ドローダウン監視、LINE 通知、kill.flag による ExecutionEngine 停止シグナル出力。
- ポートフォリオ構築: 候補選定、重み計算（等分／スコア加重）、リスク調整（セクターキャップ／レジーム乗数）、単元丸め付きのポジションサイズ計算。
- 研究モジュール: DuckDB を用いたファクター計算（モメンタム・バリュー・ボラティリティ）、将来リターン、IC 計算、統計サマリー。
- AI モジュール: OpenAI（gpt-4o-mini）を使ったニュースセンチメント（ai_scores）と市場レジーム判定（market_regime）。失敗時は安全にフォールバック。
- ツール: Paper Trading の検証レポート生成スクリプト、Streamlit ベースの監視ダッシュボードなど。
- ユーティリティ: 設定管理（.env 対応）、プロセス優先度／CPU affinity 設定ユーティリティ。

前提・必須ライブラリ
--------------------
- Python 3.9+
- パッケージ（主なもの）:
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit（監視ダッシュボードを使う場合）
- 標準ライブラリ: sqlite3, logging, datetime 等

セットアップ手順（ローカル）
--------------------------
1. リポジトリをクローンしてワークディレクトリに移動します。
   - 例: git clone <repo> && cd <repo>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install -r requirements.txt
   ※ requirements.txt がない場合は最低限以下をインストールしてください:
   - pip install duckdb psutil requests openai streamlit

4. データディレクトリの作成
   - mkdir -p data

5. 環境変数の設定
   - プロジェクトルートに .env を配置するか、OS環境変数を設定します。
   - main に使用される主な環境変数（例）:
     - KABUSYS_ENV: development | paper_trading | live  （デフォルト: development）
     - JQUANTS_REFRESH_TOKEN: （必須: J-Quants API を使う機能用）
     - KABU_API_PASSWORD: （必須: kabuステーション API 用）
     - OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用 DB）
     - SQLITE_PATH: data/monitoring.db（監視ログ用 DB、デフォルト）
     - DUCKDB_PATH: data/kabusys.duckdb（DuckDB ファイル、デフォルト）
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知用
     - PAPER_FILL_MODE: instant | partial | never | reject（paper_trading の約定挙動）
     - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring 用）
     - PID_FILE_PATH / KILL_FLAG_PATH 等（デフォルトは data/execution.pid / data/kill.flag）

   - Settings モジュールは .env / .env.local を自動読み込みします（OS 環境変数優先）。自動読み込みを抑制するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

使い方（主要コマンド）
--------------------

1. ExecutionEngine を起動する
   - 本番（default）:
     - KABUSYS_ENV=live python -m kabusys.run_execution
   - Paper Trading（ブローカーはモック、DB は data/paper_trading.db に分離）:
     - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
   - 実行前に .env で環境変数（API キー等）を設定してください。
   - 起動時に実行プロセスの優先度を high に設定し、pid_file にプロセス ID を書き込みます。
   - Paper Trading は本番 DB と完全分離されるため安全にローカル検証可能です。

2. MonitoringEngine を起動する（監視ループ）
   - python -m kabusys.run_monitoring
   - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書きできます（デフォルト 60 秒）。
   - 監視は常に本番の sqlite_path を使用（環境にかかわらず監視データは本番 DB に記録される点に注意）。

3. Streamlit ダッシュボード
   - 起動例:
     - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - ブラウザで監視ダッシュボードを表示し、ポートフォリオ値・ポジション・最近の注文・リスクログ・システム状況を確認できます。

4. Paper Trading 検証レポート生成
   - コマンドライン実行:
     - python -m kabusys.tools.paper_verification_report
     - 期間指定: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
     - DB 指定: --db /path/to/data/paper_trading.db
   - 指標: 稼働率・注文成功率・送信率・P95 レイテンシ 等に基づき PASS/FAIL 判定を行います。

5. AI（ニュースセンチメント / レジーム判定）をプログラムから実行
   - ニューススコアリング:
     - from kabusys.ai.news_nlp import score_news
     - score_news(conn, target_date, api_key="...")  # conn は duckdb connection
   - 市場レジーム判定:
     - from kabusys.ai.regime_detector import score_regime
     - score_regime(conn, target_date, api_key="...")
   - OpenAI API キーは引数で渡すか、環境変数 OPENAI_API_KEY を使用します。
   - AI モジュールは失敗時にフォールバック（例: macro_sentiment=0.0）するため安全に呼び出せます。

設定のポイント・挙動
-------------------
- PAPER_TRADING: KABUSYS_ENV=paper_trading の際、ExecutionEngine は MockBrokerClient を使い、DB は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に切り替わります。本番 DB と完全分離されます。
- PID / Kill flag:
  - ExecutionEngine は PID ファイル（デフォルト data/execution.pid）を用いて稼働確認を行います。
  - Monitoring は stale PID を検出すると PID ファイルを削除して risk_event をログし、KillSwitch は条件に応じて data/kill.flag を作成します。ExecutionEngine は起動時に kill.flag のクリア設定（KILL_FLAG_CLEAR_ON_START）を確認できます。
- Settings 自動読み込み:
  - プロジェクトルート (pyproject.toml / .git が存在するディレクトリ) の .env を自動読み込みします（.env.local は上書き）。必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます。

ディレクトリ構成（抜粋）
-----------------------
src/
  kabusys/
    __init__.py
    config.py                      — 環境変数 / Settings 管理（.env ロード含む）
    run_execution.py               — ExecutionEngine 起動スクリプト
    run_monitoring.py              — SystemMonitor ポーリングループ起動スクリプト

    execution/
      order_manager.py
      reconciler.py
      order_repository.py          — （OrderRepository 等は存在する想定）
      execution_engine.py
      broker_factory.py
      broker_api.py
      ...                          — 実行関連コンポーネント

    monitoring/
      monitoring_db.py             — SQLite ベースの監視 DB 層
      system_monitor.py
      trade_monitor.py
      risk_monitor.py
      kill_switch.py
      alert_manager.py
      monitoring_engine.py
      streamlit_dashboard.py
      __init__.py

    portfolio/
      portfolio_builder.py
      position_sizing.py
      risk_adjustment.py
      __init__.py

    research/
      factor_research.py
      feature_exploration.py
      __init__.py

    ai/
      news_nlp.py                   — ニュースセンチメント（OpenAI）
      regime_detector.py            — 市場レジーム判定（OpenAI）
      __init__.py

    tools/
      paper_verification_report.py  — Paper Trading 検証レポート
      __init__.py

    data/                           — （ランタイムで使用する SQLite / DuckDB ファイルを想定）
      monitoring.db
      paper_trading.db
      kabusys.duckdb
    utils/
      process_priority.py           — プロセス優先度 / CPU affinity ユーティリティ
      __init__.py
    research/, portfolio/, monitoring/, ai/ ...  — その他モジュール

注意事項・運用メモ
-----------------
- Monitoring は監視用 DB を常に本番用 sqlite_path に書き込みます。テスト時は設定に注意してください。
- Paper Trading モードは実発注をしない設計ですが、モックの挙動（PAPER_FILL_MODE）により挙動が異なります。
- OpenAI を使う機能は API コストとレート制限に注意してください。API エラーやタイムアウトはリトライとフェイルセーフ処理が組み込まれていますが、過剰呼び出しは避けてください。
- DuckDB / SQLite のバージョンや executemany の空引数に関する制約（コード内に回避処理あり）に依存する部分があります。環境により挙動差異が出る場合はログを確認してください。

貢献・拡張
----------
- Broker 実装（kabuステーション等）の追加・差し替えは BrokerClientFactory を拡張してください。
- ポートフォリオ設計（weights, allocation 方法）や手数料・スリッページの扱いは position_sizing のパラメータで拡張可能です。
- AI モデルやプロンプト調整は kabusys/ai 内で行えます。テストのため API 呼び出しはモック化しやすい設計になっています。

ライセンス
----------
プロジェクトのライセンス表記をここに追記してください（例: MIT 等）。

お問い合わせ
------------
実装に関する質問やバグ報告はリポジトリの issue にお願いします。

以上。