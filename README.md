# KabuSys — 日本株自動売買システム

このリポジトリは日本株向けの自動売買/リサーチ基盤「KabuSys」の実装です。  
本 README はコードベース（src/kabusys 以下）に基づき、導入・実行方法・各種ユーティリティの使い方を日本語でまとめたものです。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（主要スクリプト・CLI）
- 環境変数（主要項目）
- ディレクトリ構成
- 補足・注意事項

---

プロジェクト概要
- KabuSys は日本株の自動売買エンジン、監視（Monitoring）、ポートフォリオ構築、ファクター計算、AI（ニュース NLP / レジーム判定）などを含む統合システムです。
- 設計方針のポイント
  - 本番/ペーパートレード/開発を環境変数 KABUSYS_ENV で切り替え
  - SQLite（監視/ペーパートレード）と DuckDB（分析）を使用
  - OpenAI API を利用したニュース解析・レジーム判定（任意）
  - ログはコンソール + 日次ローテーションで出力

---

機能一覧
- ExecutionEngine（発注実行エンジン）
  - live / paper_trading（MockBroker） / development 切替
  - RiskManager / OrderManager / Reconciler 等を組み合わせて発注制御
- Monitoring（監視）
  - SystemMonitor: CPU/MEM/DISK、プロセス死活、データ鮮度監視
  - TradeMonitor / RiskMonitor / KillSwitch / AlertManager 組合せで自動アラート・停止
  - 監視ログは SQLite（デフォルト data/monitoring.db）に永続化
- Portfolio（ポートフォリオ構築）
  - 候補選定、等ウェイト/スコア加重、ポジションサイズ計算、セクター上限適用など
- Research（リサーチ）
  - ファクター計算（Momentum / Value / Volatility 等）
  - 特徴量探索、IC計算、将来リターン計算
- AI モジュール
  - news_nlp: ニュース記事を OpenAI でセンチメント評価し ai_scores に書込
  - regime_detector: MA200 とマクロニュースの LLM 評価で市場レジーム判定
- Tools
  - paper_verification_report: ペーパートレード結果の評価レポート生成
- 設定ユーティリティ
  - config_setup: .env を対話式で作成/更新
  - validate_config: 起動前の設定検証 CLI

---

セットアップ手順（開発環境向け）
1. リポジトリをクローンし、Python 仮想環境を用意
   - python >=3.10 を推奨
   - 仮想環境作成:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
2. 必要パッケージをインストール
   - duckdb, psutil, openai, (PyYAML は config 検証のため任意)
   - 例: pip install duckdb psutil openai pyyaml
   - requirements.txt があればそれを使用してください（本コードでは記載なし）
3. .env の作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - あるいは .env.example を参考に手動で作成（.env を絶対に Git にコミットしない）
4. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告がある場合も exit code 1 にする
5. データディレクトリ等を作成（通常は自動作成されるが事前に作ると安全）
   - mkdir -p data logs

---

主要な使い方（CLI / スクリプト）
- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config [--strict]
- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - 振る舞い:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH / default data/paper_trading.db）を利用します
    - 起動前に data/stop_requested.flag が存在する場合は起動を行わず終了
    - 実行中に data/stop_requested.flag が作成されるとエンジンを停止します
- 監視ループ起動（Monitoring）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き（デフォルト 60 秒）
  - Monitoring は KABUSYS_ENV に関わらず本番 sqlite_path を使用（監視データは共通 DB）
  - 停止フラグ: プロジェクトルート/data/stop_requested.flag を検知するとループを終了
- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db
- AI モジュール呼び出し（プログラムから利用）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - OpenAI API キーは api_key 引数、または環境変数 OPENAI_API_KEY
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - OpenAI が必須な機能は API キーが必要

---

主要な環境変数（デフォルト値を含む）
- 必須（運用時に設定）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 実行環境
  - KABUSYS_ENV: development | paper_trading | live (default: development)
- DB/ファイルパス
  - DUCKDB_PATH (default: data/kabusys.duckdb)
  - SQLITE_PATH (default: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (paper_trading 用、default: data/paper_trading.db)
  - PID_FILE_PATH (default: data/execution.pid)
  - KILL_FLAG_PATH (default: data/kill.flag)
- ログ
  - LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL, default: INFO)
  - LOG_DIR (default: logs/)
- Paper Trading / AI
  - PAPER_FILL_MODE: instant | partial | never | reject (default: instant)
  - OPENAI_API_KEY: OpenAI の API キー（AI 機能を使う場合必須）
- Monitoring
  - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring で使用）

注意: .env 自動ロードはプロジェクトルート（.git または pyproject.toml を基準）から行われます。テストなどで自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

重要ファイル / フラグ
- data/stop_requested.flag
  - run_execution.py / run_monitoring.py が監視している停止フラグ。存在すると動作終了する。
- data/kill.flag
  - KillSwitch が書き込む停止指令ファイル。ExecutionEngine 起動時に KILL_FLAG_CLEAR_ON_START=1 設定で自動クリアするオプションあり（本番では 0 推奨）。
- data/execution.pid
  - ExecutionEngine の PID ファイル（デフォルト path は Settings.pid_file_path）

---

ログ設定
- 共通ユーティリティ: kabusys.utils.logging_setup.setup_logging(app_name="execution"など)
  - stdout（StreamHandler） と 日次ローテーションファイル（TimedRotatingFileHandler）をルートロガーに設定
  - ログディレクトリ: LOG_DIR 環境変数 > 引数 > default "logs/"
  - ログファイル名: <log_dir>/<app_name>.log

---

ディレクトリ構成（src/kabusys の主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / Settings 管理、自動 .env ロードロジック
  - config_setup.py — .env 対話ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト
  - utils/
    - logging_setup.py
    - process_priority.py
  - execution/  (実行エンジン関連)
    - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py など（実装ファイル群）
  - monitoring/
    - monitoring_db.py
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
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - tools/
    - paper_verification_report.py

（上記は主要ファイルを抜粋した構成です。各サブパッケージにさらに詳細実装があります）

---

補足・運用上の注意
- KABUSYS_ENV による振る舞い
  - paper_trading: Mock ブローカーを使用し、ペーパートレード用 DB（PAPER_TRADING_SQLITE_PATH）に記録。実際の発注は行いません。
  - live: 本番モードになります。LINE 通知や kill flag 設定など本番向けガードがあるため設定は十分注意してください。
- DB 初期化
  - run_execution/run_monitoring は起動時に必要な監視テーブル（monitoring_db.init_monitoring_db）を冪等で作成します。既存 DB のマイグレーション処理も組み込みあり。
- OpenAI 利用
  - news_nlp / regime_detector は OpenAI API に依存します。API 呼び出しの失敗はフェイルセーフ（多くは 0 にフォールバック）になっていますが、API キーの管理／レート制限に注意してください。
- 権限/優先度
  - 起動スクリプトは最初に set_process_priority("high") を試みます。環境によっては権限不足で設定できない場合があるため警告が出ますが、処理は継続します。
- 停止シグナル
  - 停止フラグ（stop_requested.flag / kill.flag）はファイル存在による簡易な制御です。運用時は適切な取り扱いが必要です。

---

トラブルシュート
- .env が読み込まれない／想定外の設定が有効になる
  - プロジェクトルートの検出は .git または pyproject.toml を基準に行います。CI 等で CWD が異なる場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して手動で環境変数を供給してください。
- 実行スクリプトが起動しない／即終了する
  - data/stop_requested.flag が存在していないか、KILL_FLAG_CLEAR_ON_START の値を確認してください。
- OpenAI 呼び出しで失敗する／レート制限
  - OPENAI_API_KEY の設定、ネットワーク、API レート、ライブラリバージョン（openai SDK 互換性）を確認してください。news_nlp ではリトライロジックがありますが上限に到達するとスキップされます。

---

さらに参照すべきファイル
- src/kabusys/PortfolioConstruction.md, StrategyModel.md 等の設計ドキュメント（リポジトリに含まれる場合）。コード中に設計参照コメントが多数あります。

---

この README はコードベースのエントリポイント・設定類・運用フローの要点をまとめたものです。詳細な API や内部実装を確認する際は各モジュールのドキュメントコメント（docstring）とソースコードを参照してください。必要であれば実運用向けのデプロイ手順／CI スクリプト／systemd ユニット例なども作成できますのでお知らせください。