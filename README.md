KabuSys — README (日本語)
概要
- KabuSys は日本株の自動売買・調査・監視を支援するPythonパッケージのコレクションです。
- 主な目的: 戦略研究（ファクター計算・特徴量解析）、ポートフォリオ構築（選定・配分・ロット丸め）、実行エンジン（本番 / ペーパートレード）、およびシステム監視・アラート。
- 設計方針: DB（DuckDB/SQLite）をデータ層として利用し、外部API呼び出しは必要最小限（OpenAI 等はAI機能のみ）。モジュールはテストしやすい純粋関数と、シンプルな永続化層で構成。

主な機能一覧
- 環境設定・検証
  - 対話式ウィザードで .env を生成・更新 (kabusys.config_setup)
  - 起動前チェック: 必須環境変数・YAML・パス等を検証 (kabusys.validate_config)
- 実行エンジン
  - ExecutionEngine 起動スクリプト（run_execution）:
    - KABUSYS_ENV による本番 / paper_trading の切替
    - paper_trading 時は MockBrokerClient を使用し DB を分離（data/paper_trading.db）
- 監視・Kill Switch
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - run_monitoring スクリプトでポーリング監視を実行
  - 条件に応じて data/kill.flag を書き込み、ExecutionEngine 停止を指示
- ポートフォリオ構築
  - 候補選定、等重・スコア重み、ポジションサイズ計算（単元丸め、リスク制限）
  - セクター上限やレジーム乗数を適用するユーティリティ
- 研究用モジュール（DuckDBに接続して計算）
  - ファクター計算（モメンタム、バリュー、ボラティリティ）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
- AI（任意）
  - ニュースのセンチメントを OpenAI でスコアリングし ai_scores テーブルへ書き込み
  - 市場レジーム判定（マクロニュース + ETF MA の組合せ）
- ツール
  - Paper Trading 検証レポート生成スクリプト（tools.paper_verification_report）
- ユーティリティ
  - 統一的なログ設定（logs/ に日次ローテート）
  - プロセス優先度・CPU affinity の設定ユーティリティ

セットアップ手順（ローカル開発向け）
1. 前提
   - Python 3.10 以上（| 演算子を使う型注釈のため）
   - git, SQLite（標準で付属）、任意で DuckDB（Pythonパッケージで利用）
2. リポジトリをクローン
   - git clone <repository-url>
   - cd <project-root>
3. 仮想環境の作成
   - python -m venv .venv
   - source .venv/bin/activate （Windows: .venv\Scripts\activate）
4. 依存パッケージをインストール（例）
   - pip install duckdb psutil openai PyYAML
   - 注: OpenAI は AI 機能を使う場合に必要。PyYAML は validate_config の YAML検証に任意で使われます。
5. .env の初期作成
   - python -m kabusys.config_setup
   - あるいは手動で .env を作成。主な環境変数:
     - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
     - 任意: KABUSYS_ENV (development|paper_trading|live, デフォルト development)
     - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH（監視DB デフォルト data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（ペーパートレード用 DB、デフォルト data/paper_trading.db）
     - LOG_LEVEL（デフォルト INFO）
     - OPENAI_API_KEY（AI機能を使う場合）
     - KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするか、開発用）
   - 自動 .env ロードを無効化する場合: 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
6. 設定検証（推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いで exit(1)
7. ログディレクトリの準備
   - デフォルトは logs/（setup_logging が起動時に作成します）。権限に注意。

使い方（起動例）
- 監視ループを起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き（デフォルト 60 秒）
  - 監視は常に本番用の sqlite_path を使用（監視データは環境に依らず共通の監視DBへ記録）
  - 停止: data/stop_requested.flag を作成するか、Ctrl+C
- 実行エンジンを起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBroker と専用 DB（PAPER_TRADING_SQLITE_PATH）を使用
  - 停止: data/stop_requested.flag を作成するとエンジンの起動途中・実行中に停止を指示できます
- 環境設定ウィザード
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config [--strict]
- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - 環境変数 PAPER_TRADING_SQLITE_PATH で DB を指定可能
- AI 機能（ニューススコア・レジーム判定）
  - OPENAI_API_KEY を設定し、対応するモジュール関数を呼ぶ（ライブラリ用途）
  - 例: kabusys.ai.score_news（DuckDB 接続と target_date を与えて呼び出す）
  - 注意: APIキー未設定時は例外を投げる／フォールバック処理がある箇所があります

重要な運用・実装ノート
- データベース
  - DuckDB は時系列価格・財務データ等の分析用 DB。パスは DUCKDB_PATH。
  - SQLite は監視ログや発注ログ用。監視DB は sqlite_path、ペーパートレード時は paper_sqlite_path。
- Kill / Stop フラグ
  - data/kill.flag : Kill Switch により ExecutionEngine を停止・保護するためのフラグ（監視側で書き込まれる）
  - data/stop_requested.flag : プロセス（run_execution / run_monitoring）を安全に終了させるためのフラグ
- ログ
  - ログ設定は kabusys.utils.logging_setup.setup_logging で統一
  - 日次ローテーションで logs/<app_name>.log に保存（デフォルト 30 日保持）
- プロセス優先度
  - run_monitoring/run_execution は起動時に set_process_priority("high") を呼びます（psutil を利用）
- レジーム・AI 処理
  - OpenAI 呼び出しはリトライやレスポンス検証を含む堅牢な実装
  - ただし OpenAI の呼び出し回数やトークン使用料に注意

ディレクトリ構成（主要ファイル・モジュール）
- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数 / Settings 管理（.env 自動ロード）
  - config_setup.py               — .env 対話式ウィザード
  - validate_config.py            — 設定検証 CLI
  - run_monitoring.py             — SystemMonitor ポーリング起動スクリプト
  - run_execution.py              — ExecutionEngine 起動スクリプト
  - utils/
    - logging_setup.py            — ログ設定ユーティリティ
    - process_priority.py         — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py            — SQLite 用永続化・CRUD ラッパー
    - system_monitor.py           — システム・データ鮮度監視
    - trade_monitor.py            — 発注ログ監視（滞留注文・約定異常など）
    - risk_monitor.py             — ドローダウン・ポジション上限監視
    - kill_switch.py              — kill.flag の作成・評価
    - alert_manager.py            — （アラート送信をまとめる想定モジュール）
    - monitoring_engine.py        — 各 monitor を束ねるエンジン
  - execution/                     — ExecutionEngine / BrokerFactory / OrderManager 等（実行関連）
  - portfolio/
    - portfolio_builder.py        — 候補選定・重み計算
    - position_sizing.py          — 株数計算・集約キャップ調整
    - risk_adjustment.py          — セクター上限・レジーム乗数
  - research/
    - factor_research.py          — ファクター計算（momentum/value/volatility）
    - feature_exploration.py      — 将来リターン・IC・統計サマリー
  - ai/
    - news_nlp.py                 — ニュース文章の LLM スコアリング
    - regime_detector.py          — マクロセンチメント + MA を使ったレジーム判定
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成ツール
- data/                            — DB / pid / flag 等の実ファイル（実行時に使用）
  - monitoring.db (デフォルト)
  - paper_trading.db (paper_trading 用)
  - kill.flag, stop_requested.flag, execution.pid
- logs/                            — ログ出力先（setup_logging が作成）

開発時のヒント
- DuckDB には prices_daily / raw_financials / raw_news 等のテーブルが想定されているため、
  解析機能を利用するには事前にデータ投入が必要です（データ取得パイプラインは別途実装）。
- 単体モジュール（portfolio, research）は DuckDB 接続や単純な引数でテストが可能です。副作用を持たない純粋関数が多く含まれます。
- 自動 .env ロードはプロジェクトルート（.git または pyproject.toml が存在する場所）を基準に行われます。CI/テスト時に自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

ライセンス・貢献
- 本 README にライセンス情報は含まれていません。リポジトリの LICENSE ファイルを参照してください。
- 貢献方法やコントリビュートの手順はプロジェクトの CONTRIBUTING.md を参照してください（存在する場合）。

以上が簡易 README です。必要であれば実行例の詳細（環境変数テンプレート、systemd / supervisor 用のサービス定義例、Dockerfile / docker-compose 例）や各モジュールの API 使用例を追加できます。どの情報を優先して詳述しますか？