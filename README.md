KabuSys — 日本株自動売買システム
=================================

概要
----
KabuSys は日本株向けの自動売買フレームワークです。  
戦略・ポートフォリオ構築、発注エンジン（実運用 / ペーパートレード）、監視（モニタリング / Kill Switch）、リサーチ（ファクター計算 / 特徴量解析）およびニュース由来の AI スコアリング等のコンポーネントを含みます。  
設計方針として「可能な限りフェイルセーフ」「ルックアヘッドバイアスの回避」「テストしやすい純粋関数化」を重視しています。

主な機能
--------
- 実発注・ペーパートレードを切替可能な ExecutionEngine
  - KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用し、data/paper_trading.db に記録
- 監視（Monitoring）
  - システムリソース、プロセス生存、データ鮮度、注文/約定ログの監視
  - Kill Switch（条件成立で data/kill.flag を書き込み、実行エンジンを停止）
  - リスクモニタ（ドローダウン・ポジション上限の検出・ログ記録）
- ポートフォリオ構築ユーティリティ
  - 候補選定、等金額／スコア加重配分、ポジションサイジング（lot 単位丸め）
  - セクターキャップ適用、レジーム乗数
- リサーチ
  - Momentum / Volatility / Value 等のファクター計算（DuckDB 上の prices_daily, raw_financials を参照）
  - 将来リターン計算、IC（Information Coefficient）等の統計解析
- AI（OpenAI）連携
  - ニュースの銘柄別センチメントスコアリング（news_nlp）
  - マクロニュース + ETF MA による市場レジーム判定（regime_detector）
  - OpenAI 呼び出しはリトライ／バリデーション処理あり（フェイルセーフ）
- ツール
  - 環境設定ウィザード（.env の初期作成 / 更新）
  - 設定検証 CLI（.env や config/*.yaml のチェック）
  - Paper Trading 検証レポート生成スクリプト

前提・依存
----------
主な外部依存（例）
- Python 3.9+
- duckdb
- psutil
- openai
- pyyaml（config YAML の検証に使用。未インストール時はスキップ）

pip 等でインストールしてください。requirements.txt があればそちらを利用してください。

セットアップ手順
----------------
1. リポジトリを取得して作業ディレクトリをプロジェクトルートにする。

2. 仮想環境作成・依存インストール（例）
   - python -m venv .venv
   - source .venv/bin/activate
   - pip install -U pip
   - pip install duckdb psutil openai pyyaml

3. 環境変数設定 (.env)
   - 対話式ウィザードで .env を作成:
     - python -m kabusys.config_setup
   - あるいは .env.example を参考に .env を作成（必須キーは後述）。
   - 自動読み込みはデフォルトで有効。自動ロードを無効化するには:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

4. 設定検証（推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗として exit(1) になります:
     - python -m kabusys.validate_config --strict

5. データディレクトリ作成（必要に応じて）
   - data/（デフォルトの DB・PID・フラグファイル格納先）
   - logs/（ログ出力先。自動作成されますが権限のない環境では作成に失敗する場合があります）

主要な環境変数
----------------
（.env で設定する想定。必須）
- JQUANTS_REFRESH_TOKEN （必須）
- KABU_API_PASSWORD （必須）

（任意／既定値あり）
- KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
  - paper_trading: 発注は MockBrokerClient に切り替わり DB は data/paper_trading.db を使用
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL
- LOG_DIR: ログ出力先（デフォルト: logs/）
- KILL_FLAG_CLEAR_ON_START: 0 | 1
  - 本番では 0 を推奨（1 は起動時に Kill Flag を自動クリア）

その他:
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- OPENAI_API_KEY: OpenAI API キー（AI モジュールで利用）

主要コマンド / 使い方
--------------------

- 環境ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
    - KABUSYS_ENV が paper_trading の場合、MockBrokerClient を使用し paper_trading DB に記録
    - 起動時に data/stop_requested.flag が存在すると起動をスキップ
    - 実行中に data/stop_requested.flag が作成されるとエンジンを停止

- 監視モニタ起動（SystemMonitor のポーリングループ）
  - python -m kabusys.run_monitoring
    - デフォルトのポーリング間隔は 60 秒。MONITOR_POLL_INTERVAL で上書き可
    - 監視は production sqlite_path（Settings.sqlite_path）を使用（環境に依存せず）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
    - PAPER_TRADING_SQLITE_PATH 環境変数が優先されます（--db により上書き可）

- AI 関連（プログラムとして呼び出す）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは DuckDB 接続（DuckDBPyConnection）を直接受け取り、DB のテーブルを読み書きします。
  - OpenAI API キーは引数または環境変数 OPENAI_API_KEY を使用

ログ
----
- 共通のログ設定ユーティリティ: kabusys.utils.logging_setup.setup_logging(app_name="...")  
  - stdout（StreamHandler）と日次ローテーションファイル（logs/<app_name>.log）を設定
  - ログディレクトリが作れない場合はコンソール出力のみで継続

監視 / フラグ類
----------------
- 停止フラグ（run_execution / run_monitoring）
  - data/stop_requested.flag を存在チェックしてプロセスを停止・起動抑止
- Kill Switch
  - 条件を満たした際に data/kill.flag を書き込み、ExecutionEngine 停止を促す
  - KillSwitch クラスで評価・書込み・クリアを行える
- PID ファイル
  - data/execution.pid（Settings.pid_file_path がデフォルト）

DB
--
- DuckDB: 分析用（default: data/kabusys.duckdb）
- SQLite: 監視・発注ログ等（default: data/monitoring.db）
- Paper Trading 用 SQLite（分離）: data/paper_trading.db

コード内で DB スキーマの簡易マイグレーション処理（columns 追加等）を行います（monitoring_db.init_monitoring_db）。

ディレクトリ構成（抜粋）
-----------------------
src/kabusys/
- __init__.py
- config.py                  — 環境変数読み込み・Settings クラス（.env 自動ロード機能有）
- config_setup.py            — .env 対話式ウィザード
- validate_config.py         — 設定検証 CLI
- run_execution.py           — ExecutionEngine 起動スクリプト
- run_monitoring.py          — SystemMonitor ポーリングループ起動スクリプト
- tools/
  - paper_verification_report.py — Paper Trading 検証レポート生成スクリプト
- utils/
  - logging_setup.py         — ログ設定ユーティリティ
  - process_priority.py      — プロセス優先度 / CPU affinity 設定
- monitoring/
  - monitoring_db.py         — 監視用 SQLite ラッパー（テーブル生成・ログ用 API）
  - system_monitor.py        — システム状態 / データ鮮度監視
  - trade_monitor.py         — 注文/約定監視（ファイル中に定義あり）
  - risk_monitor.py          — ドローダウン・ポジション監視
  - kill_switch.py           — Kill Switch 実装
  - monitoring_engine.py     — 各 Monitor を組み合わせたループ実行器
  - alert_manager.py         — アラート送信（LINE 等想定）
- execution/
  - execution_engine.py      — 実行エンジン本体（EngineConfig, run_session 等）
  - order_manager.py
  - order_repository.py
  - broker_factory.py
  - reconciler.py
  - risk_manager.py
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- ai/
  - news_nlp.py              — ニュース NLP スコアリング（OpenAI 連携）
  - regime_detector.py       — レジーム判定（ETF MA + マクロニュース）

出力例・実行フロー（簡略）
-------------------------
1. .env を作成 -> 設定を検証
2. 実行エンジンを起動（run_execution）またはペーパートレードで検証
3. 別プロセスで監視を起動（run_monitoring）して状態を定期的に記録／Kill Switch を評価
4. 必要に応じて AI モジュールでニューススコア/レジーム判定を行い DB に書き込む
5. tools/paper_verification_report でペーパートレード挙動を総括

注意点 / トラブルシューティング
--------------------------------
- .env に必須キーが無いと起動時にエラーになります。validate_config を必ず実行してください。
- ログディレクトリの作成に失敗した場合はファイルログが無効化され、コンソールのみになります（警告が出ます）。
- OpenAI API 呼び出しにはレート制限やネットワークエラーが発生します。本実装は指数バックオフとリトライを備えていますが、API キーや料金設定は各自で管理してください。
- 自動環境変数ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト時に有用）。

貢献 / 拡張のヒント
-------------------
- ブローカークライアント実装を追加して実ブローカ接続を実装できます（broker_factory.py を参照）。
- ポートフォリオ構築ロジックや戦略モデルは独立したモジュールとして実装し、ExecutionEngine に差し込む設計です。
- 単体テストや CI を導入して各純粋関数（portfolio/*、research/*）の検証を強化してください。

---

この README はコードベースの主要部分をもとに作成しています。実環境での運用前に必ず設定検証（python -m kabusys.validate_config）とローカルでの十分なテストを行ってください。