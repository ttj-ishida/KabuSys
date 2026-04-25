KabuSys — 日本株自動売買システム（簡易 README）
====================================

概要
----
KabuSys は日本株の自動売買・研究・監視を目的とした Python パッケージです。
モジュール群は以下の責務を持ちます（抜粋）:

- execution: 発注エンジン、注文管理、リスク管理、ブローカー抽象化
- monitoring: システム／注文／リスク監視、Kill Switch、アラート連携
- portfolio: 候補選定・重み計算・ポジションサイズ算出・リスク調整
- research: ファクター計算・特徴量探索
- ai: ニュース NLP（OpenAI）を用いたセンチメント処理・レジーム判定
- tools: Paper Trading の検証レポートなどユーティリティ
- utils: ロギング設定、プロセス優先度設定等の共通ユーティリティ
- データ永続化: DuckDB（分析用） / SQLite（監視・発注ログ）

特徴（主な機能）
----------------
- ExecutionEngine（本番 / Paper Trading 切替）:
  - KABUSYS_ENV により paper_trading モードを切替可能。Paper Trading は本番 DB と分離して data/paper_trading.db を使用。
  - ブローカークライアントを抽象化し、Mock 実装をサポート。
- 監視（Monitoring）:
  - SystemMonitor / TradeMonitor / RiskMonitor を組み合わせた MonitoringEngine。
  - KillSwitch によるフラグファイル方式で ExecutionEngine を安全に停止可能（data/kill.flag）。
  - 監視データは SQLite に永続化（data/monitoring.db がデフォルト）。
- ポートフォリオ構築:
  - 候補選定（スコア降順）、等金額・スコア加重配分、リスクベースの株数算出、セクターキャップの適用等を純粋関数で提供。
- 研究（Research）:
  - DuckDB を使ったファクター計算（モメンタム、バリュー、ボラティリティ）、将来リターンや IC 計算、統計サマリー。
- AI（OpenAI）連携:
  - ニュース記事を LLM（gpt-4o-mini 等）で評価し ai_scores に保存。
  - マクロニュース + ETF 差分から市場レジームを判定して market_regime テーブルへ保存。
  - API 呼び出しはリトライ等を含むフェイルセーフ設計。
- 運用ユーティリティ:
  - .env 対話式ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading 検証レポート生成ツール

前提（依存パッケージ）
--------------------
（実プロジェクトの requirements.txt がある前提ですが、主要依存は以下）
- Python 3.8+
- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML（config/*.yaml の検証を行う場合に推奨）

セットアップ手順
----------------
1. リポジトリをクローンし、仮想環境を作成・有効化します。
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストールします（例）。
   - pip install duckdb psutil openai pyyaml

3. .env を用意します（対話式ウィザード推奨）。
   - python -m kabusys.config_setup
     - J-Quants / kabuステーション のトークン類、KABUSYS_ENV（development / paper_trading / live）などを設定します。

4. 設定を検証します。
   - python -m kabusys.validate_config
   - 問題があれば修正し、--strict を付けると警告も FAIL 扱いになります。

5. データディレクトリの初期化（任意）。
   - デフォルトの DB / ログディレクトリは下記の通り:
     - DuckDB: data/kabusys.duckdb   (環境変数 DUCKDB_PATH で上書き可)
     - SQLite (監視): data/monitoring.db (環境変数 SQLITE_PATH)
     - Paper Trading 用 SQLite: data/paper_trading.db (KABUSYS_ENV=paper_trading 時、自動使用, PAPER_TRADING_SQLITE_PATH で上書き可)
     - ログ: logs/（LOG_DIR 環境変数で変更可）

使い方（起動 / 主要 CLI）
------------------------
- ExecutionEngine 起動（通常は systemd / supervisor 等で運用）
  - python -m kabusys.run_execution
  - 動作モードは KABUSYS_ENV 環境変数で制御:
    - development: 発注なし（ローカル開発）
    - paper_trading: MockBroker を使用し data/paper_trading.db に記録（本番 DB と分離）
    - live: 実際に発注する本番モード
  - 実行時、プロセス優先度を high に設定します（utils.process_priority）。
  - 停止方法:
    - 管理者側から ExecutionEngine を停止したい場合は data/kill.flag に理由を書き込み（KillSwitch）、Execution 側が検出して安全停止します。
    - または run_execution が利用している stop フラグ: data/stop_requested.flag を作れば起動スレッドを終了させます（run_execution 側でチェック）。

- Monitoring 起動
  - python -m kabusys.run_monitoring
  - 監視ループはデフォルト 60 秒間隔でポーリングします。環境変数 MONITOR_POLL_INTERVAL で秒数を上書きできます。
  - 監視は常に production の sqlite_path（.env の SQLITE_PATH）を参照して monitoring テーブルを初期化します。

- .env 管理
  - .env を対話式で作成/更新: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH を使うか環境変数 PAPER_TRADING_SQLITE_PATH を設定

- AI（ニューススコア / レジーム）
  - OPENAI_API_KEY を .env または環境変数に設定した上で、プログラムから呼び出します。
  - 例（ニューススコア、プログラム的に呼ぶ）:
    - from kabusys.ai import score_news
      score_news(duckdb_conn, target_date, api_key=None)  # api_key が None の場合は環境変数を使います
  - レジーム判定:
    - kabusys.ai.regime_detector.score_regime(duckdb_conn, target_date, api_key=None)

運用上の注意
------------
- Paper Trading は本番 DB とは分離しているため、間違って本番データを上書きするリスクを軽減しています（settings.is_paper を参照）。
- Kill Switch（data/kill.flag）は本番での強力な停止手段です。KILL_FLAG_CLEAR_ON_START が 1 に設定されていると起動時に自動クリアされますが、本番では 0（クリアしない）を推奨します。
- ログは logs/<app_name>.log に日次ローテーションで保存されます。ログ出力先・レベルは環境変数 LOG_DIR / LOG_LEVEL で変更可能。
- OpenAI 関連処理はネットワークや API の一時的な失敗に備え指数バックオフでリトライする設計になっていますが、API キーの管理には注意してください。

主要環境変数（抜粋）
--------------------
- KABUSYS_ENV: development | paper_trading | live
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト data/paper_trading.db）
- OPENAI_API_KEY: OpenAI API キー（AI 機能で必須）
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR
- LOG_DIR: ログ保存ディレクトリ
- MONITOR_POLL_INTERVAL: 監視ループ間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（"1" で有効）

ディレクトリ構成（主要ファイル）
------------------------------
以下はパッケージルート src/kabusys/ の主な構成（抜粋）:

- __init__.py
- config.py                 — 設定管理（.env ロード・Settings クラス）
- config_setup.py           — .env 対話式ウィザード
- validate_config.py        — 設定検証 CLI
- run_execution.py          — ExecutionEngine 起動スクリプト
- run_monitoring.py         — SystemMonitor ポーリング起動スクリプト

- ai/
  - news_nlp.py             — ニュース NLP（OpenAI）によるスコア付け
  - regime_detector.py      — 市場レジーム判定（MA + マクロセンチメント）
- monitoring/
  - monitoring_db.py        — SQLite 永続化／API
  - system_monitor.py
  - trade_monitor.py        — （trade_monitor モジュールあり）
  - risk_monitor.py
  - kill_switch.py
  - monitoring_engine.py
  - alert_manager.py        — （アラート送信機能）
- execution/
  - execution_engine.py
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - risk_manager.py
  - broker_factory.py
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- data/                     — 実行時に使う DB やフラグファイル（例: data/monitoring.db, data/kill.flag）
- logs/                     — ログ出力先（デフォルト）

補足（開発者向け）
------------------
- DuckDB 接続を受け取る設計のため、ローカルでの分析／テストが容易です（副作用を避ける純粋関数が多く含まれます）。
- モジュールにはフェイルセーフ（例: DB マイグレーション・部分失敗時のロールバック保護・API のリトライ等）が考慮されています。
- テスト時に .env 自動ロードを抑止したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

問題報告 / 貢献
----------------
- バグや改善提案は issue を立ててください。
- 大きな変更を行う場合は設計意図（簡潔な概要）と合わせて PR を送ってください。

以上がこのコードベースの概要と運用の起点となる情報です。必要であれば「デプロイ手順（systemd 例）」「CI 用のテスト手順」「より詳細な設定項目一覧」などを追記できます。どの情報を追加しますか？