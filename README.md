# KabuSys

日本株自動売買システムのコアモジュール群（ライブラリ + 起動スクリプト群）。  
本リポジトリには実運用向けの ExecutionEngine / Monitoring / Research / Portfolio / AI 製品ロジックが含まれます。

以下はコードベースから抽出した README。起動・設定・主要機能・ディレクトリ構成の概要を日本語でまとめています。

---

目次
- プロジェクト概要
- 主な機能一覧
- 前提（依存ライブラリ・推奨）
- セットアップ手順
- 環境変数（主なもの）
- 使い方（コマンド例）
- 停止・Kill Switch
- ディレクトリ構成（抜粋）

---

プロジェクト概要
- KabuSys は日本株向けの自動売買フレームワークです。  
  - 注文管理、リスク制御、監視・アラート、ポートフォリオ構築、リサーチ（ファクター計算）、AI を使ったニュースセンチメント評価などを含みます。
- 起動スクリプトは実行モード（development / paper_trading / live）によって挙動が変わります（例：paper_trading では MockBroker を用いて paper DB に記録）。

主な機能一覧
- Execution
  - ExecutionEngine：ブローカークライアント経由の注文処理（risk manager、order manager、reconciler 等と連携）
  - paper_trading モードでは MockBroker を利用し、本番 DB と分離（data/paper_trading.db）
- Monitoring
  - SystemMonitor：CPU/メモリ/ディスク・プロセス PID・データ鮮度の監視
  - TradeMonitor / RiskMonitor：注文滞留、異常約定、ドローダウン／ポジション上限監視
  - KillSwitch：閾値超過時にフラグファイルを書き ExecutionEngine を安全停止
  - MonitoringEngine：各 Monitor を束ねて定期ポーリング・アラート送出
- Portfolio
  - 銘柄選定、重み計算（等配分・スコア加重）、ポジションサイズ計算、セクター制限、レジーム乗数など純粋関数群
- Research
  - ファクター計算（momentum / volatility / value）、将来リターン、IC 計算、統計サマリー
  - DuckDB を用いた分析用クエリ群（prices_daily / raw_financials 等参照）
- AI
  - news_nlp: OpenAI を使ったニュースセンチメント集約（ai_scores テーブルへ書き込み）
  - regime_detector: ETF（1321）MA200 の乖離 + マクロニュースで市場レジーム判定
- ツール
  - config_setup: 対話式 .env 作成ウィザード
  - validate_config: 起動前の設定検証 CLI
  - paper_verification_report: ペーパートレード結果の検証レポート生成

前提（依存ライブラリ・推奨）
- Python 3.9+
- 主な Python パッケージ（例）
  - duckdb
  - psutil
  - openai
  - sqlite3（標準）
  - PyYAML（config の YAML 検証を行う場合に任意）
- システム（Windows / Linux / macOS）対応。プロセス優先度や CPU affinity は OS による差異を吸収する実装あり。

セットアップ手順（ローカル開発向けの最小手順）
1. リポジトリをクローン／チェックアウト
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 必要パッケージをインストール
   - （プロジェクトに requirements.txt があれば）pip install -r requirements.txt
   - または最低限: pip install duckdb psutil openai
   - PyYAML を入れると validate_config による YAML 検証が有効になります
4. 環境変数を作成
   - 対話式ウィザード: python -m kabusys.config_setup
   - もしくは手動で .env を作成（.env.example を参照）
5. 設定検証（任意／推奨）
   - python -m kabusys.validate_config
   - --strict を付けると warning も fail 扱い（exit 1）
6. データディレクトリ・ログディレクトリ
   - デフォルトの DB / PID / フラグは data/ 以下に配置されます。必要に応じて .env でパスを調整してください。
   - デフォルトログディレクトリ: logs/

主要な環境変数（主なもの、デフォルト値含む）
- KABUSYS_ENV: execution モード。development / paper_trading / live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: （必須）J-Quants API 用トークン
- KABU_API_PASSWORD: （必須）kabuステーション API パスワード
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の約定モード（instant / partial / never / reject）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR: ログ保存先（デフォルト: logs/）
- PID_FILE_PATH: ExecutionEngine 用 PID ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: Kill Switch フラグファイル（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0）
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、デフォルト 60） ← run_monitoring で参照
- OPENAI_API_KEY: OpenAI API キー（ニュース NLP / レジーム判定で必要）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: 本番アラート用（任意）

使い方（主要コマンド）
- .env 作成（対話ウィザード）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- 実行エンジン起動（本番／paper_trading／development は KABUSYS_ENV に依存）
  - python -m kabusys.run_execution
  - 挙動: 起動時にプロセス優先度を "high" に設定、DB に接続、ExecutionEngine をスレッドで起動。data/stop_requested.flag を検知すると停止。
  - paper_trading モード時は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH に記録
- 監視ループ起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可能（例: MONITOR_POLL_INTERVAL=30）
  - run_monitoring は monitoring DB と duckdb に接続して SystemMonitor を起動
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定例: python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
- AI / Research 機能（プログラム API）
  - kabusys.ai.score_news(duckdb_conn, target_date, api_key=None)
    - raw_news / news_symbols / ai_scores を使って OpenAI に問い合わせて ai_scores を更新
    - OPENAI_API_KEY が必要（引数で上書き可）
  - kabusys.ai.regime_detector.score_regime(duckdb_conn, target_date, api_key=None)
    - ETF 1321 の MA200 乖離 + マクロニュースで regime 判定して market_regime テーブルに書き込む
  - research モジュール: calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic 等。DuckDB 接続を渡して使用

停止・Kill Switch
- 停止フラグ（外部停止）
  - data/stop_requested.flag を作成すると run_execution / run_monitoring のループが検知してシャットダウンします。
- Kill Switch（自動停止用）
  - KillSwitch が条件を満たすと KILL_FLAG_PATH（デフォルト data/kill.flag）を書き込みます。ExecutionEngine は起動時にこのフラグ存在を確認し、存在すれば起動を拒否します。
  - 本番環境では KILL_FLAG_CLEAR_ON_START=0 を推奨（自動クリアさせると危険）
- PID ファイル
  - 実行時に ExecutionEngine は PID を data/execution.pid に書きます（PID_FILE_PATH で上書き可能）

ログ
- setup_logging() によりルートロガーは stdout へ StreamHandler を出力し、ファイルは logs/<app_name>.log に日次ローテーションで出力（30日保持）します。ログディレクトリは LOG_DIR またはデフォルト logs/。

注意点・運用上の留意事項
- .env に機密情報（API トークン / パスワード）を含めるので絶対に Git 等にコミットしないでください。
- 本番（KABUSYS_ENV=live）では LINE 通知や kill フラグなどの設定を慎重に行ってください。validate_config にライブガードのチェックあり。
- OpenAI を使用する処理は API エラー時にリトライやフォールバック（0.0）を行う実装になっていますが、API キーやコスト管理は運用側で注意してください。
- DuckDB / SQLite のファイルはデフォルトで data/ 以下に作成されます。バックアップやストレージ確保を推奨します。

ディレクトリ構成（抜粋）
- src/kabusys/
  - __init__.py
  - config.py               — 環境変数 / 設定読み込みロジック（.env 自動ロード機能含む）
  - config_setup.py         — .env 対話式ウィザード
  - validate_config.py      — 設定検証 CLI
  - run_execution.py        — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — SystemMonitor 起動スクリプト
  - utils/
    - logging_setup.py      — 統一ロギング設定
    - process_priority.py   — プロセス優先度 / CPU affinity 設定
  - execution/               — Execution に関するモジュール群（broker_factory 等）
  - monitoring/
    - monitoring_db.py      — SQLite 永続化層
    - system_monitor.py
    - risk_monitor.py
    - trade_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - tools/
    - paper_verification_report.py
  - data/ (ランタイム生成想定)
    - monitoring.db (デフォルト sqlite)
    - paper_trading.db
    - kabusys.duckdb
    - execution.pid
    - kill.flag / stop_requested.flag

補足（よく使うコマンドまとめ）
- .env 作成: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config
- 実行エンジン起動: python -m kabusys.run_execution
- 監視ループ起動: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Paper 検証レポート: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

README はコード内の注釈に基づき要点をまとめたものであり、実運用前は必ず validate_config によるチェック、.env の確認、テストモード（paper_trading・development）での動作確認を行ってください。必要であれば追加のドキュメント（運用手順書、デプロイ手順、監視・アラート仕様）を作成することを推奨します。