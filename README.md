KabuSys — README
=================

概要
----
KabuSys は日本株自動売買システムのコアライブラリ群です。本リポジトリは以下の主要機能を持つコンポーネントで構成されています。

- 注文管理・発注エンジン（ExecutionEngine / OrderManager / BrokerClientFactory 等）
- モニタリング（SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算、セクター制限など）
- リサーチ（ファクター計算・特徴量解析）
- AI 補助（ニュースの NLP スコアリング / 市場レジーム判定）
- 運用ツール（Paper Trading 検証レポート生成、Streamlit ダッシュボード）

設計方針の要点:
- 本番 DB と Paper Trading DB を明確に分離可能
- DuckDB を用いたファクタ計算／研究処理（ローカル DB を参照）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント／レジーム判定（API キーは環境変数で設定）
- 監視は SQLite（monitoring.db）へ永続化し、LINE での通知やファイルベースのキルスイッチを備える

主な機能一覧
--------------
- Execution
  - 注文作成 / 送信 / 同期（OrderManager, OrderRepository, Reconciler）
  - BrokerClientFactory を介して実際のブローカー or MockBroker を切替可能（KABUSYS_ENV）
- Monitoring
  - SystemMonitor: CPU / メモリ / ディスク / PID ファイル / データ鮮度監視
  - TradeMonitor: 滞留注文検出、約定価格異常検出
  - RiskMonitor: ドローダウン・ポジション上限監視、ダッシュボード更新
  - MonitoringEngine: これらを束ねてポーリング・アラート送信（LINE）
  - Streamlit ダッシュボード（読み取り専用モードで監視データを可視化）
- Portfolio
  - 候補選定、等重・スコア重み付け、ポジションサイズ計算、セクター制限、レジーム乗数
- Research
  - Momentum / Volatility / Value ファクター計算（DuckDB）
  - 将来リターン計算、IC（スピアマン）計算、統計サマリ
- AI
  - news_nlp.score_news(): ニュース記事をLLMで評価して ai_scores に書き込み
  - regime_detector.score_regime(): ETF(MA) + マクロニュースで日次レジーム判定
- Tools
  - Paper Trading 検証レポート生成ツール（kabusys.tools.paper_verification_report）
  - 各種起動スクリプト（run_execution.py, run_monitoring.py）

セットアップ手順
----------------

1. リポジトリをクローン
   - 例: git clone <repo-url>

2. Python 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - 必要な主要ライブラリ（例）
     - duckdb
     - psutil
     - requests
     - openai
     - streamlit (ダッシュボード利用時)
   - 例:
     - pip install duckdb psutil requests openai streamlit
   - （プロジェクトに requirements.txt があれば pip install -r requirements.txt）

4. データディレクトリ作成
   - mkdir -p data
   - デフォルトのファイルパス:
     - DuckDB: data/kabusys.duckdb
     - Monitoring SQLite: data/monitoring.db
     - Paper Trading SQLite: data/paper_trading.db
     - PID ファイル: data/execution.pid
     - Kill フラグ: data/kill.flag

5. 環境変数 / .env の準備
   - プロジェクトルートに .env（または .env.local）を置くと自動読み込みされます（OS 環境変数優先）。
   - 自動読み込みを無効にする場合: export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   - 主要な環境変数（抜粋）:
     - KABUSYS_ENV: development | paper_trading | live  (デフォルト: development)
     - JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必要なら）
     - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
     - OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: Monitoring SQLite（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH: Paper DB（デフォルト: data/paper_trading.db）
     - PAPER_FILL_MODE: instant | partial | never | reject（Paper Trading の約定挙動）
     - PID_FILE_PATH, KILL_FLAG_PATH, LOG_LEVEL 等
     - MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒。デフォルト 60）

6. 初期 DB 作成
   - run_monitoring.py や run_execution.py は起動時に監視用テーブルを自動で作成します（init_monitoring_db 呼び出し）。
   - したがって初回は run_monitoring を一度起動しておくと良いです。

使い方（主要コマンド）
---------------------

- ExecutionEngine を起動（本番 / paper_trading 切替）
  - 環境変数で挙動を切替:
    - 本番: export KABUSYS_ENV=live
    - Paper Trading: export KABUSYS_ENV=paper_trading
      - Paper Trading は専用の SQLite（PAPER_TRADING_SQLITE_PATH）へ記録し、本番 DB と分離されます。
      - PAPER_FILL_MODE により MockBroker の約定挙動を制御できます。
  - 起動コマンド:
    - python -m kabusys.run_execution
  - 補足:
    - 起動時にプロセス優先度を "high" に設定します（可能な場合）。
    - ExecutionEngine は pid ファイル（Settings.pid_file_path）を使ってプロセス存否を管理します。

- MonitoringEngine を起動
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング秒間隔を上書き可能（例: export MONITOR_POLL_INTERVAL=30）。
  - 起動コマンド:
    - python -m kabusys.run_monitoring
  - 説明:
    - 監視は常に Settings.sqlite_path（デフォルト data/monitoring.db）に記録します（KABUSYS_ENV に依らず）。
    - SystemMonitor は PID 存在チェックやデータ鮮度チェックを行い、RiskMonitor / TradeMonitor と連携します。
    - LINE 通知を有効にする場合は Settings.line_channel_access_token / Settings.line_user_id を設定してください。

- Streamlit 監視ダッシュボード
  - 起動例（読み取り専用で SQLite を開く）:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - ダッシュボードは monitoring.db を read-only で開きます。MonitoringEngine がデータを生成している必要があります。

- Paper Trading 検証レポート生成
  - コマンド:
    - python -m kabusys.tools.paper_verification_report
    - 期間指定例:
      - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    - DB 指定:
      - --db data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH でも指定可能）
  - 出力: 標準出力に指標（稼働率 / 注文成功率 / レイテンシ等）と PASS/FAIL 判定を表示します。

- AI 機能（スクリプト外から呼び出す場合）
  - ニューススコアリング:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key=os.environ.get("OPENAI_API_KEY"))
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key=os.environ.get("OPENAI_API_KEY"))
  - 注意:
    - API キー未設定のまま呼ぶと ValueError を送出します（明示的に渡すか OPENAI_API_KEY を設定してください）。
    - LLM 呼び出しはリトライ・フェイルセーフを持っていますが、失敗時はデフォルト値で継続する設計です。

設定周りの注意点
----------------
- .env 読み込み順序:
  - OS 環境変数 > .env.local > .env
  - プロジェクトルートは .git または pyproject.toml を基準に自動検出します。検出できない場合、自動ロードはスキップされます。
- 自動ロード無効化:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動 .env ロードをスキップします（テスト時に便利）。
- PID / Kill フラグ:
  - ExecutionEngine は pid ファイルを生成する想定です。監視プロセスは stale PID を検出するとファイルを削除してアラートを記録します。
  - KillSwitch は data/kill.flag を書き込むことで ExecutionEngine に停止要請を送ります。起動時に自動でクリアする挙動は Settings.kill_flag_clear_on_start で制御可能です。

ディレクトリ構成（抜粋）
-----------------------
以下は src/kabusys 内の主要ファイル・モジュールと役割の概略です。

- kabusys/
  - __init__.py
    - パッケージ定義・バージョン
  - config.py
    - 環境変数 / .env の読み込みと Settings クラス
  - run_execution.py
    - ExecutionEngine 起動スクリプト（KABUSYS_ENV による paper/live 切替）
  - run_monitoring.py
    - SystemMonitor 単体ポーリング起動スクリプト（MONITOR_POLL_INTERVAL 制御）
  - execution/
    - order_manager.py, reconciler.py, ...（発注ロジック、リコンシリエーション）
    - broker_factory.py（ブローカークライアント生成）
  - monitoring/
    - monitoring_db.py（SQLite スキーマ / CRUD）
    - system_monitor.py（CPU/メモリ/データ鮮度 / PID チェック）
    - trade_monitor.py（滞留注文 / 約定異常）
    - risk_monitor.py（ドローダウン / ポジション上限）
    - kill_switch.py（flag ファイルで停止シグナル）
    - alert_manager.py（LINE Push）
    - monitoring_engine.py（各モニタのオーケストレーション）
    - streamlit_dashboard.py（可視化）
  - portfolio/
    - portfolio_builder.py, position_sizing.py, risk_adjustment.py（ポートフォリオ構築）
  - research/
    - factor_research.py（ファクター算出）
    - feature_exploration.py（IC, forward returns, stats）
  - ai/
    - news_nlp.py（記事の LLM スコアリング）
    - regime_detector.py（市場レジーム判定）
  - tools/
    - paper_verification_report.py（Paper Trading 検証レポートツール）
  - utils/
    - process_priority.py（プロセス優先度 / CPU affinity 設定ユーティリティ）

運用上の留意点
---------------
- Paper Trading と本番 DB は意図的に分離されています。KABUSYS_ENV=paper_trading を使用すれば発注は MockBroker へ切替えられ、記録は PAPER_TRADING_SQLITE_PATH に残ります。
- AI 呼び出しは外部サービスに依存するため、API キー管理とレート制限に注意してください。news_nlp / regime_detector はエクスポネンシャルバックオフとフェイルセーフを備えていますが、費用・利用制限は運用側で管理してください。
- MonitoringEngine による通知は一方向（LINE Push）。トークン未設定時は送信をスキップします。
- ポートフォリオ構築関数やリサーチ関数は副作用を持たない純関数設計を基本とし、DuckDB / 引数でデータを受け取るようになっています。テストやオフライン分析に適しています。

開発・テスト
-------------
- コードは比較的モジュール化されています。ユニットテストを追加する場合、DuckDB/SQLite 接続をモックまたは一時ファイルで用意してください。
- news_nlp / regime_detector の外部 API 呼び出しは、テスト時に _call_openai_api を patch してモック可能です（所定の箇所にコメントあり）。

最後に
------
この README はコードベースから抜粋された情報を元にまとめています。実際に運用する際は .env.example（存在する場合）を参考に必要な環境変数を整備し、まずはローカル環境で Paper Trading モードおよびモニタリングを動かして挙動を確認してください。必要があれば README をプロジェクト実情に合わせて更新してください。