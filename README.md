KabuSys — 日本株自動売買システム（README）
=====================================

概要
----
KabuSys は日本株向けの自動売買システムのコードベースです。本リポジトリには以下の主要機能を持つモジュールが含まれます。
- 実行エンジン（ExecutionEngine）: 発注・リスク管理・約定管理を担う（本番 / ペーパートレード対応）
- 監視（Monitoring）: システム健全性・注文・リスクを定期チェックしてログ保存・アラート／Kill Switch を管理
- ポートフォリオ構築（Portfolio）: 候補選定、重み付け、ポジションサイズ計算、セクター制限など
- リサーチ（Research）: ファクター計算、特徴量探索（DuckDB を利用）
- AI ユーティリティ: ニュース NLP によるセンチメント評価、レジーム判定（OpenAI）
- 開発ツール: 設定ウィザード、設定検証、ペーパー取引検証レポート出力

主な特徴（機能一覧）
------------------
- 環境別分離
  - KABUSYS_ENV により development / paper_trading / live を切替
  - paper_trading 時は MockBroker を使い、ペーパートレード用 DB（data/paper_trading.db）に記録
- 監視機構
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - システム稼働率、データ鮮度、滞留注文、異常約定、ドローダウン・ポジション上限監視
  - Kill Switch（data/kill.flag）で実行エンジンを安全に停止可能
- ログ管理
  - 統一的な logging セットアップ（コンソール + 日次ローテートファイル）
  - デフォルトログディレクトリ: logs/
- DB
  - 分析用 DuckDB（デフォルト: data/kabusys.duckdb）
  - 監視用 SQLite（デフォルト: data/monitoring.db）
  - （紙上トレード時に分離される）ペーパートレード SQLite（デフォルト: data/paper_trading.db）
- AI 統合
  - OpenAI を用いたニュースセンチメント（ai.news_nlp）
  - マクロニュース + ETF MA を用いた市場レジーム判定（ai.regime_detector）
- リサーチ機能
  - モメンタム、ボラティリティ、バリュー等のファクター計算（DuckDB）
  - IC（Information Coefficient）や統計サマリー計算

前提条件
--------
- Python 3.10+
- 必須パッケージ（代表例）:
  - duckdb
  - psutil
  - openai
- 任意（機能によって必要）:
  - PyYAML（config/*.yaml の内容検証に使用。validate_config で警告軽減）
- SQLite（標準ライブラリに含まれます）

セットアップ手順
---------------
1. リポジトリをクローン・移動
   - git clone ... && cd <repo>

2. 仮想環境を作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb psutil openai
   - （オプション）pip install pyyaml

   ※ requirements.txt は本コードベースに含まれていないため、上記パッケージを個別にインストールしてください。

4. データディレクトリ等の準備
   - data/ と logs/ は起動時に自動作成されることが多いですが、必要に応じて手動で作成してください。

環境変数（主要）
----------------
設定は .env ファイルまたは OS 環境変数で行います。config_setup.py のウィザードで .env を生成できます。

代表的な環境変数（デフォルト値／説明）:
- KABUSYS_ENV (development | paper_trading | live) — 実行環境（デフォルト: development）
- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABU_API_BASE_URL (http://localhost:18080/kabusapi) — kabu API ベース URL
- OPENAI_API_KEY — OpenAI API キー（ai モジュール利用時必須）
- DUCKDB_PATH (data/kabusys.duckdb) — DuckDB ファイルパス
- SQLITE_PATH (data/monitoring.db) — 監視用 SQLite ファイルパス
- PAPER_TRADING_SQLITE_PATH (data/paper_trading.db) — ペーパー取引用 SQLite（paper_trading 時）
- LOG_LEVEL (INFO) — ログレベル
- LOG_DIR (logs/) — ログ出力ディレクトリ
- KILL_FLAG_CLEAR_ON_START (0|1) — 起動時に kill.flag を自動クリア（本番では 0 推奨）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE — ペーパートレードの約定挙動（instant|partial|never|reject、デフォルト instant）

自動 .env ロード
- kabusys.config はプロジェクトルート（.git または pyproject.toml を基準）から .env/.env.local を自動で読み込みます。
- 自動読み込みを抑止する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

使い方（起動コマンド）
--------------------
各スクリプトはパッケージモジュールとして起動できます（推奨: 仮想環境内で実行）。

1. 設定ウィザード（.env の初期作成）
   - python -m kabusys.config_setup
   - 対話形式で .env を作成・更新します。

2. 設定の検証
   - python -m kabusys.validate_config
   - --strict をつけると警告も失敗扱いになります:
     - python -m kabusys.validate_config --strict

3. 実行エンジン（ExecutionEngine）起動
   - python -m kabusys.run_execution
   - 動作:
     - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、paper_trading 用 DB へ記録
     - プロセス優先度を high にセット
     - 停止: data/stop_requested.flag を作成するか、Execution 側のログに従って停止

4. 監視（Monitoring）起動
   - python -m kabusys.run_monitoring
   - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で変更可能（デフォルト 60）
   - 監視は本番 sqlite_path（Settings.sqlite_path）を使用（環境に依らず）

5. ペーパートレード検証レポート
   - python -m kabusys.tools.paper_verification_report
   - 期間指定:
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - DB パスは --db または 環境変数 PAPER_TRADING_SQLITE_PATH で指定可能

6. AI / レジーム判定など（ライブラリ関数の呼び出し）
   - Python から直接呼び出して利用:
     - from kabusys.ai.news_nlp import score_news
     - from kabusys.ai.regime_detector import score_regime
   - OpenAI API キー（OPENAI_API_KEY）を適切に設定してください。

停止・Kill Switch
-----------------
- 停止フラグ（実行制御）:
  - data/stop_requested.flag — run_execution/run_monitoring が監視している「停止要求ファイル」
  - data/kill.flag — KillSwitch が書き込むファイル。ExecutionEngine 停止のトリガーに使われる
- KillSwitch は RiskMonitor のチェック結果（ドローダウン・ポジション上限）に基づき kill.flag を作成します。
- 起動時に kill.flag を自動削除したい場合は KILL_FLAG_CLEAR_ON_START=1 を設定できます（本番では推奨されません）。

ディレクトリ構成（抜粋）
----------------------
ここでは本コードベースに含まれる主要ファイル／モジュールのツリー（抜粋）を示します。

- src/
  - kabusys/
    - __init__.py
    - config.py                — 環境変数 / 設定管理（自動 .env ロード含む）
    - config_setup.py          — .env 対話ウィザード
    - validate_config.py       — 設定検証 CLI
    - run_execution.py         — ExecutionEngine 起動スクリプト
    - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
    - monitoring/
      - monitoring_db.py       — SQLite テーブル初期化・永続化 API
      - monitoring_engine.py   — 各 Monitor をまとめたエンジン
      - system_monitor.py      — CPU/メモリ/ディスク・データ鮮度監視
      - risk_monitor.py        — ドローダウン・ポジション上限監視
      - kill_switch.py         — kill.flag 管理
      - (alert_manager, trade_monitor 等の補助モジュール)
    - execution/
      - execution_engine.py
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - broker_factory.py
      - risk_manager.py
      - （各実行ロジック）
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - factor_research.py
      - feature_exploration.py
    - ai/
      - news_nlp.py
      - regime_detector.py
    - tools/
      - paper_verification_report.py
    - utils/
      - logging_setup.py
      - process_priority.py
    - data/ (runtime)
      - kill.flag
      - stop_requested.flag
      - *.db
- config/
  - system_config.yaml, data_config.yaml, ...（テンプレート／生成用）

開発・デバッグのヒント
---------------------
- ログ設定:
  - 各起動スクリプトは setup_logging(app_name=...) を使ってログを統一しています。LOG_DIR / LOG_LEVEL を調整してください。
- 設定検証:
  - python -m kabusys.validate_config で未設定の環境変数や YAML ファイルの存在を確認できます。PyYAML が入っていれば YAML のパース検証も行います。
- テスト実行:
  - モジュールは関数単位で純粋関数設計（リサーチ／ポートフォリオ等）になっているためユニットテストを書きやすい構成です。
- DuckDB:
  - research モジュールは DuckDB 接続を受け取り prices_daily / raw_financials などのテーブルを前提としています。データ投入方法は別ドキュメント（Data Pipeline）を参照してください。

注意事項 / 安全上の留意点
------------------------
- .env は絶対に Git にコミットしないでください（config_setup.py の出力にも注意書きがあります）。
- KABUSYS_ENV=live の設定は本番運用につながるため、LINE 通知設定や kill flag 設定等を慎重に確認してください（validate_config がいくつかのガードチェックを提供します）。
- OpenAI API キーやブローカー情報は安全に管理してください。
- run_execution/run_monitoring はプロセス優先度を "high" に設定しようとしますが、環境によっては権限エラーが出る場合があります（警告ログが出ますが継続します）。

よく使うコマンドまとめ
---------------------
- 設定ウィザード: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config [--strict]
- 実行エンジン起動: python -m kabusys.run_execution
- 監視起動: python -m kabusys.run_monitoring
- ペーパートレード検証レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

付録: 例 .env（最小）
--------------------
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_api_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-xxxx  # AI 機能を使う場合のみ設定

以上がこのコードベースの概要、セットアップ、使い方、構成になります。必要であれば各モジュール（ExecutionEngine の起動オプション、Broker 実装の切替、monitoring の詳細なアラート設定方法など）についてさらに詳細なドキュメントを作成します。どの部分を深掘りしましょうか？