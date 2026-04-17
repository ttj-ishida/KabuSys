KabuSys — README
=================

概要
----
KabuSys は日本株自動売買システムのコンポーネント群を集めた Python パッケージです。本リポジトリはトレーディング実行エンジン（ExecutionEngine）、監視モジュール（Monitoring）、ポートフォリオ構築ロジック、リサーチ／ファクター計算、AI（ニュース NLP / レジーム判定）などを含みます。設計方針として、可能な限り純粋関数／副作用を分離し、DB（SQLite / DuckDB）で状態を永続化する構成になっています。

主な特徴
--------
- ExecutionEngine 起動スクリプト（実運用 / paper_trading 切り替え）
  - paper_trading 環境では MockBroker を使って紙上取引用 DB に分離
- 監視（Monitoring）
  - SystemMonitor: CPU・メモリ・ディスク・プロセス存在確認、データ鮮度チェック
  - TradeMonitor: 注文滞留・約定異常価格検出
  - RiskMonitor: ドローダウン / ポジション上限の監視とダッシュボード更新
  - KillSwitch: 条件により停止フラグ（data/kill.flag）を書き込み ExecutionEngine を停止
  - AlertManager: LINE Messaging API による通知（クールダウン管理）
  - Streamlit ベースの監視ダッシュボード起動スクリプト
- ポートフォリオ構築ユーティリティ（選定・重み付け・ポジション決定・セクター制限）
- リサーチ（DuckDB を使ったファクター計算、将来リターン、IC、統計サマリー）
- AI モジュール
  - ニュースを OpenAI（gpt-4o-mini）でセンチメント化して ai_scores に書き込み
  - マクロニュース + ETF MA200 による市場レジーム判定（bull/neutral/bear）
- 各種ツール
  - Paper Trading 向け検証レポート生成スクリプト

セットアップ手順
----------------
※以下は最小限の手順例です。Python のバージョンは 3.10 以上を推奨します（| 型注釈等を使用しているため）。

1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo-root>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要ライブラリをインストール
   必要な代表パッケージ（プロジェクト内で使用）:
   - duckdb
   - psutil
   - requests
   - openai
   - streamlit

   例:
   - pip install duckdb psutil requests openai streamlit

   （実際の requirements.txt がある場合はそれを使用してください）

4. 環境変数 / .env
   - .env または .env.local に必要な環境変数を配置します。
   - 自動ロード順序: OS 環境 > .env.local (上書き) > .env（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）
   - 重要な環境変数（一部）:
     - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
     - JQUANTS_REFRESH_TOKEN: （必須）
     - KABU_API_PASSWORD: （kabuステーション API 用、必須）
     - OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
     - PAPER_FILL_MODE: paper_trading の約定挙動（instant | partial | never | reject）
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用 DB）
     - SQLITE_PATH: data/monitoring.db（監視 DB。Monitoring は常に本番 sqlite_path を使用）
     - DUCKDB_PATH: data/kabusys.duckdb
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: AlertManager 用
     - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL
     - MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）

5. データディレクトリ
   - デフォルトでは data/ 以下に sqlite/duckdb/pid/flag ファイルを書きます。必要に応じて作成してください。
   - 停止フラグ: data/stop_requested.flag（run_* スクリプトはこのファイルが存在すると停止）
   - Kill スイッチ: data/kill.flag（KillSwitch が書き込む）

使い方
------
主要スクリプトの起動方法と使い方例を示します。

1. 監視ループ（Monitoring）起動
   - python -m kabusys.run_monitoring
   - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可能（例: MONITOR_POLL_INTERVAL=30）

   備考:
   - 監視は Settings.sqlite_path（本番）を使用して monitoring テーブル群を初期化します。
   - 起動時にプロセス優先度を "high" に設定しようとします（psutil による）。

2. 実行エンジン（ExecutionEngine）起動
   - python -m kabusys.run_execution

   備考:
   - KABUSYS_ENV=paper_trading の場合は paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）を使用し、Mock ブローカーで分離実行されます。
   - 起動時に data/execution.pid に PID を書く等の管理を行います（停止フラグがある場合は起動しません）。
   - 実行中に data/stop_requested.flag を作成するとエンジンを停止できます。

3. Paper Trading 検証レポート生成
   - python -m kabusys.tools.paper_verification_report
   - 期間指定:
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - DB 指定:
     - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
   - デフォルト DB は data/paper_trading.db（PAPER_TRADING_SQLITE_PATH を参照）

4. Streamlit 監視ダッシュボード
   - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - 監視 DB が読み取り専用で開かれます（存在しない場合はエラー表示）

5. AI 系関数（プログラムから呼び出す）
   - kabusys.ai.score_news(conn, target_date, api_key=None)
     - raw_news を元に銘柄毎に ai_scores を作成します。api_key を渡すか OPENAI_API_KEY を環境変数に設定してください。
   - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
     - ETF(1321) の MA200 乖離とマクロ記事センチメントを統合して market_regime テーブルへ書き込みます。

内部 API / ライブラリの利用例
- ポートフォリオ構築:
  - from kabusys.portfolio import select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes, apply_sector_cap, calc_regime_multiplier
- リサーチ:
  - from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank

設定（Settings）について
-----------------------
設定は環境変数から読み込みます（.env/.env.local 自動読み込みあり）。主なプロパティ:
- jquants_refresh_token, kabu_api_password, kabu_api_base_url
- duckdb_path（デフォルト data/kabusys.duckdb）
- sqlite_path（デフォルト data/monitoring.db）
- paper_sqlite_path（デフォルト data/paper_trading.db）
- pid_file_path, kill_flag_path, kill_flag_clear_on_start
- cpu_threshold_pct, memory_threshold_pct, disk_threshold_pct
- env (development | paper_trading | live)、is_paper / is_live / is_dev
- paper_fill_mode（instant|partial|never|reject） — paper_trading の成行約定挙動

注意事項 / 実運用上のポイント
----------------------------
- 監視（Monitoring）は環境にかかわらず Settings.sqlite_path（本番監視 DB）を使用します。paper_trading でも監視は本番 DB を参照する点に注意してください。
- ExecutionEngine は paper_trading 環境のとき専用 DB に分離されます（PAPER_TRADING_SQLITE_PATH）。
- OpenAI を使う機能は API レート制限・エラーに対してリトライやフェイルセーフ（スコア 0.0 等）を実装していますが、API キーとコスト管理は必ず行ってください。
- PID / FLAG ファイルは data/ に作成されます。外部運用ツールからの停止指示は stop_requested.flag の作成や kill.flag の確認が利用されます。
- 依存ライブラリ（psutil 等）により管理者権限が必要になる場合があります。プロセス優先度/CPU affinity 設定は権限不足時はログに警告が出てスキップされます。

ディレクトリ構成（主要ファイル）
-----------------------------
src/kabusys/
- __init__.py
- config.py                — 環境変数 / Settings 管理
- run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
- run_execution.py         — ExecutionEngine 起動スクリプト

subpackages:
- ai/
  - news_nlp.py            — ニュース NLP（OpenAI）を使った ai_scores 書き込み
  - regime_detector.py     — 市場レジーム判定
- monitoring/
  - monitoring_db.py       — SQLite スキーマ + MonitoringDB ラッパー
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - alert_manager.py
  - monitoring_engine.py
  - streamlit_dashboard.py
- execution/
  - order_manager.py
  - reconciler.py
  - (その他実行エンジン関連モジュール)
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
  - __init__.py
- research/
  - factor_research.py
  - feature_exploration.py
  - __init__.py
- tools/
  - paper_verification_report.py
- utils/
  - process_priority.py

data/ (ランタイムで生成されることを想定)
- monitoring.db (または環境で指定した SQLITE_PATH)
- kabusys.duckdb (または DUCKDB_PATH)
- paper_trading.db (paper_trading 用)
- execution.pid, stop_requested.flag, kill.flag, etc.

テスト / 開発
-------------
- 各モジュールは副作用を抑えた設計（純粋関数、明示的な DB/接続注入）になっています。ユニットテストではモック（OpenAI 呼び出し、psutil、DB コネクション等）を利用してください。
- AI API 呼び出しはプライベート関数をモックすることで容易にテスト可能（コード内にその旨の注記あり）。

ライセンス / 参考
-----------------
- この README はソースコード内の docstring と実装を基に作成しています。実運用前に .env の整備、DB のバックアップ方針、OpenAI API キーの管理、ログ監視の設定を必ず行ってください。

以上。運用に際して不明点や追加で README に載せたい手順（例: systemd ユニット作成、Docker 化、CI 設定など）があれば教えてください。必要に応じて追記・テンプレート化します。