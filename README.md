KabuSys — README
=================

概要
----
KabuSys は日本株向けの自動売買・研究・監視ユーティリティ群です。  
主な目的は戦略の研究（ファクター計算・特徴量解析）、ポートフォリオ構築、発注実行、ならびに稼働監視・アラート発行です。  
コードは純粋関数的なポートフォリオ構築ロジック、DuckDB を使ったリサーチ・ファクター計算、SQLite を使った監視/トレードログ、OpenAI を使ったニュース NLP など複数のモジュールで構成されています。

主な機能
--------
- リサーチ
  - モメンタム / ボラティリティ / バリュー等のファクター計算（kabusys.research）
  - 将来リターン計算、IC（Information Coefficient）や統計サマリー（feature_exploration）
- ポートフォリオ構築
  - 候補選別、等重・スコア重み付け、リスク調整（セクター上限・レジーム乗数）
  - 発注株数（ロット）決定・投下資金スケーリング（position_sizing）
- 実行（Execution）
  - ブローカーファクトリを用いた実際の発注処理（paper_trading 時は MockBroker）
  - OrderManager / Reconciler による再起動時の同期処理
  - RiskManager による発注前リスクチェック
- 監視（Monitoring）
  - SystemMonitor / TradeMonitor / RiskMonitor による定期ポーリングとログ記録
  - MonitoringDB（SQLite）による永続化／マイグレーション処理
  - AlertManager による LINE プッシュ通知（クールダウン管理あり）
  - KillSwitch: ドローダウン等の条件で ExecutionEngine 停止フラグ（data/kill.flag）を書き込み
  - Streamlit ダッシュボード（リアルタイム監視 UI）
- AI（OpenAI）
  - ニュース記事を LLM でスコア化し ai_scores に書き込む（kabusys.ai.news_nlp）
  - ETF の MA 乖離とマクロニュースの LLM スコアを組み合わせて市場レジーム判定（kabusys.ai.regime_detector）
- ツール
  - Paper Trading の検証レポート生成スクリプト（kabusys.tools.paper_verification_report）

前提（依存）
------------
最低限の実行に必要な主なパッケージ例（プロジェクトの requirements.txt がない場合の参考）:
- Python 3.9+
- duckdb
- psutil
- requests
- openai
- streamlit （監視ダッシュボードを使う場合）
- その他（標準ライブラリのみで動作する部分も多数）

セットアップ手順
----------------
1. リポジトリをチェックアウト／配置
   - ソースは src/kabusys 以下に格納されています。

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージのインストール
   - pip install duckdb psutil requests openai streamlit
   - （必要に応じて他の補助パッケージを追加）

4. データディレクトリ作成
   - mkdir -p data

5. 環境変数の設定
   - プロジェクトルートに .env または .env.local を置くと自動で読み込まれます（既存 OS 環境変数は上書きされません。 .env.local は上書きされる）。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
   - 代表的な環境変数（必須のものもあり）:
     - JQUANTS_REFRESH_TOKEN — （J-Quants API 用）
     - KABU_API_PASSWORD — （kabuステーション API 用）
     - OPENAI_API_KEY — OpenAI 呼び出しに必要
     - KABUSYS_ENV — 実行モード: development | paper_trading | live （デフォルト: development）
     - PAPER_FILL_MODE — paper_trading の約定挙動: instant | partial | never | reject
     - PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト data/paper_trading.db）
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH — 監視用 SQLite（デフォルト data/monitoring.db）
     - PID_FILE_PATH — ExecutionEngine の PID ファイル（デフォルト data/execution.pid）
     - KILL_FLAG_PATH — KillSwitch のフラグファイル（デフォルト data/kill.flag）
     - MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — LINE アラートを利用する場合

   例 .env（用途に応じて編集）:
   KABUSYS_ENV=development
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=...
   JQUANTS_REFRESH_TOKEN=...
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db

6. データベース初期化
   - run_monitoring/run_execution 実行時に init_monitoring_db が呼ばれ、必要なテーブルは冪等で作成されます。特別な手順は不要です。

基本的な使い方
--------------

- 監視ループを起動（SystemMonitor 単体）
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を変更可能（デフォルト 60 秒）。
  - python -m kabusys.run_monitoring
  - 特記事項:
    - run_monitoring は Monitoring 用の SQLite を本番 sqlite_path（Settings.sqlite_path）で開きます。KABUSYS_ENV に関わらず本番 sqlite_path を使用します。
    - 起動時にプロセス優先度を "high" に試みます（psutil による設定。権限不足なら警告が出ます）。

- 実行エンジンを起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、paper_trading 用の DB（PAPER_TRADING_SQLITE_PATH）に分離して記録します。
  - PID ファイル（Settings.pid_file_path）を利用してプロセス生存チェックを行います。KillSwitch は data/kill.flag によって停止指示を出します。

- Streamlit ダッシュボード（監視 UI）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - DB を読み取り専用で開きます（存在しない場合は Monitoring を先に起動してください）。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH または環境変数 PAPER_TRADING_SQLITE_PATH

- AI 関連（プログラムから呼び出す）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - raw_news / news_symbols / ai_scores テーブルを使ってニュースごとのセンチメントを作成し ai_scores に書き込みます。
    - api_key が None の場合は環境変数 OPENAI_API_KEY を参照します。未設定だと ValueError。
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - ETF(1321) の MA とマクロニュース LLM スコアを合成して market_regime に書き込みます。
  - 両関数とも LLM 呼び出しはリトライ・フォールバックロジック（429/5xx 等）を備えています。

設定と挙動のポイント
--------------------
- 環境モード（Settings.env）
  - development / paper_trading / live の 3 種。paper_trading は発注系をモック化し、本番 DB と分離して動作します。
- .env の自動ロード
  - プロジェクトルート（.git または pyproject.toml を基準）を探索して .env / .env.local を読み込みます。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
- プロセス優先度 / CPU affinity
  - set_process_priority / set_cpu_affinity を utils/process_priority.py が提供。プラットフォーム差分（Windows / POSIX）を内部で吸収します。権限不足や未対応プラットフォームでは警告が出て続行します。
- KillSwitch
  - RiskMonitor がトリガー条件（ドローダウンやポジション上限）を検出すると data/kill.flag に理由を書き込み、ExecutionEngine に停止シグナルを送ります。既存フラグがある場合は上書きしません。flag 削除は KillSwitch.clear() を呼ぶか手動で削除してください。
- MonitoringDB マイグレーション
  - init_monitoring_db は既存 DB を破壊せずに必要なテーブル/カラムを追加（冪等）します。

ディレクトリ構成（抜粋）
------------------------
src/kabusys/
- __init__.py
- config.py                      — 環境変数 / Settings 管理 (.env ロード含む)
- run_monitoring.py              — SystemMonitor ポーリングループ起動スクリプト
- run_execution.py               — ExecutionEngine 起動スクリプト

パッケージ別:
- kabusys/monitoring/
  - monitoring_db.py              — SQLite 永続化層（テーブル作成含む）
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - monitoring_engine.py
  - alert_manager.py
  - kill_switch.py
  - streamlit_dashboard.py

- kabusys/execution/
  - order_manager.py
  - reconciler.py
  - order_repository.py (参照あり)
  - execution_engine.py (参照あり)
  - broker_factory.py (参照あり)
  - risk_manager.py (参照あり)
  - ...（発注関連の中心ロジック）

- kabusys/research/
  - factor_research.py             — momentum / volatility / value
  - feature_exploration.py         — forward returns / IC / summary
  - __init__.py

- kabusys/portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
  - __init__.py

- kabusys/ai/
  - news_nlp.py                    — ニュースの LLM センチメント付与
  - regime_detector.py             — 市場レジーム判定（MA + LLM）
  - __init__.py

- kabusys/tools/
  - paper_verification_report.py   — Paper Trading 検証レポート
  - __init__.py

- kabusys/utils/
  - process_priority.py
  - __init__.py

補足 / トラブルシューティング
------------------------------
- OpenAI API を使う機能を実行するには OPENAI_API_KEY が必要です。未設定だと例外になります。
- psutil によるプロセス優先度設定は管理者権限が必要な場合があります。権限不足だと警告が出ますが処理自体は続行します。
- streamlit ダッシュボードは監視 DB を読み取り専用で開きます。MonitoringEngine を先に起動してデータを生成してください。
- run_monitoring は MONITOR_POLL_INTERVAL を環境変数で上書きできます（整数秒）。不正な値が設定されているとデフォルト（60 秒）にフォールバックします。
- Paper Trading を試す場合は KABUSYS_ENV=paper_trading を設定すると実際のブローカー呼び出しを回避し、データを data/paper_trading.db に書きます（PAPER_TRADING_SQLITE_PATH で変更可）。

ライセンス・貢献
----------------
（このサンプルではライセンス情報は含まれていません。実プロジェクトでは LICENSE を追加してください。）

お問い合わせ・拡張
-----------------
- モデルや閾値の調整、追加の監視項目、外部通知先（Slack 等）への拡張は比較的容易に行えます。  
- AI 周りはモデル名（デフォルト gpt-4o-mini）やバッチサイズ、トリム文字数などが定数で管理されているため、要件に応じて調整してください。

以上がプロジェクト概要と利用方法の要点です。必要であれば、具体的な .env の例やよくある運用シナリオ（本番起動手順、Paper Trading のワークフロー、CLI の具体例）を追加で作成します。どの内容を優先しますか？