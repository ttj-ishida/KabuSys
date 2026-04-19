# KabuSys — README (日本語)

概要
- KabuSys は日本株向けの自動売買・研究・監視フレームワークです。
- 主な目的は「戦略の研究（ファクター計算）」「発注エンジン（実行／ペーパートレード）」「システム監視／Kill Switch」「ニュースの NLP による補助情報」の提供です。
- ライブラリはモジュール化されており、個別機能（ポートフォリオ構築、ポジションサイジング、ファクター計算、AI スコアリング、監視）を組み合わせて運用できます。

主な機能一覧
- 設定管理
  - .env 自動読み込み / 対話式ウィザード（kabusys.config_setup）
  - 起動前設定検証（kabusys.validate_config）
- 実行エンジン
  - ExecutionEngine を起動する run_execution.py
  - paper_trading モードでは MockBrokerClient を使用し、paper_trading用DBに完全分離して記録
- 監視
  - SystemMonitor / TradeMonitor / RiskMonitor を組み合わせたポーリング監視（run_monitoring.py）
  - Kill Switch（data/kill.flag）による ExecutionEngine 停止シグナル
  - 監視ログは SQLite（デフォルト data/monitoring.db）に永続化
- ポートフォリオ構築
  - 候補選定、等金額／スコア重み、リスク調整（セクター上限、レジーム乗数）、ポジションサイズ計算
- 研究用モジュール
  - ファクター計算（Momentum、Volatility、Value など）、将来リターン計算、IC 計算
  - DuckDB を用いた高速な時系列集計
- AI（OpenAI）統合
  - ニュースのセンチメント評価（news_nlp）
  - マクロセンチメント＋価格指標による市場レジーム判定（regime_detector）
  - OpenAI の API キーが必要（AI 機能はオプション）
- ユーティリティ
  - ロギング設定ユーティリティ（コンソール + 日次ローテートファイル）
  - プロセス優先度 / CPU アフィニティ設定ユーティリティ
- ツール
  - ペーパートレード検証レポート生成スクリプト（tools/paper_verification_report.py）

前提・推奨環境
- Python 3.10+
- 必要パッケージ（代表例）:
  - duckdb
  - psutil
  - openai（AI 機能を使う場合）
  - PyYAML（config ファイル検証を行う場合）
- デフォルトで使用するファイル:
  - DuckDB: data/kabusys.duckdb
  - SQLite (監視): data/monitoring.db
  - Paper Trading SQLite: data/paper_trading.db（paper_trading モード）

セットアップ手順
1. リポジトリをクローン / ソースを入手
2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存関係をインストール
   - pip install duckdb psutil
   - AI 機能を使う場合: pip install openai
   - 設定検証で YAML を使う場合: pip install PyYAML
   - （プロジェクト用 requirements.txt があればそれを利用）
4. .env を作成
   - 対話式ウィザードを使う（推奨）
     - python -m kabusys.config_setup
   - もしくは手動で .env を作成し、必須環境変数を設定:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - そのほか（任意/デフォルトあり）: KABUSYS_ENV, DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL, KABU_API_BASE_URL, LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID など
5. 設定の検証（任意）
   - python -m kabusys.validate_config
   - 警告も失敗扱いにする: python -m kabusys.validate_config --strict
6. データディレクトリを作成（必要なら）
   - mkdir -p data logs

主要な環境変数（抜粋）
- 必須
  - JQUANTS_REFRESH_TOKEN: J-Quants API 用リフレッシュトークン
  - KABU_API_PASSWORD: kabuステーション API パスワード
- 運用関連
  - KABUSYS_ENV: execution モード選択（development / paper_trading / live）
  - LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
  - LOG_DIR: ログディレクトリ（デフォルト logs/）
- DB パス
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト data/paper_trading.db）
- Paper Trading の挙動
  - PAPER_FILL_MODE: instant / partial / never / reject（デフォルト instant）
- 監視 / プロセス制御
  - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START
  - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring で上書き可能、デフォルト 60）
- OpenAI
  - OPENAI_API_KEY: OpenAI 呼び出しに必要（AI 機能使用時）

使い方（主なコマンド）
- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
- 監視ループ（SystemMonitor のポーリング）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL で秒間隔を変更可能（例: MONITOR_POLL_INTERVAL=30）
  - 監視は常に本番用の sqlite_path を参照（環境に関わらず）
  - 停止フラグ: data/stop_requested.flag（存在するとループが終了）
- 実行エンジン (ExecutionEngine)
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBroker を使用し paper_trading 用 DB に記録（本番 DB と分離）
  - 起動時に data/stop_requested.flag があると起動しない
  - 実行中に同フラグが作成されるとエンジンは安全に停止する
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション: --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
- AI 機能（例）
  - kabusys.ai.score_news を呼んでニューススコアを生成（OpenAI API キー必須）
  - kabusys.ai.regime_detector.score_regime で市場レジームを判定して DB 書き込み
- ライブラリ的利用（研究／戦略）
  - ファクター計算: from kabusys.research import calc_momentum, calc_volatility, calc_value
  - ポートフォリオ: from kabusys.portfolio import select_candidates, calc_equal_weights, calc_position_sizes
  - ユーティリティ: from kabusys.utils.logging_setup import setup_logging

運用上の注意
- 本番環境（KABUSYS_ENV=live）では kill flag（KILL_FLAG_CLEAR_ON_START）や LINE 通知設定を慎重に扱ってください。
- Run スクリプトはプロセス優先度を "high" に設定します（プラットフォーム依存で失敗する場合は警告のみ）。
- AI 機能は OpenAI API を呼び出すため、料金・レート制限に注意してください。リトライ・バックオフの仕組みはありますが不確実性は残ります。
- ログは logs/<app_name>.log に日次ローテーションで保存されます。ログディレクトリ作成に失敗した場合はコンソールのみ出力にフォールバックします。
- 停止制御はフラグファイル（data/stop_requested.flag, data/kill.flag）を利用する設計です。外部運用ツールと連携する場合はその仕様に従ってください。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / .env 読み込みロジック、Settings クラス
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - utils/
    - logging_setup.py       — 一貫したロギング設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py       — 監視用 SQLite 永続化層（テーブル初期化・CRUD）
    - system_monitor.py      — システム状態・データ鮮度監視
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - trade_monitor.py       — (注文監視ロジック) — 注: ここに関連実装あり
    - monitoring_engine.py   — 各 Monitor 統合ポーリング
    - kill_switch.py         — フラグ書き込みによる停止シグナル管理
    - alert_manager.py       — (通知処理: LINE 等) — 実装あり
  - execution/
    - execution_engine.py    — ExecutionEngine（セッション実行ロジック）
    - broker_factory.py      — ブローカクライアントの生成（Mock / live 切り替え）
    - order_manager.py, order_repository.py, reconciler.py, risk_manager.py — 発注・管理関連
  - research/
    - factor_research.py     — Momentum / Volatility / Value 計算
    - feature_exploration.py — IC・将来リターン・統計
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - ai/
    - news_nlp.py            — ニュースの LLM センチメント集計・DB 書き込み
    - regime_detector.py     — マクロ + MA200 によるレジーム判定
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - data/                    — 実行時に使用するファイル類（.pid, .flag, DB ファイル等、通常 Git 管理外）
  - config/                  — YAML 設定テンプレート等（system_config.yaml など）

補遺（運用ヒント）
- .env は絶対にリポジトリへコミットしないでください（秘密情報含む）。
- 初回起動時に監視 DB / DuckDB のスキーマは自動作成 / マイグレーションされます（init_monitoring_db）。
- paper_trading モードは実運用との分離が前提です。運用時は KABUSYS_ENV を正しく設定してください。
- ローカル開発では KABUSYS_ENV=development にして外部 API を呼ばない実装パスを利用してください。

ライセンス・貢献
- （リポジトリに LICENSE があれば追記してください）

問題報告・貢献方法
- バグ報告や機能追加の提案は Issue を立ててください。プルリク歓迎です。

以上。必要であれば README にサンプル .env のテンプレート、よくあるトラブルシュート（OpenAI レート制限、psutil の権限エラー、DuckDB 接続エラー等）を追記します。どの情報を補足しますか？