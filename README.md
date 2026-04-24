KabuSys — README
=================

概要
----
KabuSys は日本株向けの自動売買システムのコアライブラリ群です。システム監視、発注エンジン（実運用／ペーパートレード分離）、ポートフォリオ構築、リサーチ（ファクター計算・特徴量解析）、AI を用いたニュースセンチメント／レジーム判定などのコンポーネントを提供します。

主な設計方針
- 本番とペーパートレードの DB を分離（KABUSYS_ENV に依存）
- ルックアヘッドバイアスに注意した時刻扱い（date.today()/datetime.today() を参照しない設計を原則）
- 外部 API 呼び出し（OpenAI 等）はフェイルセーフ（API 失敗時のフォールバック）を備える
- ロギング・監視・Kill Switch による安全運転支援

機能一覧
--------
主要な機能・モジュール（抜粋）:

- 実行・監視
  - run_execution.py: ExecutionEngine 起動スクリプト（本番 / ペーパートレード切替）
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプト
  - monitoring_engine.py / SystemMonitor / TradeMonitor / RiskMonitor: 監視ロジックとアラート判定
  - kill_switch.py: フラグファイルによる ExecutionEngine 停止機構

- 設定・ユーティリティ
  - config.py: 環境変数 / .env の読み込み・Settings 抽象化
  - config_setup.py: 対話式 .env 生成ウィザード
  - validate_config.py: 起動前の設定検証 CLI
  - utils.logging_setup: 統一ログ設定（コンソール + 日次ローテーション）
  - utils.process_priority: プロセス優先度 / CPU affinity 操作

- ポートフォリオ構築（純粋関数）
  - portfolio.portfolio_builder: 候補選定、等配分／スコア配分の重み計算
  - portfolio.position_sizing: 株数決定、集約キャップ、単元丸め
  - portfolio.risk_adjustment: セクター上限・レジーム乗数

- リサーチ
  - research.factor_research: Momentum / Volatility / Value 等のファクター計算（DuckDB 使用）
  - research.feature_exploration: 将来リターン計算、IC（スピアマン）等

- AI
  - ai.news_nlp: ニュースの LLM センチメント取得・ai_scores テーブル書込
  - ai.regime_detector: ETF ma200 とマクロニュースの LLM 評価を合成して日次の市場レジーム判定

- ツール
  - tools.paper_verification_report: ペーパートレードの検証レポート生成

セットアップ手順
----------------

前提
- Python 3.9+（コードは型ヒントで 3.10+ 想定だが互換性はある）
- Git リポジトリルート（.git / pyproject.toml があるディレクトリ）がプロジェクトルートとして参照されます

インストール（ローカル開発）
1. 仮想環境を作成・有効化
   - python -m venv .venv
   - (Unix) source .venv/bin/activate
   - (Windows) .venv\Scripts\activate

2. 依存ライブラリをインストール
   - requirements.txt がある場合:
     - pip install -r requirements.txt
   - 最低限必要になるパッケージ（例）:
     - pip install duckdb psutil openai

   ※ PyYAML は config の YAML 検証（validate_config）でオプションです。

3. .env を作成
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - もしくは手動でプロジェクトルートに .env を作成（下記「環境変数」参照）

4. 設定検証（任意）
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱いになります

主要な環境変数（.env 例）
- 必須
  - JQUANTS_REFRESH_TOKEN=your_token_here
  - KABU_API_PASSWORD=your_kabu_password

- 運用関連（デフォルト値は右記）
  - KABUSYS_ENV=development | paper_trading | live  (default: development)
  - DUCKDB_PATH=data/kabusys.duckdb
  - SQLITE_PATH=data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
  - LOG_LEVEL=INFO
  - LOG_DIR=logs
  - OPENAI_API_KEY=（AI 機能を使う場合に必要）
  - PAPER_FILL_MODE=instant | partial | never | reject (paper_trading 時の挙動)

- 監視 / Kill Switch
  - KILL_FLAG_CLEAR_ON_START=0  # 起動時に kill.flag を自動クリアするか（本番では 0 推奨）
  - PID_FILE_PATH=data/execution.pid
  - KILL_FLAG_PATH=data/kill.flag
  - MONITOR_POLL_INTERVAL は run_monitoring で利用（デフォルト 60 秒）

使い方
------

起動系
- 実行エンジン（ExecutionEngine）を起動（パッケージを PYTHONPATH に置くかインストールした状態で）:
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を使用するため本番 DB と分離されます
    - 起動時に data/stop_requested.flag が存在すると起動しません
    - 停止は Kill Switch（data/kill.flag）や stop_requested.flag によって制御します

- 監視ループを起動:
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能（例: export MONITOR_POLL_INTERVAL=30）
  - 監視は Settings.sqlite_path（monitoring DB）を使用します（Monitoring は環境にかかわらず本番 sqlite_path を参照する設計）

ユーティリティ
- 環境設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ペーパートレード検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH を使うか、環境変数 PAPER_TRADING_SQLITE_PATH を設定

注意点 / 運用ノウハウ
- ログ: setup_logging によって stdout と logs/<app>.log（日次ローテーション）が出力されます。LOG_DIR や LOG_LEVEL を環境変数で調整してください。
- Kill Switch:
  - risk_monitor により drawdown やポジション上限を検出すると kill.flag を書き込みます（Settings.kill_flag_path、デフォルト data/kill.flag）。
  - ExecutionEngine は起動時に kill.flag の有無を確認し、書かれている場合は起動を中止します。kill.flag は明示的にクリアする必要があります（config_setup で KILL_FLAG_CLEAR_ON_START=1 にすると起動時クリアが可能だが本番では非推奨）。
- 監視 DB の初期化:
  - monitoring_db.init_monitoring_db は冪等でテーブル作成・マイグレーション（列追加）を行います。実行前に手動で DB を準備する必要はありません。
- AI 機能:
  - OpenAI API を使用する処理（news_nlp / regime_detector）は OPENAI_API_KEY が必要です。API 失敗時はフェイルセーフで処理をスキップまたはデフォルト値を使う設計です。
  - LLM 呼び出しはレート制限やネットワークエラーを考慮し、リトライ（指数バックオフ）を行います。

ディレクトリ構成
----------------

（主要ファイルのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                — 環境変数 / Settings
    - config_setup.py          — .env 対話式ウィザード
    - validate_config.py       — 設定検証 CLI
    - run_execution.py         — ExecutionEngine 起動スクリプト
    - run_monitoring.py        — Monitoring 起動スクリプト
    - ai/
      - __init__.py
      - news_nlp.py            — ニュース NLP（OpenAI）処理
      - regime_detector.py     — 市場レジーム判定（LLM + ma200）
    - monitoring/
      - __init__.py
      - monitoring_db.py       — SQLite 永続層
      - system_monitor.py      — システム監視
      - trade_monitor.py       — 発注・約定監視（抜粋していませんが存在）
      - risk_monitor.py        — ドローダウン / ポジション上限監視
      - kill_switch.py         — kill.flag 管理
      - monitoring_engine.py   — 各 Monitor の統合
      - alert_manager.py       — 通知（LINE など）管理（抜粋）
    - execution/
      - execution_engine.py    — 実行エンジン本体（抜粋）
      - order_manager.py
      - order_repository.py
      - broker_factory.py
      - reconciler.py
      - risk_manager.py
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
      - __init__.py
    - research/
      - factor_research.py
      - feature_exploration.py
      - __init__.py
    - tools/
      - __init__.py
      - paper_verification_report.py
    - utils/
      - logging_setup.py
      - process_priority.py
      - __init__.py
    - data/                     — 実行時に使用するファイル置き場（logs/, data/ 以下）
      - kill.flag
      - stop_requested.flag
      - monitoring.db, paper_trading.db, kabusys.duckdb など

追加情報
--------
- DB:
  - DuckDB は分析用（prices_daily, raw_financials 等）に使われます。パフォーマンスを考慮してローカルファイルを使用する設計です。
  - SQLite は監視ログ / 発注履歴一部に使われます（init_monitoring_db にてテーブル作成・マイグレーションあり）。
- テスト / 開発:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動で .env を読み込む挙動を無効化できます（テスト時に便利）。
- 互換性:
  - process_priority は Windows / POSIX を吸収する旨の実装。psutil による権限エラーは警告を出してスキップします。

ライセンス・貢献
----------------
この README はコードベースから生成された概要です。実運用・商用利用の前に十分なレビューとテストを行ってください。README に追記すべき点（追加コマンド、CI 手順、実運用のデプロイ手順など）があればお知らせください。