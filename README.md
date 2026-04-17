# KabuSys — 日本株自動売買システム

このリポジトリは、バックテスト／ペーパートレード／本番発注を想定した日本株自動売買システムのコアモジュール群です。  
README は最小限のセットアップ手順・使い方・ディレクトリ構成を日本語でまとめたものです。

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（主要コマンド）
- 重要な環境変数
- ファイル / ディレクトリ構成（主要ファイルの説明）
- 補足メモ

---

プロジェクト概要
- KabuSys は日本株向けの自動売買エンジン (ExecutionEngine)、監視（Monitoring）機能、ファクター計算・リサーチ、ポートフォリオ構築ユーティリティ、AI を用いたニュース評価などを含むライブラリ群です。
- 設計方針として、実行環境（development / paper_trading / live）を区別し、ペーパートレード時は本番 DB と完全分離する仕組みがあります。
- DuckDB をデータ分析（prices, raw_financials 等）、SQLite を監視・注文ログ保存に使用します。OpenAI を使った NLP モジュールも含まれます（外部 API キーが必要）。

機能一覧
- ExecutionEngine 起動スクリプト（run_execution）  
  - 本番 / ペーパートレードを環境変数 KABUSYS_ENV により切替
  - Paper Trading では MockBrokerClient を使用し data/paper_trading.db に記録
  - プロセス優先度設定、PID ファイルによる存在チェック、停止フラグ対応
- Monitoring（run_monitoring / MonitoringEngine）  
  - システムリソース（CPU/Mem/Disk）監視、データ鮮度チェック、プロセス死活検出
  - 注文滞留・約定異常検出、ドローダウン / ポジション上限監視（Kill Switch）
  - 監視ログ永続化（SQLite）とリスクイベント記録
- Portfolio construction utilities  
  - 候補選定、重み計算（等配分・スコア加重）、ポジションサイズ計算（単元株丸め・集約キャップ）
  - セクター集中制限、レジームベースの乗数適用
- Research / Factor modules（DuckDB ベース）  
  - モメンタム・ボラティリティ・バリュー等のファクター計算、将来リターン計算、IC 計算、統計要約
- AI モジュール（OpenAI）  
  - ニュース記事から銘柄ごとにセンチメント評価（news_nlp）
  - マクロニュース + ETF MA 指標を合成して市場レジーム判定（regime_detector）
  - LLM 呼び出しはリトライ・検証ロジックを備え、失敗時はフェイルセーフで継続
- ツール
  - 設定ウィザード（config_setup）: 対話式で .env を作成・更新
  - 設定検証 CLI（validate_config）: 起動前の必須環境変数・設定ファイルチェック
  - Paper Trading 検証レポート生成（tools/paper_verification_report）

セットアップ手順（開発環境向け・推奨）
1. リポジトリをクローン
   - git clone <repo-url>

2. Python 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb psutil openai
   - PyYAML は設定ファイル検証（validate_config の YAML パース）を行う場合に必要: pip install PyYAML
   - （requirements.txt がある場合はそれを利用）

4. .env の準備（対話式ウィザード推奨）
   - python -m kabusys.config_setup
   - ウィザードは .env を生成します（.env は必ず Git 管理から除外してください）

5. 設定検証（任意）
   - python -m kabusys.validate_config
   - 警告も厳密に扱いたい場合は --strict を付与

主要な使い方（コマンド）
- 実行エンジン（注文発行）を起動
  - python -m kabusys.run_execution
  - 注意: KABUSYS_ENV が paper_trading の場合は paper DB に記録され、本番 DB と分離されます。
  - 停止はプロジェクトルート/data/stop_requested.flag を作成すると実行中エンジンが検知して停止します。
- 監視ループを起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）
  - 監視は本番 sqlite_path を使用（環境にかかわらず本番監視 DB に書き込み）
- 設定ウィザード（.env 作成/更新）
  - python -m kabusys.config_setup
- 設定検証（起動前チェック）
  - python -m kabusys.validate_config [--strict]
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD
  - --db で SQLite ファイルを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH でも指定可）

重要な環境変数（代表）
- 必須
  - JQUANTS_REFRESH_TOKEN : J-Quants API 用リフレッシュトークン
  - KABU_API_PASSWORD     : kabuステーション API パスワード
- 実行環境
  - KABUSYS_ENV : development | paper_trading | live（デフォルト: development）
- データベース（デフォルト値）
  - DUCKDB_PATH = data/kabusys.duckdb
  - SQLITE_PATH = data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH = data/paper_trading.db（paper_trading モード用）
- OpenAI（AI モジュールを使う場合）
  - OPENAI_API_KEY
- ログ / PID / Kill Switch
  - LOG_LEVEL (DEBUG/INFO/...)
  - PID_FILE_PATH (デフォルト data/execution.pid)
  - KILL_FLAG_PATH (デフォルト data/kill.flag)
  - KILL_FLAG_CLEAR_ON_START (0/1) — 起動時に kill.flag を自動クリアするか
- モニタ / 実行
  - MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）
- Paper Trading 固有
  - PAPER_FILL_MODE — instant | partial | never | reject（デフォルト "instant"）

デフォルト .env（概略）
- KABUSYS_ENV=development
- JQUANTS_REFRESH_TOKEN=
- KABU_API_PASSWORD=
- KABU_API_BASE_URL=http://localhost:18080/kabusapi
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- LINE_CHANNEL_ACCESS_TOKEN=
- LINE_USER_ID=
- LOG_LEVEL=INFO
- KILL_FLAG_CLEAR_ON_START=0

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py  — パッケージ定義
  - config.py    — 環境変数と設定の読み込み・整合チェックユーティリティ
  - config_setup.py — .env を対話式に生成するウィザード
  - validate_config.py — 起動前設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — Monitoring ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成
  - ai/
    - news_nlp.py         — ニュース記事の LLM によるセンチメント評価
    - regime_detector.py  — ETF MA とマクロセンチメントを用いたレジーム判定
  - monitoring/
    - monitoring_db.py    — 監視ログ用 SQLite の初期化・永続化 API
    - system_monitor.py   — システム状態・データ鮮度チェック
    - trade_monitor.py    — 注文滞留・約定異常検出
    - risk_monitor.py     — ドローダウン・ポジション上限監視
    - kill_switch.py      — kill.flag の書き込み/評価（ExecutionEngine 停止トリガ）
    - monitoring_engine.py — 各 Monitor を束ねるループ実装
    - alert_manager.py    — （アラート送信の抽象化：未列挙）
  - execution/  — ExecutionEngine、OrderManager、BrokerFactory 等（コードベースの他ファイル）
  - portfolio/  — 銘柄選定・重み算出・ポジションサイズ計算等（pure functions）
  - research/   — factor_research, feature_exploration（DuckDB を使った分析）
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

補足メモ / 運用上の注意
- .env は Git にコミットしないこと（機密情報を含む）。config_setup で生成後 .gitignore へ追加してください。
- OpenAI を用いる機能は API キーが必須です（環境変数 OPENAI_API_KEY）。
- run_execution/run_monitoring は stop_requested.flag（プロジェクト data/stop_requested.flag）をチェックして優雅に終了します。停止させたい場合は該当ファイルを作成してください。
- モニタリングは監視 DB（SQLite）に常に本番用パスを使って書き込むため、環境をまたいで監視 DB を共有しないよう注意してください。Paper Trading は paper_sqlite_path を使用して分離します。
- PyYAML が無い場合、validate_config は YAML ファイルの内容検証をスキップします（警告）。
- DuckDB への書き込み処理（ai_scores など）は一部互換性対策（executemany の空リスト対策など）を実装していますが、実運用／バージョン差異の確認は行ってください。

何か追記してほしい箇所（例：依存関係の固定化、追加の CLI、開発用の docker-compose など）があれば教えてください。README をプロジェクトに合わせて調整します。