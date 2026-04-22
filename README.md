KabuSys — 日本株自動売買システム（README 日本語版）

概要
- KabuSys は日本株向けの自動売買・リサーチ基盤のコードベースです。  
  主な責務は「シグナル生成 → ポートフォリオ構築 → 発注（ExecutionEngine）」「実行監視（Monitoring）」「研究用ファクター計算」「ニュース NLP によるセンチメント評価」などを提供します。  
- 設計方針の要点: 本番／ペーパーを分離した DB 設計、DuckDB を使ったリサーチ、OpenAI を使ったニュース解析（任意）、監視／Kill Switch による安全停止機構。

主な機能
- ExecutionEngine: ブローカープラグイン経由で発注を行うエンジン（KABUSYS_ENV に応じて MockBroker を使用可能）。
- Monitoring: CPU/メモリ/ディスク、プロセス生存、注文/約定の監視、Kill Switch による自動停止。
- Portfolio モジュール: 候補選定、重み付け、ポジションサイズ計算、セクター制限などの純粋関数群。
- Research: DuckDB を用いたファクター算出（モメンタム・バリュー・ボラティリティ等）、将来リターン・IC 計算。
- AI: ニュース記事の LLM ベースのスコアリング（OpenAI）と市場レジーム判定。
- ユーティリティ: 設定ウィザード（.env 作成）、設定検証 CLI、ペーパートレード検証レポート生成ツールなど。
- ロギング: stdout と日次ローテートファイル出力（logs/）。

セットアップ手順（ローカル開発向け）
1. 前提
   - Python 3.10 以上
   - Git（ソース管理）

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存ライブラリのインストール（プロジェクトに requirements.txt がない場合の例）
   - pip install duckdb psutil openai
   - 任意: pip install PyYAML  # config/*.yaml のパース検証を有効化
   - （開発時）パッケージを editable インストール:
     - python -m pip install -e .

   ※ OpenAI を使う場合は openai パッケージが必要です。DuckDB や psutil は必須。

4. ディレクトリ作成
   - data/ と logs/ を作成（多くのコードは存在しない場合に作成するが、手動で用意しておくと安心）
     - mkdir -p data logs

5. 環境変数設定（.env の作成）
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - 手動で .env を作る場合は .env.example を参考に必須項目を設定してください。

主要な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI を利用する場合に必要
- KABUSYS_ENV: 実行環境（development / paper_trading / live）、デフォルトは development
  - paper_trading の場合、MockBroker を使用し DB は data/paper_trading.db に分離して記録
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパー専用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の約定モード（instant|partial|never|reject）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（開発用）
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒） — デフォルト 60

使い方（主なコマンド）
- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 警告を FAIL 扱いにする: python -m kabusys.validate_config --strict

- ExecutionEngine 起動（本番 / ペーパー）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を設定するとペーパー専用 DB を使用し MockBroker 動作
  - 実行中に data/stop_requested.flag を作成すると起動済み Engine に停止シグナルを送れます
  - エンジンは data/execution.pid に PID を書く（pid ファイルパスは Settings で変更可）

- Monitoring 起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能（例: MONITOR_POLL_INTERVAL=30）
  - 監視は常に本番 sqlite_path（data/monitoring.db）を使用します
  - 停止は data/stop_requested.flag を作るか KeyboardInterrupt（Ctrl+C）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH（環境変数 PAPER_TRADING_SQLITE_PATH を使う代わりに指定可能）

- プログラム的に利用する（例）
  - ニューススコア生成（AI）を呼ぶ:
    from kabusys.ai.news_nlp import score_news
    score_news(duckdb_conn, target_date, api_key="xxx")
  - リサーチ関数:
    from kabusys.research import calc_momentum
    calc_momentum(duckdb_conn, target_date)

安全停止・フラグ
- Kill Switch: risk_monitor の検知により data/kill.flag を書き込むことで ExecutionEngine に停止を要求できます（Settings.kill_flag_path）。
- stop_requested.flag: run_execution/run_monitoring はプロセスルートから見て data/stop_requested.flag の存在を確認して終了します（プロセス外から停止させたい場合に使用）。
- KILL_FLAG_CLEAR_ON_START が 1 の場合、ExecutionEngine 起動時に kill.flag を自動クリアします（本番では 0 推奨）。

ロギング
- デフォルトで stdout（コンソール）と logs/<app_name>.log（日次ローテート、30日保持）に出力します。
- ログディレクトリは LOG_DIR 環境変数で変更可能。

ディレクトリ構成（主なファイル/モジュール）
- src/kabusys/
  - __init__.py
  - config.py            : 環境変数 / Settings クラス、自動 .env 読み込み
  - config_setup.py      : 対話式 .env ウィザード
  - validate_config.py   : 起動前設定検証 CLI
  - run_execution.py     : ExecutionEngine 起動スクリプト
  - run_monitoring.py    : Monitoring 起動スクリプト
  - utils/
    - logging_setup.py   : ログ初期化ユーティリティ
    - process_priority.py: プロセス優先度・CPU affinity 設定
  - execution/            : ExecutionEngine 周り（BrokerFactory, OrderManager, RiskManager, Reconciler 等）
  - monitoring/
    - monitoring_db.py   : 監視用 SQLite 永続化層
    - system_monitor.py  : システム/データ鮮度監視
    - trade_monitor.py   : 発注履歴・滞留注文監視（未列挙のファイルあり）
    - risk_monitor.py    : ドローダウン・ポジション上限監視
    - kill_switch.py     : kill.flag 書込管理
    - monitoring_engine.py: 複数モニタを束ねる実行ループ
    - alert_manager.py   : 外部通知（LINE 等）管理（実装に依存）
  - portfolio/
    - portfolio_builder.py: 候補選定・重み計算
    - position_sizing.py  : 株数決定・上限計算
    - risk_adjustment.py  : セクターキャップ・レジーム乗数
  - research/
    - factor_research.py  : Momentum/Value/Volatility 等の計算
    - feature_exploration.py: 将来リターン / IC / 統計
  - ai/
    - news_nlp.py         : ニュースを LLM で評価して ai_scores に書き込む
    - regime_detector.py  : ETF MA 等と LLM 結果を合成してレジーム判定
  - tools/
    - paper_verification_report.py : ペーパートレード検証レポート生成
  - data/ (運用時に生成される想定)
    - kill.flag, stop_requested.flag, execution.pid, monitoring.db, paper_trading.db, etc.
  - logs/ (ログ出力先)

補足・運用上の注意
- 本番運用（KABUSYS_ENV=live）では設定検証（validate_config）を必ず実行して警告・必須項目を確認してください。KILL_FLAG_CLEAR_ON_START は本番で 0 を推奨します。
- OpenAI を利用する機能は API コストとレイテンシに注意してください。API 失敗時のフォールバック処理が組まれていますが、キーの管理は厳重に行ってください。
- DuckDB は分析用 DB として高性能ですがバックアップ戦略を用意してください。
- psutil によるプロセス優先度変更は権限が必要な場合があります。権限不足は警告ログで無害に扱われます。

ライセンス / バージョン
- パッケージの __version__ は src/kabusys/__init__.py に定義されています（例: 0.1.0）。
- リポジトリのライセンス情報はルートの LICENSE を参照してください（無ければ運用前に決めてください）。

お問い合わせ / 開発
- ローカルでの拡張やテストは python -m を使ったモジュール起動、または直接関数をインポートしてユニットテストを作成してください。テスト時は環境変数の自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使えます。

以上が主要な README 内容になります。追加で README に載せたい具体的な実行例（systemd unit ファイル、Dockerfile、CI 設定 など）があれば教えてください。それに合わせた運用手順を追記します。