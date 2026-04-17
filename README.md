# KabuSys

日本株向け自動売買基盤のコアモジュール群です。監視（Monitoring）、発注実行（Execution）、ポートフォリオ構築、ファクター研究、AI（ニュースNLP / レジーム判定）などのコンポーネントを含みます。

以下はこのリポジトリのREADME.md（日本語）です。

---

目次
- プロジェクト概要
- 主な機能
- 前提条件 / 依存関係
- セットアップ手順
- 実行・使い方（コマンド例）
- 環境変数（主な設定）
- 停止 / フラグファイルについて
- ディレクトリ構成（概要）
- 主要コンポーネントの説明

---

プロジェクト概要
- KabuSys は日本株の自動売買システムのコアライブラリ群です。
- 発注エンジン、注文管理、リコンシリエーション、監視（システム状態／注文品質／リスク）、ポートフォリオ構築、ファクター算出、ニュースNLP を用いたセンチメント評価、ストリーミングダッシュボード等を含みます。
- DuckDB を使った調査・ファクター計算、SQLite を使った監視ログ/注文ログの永続化を行います。
- Paper Trading（検証）モードを備え、本番 DB と論理的に分離して検証可能です。

主な機能
- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク、Execution プロセス存在チェック、データ鮮度チェック
  - TradeMonitor: 注文滞留（stale orders）、約定価格の異常検出
  - RiskMonitor: ドローダウン／ポジション上限監視、Dashboard の永続化
  - AlertManager: LINE Push による通知（クールダウン管理）
  - KillSwitch: 条件で stop（kill.flag）を書き込み ExecutionEngine を停止させる
  - Streamlit ダッシュボード（監視表示）
- Execution
  - ExecutionEngine 起動スクリプト、OrderManager、OrderRepository、Reconciler、RiskManager、BrokerClientFactory（実装により本番/モック切替）
  - Paper trading モードでは MockBrokerClient を利用し DB を分離
- Portfolio
  - 候補選定、等重/スコア重み、リスク調整（セクター上限、レジーム乗数）、ポジションサイジング（単元丸め、aggregate cap）
- Research
  - ファクター計算（Momentum / Volatility / Value 等）
  - 特徴量探索、将来リターン計算、IC 計算、統計サマリ
- AI
  - news_nlp: OpenAI を用いたニュースからの銘柄センチメント算出（ai_scores テーブルへ書き込み）
  - regime_detector: ETF MA とマクロニュースを合成して市場レジーム（bull/neutral/bear）を判定・永続化
- Tools
  - paper_verification_report: Paper Trading DB を解析して検証レポートを出力

前提条件 / 依存関係
- Python 3.10 以上（型注釈に `|` を使用）
- 必要なライブラリ（一例）:
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit（ダッシュボード利用時）
- 実行環境により追加でブローカー SDK 等が必要（BrokerClientFactory に紐づく）

セットアップ手順（ローカル開発向け）
1. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール（例）
   - pip install duckdb psutil requests openai streamlit

   ※requirements.txt があれば `pip install -r requirements.txt` を推奨します。

3. 必要なディレクトリを作成
   - mkdir -p data

4. 環境変数設定
   - プロジェクトルートに .env / .env.local を置くと自動読み込みされます（自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。
   - 必須の環境変数例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
   - 詳細は次節「環境変数」を参照。

5. DB 初期化
   - 監視用 DB はスクリプト実行時に自動でテーブル作成が行われます（init_monitoring_db）。

実行・使い方（コマンド例）
- 監視ループ起動（バックグラウンド監視）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。

- ExecutionEngine 起動（発注エンジン）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient が利用され、data/paper_trading.db に書き込まれます（本番 DB と分離）。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションまたは環境変数 PAPER_TRADING_SQLITE_PATH で DB を指定できます。

- Streamlit 監視ダッシュボード起動
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - ダッシュボードは監視 DB を読み取り専用で開きます（起動中の MonitoringEngine が書き込む前提）。

- AI / レジーム判定・ニューススコア（プログラム呼び出し例）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは DuckDB 接続と target_date を受け取り、OPENAI_API_KEY を使います（引数で API キーを渡すことも可能）。

環境変数（主な設定）
- KABUSYS_ENV: 起動環境。development / paper_trading / live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector 等で使用）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: AlertManager（LINE通知）用
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（default: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（default: data/paper_trading.db）
- PAPER_FILL_MODE: Paper Trading の約定挙動（instant / partial / never / reject、デフォルト: instant）
- PID_FILE_PATH: pid ファイルパス（default: data/execution.pid）
- KILL_FLAG_PATH: kill.flag のパス（default: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: ExecutionEngine 起動時に kill.flag を消すか（"1" で有効）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）

停止 / フラグファイルについて
- 優雅な停止:
  - run_monitoring / run_execution はプロジェクトルートの data/stop_requested.flag を監視します。該当ファイルが存在するとループを抜けて終了します。
- KillSwitch:
  - リスク条件（ドローダウン超過 等）により data/kill.flag が書かれると ExecutionEngine は停止指示を受けます。KillSwitch は冪等に動作します（既存ファイルがあれば書き直さない）。
- PID ファイル:
  - ExecutionEngine は起動時に PID ファイルを作成します（デフォルト data/execution.pid）。SystemMonitor はこの PID を参照してプロセス生存をチェックします。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / .env ロジック（自動読み込み）
  - run_monitoring.py        — SystemMonitor のポーリングループ起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - utils/
    - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - __init__.py
    - monitoring_db.py       — monitoring 用 SQLite 永続化層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
    - streamlit_dashboard.py
  - execution/
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - execution_engine.py    — （実装参照ファイルは存在）
    - broker_factory.py
    - risk_manager.py
    - order_record.py
    - order_repository.py
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
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - data/                    — 実行時に使用する DB / フラグファイル等（例: data/monitoring.db）
  - tools/
    - paper_verification_report.py

（注）上記は主要モジュールのみ抜粋。実際の詳細はソースコードを参照してください。

主要コンポーネントの簡単な説明
- Settings（config.py）
  - .env /.env.local を自動ロード（ただし OS 環境変数が優先）。プロジェクトルートは .git または pyproject.toml を基準に探索します。
  - 各種パスや閾値、環境（development/paper_trading/live）などの取得を一元化します。

- MonitoringDB / MonitoringEngine
  - SQLite に system_status, trade_logs, risk_logs, positions, dashboard テーブルを持ち、各監視モジュールはここへログ・集計を残します。
  - MonitoringEngine は SystemMonitor / TradeMonitor / RiskMonitor を束ね、アラートや KillSwitch 評価を行います。

- ExecutionEngine / OrderManager / Reconciler
  - 発注のライフサイクル管理、ブローカー照合、クラッシュ後の自動復旧を担います。
  - Paper Trading モードは本番 DB とは分離された SQLite ファイルに記録されます。

- AI（news_nlp / regime_detector）
  - OpenAI API（gpt-4o-mini を想定）を用いたニュースセンチメント評価と市場レジーム判定。
  - API 呼び出しはリトライ・バックオフやレスポンス検証を組み込んでおり、失敗時はフォールバックする設計です。
  - api_key は引数で渡すか環境変数 OPENAI_API_KEY を使用します。

開発上の注意点 / 運用メモ
- Paper Trading は本番 DB を汚さないよう分離されていますが、設定ミスで本番 SQLite を参照しないよう注意してください（Settings.is_paper を確認）。
- .env ファイルのパースはシンプルな実装を含みます。特殊なクォートやエスケープがある場合は挙動に注意してください。
- OpenAI API 呼び出しはコストがかかります。ローカルテスト時はモック化（unittest.mock.patch）推奨。
- process priority / cpu affinity 設定は権限やプラットフォームに依存します。失敗時は警告を出してスキップします。

最後に
- ここで示したコマンドや設定はリポジトリ内のスクリプト群に対応しています。用途に合わせてモジュールを組み合わせ、運用ルール（kill.flag の運用やアラート閾値の調整等）を整備してください。
- 追加の質問や README に欲しい情報（例: より詳細な環境変数一覧、運用手順書、デプロイ方法など）があれば教えてください。必要に応じて README を拡張します。