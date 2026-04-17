README
======

概要
----
KabuSys は日本株向けの自動売買・研究・監視を目的とした Python ベースのプロジェクトです。本リポジトリは以下の主要機能を備えます。

- 注文発行・状態管理（ExecutionEngine）
- 監視（System / Trade / Risk）とアラート（LINE 連携）
- ポートフォリオ構築（銘柄選定・重み計算・ポジションサイズ）
- リサーチ（ファクター計算・将来リターン・IC 等）
- AI 支援（ニュースセンチメントによるスコアリング・レジーム判定）
- Paper Trading 用検証レポート生成
- Streamlit による監視ダッシュボード

機能一覧
--------
主な機能とモジュール（抜粋）

- execution/
  - ExecutionEngine 起動・注文管理・リコンシリエーション（reconciler）
  - Broker クライアント抽象化（BrokerClientFactory）
  - OrderManager / OrderRepository（SQLite ベース）
- monitoring/
  - SystemMonitor: CPU/メモリ/ディスク、データ鮮度、実行プロセス監視
  - TradeMonitor: 注文滞留、約定価格異常検出
  - RiskMonitor: ドローダウン・ポジション上限監視
  - KillSwitch: 監視条件で実行エンジンを停止するフラグ生成
  - AlertManager: LINE Push による通知（クールダウン付き）
  - MonitoringDB: 監視ログ永続化（SQLite）
  - Streamlit ダッシュボード
- portfolio/
  - 銘柄選定（select_candidates）
  - 重み計算（等金額 / スコア重み）
  - セクターキャップ適用、レジーム乗数
  - ポジションサイズ計算（単元丸め・リスク制約対応）
- research/
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリ
- ai/
  - news_nlp: OpenAI を使ったニュースセンチメント集約 → ai_scores テーブル書き込み
  - regime_detector: ETF とマクロニュースを合成して市場レジーム判定
- tools/
  - paper_verification_report: Paper Trading DB から検証レポートを生成

セットアップ手順
--------------
前提
- Python 3.10+（typing | 区分 Optional 等を利用）
- git 等でリポジトリを取得済み

1) 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (# Windows: .venv\Scripts\activate)

2) 必要パッケージのインストール
   使用しているパッケージ（主要例）:
   - duckdb
   - psutil
   - openai
   - requests
   - streamlit

   例:
   - pip install duckdb psutil openai requests streamlit

   （プロジェクトに requirements.txt がある場合は pip install -r requirements.txt を使用）

3) 環境変数の準備
   プロジェクトルートに .env または .env.local を置くと、自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すれば無効化可能）。

   主要な環境変数（例）
   - JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
   - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
   - OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合に必須）
   - KABUSYS_ENV: 実行環境 (development | paper_trading | live)（デフォルト: development）
   - PAPER_FILL_MODE: Paper Trading の約定モード（instant | partial | never | reject）（デフォルト: instant）
   - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
   - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
   - DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
   - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用（任意）
   - LOG_LEVEL: ログレベル（DEBUG/INFO/...）

   例 .env（最小）
   - JQUANTS_REFRESH_TOKEN=your_token
   - KABU_API_PASSWORD=your_password
   - OPENAI_API_KEY=sk-...
   - KABUSYS_ENV=development

4) データディレクトリ
   - data/ 配下に SQLite / PID / flag ファイルが生成されます。必要に応じて mkdir -p data を作成してください。

使い方
------

実行系（ExecutionEngine）
- 本番 / Paper トレードの ExecutionEngine を起動します。
  - python -m kabusys.run_execution
  - 環境変数 KABUSYS_ENV=paper_trading を設定すると、Paper Trading 用のモックブローカーが使用され、データは data/paper_trading.db（PAPER_TRADING_SQLITE_PATH で上書き可）に記録されます。
  - 実行中は data/execution.pid に PID を書き込みます。data/stop_requested.flag を作成すると起動ループは停止します。

監視（Monitoring）
- 監視ポーリングループを起動します（SystemMonitor が定期的にチェックして monitoring DB に書き込み）。
  - python -m kabusys.run_monitoring
  - デフォルトポーリング間隔: 60 秒。環境変数 MONITOR_POLL_INTERVAL で上書き可能（秒）。
  - 監視は Settings.sqlite_path（デフォルト data/monitoring.db）を使用します。起動時に monitoring テーブルがなければ init_monitoring_db によって作成されます。
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用します（監視は常に本番 DB を想定）。

Streamlit ダッシュボード
- 監視 DB を読み取り専用で可視化します。
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

Paper Trading 検証レポート
- Paper Trading DB を解析してレポートを標準出力に出すツールです。
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パス変更:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

AI 関連
- ニュースセンチメントスコア取得:
  - kabusys.ai.score_news をプログラムから呼び出す（DuckDB 接続と target_date、OPENAI_API_KEY を渡す）。
- レジーム判定:
  - kabusys.ai.regime_detector.score_regime を呼び出す（DuckDB 接続と target_date、OPENAI_API_KEY を渡す）。
- 注意: OpenAI API 呼び出しはネットワーク・料金が発生します。テスト時は該当呼び出し関数をモックすることを推奨します。

停止・Kill 機構
- ExecutionEngine を強制停止したい場合はデータディレクトリの kill.flag（Settings.kill_flag_path、デフォルト data/kill.flag）に理由を含めて書き込むと、次の監視チェックで KillSwitch により停止シグナルが送られます。
- 一時的な停止要求には data/stop_requested.flag を使用します（run_* スクリプトがこれを見てループを破棄します）。

ディレクトリ構成（抜粋）
---------------------
src/kabusys/
- __init__.py
  - パッケージメタ情報
- config.py
  - 環境変数読み込み / Settings クラス（.env 自動読み込みロジック含む）
- run_execution.py
  - ExecutionEngine 起動スクリプト（PID 管理、paper_trading 切替）
- run_monitoring.py
  - SystemMonitor ポーリングループ起動スクリプト
- execution/
  - order_manager.py, order_repository.py, reconciler.py, execution_engine.py, broker_factory.py など
  - 注文管理・ブローカ連携・リコンシリエーション関連
- monitoring/
  - monitoring_db.py: SQLite テーブル定義 / 永続化 API
  - system_monitor.py / trade_monitor.py / risk_monitor.py
  - monitoring_engine.py: 各 Monitor をまとめるエンジン
  - alert_manager.py: LINE 通知
  - kill_switch.py: 停止フラグ生成
  - streamlit_dashboard.py: ダッシュボード
- portfolio/
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py
- research/
  - factor_research.py, feature_exploration.py
- ai/
  - news_nlp.py, regime_detector.py
- data/ （実行時に生成されることが期待される）
  - monitoring.db（監視用 SQLite、デフォルト path）
  - paper_trading.db（paper trading 用 DB）
  - kabusys.duckdb（DuckDB ファイル）
  - execution.pid / stop_requested.flag / kill.flag

補足・注意点
------------
- .env の自動読み込みは config._find_project_root() によりプロジェクトルート（.git または pyproject.toml）を探索して行われます。CWD に依存せずパッケージ後も機能します。
- 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env の自動読み込みを抑制できます（テスト用）。
- MonitoringDB のスキーマは init_monitoring_db により冪等に作成・マイグレーションされます。
- Paper Trading（KABUSYS_ENV=paper_trading）ではブローカーはモック実装を使い、本番 DB とは分離された PAPER_TRADING_SQLITE_PATH に記録します。
- OpenAI/API キーなどの秘匿情報は .env で管理し、リポジトリにコミットしないでください。

貢献・開発
----------
- 開発時は仮想環境を使い、lint / unit-test を整備してください。
- OpenAI 呼び出しなど外部依存はモックして単体テストを書くことを推奨します。

ライセンス
---------
- リポジトリに記載のライセンスファイルを参照してください（本 README にはライセンス情報は含めていません）。

以上。必要であれば README にサンプル .env.example や起動スクリプトの systemd ユニットサンプル、より詳しい設定項目一覧を追加します。どの情報を追加しますか？