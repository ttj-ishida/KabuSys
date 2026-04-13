README
======

概要
----
KabuSys は日本株向けの自動売買システムのコンポーネント群です。本リポジトリには取引実行エンジン、監視（モニタリング）、ポートフォリオ構築ユーティリティ、ファクター/リサーチ用モジュール、LLM を使ったニュース解析・レジーム判定、運用補助ツール（レポート生成・Streamlit ダッシュボード）などが含まれます。

主な特徴
--------
- ExecutionEngine（発注・リスク管理・リコンシリエーション）
- MonitoringEngine（システム状態、滞留注文、価格異常、ドローダウン監視）
- Monitoring DB（SQLite）用の永続化層と操作ユーティリティ
- Portfolio construction（候補選定、重み計算、ポジションサイズ算出、セクター制限）
- Research ツール（ファクター計算、将来リターン、IC 計測、統計サマリー）
- AI コンポーネント（OpenAI を用いたニュースセンチメント評価・市場レジーム判定）
- 運用ツール（Paper Trading 検証レポート、Streamlit ダッシュボード）
- プラットフォーム差分を吸収するユーティリティ（プロセス優先度・CPU affinity）

動作要件
--------
- Python 3.9+（コードは型注釈を含むため 3.9 以上を推奨）
- 必要な主要パッケージ（例）:
  - duckdb
  - psutil
  - openai
  - requests
  - streamlit
  - （SQLite は標準ライブラリで利用）
- OS: Linux / macOS / Windows（ただし一部機能は OS に依存）

セットアップ手順
---------------
1. リポジトリをクローンしワークディレクトリへ移動
   - git clone ... && cd <repo>

2. 仮想環境を作成・アクティベート
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - pip install -U pip
   - pip install duckdb psutil openai requests streamlit

   （要件ファイルがある場合は pip install -r requirements.txt を使用してください）

4. 環境変数 / .env の準備
   - プロジェクトルートに .env または .env.local を置くと自動読み込みされます（既存の OS 環境変数を上書きしないのがデフォルト）。
   - 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

重要な環境変数（主要）
- KABUSYS_ENV: 起動環境。許容値: development, paper_trading, live（デフォルト: development）
  - paper_trading の場合、専用の paper_trading DB を使い本番 DB と分離されます。
- JQUANTS_REFRESH_TOKEN: J-Quants API のリフレッシュトークン（必須な箇所あり）
- KABU_API_PASSWORD: kabuステーション API 用のパスワード
- OPENAI_API_KEY: OpenAI API を使う機能（ニュース NLP / レジーム判定）で必要
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite DB（デフォルト: data/paper_trading.db）
- SQLITE_PATH: 監視用 SQLite DB（デフォルト: data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）※0 や負値は無効でデフォルトにフォールバック
- PID_FILE_PATH / KILL_FLAG_PATH 等: Execution/Monitoring 関連のファイルパス設定
- PAPER_FILL_MODE: paper_trading の MockBroker の動作 ("instant" | "partial" | "never" | "reject")

使い方（主要 CLI / モジュール）
--------------------------------

1) ExecutionEngine（取引実行）
- 本番 / paper_trading を切り替えるには KABUSYS_ENV を設定:
  - 本番: export KABUSYS_ENV=live
  - Paper: export KABUSYS_ENV=paper_trading
- 実行:
  - python -m kabusys.run_execution
  - 挙動: プロセス優先度を high に設定 → DB 接続（paper_trading は専用 DB）→ ブローカクライアント作成 → ExecutionEngine 起動

2) Monitoring（監視ポーリング）
- ポーリング間隔変更:
  - export MONITOR_POLL_INTERVAL=30  （秒）
- 実行:
  - python -m kabusys.run_monitoring
  - 挙動: プロセス優先度設定 → monitoring 用 SQLite に接続（環境にかかわらず本番 sqlite_path を使用）→ SystemMonitor のポーリング（デフォルト 60 秒）

3) Streamlit ダッシュボード（監視 UI）
- 起動:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- 説明: read-only モードで監視 DB を開き、ダッシュボードを表示します。MonitoringEngine が起動していないと DB が存在しない旨が表示されます。

4) Paper Trading 検証レポート
- レポート生成:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を明示:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
- 出力: 稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）などを表示し PASS/FAIL 判定を行います。

5) AI 系ユーティリティ（ニュース NLP / レジーム判定）
- 関数: kabusys.ai.score_news(conn, target_date, api_key=None)
  - raw_news / news_symbols テーブルから記事を集約し、OpenAI（gpt-4o-mini）でセンチメント評価して ai_scores テーブルへ書き込みます。
- 関数: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - ETF(1321) の MA200 乖離とマクロニュースの LLM 評価を合成して market_regime テーブルへ冪等書き込みします。
- 利用方法（対話 or スクリプト）:
  - Python REPL / スクリプト内で duckdb 接続を作成し関数を呼び出します:
    - import duckdb
    - conn = duckdb.connect("data/kabusys.duckdb")
    - from kabusys.ai import score_news
    - score_news(conn, date(2026, 4, 10), api_key="sk-...")

実行時の挙動・注意点
--------------------
- .env の自動ロード:
  - プロジェクトルート（.git または pyproject.toml を基準）から .env / .env.local を自動読み込みします。
  - OS の環境変数は保護され、デフォルトでは上書きされません。
  - 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Paper Trading と本番 DB の分離:
  - KABUSYS_ENV=paper_trading の場合、デフォルトで data/paper_trading.db を使用して本番 DB と完全分離します（安全対策）。
- Monitoring の DB:
  - monitoring は KABUSYS_ENV に依存せず常に settings.sqlite_path（デフォルト data/monitoring.db）を使用します。
- PID / kill flag:
  - ExecutionEngine は起動時に PID ファイルを書き、監視側（SystemMonitor）でプロセス生存確認をします。
  - KillSwitch は data/kill.flag を書くことで ExecutionEngine に停止シグナルを送る仕組みです。既存ファイルがあれば再書き込みしません（冪等）。
- OpenAI API:
  - API 呼び出しはリトライやエラー時のフェイルセーフを組み込んでいますが、API キー（OPENAI_API_KEY）の管理は運用者側で行ってください。
- ログレベル:
  - LOG_LEVEL 環境変数で変更可能（INFO デフォルト）。起動スクリプトは logging.basicConfig(level=logging.INFO) を呼ぶため環境で調整してください。

主要ファイル / ディレクトリ構成
-----------------------------
（src/kabusys をルートとする主要なファイル一覧）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / .env ローダ・Settings
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py — Paper Trading 検証レポート CLI
  - utils/
    - __init__.py
    - process_priority.py     — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - __init__.py
    - monitoring_db.py       — SQLite Monitoring DB 初期化・ラッパー
    - monitoring_engine.py   — 各 Monitor を束ねるエンジン
    - system_monitor.py      — CPU/メモリ/ディスク/データ鮮度/プロセス監視
    - trade_monitor.py       — 注文滞留 / 約定異常監視
    - risk_monitor.py        — ドローダウン / ポジション上限監視
    - alert_manager.py       — LINE Push 通知
    - kill_switch.py         — kill.flag 管理
    - streamlit_dashboard.py — Streamlit ダッシュボード
  - execution/
    - order_manager.py
    - reconciler.py
    - (その他: broker_factory, execution_engine, order_repository 等、実行に関連するモジュール)
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
    - news_nlp.py            — ニュース NLP / OpenAI 連携（ai_scores へ書込）
    - regime_detector.py     — マクロ＋MA200 によるレジーム判定
    - __init__.py

例: よく使うコマンド集
--------------------
- Execution 起動:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- Monitoring 起動:
  - MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
- Streamlit ダッシュボード:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- Paper レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-10

その他 / 運用メモ
-----------------
- DB マイグレーション: monitoring_db.init_monitoring_db() は冪等で、既存テーブルにカラムがない場合は ALTER TABLE による追加を行います（起動時に自動実行）。
- 単体関数群（portfolio、research 等）は副作用を持たない純粋関数として設計されており、ユニットテストが容易です。
- OpenAI 呼び出し部分はリトライやレスポンスバリデーションを入れており、部分的な失敗が他データを破壊しないよう設計されています。

ライセンス / 貢献
-----------------
- 本ドキュメントはコードベースを元に作成しています。実運用にあたっては必ずコードと .env.example（存在する場合）を参照し、適切なテストと安全対策を行ってください。開発・改善のプルリク歓迎です。

お問い合わせ
------------
- 実装や運用に関する詳細はソースコード内の docstring / コメントを参照してください。質問があればリポジトリの issue に記載してください。