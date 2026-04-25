KabuSys
=======
日本株自動売買システムの一部を収めた Python コードベースの簡易 README（日本語）。  
本ドキュメントはリポジトリ内のスクリプト・モジュール群を読み取り、開発者／運用者向けに要点をまとめたものです。

要約（プロジェクト概要）
--------------------
KabuSys は日本株の自動売買・検証・監視を目的としたモジュール群です。主な機能は以下の通りです。
- ExecutionEngine（発注実行）: ブローカークライアントを用いた注文管理・リスク制御・約定管理
- Monitoring（監視）: システム状態・注文状況・リスクの常時監視とアラート / Kill Switch
- Portfolio モジュール: 候補選定、重み付け、ポジションサイズ計算、セクター制限等
- Research（研究）: ファクター計算、将来リターン・IC 計算、統計サマリー
- AI 補助: ニュース NLP によるセンチメント算出、レジーム判定（OpenAI API を利用）
- ユーティリティ: .env ウィザード、設定検証、ログ設定、プロセス優先度設定 等
- ツール: Paper Trading の検証レポート生成スクリプト等

主な機能一覧
--------------
- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV=paper_trading のときは MockBroker を使用し paper_trading.db に記録）
  - run_monitoring.py: SystemMonitor のポーリングループを起動（MONITOR_POLL_INTERVAL で間隔変更可、デフォルト 60s）
- 環境設定管理
  - config_setup.py: .env を対話式に作成／更新するウィザード
  - validate_config.py: .env や config/*.yaml の整合性チェック CLI
- 監視
  - monitoring/monitoring_engine.py: 各 Monitor（SystemMonitor / TradeMonitor / RiskMonitor）を束ねる
  - monitoring/monitoring_db.py: SQLite ベースの永続化層（system_status / trade_logs / positions / risk_logs / dashboard 等）
  - monitoring/kill_switch.py: data/kill.flag を書き込むことで ExecutionEngine に停止シグナルを送る仕組み
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py: 候補選定・重み付け
  - portfolio/position_sizing.py: 発注株数計算（丸め・上限・スケーリング）
  - portfolio/risk_adjustment.py: セクターキャップ・レジーム乗数
- 研究・分析
  - research/factor_research.py: Momentum / Volatility / Value ファクター計算（DuckDB 使用）
  - research/feature_exploration.py: 将来リターン計算、IC、統計サマリー
- AI（OpenAI）
  - ai/news_nlp.py: ニュースを LLM でセンチメント評価 → ai_scores に書き込み
  - ai/regime_detector.py: ETF の MA 乖離 + マクロニュースの LLM センチメント合成で日次レジーム判定
- ツール
  - tools/paper_verification_report.py: Paper Trading の運用検証レポート生成

セットアップ手順
----------------
1. リポジトリをクローン／配置
   - この README はパッケージソース（src/kabusys）を想定しています。

2. Python 環境を用意
   - 推奨: Python 3.10+（コードは型注釈を使っています）
   - 仮想環境を作成して有効化してください。

3. 依存ライブラリをインストール
   - 必要ライブラリ（主要）:
     - duckdb
     - psutil
     - openai (AI 機能を使う場合)
     - PyYAML（validate_config の YAML 検査に任意で使用）
   - 例:
     pip install duckdb psutil openai pyyaml

4. .env の作成（必須項目を設定）
   - 対話式ウィザードを利用:
     python -m kabusys.config_setup
   - あるいは .env ファイルを手動で作成（以下の必須項目を少なくとも設定）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 重要: .env はリポジトリにコミットしないこと（シークレット含む）

5. 設定検証
   - 自動検証を実行:
     python -m kabusys.validate_config
   - 本番移行前は --strict を使い警告も失敗扱いにすること:
     python -m kabusys.validate_config --strict

6. DB / データディレクトリ
   - デフォルトで以下パスが使われます（必要に応じて .env で上書き）
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
   - 起動スクリプトは必要に応じてディレクトリを自動作成しようとしますが、パーミッション等を事前に確認してください。

主な環境変数（抜粋）
-------------------
- 必須（アプリ起動前に設定）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 環境・動作制御
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
  - KILL_FLAG_CLEAR_ON_START: 0|1（本番は 0 推奨）
- DB / ファイルパス
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
  - PID_FILE_PATH: data/execution.pid
  - KILL_FLAG_PATH: data/kill.flag
- Monitoring
  - MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）
  - CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT: 監視閾値
- Paper Trading
  - PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）
- AI
  - OPENAI_API_KEY: OpenAI 呼び出しに必要（ai/news_nlp.py, ai/regime_detector.py）
- 通知（任意）
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID

使い方（起動・コマンド例）
-----------------------
- 環境変数を読み込んだ上で ExecutionEngine を起動
  - 本番（設定上の動作）:
    python -m kabusys.run_execution
  - Paper Trading（KABUSYS_ENV=paper_trading の場合、自動で paper DB が使われる）
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- Monitoring を起動（SystemMonitor のポーリング）
  - デフォルト 60 秒間隔:
    python -m kabusys.run_monitoring
  - 間隔 override:
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- 環境設定ウィザード（.env 作成）
  python -m kabusys.config_setup

- 設定検証
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- Paper Trading 検証レポートの生成
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db --from 2026-04-01 --to 2026-04-11
  （--db を省略すると環境変数 PAPER_TRADING_SQLITE_PATH またはデフォルト path が使用されます）

- AI モジュールの使用（ライブラリ関数）
  - ニューススコア算出:
    from kabusys.ai.news_nlp import score_news
    score_news(duckdb_conn, target_date, api_key="...")

  - レジーム判定:
    from kabusys.ai.regime_detector import score_regime
    score_regime(duckdb_conn, target_date, api_key="...")

停止・Kill Switch・フラグファイル
-------------------------------
- 実行中のループを外部から停止するためのフラグ:
  - data/stop_requested.flag: run_monitoring / run_execution のループ内で検知される停止フラグ（存在するとループを抜けます）
  - data/kill.flag: KillSwitch が書き込むファイル。ExecutionEngine 側はこのファイルを検知して処理を停止します
- PID ファイル:
  - data/execution.pid に ExecutionEngine の PID を書き出す運用をしている点に注意

ログ
----
- ログ設定は kabusys.utils.logging_setup.setup_logging によって統一的に行われます。
- デフォルトのログ保存先は logs/、アプリケーション別に logs/<app_name>.log（日次ローテーション）に出力されます。
- ログレベルは LOG_LEVEL 環境変数または setup_logging の引数で指定できます。

ディレクトリ構成（主要ファイル・モジュール）
-----------------------------------------
以下は src/kabusys フォルダ配下の主なファイル・モジュール（抜粋）です。

- kabusys/
  - __init__.py            — パッケージ定義
  - config.py              — Settings クラス（環境変数 / .env のロードと検証）
  - config_setup.py        — .env 対話式ウィザード
  - validate_config.py     — 起動前の設定検証 CLI
  - run_execution.py       — ExecutionEngine 起動スクリプト
  - run_monitoring.py      — SystemMonitor ポーリングループ起動スクリプト

  - utils/
    - logging_setup.py     — ロギング初期化ユーティリティ
    - process_priority.py  — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py     — SQLite テーブル作成・アクセスラッパー
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
    - system_monitor.py    — CPU/メモリ/Disk/データ鮮度/プロセス監視
    - trade_monitor.py     — （注文に関する監視 — リポジトリ内に存在）
    - risk_monitor.py      — ドローダウン / ポジション上限監視
    - kill_switch.py       — kill.flag の管理
    - alert_manager.py     — （アラート送信の抽象化）
  - execution/
    - execution_engine.py  — 実際の注文セッション管理（Engine）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - broker_factory.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py          — ニュースの LLM スコアリング
    - regime_detector.py   — 市場レジーム判定
  - tools/
    - paper_verification_report.py

注意事項 / 運用上のヒント
-----------------------
- 本番環境で KABUSYS_ENV=live を設定する場合は設定内容（特に KILL_FLAG_CLEAR_ON_START、LINE 通知設定、API キー）を慎重に確認してください。validate_config で live に関する追加チェックを行います。
- .env ファイルはセキュリティ上 Git に含めないでください（config_setup.py のヘッダーにも注意書きがあります）。
- AI（OpenAI）機能を利用するには OPENAI_API_KEY が必要です。API 呼び出しはレート制限/ネットワークエラー等を考慮したリトライ設計になっていますが、コストや使用制限に注意してください。
- Paper Trading（検証）用の DB と本番 monitoring DB は分離されています（paper_trading 環境では専用 SQLite が使用されます）。
- ログディレクトリの権限・容量管理（ログローテーションの確認）を行ってください。

追加のドキュメント参照
--------------------
- ソース中の docstring / コメントに設計方針や注意点が多く含まれています。各モジュールの先頭コメントを参照してください（例: portfolio/*.py、research/*.py、ai/*.py）。
- config_setup.py と validate_config.py は運用準備に役立ちます。まずこれらを実行して設定を検証してください。

---

問題や不明点があれば、どの機能（例: ExecutionEngine の起動方法、AI モジュールの使い方、監視ループのカスタマイズなど）について詳しく知りたいか教えてください。必要に応じて具体的なコマンド例や .env テンプレートを提供します。