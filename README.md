KabuSys — 日本株自動売買システム
================================

この README はコードベース（src/kabusys 以下）に対する概要・セットアップ・使い方・ディレクトリ構成を日本語でまとめたものです。開発・テスト・ペーパートレード・本番（live）を想定した設計になっています。

プロジェクト概要
---------------
KabuSys は日本株向けの自動売買システムのコンポーネント群です。主な役割は以下の通りです。

- 市場データ（DuckDB）を用いたファクター・リサーチと特徴量抽出
- ポートフォリオ構築（候補選定・重み算出・ポジションサイジング・セクター制約）
- ExecutionEngine（発注・リスク管理・再整合）
- Monitoring（システム稼働監視、トレード監視、リスク監視、Kill Switch）
- AI モジュール（ニュース NLP による銘柄センチメント、レジーム判定）
- 各種ユーティリティ（ログ設定、プロセス優先度設定、設定ウィザード・検証）

設計上のポイント
- 環境変数 / .env による設定管理（config モジュール）
- DuckDB を分析用 DB、SQLite を監視・注文履歴用 DB として利用
- ペーパートレード時は本番 DB と分離（data/paper_trading.db）
- モジュールは可能な限り純粋関数／副作用を限定する実装方針

機能一覧
---------
主な機能（モジュール単位）：

- 起動スクリプト
  - python -m kabusys.run_execution : ExecutionEngine を起動
  - python -m kabusys.run_monitoring : Monitoring のポーリングループを起動

- 設定関連
  - python -m kabusys.config_setup : .env を対話式で作成/更新するウィザード
  - python -m kabusys.validate_config : .env と config/*.yaml を事前検証（--strict オプションあり）

- Monitoring
  - system_monitor: CPU/メモリ/ディスク、データ鮮度、Execution プロセス存在などを監視し SQLite に記録
  - trade_monitor: 注文の滞留や約定異常の検出（trade_logs）
  - risk_monitor: ドローダウンやポジション上限の監視、dashboard の更新
  - kill_switch: 条件を満たした場合 data/kill.flag を作成して ExecutionEngine に停止シグナルを送る
  - monitoring_engine: 各モニタを束ね定期実行・アラート通知

- Execution
  - ExecutionEngine（発注 / リスク管理 / Reconciler / OrderManager など）
  - BrokerClientFactory により環境（KABUSYS_ENV）に応じて実ブローカ or Mock を選択

- 研究・リサーチ
  - research.factor_research: モメンタム・ボラティリティ・バリュー等の計算（DuckDB を用いる）
  - research.feature_exploration: 将来リターン計算・IC 等の統計解析

- ポートフォリオ構築
  - portfolio.portfolio_builder: 候補選定、等金額・スコア重み算出
  - portfolio.position_sizing: 株数計算（リスクベース、配分ベース）、lot（単元）丸め
  - portfolio.risk_adjustment: セクターキャップ、レジーム乗数

- AI（OpenAI）
  - ai.news_nlp.score_news: raw_news を LLM に送り銘柄別センチメントを ai_scores に書き込む
  - ai.regime_detector.score_regime: ma200 と LLM マクロセンチメントを合成して market_regime を更新

- ツール
  - tools.paper_verification_report: ペーパートレード DB を元に検証レポートを生成

セットアップ手順
-----------------
※ プロジェクトルートは .git または pyproject.toml によって自動検出されます。

1. 必要パッケージのインストール（例）
   - Python 3.9+ を想定（実際の要件はプロジェクトの pyproject/requirements を参照）
   - よく使う外部依存:
     - duckdb
     - psutil
     - openai
     - PyYAML（validate_config の YAML 検証に必要）
   例:
     pip install duckdb psutil openai PyYAML

2. プロジェクトルートに移動し .env を作成する
   - 対話式ウィザードで作成:
       python -m kabusys.config_setup
   - もしくは .env.example を参考に手動作成

3. 設定の事前検証
     python -m kabusys.validate_config
   - 警告も FAIL 扱いにしたい場合:
     python -m kabusys.validate_config --strict

4. データディレクトリの作成（必要に応じて）
   - デフォルトで使用するパス:
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - PaperTrading SQLite: data/paper_trading.db
     - ログディレクトリ: logs/
   - これらは環境変数で上書き可能（後述）

5. 環境変数（主要）
   - 必須:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 推奨/任意:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト development
     - DUCKDB_PATH (default: data/kabusys.duckdb)
     - SQLITE_PATH (default: data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)
     - OPENAI_API_KEY (AI 機能を使う場合必須)
     - LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL)
     - LOG_DIR (ログ出力先ディレクトリ)
     - PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START
     - PAPER_FILL_MODE (instant | partial | never | reject) — ペーパートレード時の約定挙動
     - MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）

6. （任意）Kill Flag の初期クリア
   - Settings.kill_flag_clear_on_start = 1 を設定している場合は起動時に kill.flag が自動で削除されます。ただし本番では 0 を推奨します。

使い方
-------
起動・運用に関する代表的なコマンドと説明です。

- ExecutionEngine 起動（本番 or paper_trading を env に応じて切替）
    python -m kabusys.run_execution

  説明:
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db に記録します（本番 DB と分離）。
  - 起動前に data/stop_requested.flag が存在すると起動を行わず終了します。
  - 実行中に data/stop_requested.flag を作成するとエンジンは停止します。
  - PID ファイルは data/execution.pid（設定で変更可）に書き込まれます。

- Monitoring 起動（定期ポーリング）
    python -m kabusys.run_monitoring

  説明:
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可（デフォルト 60）。
  - Monitoring は環境にかかわらず本番 sqlite_path（SQLITE_PATH）を使用して監視ログを残します。
  - 停止はプロジェクトルート/data/stop_requested.flag を作ることで行えます（run_monitoring はこれを検出してループを終了します）。

- 設定ウィザード
    python -m kabusys.config_setup
  - .env を対話的に作成・更新します。作成後は validate_config を実行してください。

- 設定検証
    python -m kabusys.validate_config [--strict]
  - 必須環境変数や config/*.yaml の存在・簡易パースをチェックします。--strict で警告を FAIL 扱いにできます。

- Paper Trading 検証レポート
    python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB は環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db。
  - 稼働率・注文成功率・送信率・P95 レイテンシなどを評価し PASS/FAIL を出力します。

- AI 機能（プログラムから呼ぶ）
  - ai.news_nlp.score_news(conn, target_date, api_key=None)
  - ai.regime_detector.score_regime(conn, target_date, api_key=None)
  これらは DuckDB 接続を受け取り、結果を DB に書き込みます。OPENAI_API_KEY を環境変数に設定するか、api_key 引数を渡してください。

ロギング
--------
- ログはデフォルトで stdout（コンソール）と日次ローテートファイル logs/<app_name>.log に出力されます。
- LOG_LEVEL / LOG_DIR で挙動を変更できます。
- logging 設定は kabusys.utils.logging_setup.setup_logging で統一的に行われます。

停止・Kill Switch
-----------------
- Kill Switch は監視コンポーネントが条件を満たした場合 data/kill.flag を作成します。ExecutionEngine は kill.flag の存在を確認して安全停止を行う設計です。
- 人手で停止したい場合はプロジェクトルートに data/stop_requested.flag を作成すると run_* スクリプトが検出して停止します（run_execution/run_monitoring 共通）。

ディレクトリ構成
----------------
（主要ファイル・ディレクトリのみ抜粋。実際は src/kabusys 以下に配置されます）

- src/
  - kabusys/
    - __init__.py
    - run_execution.py            — ExecutionEngine 起動スクリプト
    - run_monitoring.py          — Monitoring 起動スクリプト
    - config.py                  — 環境変数・設定読み込みロジック（Settings）
    - config_setup.py            — .env 対話ウィザード
    - validate_config.py         — 起動前設定検証 CLI

    - utils/
      - logging_setup.py         — logging 設定ユーティリティ
      - process_priority.py      — プロセス優先度 / CPU affinity ユーティリティ
    - monitoring/
      - monitoring_db.py         — SQLite テーブル初期化・永続化層
      - system_monitor.py        — システム・データ鮮度監視
      - trade_monitor.py         — 注文監視（滞留・約定異常） ※（ファイルはリスト全体では省略）
      - risk_monitor.py          — ドローダウン・ポジション監視
      - kill_switch.py           — kill.flag 書込ロジック
      - monitoring_engine.py     — 各 Monitor を束ねる実行器
      - alert_manager.py         — （アラート送信の統括）
    - execution/
      - execution_engine.py      — 実際のセッション制御（Engine）
      - order_manager.py
      - order_repository.py
      - broker_factory.py        — Broker クライアント生成（Mock or 実ブローカ）
      - reconciler.py
      - risk_manager.py
    - portfolio/
      - portfolio_builder.py     — 候補選定・重み計算
      - position_sizing.py       — 株数計算・キャップ処理
      - risk_adjustment.py       — セクターキャップ・レジーム乗数
    - research/
      - factor_research.py       — モメンタム/ボラティリティ/バリュー計算
      - feature_exploration.py   — 将来リターン・IC・統計サマリー
    - ai/
      - news_nlp.py              — ニュース NLP → ai_scores 書込
      - regime_detector.py       — 市場レジーム判定・market_regime 書込
    - tools/
      - paper_verification_report.py — ペーパートレード検証レポート

補足 / 注意点
-------------
- DB マイグレーション
  - monitoring_db.init_monitoring_db は既存 DB に対して必要な列（peak_value, latency_ms など）を追記する簡易マイグレーション処理を行います。
- 環境切替
  - KABUSYS_ENV=paper_trading の場合、発注は MockBrokerClient になり data/paper_trading.db に書き込まれます（本番 DB に影響を与えません）。
- セキュリティ
  - .env ファイルは機密情報を含むため決して Git にコミットしないでください。
- AI API
  - OpenAI へのリクエストは課金が発生する可能性があります。API キーの管理、レート制限、コストに注意してください。
- ローカル開発
  - KILL_FLAG_CLEAR_ON_START は開発時に便利ですが、本番では 0 を推奨します（誤って自動クリアすると Kill Switch が無効化される恐れがあります）。

よくある操作例（まとめ）
-----------------------
- .env を作って設定を検証する:
    python -m kabusys.config_setup
    python -m kabusys.validate_config

- ペーパートレード実行（環境変数設定例）:
    export KABUSYS_ENV=paper_trading
    export JQUANTS_REFRESH_TOKEN=...
    export KABU_API_PASSWORD=...
    python -m kabusys.run_execution

- 監視プロセスを起動（デフォルト 60 秒ごと）:
    export MONITOR_POLL_INTERVAL=30
    python -m kabusys.run_monitoring

- ペーパートレード検証レポート（期間指定）:
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

フィードバック / 開発
---------------------
コードやドキュメントの改善提案は Pull Request で受け付けます。設計方針や API 変更は下流への影響が大きいため、事前に Issue で相談してください。

以上。必要に応じて README の追加項目（例: systemd / supervisor 用のユニットファイル例、より詳細な依存関係・型情報、CI 設定）を作成しますので、追加で欲しい内容を教えてください。