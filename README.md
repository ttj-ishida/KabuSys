README
======

概要
----
KabuSys は日本株向けの自動売買／研究フレームワークです。本リポジトリは以下の機能を備えた Python パッケージ構成になっています。

- 発注実行（ExecutionEngine）と監視（Monitoring）プロセス
- ペーパートレード用の隔離された DB サポート
- ポートフォリオ構築（候補抽出、重み付け、株数決定）
- ファクター計算・リサーチユーティリティ（DuckDB を利用）
- ニュースの LLM（OpenAI）を用いた NLP スコアリングとレジーム判定
- 監視ログ（SQLite）とアラート／Kill Switch 機能
- .env 対話式ウィザードおよび設定検証ツール

主な機能
--------
- execution/run: ExecutionEngine による発注フロー（本番 / ペーパーを区別）
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、data/paper_trading.db に記録
- monitoring/run: SystemMonitor / TradeMonitor / RiskMonitor をポーリングして監視・アラート・Kill Switch 評価
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト: 60 秒）
- portfolio: 候補選定、重み計算、ポジションサイズ計算、セクター上限・レジーム補正
- research: DuckDB 上でのファクター計算（Momentum / Volatility / Value 等）と探索ツール（IC / 統計等）
- ai: ニュースのセンチメントスコアリング（OpenAI）と市場レジーム判定
- tools: Paper Trading の検証レポート生成ツール（paper_verification_report）
- utils: ログ設定、プロセス優先度設定など運用ユーティリティ
- 設定管理: .env ウィザード（config_setup）と起動前チェック（validate_config）

システム要件（推奨）
-------------------
- Python 3.9+
- duckdb
- psutil
- openai （AI 機能を利用する場合）
- PyYAML（config/*.yaml の静的検証を行う場合 / 任意）

依存パッケージはプロジェクト内 requirements.txt があればそれを使用してください。無い場合は少なくとも上記をインストールしてください。

セットアップ手順
----------------

1. リポジトリをクローン
   - git clone <repo_url>
   - cd <repo_root>

2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install -U pip
   - pip install duckdb psutil openai
   - （ローカルで YAML 検証を使うなら）pip install pyyaml

   ※ プロジェクトに requirements.txt / pyproject.toml がある場合はそちらを使ってください:
   - pip install -r requirements.txt

4. 初期設定（.env）
   - 対話式ウィザードで .env を作成・更新:
     - python -m kabusys.config_setup
   - ウィザードでは J-Quants トークンや kabuステーション API パスワード、DB パス、ログレベル等を設定できます。

5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - --strict を付けると警告も FAIL 扱いになります:
     - python -m kabusys.validate_config --strict

使い方
------

起動スクリプト
- 監視ループを起動:
  - python -m kabusys.run_monitoring
  - デフォルトで MONITOR_POLL_INTERVAL=60 秒。変更する場合は環境変数で設定:
    - export MONITOR_POLL_INTERVAL=30

  動作のポイント:
  - run_monitoring は常に「本番 sqlite_path（Settings.sqlite_path）」を使用して監視 DB を操作します（環境に関わらず）。
  - 停止は data/stop_requested.flag ファイルの作成で検知して終了します。

- 実行エンジンを起動:
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い data/paper_trading.db に記録して本番 DB と分離します。
  - 実行中は PID を data/execution.pid に書きます。停止は data/stop_requested.flag の作成で検知します。

Kill Switch / 停止フラグ
- data/kill.flag:
  - KillSwitch によって作成されるフラグ。RiskMonitor 等がしきい値を超えた場合に書き込まれ、ExecutionEngine に停止シグナルを送ります。
  - 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定していると自動でクリアされる設定がありますが、本番では 0 推奨です。

- data/stop_requested.flag:
  - 管理者が作成することで run_monitoring / run_execution のポーリングループを安全に終了させます。

ログ
- ログは logs/<app_name>.log に日次ローテートで保存されます（TimedRotatingFileHandler）。app_name は起動スクリプトの setup_logging 呼出しで "execution" や "monitoring" になります。
- コンソール出力は stdout に出ます。

ツール
- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11 --db path/to/paper_trading.db
  - --db を指定しない場合、環境変数 PAPER_TRADING_SQLITE_PATH またはデフォルト data/paper_trading.db を使用します。

プログラム的な利用例（AI / Research 等）
- AI ニューススコアリング:
  - from kabusys.ai.news_nlp import score_news
  - score_news(duckdb_conn, target_date, api_key="...")

- レジーム判定:
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(duckdb_conn, target_date, api_key="...")

- ファクター計算:
  - from kabusys.research import calc_momentum, calc_volatility, calc_value
  - results = calc_momentum(duckdb_conn, date(...))

設定（主な環境変数）
- 必須（.env で設定）:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 任意 / 推奨:
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
  - LOG_LEVEL（デフォルト: INFO）
  - OPENAI_API_KEY（AI 機能時）
  - PAPER_FILL_MODE（paper_trading の約定挙動: instant | partial | never | reject）
  - KILL_FLAG_CLEAR_ON_START（"1" で起動時に kill.flag を自動クリア）

ディレクトリ構成（主要ファイル）
--------------------------------
以下は主要なモジュールとファイルの一覧（src/kabusys 配下）。各ファイルに簡単な説明を付記します。

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数 / 設定を読み込む Settings クラス（.env 自動読み込みロジック含む）
  - config_setup.py
    - .env を対話式に作成・更新するウィザード CLI
  - validate_config.py
    - 起動前チェック（必須環境変数・config/*.yaml・DB パス等の検証）CLI
  - run_execution.py
    - ExecutionEngine 起動スクリプト（本番 / ペーパー切替）
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL）
  - tools/
    - paper_verification_report.py
      - ペーパートレード検証レポート生成 CLI
  - utils/
    - logging_setup.py
      - 共通のログ設定ユーティリティ（stdout + 日次ファイルローテート）
    - process_priority.py
      - プロセス優先度 / CPU affinity 設定ユーティリティ
  - monitoring/
    - monitoring_db.py
      - SQLite ベースの監視ログ永続化層（テーブル初期化・操作）
    - system_monitor.py
      - システム状態（CPU/メモリ/ディスク）とデータ鮮度監視
    - trade_monitor.py
      - 発注／約定ログの監視（滞留注文、約定異常等）
    - risk_monitor.py
      - ドローダウン・ポジション上限の監視。Kill Switch と連携
    - kill_switch.py
      - Kill Switch（data/kill.flag）作成ユーティリティ
    - monitoring_engine.py
      - 各モニタを束ねてポーリング・アラート送出
    - alert_manager.py
      - （実装に応じて）LINE 等の通知管理（存在すれば）
  - execution/
    - broker_factory.py, execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py
      - 発注フロー、ブローカ抽象、リスク制御、注文管理等（実行ロジック）
  - portfolio/
    - portfolio_builder.py, position_sizing.py, risk_adjustment.py
      - 候補選定・重み付け・株数決定・セクター/レジーム調整
  - research/
    - factor_research.py, feature_exploration.py
      - DuckDB を用いたファクター計算、IC 計算、統計サマリー等
  - ai/
    - news_nlp.py
      - raw_news を LLM（OpenAI）でスコアリングして ai_scores へ書き込み
    - regime_detector.py
      - ETF MA 乖離とマクロニュースの LLM スコアを合成して市場レジーム判定
  - data/ （運用時に生成・使用するディレクトリ・ファイル）
    - monitoring.db（デフォルト）
    - paper_trading.db（paper_trading 時）
    - kill.flag / stop_requested.flag / execution.pid などのフラグ / PID ファイル

運用上の注意
------------
- 本番環境（KABUSYS_ENV=live）では設定（LINE 通知や KILL_FLAG_CLEAR_ON_START 等）を特に慎重に確認してください。validate_config の警告を必ず確認してください。
- kill.flag / stop_requested.flag はファイルベースの制御なので運用者が誤って削除・上書きしないよう注意してください。
- OpenAI を利用する機能は API 利用料とレイテンシを伴います。API キーの管理と呼び出し頻度に注意してください。
- DuckDB / SQLite のファイルパスは .env で指定できます。paper_trading 用 DB は本番 DB と物理的に分離する設計です。

追加情報 / 開発
----------------
- テストや CI のために KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動 .env ロードを抑止できます（config.py の自動ロードを回避）。
- ローカル開発では KABUSYS_ENV=development を使用すると一部の機構が発注を行わないようになります（実装に依存）。

問い合わせ
---------
実装の詳細や運用に関する質問、改善提案はリポジトリ Issue または担当までお問い合わせください。

以上。