README — KabuSys
=================

概要
----
KabuSys は日本株の自動売買システム向けユーティリティ群および実行/監視コンポーネントの実装です。  
主に以下を提供します。

- ExecutionEngine: 発注・注文管理・リスク管理・約定調整を行う実行エンジン
- Monitoring: システム状態、注文状況、リスク（ドローダウン等）を定期チェックしログ・アラートを管理
- Portfolio 構築ユーティリティ: 候補選定、重み計算、ポジションサイズ決定などの純関数群
- Research / AI: DuckDB を用いたファクター計算、特徴量探索、および OpenAI を用いたニュース NLP / レジーム判定
- ユーティリティ: ログ設定、プロセス優先度設定、設定ウィザード、設定検証など

機能一覧
--------
- 環境設定ウィザード（.env の対話的作成・更新）: kabusys.config_setup
- 設定検証 CLI（.env と config/*.yaml の基本チェック）: kabusys.validate_config
- ExecutionEngine 起動スクリプト: run_execution.py
  - KABUSYS_ENV=paper_trading 時は MockBroker を使用し paper_trading DB に記録（本番 DB と分離）
- Monitoring 起動スクリプト: run_monitoring.py
  - 定期ポーリングで system/trade/risk をチェックし監視ログを永続化
  - MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60 秒）
- Paper Trading 検証レポート生成ツール: kabusys.tools.paper_verification_report
- DuckDB ベースのリサーチ（ファクター計算、forward returns、IC 計算 等）
- OpenAI を用いたニュースセンチメント（ai.news_nlp）と市場レジーム判定（ai.regime_detector）
- ロギングの統一設定（コンソール + 日次ローテートファイル）
- プロセス優先度 / CPU affinity のクロスプラットフォーム対応ユーティリティ

必要条件
--------
- Python 3.9+（コードは型注釈を含むため 3.9 以上を想定）
- 依存パッケージ（例）
  - duckdb
  - psutil
  - openai（AI 機能を使う場合）
  - PyYAML（config YAML の内容検証を行う場合）
- SQLite（標準ライブラリに同梱）
- OS 標準のファイルアクセス権（data/, logs/ ディレクトリの作成・書き込み）

セットアップ手順
---------------
1. リポジトリをクローン／展開
2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install -r requirements.txt
     （プロジェクトに requirements.txt がない場合は最低限 duckdb, psutil, openai, pyyaml を導入）
4. .env の作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
   - 指示に従って J-Quants トークン、Kabu API パスワード、DB パス、環境等を設定します
   - 生成された .env は絶対に Git にコミットしないでください
5. 設定検証（任意）
   - python -m kabusys.validate_config
   - 警告も失敗扱いにする場合は --strict を付与
6. （AI 機能を使う場合）OpenAI API キーを設定
   - 環境変数 OPENAI_API_KEY を .env に設定

主要な環境変数（抜粋）
--------------------
- JQUANTS_REFRESH_TOKEN（必須）: J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD（必須）: kabuステーション API のパスワード
- KABUSYS_ENV: 実行環境（development / paper_trading / live）
- DUCKDB_PATH: DuckDB ファイルのパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（monitoring）パス（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（paper_trading 時に使用）
- PAPER_FILL_MODE: ペーパートレードの約定挙動（instant|partial|never|reject）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- OPENAI_API_KEY: OpenAI 利用時に必要
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）

使い方
------
- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - strict モード: python -m kabusys.validate_config --strict

- ExecutionEngine 起動（本番/ペーパー共通起動スクリプト）
  - python -m kabusys.run_execution
  - 注意: KABUSYS_ENV が paper_trading の場合、MockBrokerClient を使い PAPER_TRADING_SQLITE_PATH を使用します
  - 停止制御:
    - stop: プロジェクトルートの data/stop_requested.flag を作成すると実行中のプロセスが検知して終了します
    - kill switch: monitor 側から data/kill.flag を書き込んでエンジンを停止させる仕組みがあります

- Monitoring 起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔を上書き: MONITOR_POLL_INTERVAL=120 python -m kabusys.run_monitoring
  - 停止: data/stop_requested.flag を作成

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスは --db または 環境変数 PAPER_TRADING_SQLITE_PATH

- AI 関連（プログラム API）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - いずれも OpenAI API キー（OPENAI_API_KEY）を参照／受け取ります

ログ
----
- ログ設定は kabusys.utils.logging_setup.setup_logging を通して統一されます
- デフォルトでコンソール (stdout) と logs/<app_name>.log（日次ローテート）に出力
- ログディレクトリは LOG_DIR 環境変数、もしくはデフォルト "logs/"

停止／Kill フラグ
-----------------
- data/stop_requested.flag: run_execution/run_monitoring が存在を検知すると安全に停止します
- data/kill.flag: KillSwitch により書き込まれると ExecutionEngine 側で停止（本番向けの安全機構）
- PID ファイル: data/execution.pid に ExecutionEngine の PID を書きます（プロセス監視用）

ディレクトリ構成（主要ファイル）
------------------------------
以下は src/kabusys 配下の主要モジュールと役割の抜粋です。

- kabusys/
  - __init__.py: パッケージ定義（__version__ 等）
  - config.py: 環境変数 / 設定読み込みロジック、Settings クラス
  - config_setup.py: .env 対話式ウィザード
  - validate_config.py: 設定検証 CLI
  - run_execution.py: ExecutionEngine 起動スクリプト
  - run_monitoring.py: Monitoring 起動スクリプト

  - utils/
    - logging_setup.py: ログ初期化ユーティリティ
    - process_priority.py: プロセス優先度・CPU affinity 設定ユーティリティ

  - monitoring/
    - monitoring_db.py: SQLite 監視 DB（テーブル作成・読み書きユーティリティ）
    - system_monitor.py: CPU/メモリ/ディスク/データ鮮度/プロセス生存チェック
    - trade_monitor.py: （注文関連監視ロジック）
    - risk_monitor.py: ドローダウン・ポジション上限監視
    - kill_switch.py: kill.flag の作成・評価
    - monitoring_engine.py: 各 Monitor を束ねるエンジン
    - alert_manager.py: （LINE などへの通知処理 / 別実装想定）

  - execution/
    - execution_engine.py: 実行エンジン本体
    - order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py: 発注・リスク・リポジトリ等（実行に関わるコンポーネント）

  - portfolio/
    - portfolio_builder.py: 候補選定・重み付け
    - position_sizing.py: 株数算出（単元丸め、aggregate cap）
    - risk_adjustment.py: セクター上限、レジーム乗数

  - research/
    - factor_research.py: モメンタム/ボラ/バリュー等ファクター計算（DuckDB 利用）
    - feature_exploration.py: 将来リターン、IC、統計サマリー

  - ai/
    - news_nlp.py: ニュースを OpenAI で評価し ai_scores に書き込む処理
    - regime_detector.py: ETF MA とマクロニュースで市場レジーム判定

  - tools/
    - paper_verification_report.py: ペーパートレード検証レポート生成

実運用時の注意点 / 開発メモ
--------------------------
- 本番実行環境（KABUSYS_ENV=live）では設定・キーの管理に細心の注意を払ってください。validate_config は本番用のガードを含みます。
- .env は絶対に Git にコミットしないでください。
- Monitoring はどの環境でも（設定にかかわらず）監視用の sqlite_path を参照して監視ログを記録します（run_monitoring の実装上の仕様）。
- Paper Trading は本番 DB と分離されます（paper_sqlite_path / PAPER_TRADING_SQLITE_PATH を使用）。
- OpenAI 呼び出しはレート制限やネットワークエラーに対してリトライロジックを備えていますが、API キー管理とコスト管理を行ってください。
- DuckDB を利用する関数群は prices_daily / raw_financials 等のテーブルを前提にしています。データ投入パイプラインは別実装（kabusys.data.pipeline）を参照してください。

貢献 / テスト
--------------
- 小さなユニット（portfolio の純粋関数群、research の計算関数等）は単体テストを書きやすい設計です。外部依存（DB / API）をモックしてテストを実施してください。
- AI 呼び出し部分は _call_openai_api を patch してテスト可能です。

付記
----
この README はコードベースの主要機能と操作手順をまとめたものです。実際の運用前に python -m kabusys.validate_config による検証と .env の確認、そしてテスト実行を必ず行ってください。