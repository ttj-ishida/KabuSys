README
=====

概要
----
KabuSys は日本株向けの自動売買／リサーチ基盤の一部を実装したパッケージです。本リポジトリには次のような機能群が含まれます:

- ExecutionEngine（発注エンジン）: 本番 / ペーパートレードに対応
- Monitoring（監視）: システム稼働・注文状況・リスク監視、Kill Switch の発動
- Portfolio 構築ユーティリティ: 候補選定、配分、ポジション決定、セクター制限
- Research ツール: ファクター計算、将来リターン・IC 計算、特徴量要約
- AI ユーティリティ: ニュースセンチメント（OpenAI）やレジーム判定のラッパ
- 各種 CLI ツール: .env ウィザード、設定検証、Paper Trading レポート など

本 README はソースコード（src/kabusys 配下）をもとに、導入・起動手順、使い方、ディレクトリ構成をまとめたものです。

主な機能一覧
-------------
- 環境管理
  - .env ウィザード（kabusys.config_setup）で初期設定を支援
  - 自動 .env 読み込み（プロジェクトルートに .env / .env.local があればロード）
- 設定検証
  - kabusys.validate_config: 起動前に環境変数／config/*.yaml の整合性チェック
- 発注（Execution）
  - KABUSYS_ENV による本番 / ペーパー分離
  - paper_trading モードでは専用の paper_trading.db にログを保持
  - プロセス優先度設定、PID 管理、停止フラグ監視
- 監視（Monitoring）
  - System / Trade / Risk 各 Monitor を組み合わせたポーリング
  - kill.flag による強制停止、アラート発行フック
  - monitoring.db に稼働ログ、注文ログ、リスクログ、ダッシュボードを永続化
- ポートフォリオ関連（純粋関数）
  - 候補選定、等配分／スコア加重、リスク調整（セクターキャップ、レジーム乗数）
  - ポジションサイズ計算（単元株丸め、aggregate cap のスケール）
- Research
  - モメンタム / ボラティリティ / バリュー等のファクター計算（DuckDB 接続前提）
  - 将来リターン、IC、ファクター統計サマリ
- AI
  - news_nlp: OpenAI によるニュースセンチメント算出・ai_scores 書込み
  - regime_detector: ma200 とマクロニュースを合成して market_regime を判定
- ツール
  - paper_verification_report: ペーパートレード実績を要約・合否判定レポート生成

セットアップ手順
----------------
1. リポジトリをクローン:
   - git clone <repo-url>
   - cd <repo>

2. Python 仮想環境作成（推奨）:
   - python -m venv .venv
   - source .venv/bin/activate  # Unix/macOS
   - .venv\Scripts\activate     # Windows (PowerShell)

3. 依存ライブラリをインストール:
   - requirements.txt がある場合:
     - pip install -r requirements.txt
   - なければ少なくとも以下を入れてください:
     - pip install duckdb psutil openai
     - PyYAML は config/.yaml のパース確認に必要（任意）:
       - pip install PyYAML

   ※ sqlite3 は標準ライブラリに含まれます。

4. .env を作成（ウィザード推奨）:
   - python -m kabusys.config_setup
     - 対話的に .env を生成します（デフォルト: プロジェクトルート/.env）。
   - あるいは .env を手動で作成（.env.example を参照）

5. 設定の検証:
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit code 1）になります

環境変数（主なもの）
-------------------
以下はソースコードで参照される主要な環境変数とデフォルト値（存在しない場合）です:

必須（実運用時）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）

主な任意 / デフォルト
- KABUSYS_ENV: 実行環境（development / paper_trading / live） — デフォルト: development
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading モード専用）
- LOG_LEVEL: INFO（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- KABU_API_BASE_URL: http://localhost:18080/kabusapi
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: 通知用（任意）
- PAPER_FILL_MODE: ペーパートレードでの約定モード（instant / partial / never / reject）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）

デフォルトの注意点:
- monitoring は "環境にかかわらず本番 sqlite_path を使用"（run_monitoring の挙動）
- run_execution は KABUSYS_ENV=paper_trading の場合 paper_sqlite_path を使用して本番 DB から分離

ログ
----
- setup_logging 関数は stdout（StreamHandler）と 日次ローテートのファイルハンドラ（logs/<app_name>.log）を設定します。
- デフォルトログディレクトリ: logs/
- ログファイルは日次ローテーション・30日分保持

基本的な使い方（起動・実行例）
----------------------------

1) ExecutionEngine を起動（パッケージモード）
- 標準起動:
  - python -m kabusys.run_execution
- ペーパートレードで起動する場合:
  - export KABUSYS_ENV=paper_trading
  - python -m kabusys.run_execution
  - （Windows PowerShell の場合: $env:KABUSYS_ENV="paper_trading"）

- 停止:
  - プロセスを終了するか、プロジェクトルート/data/stop_requested.flag を作成すると停止検出します。
  - エンジンの PID は data/execution.pid（デフォルト）に保存されます。

2) Monitoring を起動（ポーリングループ）
- python -m kabusys.run_monitoring
- ポーリング間隔を変更する:
  - export MONITOR_POLL_INTERVAL=30
  - python -m kabusys.run_monitoring
- 停止フラグ:
  - プロジェクトルート/data/stop_requested.flag を作成すると監視ループが終了します。

3) .env のウィザード（対話で設定）
- python -m kabusys.config_setup
  - 完了後は python -m kabusys.validate_config でチェック

4) 設定検証 CLI
- python -m kabusys.validate_config
- --strict を付けると警告があると exit(1) で終了

5) Paper Trading 検証レポート
- python -m kabusys.tools.paper_verification_report
- 期間指定:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- DB ファイル指定:
  - --db path/to/paper_trading.db
  - 環境変数 PAPER_TRADING_SQLITE_PATH で指定することも可能

6) AI / Research 関数の利用（プログラムから）
- DuckDB の接続（duckdb.connect）を渡して各関数を呼び出します:
  - from kabusys.research import calc_momentum, calc_volatility, calc_value
  - from kabusys.ai import score_news
  - 例: score_news(conn, target_date, api_key="sk-...")

注意:
- AI 関連（news_nlp, regime_detector）は OpenAI API キー（OPENAI_API_KEY）を要求します。テスト時は関数をモックしてください。
- Research / AI はデータベース（DuckDB）のテーブル構造に依存します（prices_daily, raw_financials, raw_news 等）。

Kill Switch / 停止フラグ
---------------------
- Kill Switch は data/kill.flag を書き込むことで ExecutionEngine を停止対象にします（KillSwitch クラス）。
- 設定で KILL_FLAG_CLEAR_ON_START=1 を指定すると起動時に自動で kill.flag をクリアします（本番では推奨されません）。
- また run_* スクリプトは data/stop_requested.flag による手動停止もサポートします。

ディレクトリ構成（主要ファイル）
------------------------------
以下は src/kabusys 配下の主要モジュールとサブパッケージの概観（抜粋）です:

- src/
  - kabusys/
    - __init__.py
    - config.py                # 環境変数 & Settings クラス（自動 .env ロード）
    - config_setup.py          # .env ウィザード CLI
    - validate_config.py       # 設定検証 CLI
    - run_execution.py         # ExecutionEngine 起動スクリプト
    - run_monitoring.py        # Monitoring 起動スクリプト
    - monitoring/
      - monitoring_db.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - monitoring_engine.py
      - kill_switch.py
      - alert_manager.py
    - execution/
      - execution_engine.py
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
    - ai/
      - news_nlp.py
      - regime_detector.py
      - __init__.py
    - utils/
      - logging_setup.py
      - process_priority.py
      - __init__.py
    - tools/
      - paper_verification_report.py
      - __init__.py
    - data/                    # 実行時に生成される (logs/, data/*.db, flag ファイル 等)
    - config/                  # YAML テンプレート等（system_config.yaml 等）

補足・運用上の注意
------------------
- 本リポジトリには本番発注ロジックや外部 API の取り扱いが含まれるため、KABUSYS_ENV を "live" にする前に .env と config を十分に検証してください。
- .env は絶対に Git にコミットしないこと（config_setup のヘッダにその旨が書かれています）。
- ログディレクトリ・DB パスは起動時に自動作成される場合がありますが、適切なパーミッションがない環境ではファイル出力が失敗する可能性があります（その場合は標準出力にフォールバックします）。
- OpenAI や J-Quants 等の API キーは必要に応じて環境変数で設定してください。

ライセンス / 貢献
-----------------
- 本 README にライセンスや貢献方針の記載はありません。実運用や配布の前に LICENSE を確認してください。

以上が本コードベースの README です。必要に応じて、起動コマンドのユニットや systemd / supervisor 用のサービス定義、Dockerfile、具体的な config/*.yaml のテンプレートなどを追加で用意すると本番運用が容易になります。