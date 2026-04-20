KabuSys — 日本株自動売買システム
=================================

概要
----
KabuSys は日本株向けの自動売買 / 研究 / 監視を目的とした Python パッケージ群です。  
主要機能は銘柄選定・配分計算、ポジションサイズ計算、ファクター計算・研究、AI（ニュース NLP / レジーム判定）、ExecutionEngine（発注系）の起動、監視（Monitoring）および各種ツール（ペーパートレード検証レポート等）を含みます。

主な設計方針
- DuckDB / SQLite をデータ層に利用（分析用と監視用を分離）
- 実行環境（development / paper_trading / live）により挙動を切替
- AI 部分は OpenAI API（gpt-4o-mini 等）を利用。API キーは環境変数で指定
- 監視は kill.flag 等のフラグファイルによるセーフガードを備える
- ログはコンソール + 日次ローテートファイルで統一管理

機能一覧
--------
- Execution
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - ブローカークライアントの抽象化（本番 / ペーパートレードを切替）
  - OrderManager / RiskManager / Reconciler 等による発注管理
- Monitoring
  - SystemMonitor, TradeMonitor, RiskMonitor を束ねる MonitoringEngine（run_monitoring.py）
  - kill.flag による ExecutionEngine 停止・通知（KillSwitch）
  - 監視データの永続化（SQLite）とダッシュボード更新
- Portfolio
  - 銘柄選定（select_candidates）
  - 重み計算（等配分 / スコア重み）
  - セクター制約、レジーム乗数、ポジションサイズ計算（単元株丸め・スケールダウン対応）
- Research
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
- AI
  - ニュース NLP による銘柄単位センチメントスコア（ai.news_nlp）
  - レジーム判定（ai.regime_detector） — MA200 とマクロニュースを合成
- Tools
  - Paper Trading 検証レポート生成（kabusys.tools.paper_verification_report）
- 設定 / ユーティリティ
  - 対話式 .env 作成ウィザード（config_setup.py）
  - 起動前設定検証 CLI（validate_config.py）
  - ログ設定ユーティリティ、プロセス優先度設定ユーティリティ等

セットアップ手順
----------------

前提
- Python 3.9+（コードの型・記法に合わせて適宜）
- システム依存のネイティブモジュール（psutil 等）が必要

基本手順（例）
1. リポジトリをクローン／配置
2. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 必要パッケージをインストール（プロジェクトに requirements.txt がある場合はそれを使用）
   - pip install duckdb psutil openai
   - （オプション）PyYAML があると config/*.yaml の内容検証を行える
4. .env を作成
   - 対話式ウィザード: python -m kabusys.config_setup
   - または手動で .env を作成（.env.example を参考）
5. 設定検証（推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱いにする
6. データディレクトリ等の準備
   - デフォルトで data/ 以下に DB や PID / flag ファイルが置かれます。適宜読み書き権限を確認してください。
7. ログディレクトリ
   - デフォルトは logs/。環境変数 LOG_DIR で変更可能

主要な環境変数（抜粋）
- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
  - KABU_API_PASSWORD — kabuステーション API パスワード
- 実行環境制御
  - KABUSYS_ENV (development | paper_trading | live) — デフォルト development
- DB パス
  - DUCKDB_PATH — デフォルト data/kabusys.duckdb
  - SQLITE_PATH — デフォルト data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH — paper_trading 用 DB（デフォルト data/paper_trading.db）
- ログ / PID / Kill-Switch
  - LOG_LEVEL — デフォルト INFO
  - LOG_DIR — ログ保存先ディレクトリ
  - PID_FILE_PATH — ExecutionEngine 用 PID ファイル（デフォルト data/execution.pid）
  - KILL_FLAG_PATH — Kill Switch ファイル（デフォルト data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0）
- ペーパートレード関連
  - PAPER_FILL_MODE — instant | partial | never | reject（デフォルト "instant"）
- AI
  - OPENAI_API_KEY — OpenAI API キー（ai 関連機能で必須）
- Monitoring
  - MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、デフォルト 60）

使い方
------

1. .env の準備
   - python -m kabusys.config_setup
   - 完了後、python -m kabusys.validate_config で検証

2. ExecutionEngine の起動
   - 本番 / 開発 / ペーパーは KABUSYS_ENV で切替
   - 起動（フォアグラウンド）
     - python -m kabusys.run_execution
   - 停止方法
     - プロセス自体を終了するか、停止フラグファイルを作成：
       - data/stop_requested.flag を作ると run_execution / run_monitoring のループが検知して終了します
     - または監視経由で kill.flag を書き込み、ExecutionEngine に停止を要求可能（KillSwitch が判定すると kill.flag が作成されます）

3. Monitoring の起動
   - python -m kabusys.run_monitoring
   - 環境変数 MONITOR_POLL_INTERVAL（秒）でポーリング間隔を上書きできます（デフォルト 60 秒）
   - 監視は Settings.sqlite_path にある監視用 SQLite DB を利用（monitoring は KABUSYS_ENV に関わらず本番 sqlite_path を使用）

4. Paper Trading（ペーパートレード）
   - KABUSYS_ENV=paper_trading とすると MockBrokerClient が使用され、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録されます

5. Paper Trading 検証レポート
   - python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD
   - --db で別 DB を指定可能（環境変数 PAPER_TRADING_SQLITE_PATH の代わりに使用）

6. AI 機能（ニューススコア・レジーム判定）
   - OpenAI API キー（OPENAI_API_KEY）が必須
   - ai.news_nlp.score_news(conn, target_date, api_key=None) — DuckDB コネクションを渡して実行
   - ai.regime_detector.score_regime(conn, target_date, api_key=None)

注意事項 / トラブルシューティング
- 権限
  - set_process_priority は OS により権限が必要になる場合があります。権限不足時は警告ログを出して続行します。
- OpenAI API
  - ネットワーク・RateLimit・5xx に対してはリトライ処理が組み込まれていますが、APIキー未設定の場合は例外になります。
- PyYAML
  - validate_config で YAML の内容検証を行うには PyYAML が必要です。未インストール時はスキップされ、警告が出ます。
- DB マイグレーション
  - monitoring_db.init_monitoring_db は冪等にテーブル・インデックスを作成し、既存スキーマに列を追加する簡易マイグレーションを含みます。

ディレクトリ構成（主要ファイル）
---------------------------------
- src/kabusys/
  - __init__.py
  - config.py               — 環境変数 / 設定管理
  - config_setup.py         — 対話式 .env ウィザード
  - validate_config.py      — 設定検証 CLI
  - run_execution.py        — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — Monitoring 起動スクリプト
  - utils/
    - logging_setup.py      — ログ設定ユーティリティ
    - process_priority.py   — プロセス優先度 / CPU affinity
  - execution/              — 発注系コンポーネント（Engine, BrokerFactory, OrderManager 等）
  - monitoring/
    - monitoring_db.py      — 監視用 SQLite 永続層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py           — ニュース NLP（OpenAI 呼び出し）
    - regime_detector.py    — レジーム判定
  - tools/
    - paper_verification_report.py

ログ / データファイル（デフォルト）
- logs/<app_name>.log       — 日次ローテーションログ（デフォルト logs/）
- data/monitoring.db        — 監視用 SQLite（SQLITE_PATH 環境変数）
- data/paper_trading.db     — ペーパートレード用 SQLite（PAPER_TRADING_SQLITE_PATH）
- data/kabusys.duckdb       — DuckDB（DUCKDB_PATH）
- data/execution.pid        — ExecutionEngine の PID（PID_FILE_PATH）
- data/kill.flag            — Kill Switch 用フラグ（KILL_FLAG_PATH）
- data/stop_requested.flag  — 手動停止フラグ（run_* スクリプトで監視）

最後に
-----
この README はコードベースの主要な使い方・設定指針をまとめたものです。実運用に入れる前に必ず python -m kabusys.validate_config による検証と、テスト環境での動作確認を行ってください。必要に応じて .env のバックアップ・シークレット管理を徹底してください。問題が発生した場合はログ（logs/）と SQLite / DuckDB の中身を参照して原因切り分けを行うことを推奨します。