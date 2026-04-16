README
======

概要
----
KabuSys は日本株の自動売買・リサーチ・監視を想定した小規模なシステム群です。本リポジトリは以下の機能群を含みます:

- 市場データ・ファクター計算（DuckDB を使った Research）
- ポートフォリオ構築（候補選定・重み計算・ポジションサイジング）
- ExecutionEngine（ブローカーインターフェースを経由した発注管理、リコンシリエーション）
- 監視機能（システム状態・注文監視・リスク監視・Kill Switch）
- AI 補助（ニュースのセンチメント評価、レジーム判定。OpenAI を使用）
- 運用ツール（Paper Trading 検証レポート生成、Streamlit ダッシュボード）

主な設計方針:
- DuckDB と SQLite を使ったローカル分析・永続化
- Paper Trading モードでは本番 DB と分離（data/paper_trading.db）
- 外部 API 呼び出し（OpenAI / kabuステーション 等）は設定で有効化
- 監視は独立してポーリング実行し、フラグファイルで ExecutionEngine を停止可能

機能一覧
--------
主要コンポーネントと機能:

- kabusys.config.Settings
  - 環境変数 / .env(.local) から設定をロード・検証します。
  - KABUSYS_ENV (= development | paper_trading | live) を解釈。

- 実行スクリプト
  - run_execution.py: ExecutionEngine を起動。paper_trading 時は MockBroker を使用し DB を分離。
  - run_monitoring.py: SystemMonitor を定期ポーリングして監視ログを記録。

- 監視
  - SystemMonitor: CPU/メモリ/ディスク/プロセス状態・データ鮮度を監視。
  - TradeMonitor: 注文滞留・約定価格異常を検出。
  - RiskMonitor: ドローダウン・ポジション上限をチェック。
  - KillSwitch: 条件により data/kill.flag を書き込み、ExecutionEngine 停止を通知。
  - AlertManager: LINE Messaging API によるプッシュ通知（クールダウン付き）。
  - MonitoringDB: SQLite ベースの監視ログテーブルを作成・操作（system_status / trade_logs / positions / risk_logs / dashboard）。

- 運用ツール
  - tools/paper_verification_report.py: Paper Trading 結果の検証レポートを生成。
  - monitoring/streamlit_dashboard.py: Streamlit で監視ダッシュボードを表示。

- ポートフォリオ構築（pure functions）
  - portfolio.portfolio_builder: 候補選定・等重/スコア重み
  - portfolio.position_sizing: 株数算出・制約（lot_size、aggregate cap 等）
  - portfolio.risk_adjustment: セクターキャップ・レジーム乗数

- リサーチ
  - research.factor_research: Momentum / Volatility / Value ファクター計算（DuckDB）
  - research.feature_exploration: 将来リターン、IC、統計サマリ等

- AI 関連
  - ai.news_nlp: raw_news を LLM でスコアリング → ai_scores へ書き込み
  - ai.regime_detector: ETF マーケット指標 + マクロニュースで市場レジーム判定

セットアップ手順
----------------
前提:
- Python 3.10+（typing / match 等に合わせて適宜）
- system パッケージ: SQLite（標準）、DuckDB ライブラリ、psutil、requests、openai、streamlit 等

推奨手順（例）
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb psutil requests openai streamlit
   （プロジェクトに requirements.txt がある場合は pip install -r requirements.txt）

3. プロジェクトルートに .env を作成
   - .env.example がある場合は参考にしてください。主な環境変数例:

     JQUANTS_REFRESH_TOKEN=...
     KABU_API_PASSWORD=...
     OPENAI_API_KEY=...
     KABUSYS_ENV=development         # development | paper_trading | live
     PAPER_FILL_MODE=instant        # paper_trading 用: instant|partial|never|reject
     PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     SQLITE_PATH=data/monitoring.db
     DUCKDB_PATH=data/kabusys.duckdb
     LINE_CHANNEL_ACCESS_TOKEN=...
     LINE_USER_ID=...
     LOG_LEVEL=INFO

   - 自動ロードはデフォルトで有効（.env / .env.local をプロジェクトルートから読み込み）。
   - テスト等で自動ロードを無効にする場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

4. データディレクトリ
   - data/ を作成し、必要なら空の DB ファイルを作る（初回はコードが自動作成します）。
   - 実行中の PID / フラグファイルは data/execution.pid / data/kill.flag / data/stop_requested.flag 等を使用します。

使い方
------
基本的な実行例:

- 監視ループを起動（ポーリング）
  - 環境変数 MONITOR_POLL_INTERVAL で間隔秒を上書き（デフォルト: 60）
  - 実行:
    python -m kabusys.run_monitoring

  - 補足:
    - run_monitoring は監視用に本番 sqlite_path を常に使用します（KABUSYS_ENV に関係なく）。
    - 停止: data/stop_requested.flag を作成するとループは安全終了します。
    - プロセス優先度を "high" に設定します（psutil を使用、権限により失敗することがあります）。

- ExecutionEngine を起動（発注エンジン）
  - 実行:
    python -m kabusys.run_execution

  - 補足:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し paper_sqlite_path（デフォルト: data/paper_trading.db）に記録します（本番 DB と分離）。
    - 起動時に data/stop_requested.flag が存在する場合は起動を中止します。
    - 実行スレッドはバックグラウンドで run_session を実行し、stop フラグで停止可能です。

- Paper Trading 検証レポート生成
  - 実行:
    python -m kabusys.tools.paper_verification_report
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション --db で DB パスを指定可能（デフォルト: env または data/paper_trading.db）。

- Streamlit ダッシュボード
  - 実行:
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 監視 DB を read-only で開き、ポートフォリオダッシュボード・ポジション一覧・最近の発注・システム状態・最近のリスクログを表示します。

主要な環境変数（抜粋）
---------------------
- KABUSYS_ENV: development | paper_trading | live（必須。Settings で検証）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（ai モジュール使用時に必要）
- DUCKDB_PATH: DuckDB ファイル（default: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（default: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（default: data/paper_trading.db）
- PAPER_FILL_MODE: instant | partial | never | reject（paper_trading の約定挙動）
- PID_FILE_PATH / KILL_FLAG_PATH: 実行時ファイルパスの上書き
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、default 60）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL

運用上の注意
------------
- Paper Trading モードは本番 DB と明確に分離されます。実運用前に env を必ず確認してください（KABUSYS_ENV）。
- kill.flag / stop_requested.flag / execution.pid 等のフラグファイルを使ってプロセスの制御を行います。不要なファイルが残っていると起動や監視に影響します。
- OpenAI 等の外部 API 呼び出しはキーやレート制限に依存します。AI モジュールはエラー時にフェイルセーフ（スコア 0.0 等）で継続する設計になっていますが、ログを確認してください。
- process priority / CPU affinity の設定は OS と権限に依存します。設定に失敗しても処理は継続します（警告ログが出ます）。

ディレクトリ構成
----------------
（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数読み込み・Settings
  - run_execution.py             — ExecutionEngine 起動スクリプト
  - run_monitoring.py            — SystemMonitor 起動スクリプト
  - utils/
    - process_priority.py        — プロセス優先度・CPU affinity ユーティリティ
  - monitoring/
    - __init__.py
    - monitoring_db.py           — SQLite 監視テーブル初期化・CRUD
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - alert_manager.py
    - kill_switch.py
    - streamlit_dashboard.py
  - execution/
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - execution_engine.py       (実装ファイルがある想定)
    - broker_factory.py
    - broker_api.py             (インターフェース)
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
  - data/                        — 実行時に使う DB / フラグファイルを置くディレクトリ（例）
    - monitoring.db
    - paper_trading.db
    - kabusys.duckdb
    - execution.pid
    - kill.flag
    - stop_requested.flag
  - tools/
    - paper_verification_report.py
    - __init__.py

トラブルシューティング
-----------------------
- DB が存在しない / 読み込めない:
  - monitoring/streamlit_dashboard は読み取り専用で DB を開きます。MonitoringEngine を先に起動して DB を作成してください。
- 環境変数エラー:
  - Settings._require は必須キーが未設定だと ValueError を投げます。エラーメッセージに従い .env を確認してください。
- OpenAI 関連:
  - API キー未設定だと ai モジュールは ValueError を投げます。テスト時は環境変数や api_key 引数で指定してください。
- プロセス優先度・CPU affinity の設定は psutil に依存し、権限や OS によって失敗します。ログの警告を確認してください。

貢献・拡張のヒント
-------------------
- StrategyModel.md / PortfolioConstruction.md 等の仕様に基づく拡張ポイントが各モジュールにコメントで示されています。例えば:
  - position_sizing: 銘柄別 lot_size を導入する拡張
  - news_nlp: バッチサイズ・プロンプト調整・JSON レスポンスの堅牢化
  - regime_detector: マクロキーワードリストや重みのチューニング

ライセンス
----------
（この README にライセンス情報は含まれていません。プロジェクトルートに LICENSE がある場合はそちらを参照してください。）

おわりに
--------
この README はコードベース内の主要なモジュールおよび運用フローの概要をまとめたものです。実行時の詳細な挙動や追加オプションは各モジュールの docstring / ログメッセージを参照してください。必要であれば、特定の機能（例: AI スコアリングの動作、ExecutionEngine の設定）の詳細ドキュメントを別途作成します。