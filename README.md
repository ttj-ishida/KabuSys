# KabuSys

日本株自動売買システムのコアライブラリ・ユーティリティ群です。  
このリポジトリには、戦略の研究用モジュール、ポートフォリオ構築・ポジション決定ロジック、監視／リスク管理、実行エンジン起動スクリプト、AI（ニュース NLP / レジーム判定）連携などが含まれます。

主にローカル開発・ペーパートレード・本番（live）の3モードで動作することを想定しています。

---

## 主要機能

- 実行エンジン起動（ExecutionEngine）
  - KABUSYS_ENV により paper_trading（MockBroker）/ live（実ブローカー）を切り替え
  - paper_trading 時は data/paper_trading.db に完全分離して記録
- 監視デーモン（Monitoring）
  - CPU/メモリ/Disk、Execution プロセスの生存、データ鮮度などを監視して SQLite に永続化
  - Kill Switch（条件に応じて data/kill.flag を書き込み、Execution を停止）
  - 各種アラート連携（LINE など、設定次第）
- ポートフォリオ構築（純粋関数群）
  - 候補選定、重み計算（等金額・スコア加重）、ポジションサイズ計算、セクター上限適用、レジーム乗数
- 研究（Research）
  - DuckDB を用いたファクター計算（モメンタム／ボラティリティ／バリュー等）
  - 特徴量探索（forward returns, IC, summary）
- AI連携
  - ニュースを OpenAI に送信して銘柄ごとのセンチメントを ai_scores に保存（news_nlp）
  - マクロニュース + ETF MA200 乖離で市場レジーム判定（regime_detector）
- ユーティリティ
  - ログ設定（stdout + 日次ローテートファイル）
  - プロセス優先度 / CPU affinity 設定
  - 環境変数ウィザード（.env の対話的作成）
  - 設定バリデーション CLI（.env と config/*.yaml の事前検証）
  - Paper Trading 検証レポート生成ツール

---

## 前提条件

- Python 3.10 以上（PEP 604 の型表記などを使用）
- 推奨パッケージ（要インストール）
  - duckdb
  - psutil
  - openai
  - PyYAML（config YAML の検証で使用。必須ではない）
- 標準ライブラリ: sqlite3 等

※ requirements.txt がある場合はそれを使ってください。ない場合は上記パッケージを pip でインストールしてください。

例:
    python -m venv .venv
    source .venv/bin/activate
    pip install duckdb psutil openai PyYAML

---

## セットアップ手順

1. リポジトリをクローン
    git clone <repo-url>
    cd <repo-root>

2. 仮想環境を作成・有効化（推奨）
    python -m venv .venv
    source .venv/bin/activate  # Windows: .venv\Scripts\activate

3. 依存パッケージをインストール
    pip install duckdb psutil openai PyYAML

4. 環境変数設定 (.env) の作成
   - 対話式ウィザードで .env を作成できます:
       python -m kabusys.config_setup
   - 必須項目（最低限）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 重要な項目:
     - KABUSYS_ENV: development | paper_trading | live
     - DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
     - SQLITE_PATH: data/monitoring.db（デフォルト）
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用）
     - OPENAI_API_KEY: AI 機能を使う場合に必要
     - LOG_LEVEL, LOG_DIR 等

5. 設定の検証（任意だが推奨）
    python -m kabusys.validate_config
   - 警告もエラーとして扱う strict モード:
    python -m kabusys.validate_config --strict

---

## 使い方（主要コマンド）

- 実行エンジン（エンジンが別スレッドで run_session を実行）
    python -m kabusys.run_execution

  - 注意:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient が使用され、PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）に記録されます。
    - 実行開始前に data/stop_requested.flag が存在すると起動しません。
    - 実行中に data/stop_requested.flag を作成するとエンジン停止を要求します（監視側・手動いずれでも）。

- 監視ループ（SystemMonitor のポーリング）
    python -m kabusys.run_monitoring

  - 説明:
    - デフォルトのポーリング間隔は 60 秒。
    - 環境変数 MONITOR_POLL_INTERVAL で上書き可能（例: MONITOR_POLL_INTERVAL=30）。
    - 停止フラグ: data/stop_requested.flag を置くと監視が終了します。
    - 監視は環境に関係なく本番用 sqlite_path（SQLITE_PATH）を使用して監視ログを保存します。

- 環境設定ウィザード
    python -m kabusys.config_setup

- 設定検証
    python -m kabusys.validate_config
    python -m kabusys.validate_config --strict

- Paper Trading 検証レポート
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db を参照

- プログラムからの利用例（AI・Research）
  - DuckDB 接続を作成して関数を呼ぶ例:
        import duckdb
        from datetime import date
        from kabusys.research import calc_momentum
        conn = duckdb.connect("data/kabusys.duckdb")
        results = calc_momentum(conn, date(2026, 4, 1))

  - ニュース NLP（OpenAI の API キーが必要）:
        from kabusys.ai import score_news
        from datetime import date
        conn = duckdb.connect("data/kabusys.duckdb")
        score_count = score_news(conn, date(2026, 4, 1), api_key="sk-...")

  - レジーム判定:
        from kabusys.ai.regime_detector import score_regime
        score_regime(conn, date(2026, 4, 1), api_key="sk-...")

---

## 重要な挙動・運用メモ

- KABUSYS_ENV の意味
  - development: 開発用（発注は行わない設計の箇所あり）
  - paper_trading: ペーパートレード（MockBrokerClient、別 DB に記録）
  - live: 本番（実際に発注を行う）
- paper_trading は本番 DB と完全分離されるため、実データを汚す心配はありません。
- stop / kill フラグ
  - data/stop_requested.flag: run_monitoring / run_execution が定期チェックする停止フラグ
  - data/kill.flag: KillSwitch が書き込むことで ExecutionEngine に停止指示を与える（条件により自動作成）
- ログ
  - ログ設定は kabusys.utils.logging_setup.setup_logging で行います。デフォルトは logs/<app_name>.log に日次ローテーション（30日保管）＋ stdout 出力。
  - LOG_LEVEL, LOG_DIR で制御可能。
- プロセス優先度
  - 起動スクリプトは最初に set_process_priority("high") を呼びます（psutil 経由、OS によっては設定できない場合あり）。
- DB マイグレーション
  - monitoring_db.init_monitoring_db は冪等でテーブルとインデックスを作成し、既存 DB に対して必要な列追加（ALTER）も行います。

---

## 環境変数（主要一覧）

- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 推奨 / 重要
  - KABUSYS_ENV (development | paper_trading | live)
  - OPENAI_API_KEY (AI 機能利用時)
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (監視 DB、デフォルト: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB、デフォルト: data/paper_trading.db)
  - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL)
  - LOG_DIR
  - MONITOR_POLL_INTERVAL (run_monitoring のポーリング間隔秒)
  - PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START（監視・停止制御）

詳細は kabusys.config.Settings プロパティ実装を参照してください（ドキュメントは関数 docstring に記載）。

---

## ディレクトリ構成（抜粋）

リポジトリ内の主要なディレクトリ・ファイル（ src/kabusys 以下）:

- src/kabusys
  - __init__.py
  - config.py                 — 環境変数 / Settings
  - config_setup.py           — .env 対話ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリングスクリプト
  - utils/
    - logging_setup.py        — ログ初期化
    - process_priority.py     — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py        — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py
    - trade_monitor.py        — （監視関連ロジック）
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py        — （アラート送信管理）
  - execution/
    - execution_engine.py     — ExecutionEngine 本体
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
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
    - news_nlp.py              — ニュース NLP（OpenAI 連携）
    - regime_detector.py      — 市場レジーム判定（MA200 + マクロセンチメント）
    - __init__.py
  - tools/
    - paper_verification_report.py  — Paper Trading 検証レポート生成ツール

プロジェクトルートには `config/` ディレクトリ（system_config.yaml 等）や `data/`、`logs/` が想定されます。`config/*.yaml` は validate_config でチェックされます（PyYAML があればパース検証も行います）。

---

## 開発・デバッグのヒント

- .env は絶対に Git にコミットしないでください（config_setup はその旨を注意喚起します）。
- AI 機能（OpenAI）を使う際は API キーの料金・レート制限に注意してください。news_nlp はリトライ／バックオフを実装していますが、テスト時はモックを使用してください。
- DuckDB に格納するデータ（prices_daily / raw_financials / raw_news 等）を準備すると research / ai / regime 機能が動作します。
- run_monitoring / run_execution の停止は `data/stop_requested.flag` を作成することで行えます（安全に終了させるための仕組み）。

---

## 参考

コード内の docstring や関数コメントに設計意図や運用上の注意が豊富に書かれています。特定のモジュールの詳細な使い方やパラメータは当該ファイルを参照してください。

---

ご希望があれば、README に以下の追加情報を追記できます:
- requirements.txt の生成例
- systemd / supervisor / docker-compose の起動例
- API キーの安全な管理方法（Vault / environment secrets）
- さらなるコマンド例やサンプル .env.example

必要であればどれを追記するか教えてください。