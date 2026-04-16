KabuSys — 日本株自動売買システム
=================================

この README はリポジトリ内の主要コンポーネント（ExecutionEngine / Monitoring / Portfolio / Research / AI など）を使い始めるための最小限の説明書です。内部設計の詳細は各モジュールの docstring を参照してください。

対応 Python バージョン
- Python >= 3.10（型注釈に "X | None" 形式を利用しているため）

必須外部ライブラリ（例）
- duckdb
- psutil
- openai
- requests
- streamlit

インストール（例）
- 仮想環境を作成して依存をインストールしてください。
  - python -m venv .venv
  - source .venv/bin/activate
  - pip install --upgrade pip
  - pip install duckdb psutil openai requests streamlit

プロジェクト概要
-------------
KabuSys は日本株の自動売買システムの基盤ライブラリと実行コンポーネント群です。主な機能群は以下の通りです。

機能一覧
--------
- ExecutionEngine（発注・注文管理・リスク制御・再同期機能）
  - run_execution.py から起動可能。KABUSYS_ENV に応じて paper_trading（モックブローカー）と live の切り替えを行う。
  - 起動時に Reconciler による自動復旧を実施。
- Monitoring（プロセス・システム状態・注文・リスクの監視）
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine。
  - 監視ログは SQLite（デフォルト: data/monitoring.db）に永続化。
  - LINE によるアラート送信機能（AlertManager）。
  - Streamlit ダッシュボード（監視・ダッシュボード表示）。
- Portfolio（銘柄選定・重み付け・ポジションサイズ計算）
  - 等重み・スコア重み・リスクベースのポジションサイズ計算、セクター上限適用等。
- Research（ファクター計算・特徴量探索）
  - DuckDB 上の時系列データを用いたモメンタム／ボラティリティ／バリュー計算、IC 計算等。
- AI（ニュース NLP / レジーム判定）
  - OpenAI を用いたニュースセンチメント集計（ai_scores）と市場レジーム判定（market_regime）。
- ツール
  - paper_verification_report: Paper Trading の検証レポート出力（CLI）。
  - Streamlit ベースの監視ダッシュボード。

セットアップ手順
----------------

1. ソースチェックアウト
   - git clone ... あるいはソースを取得

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate

3. 依存パッケージのインストール
   - pip install duckdb psutil openai requests streamlit

4. データディレクトリの準備
   - mkdir -p data
   - 実行時に自動的に DB や PID/flag ファイルが作成されますが、必要に応じて事前に作成してパーミッションを調整してください。

5. 環境変数 (.env)
   - プロジェクトルートに .env（および .env.local）を置くと、起動時に自動読み込みされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 重要な環境変数（例）
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須の設定例）
     - KABU_API_PASSWORD: kabuステーション API パスワード（live 時必須）
     - OPENAI_API_KEY: OpenAI API キー（AI 機能利用時必須）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
     - PAPER_FILL_MODE: paper_trading での約定動作 ("instant" | "partial" | "never" | "reject")
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用（任意）

使い方（起動・ツール）
---------------------

1. 監視ループの起動（Monitoring）
   - デフォルトのポーリング間隔: 60 秒
   - 環境変数で上書き: MONITOR_POLL_INTERVAL（秒）
   - 実行:
     - python -m kabusys.run_monitoring
   - 動作:
     - プロセス優先度を "high" に設定し、SQLite / DuckDB を開いて SystemMonitor を定期実行します。
     - 停止はプロジェクトルート下 data/stop_requested.flag の存在で検知します。停止したい場合は touch data/stop_requested.flag。

2. 実行エンジンの起動（Execution）
   - paper_trading モード（モックブローカー・DB 分離）:
     - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
     - PAPER_TRADING_SQLITE_PATH（任意）で DB を指定可能
   - live モード:
     - KABUSYS_ENV=live として必須のブローカー設定（KABU_API_PASSWORD 等）を与えて起動
   - 実行:
     - python -m kabusys.run_execution
   - 停止 / 停止要求:
     - run_execution は data/stop_requested.flag を監視して安全に停止します。
     - KillSwitch（監視モジュール）が条件を満たすと Settings.kill_flag_path（デフォルト data/kill.flag）にフラグを書き、ExecutionEngine に停止指示を送ります（ExecutionEngine 側で kill.flag を参照して停止）。

3. Streamlit ダッシュボード（監視 UI）
   - 起動コマンド（ファイル内にヘルプあり）:
     - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - 監視用 SQLite DB を read-only で開きダッシュボードを表示します。

4. Paper Trading 検証レポート
   - CLI:
     - python -m kabusys.tools.paper_verification_report
     - 期間指定例:
       - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
     - DB 指定:
       - --db /path/to/paper_trading.db
   - 出力: 稼働率・注文成功率・送信率・レイテンシ等のサマリと PASS/FAIL 判定

5. AI（ニューススコア / レジーム判定）
   - OpenAI API キーが必要（OPENAI_API_KEY 環境変数または関数引数で指定）
   - ライブラリ関数呼び出し例（Python REPL / スクリプト内で実行）:
     - from datetime import date
       import duckdb
       from kabusys.ai import score_news
       conn = duckdb.connect('data/kabusys.duckdb')
       score_news(conn, date(2026, 4, 1), api_key='sk-...')
   - 実行結果は ai_scores / market_regime テーブルへ書き込まれます。
   - 実運用では API エラー時にフェイルセーフでスコアを 0 にする、リトライを行うなどの処理が組まれています。

運用時のフラグ / PID ファイル
---------------------------
- data/stop_requested.flag
  - run_monitoring.py / run_execution.py がループを終了するための外部停止フラグ（手動で作成してプロセスを停止）。
- data/execution.pid
  - ExecutionEngine の PID（Settings.pid_file_path で変更可）。SystemMonitor は PID ファイルが stale（存在するがプロセスが死んでいる）場合に削除してログを残す。
- data/kill.flag
  - KillSwitch が書き込む停止理由フラグ（ExecutionEngine に停止を促す用途）。Settings.kill_flag_path でパス指定可。

設定ファイル自動読み込み
---------------------
- プロジェクトルート（.git または pyproject.toml があるディレクトリ）を起点に .env と .env.local を自動ロードします（OS 環境変数が優先されます）。
- 自動ロードを無効化する場合:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

ディレクトリ構成（主要ファイル）
------------------------------
（これは src/kabusys をルートに見た簡易ツリーです）

- src/kabusys/
  - __init__.py                — パッケージ定義（バージョン等）
  - config.py                  — 環境変数 / Settings 管理（.env 自動読み込み）
  - run_monitoring.py          — SystemMonitor のポーリングループ起動スクリプト
  - run_execution.py           — ExecutionEngine 起動スクリプト

  - ai/
    - __init__.py
    - news_nlp.py              — ニュース NLP（OpenAI）で ai_scores を生成
    - regime_detector.py       — マクロセンチメント + MA200 でレジーム判定

  - monitoring/
    - __init__.py
    - monitoring_db.py         — SQLite テーブル作成 / MonitoringDB 抽象
    - system_monitor.py        — CPU/メモリ/ディスク / データ鮮度チェック
    - trade_monitor.py         — 注文滞留 / 約定価格異常検出
    - risk_monitor.py          — ドローダウン / ポジション上限監視
    - kill_switch.py           — kill.flag 書き込みロジック
    - alert_manager.py         — LINE による通知管理
    - monitoring_engine.py     — 各 Monitor を束ねる制御層
    - streamlit_dashboard.py   — Streamlit ベースの簡易ダッシュボード

  - execution/
    - order_manager.py         — 発注・状態遷移管理（OrderManager）
    - reconciler.py            — 起動時の再同期 / リコンシリエーション
    - ...                      — （ブローカー API 周り、ExecutionEngine 本体等はここに配置）

  - portfolio/
    - portfolio_builder.py     — 候補選定・等重・スコア重み
    - position_sizing.py       — 株数計算・集約キャップ・単元丸め
    - risk_adjustment.py       — セクターキャップ・レジーム乗数

  - research/
    - factor_research.py       — Momentum / Volatility / Value 等の計算（DuckDB）
    - feature_exploration.py   — 将来リターン・IC・統計要約

  - utils/
    - process_priority.py      — プロセス優先度 / CPU affinity 設定ユーティリティ
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成 CLI

設計上の注意点 / 運用メモ
------------------------
- Paper Trading は本番 DB と分離していて紙上検証用途に適しています（Settings.is_paper を利用）。
- Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計になっている部分があるため（run_monitoring 参照）、運用環境での DB パス設定には注意してください。
- OpenAI 呼び出し周りはリトライとフェイルセーフ（失敗時のデフォルト値）を備えていますが、API 使用料・レート制限に注意して運用してください。
- process priority / cpu affinity の設定は psutil に依存し、OS によって挙動や権限（root/管理者）が必要になる場合があります。
- DB マイグレーションは最小限（例: dashboard.peak_value の追加、trade_logs.latency_ms の追加）を init_monitoring_db が行います。既存データのバックアップは推奨します。

トラブルシューティング（よくある質問）
-----------------------------------
Q: 起動しても DB が見つからない / 開けない
A: run_monitoring や streamlit ダッシュボードで指定する DB パスが存在するか、パーミッションを確認してください。DuckDB/SQLite ファイルのパスは Settings の環境変数（DUCKDB_PATH / SQLITE_PATH）で変更できます。

Q: OpenAI API キーが無いときは？
A: AI 機能（news_nlp / regime_detector）は API キーが必要です。API を呼ぶ関数は api_key 引数を受け取るので、環境変数に入れたくない場合は引数で渡せます。

Q: 実行を止めたい（強制停止）
A: 停止を促すフラグファイルは data/stop_requested.flag（run_* スクリプト）と data/kill.flag（Execution 側の停止トリガ）です。touch で作成、rm で削除してください。

最後に
-----
各モジュールには詳細な docstring と運用上の注意が書かれています。運用を始める前に config.py と各 run_*.py、監視周り（kill_flag / stop flag / PID）の動作を必ず確認してください。README に書ききれない実装の前提や副作用（例: Settings が .env を自動読み込みする挙動）はコードの docstring を参照することを強く推奨します。