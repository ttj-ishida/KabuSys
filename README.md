KabuSys
=======

日本株向けの自動売買システムのコアライブラリ／起動スクリプト群です。  
本リポジトリは発注エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築・リスク管理、リサーチ（ファクター計算）、
およびニュース NLP / レジーム判定（OpenAI を利用する AI モジュール）などの主要コンポーネントを含みます。

主な設計方針
- 本番／ペーパートレードを明確に分離（KABUSYS_ENV により切替）
- DuckDB（分析用）と SQLite（監視・発注ログ用）を併用
- 各種モジュールは可能な限り副作用を排し純粋関数で実装（テスト容易性）
- OpenAI 呼び出しはフェイルセーフ設計（リトライ・フォールバック）

機能一覧
- Execution
  - ExecutionEngine（発注セッションの実行）
  - BrokerClientFactory：KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用し paper_trading DB に記録
  - 注文管理 / リスク管理 / リコンサイル（モジュール化）
- Monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - kill.flag による外部停止（KillSwitch）
  - monitoring 用の SQLite スキーマ初期化・マイグレーション（monitoring_db）
- Portfolio
  - 候補選定、重み計算、ポジションサイズ計算、セクター上限、レジーム乗数 などの純粋関数群
- Research
  - ファクター計算（モメンタム・バリュー・ボラティリティ等）
  - 将来リターン計算、IC 計算、統計サマリー
- AI（OpenAI 経由）
  - ニュース NLP による銘柄別センチメントスコア生成（ai.news_nlp.score_news）
  - マクロニュース＋MA乖離の合成による市場レジーム判定（ai.regime_detector.score_regime）
- ツール
  - 環境設定ウィザード（python -m kabusys.config_setup）
  - 設定検証 CLI（python -m kabusys.validate_config）
  - Paper Trading 検証レポート生成スクリプト（python -m kabusys.tools.paper_verification_report）
- ユーティリティ
  - 統一的ログ設定（kabusys.utils.logging_setup）
  - プロセス優先度 / CPU affinity 設定（kabusys.utils.process_priority）
  - 環境変数自動ロード / Settings ラッパー（kabusys.config）

前提条件 / 推奨環境
- Python 3.10 以上（typing の | アノテーション等を使用）
- SQLite（標準ライブラリ）
- 推奨パッケージ（最低限）
  - duckdb
  - psutil
  - openai（AI 機能を使う場合）
  - PyYAML（validate_config で config/*.yaml の検証をしたい場合、任意）
- OS: Linux / macOS / Windows（process priority 設定は OS に依存する挙動あり）

セットアップ手順（ローカル開発向け）
1. 仮想環境作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - pip install duckdb psutil openai
   - （任意）pip install PyYAML

   ※ requirements.txt は含まれていないため、必要なパッケージを上記から導入してください。

3. ディレクトリ作成（logs / data）
   - mkdir -p logs data

4. .env の作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
   - もしくは手動で .env を作成（.env.example を参考に）

5. 設定検証
   - python -m kabusys.validate_config
   - 本番用に厳格チェックをしたい場合: python -m kabusys.validate_config --strict

重要な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV（development | paper_trading | live、デフォルト: development）
  - paper_trading: MockBroker を使用し data/paper_trading.db に記録（本番 DB と完全分離）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（ペーパー用 SQLite、デフォルト: data/paper_trading.db）
- OPENAI_API_KEY（AI 機能を使用する場合）
- LOG_LEVEL（デフォルト: INFO）
- KILL_FLAG_CLEAR_ON_START（起動時 kill.flag を自動クリアするか、開発用オプション）

運用上のポイント
- ログ: kabusys.utils.logging_setup により logs/<app_name>.log に日次ローテーションで出力（デフォルト logs/）
- Kill / Stop:
  - Monitoring / Execution の停止はプロジェクトルート data/stop_requested.flag を作成することでループを終了できます（run_* スクリプトが確認）。
  - KillSwitch（監視側）が条件を満たすと data/kill.flag を書き込み、ExecutionEngine に停止を要求します。
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動クリアします（開発時のみ推奨）。
- モニタリングのポーリング間隔:
  - 環境変数 MONITOR_POLL_INTERVAL で秒数を上書き（デフォルト 60 秒）。1秒以上の整数が必要。

使い方（主なコマンド）
- 環境設定ウィザード
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
- ExecutionEngine を起動
  - python -m kabusys.run_execution
  - 注意: KABUSYS_ENV=paper_trading の場合は paper_trading DB が使用され MockBroker が選択されます
- Monitoring を起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL でポーリング間隔を調整
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
- プログラムから利用する関数（一例）
  - kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - kabusys.portfolio.select_candidates(...) / calc_position_sizes(...) など

データベースの取り扱い
- DuckDB: 分析用（prices_daily, raw_financials 等） — デフォルト data/kabusys.duckdb
- SQLite: 監視ログ（monitoring.db） — デフォルト data/monitoring.db
- Paper trading 用 SQLite は data/paper_trading.db（KABUSYS_ENV=paper_trading 時に使用）
- monitoring_db.init_monitoring_db は起動時にテーブルを冪等で初期化・簡易マイグレーションを行います（例: カラム追加）

主要ファイル / ディレクトリ構成（抜粋）
- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数の自動ロード、Settings クラス（.env 読込ロジック含む）
  - config_setup.py
    - .env 作成の対話式ウィザード
  - validate_config.py
    - 起動前の設定検証 CLI
  - run_execution.py
    - ExecutionEngine 起動スクリプト
  - run_monitoring.py
    - Monitoring のポーリングループ起動スクリプト
  - execution/
    - ExecutionEngine や OrderManager, BrokerFactory 等（発注処理）
  - monitoring/
    - monitoring_db.py (SQLite スキーマ + MonitoringDB ラッパ)
    - system_monitor.py, trade_monitor.py, risk_monitor.py, kill_switch.py
    - monitoring_engine.py, alert_manager.py
  - portfolio/
    - portfolio_builder.py, position_sizing.py, risk_adjustment.py
  - research/
    - factor_research.py, feature_exploration.py
  - ai/
    - news_nlp.py（ニュース NLP スコアリング）
    - regime_detector.py（市場レジーム判定）
  - utils/
    - logging_setup.py（ログ設定）
    - process_priority.py（優先度設定）
  - tools/
    - paper_verification_report.py（ペーパートレード検証レポート）

実行・運用時の注意
- KABUSYS_ENV=live の場合は本番口座での発注が行われます。環境変数や kill フラグの状態、LINE 通知設定等を必ず確認してください（validate_config に警告機能あり）。
- OpenAI を使用する機能は API 利用上のレートリミット・料金が発生します。API キーの漏洩管理、レート制御の適切な設定をしてください。
- プロセス優先度や CPU affinity の設定は OS の権限に左右されます（psutil を使用）。実行権限がない場合は警告を出してスキップします。
- データの永続化・DB スキーマ変更は簡易マイグレーションを行いますが、本格的なマイグレーションをする場合はバックアップを取得してください。

開発・拡張のヒント
- research / portfolio モジュールは副作用を持たない純粋な関数群として設計されているため、ユニットテストが書きやすく、モデルの検証に適しています。
- AI モジュールは外部 API 呼び出しを抽象化しており、テスト時は _call_openai_api を patch してモックする想定です。
- monitoring_db や MonitoringEngine は監視ロジックと DB 書き込みを分離しており、アラート先（AlertManager）を差し替えれば通知機能の拡張が容易です。

ライセンス・貢献
- 本リポジトリのライセンスやコントリビュートルールはプロジェクトに応じて明記してください（README に追記を推奨）。

問題が発生したら
- まず python -m kabusys.validate_config で設定を確認してください。
- ログ（logs/）を確認し、発生箇所のスタックトレースや警告メッセージを参照してください。
- AI 関連でレスポンスの不正や JSON 解析エラーが出る場合は OpenAI のレスポンス内容をログに出力して検査してください。

以上がこのコードベースの概要と使い方の要約です。必要であれば、特定モジュール（例: ExecutionEngine の構成、Broker 実装、monitoring のアラート設定方法など）について詳細な README や運用手順を追記します。どの部分のドキュメントが欲しいか教えてください。