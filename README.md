README
======

概要
----
KabuSys は日本株向けの自動売買・研究・監視を目的とした軽量フレームワークです。本リポジトリは以下の機能群を持ち、単体モジュールとして実行・組合せ可能な設計になっています。

- 注文送信・注文状態管理・再同期（ExecutionEngine／OrderManager／Reconciler）
- 監視（SystemMonitor／TradeMonitor／RiskMonitor／MonitoringEngine）
- Paper Trading 用の分離 DB と検証レポート出力
- ニュースの NLP による銘柄センチメント（OpenAI 利用）
- 市場レジーム判定（MA + LLM の組合せ）
- ポートフォリオ構築・配分・ポジションサイジング（純粋関数群）
- DuckDB を用いたファクター計算・リサーチユーティリティ
- Streamlit ベースの監視ダッシュボード

特徴
----
- モジュール単位での実行が可能（監視ループ、エンジン、レポート、ダッシュボード等）
- Paper Trading と Live の DB を完全に分離
- OpenAI を使ったニューススコアリングやレジーム判定をサポート（API キー必須）
- SQLite（監視ログ等）と DuckDB（履歴価格・ファクター計算）を併用
- シンプルなフラグファイル方式で外部からエンジン停止指示（kill.flag / stop_requested.flag）
- プロセス優先度や CPU affinity の簡易設定ユーティリティ付き

セットアップ
-----------
1. リポジトリをクローンし、Python 仮想環境を作成・有効化します。
   - 例（Unix/macOS）:
     - python -m venv .venv
     - source .venv/bin/activate

2. 依存ライブラリをインストールします（プロジェクトの requirements.txt がある想定）。
   - 代表的な依存:
     - duckdb
     - psutil
     - requests
     - openai
     - streamlit
   - 例:
     - pip install duckdb psutil requests openai streamlit

3. データディレクトリを作成します（必要に応じて）。
   - mkdir -p data

4. 環境変数を用意します。
   - プロジェクトルートに .env / .env.local を置くと自動で読み込まれます（OS 環境変数が優先）。
   - 自動読み込みを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

主な必要環境変数（例）
- JQUANTS_REFRESH_TOKEN (必須: J-Quants API 用)
- KABU_API_PASSWORD (必須: kabuステーション API 用)
- OPENAI_API_KEY (AI モジュール使用時に必須)
- KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
- PAPER_FILL_MODE: instant | partial | never | reject（paper_trading の約定挙動）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト data/paper_trading.db）
- SQLITE_PATH（監視 DB、デフォルト data/monitoring.db）
- DUCKDB_PATH（価格データ等の DuckDB ファイル、デフォルト data/kabusys.duckdb）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（通知に使用。未設定時は通知が送信されません）

使い方
------

実行可能スクリプト
- 監視ループ（SystemMonitor 単体でのポーリング）
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60）。
  - 実行例:
    - python -m kabusys.run_monitoring
    - あるいは python src/kabusys/run_monitoring.py
  - 監視は本番用 sqlite_path（Settings.sqlite_path）を常に使用します。

- Execution Engine（注文実行）
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して data/paper_trading.db に記録します（本番 DB とは分離）。
  - 実行例:
    - python -m kabusys.run_execution
    - あるいは python src/kabusys/run_execution.py
  - 停止は data/stop_requested.flag を作成することで外部から指示できます（KillSwitch は別途 data/kill.flag を書き込みます）。

- Paper Trading 検証レポート
  - データベース（paper_trading.sqlite）を集計してレポートを標準出力に出します。
  - 実行例:
    - python -m kabusys.tools.paper_verification_report
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    - オプション --db で DB パスを指定できます（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- Streamlit ダッシュボード（監視データの可視化）
  - 実行例:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - readonly モードで SQLite を開くため、監視プロセスが DB を書き込んでいる運用系でも表示可能です。

AI 関連
- kabusys.ai.news_nlp.score_news(target_date) / kabusys.ai.regime_detector.score_regime(target_date)
  - OpenAI API キーが必要です（OPENAI_API_KEY 環境変数、または関数引数で指定）。
  - 使用モデルは gpt-4o-mini（プロンプトやバッチサイズなどはコードで設定済み）。
  - レート制限・ネットワーク障害に対してリトライ・フォールバックの実装がありますが、API コストに注意してください。

DB 初期化
- run_monitoring / run_execution は起動時に init_monitoring_db() を呼んで監視用の SQLite スキーマを冪等的に作成します（テーブル・カラムのマイグレーション処理を含む）。

停止 / フラグファイル
- data/stop_requested.flag: run_monitoring / run_execution のポーリングループを優雅に終了させるためのフラグ（存在を検知するとループを抜けて終了）。
- data/kill.flag: KillSwitch が書き込むファイル。ExecutionEngine に対する強制停止シグナルとして機能します（存在するとエンジンは起動を阻止または停止処理を行います）。
- data/execution.pid: 実行中の ExecutionEngine が PID を書き込むファイル。SystemMonitor はこの PID の有無でプロセス生存を判定します。stale PID は自動で削除され、リスクイベントを記録します。

主要コンポーネント概要
- kabusys.config.Settings
  - 環境変数と .env の読み込み・検証を行う中心クラス。自動でプロジェクトルートの .env/.env.local を読み込みます（必要に応じて自動ロード無効化可）。

- kabusys.monitoring
  - MonitoringDB: SQLite に対する CRUD を提供（system_status / trade_logs / positions / risk_logs / dashboard）。
  - SystemMonitor / TradeMonitor / RiskMonitor: 各種監視ロジック。
  - MonitoringEngine: 各 Monitor を束ねポーリングを行う。AlertManager 経由で LINE 通知も可能。
  - KillSwitch: リスク閾値を満たした場合に kill.flag を書き、ExecutionEngine 停止を促す。

- kabusys.execution
  - ExecutionEngine（起動スクリプト側で組み立てて実行）
  - OrderManager / OrderRepository / Reconciler: 注文状態管理と再同期間合処理

- kabusys.portfolio
  - portfolio_builder, position_sizing, risk_adjustment: 候補選定、重み計算、単元株丸め、セクター制約、レジーム乗数等の純粋関数群

- kabusys.research
  - factor_research, feature_exploration: DuckDB を使ったファクター算出、将来リターン・IC 計算、統計サマリー

- kabusys.ai
  - news_nlp: ニュースを LLM に投げて銘柄スコアを生成・ai_scores に書き込み
  - regime_detector: MA200 とマクロ記事の LLM スコアを合成して market_regime テーブルに書き込む

環境変数の自動読み込み挙動
- プロジェクトルート（.git または pyproject.toml があるディレクトリ）を起点として .env（優先度低）と .env.local（優先度高）が自動で読み込まれます。
- OS 環境変数は常に優先され、.env の内容が上書きされることはありません（ただし .env.local は override=True で既存値を上書きしますが、読み込み時に保護された OS 環境変数は上書きされません）。
- 自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

ディレクトリ構成
----------------
以下は src/kabusys 配下の主要ファイルとディレクトリ（抜粋）です。

- src/
  - kabusys/
    - __init__.py
    - config.py                # 環境変数設定管理
    - run_monitoring.py        # SystemMonitor ポーリング起動スクリプト
    - run_execution.py         # ExecutionEngine 起動スクリプト
    - tools/
      - __init__.py
      - paper_verification_report.py  # Paper Trading 検証レポート
    - ai/
      - __init__.py
      - news_nlp.py            # ニュース NLP スコアリング（OpenAI）
      - regime_detector.py     # 市場レジーム判定（MA + LLM）
    - monitoring/
      - __init__.py
      - monitoring_db.py      # SQLite スキーマ・DB 操作
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - monitoring_engine.py
      - alert_manager.py
      - kill_switch.py
      - streamlit_dashboard.py
    - execution/
      - reconciler.py
      - order_manager.py
      - order_repository.py    # （参照のみ; DB 用）
      - ...                   # 実際の broker_factory 等の実装を含む
    - portfolio/
      - __init__.py
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - utils/
      - __init__.py
      - process_priority.py    # プロセス優先度・CPU affinity ユーティリティ
    - data/                    # 実行時に生成される（例: monitoring.db, paper_trading.db, kill.flag, execution.pid）
    - ...                      # そのほかモジュール群

開発メモ / 注意事項
------------------
- OpenAI 使用箇所は外部 API 呼び出しを行うため、API キー・レート制限・コストに注意してください。テスト時は _call_openai_api を patch して外部呼び出しをモックできます。
- Paper Trading モードを有効にするには KABUSYS_ENV=paper_trading を設定してください。Paper 用 DB はデフォルトで data/paper_trading.db が使用され、本番監視 DB とは分離されます。
- Monitoring の DB は init_monitoring_db() により自動で必要テーブル・カラムを作成します。互換性のためにマイグレーションロジックを簡易的に含めています。
- Streamlit ダッシュボードは読み取り専用で DB を開きます。監視プロセスが稼働中でもほぼ安全に閲覧可能です。

例: 簡単な起動フロー
1. 環境変数を設定（.env に JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD 等を記載）
2. 監視プロセスを起動:
   - python -m kabusys.run_monitoring
3. 別プロセスで ExecutionEngine を起動:
   - python -m kabusys.run_execution
4. 状況確認・ダッシュボード表示:
   - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
5. Paper 検証レポート:
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

ライセンス / 貢献
----------------
本 README はコードベースの説明に基づく技術ドキュメントです。実際のライセンス・貢献ルールはリポジトリの LICENSE / CONTRIBUTING ファイルを参照してください。

補足が必要な箇所（実行手順の詳細化、.env.example のテンプレート、依存関係ファイル等）があればお知らせください。README を拡張して具体的なコマンドやサンプル .env を追記します。