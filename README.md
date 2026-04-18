# KabuSys — README (日本語)

このリポジトリは日本株向けの自動売買・研究・監視ユーティリティ群を含むパッケージ「KabuSys」です。戦略の研究、ポートフォリオ構築、発注エンジン（ExecutionEngine）、監視・アラート、AI ベースのニュース評価などのコンポーネントを収録しています。

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方（起動コマンドと主要スクリプト）
- 主要環境変数（.env）
- ファイル / ディレクトリ構成（抜粋）
- 運用上の注意

プロジェクト概要
- Python パッケージとして実装された日本株自動売買システムのユーティリティ群。
- データ永続化は DuckDB（分析用）と SQLite（監視・発注ログ）を使用。
- 発注実行は live / paper_trading（ペーパートレード） / development の3モードをサポート。
- 監視コンポーネントはシステム状態・注文状態・リスク（ドローダウンやポジション数上限）を定期チェックし、必要に応じて kill flag を作成してエンジン停止を促します。
- AI（OpenAI）を用いたニュースのセンチメント評価や市場レジーム判定機能を含む。

主な機能一覧
- 環境設定ウィザード（kabusys.config_setup）
  - 対話形式で .env を生成 / 更新
- 設定検証ツール（kabusys.validate_config）
  - .env と config/*.yaml の基本チェック
- 実行エンジン起動スクリプト（kabusys.run_execution）
  - ExecutionEngine を起動。paper_trading では MockBroker を用いて paper DB を使用
- 監視ループ起動スクリプト（kabusys.run_monitoring）
  - SystemMonitor のポーリングループを起動。MONITOR_POLL_INTERVAL で間隔を変更可
- 監視ライブラリ（kabusys.monitoring.*）
  - SystemMonitor, TradeMonitor, RiskMonitor, KillSwitch, MonitoringEngine, MonitoringDB
- ポートフォリオ構築モジュール（kabusys.portfolio.*）
  - 候補選定、等重/スコア重み、ポジションサイジング、セクター制約、レジーム乗数
- 研究用モジュール（kabusys.research.*）
  - モメンタム、ボラティリティ、バリューなどのファクター計算・特徴量探索
- AI モジュール（kabusys.ai.*）
  - ニュース NLP（OpenAI を用いた銘柄ごとのスコア算出）、市場レジーム判定
- ツール
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）

セットアップ手順（ローカル開発向け）
1. リポジトリをクローン
   - git clone <repo-url>
2. 仮想環境を作成して有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - 必須の主な依存:
     - duckdb, psutil, openai
     - （YAML チェックを行う場合）PyYAML
   - 例:
     - pip install duckdb psutil openai pyyaml
   - （プロジェクトに requirements.txt があればそれを利用してください）
4. .env の作成
   - 対話的ウィザードを推奨:
     - python -m kabusys.config_setup
   - 生成後、設定を検証:
     - python -m kabusys.validate_config
5. ディレクトリ / DB の初期化
   - デフォルトで data/ 以下に SQLite / DuckDB が置かれます。起動時に自動作成されることが多いです。

主要環境変数（.env）
- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用トークン
  - KABU_API_PASSWORD — kabuステーション API パスワード
- 推奨 / 任意（主なもの）
  - KABUSYS_ENV — 実行環境: development | paper_trading | live （デフォルト: development）
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — SQLite 監視DB（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
  - LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
  - LOG_DIR — ログ保存ディレクトリ（デフォルト: logs/）
  - OPENAI_API_KEY — OpenAI を使う機能（news_nlp / regime_detector）で必要
  - PAPER_FILL_MODE — ペーパートレード時の約定挙動（instant|partial|never|reject）
  - MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト: 60）
  - KILL_FLAG_CLEAR_ON_START — 実行時に data/kill.flag を自動でクリアするか（0/1、デフォルト: 0）
- 重要:
  - KABUSYS_ENV=live は本番発注を行います。値を慎重に設定してください。

使い方（主要コマンド例）
- 環境ウィザード
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
  - オプション: --strict（警告も失敗扱い）
- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - ポイント:
    - KABUSYS_ENV=paper_trading のときは MockBroker を使い、data/paper_trading.db を使用（本番 DB と分離）
    - 起動時に data/stop_requested.flag が存在すると起動をスキップ
    - 実行中に data/stop_requested.flag が作成されると Engine を停止
- 監視ループ起動（SystemMonitor）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可（デフォルト 60 秒）
  - 監視は常に本番用 sqlite_path を使う（環境にかかわらず）
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - SQLite DB はデフォルト data/paper_trading.db、--db で指定可能
- AI 機能（ニュース NLP / レジーム判定）
  - OpenAI API キー（OPENAI_API_KEY）が必須
  - 関数として利用: kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime

ログ / 実行ファイル
- ログは kabusys.utils.logging_setup.setup_logging により統一的に出力
  - stdout（StreamHandler）およびファイル（logs/<app_name>.log、日次ローテーション）に出力
- PID / フラグ
  - PID ファイル: data/execution.pid（ExecutionEngine で使用）
  - 停止リクエスト: data/stop_requested.flag（存在すると run_* スクリプトが停止または起動を制御）
  - Kill Switch: data/kill.flag（KillSwitch を通じて書き込まれ、Engine に停止を促す）
  - kill.flag 自動クリアは KILL_FLAG_CLEAR_ON_START=1 で可能（本番では非推奨）

ディレクトリ構成（主要ファイル抜粋）
- src/kabusys/
  - __init__.py
  - config.py               — 環境変数 / Settings 管理
  - config_setup.py         — .env 対話ウィザード
  - validate_config.py      — 設定検証 CLI
  - run_execution.py        — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — SystemMonitor ポーリング起動スクリプト
  - utils/
    - logging_setup.py      — ログ設定ユーティリティ
    - process_priority.py   — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py      — SQLite 用永続化層（テーブル初期化含む）
    - system_monitor.py     — システム・データ鮮度監視
    - trade_monitor.py      — 注文系監視（存在）
    - risk_monitor.py       — ドローダウン・ポジション上限監視
    - kill_switch.py        — kill.flag 書き込みユーティリティ
    - monitoring_engine.py  — 全体を束ねるエンジン
    - alert_manager.py      — 通知管理（存在）
  - execution/              — ExecutionEngine 周り（broker, order_manager 等）
  - portfolio/              — ポートフォリオ構築（builder, sizing, risk_adjustment）
  - research/               — ファクター計算 / 特徴量解析
  - ai/
    - news_nlp.py           — ニュースセンチメント（OpenAI）
    - regime_detector.py    — 市場レジーム判定（OpenAI + MA200）
  - tools/
    - paper_verification_report.py — Paper Trading 用検証レポート

運用上の注意 / ベストプラクティス
- 本番（KABUSYS_ENV=live）は慎重に:
  - 必須環境変数や通知設定（LINE など）を必ず検証すること
  - validate_config を事前に実行し、警告・エラーを確認すること
- kill.flag / stop_requested.flag の扱い:
  - 運用時は停止フラグの存在確認・クリアを運用手順に明確に組み込む
  - KILL_FLAG_CLEAR_ON_START=1 は本番では危険（自動クリアは推奨しない）
- OpenAI API の使用:
  - API キー（OPENAI_API_KEY）を厳重に管理すること
  - レート制限や API 失敗に備えてログとリトライ設定を確認すること
- ログディレクトリ:
  - デフォルトは logs/。容量管理（ローテーション、バックアップ数）が設定済みだが運用監視を推奨
- 開発環境では paper_trading モードを活用:
  - 発注ロジックの挙動確認、Paper DB による分離された検証が可能

追加情報 / トラブルシューティング
- .env の自動読み込み:
  - config.py はプロジェクトルート（.git または pyproject.toml）を検出して .env/.env.local を自動ロードします。
  - 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- PyYAML 未インストール時:
  - validate_config は YAML の内容検証をスキップし警告を出力します。config/*.yaml を検証する場合は PyYAML をインストールしてください。
- DB マイグレーション:
  - monitoring_db.init_monitoring_db は冪等的にテーブル・インデックスを作成し、既存 DB に対する簡易的なカラム追加マイグレーションも行います。

以上がこのコードベースの主要な説明です。具体的なモジュールや関数の実装（例: ExecutionEngine の詳細、TradeMonitor の仕様など）は各モジュールのドキュメント / docstring を参照してください。必要であれば README に含めるサンプル .env のテンプレートやよくある運用手順（デプロイ手順、Cron / systemd 用の起動例）も追記できます。どの情報を追加しますか？