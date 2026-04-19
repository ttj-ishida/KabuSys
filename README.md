# KabuSys

日本株自動売買システム（KabuSys）のリポジトリ向け README（日本語）。

概要、機能、セットアップ・起動手順、ディレクトリ構成などをまとめています。開発向けメモや運用時の注意点も含みます。

---

プロジェクト概要
- KabuSys は日本株向けの自動売買プラットフォームのコア実装群です。
- 主な役割:
  - ExecutionEngine：発注・オーダー管理・リスク管理を行う実行エンジン（本番 / ペーパートレード対応）
  - Monitoring：システム状態・注文状態・リスクを監視し、必要時に Kill Switch を発動
  - Research / Portfolio：ファクター計算、特徴量解析、ポートフォリオ構築（候補選定・配分・サイズ決定）
  - AI モジュール：ニュースのセンチメント評価や市場レジーム判定（OpenAI を利用）
  - ユーティリティ：ログ設定、プロセス優先度設定、設定ウィザードなど

主な機能一覧
- Execution
  - KABUSYS_ENV により動作モードを切替（development / paper_trading / live）
  - paper_trading モードでは MockBrokerClient を用い、ペーパートレード用 DB（data/paper_trading.db）に記録
  - リスクマネージャ、オーダーリポジトリ、リコンシリエーションなどのコンポーネントを提供
- Monitoring
  - システム（CPU/メモリ/ディスク）・データ鮮度監視
  - 注文テーブルの滞留・約定異常の検出
  - ドローダウン・ポジション上限の監視と kill.flag 発行（Kill Switch）
  - ポーリングループ（デフォルト 60 秒、環境変数で変更可）
- Research / Portfolio
  - モメンタム・ボラティリティ・バリュー等のファクター計算（DuckDB を使用）
  - forward returns / IC（Information Coefficient）算出、基本統計量
  - 候補選定、等金額／スコア重み、ポジションサイズ計算、セクター制限、レジーム乗数
- AI
  - ニュース文章を LLM（OpenAI）で評価し銘柄ごとにスコアリング（ai_scores テーブルへ保存）
  - マクロニュースと ETF の MA200 を使った市場レジーム判定（market_regime へ保存）
  - API 呼び出しはリトライ・バックオフ・バリデーションあり
- ツール
  - 環境設定ウィザード（.env 作成/更新補助）
  - 設定検証 CLI（.env と config/*.yaml のチェック）
  - Paper Trading 用検証レポート生成スクリプト

セットアップ手順（開発 / 運用共通）
1. 必要条件
   - Python 3.10 以上（PEP604 の型記法 (A|B) を使用しているため）
   - SQLite（標準ライブラリで可）、DuckDB（Python パッケージ）、psutil、openai（AI 機能を使う場合）、PyYAML（設定検証で任意）
2. 依存パッケージのインストール（例）
   - リポジトリに requirements.txt がある想定で:
     - pip install -r requirements.txt
   - 主要パッケージ（手動例）:
     - pip install duckdb psutil openai PyYAML
3. ディレクトリ作成
   - data/ および logs/ を作成しておく（実行時に自動作成される場合もありますが、権限で失敗することがあるため事前作成を推奨）
     - mkdir -p data logs
4. 環境変数設定
   - 対話式ウィザードで .env を作る:
     - python -m kabusys.config_setup
   - もしくは .env を手動作成
   - 必須環境変数（最低限設定が必要）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 主要な環境変数（デフォルトを持つもの含む）
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH — デフォルト: data/paper_trading.db
     - LOG_LEVEL — デフォルト: INFO
     - OPENAI_API_KEY — AI 機能を使う場合必須
     - PAPER_FILL_MODE — paper_trading 時のフィルモード (instant|partial|never|reject)。デフォルト: instant
     - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか (0/1)。本番では 0 推奨
     - MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒）。run_monitoring で使用（デフォルト 60）
5. 設定検証（推奨）
   - python -m kabusys.validate_config
   - 警告も fail としたい場合:
     - python -m kabusys.validate_config --strict

基本的な使い方（実行コマンド）
- 実行エンジン（ExecutionEngine）を起動
  - python -m kabusys.run_execution
  - 動作モードは KABUSYS_ENV に依存。paper_trading の場合は MockBrokerClient を使用し data/paper_trading.db に記録されます。
  - 実行中は data/execution.pid（デフォルト）等の PID ファイルが生成されます。
  - 強制停止は data/stop_requested.flag を作成することで行えます（run スクリプトは stop_requested.flag を検知して終了します）。
- 監視ループを起動
  - python -m kabusys.run_monitoring
  - デフォルトポーリング間隔は 60 秒。MONITOR_POLL_INTERVAL 環境変数で上書きできます（例: MONITOR_POLL_INTERVAL=30）。
  - 監視は常に本番 sqlite_path を使用して監視テーブルに書き込みます（KABUSYS_ENV にかかわらない）。
  - 監視側も data/stop_requested.flag を監視して終了します。
- 環境ウィザード
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config [--strict]
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH でも指定可）

重要な運用・仕組みメモ
- Kill Switch / stop フロー
  - Monitoring の KillSwitch はリスク超過等の条件を満たすと data/kill.flag を作成し、ExecutionEngine に停止シグナルを送ります（ExecutionEngine は定期的に kill.flag を参照して停止する仕組み）。
  - run_execution / run_monitoring の停止は data/stop_requested.flag によるプロセス間制御（起動スクリプトが存在確認してループを抜ける）。
  - 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定していると kill.flag を自動クリアする動作がありますが、本番では危険なため 0 を推奨します。
- DB
  - 監視用 SQLite: デフォルト data/monitoring.db
  - ペーパートレード用 SQLite: data/paper_trading.db（paper_trading モードで使用）
  - DuckDB: 分析用 data/kabusys.duckdb
- ログ
  - ログ設定ユーティリティは kabusys.utils.logging_setup.setup_logging を提供
  - デフォルトログディレクトリ: logs/
  - ログファイル名は起動時に app_name を渡して決定（例: execution.log, monitoring.log）
- OpenAI / AI 機能
  - OPENAI_API_KEY が必要
  - AI 呼び出しはリトライ・バックオフ実装あり。API 利用が失敗した場合は安全側のフォールバック（スコア 0.0 など）を行うように設計されています
- 設定ファイル
  - config/ 以下に各種 YAML（system_config.yaml, data_config.yaml, strategy_config.yaml, risk_config.yaml, execution_config.yaml, monitoring_config.yaml）を想定しており、validate_config で存在とパース検証を行います（PyYAML 未導入時は検証がスキップされます）。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py — 環境変数の読み込みと Settings ラッパー
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - ai/
    - news_nlp.py — ニュース NLP スコアリングロジック
    - regime_detector.py — 市場レジーム判定
  - monitoring/
    - monitoring_db.py — SQLite 永続化層（テーブル定義・CRUD ユーティリティ）
    - system_monitor.py — システム監視（CPU/メモリ/ディスク・データ鮮度）
    - trade_monitor.py — 注文周りの監視（ファイル内に実装あり）
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
    - kill_switch.py — kill.flag 制御
    - alert_manager.py — アラート送信（LINE 等。コード内参照）
  - portfolio/
    - portfolio_builder.py — 候補選定 / 重み計算
    - position_sizing.py — 株数決定 / 利用可能現金スケーリング等
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — ファクター計算（momentum/volatility/value）
    - feature_exploration.py — 将来リターン / IC / 統計サマリー
  - utils/
    - logging_setup.py — ログ設定ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

監視 DB（monitoring_db.py）に作成される主なテーブル
- system_status: CPU/Mem/Disk、プロセス稼働フラグ、記録時刻
- trade_logs: 発注イベントログ（Created / Sent / Filled 等）、latency_ms カラムあり
- positions: 現在のポジション
- risk_logs: リスクイベント（ドローダウン・ポジション上限等）
- dashboard: 集計（portfolio_value / cash / drawdown_pct / open_order_count / position_count / peak_value）

トラブルシューティング（よくある注意点）
- PyYAML が無い場合は validate_config の YAML 検証がスキップされます（警告表示）。
- DuckDB/psutil/OpenAI ライブラリが未インストールだと関連機能が動作しません（エラー/警告を確認してください）。
- ログディレクトリや data ディレクトリの作成に失敗するとファイル出力ハンドラが設定されずコンソール出力のみになります。権限を確認してください。
- MONITOR_POLL_INTERVAL は整数秒を期待します。1 未満や不正な値を設定するとデフォルト（60 秒）にフォールバックします。

開発者向けメモ
- 多くのモジュールは外部副作用を避ける純粋関数群（research, portfolio 等）と、DB 参照や永続化を行う層（monitoring_db, execution のリポジトリ等）が明確に分離されています。
- LLM 周り（news_nlp, regime_detector）は外部 API 依存のため、ユニットテストでは API 呼び出し関数をモックすることを推奨します（コード中にも patch 用の注記あり）。
- process priority / affinity は utils/process_priority.py で OS を吸収しています。権限不足で設定できない場合は警告扱いでスキップします。

必要に応じて README を拡張して、実際の運用手順（systemd / Supervisor / docker-compose の service 定義例）、CI/CD、テスト実行方法、詳細な設定例（.env.sample）などを追加してください。質問や補足したい箇所があれば教えてください。