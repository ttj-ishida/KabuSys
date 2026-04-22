# KabuSys

日本株向けの自動売買 / 研究フレームワーク（ライブラリ＋起動スクリプト群）。  
シグナル生成 → ポートフォリオ構築 → 発注（実発注 / ペーパートレード）までの実用的なワークフローと、監視・アラート、研究ユーティリティを含みます。

注意: このリポジトリはライブラリ兼アプリケーションの集合です。起動スクリプトはモジュールとして実行できます（例: python -m kabusys.run_execution）。

概要
- 自動売買エンジン（ExecutionEngine）: ブローカークライアント抽象化、オーダー管理、リスク管理、再整合（reconciler）を含む。
- 監視コンポーネント: System / Trade / Risk モニタ、Kill Switch、アラート管理、監視用 SQLite DB。
- ポートフォリオ構築ライブラリ: 候補選定、重み計算、ポジションサイズ計算、セクター制約、レジーム乗数。
- 研究用ユーティリティ: ファクター計算（Momentum/Value/Volatility 等）、特徴量解析（IC 等）。
- AI 統合: OpenAI を使ったニュースセンチメント（news_nlp）、市場レジーム判定（regime_detector）。
- ツール: 環境設定ウィザード、設定検証、ペーパートレード検証レポート。

主な機能
- 起動スクリプト
  - run_execution: ExecutionEngine を起動（KABUSYS_ENV=paper_trading で MockBroker を使用し data/paper_trading.db に記録）
  - run_monitoring: SystemMonitor ポーリングループを起動（MONITOR_POLL_INTERVAL で間隔変更可）
- 監視 / Kill Switch
  - システム資源・プロセス稼働・データ鮮度チェック、ドローダウン・ポジション数監視、条件に応じて data/kill.flag を書き込み停止指示
- データ永続化（MonitoringDB）
  - SQLite を使った監視ログ（system_status / trade_logs / positions / risk_logs / dashboard）
  - 起動時に冪等的にテーブル作成と簡易マイグレーションを実行
- ポートフォリオ構築（純粋関数群）
  - 候補選定、等重・スコア加重、リスクベースの単位数量算出（単元株丸め、aggregate キャップ）
  - セクターキャップとレジーム乗数の適用
- 研究ツール（DuckDB 想定）
  - ファクター計算（momentum / volatility / value）、forward returns、IC、統計サマリ
- AI 関連
  - news_nlp.score_news: ニュース記事を集約して OpenAI に投げ、銘柄ごとのスコアを ai_scores テーブルに保存
  - regime_detector.score_regime: ETF の MA200 とマクロニュースの LLM 評価を合成して market_regime に書き込み
- 運用支援ツール
  - config_setup: .env を対話的に作成 / 更新
  - validate_config: .env と config/*.yaml を起動前に検証
  - tools.paper_verification_report: ペーパートレード DB から検証レポートを生成

前提 / 推奨環境
- Python 3.10 以上（PEP 604 union 型表記などを使用）
- 必須ライブラリ（例）:
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - （任意）PyYAML: validate_config で config/*.yaml のパース検証を行う場合
- SQLite（組み込み）およびファイルシステムアクセス

セットアップ手順（ローカル開発向け）
1. リポジトリをクローンし、作業ディレクトリを src を含むルートに移動
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存関係をインストール（例）
   - pip install duckdb psutil openai
   - （開発）pip install PyYAML
4. 環境変数設定
   - 対話式ウィザードで .env を生成:
     - python -m kabusys.config_setup
   - もしくは .env を直接作成（以下は主な環境変数）
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - KABUSYS_ENV (development | paper_trading | live) — デフォルトは development
     - DUCKDB_PATH (デフォルト data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (ペーパートレード DB、デフォルト data/paper_trading.db)
     - LOG_LEVEL (DEBUG/INFO/...)
     - OPENAI_API_KEY (news_nlp / regime_detector を使う場合)
5. 設定検証（起動前推奨）
   - python -m kabusys.validate_config
   - 警告も失敗扱いにする場合は --strict

使い方（主な起動コマンド）
- ExecutionEngine（実行エンジン）を起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使い、PAPER_TRADING_SQLITE_PATH に記録される
  - 停止要求は data/stop_requested.flag を作成または Kill Switch が data/kill.flag を書き込むことで行われる
- Monitoring を起動（ポーリング）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き（デフォルト 60）
  - 監視は本番 sqlite_path を使用（KABUSYS_ENV に依存せず）
- 設定ウィザード
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config [--strict]
- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で DB パスを上書き可能（環境変数 PAPER_TRADING_SQLITE_PATH でも指定可）
- AI スコアリング（ライブラリ呼び出し）
  - ニューススコアを生成して書き込む:
    - from kabusys.ai import score_news
    - score_news(duckdb_conn, target_date, api_key="...")  # api_key を省略すると OPENAI_API_KEY 環境変数を参照
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key="...")

重要な挙動・運用メモ
- .env 自動ロード
  - プロジェクトルート（.git または pyproject.toml を基準）を探索して .env / .env.local を自動読み込みします。
  - 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
- Kill / Stop フラグ
  - data/stop_requested.flag: run_monitoring / run_execution はこのファイルの存在を見てループ終了やエンジン停止を行います（手動停止用）。
  - data/kill.flag: KillSwitch（監視）がリスク条件により書き込み、ExecutionEngine に停止を指示します（起動時に KILL_FLAG_CLEAR_ON_START が 1 なら自動クリアされる設定あり。production では 0 推奨）。
- ロギング
  - kabusys.utils.logging_setup.setup_logging を使い、stdout と logs/<app_name>.log（デフォルト）に出力します。ログディレクトリは環境変数 LOG_DIR で上書き可能。
- DB
  - 監視用 DB: デフォルト data/monitoring.db（Settings.sqlite_path）
  - DuckDB: 分析用 data/kabusys.duckdb（Settings.duckdb_path）
  - ペーパートレード時は Monitoring DB と本番 DB を分離するため PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を使用
- プロセス優先度設定
  - 起動スクリプトは set_process_priority("high") を呼び出します（psutil 必要）。権限不足や未対応 OS の場合は警告ログが出てスキップされます。
- マイグレーション
  - monitoring_db.init_monitoring_db は起動時に冪等的にテーブル作成と簡易カラム追加（例: trade_logs.latency_ms、dashboard.peak_value）を行います

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理（.env 自動ロード含む）
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - __init__.py
    - news_nlp.py            — ニュースセンチメント集約 + OpenAI 呼び出し
    - regime_detector.py     — マクロ + MA200 を使ったレジーム判定
  - research/
    - __init__.py
    - factor_research.py     — Momentum/Volatility/Value ファクター計算（DuckDB）
    - feature_exploration.py — forward returns, IC, 統計サマリ
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py       (実装ファイルがある前提)
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py       (実装ファイルがある前提)
  - execution/
    - (Execution 関連コンポーネント: broker_factory, execution_engine, order_manager, order_repository, reconciler, risk_manager)
  - utils/
    - logging_setup.py
    - process_priority.py

（注）上記は主要ファイルを抜粋した一覧です。実際のファイル群はさらに細分化されています。

開発・拡張ポイント（参考）
- BrokerClientFactory により本番/ペーパーを切替可能。新しいブローカーを追加する場合は factory を拡張してください。
- AI モジュールは OpenAI SDK に依存。API 仕様変更に備えてラッパー関数の差し替えが容易な設計になっています（テスト時はモックしやすい）。
- DuckDB を用いたファクター計算は SQL ベースで記述されており、大規模データにも比較的高速に対応できます。
- position_sizing の lot_size は将来銘柄毎に変更可能なように拡張可能（現在は全銘柄共通 100 を想定）。

お問い合わせ / 貢献
- バグや改善提案は Issue を立ててください。プルリクエストは歓迎します。テストやドキュメントを同梱してください。

以上。必要であれば README に「インストール用 requirements.txt の例」や「よくある運用手順 (起動順序・監視フロー)」を追加します。どの情報を優先的に追加しますか？