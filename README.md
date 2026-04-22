# KabuSys

日本株自動売買システム（KabuSys）のコードベース README（日本語）

このリポジトリは、日本株向けの自動売買システムのコアモジュール群を含みます。発注ロジック・ポートフォリオ構築・監視・研究用ユーティリティ・AI を組み合わせて、実運用・ペーパートレード・研究用途に対応する設計になっています。

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（主なコマンド／例）
- ディレクトリ構成（主要ファイルの説明）
- その他注意事項

---

プロジェクト概要
- KabuSys は日本株の自動売買システムのコア実装群です。
- ExecutionEngine（発注エンジン）／Monitoring（監視）／Portfolio 構築／Research（ファクター計算）／AI（ニュースセンチメント、レジーム判定）等のコンポーネントで構成されます。
- 設定は .env（環境変数）で管理。config_setup による対話式ウィザードと validate_config による事前検証が用意されています。
- ログはコンソール（stdout）と日次ローテートのログファイル（logs/<app>.log）へ出力します。

---

機能一覧（抜粋）
- Execution
  - ExecutionEngine（発注処理の起動 / セッション管理）
  - BrokerClientFactory を用いた実ブローカー / MockBroker の切替（KABUSYS_ENV=paper_trading）
  - Paper trading 用に本番 DB と分離した paper DB を使用
- Monitoring
  - SystemMonitor（CPU/メモリ/ディスク/プロセスの監視、データ鮮度チェック）
  - TradeMonitor（発注ログチェック、滞留注文・約定異常の検出）
  - RiskMonitor（ドローダウン、ポジション上限の監視）
  - KillSwitch（条件により data/kill.flag を書いて ExecutionEngine を止める）
  - MonitoringEngine（各 Monitor を束ねて定期ポーリング）
  - monitoring DB（SQLite）への永続化・マイグレーション機能
- Portfolio（純粋関数群）
  - 候補選定、等配分／スコア重み付け、ポジションサイズ計算（lot 単位、リスク制限、aggregate cap）
  - セクターキャップ、レジーム乗数
- Research
  - ファクター計算（モメンタム、バリュー、ボラティリティ等） — DuckDB を用いた SQL 処理
  - 将来リターン計算、IC、統計要約など
- AI
  - news_nlp: OpenAI を用いたニュースセンチメント集約・ai_scores 書き込み
  - regime_detector: ETF（1321）MA とマクロ記事の LLM センチメントを組み合わせた市場レジーム判定
- ツール
  - config_setup: .env の対話式作成・更新ウィザード
  - validate_config: .env と config/*.yaml の事前検証 CLI
  - paper_verification_report: ペーパートレード結果を評価するレポート生成
- ユーティリティ
  - logging_setup: 一貫したログ設定（stdout + 日次ローテーション）
  - process_priority: プロセス優先度 / CPU affinity 設定ユーティリティ

---

セットアップ手順（簡易）
前提: Python 3.10 以上（| 型ヒントや構文を使用しているため）、SQLite は標準、その他 Python パッケージは pip でインストール。

1. リポジトリを取得
   - git clone <repo>
   - cd <repo>

2. 仮想環境の作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - 必須パッケージの例（実際の requirements.txt を参照してください）
     - duckdb
     - psutil
     - openai
     - PyYAML（config の検証で任意）
   - 例:
     - pip install duckdb psutil openai PyYAML

4. .env の作成
   - 対話式ウィザードを利用:
     - python -m kabusys.config_setup
   - 必須環境変数（例）
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - OPENAI_API_KEY（AI 機能を使う場合）
   - デフォルト（主なもの）
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - KABUSYS_ENV=development|paper_trading|live

   注: .env は絶対に Git にコミットしないでください（config_setup でも警告あり）。

5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 本番を想定する場合は --strict を付けて警告も失敗扱い:
     - python -m kabusys.validate_config --strict

6. データディレクトリ作成（必要に応じて）
   - mkdir -p data logs

7. DB 初期化
   - 多くのテーブルは初回起動時に自動作成されます（init_monitoring_db）。
   - DuckDB の prices_daily / raw_financials 等は研究機能で参照されるため、別途データ投入が必要です（この README ではデータ投入手順は含みません）。

---

使い方（主なコマンド・例）

- ExecutionEngine の起動（発注エンジン）
  - 通常起動:
    - python -m kabusys.run_execution
  - 動作設定:
    - KABUSYS_ENV によりブローカー実装が切替わる
      - paper_trading: MockBrokerClient を使用し data/paper_trading.db に記録（本番 DB と分離）
      - live: 本番ブローカーを使用
  - 実行時は data/stop_requested.flag を監視し、フラグがあると起動しない/停止する
  - 実行時に PID ファイルを書き込む（デフォルト: data/execution.pid、Settings.pid_file_path）

- Monitoring の起動（監視ループ）
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数で上書き可能:
    - MONITOR_POLL_INTERVAL=30  # 秒
  - Monitoring は常に（KABUSYS_ENV にかかわらず）本番 sqlite_path を使用して監視ログを書き込みます

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config [--strict]

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション --db で別 DB を指定可能。環境変数 PAPER_TRADING_SQLITE_PATH も利用可。

- AI 系関数（プログラムから利用）
  - ニュースセンチメントを実行（例）:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key="...")  # duckdb_conn は duckdb.connect() の接続
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key="...")

- ログ
  - デフォルトログディレクトリ: logs/
  - ログファイル: logs/<app_name>.log（app_name: "execution"/"monitoring" 等）
  - ログ設定は kabusys.utils.logging_setup.setup_logging で統一

停止・Kill Switch
- KillSwitch は RiskMonitor 等が検出した条件（ドローダウン超過、ポジション過多など）で data/kill.flag を書き、ExecutionEngine に停止シグナルを送ります。
- 手動で停止を要求する際は data/stop_requested.flag を作成すると run_execution/run_monitoring 側が検出して終了します。
- Kill フラグを自動クリアするオプション KILL_FLAG_CLEAR_ON_START（.env）がありますが、本番では 0（クリアしない）を推奨します。

---

主な環境変数（抜粋・デフォルト）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- OPENAI_API_KEY (AI 機能利用時に必要)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db)
- KABUSYS_ENV (development / paper_trading / live) — default: development
- LOG_LEVEL (デフォルト: INFO)
- MONITOR_POLL_INTERVAL (監視ポーリング間隔、デフォルト: 60 秒)
- KILL_FLAG_CLEAR_ON_START (0/1)

設定自動ロード挙動
- パッケージロード時にプロジェクトルート（.git または pyproject.toml を基準）を探索し、.env および .env.local を自動で読み込みます。
- 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

ディレクトリ構成（主要ファイル / モジュール説明）

src/kabusys/
- __init__.py
  - パッケージメタ情報（__version__ など）
- config.py
  - Settings クラス：.env / 環境変数の取得・検証ロジック、デフォルトパス等
  - 自動 .env 読み込み機能
- config_setup.py
  - .env を対話式で生成・更新するウィザード
- validate_config.py
  - .env と config/*.yaml の事前検証 CLI
- run_execution.py
  - ExecutionEngine の起動スクリプト（PID 管理、stop flag 監視）
- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL で間隔変更）

サブパッケージ（主なモジュール）
- ai/
  - news_nlp.py: ニュースを LLM でスコアリングして ai_scores に書き込む処理
  - regime_detector.py: 市場レジーム判定（MA200 と LLM を合成）
- portfolio/
  - portfolio_builder.py: 候補選定・スコア順ソート
  - position_sizing.py: 発注株数決定・aggregate cap・lot 単位処理
  - risk_adjustment.py: セクターキャップ・レジーム乗数
- research/
  - factor_research.py: モメンタム／バリュー／ボラティリティ計算（DuckDB 経由）
  - feature_exploration.py: 将来リターン、IC、統計サマリ等
- monitoring/
  - monitoring_db.py: SQLite 監視 DB テーブル作成・永続化 API（MonitoringDB）
  - system_monitor.py: システム状態・データ鮮度監視
  - risk_monitor.py: ドローダウン・ポジション上限監視
  - kill_switch.py: kill.flag 書き込みユーティリティ
  - monitoring_engine.py: 各 Monitor を束ねるエンジン
  - trade_monitor.py, alert_manager.py 等（取引監視・通知管理：コードベースに含まれる想定）
- execution/
  - BrokerClientFactory, ExecutionEngine, OrderManager, Reconciler, RiskManager 等（発注ロジック）
- utils/
  - logging_setup.py: ログ設定（stdout + TimedRotatingFileHandler）
  - process_priority.py: プロセス優先度設定（Windows / POSIX 対応）
- tools/
  - paper_verification_report.py: ペーパートレードの検証レポート生成スクリプト

その他トップレベルファイル（実行時生成を想定）
- data/
  - monitoring DB / paper_trading DB / stop_requested.flag / kill.flag / execution.pid など
- logs/
  - ログファイルを格納

※上記はコード内コメントおよび実装から抽出した主要モジュールです。実際のリポジトリには他の補助モジュール（order_repository、trade_monitor 等）も含まれます。

---

注意事項 / 運用のヒント
- .env は絶対に Git にコミットしないでください。
- 本番（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START=0 を推奨します（自動クリアは危険）。
- AI 機能を利用する際は OPENAI_API_KEY を必ず設定してください。API のエラーはフェイルセーフ設計（多くの箇所でフォールバックやスキップ）ですが、キー未設定時は例外が発生します。
- run_execution/run_monitoring は CLI から直接起動できますが、運用では systemd / supervisord 等でプロセス管理すると良いです。
- DuckDB のテーブル（prices_daily、raw_financials 等）は研究・因子計算で使用されます。必要に応じて外部データ取り込みスクリプトでデータを用意してください。
- ローカルでのペーパートレードは KABUSYS_ENV=paper_trading を利用すると本番 DB と切り離された paper_trading DB に記録されます。

---

フィードバック / 開発
- 各モジュールはドキュメント文字列（docstring）と注釈を充実させています。実装詳細は該当ファイルのコメントを参照してください。
- 新しい機能追加や設定変更を行う際は validate_config と config_setup を更新し、必要な環境変数を .env.example に追記してください。

---

この README はコードベースの主要点をまとめたものです。具体的な導入手順や運用フローは貴社／チームの運用ルールに合わせて調整してください。質問や補足があれば教えてください。