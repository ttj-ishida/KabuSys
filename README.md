README
======

概要
----
KabuSys は日本株の自動売買および関連ツール群を集めた Python パッケージです。本リポジトリには以下の主要機能が含まれます。

- 実行エンジン（ExecutionEngine）: 注文発行、リスク管理、約定管理
- 監視コンポーネント（Monitoring）: システム状態、注文状況、リスク（ドローダウン等）を定期監視しアラート／Kill Switch を管理
- ポートフォリオ構築ロジック: 候補選定、重み計算、ポジションサイズ算出、セクター制約やレジームによる調整
- リサーチ／ファクター計算: モメンタム、ボラティリティ、バリュー等のファクター計算と解析ユーティリティ
- AI 補助機能: ニュースのセンチメント解析（OpenAI を使用）や市場レジーム判定
- 運用支援ツール: .env 作成ウィザード、設定検証、Paper Trading 検証レポート生成など

主な設計方針
- 本番とペーパー（paper_trading）を明確に分離（ペーパートレード時は専用 SQLite DB を使用）
- DuckDB を分析用 DB、SQLite を監視・発注ログ等の永続化に使用
- OpenAI を利用するモジュールは API キーを明示的に渡すか環境変数で指定
- ルックアヘッドバイアス回避（日時の直接参照を避ける実装）など、取引ロジックの安全性に配慮

機能一覧
--------
- 実行
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV に応じて本番/ペーパー用ブローカーを使用）
  - ブローカー抽象化（MockBrokerClient を含む）
  - リスク管理（position 上限、ドローダウン等）
- 監視
  - run_monitoring.py: SystemMonitor のポーリングループ起動
  - MonitoringEngine: SystemMonitor / TradeMonitor / RiskMonitor の束ね
  - Kill Switch：条件に応じて data/kill.flag を書き込み ExecutionEngine に停止指示
  - 監視 DB スキーマ（system_status, trade_logs, positions, risk_logs, dashboard）
- ポートフォリオ
  - 候補選定（select_candidates）
  - 重み計算（等配分 / スコア加重）
  - ポジションサイズ計算（risk_based / equal / score）
  - セクターキャップ、レジーム乗数
- リサーチ
  - ファクター計算（momentum / volatility / value）
  - 将来リターン、IC（スピアマン）や統計サマリ
- AI
  - news_nlp.score_news: raw_news を OpenAI に投げて銘柄ごとの ai_score を生成・保存
  - regime_detector.score_regime: ETF とマクロニュースを合成して market_regime を判定・保存
- ツール
  - config_setup.py: .env 対話ウィザード（初期作成・更新）
  - validate_config.py: .env と config/*.yaml の基本検証
  - tools/paper_verification_report.py: ペーパートレードの検証レポートを生成

セットアップ手順
--------------
前提
- Python 3.10+ を想定（typing の | 演算子などを使用）
- 必要ライブラリ（代表例）
  - duckdb
  - psutil
  - openai（AI 機能を利用する場合）
  - PyYAML（設定ファイルの検証を行う場合に任意）
- システムに sqlite3 は標準で含まれます

インストール（例）
1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb psutil openai
   - （任意）pip install pyyaml

3. プロジェクトルートに移動（.git または pyproject.toml がある場所）
   - 上記 config モジュールはプロジェクトルートを自動検出して .env/.env.local を読み込みます

環境変数（.env）
- 推奨: python -m kabusys.config_setup を実行して対話的に .env を作成
- 最低限必要な環境変数:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 主な設定例（.env の抜粋）
  - KABUSYS_ENV=development|paper_trading|live
  - DUCKDB_PATH=data/kabusys.duckdb
  - SQLITE_PATH=data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
  - OPENAI_API_KEY=sk-...
  - LOG_LEVEL=INFO
  - KILL_FLAG_CLEAR_ON_START=0

注意:
- Settings モジュールは自動で .env を読み込みます（.env.local を優先上書き）。テスト等で自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- ペーパートレード時は settings.is_paper が True になり、専用の SQLite（デフォルト: data/paper_trading.db）を使います。

使い方
------

1) 初期設定ウィザード（.env 作成）
- 実行:
  - python -m kabusys.config_setup
- 対話的に鍵やパスなどを入力して .env を生成します。

2) 設定検証
- 実行:
  - python -m kabusys.validate_config
- --strict を付けると警告も失敗扱いで exit(1) になります:
  - python -m kabusys.validate_config --strict

3) 監視プロセスの起動
- 監視ループを起動:
  - python -m kabusys.run_monitoring
- 振る舞い:
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能（デフォルト 60 秒）
  - 監視は常に本番の sqlite_path（Settings.sqlite_path）を使用します
  - 停止方法: プロジェクトルート/data/stop_requested.flag を作成するとループが終了します

4) 実行エンジンの起動（ExecutionEngine）
- 実行:
  - python -m kabusys.run_execution
- 振る舞い:
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録
  - エンジンはスレッドで実行され、data/stop_requested.flag が作られると停止指示を送り安全にシャットダウンします
  - PID ファイル: data/execution.pid を利用（Settings.pid_file_path 参照）
  - 起動時に既に stop フラグがある場合は起動せず終了します

5) Paper Trading 検証レポート
- 実行:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH（PAPER_TRADING_SQLITE_PATH 環境変数でも指定可）
- 出力: 稼働率、注文成功率、送信率、レイテンシ（P95）などを表示し PASS/FAIL を判定

6) AI モジュール（ニュース NLP / レジーム判定）
- ニューススコア生成:
  - 関数: kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
  - api_key が未指定なら OPENAI_API_KEY 環境変数を参照
- レジーム判定:
  - 関数: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
- 注意: OpenAI 呼び出しはネットワークエラーや 429/5xx に対してリトライロジックを実装しています。API キーは安全に管理してください。

ログ
---
- 共通ロギングユーティリティ: kabusys.utils.logging_setup.setup_logging(app_name="execution")
  - コンソール出力（stdout）と日次ローテーションファイル（logs/<app_name>.log）を設定
  - LOG_DIR 環境変数でログ保存先を変更可能
  - LOG_LEVEL でログレベルを制御

主要ファイル / ディレクトリ構成
---------------------------
（プロジェクトルート下の src/kabusys を想定したツリー）

- src/
  - kabusys/
    - __init__.py
    - config.py                      — 環境変数 / Settings 管理（.env 自動ロード等）
    - config_setup.py                — .env 対話ウィザード
    - validate_config.py             — 設定検証 CLI
    - run_execution.py               — ExecutionEngine 起動スクリプト
    - run_monitoring.py              — SystemMonitor ポーリング起動スクリプト
    - execution/                      — Execution 関連（Engine/OrderManager/リポジトリ等）
      - ... (実行ロジック, broker factory 等)
    - monitoring/
      - monitoring_db.py             — SQLite スキーマ定義と DB 用ラッパ
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - monitoring_engine.py
      - alert_manager.py
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
    - tools/
      - paper_verification_report.py
    - utils/
      - logging_setup.py
      - process_priority.py
      - __init__.py

監視 DB（monitoring_db.py）の主なテーブル
- system_status: 定期ポーリングの結果（cpu/memory/disk, process_ok 等）
- trade_logs: 発注イベントログ（Created, Sent, Filled など、latency_ms カラムあり）
- positions: 保有ポジション
- risk_logs: リスクイベント（DRAWDOWN_ALERT, POSITION_LIMIT 等）
- dashboard: ダッシュボード集計（portfolio_value, cash, drawdown_pct, peak_value 等）

運用上のポイント / トラブルシュート
---------------------------------
- 必須環境変数が未設定だと Settings のプロパティ呼び出しで ValueError を送出します。validate_config.py で事前検証することを推奨します。
- .env を Git にコミットしないでください（config_setup.py にもその旨の注記あり）。
- ログディレクトリ作成に失敗するとコンソール出力のみになります。ファイル出力に失敗したログは stderr に警告が出ます。
- OpenAI を使う機能は API キーを必要とします。テストや開発時はモック（unittest.mock.patch）を使って外部呼び出しを差し替えられる設計です。
- 停止フラグ:
  - 実行エンジンの安全停止: data/stop_requested.flag を作成すると起動中の run_execution / run_monitoring はこれを検知して終了します。
  - Kill Switch: 条件により data/kill.flag を書き込み、ExecutionEngine 側で検出して停止させる仕組みです（Settings.kill_flag_clear_on_start を使って起動時に自動クリアするか制御可能。production では 0 を推奨）。

開発者向け補足
--------------
- DuckDB はリサーチ/ファクター計算で利用します。DuckDB 接続オブジェクトを渡して SQL と Python の組合せで高速に集計できます。
- モジュール群は副作用を最小にする設計（外部 API 呼び出しやファイル操作は明示的）で、テストしやすいように関数分割されています。
- YAML の検証は PyYAML がある場合のみ実行されます（validate_config.py）。

ライセンスや貢献方法など
-----------------------
- （本 README には記載がありません。必要に応じて LICENSE ファイルを追加してください。）

以上。必要であれば README にサンプル .env テンプレート、起動スクリプトの systemd ユニット例、cron / supervisor の例などを追加できます。どの情報を追記しますか？