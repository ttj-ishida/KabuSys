README
=====

プロジェクト概要
-----
KabuSys は日本株向けの自動売買システムのコアライブラリ群です。  
主な目的は次のとおりです。

- 戦略（ファクター計算・特徴量解析）とポートフォリオ構築ロジック（銘柄選定、配分、株数決定）の実装
- 実際の発注/モック発注を行う ExecutionEngine（本番 / ペーパートレード対応）
- システム監視・リスク監視（監視ログの永続化、Kill Switch）
- ニュースの NLP によるセンチメント評価や市場レジーム判定（OpenAI を利用）
- Paper Trading 向けの検証レポート生成ツール

主要設計方針として、DB（DuckDB / SQLite）や外部 API 呼び出しを明示的に分離し、テスト可能でフェイルセーフな実装を心がけています。

主な機能一覧
-----
- 環境設定管理
  - .env の自動ロード（プロジェクトルート検出）および対話式ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
- Execution
  - 実口座 / ペーパートレード切替（KABUSYS_ENV=paper_trading）
  - 発注管理、リスク管理、オーダーの再整合（Reconciler, RiskManager, OrderManager）
- Monitoring
  - システム状態（CPU/Mem/Disk、プロセス死活、データ鮮度）監視
  - トレード監視（滞留注文、約定異常など）
  - リスク監視（ドローダウン・ポジション上限判定）
  - Kill Switch（条件を満たすと data/kill.flag を書き込み ExecutionEngine を停止）
  - 監視ログを SQLite に永続化（schema の自動初期化・マイグレーション含む）
- Portfolio（純粋関数群）
  - 候補選定、等重・スコア重みの計算
  - ポジションサイズ計算（risk_based, equal, score）
  - セクター上限適用、レジーム乗数
- Research
  - DuckDB を使ったファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算、IC（Information Coefficient）、ファクター統計
- AI
  - ニュース記事を LLM（OpenAI）でスコアリングして ai_scores テーブルへ書き込み
  - マクロニュース＋ETF MA200 乖離から市場レジーム判定（score_regime）
  - API のレート制御・リトライ・レスポンス検証の実装
- ツール
  - Paper Trading 検証レポート生成（tools.paper_verification_report）

セットアップ手順
-----
前提（代表的な依存）
- Python 3.10+
- 必要パッケージ（例）
  - duckdb, psutil, openai, (PyYAML は設定検証時にオプション)
  - 例: pip install -r requirements.txt もしくは個別に pip install duckdb psutil openai pyyaml

1) リポジトリをクローンして作業ディレクトリに移動
2) .env を作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - 手動編集:
     - .env.example を参照して .env を作成
   - 主要な環境変数（抜粋）
     - JQUANTS_REFRESH_TOKEN （必須）
     - KABU_API_PASSWORD （必須）
     - KABUSYS_ENV （development / paper_trading / live、デフォルト: development）
     - DUCKDB_PATH （デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH （監視 DB、デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH （paper_trading 用 DB、デフォルト: data/paper_trading.db）
     - OPENAI_API_KEY （AI 機能を使う場合必須）
     - PAPER_FILL_MODE （paper_trading の約定モード: instant | partial | never | reject、デフォルト: instant）
     - LOG_LEVEL, LOG_DIR, LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID 等
3) 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 警告もエラー扱いにする: python -m kabusys.validate_config --strict
4) DB の初期化
   - 各起動スクリプトが必要に応じて監視 DB の初期化（init_monitoring_db）を実行します。通常は明示的な操作不要。
5) ログディレクトリ作成
   - デフォルトで logs/ を生成します。設定で LOG_DIR を変更できます。

使い方（主要 CLI / 実行）
-----
- 環境設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告で EXIT 1

- ExecutionEngine を起動（本番 / ペーパートレード）
  - python -m kabusys.run_execution
  - 挙動
    - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（例: data/paper_trading.db）にデータを記録
    - 起動時に data/stop_requested.flag が存在する場合は起動を中止
    - 実行中に data/stop_requested.flag を書くことでエンジン停止を要求
    - PID ファイル: data/execution.pid（設定で変更可）
    - プロセス優先度を "high" に設定（set_process_priority を使用）

- Monitoring を起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き（デフォルト: 60）
  - 監視は常に本番用の sqlite_path を使用（KABUSYS_ENV に依存しない）
  - 停止フラグ: 監視ループは data/stop_requested.flag を検知すると終了

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

- AI 機能（プログラム内 API）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - OpenAI の API キーは引数または環境変数 OPENAI_API_KEY で指定
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

- ログ設定
  - 各起動スクリプトは kabusys.utils.logging_setup.setup_logging を呼び出します
  - デフォルト: logs/<app_name>.log（TimedRotatingFileHandler, 日次ローテーション）
  - ログレベルは LOG_LEVEL 環境変数または setup_logging の引数で指定

運用上の注意
-----
- Kill Switch
  - Kill 条件が満たされると data/kill.flag が書き込まれ ExecutionEngine 停止を促します
  - KILL_FLAG_CLEAR_ON_START=1 を本番で使うのは危険（自動クリアされてしまう）
- ペーパートレードは本番 DB と分離（PAPER_TRADING_SQLITE_PATH を利用）
- OpenAI を使う処理は API 失敗時にフォールバックする設計ですが、APIキーの管理に注意してください
- psutil の権限不足によりプロセス優先度/CPU affinity の設定が失敗することがあります（警告ログが出ます）

ディレクトリ構成（主要ファイル）
-----
src/kabusys/
- __init__.py
- config.py
  - Settings クラス: 環境変数読み込み / .env 自動ロード
- config_setup.py
  - 対話式 .env ウィザード
- validate_config.py
  - 起動前チェック CLI
- run_execution.py
  - ExecutionEngine 起動スクリプト
- run_monitoring.py
  - SystemMonitor ポーリングループ起動スクリプト
- utils/
  - logging_setup.py — ログ初期化ユーティリティ
  - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ
- monitoring/
  - monitoring_db.py — SQLite 永続化層（schema 初期化）
  - system_monitor.py — CPU/MEM/DISK、データ鮮度、プロセス監視
  - trade_monitor.py — （トレード監視ロジック）
  - risk_monitor.py — ドローダウン・ポジション監視
  - kill_switch.py — Kill Switch 実装
  - monitoring_engine.py — 各 Monitor を束ねるエンジン
  - alert_manager.py — （アラート送信ロジック）
- execution/
  - execution_engine.py — ExecutionEngine
  - order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py など
- portfolio/
  - portfolio_builder.py — 候補選定・重み計算
  - position_sizing.py — 株数決定・最大投下額・単元丸め
  - risk_adjustment.py — セクター制限・レジーム乗数
- research/
  - factor_research.py — momentum / volatility / value の計算（DuckDB）
  - feature_exploration.py — 将来リターン・IC・統計
- ai/
  - news_nlp.py — ニュース記事の LLM スコアリング
  - regime_detector.py — 市場レジーム判定（MA200 + LLM）
- data/ (想定)
  - monitoring.db（SQLite）
  - paper_trading.db（ペーパートレード用）
  - kill.flag, stop_requested.flag, execution.pid などの運用フラグ/ファイル
- logs/ （デフォルトロギング出力先）

追加情報 / Tips
-----
- .env は絶対に Git にコミットしないでください（README ヘッダもウィザードが生成した）
- 自動ロードの無効化:
  - テスト時などに .env の自動読み込みを抑止するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
- 設定検証で YAML の内容検証を行うには PyYAML が必要（インストールされていない場合は警告としてスキップされます）
- DuckDB を外部ツールで参照すると高速に分析できます（research モジュールは DuckDB 接続を受け取ります）

お問い合わせ / 貢献
-----
- バグ報告・機能提案は Issue を作成してください
- コードの変更は PR を通じて提出してください（ユニットテスト・ドキュメントを添付してください）

以上。README に不足している詳細や特定の機能（ExecutionEngine の内部 API、TradeMonitor の詳細挙動、AlertManager の設定方法など）について追記が必要であれば、その点を指定してください。