README — KabuSys (日本語)
======================

概要
----
KabuSys は日本株向けの自動売買・研究・監視を目的とした Python コードベースです。
主な責務は以下のとおりです。

- 発注エンジン（ExecutionEngine）による発注・注文状態管理・リコンシリエーション
- 監視機能（MonitoringEngine / SystemMonitor / TradeMonitor / RiskMonitor）によるプロセス監視・リスク検知・アラート送信
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算、セクター制約）
- 研究用モジュール（ファクター計算、将来リターン、IC 計算など）
- AI サービス連携（ニュースのセンチメント評価、レジーム判定） — OpenAI を利用
- Paper Trading 用の分離された DB と検証ツール（paper_verification_report）
- 監視ダッシュボード（Streamlit）

主要機能一覧
------------
- Execution
  - 実際のブローカー／Mock ブローカーを選択して起動（KABUSYS_ENV により paper_trading をサポート）
  - OrderManager、OrderRepository、Reconciler による注文の管理と再同期
  - リスク管理（RiskManager）による注文拒否・利用率制限など

- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク・データ鮮度・実行プロセス監視
  - TradeMonitor: 滞留注文・約定異常価格の検知
  - RiskMonitor: ドローダウン・ポジション上限の検知と kill flag / アラート生成
  - AlertManager: LINE Messaging API への通知（クールダウン付き）
  - Streamlit ダッシュボード（read-only で monitoring DB を表示）

- Portfolio
  - 候補選定、等重・スコア重み、リスクベースのポジションサイジング
  - セクター集中の抑制、レジームに応じた投下資金乗数

- Research
  - ファクター計算（Momentum, Value, Volatility, Liquidity）
  - 将来リターン・IC・統計サマリ等

- AI
  - news_nlp.score_news: OpenAI を用いたニュースセンチメントを銘柄ごとに算出して ai_scores に書き込み
  - regime_detector.score_regime: ETF の MA とマクロニュースの LLM センチメントを合成し市場レジームを判定

前提条件
--------
- Python 3.9+
- システムに応じたライブラリ（例: DuckDB、psutil、requests、openai、streamlit 等）
- (任意) LINE 通知を使う場合は LINE チャネルアクセストークン
- OpenAI を使う機能は OPENAI_API_KEY が必要

推奨インストールパッケージ（例）
- duckdb
- psutil
- requests
- openai
- streamlit
- sqlite3 は標準付属（Python）
- その他、ローカル環境で動かす際に必要なものがあればプロジェクトの requirements.txt を作成して利用してください。

環境変数（主要）
----------------
（プロジェクトは .env / .env.local を自動ロードします。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1）

必須（実行する機能による）
- JQUANTS_REFRESH_TOKEN — J-Quants API（研究機能などで必要）
- KABU_API_PASSWORD — kabuステーション API（実運用時）
- OPENAI_API_KEY — OpenAI API（news_nlp / regime_detector を使う場合）

任意・デフォルトあり（代表例）
- KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
- KABU_API_BASE_URL: kabusapi の base URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — AlertManager 用
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- PAPER_FILL_MODE: instant | partial | never | reject（paper_trading の約定挙動）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START
- MONITOR_POLL_INTERVAL（監視ポーリング間隔を秒で上書き、デフォルト 60 秒）

セットアップ手順
---------------
1. リポジトリをクローンし、作業ディレクトリに移動
   - (パッケージが src/ 配下にある場合) PYTHONPATH に src を含めるか、プロジェクトルートで実行することを想定

2. Python 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb psutil requests openai streamlit
   - 他に必要なパッケージがあれば追加でインストールしてください

4. .env を配置（任意）
   - プロジェクトルートに .env / .env.local を置くと自動的に読み込まれます
   - 例（.env）:
     KABUSYS_ENV=development
     OPENAI_API_KEY=sk-...
     KABU_API_PASSWORD=your_kabu_password
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db

5. data ディレクトリの準備（自動作成される箇所もありますが手動で用意しておくと良い）
   - mkdir -p data

使い方（起動コマンドと説明）
--------------------------

- ExecutionEngine の起動
  - 本番（live）モード:
    KABUSYS_ENV=live python -m kabusys.run_execution
  - Paper Trading（MockBroker / 分離 DB）:
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - paper_trading の場合、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に書き込まれます
  - 特記事項:
    - 起動時にプロセス優先度を high に設定しようとします（権限不足で失敗することがありますが警告のみ）
    - data/stop_requested.flag が存在する場合は起動を中止・停止します
    - PID ファイルを data/execution.pid に書き込みます（Settings.pid_file_path で変更可能）

- MonitoringEngine の起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を設定可能（デフォルト 60）
  - 監視は Settings.sqlite_path（デフォルト data/monitoring.db）を使用します（monitoring は環境にかかわらず本番 sqlite_path を使用する設計です）
  - stop フラグ（data/stop_requested.flag）を検知するとループを終了します

- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 監視 DB を読み取り専用で開き、Overview / Positions / Orders / System のタブを表示します

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11 --db data/paper_trading.db
  - オプション --from / --to（YYYY-MM-DD）で期間を指定。--db で DB パスを指定可能（指定がない場合は PAPER_TRADING_SQLITE_PATH 環境変数またはデフォルトを使用）

- AI 機能（ライブラリ API）
  - news_nlp.score_news(conn, target_date, api_key=None)
    - DuckDB 接続を渡し、指定日（date）に対するニューススコアを ai_scores テーブルに書き込む
    - api_key 未指定時は環境変数 OPENAI_API_KEY を使用
  - regime_detector.score_regime(conn, target_date, api_key=None)
    - 同様に市場レジームを計算して market_regime テーブルへ書き込む

運用上の注意・停止方法
---------------------
- 強制停止（ExecutionEngine を止めたい場合）
  - data/kill.flag を書くための KillSwitch が存在します。KillSwitch は条件に応じて kill.flag を作成します。
  - 手動で ExecutionEngine を終了させたい場合は data/stop_requested.flag を作成すると起動中プロセスが検知して停止します（run_execution/run_monitoring は stop フラグの存在を監視します）。

- Paper Trading と本番 DB は分離されています（paper_trading は PAPER_TRADING_SQLITE_PATH を使用）

- OpenAI API 呼び出しはネットワークエラーや 429 に対してリトライ実装がありますが、API キー未設定時は ValueError を投げます。API キーは厳重に管理してください。

ディレクトリ構成（概要）
----------------------
以下は主要ファイル/ディレクトリの抜粋（src/kabusys 配下）。

- src/kabusys/
  - __init__.py
  - config.py                   — 環境変数 / Settings 管理（.env 自動ロード）
  - run_execution.py            — ExecutionEngine 起動スクリプト
  - run_monitoring.py           — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート
  - ai/
    - news_nlp.py               — ニュース NLP（OpenAI）
    - regime_detector.py        — 市場レジーム判定（OpenAI）
  - monitoring/
    - monitoring_db.py          — monitoring DB の初期化・永続化レイヤ
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - alert_manager.py
    - monitoring_engine.py
    - kill_switch.py
    - streamlit_dashboard.py
  - execution/
    - order_manager.py
    - reconciler.py
    - ... (broker_factory, execution_engine, order_repository 等)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - utils/
    - process_priority.py        — プロセス優先度 / CPU affinity ユーティリティ
  - data/ (期待されるランタイムディレクトリ)
    - monitoring.db (デフォルト SQLITE_PATH)
    - kabusys.duckdb (デフォルト DUCKDB_PATH)
    - paper_trading.db (PAPER_TRADING_SQLITE_PATH)
    - execution.pid
    - stop_requested.flag
    - kill.flag

開発者向けメモ
---------------
- .env の自動ロードはプロジェクトルート（.git または pyproject.toml を基準）を探索して行われます。テストで自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- process priority / cpu affinity の設定は OS によって動作が異なり、権限不足で失敗することがあります（警告ログに留まる）。
- DuckDB に対する executemany の挙動（空パラメータ不可など）に注意して実装されています。
- AI 呼び出し部分は外部 API（OpenAI）に依存するため、テスト時は内部の _call_openai_api をモックすることが想定されています。

トラブルシューティング（よくある問題）
-----------------------------------
- permissions: プロセス優先度変更で AccessDenied が出る場合は無視するか root/管理者で再試行してください（警告ログ）。
- DB が開けない: パスが正しいか（相対/絶対）、ファイルが存在するか確認してください。Streamlit は read-only URI で開きます。
- OpenAI: API key がないとニュース NLP / レジーム判定は動作しません。環境変数 OPENAI_API_KEY を設定してください。
- MONITOR_POLL_INTERVAL に 0 や負の値を入れるとデフォルトにフォールバックします（ログ出力あり）。

ライセンス・貢献
----------------
（本リポジトリにライセンスファイルがあればその記載に従ってください）

以上。必要であれば README にサンプル .env.example、requirements.txt、運用手順（systemd / supervisor 用の unit サンプル）や詳細なアーキテクチャ図の追記を行います。どの内容を追加したいか教えてください。