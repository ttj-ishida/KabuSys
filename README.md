KabuSys — 日本株自動売買システム（README）
=======================================

概要
----
KabuSys は日本株向けの自動売買システムのコードベースです。本リポジトリは
- 発注エンジン（ExecutionEngine）
- 監視（Monitoring）・アラート
- ポートフォリオ構築・ポジションサイジング
- 研究用ファクター計算（DuckDB を利用）
- AI モジュール（ニュースセンチメント・レジーム判定）
- ペーパートレード検証ツール

などをモジュール化して提供します。設計方針として「本番・ペーパートレードの分離」「ルックアヘッドバイアス回避」「フェイルセーフ（API 失敗時のフォールバック）」を重視しています。

主な機能
--------
- ExecutionEngine：発注・注文管理・リスクチェック・再整合（reconciler）
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、ペーパートレード用 DB に記録（本番 DB と完全分離）
- Monitoring：CPU/メモリ/ディスク、プロセス生存、データ鮮度、滞留注文、ドローダウン等のポーリング監視
  - Kill Switch による停止（data/kill.flag への書き込み）
- Portfolio モジュール：候補選定、スコア配分、セクター制限、ポジションサイジング（単元丸め含む）
- Research：DuckDB 上でファクター（モメンタム/バリュー/ボラティリティ）や将来リターン、IC 等を計算
- AI：OpenAI を用いたニュースセンチメント（ai.news_nlp）および市場レジーム判定（ai.regime_detector）
- ツール：Paper Trading の検証レポート生成スクリプト（tools.paper_verification_report）
- 設定管理／ウィザード／検証：.env 作成支援（config_setup）・設定検証 CLI（validate_config）

前提条件
--------
- Python 3.9+（型注釈に依存）
- 必要な Python パッケージ（主なもの）:
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML（config/*.yaml の内容検証を行う場合。必須ではない）
- SQLite（組み込み）
- ネットワークアクセス（kabuステーション API / OpenAI を使う場合）

インストール（開発向け）
---------------------
1. 仮想環境を作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Unix)
   - .venv\Scripts\activate     (Windows)

2. 依存パッケージをインストール
   - pip install -r requirements.txt
   ※ requirements.txt が無い場合は次を個別にインストール:
   - pip install duckdb psutil openai PyYAML

初期設定（.env の作成）
---------------------
対話式ウィザードで .env を作成できます（推奨）:

- python -m kabusys.config_setup

主要な設定項目（ウィザードで設定される / 代表的な環境変数）
- KABUSYS_ENV: 実行環境（development / paper_trading / live）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabuステーション API のベース URL（デフォルト http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: ペーパートレードでの約定挙動（instant / partial / never / reject）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: 通知（任意）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動でクリアするか（0/1）

設定検証
--------
作成・編集後は設定検証を実行してください:

- python -m kabusys.validate_config
- 警告を FAIL 扱いにする場合: python -m kabusys.validate_config --strict

各種実行方法
-----------

1) ExecutionEngine を起動（発注エンジン）
- python -m kabusys.run_execution
  - KABUSYS_ENV が paper_trading のときは MockBroker を使用し、PAPER_TRADING_SQLITE_PATH（既定 data/paper_trading.db）に取引ログを残します。
  - 起動前に data/stop_requested.flag が存在する場合は起動せず終了します。
  - 起動中は data/execution.pid に PID を書きます（設定で変更可）。
  - 停止は data/stop_requested.flag を作るか ExecutionEngine の API 経由で行います。

2) Monitoring を起動（ポーリングループ）
- python -m kabusys.run_monitoring
  - 環境変数でポーリング間隔を変更: MONITOR_POLL_INTERVAL（秒、デフォルト 60）
  - モニタは常に production の sqlite_path（Settings.sqlite_path）を使用します（監視 DB は本番 DB）。
  - 停止はプロジェクトルート/data/stop_requested.flag を作成すると検出してループを抜けます。

3) Paper Trading 検証レポート
- python -m kabusys.tools.paper_verification_report
  - オプション: --from YYYY-MM-DD, --to YYYY-MM-DD, --db PATH
  - デフォルト DB は環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

4) AI 関連（コード呼び出し）
- ニュースセンチメント: kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
- レジーム判定: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - OPENAI_API_KEY 環境変数または api_key 引数が必要

ログ
---
- logging は kabusys.utils.logging_setup.setup_logging を経由して統一して設定されます。
- デフォルトで stdout に併せて logs/<app_name>.log に日次ローテーションで出力（30日保持）。
- LOG_DIR 環境変数でログディレクトリを変更可能。

重要な実行時フラグ／ファイル
--------------------------
- data/kill.flag : Kill Switch により書き込まれる停止フラグ（ExecutionEngine 側で読み取り）
- data/stop_requested.flag : run_monitoring / run_execution が監視する停止フラグ（手動で作成してプロセス停止）
- data/execution.pid : ExecutionEngine 起動時に書き込まれる PID（デフォルト）
- KILL_FLAG_CLEAR_ON_START=1 を本番で使うと危険（自動で kill.flag をクリアしてしまいます）

ディレクトリ構成（主要ファイル）
------------------------------
以下はソースツリー（src/kabusys 以下）の主要ファイル・モジュールの一覧です（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                -- 環境変数と Settings クラス
  - config_setup.py          -- .env 作成ウィザード（CLI）
  - validate_config.py       -- 設定検証 CLI
  - run_execution.py         -- ExecutionEngine 起動スクリプト
  - run_monitoring.py        -- Monitoring ポーリングループ起動スクリプト

  - execution/               -- 発注エンジン関連（OrderManager, RiskManager, Engine 等）
  - monitoring/
    - monitoring_db.py       -- SQLite 用永続化レイヤ
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py     -- momentum/value/volatility
    - feature_exploration.py -- forward returns / IC / summary
    - __init__.py
  - ai/
    - news_nlp.py            -- ニュースセンチメント（OpenAI）
    - regime_detector.py     -- 市場レジーム判定（OpenAI）
    - __init__.py
  - tools/
    - paper_verification_report.py
  - data/                    -- 実行時に使用する DB / フラグファイル等（例: data/monitoring.db, data/paper_trading.db）

開発者向け注意点
----------------
- DB 分離:
  - Monitoring は settings.sqlite_path（監視 DB）を使用します。ExecutionEngine は KABUSYS_ENV によって本番 DB とペーパートレード用 DB を切り替えます（settings.paper_sqlite_path）。
- ルックアヘッド回避:
  - research / ai モジュールは内部で datetime.today() を直接参照することを避け、target_date ベースで動作します（検証用に再現性を保つため）。
- OpenAI 呼び出し:
  - rate limit / network エラーに対して指数バックオフでリトライする実装が組み込まれていますが、API キーがない場合は ValueError を投げます。テスト時は _call_openai_api をモックすることを推奨します。
- ロギングとログディレクトリ:
  - デフォルトで logs/ に書き込むため、権限やディスク容量に注意してください。ログディレクトリ作成に失敗した場合はコンソール出力のみで継続します。
- プロセス優先度:
  - 起動スクリプトは最初に set_process_priority("high") を呼んで優先度を上げます（プラットフォーム依存・権限によっては失敗して警告が出ます）。

よく使うコマンドまとめ
--------------------
- .env 作成（対話式）:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
  - 厳密モード（警告を FAIL）: python -m kabusys.validate_config --strict
- 発注エンジン起動:
  - python -m kabusys.run_execution
- 監視ループ起動:
  - python -m kabusys.run_monitoring
  - ポーリング間隔変更: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

最後に
-----
この README はコードベースの短い概要です。各モジュール内に詳細な docstring / usage コメントがありますので、実装の詳細やパラメータ仕様は該当ソース（src/kabusys 以下の各ファイル）を参照してください。質問やドキュメント追加の要望があれば教えてください。