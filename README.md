KabuSys — 日本株自動売買システム
=================================

このリポジトリは日本株向けの自動売買フレームワーク（KabuSys）の一部実装です。ポートフォリオ構築、ポジションサイジング、モニタリング、Execution エンジン、Research/ファクター計算、AI（ニュース NLP / レジーム判定）などの機能を含みます。

主な目的
- 自動発注エンジン（本番 / ペーパートレード）
- システム稼働性・注文監視と Kill Switch（安全停止）
- ファクター計算・リサーチ用ユーティリティ
- ニュースを用いた LLM ベースのセンチメント評価（OpenAI）
- ペーパートレード検証レポート作成ツール

主な機能一覧
- 実行系
  - run_execution.py: ExecutionEngine 起動スクリプト
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、データを data/paper_trading.db に記録（本番 DB と分離）
    - 起動時にプロセス優先度を "high" に設定
    - 停止は data/stop_requested.flag によるファイルフラグで制御
- 監視系
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト
    - MONITOR_POLL_INTERVAL 環境変数で間隔を上書き（デフォルト 60 秒）
    - 監視用 DB（SQLite）への永続化（monitoring_db）
    - Kill Switch の評価（リスク/注文/システム監視結果から kill.flag を作成）
- モニタリング DB 層
  - monitoring/monitoring_db.py: system_status / trade_logs / positions / risk_logs / dashboard の初期化・読み書き
- リスク監視 / アラート
  - monitoring/risk_monitor.py: ドローダウンやポジション上限を検知して risk_logs に記録
  - monitoring/kill_switch.py: kill.flag 書き込み（Execution 停止トリガ）
  - monitoring/monitoring_engine.py: 各モニタを束ねてポーリング、AlertManager 連携ポイント
- ポートフォリオ構築（純粋関数）
  - portfolio/*.py: 候補選定（select_candidates）、重み計算、ポジションサイズ計算、セクター上限、レジーム乗数
- Research
  - research/factor_research.py: momentum / volatility / value ファクター計算（DuckDB を使用）
  - research/feature_exploration.py: 将来リターン、IC 計算、ファクター統計
- AI（OpenAI）
  - ai/news_nlp.py: raw_news を集約して OpenAI に投げ、銘柄ごとのセンチメントを ai_scores に書き込み
  - ai/regime_detector.py: ETF 1321 の MA200 とマクロニュースの LLM スコアを合成して日次レジーム判定
- ユーティリティ
  - utils/logging_setup.py: 統一的なログ設定（stdout + 日次ローテーションファイル）
  - utils/process_priority.py: Windows / POSIX 共通のプロセス優先度設定
  - config.py: .env 自動読み込み・Settings クラス（環境変数ラッパー）
  - config_setup.py: .env 対話ウィザード（初期設定支援）
  - validate_config.py: 環境変数 / config/*.yaml 等の検証 CLI
- ツール
  - tools/paper_verification_report.py: ペーパートレード DB から検証レポートを生成

セットアップ手順（開発向け）
- 前提（例）
  - Python 3.10+（型注釈や構文を利用）
  - SQLite（標準で同梱）
  - DuckDB（Python パッケージ）
- 必要パッケージのインストール（例）
  - pip install duckdb psutil openai
  - （任意だが推奨）PyYAML（config 検証用）: pip install pyyaml
  - もし requirements.txt がある場合: pip install -r requirements.txt
- プロジェクトルートを特定して .env を用意
  - 対話式で作成: python -m kabusys.config_setup
  - もしくは .env を手動で作成（下記に主要変数の説明）
- 設定検証
  - python -m kabusys.validate_config
  - 警告も失敗扱いにしたい場合: python -m kabusys.validate_config --strict
- ディレクトリ作成（必要に応じて）
  - data/ logs/ を作成。logging_setup は自動作成を試みますが、権限で失敗する場合があります。

主要な環境変数（Settings に定義されているもの）
- KABUSYS_ENV: 実行環境（development | paper_trading | live）。デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabuステーションのベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（ai/news_nlp.py, ai/regime_detector で使用）
- PAPER_FILL_MODE: paper_trading 時の MockBroker の約定モード（instant|partial|never|reject、デフォルト instant）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- LOG_LEVEL: ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL）
- LOG_DIR: ログファイル保存ディレクトリ（デフォルト logs/）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START 等（Settings を参照）

主な実行方法（例）
- .env を作成・確認した後、監視を起動:
  - python -m kabusys.run_monitoring
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可（デフォルト 60）
    - 監視は常に（設定に関わらず）settings.sqlite_path（本番監視 DB）を使用します
    - 終了: Ctrl+C またはリポジトリルート/data/stop_requested.flag を作成して検知
- Execution を起動:
  - python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用しペーパートレード DB（PAPER_TRADING_SQLITE_PATH）に書き込む
    - 起動時に data/stop_requested.flag が存在する場合は起動しません
    - 実行は別スレッドで走り、stop フラグが検知されると engine.stop() が呼ばれます
- ペーパートレード検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で別 SQLite を指定可。環境変数 PAPER_TRADING_SQLITE_PATH でも指定可
- .env の生成:
  - python -m kabusys.config_setup
- 設定の検証:
  - python -m kabusys.validate_config [--strict]

ログ・停止フラグ・Kill Switch の挙動
- ログ
  - setup_logging により stdout と logs/<app_name>.log（日次ローテーション）にログ出力
  - デフォルト保存先は logs/
- 停止制御
  - data/stop_requested.flag を作成すると run_monitoring / run_execution のループが検知して終了します
  - Kill Switch は監視コンポーネントが判定した重大アラート（ドローダウンやポジション過多等）で data/kill.flag を書き、ExecutionEngine に停止を促します
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動クリアします（本番では 0 を推奨）

AI 機能の注意点
- OpenAI API を使う処理（ai/news_nlp, ai/regime_detector）は OPENAI_API_KEY が必要
- レート制限や API エラー時はリトライ（指数バックオフ）を実装していますが、失敗時はフォールバックやスキップ動作を行いサービス全体の停止を防ぐ設計です
- 出力は JSON 形式のバリデーションを行い、安全に DB に書き込みます

簡単なワークフロー例（ペーパートレード）
1. .env を作成し KABUSYS_ENV=paper_trading を設定（config_setup を推奨）
2. python -m kabusys.validate_config で検証
3. python -m kabusys.run_monitoring を起動（監視を常時稼働）
4. python -m kabusys.run_execution を別プロセスで起動（Engine がターゲット日に対して処理）
5. 実行中に問題が発生した場合、監視が kill.flag を作成して Execution を安全停止

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / .env 自動ロード / Settings
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 起動前検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor 起動スクリプト
  - execution/               — 発注関連（Engine / OrderManager 等）（省略箇所あり）
  - monitoring/
    - monitoring_db.py       — 監視用 SQLite スキーマ & DB 操作
    - system_monitor.py      — システム状態・データ鮮度監視
    - trade_monitor.py       — 注文滞留 / 約定異常検出（実装あり）
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - kill_switch.py         — kill.flag 書込ロジック
    - monitoring_engine.py   — 各モニタの統合ポーリング
    - alert_manager.py       — アラート送信（LINE 等）（実装参照）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py             — ニュース NLP（OpenAI）による銘柄別センチメント
    - regime_detector.py      — 市場レジーム判定（MA + マクロニュース）
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py
    - process_priority.py

補足 / 開発向けメモ
- DuckDB は分析用 DB。research モジュールは DuckDB 接続を受け取り SQL で高速に集計します。
- monitoring は軽量の SQLite を使って運用ログを永続化します（system_status / trade_logs / positions / risk_logs / dashboard）。
- config.py はプロジェクトルート（.git / pyproject.toml）を探索して .env を自動ロードします。テスト時や特殊環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化できます。
- process_priority.set_process_priority("high") を起動直後に呼んでおり、Windows / POSIX の差を吸収しますが、権限不足で設定できない場合は警告を出してスキップします。

ライセンス・貢献
- 本ドキュメントではライセンス情報は記載していません。リポジトリルートの LICENSE を確認してください。
- 変更・機能追加は pull request を通じてお願いします。ユニットテストおよび設定検証 (validate_config) を追加してからマージすることを推奨します。

---

不明点や README に追加してほしい情報（例:各 CLI の出力サンプル、.env の具体的サンプル、コンテナ化手順など）があれば教えてください。必要に応じて README を追記・整形します。