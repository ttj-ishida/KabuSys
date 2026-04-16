KabuSys — 日本株自動売買システム
================================

このリポジトリは日本株自動売買システム「KabuSys」のコアライブラリ群です。  
戦略構築（ファクター計算、特徴量解析）、ポートフォリオ構成、発注実行、監視・アラート、Paper Trading 検証ツール、そして一部 AI（ニュース NLP / レジーム判定）を含みます。

プロジェクト概要
---------------
KabuSys は以下の責務を持つモジュール群で構成されています。

- research: ファクター計算・将来リターン計算・特徴量解析
- portfolio: 候補選定・重み計算・ポジションサイズ計算・リスク調整
- execution: ブローカーインタフェース・発注エンジン・リコンシリエーション
- monitoring: システム監視、注文監視、リスク監視、アラート（LINE）、監視DB、Streamlit ダッシュボード
- ai: ニュースのセンチメントスコアリング（OpenAI）や市場レジーム判定
- tools: Paper Trading 検証レポート生成スクリプト 等
- utils: プロセス優先度 / CPU affinity 等のユーティリティ
- config: 環境変数 / .env の読み込みと設定管理

主な特徴
---------
- DuckDB / SQLite を使ったデータ操作（prices_daily, raw_financials, raw_news 等を前提）
- ファクター（モメンタム、ボラティリティ、バリュー）とそれに基づく候補選定・配分
- position sizing（リスクベース／等分配／スコア加重）、単元株丸め、aggregate cap 対応
- ExecutionEngine / OrderManager / Reconciler による安全な発注管理と再起動後の復旧
- 監視エンジン（SystemMonitor / TradeMonitor / RiskMonitor）と KillSwitch による安全停止
- LINE への一方向アラート送信（AlertManager）と Streamlit ベースの監視ダッシュボード
- Paper Trading 用 DB 分離（KABUSYS_ENV=paper_trading）
- OpenAI を用いたニュース NLP（ai.news_nlp）およびレジーム判定（ai.regime_detector）
- ツール: Paper Trading の検証レポート生成スクリプト（kabusys.tools.paper_verification_report）

セットアップ手順
----------------

1. Python 環境（3.9+ 推奨）を用意
   - 仮想環境を作る例:
     python -m venv .venv
     source .venv/bin/activate  # Linux / macOS
     .venv\Scripts\activate     # Windows (PowerShell)

2. 依存パッケージをインストール
   - 必須（主要なもの）:
     pip install duckdb psutil requests openai streamlit
   - 実運用では requirements.txt を用意している場合はそれを使ってください。

3. 環境変数設定
   - プロジェクトルートに .env または .env.local を置くと自動的に読み込まれます（既存 OS 環境は保護）。
   - 自動ロードを無効化する場合:
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

   - 主な環境変数:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
     - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
     - OPENAI_API_KEY: OpenAI API キー（ai モジュール利用時）
     - PAPER_FILL_MODE: paper_trading 時のモック約定挙動: instant|partial|never|reject（デフォルト: instant）
     - PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
     - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知用
     - MONITOR_POLL_INTERVAL: 監視ループの間隔（秒、デフォルト: 60）
     - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START 等（Settings 参照）
     - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト: INFO）
     - CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT（監視しきい値）

4. data ディレクトリ（フラグ / PID / DB 等）
   - 実行前に data/ ディレクトリを作成しておくと運用がスムーズです。
     mkdir -p data

使い方
------

※いくつかのエントリポイントはモジュール化されており、python -m で起動できます。

1. 監視プロセスを起動
   - 監視ループ（SystemMonitor の単体実行）:
     python -m kabusys.run_monitoring
   - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き（秒単位）。例:
     export MONITOR_POLL_INTERVAL=30

   - 停止方法:
     - run_monitoring は data/stop_requested.flag の存在を検知して終了します。
     - 外部から停止したい場合は該当ファイルを作成してください:
       mkdir -p data; echo "stop" > data/stop_requested.flag

2. ExecutionEngine を起動（発注エンジン）
   - 通常実行:
     python -m kabusys.run_execution
   - Paper Trading（KABUSYS_ENV=paper_trading）:
     export KABUSYS_ENV=paper_trading
     python -m kabusys.run_execution
     - paper_trading モードでは MockBrokerClient を使用し、DB は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に分離されます。
   - 実行中の停止:
     - data/stop_requested.flag が作成されるとエンジンは停止を開始します。
     - KillSwitch（監視によって生成）により data/kill.flag が書かれると ExecutionEngine の起動を阻止するか停止する設計です。
   - PID ファイル:
     - 実行時に data/execution.pid (デフォルト) が使われます。SystemMonitor はこの PID を参照してプロセス生存チェックを行います。

3. Paper Trading 検証レポート
   - コマンド:
     python -m kabusys.tools.paper_verification_report
   - 期間指定:
     python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - DB 指定:
     --db オプションまたは環境変数 PAPER_TRADING_SQLITE_PATH を使えます。
   - 出力内容: 稼働率、注文成功率、送信率、レイテンシ統計、Pass/Fail 判定（閾値はソース内で定義）

4. 監視ダッシュボード（Streamlit）
   - 起動:
     streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - 監視 DB を読み取り専用で開き、ダッシュボードを表示します。

5. AI（ニュース NLP / レジーム判定）
   - OpenAI API キーが必要です（OPENAI_API_KEY）。
   - プログラム的に呼ぶ例（REPL 等）:
     from kabusys.ai.news_nlp import score_news
     from kabusys.ai.regime_detector import score_regime
     # conn は duckdb.connect(...) を渡す。target_date は datetime.date インスタンス。
   - 注意:
     - API 呼び出しはリトライ・フェイルセーフ機構を備えていますが、キー未設定の場合は例外が発生します。
     - LLM の応答は JSON 構造で取り扱うため、フォーマット要件に依存します。

運用上の重要ポイント
--------------------
- .env の自動読み込み:
  - プロジェクトルート（.git または pyproject.toml がある場所）が検出されれば .env を自動ロードします。
  - OS 環境変数は保護され、.env で上書きされません（.env.local では上書き可能）。
  - 自動ロードを無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

- DB 初期化 / マイグレーション:
  - monitoring_db.init_monitoring_db() は監視用 SQLite に対して必要なテーブルを冪等に作成します。
  - 既存の DB に対して schema 欄の追加（peak_value, latency_ms など）を行う軽微なマイグレーション処理が組み込まれています。

- 停止フロー:
  - 実行ループ（Monitoring / Execution）は data/stop_requested.flag による外部停止をサポートします。
  - KillSwitch（監視による）: リスク条件（ドローダウン超過やポジション上限超過）で data/kill.flag を書き込み、ExecutionEngine に停止を促します（冪等）。

- プロセス優先度:
  - run_monitoring / run_execution は起動時に set_process_priority("high") を呼び出します。psutil による設定で、権限不足時は警告を出して続行します。

ディレクトリ構成（主なファイル）
--------------------------------
以下はソースルート src/kabusys/ の代表的なファイル／パッケージです。

- src/kabusys/
  - __init__.py
  - config.py                  — 環境変数 / .env 読み込み・Settings
  - run_monitoring.py          — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - portfolio/
    - portfolio_builder.py
    - risk_adjustment.py
    - position_sizing.py
  - execution/
    - order_manager.py
    - reconciler.py
    - (その他: broker_factory, execution_engine, order_repository, order_record 等)
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
    - streamlit_dashboard.py
  - utils/
    - process_priority.py
  - data/ (実行時に使用する想定のディレクトリ)
    - monitoring.db (デフォルト)
    - paper_trading.db (paper_trading 用)
    - kabusys.duckdb (DuckDB)
    - execution.pid
    - stop_requested.flag
    - kill.flag

開発・拡張メモ
---------------
- DuckDB 接続は多数の research / ai モジュールで受け取る設計になっており、SQL と Python を組み合わせて処理します。
- AI モジュールは API 呼び出しの結果を検証して不正・部分失敗に耐える（フェイルセーフ）ように実装されています。
- position sizing / risk_adjustment の多くのパラメータは関数引数で変更可能で、戦略ごとのチューニングに向いています。
- モジュール設計はテスト容易性を考慮しており、外部 API 呼び出し箇所は差し替え可能（テストで patch しやすい実装）。

よくある質問（FAQ）
-------------------
Q: どの DB を編集するかはどう決まりますか？
A: Settings.is_paper により paper_trading モードでは PAPER_TRADING_SQLITE_PATH を使い、監視は環境にかかわらず監視用 sqlite_path（デフォルト data/monitoring.db）を使います。

Q: OpenAI を使うには？
A: OPENAI_API_KEY を設定してください。ai モジュールの一部関数はキー未設定時に ValueError を出します。

Q: 実運用で停止させたい場合はどうする？
A: data/stop_requested.flag を作ればループ中のプロセスはそれを検知して順次停止します。監視による強制停止は data/kill.flag を用います（KillSwitch が書き込みます）。

ライセンス / 貢献
-----------------
- 本リポジトリのライセンスや貢献ルールはこの README に追記してください（このサンプルには含まれていません）。

補足
----
- ソース内に多くのログ出力・警告・安全弁が実装されています。運用時は LOG_LEVEL を適切に設定し、監視ログを確認してください。
- 実際のブローカー接続や本番運用前に必ず Paper Trading で十分に検証してください。

---

必要であれば、README に含めるサンプル .env.example や systemd 用ユニット例、より詳細なコマンド一覧（デバッグ方法、ロギング設定、テストの実行方法）も作成できます。希望があれば教えてください。