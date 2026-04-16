KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買システムの一部（コアライブラリ・実行エンジン・監視・リサーチ・AI ユーティリティ）です。
このリポジトリには以下の主要機能を実装した軽量コンポーネント群が含まれます。

主な特徴
--------
- ExecutionEngine 起動スクリプト（run_execution.py）
  - 本番 / Paper Trading を環境変数 KABUSYS_ENV により切替可能
  - Paper Trading 時は MockBrokerClient を使い、専用 SQLite（data/paper_trading.db）にログを残す
  - 起動時に Reconciler による自動リコンシリエーションを実行
- Monitoring（run_monitoring.py）
  - System / Trade / Risk をポーリングして monitoring.db に永続化
  - Kill Switch（データに基づく停止指示）と LINE 通知によるアラート機能
  - Streamlit ベースの監視ダッシュボードを提供
- Portfolio コンポーネント（選定・重み・サイズ決定・リスク調整）
  - 等分 / スコア加重 / リスクベースの配分ロジック
- Research モジュール（DuckDB 経由でファクター計算・解析）
  - Momentum / Volatility / Value 等のファクター計算
  - 将来リターン計算、IC（スピアマン）や統計サマリー
- AI ユーティリティ
  - ニュースセンチメント（OpenAI）を使った銘柄ごとのスコアリング（kabusys.ai.score_news）
  - マクロニュース＋ETF MA を合成した市場レジーム判定（kabusys.ai.regime_detector.score_regime）
- CLI ツール
  - Paper Trading の検証レポート生成スクリプト（kabusys.tools.paper_verification_report）

セットアップ
----------
前提:
- Python 3.9+（type hint の Union 文法などに準拠）
- DuckDB と SQLite（Python バインディングで利用）
- ネットワークアクセス（OpenAI / LINE API を使う場合）

推奨依存パッケージ（例）
- duckdb
- psutil
- requests
- openai
- streamlit

インストール例
- 仮想環境を作成して pip インストール:
  - python -m venv .venv
  - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
  - pip install duckdb psutil requests openai streamlit

環境変数（主要）
- KABUSYS_ENV: 起動環境。allowed: development, paper_trading, live（デフォルト: development）
  - paper_trading: ブローカーは Mock、DB は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須な場合あり）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector 使用時）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: AlertManager が LINE へ通知する際に使用
- PAPER_FILL_MODE: paper_trading の注文約定モード。instant | partial | never | reject（デフォルト: instant）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite パス（デフォルト: data/paper_trading.db）
- SQLITE_PATH: Monitoring 用 SQLite パス（デフォルト: data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START など監視関連の設定
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）。不正値は 60 にフォールバック
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env/.env.local の自動ロードを無効化

.env 自動ロード
- プロジェクトルート（.git または pyproject.toml を起点）を探し、.env（上書き不可）→ .env.local（上書き可）の順で環境変数を読み込みます。
- 自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

使い方
------

実行エンジン（Execution）
- 本番（または開発）実行:
  - KABUSYS_ENV を適切に設定（例: export KABUSYS_ENV=live）
  - python src/kabusys/run_execution.py
  - 実行中、data/execution.pid に PID が書かれ、停止要求は data/stop_requested.flag または kill.flag により行います（kill_flag_path を Settings で上書き可能）。
- Paper Trading:
  - export KABUSYS_ENV=paper_trading
  - Paper 用 DB にログが残ります（PAPER_TRADING_SQLITE_PATH、デフォルト data/paper_trading.db）

監視（Monitoring）
- 起動:
  - python src/kabusys/run_monitoring.py
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で変更可能（例: export MONITOR_POLL_INTERVAL=30）
  - 監視は本番（Settings.sqlite_path）を使って常に monitoring DB を更新します（KABUSYS_ENV に依存しません）
  - 監視が kill.flag を生成する（KillSwitch）と ExecutionEngine に停止シグナルを送ります
- Streamlit ダッシュボード:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - ダッシュボードは SQLite を read-only モードで開くため、運用中でも安全に参照できます

Paper Trading 検証レポート
- コマンド:
  - python -m kabusys.tools.paper_verification_report
  - 例: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで別 DB を指定可能（例: --db /path/to/paper_trading.db）
  - 指標: 稼働率、注文成功率、送信率、P95 レイテンシ等を表示し PASS/FAIL を判定します

AI / リサーチ機能
- ニューススコアリング:
  - ライブラリ関数: kabusys.ai.score_news(conn, target_date, api_key=None)
  - DuckDB 接続を渡し、前日15:00 JST〜当日08:30 JST の記事を対象に OpenAI で集約スコアを生成し ai_scores テーブルに書き込みます
- レジーム判定:
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - ETF 1321 の MA とマクロニュースセンチメントから regime を判定して market_regime テーブルへ保存します
- OpenAI を利用する際は OPENAI_API_KEY を設定してください

停止・制御
- 停止フラグ: data/stop_requested.flag（run_execution/run_monitoring のローカル停止）を作成するとループが終了します
- Kill Switch: データ（ドローダウンやポジション上限）に応じて data/kill.flag が作成され、ExecutionEngine を停止させる仕組みがあります
- PID ファイル: data/execution.pid に ExecutionEngine の PID が書かれます。SystemMonitor はこの PID を参照してプロセス稼働を判断します

ディレクトリ構成（主要ファイル）
--------------------------------
- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数の読み込みと Settings クラス（各種パス・閾値・フラグ）
  - run_execution.py
    - ExecutionEngine 起動スクリプト（paper_trading の分離を含む）
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py
      - Paper Trading の検証レポート CLI
  - execution/
    - order_manager.py
    - order_repository.py (一部参照)
    - reconciler.py
    - execution_engine.py (起動/実行ロジック)
    - broker_factory.py (環境に応じた BrokerClient を生成)
  - monitoring/
    - monitoring_db.py
      - SQLite テーブル初期化 / 永続化ロジック
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
    - streamlit_dashboard.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - data/ (実行時に利用するファイル群)
    - monitoring.db (デフォルト)
    - paper_trading.db (paper_trading 用デフォルト)
    - kabusys.duckdb (DuckDB)
    - stop_requested.flag, kill.flag, execution.pid などの制御ファイル

実装上のポイント・注意点
-----------------------
- .env 自動読み込み機能はプロジェクトルートを探索して .env/.env.local を適用します（テスト時や特殊環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して無効化可）。
- Monitoring は Settings.env に関係なく本番用の sqlite_path（デフォルト data/monitoring.db）を用いる設計です。
- Paper Trading は本番 DB と分離されます（PAPER_TRADING_SQLITE_PATH を利用）。
- OpenAI 呼び出しはリトライ・バリデーション・部分失敗許容の実装がされており、失敗時はフェイルセーフ（スコア 0.0 やスキップ）で継続します。
- process priority / CPU affinity の設定を行うユーティリティ（kabusys.utils.process_priority）を用いてプロセス優先度を調整します（権限により失敗する場合があります）。

開発・デバッグ
--------------
- 単体テストやモジュール単位の実行を行う際は Settings の自動 env ロードの影響を考慮してください（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使うと安全）。
- DuckDB/SQLite のクエリはファイル参照になるため、テスト用の DB を用意してから関数を呼び出すと安全です。
- OpenAI 呼び出しは外部 API を使用するため、ユニットテストでは _call_openai_api をモックすることを推奨します（コード内にその想定があります）。

ライセンス・貢献
----------------
- 本 README ではライセンス情報を付記していません。実際の運用リポジトリでは LICENSE を配置してください。
- バグ修正・機能追加は Pull Request を通じて行ってください。大きな仕様変更は事前に Issue で議論してください。

付録：よく使うコマンド例
-----------------------
- 実行エンジン（Paper）:
  - export KABUSYS_ENV=paper_trading
  - python src/kabusys/run_execution.py
- 監視ループ:
  - python src/kabusys/run_monitoring.py
- Streamlit ダッシュボード:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- Paper 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- MONITOR_POLL_INTERVAL を 30 秒に設定して起動:
  - export MONITOR_POLL_INTERVAL=30
  - python src/kabusys/run_monitoring.py

問題や質問があれば、どの機能（Execution / Monitoring / AI / Research / Portfolio）について知りたいか教えてください。追加で README に含めたい詳細（環境変数例、サンプル .env、依存関係の固定など）を指定いただければ追記します。