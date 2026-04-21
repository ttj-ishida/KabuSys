# KabuSys

日本株向け自動売買システムの Python コードベース（モジュール群）。  
このリポジトリは取引エンジン、監視・アラート、ポートフォリオ構築、リサーチ、AI（ニュースNLP / レジーム判定）などを含む、実運用を想定した設計になっています。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方
- ディレクトリ構成（主要ファイル説明）
- 環境変数一覧（重要項目）
- 運用上の注意

---

プロジェクト概要
- KabuSys は日本株の自動売買システムを構成するライブラリ兼起動スクリプト群です。
- 主要機能はシグナル→ポートフォリオ構築→発注（ExecutionEngine）→監視（Monitoring）→アラートに至るワークフローをカバーします。
- データレイヤは DuckDB（分析用）と SQLite（監視 / ペーパートレード用）を併用します。
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント評価 / マクロセンチメントで、レジーム判定やファクター拡張が可能です。

---

機能一覧
- 実行エンジン
  - run_execution.py: ExecutionEngine を起動。環境に応じて本番／ペーパートレード切替。
  - ペーパートレード時は MockBrokerClient を使い、data/paper_trading.db に記録（本番 DB と分離）。
- 監視（Monitoring）
  - run_monitoring.py: SystemMonitor をポーリングして監視データを収集。
  - MonitoringEngine, SystemMonitor, TradeMonitor, RiskMonitor, KillSwitch, AlertManager 等を提供。
  - SQLite ベースの永続化層（monitoring_db）を備え、system_status/trade_logs/positions/risk_logs/dashboard を管理。
- ポートフォリオ構築
  - 候補選定、重み計算（等金額・スコア加重）、セクター制約、レジーム乗数、株数決定（単元丸め・リスクベース）等の純粋関数群。
- リサーチ
  - DuckDB 接続を受けるファクター計算（momentum, volatility, value）や将来リターン計算、IC 計算、統計サマリー等。
- AI（OpenAI）
  - news_nlp: ニュースをまとめて LLM に投げ、銘柄別センチメントを ai_scores テーブルへ書き込むロジック。
  - regime_detector: ETF 200日 MA とマクロニュースセンチメントを合成して market_regime を算出・永続化。
- ユーティリティ
  - 環境変数の自動読み込み・パーサ（.env 対応）
  - 対話式 .env 作成ウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py）
  - 日次ローテーションを含む統一ログ設定ユーティリティ
  - プロセス優先度 / CPU affinity 設定ユーティリティ
- ツール
  - paper_verification_report: ペーパートレード DB を解析して検証レポートを出力

---

セットアップ手順（ローカル開発向け）
1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo-root>

2. Python 仮想環境の作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - requirements.txt がある場合は `pip install -r requirements.txt` を推奨。
   - 最低限の依存（本リポジトリ内で使用されている主な外部パッケージ）:
     - duckdb
     - psutil
     - openai
     - PyYAML（config ファイル検証時に任意で使用）
   - 例:
     - pip install duckdb psutil openai PyYAML

4. .env の作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
     - 対話形式で .env を作成・更新します。生成された .env は git にコミットしないでください（秘密情報を含みます）。
   - あるいは .env.example を参考に手動作成。

5. 設定検証
   - python -m kabusys.validate_config
   - 警告もエラー扱いにする場合:
     - python -m kabusys.validate_config --strict

6. データベース / データ準備
   - monitoring 用 SQLite（デフォルト: data/monitoring.db）は run_* スクリプトが起動時に必要なテーブルを作成します。
   - DuckDB（デフォルト: data/kabusys.duckdb）は価格・ニュース等の分析データを格納するため、別途データ投入パイプラインが必要です（本リポジトリに ETL がない場合は事前に用意してください）。

---

基本的な使い方（起動例）
- ExecutionEngine を起動（本番 / paper_trading は KABUSYS_ENV による）
  - KABUSYS_ENV=development (例) の .env を用意した上で:
    - python -m kabusys.run_execution
  - 起動前に data/stop_requested.flag（停止フラグ）があると起動を行いません。

- Monitoring を起動
  - MONITOR_POLL_INTERVAL を秒で上書き可能（デフォルト 60）
    - 例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - Monitoring は常に本番 sqlite_path を使用して監視テーブルに記録します（KABUSYS_ENV に依存しない）。

- .env の対話式作成
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も fail 扱い

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

- 個別 API 呼び出し（Python から）
  - AI スコアリング:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key="...")

  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key="...")

注意: 上記の関数は DuckDB 接続と適切なデータスキーマ（prices_daily, raw_news 等）を前提とします。

---

ディレクトリ構成（主要ファイルと役割）
- src/kabusys/
  - __init__.py — パッケージ定義・バージョン
  - config.py — 環境変数 / 設定読み込みロジック（.env 自動読み込み、Settings クラス）
  - config_setup.py — 対話式 .env ウィザード
  - validate_config.py — 起動前設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト（PID/停止フラグ管理、paper_trading 分離）
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト（MONITOR_POLL_INTERVAL 環境変数対応）
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成スクリプト
  - ai/
    - news_nlp.py — ニュースセンチメント評価 / ai_scores 書き込みロジック（OpenAI 依存）
    - regime_detector.py — マクロ + ETF MA を合成した市場レジーム判定（OpenAI 依存）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - risk_adjustment.py — セクター制約・レジーム乗数
    - position_sizing.py — 株数決定・単元丸め・投下資金スケーリング
  - research/
    - factor_research.py — モメンタム・ボラティリティ・バリュー等の計算（DuckDB）
    - feature_exploration.py — 将来リターン / IC / 統計サマリー等
  - monitoring/
    - monitoring_db.py — SQLite ベースの永続化層（テーブル作成・CRUD）
    - monitoring_engine.py — 各 Monitor 統括（ポーリングループ）
    - system_monitor.py — システム状態・データ鮮度監視
    - risk_monitor.py — ドローダウン / ポジション数監視
    - kill_switch.py — 停止フラグ管理（data/kill.flag 書き込み）
    - ...（TradeMonitor, AlertManager 等がある想定）
  - utils/
    - logging_setup.py — 統一ログ設定（stdout + 日次ローテートファイル）
    - process_priority.py — プロセス優先度 / CPU affinity 設定
  - (その他) execution/*, data/* 等サブパッケージ（リポジトリに応じて存在）

補足ファイル（運用で重要なファイル）
- data/stop_requested.flag — 実行中のループを停止するためのフラグファイル（run_execution/run_monitoring が監視）
- data/kill.flag — KillSwitch により ExecutionEngine を停止するために監視側が書き込むフラグ
- data/execution.pid — ExecutionEngine の PID ファイル（設定で指定可能）
- logs/<app>.log — 日次ローテートされるログファイル（デフォルト logs/ ディレクトリ）

---

主要な環境変数（重要項目）
- 必須（validate_config で検査）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 推奨 / よく使うもの
  - KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite（デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
  - PAPER_FILL_MODE — ペーパートレードの約定挙動: instant | partial | never | reject（デフォルト instant）
  - LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
  - LOG_DIR — ログファイル保存ディレクトリ（デフォルト logs/）
  - OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector 実行時に必要）
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — LINE 通知用（任意）
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動でクリア（0/1、デフォルト 0 推奨）
- 監視関連
  - MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）

注意: Settings クラスは必須環境変数が未設定だと ValueError を投げます。validate_config で事前チェックを行ってください。

---

運用上の注意 / トラブルシュート
- .env は機密情報を含むため絶対にコミットしないこと。
- KABUSYS_ENV=live を設定する際は LINE 通知設定や kill flag の扱い等を慎重に確認してください（validate_config は live 時に追加ガードを行います）。
- run_execution / run_monitoring は stop フラグ（data/stop_requested.flag）や kill.flag を確認して安全に停止します。運用中の強制操作時はこれらのファイルを利用してください。
- ログ出力は stdout とファイルの両方に行われます。ログファイルのディレクトリ作成に失敗した場合はコンソールのみの出力になります。
- OpenAI を利用する機能は API キー・コスト・レート制限に留意してください。news_nlp と regime_detector はリトライ・バックオフの実装がありますが、API 利用制約は運用者の責任です。
- DuckDB / SQLite のスキーマはコード内で初期化/マイグレーションされますが、分析用の prices_daily, raw_news 等のデータは別途準備が必要です。

---

ライセンス / 責任
- このドキュメントにはライセンス情報が含まれていません。実運用・商用利用時はリポジトリ内の LICENSE（存在する場合）を確認してください。
- 本プロジェクトは投資助言を目的とするものではありません。運用は自己責任で行ってください。

---

その他
- 開発者向け: 単体関数群（portfolio, research など）は副作用がなくテストしやすい純粋関数として実装されています。ユニットテストを作成しやすい設計です。
- config/.yaml 系のテンプレートは scripts/generate_config.py 等で生成する想定のメッセージがあり、validate_config は YAML のパース検証を行えます（PyYAML がインストールされている場合）。

必要であれば、この README を README.md としてリポジトリルートに書き出すための具体的なテンプレートや、.env.example の雛形（サンプル）も作成します。どちらがよいですか？