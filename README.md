# KabuSys

日本株自動売買システムのコアライブラリ（可搬なモジュール群）。  
このリポジトリは戦略構築、ポートフォリオ生成、発注実行、監視、研究用ユーティリティ、AI ベースのニュース評価などを含むモジュール群で構成されています。

## 概要
- 目的：日本株の自動売買を構成するコンポーネント群を提供する。  
  主要な関心領域は「信号生成・ポートフォリオ構築」「発注エンジン」「監視・アラート」「研究用ファクター計算」「ニュースNLPによるセンチメント評価」などです。
- 設計方針：DB（DuckDB / SQLite）や外部 API（kabuステーション / J-Quants / OpenAI）へのアクセスは明確に分離し、テスト可能な純粋関数や永続化層を用いて安全性を保つように設計されています。

## 主な機能一覧
- 発注実行
  - ExecutionEngine 起動スクリプト（run_execution）: 実運用 / ペーパートレード切替対応
  - ブローカークライアントの抽象化（BrokerClientFactory）
  - 注文管理（OrderManager、OrderRepository）、リコンシリエーション（Reconciler）、リスク管理（RiskManager）

- 監視・運用
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - SQLite ベースの監視 DB（monitoring_db）と永続化 API
  - Kill Switch（フラグファイルで ExecutionEngine を停止）
  - run_monitoring スクリプト：定期ポーリングで各監視を実行

- ポートフォリオ構築（pure functions）
  - 候補選定、等金額/スコア加重配分
  - セクターキャップ適用、レジーム乗数
  - ポジションサイジング（単元丸め・資金制約のスケール調整）

- 研究・リサーチ
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン、IC（Information Coefficient）、統計サマリー等のユーティリティ

- AI（ニュース評価 / レジーム判定）
  - OpenAI API を用いたニュースセンチメント（news_nlp）
  - マクロニュース＋ETF MA による市場レジーム判定（regime_detector）
  - API コールのリトライやレスポンス検証などフェイルセーフな実装

- 運用ツール
  - 対話式 .env 作成ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - ペーパートレード検証レポート生成ツール（tools/paper_verification_report）

## 動作前提（推奨）
- Python 3.10 以上（PEP 604 の union 型などを使用）
- 必要な Python パッケージ（例）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config の YAML 検証を行う場合）
- 標準ライブラリの sqlite3 は使用

（requirements.txt がある場合はそれに従ってください。なければ上記パッケージを pip でインストールしてください）
例:
pip install duckdb psutil openai PyYAML

## セットアップ手順
1. リポジトリをクローン / checkout
2. Python 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate (Unix) / .venv\Scripts\activate (Windows)
3. 必要依存をインストール
   - pip install duckdb psutil openai PyYAML
   - （プロジェクトに requirements.txt があれば）pip install -r requirements.txt
4. .env を作成
   - 対話型ウィザードを利用:
     - python -m kabusys.config_setup
   - あるいは手動で `.env` を作成（.env.example を参照）
   - 重要な環境変数（必須）:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
   - 推奨設定:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - OPENAI_API_KEY: OpenAI を使う機能を利用する場合に必須
5. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - 警告を厳格に扱いたい場合: python -m kabusys.validate_config --strict
6. 初期データディレクトリの準備
   - デフォルトでは data/ に DB 等を置きます。必要に応じてディレクトリを作成してください。
   - Logs は logs/ に出力されます（setup_logging により日次ローテート）

## 主要な環境変数（概要とデフォルト）
- KABUSYS_ENV: 実行環境 ("development" / "paper_trading" / "live") — デフォルト "development"
- LOG_LEVEL: ログレベル ("INFO" など) — デフォルト "INFO"
- DUCKDB_PATH: DuckDB ファイルパス — デフォルト data/kabusys.duckdb
- SQLITE_PATH: 監視用 SQLite DB パス — デフォルト data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（KABUSYS_ENV=paper_trading の場合使用） — デフォルト data/paper_trading.db
- OPENAI_API_KEY: OpenAI API を使用する場合に設定
- PAPER_FILL_MODE: ペーパートレードの約定挙動（instant|partial|never|reject） — デフォルト "instant"
- KILL_FLAG_CLEAR_ON_START: 実行開始時に kill.flag を自動クリアするか（0/1、本番では 0 推奨）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）

（詳細は kabusys.config.Settings のプロパティや config_setup.py の項目を参照してください）

## 使い方（代表的なコマンド）
- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
- 監視ループ起動（Monitoring）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring  # ポーリング間隔を上書き
  - 監視は monitoring DB（Settings.sqlite_path）にログを書き込みます（注: Monitoring は環境にかかわらず本番 sqlite_path を使用）
- 発注エンジン起動（Execution）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution  # ペーパートレード（paper db に書き込む）
  - 起動時に data/stop_requested.flag が存在すると起動しません
- ペーパートレード検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定: --db PATH（または環境変数 PAPER_TRADING_SQLITE_PATH）
- AI ニューススコア（ライブラリ関数）
  - kabusys.ai.score_news(conn, target_date, api_key=...)
  - OpenAI API キーが必要

## 運用上の注意・挙動
- run_execution は KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db に書き込みます（本番 DB と分離）。
- run_monitoring と monitoring コンポーネントは監視結果を監視用 sqlite（Settings.sqlite_path）に書き込みます。Monitoring は KABUSYS_ENV に依らず本番 sqlite_path を参照する点に注意してください。
- Kill Switch:
  - kabusys.monitoring.kill_switch はデータベースの評価結果（ドローダウンやポジション上限）に応じて data/kill.flag を書き込み、ExecutionEngine に停止信号を送ります。
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動クリアしますが、本番では非常に危険な設定です（推奨は 0）。
- プロセス優先度:
  - 起動スクリプトは set_process_priority("high") を呼び出し、可能な限り高優先度に設定しようとします（権限不足等により無視される場合あり）。
- ログ:
  - 共通の setup_logging が利用され、logs/<app_name>.log に日次ローテーションで出力されます。ログディレクトリが作れない場合はコンソール出力のみになります。

## 代表的なモジュール（ディレクトリ構成）
（src/kabusys 以下の主要ファイル／ディレクトリを抜粋）

- run_monitoring.py — SystemMonitor のポーリング起動スクリプト
- run_execution.py — ExecutionEngine の起動スクリプト
- config.py — 環境変数 / .env 自動読み込み & Settings
- config_setup.py — .env 対話式作成ウィザード
- validate_config.py — 起動前の設定検証 CLI
- __init__.py — パッケージ定義（__version__ 等）

ディレクトリ別主要ファイル:
- kabusys/ai/
  - news_nlp.py — ニュース NLP（OpenAI）ベースのスコア化
  - regime_detector.py — 市場レジーム判定（MA + マクロセンチメント）
- kabusys/monitoring/
  - monitoring_db.py — 監視 DB の作成／永続化 API
  - system_monitor.py / trade_monitor.py / risk_monitor.py — 各種監視
  - monitoring_engine.py — モニター束ね用のエンジン
  - kill_switch.py / alert_manager.py（アラート系）
- kabusys/execution/
  - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py
- kabusys/portfolio/
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py
- kabusys/research/
  - factor_research.py, feature_exploration.py
- kabusys/tools/
  - paper_verification_report.py
- kabusys/utils/
  - logging_setup.py — 統一ログ設定
  - process_priority.py — 優先度 / CPU affinity ユーティリティ

簡易ツリー（抜粋）
- src/
  - kabusys/
    - __init__.py
    - config.py
    - config_setup.py
    - validate_config.py
    - run_execution.py
    - run_monitoring.py
    - ai/
    - monitoring/
    - execution/
    - portfolio/
    - research/
    - tools/
    - utils/

## 開発・拡張のヒント
- テストやローカル開発では KABUSYS_ENV=development を使用。実際の発注を避けるため paper_trading を使う場合は paper DB と MockBroker を利用する。
- DuckDB は高速な分析クエリ用途に使われています。ファクター計算・研究モジュールは DuckDB 接続を受け取り SQL を発行して結果を返す純粋関数になっているため、ユニットテストがしやすいです。
- OpenAI を使うモジュールは API レート制限やネットワークエラーを考慮したリトライとレスポンス検証を行っています。テスト時は _call_openai_api をモックすることでネットワークをカットできます。
- config/.yaml のテンプレート生成スクリプト等（scripts/generate_config.py）を用意している場合は、config/*.yaml を用意すると validate_config の警告が減ります。

## トラブルシューティング（よくある問題）
- .env が読み込まれない / 環境変数が反映されない
  - config.py はプロジェクトルート（.git または pyproject.toml を基準）を自動探索して .env を読み込みます。プロジェクトルートが特定できないと自動ロードをスキップします。テスト中や CI では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットして自動ロードを抑止できます。
- logs ディレクトリ作成失敗
  - 権限問題等でディレクトリ作成に失敗した場合はコンソールログのみになります。書き込み権限を確認してください。
- OpenAI API エラー
  - OPENAI_API_KEY が未設定だと例外になります。API 呼び出しはリトライを実装していますが、キーや接続状況を確認してください。

---

README はここまでです。必要に応じて「導入手順（OS より詳細）」「環境別運用手順（開発 / ペーパー / 本番）」や「DB スキーマ詳細」「API 契約（kabu/OpenAI）」などを追記できます。どの部分を詳しく載せたいか教えてください。