KabuSys — 日本株自動売買システム
==============================

このリポジトリは日本株向けの自動売買／研究／監視ユーティリティ群をまとめた Python パッケージです。  
本 README はコードベース（src/kabusys 以下）に基づく概要、機能、セットアップ手順、起動方法、ディレクトリ構成を日本語でまとめたものです。

要約
----
- 自動売買実行エンジン（ExecutionEngine） と監視コンポーネント（MonitoringEngine）を備える。
- Paper trading（モックブローカー）用の分離DBをサポート。
- DuckDB を用いた研究（ファクター計算・特徴量解析）モジュールを含む。
- ニュースを LLM（OpenAI）で解析する AI モジュール（ニュースセンチメント / レジーム判定）。
- 監視結果を SQLite に永続化し、Streamlit ベースのダッシュボードで可視化可能。
- kill.flag による外部停止シグナル、LINE へのアラート送信機能あり。

主要な機能一覧
----------------
- Execution
  - 注文作成→送信→状態同期の管理（OrderManager、OrderRepository、Reconciler など）
  - Paper trading モードでは MockBroker を使い data/paper_trading.db に記録
- Monitoring
  - システム状態（CPU/メモリ/ディスク）と Execution プロセスの監視（SystemMonitor）
  - 注文滞留・約定異常の検出（TradeMonitor）
  - ドローダウン・ポジション上限の監視（RiskMonitor）と kill flag のトリガー
  - LINE push によるアラート送信（AlertManager）
  - Streamlit ダッシュボード（streamlit_dashboard.py）
- Research
  - Momentum / Volatility / Value 等のファクター計算（DuckDB 接続を受け取る純関数）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリ
- AI
  - ニュース記事の銘柄別センチメントスコアリング（OpenAI）
  - マクロニュース + ETF ma200 に基づく市場レジーム判定（OpenAI）
- Tools
  - Paper Trading 検証レポート生成スクリプト（paper_verification_report.py）
  - その他ユーティリティ群

前提 / 推奨環境
----------------
- Python 3.10 以上（型注釈や新しい構文を使用）
- 必要な Python パッケージ（最低限）:
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit（ダッシュボード利用時）
- OS: Linux / macOS / Windows（ただし process priority / cpu affinity はプラットフォーム依存の挙動あり）

セットアップ手順
----------------
1. 仮想環境作成（推奨）
   - python -m venv .venv
   - Windows: .venv\Scripts\activate
   - Unix/macOS: source .venv/bin/activate

2. 必要パッケージをインストール
   - 例（pip）:
     - pip install duckdb psutil requests openai streamlit
   - 実プロジェクトでは requirements.txt を用意して pip install -r requirements.txt を利用してください。

3. 環境変数 / .env
   - このモジュール群は .env /.env.local を自動で読み込む仕組みを持ちます（プロジェクトルートを .git または pyproject.toml で検出）。
   - 自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
   - 重要な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN — J-Quants API（必須な箇所あり）
     - KABU_API_PASSWORD — kabuステーション API パスワード
     - OPENAI_API_KEY — OpenAI を使う機能で必須（AI モジュール実行時）
     - KABUSYS_ENV — 実行環境（development / paper_trading / live）。デフォルトは development
     - LOG_LEVEL — ログレベル（DEBUG/INFO/...）
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH — Monitoring DB パス（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH — Paper trading 用 SQLite（デフォルト: data/paper_trading.db）
     - PID_FILE_PATH, KILL_FLAG_PATH 等は Settings クラスのプロパティ参照

   - .env のサンプル（.env.example を参考に）:
     JQUANTS_REFRESH_TOKEN=...
     KABU_API_PASSWORD=...
     OPENAI_API_KEY=...
     KABUSYS_ENV=development
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     PAPER_TRADING_SQLITE_PATH=data/paper_trading.db

4. データディレクトリ作成
   - data/ を作って DB ファイルや pid/flag を格納することを推奨:
     - mkdir -p data

使い方（主要なエントリポイント）
-------------------------------

- 監視ループ（Monitoring）
  - 実行スクリプト: src/kabusys/run_monitoring.py
  - 実行方法:
    - python -m kabusys.run_monitoring
    - あるいはパスを通した上で python src/kabusys/run_monitoring.py
  - 環境変数:
    - MONITOR_POLL_INTERVAL: ポーリング間隔（秒）。デフォルト 60。無効値（0以下等）はデフォルトにフォールバック。
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用（監視データは本番 DB を参照）。
  - 動作概要:
    - プロセス優先度を high にセット（可能な範囲で）
    - sqlite (monitoring DB) と duckdb を接続し SystemMonitor をポーリング

- 実行エンジン（Execution）
  - 実行スクリプト: src/kabusys/run_execution.py
  - 実行方法:
    - python -m kabusys.run_execution
  - 特記事項:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録。実口座と完全に分離されます。
    - 起動時に Reconciler による自動復旧処理が行われます。
    - 実行前に KILL_FLAG_CLEAR_ON_START を 1 にすると起動時に既存 kill.flag をクリアできます（Settings.kill_flag_clear_on_start を参照）。

- Paper Trading 検証レポート
  - スクリプト: src/kabusys/tools/paper_verification_report.py
  - 実行方法:
    - python -m kabusys.tools.paper_verification_report
    - オプション:
      --from YYYY-MM-DD
      --to YYYY-MM-DD
      --db PATH（PAPER_TRADING_SQLITE_PATH 環境変数の代替）
  - 出力: 注文成功率、送信率、稼働率、レイテンシ（P95）等のサマリと PASS/FAIL 判定

- Streamlit ダッシュボード
  - ファイル: src/kabusys/monitoring/streamlit_dashboard.py
  - 起動方法（コメント内推奨）:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - ダッシュボード機能: Overview / Positions / Orders / System タブで監視情報を可視化

- AI モジュール（ニュース NLP / レジーム判定）
  - 関数:
    - kabusys.ai.score_news(conn, target_date, api_key=None)
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - 必要: OpenAI API キー（api_key 引数 or 環境変数 OPENAI_API_KEY）
  - 注意:
    - API 呼び出しは失敗時にフォールバック（大抵は 0.0 やスキップ）する設計
    - レスポンス検証やリトライ（指数バックオフ）を実装済み

設定と挙動のポイント
-------------------
- Settings（kabusys.config.Settings）
  - 環境変数ベースで設定を取得。KABUSYS_ENV は development / paper_trading / live のいずれか。
  - PAPER_FILL_MODE（paper trading の約定振る舞い）: instant | partial | never | reject
  - DB パスはデフォルトで data/ 以下を使用（DuckDB / SQLite）
  - .env の自動読み込みはプロジェクトルートを .git または pyproject.toml から検出して実施

- Monitoring DB（kabusys.monitoring.monitoring_db.init_monitoring_db）
  - 起動時にテーブルを冪等に作成（system_status, trade_logs, positions, risk_logs, dashboard）
  - マイグレーションロジック（カラム追加）を含むので既存 DB に対しても対応

- プロセス優先度 / CPU affinity（kabusys.utils.process_priority）
  - set_process_priority("high") の呼び出しが起動スクリプトで使われている
  - Linux では nice 値の設定が試みられ、権限がない場合は警告を出してスキップ

ディレクトリ構成（主要ファイル）
------------------------------
以下は src/kabusys 配下の主要モジュール（本リポジトリの抜粋に基づく）です。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数・設定管理
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py
  - monitoring/
    - __init__.py
    - monitoring_db.py       — SQLite への永続化 API
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
    - streamlit_dashboard.py
  - execution/
    - order_manager.py
    - reconciler.py
    - ... (broker_factory, execution_engine, order_repository 等: 実行関連)
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
  - utils/
    - process_priority.py
    - __init__.py
  - data/ (想定)
    - <DuckDB / SQLite ファイル、pid/flag 等配置>

トラブルシューティング
-----------------------
- データベースが見つからない / 開けない
  - run_monitoring/run_execution は指定した DB パスにファイルがない場合、新規作成/テーブル作成しますが、streamlit の read-only URI で開けない場合は起動時にエラーになります。streamlit 起動時に --db パスを確認してください。
- OpenAI API キーが未設定
  - AI 機能は OPENAI_API_KEY が必須です。未設定だと ValueError が発生します（score_news / score_regime）。
- psutil 関連の権限エラー
  - 優先度変更や cpu_affinity の設定は権限問題で失敗することがあり、その場合は警告でスキップします。
- MONITOR_POLL_INTERVAL の無効値
  - 0 以下や整数変換できない値はログ警告の上デフォルト（60 秒）にフォールバックします。

開発上の注意
--------------
- 多くの関数は DuckDB / SQLite 接続を引数で受け取る純関数設計を心がけています。これによりユニットテストでのモックが容易です。
- datetime.today()/date.today() を直接参照しない設計が一部にあり（ルックアヘッドバイアス防止）、テストしやすい実装になっています。
- OpenAI 関連の API 呼び出し箇所はいずれもリトライ・バリデーションを備えフェイルセーフに設計されています。

ライセンス・貢献
----------------
- この README はコードベースから生成された説明です。実際のライセンス・貢献ポリシーはリポジトリに別途含めてください（LICENSE 等）。

以上が本プロジェクトの概要、使い方および構成の説明です。必要があれば、README に含めるサンプル .env.example のテンプレートや、よく使うコマンド群（systemd / supervisor 用の起動ユニット例）などを追加で作成しますのでお知らせください。