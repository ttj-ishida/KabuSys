README.md

KabuSys — 日本株自動売買システム
=================================

概要
----
KabuSys は日本株向けの自動売買・研究・監視を目的とした Python コードベースです。
主に以下の機能を備えます:

- 実行エンジン（ExecutionEngine）による発注処理（本番 / ペーパートレード対応）
- 監視（System / Trade / Risk）と Kill Switch による安全停止
- ポートフォリオ構築（銘柄選定、配分、ポジションサイズ計算）
- リサーチ用ファクター計算・特徴量探索（DuckDB を利用）
- AI を使ったニュースセンチメント評価・市場レジーム判定（OpenAI）
- ペーパートレード検証レポート生成ツール

このリポジトリは、運用用の DB（SQLite / DuckDB）や外部 API（kabuステーション、J-Quants、OpenAI）と連携して動作します。

主要機能一覧
--------------
- 実行エンジン起動スクリプト:
  - run_execution.py — ExecutionEngine を起動（KABUSYS_ENV により Mock / Live 切替）
- 監視ループ起動スクリプト:
  - run_monitoring.py — SystemMonitor をポーリングして監視ログを書き込み
- 環境設定ウィザード:
  - config_setup.py — 対話式で .env を作成 / 更新
- 設定検証 CLI:
  - validate_config.py — .env / config/*.yaml 等のチェック
- ペーパートレード検証:
  - tools/paper_verification_report.py — ペーパートレード SQLite DB から指標を集計しレポート出力
- ポートフォリオ構築:
  - portfolio/* — 候補選定、重み計算、セクター制約、ポジションサイズ算出
- リサーチ:
  - research/* — ファクター計算（Momentum、Volatility、Value）、将来リターン、IC、統計サマリ
- AI モジュール:
  - ai/news_nlp.py — ニュースを LLM でスコアリングして ai_scores に書込
  - ai/regime_detector.py — MA と LLM を合成して market_regime を判定
- 監視:
  - monitoring/* — monitoring DB 層、System/Trade/Risk モニタ、KillSwitch、AlertManager 等
- ユーティリティ:
  - utils/process_priority.py — プロセス優先度・CPU affinity 設定ユーティリティ

要件 / 依存関係
----------------
- Python 3.10+
- 必須（機能に応じて）:
  - duckdb
  - psutil
  - openai （AI 機能利用時）
- 任意 / 開発時:
  - PyYAML（config 検証時に YAML のパースチェックを行う場合）
- インストール例:
  - pip install duckdb psutil openai pyyaml

セットアップ手順
----------------
1. リポジトリをクローン / 展開する。

2. 必要パッケージをインストールする:
   - pip install duckdb psutil openai pyyaml

3. 環境変数（.env）を用意する:
   - 対話式ウィザードで生成:
     - python -m kabusys.config_setup
   - もしくは手動で .env を作成（プロジェクトルートに配置）
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - AI 機能を使う場合:
     - OPENAI_API_KEY を設定

4. 設定を検証する:
   - python -m kabusys.validate_config
   - 警告もエラー扱いにする場合は --strict を付与

5. DB 初期化:
   - 実行スクリプトを起動すると monitoring 用 SQLite（デフォルト: data/monitoring.db）のテーブルは自動作成されます。
   - DuckDB（デフォルト: data/kabusys.duckdb）は外部で準備してください（price データ等をロードする用途）。

重要な環境変数（主なもの）
--------------------------
- KABUSYS_ENV: 実行環境（development | paper_trading | live）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（SQLite）パス（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: ペーパー口座の約定挙動（instant | partial | never | reject）デフォルト "instant"
- LOG_LEVEL: ログレベル (DEBUG|INFO|WARNING|ERROR|CRITICAL)
- OPENAI_API_KEY: OpenAI API キー（AI 機能で必須）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング秒数（デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動クリアするか (0/1)

.example .env（出力される内容の例）
----------------------------------
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password_here
KABU_API_BASE_URL=http://localhost:18080/kabusapi
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0
LINE_CHANNEL_ACCESS_TOKEN=
LINE_USER_ID=

実行方法 / 使い方
------------------
- 環境設定ウィザード（.env 作成）:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行エンジン起動（本番/ペーパーに依存）:
  - python -m kabusys.run_execution
  - 注意: KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、ペーパー用 DB（data/paper_trading.db）に記録されます。

- 監視ループ起動:
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更する:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- ペーパートレード検証レポート:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB ファイルを指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

停止 / Kill Switch / フラグファイル
----------------------------------
- Kill Switch（自動停止）:
  - リスク条件（ドローダウンやポジション上限）を満たすと、data/kill.flag が書き込まれ ExecutionEngine 側で検出して停止します。
- 手動停止（監視）:
  - run_monitoring は data/stop_requested.flag の存在を検出するとループを終了します。
- ExecutionEngine 停止:
  - run_execution は起動中に data/stop_requested.flag を検出するとエンジンを停止します。
- PID ファイル:
  - Execution 起動時に data/execution.pid が生成されることが想定されています。SystemMonitor は PID ファイルの有無とプロセス存在をチェックします。

監視 DB（SQLite）について
-------------------------
- monitoring_db.init_monitoring_db が以下テーブルを作成（冪等）:
  - system_status, trade_logs, positions, risk_logs, dashboard
- run_execution と run_monitoring 起動時に必要に応じてテーブルを初期化します。

開発・デバッグのヒント
---------------------
- 自動で .env を読み込む仕組み:
  - プロジェクトルートにある .env を自動で読み込みます（優先順: OS 環境変数 > .env.local > .env）。
  - テスト時など自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- process priority:
  - 実行スクリプトは起動時にプロセス優先度を "high" に設定しようとします（psutil を使用）。権限や OS により失敗する場合がありますがログは出力されます。
- AI 機能のテスト:
  - news_nlp._call_openai_api や regime_detector._call_openai_api を unittest.mock.patch して API 呼び出しをモックできます。

ディレクトリ構成
----------------
（主要ファイルとサブパッケージの概観）
- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / 設定取得ロジック
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - utils/
    - process_priority.py
  - execution/                 — (ExecutionEngine, OrderManager 等。詳細実装は本ツリー内に存在)
  - data/                      — 実行時に使用するデータファイル（data/kabusys.duckdb, data/monitoring.db 等）
  - その他 config/*.yaml 等

ライセンス / バージョン
-----------------------
- パッケージバージョンは kabusys.__version__ で管理されています（例: 0.1.0）。
- ライセンス情報はプロジェクトルートの LICENSE を参照してください（このリポジトリのサンプルコードには含まれていません）。

補足
----
- 本リポジトリのコードは「実運用での安全性・機密管理」を前提に設計されています。.env や API キー等の機密情報は決してバージョン管理にコミットしないでください。
- 実際の発注処理（Kabuステーション連携）を行うモジュールは十分なテストと現場での確認が必要です。ペーパートレードモードでの検証を推奨します。

質問や README の追記希望があれば、どの部分を詳しく書けばよいか教えてください。