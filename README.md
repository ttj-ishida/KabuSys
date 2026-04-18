KabuSys — 日本株自動売買システム
=============================

本リポジトリは日本株向けの自動売買／リサーチ基盤のコード群（ライブラリ＋起動スクリプト）です。  
この README はコードベース（src/kabusys 以下）の主要コンポーネント、導入手順、起動方法、ディレクトリ構成の概要を日本語でまとめたものです。

要点
----
- 自動売買エンジン（ExecutionEngine）と監視プロセス（Monitoring）を備えます。
- Paper Trading（ペーパートレード）用に本番 DB と分離した専用 DB を使えます。
- DuckDB を使ったリサーチ／ファクター計算、AI（OpenAI）を使ったニュース NLP、レジーム判定などの機能を含みます。
- ログ周り・プロセス優先度設定・Kill Switch（停止フラグ）など運用向けのユーティリティを用意しています。

主な機能
-------
- ExecutionEngine（起動スクリプト: run_execution.py）
  - ブローカークライアントを抽象化（paper_trading では MockBrokerClient を使用）。
  - 注文管理・リスク管理・リコンサイル（整合性復元）などの実行ロジックを統合。
  - 起動時に data/execution.pid を作成、停止はフラグファイルで制御。

- Monitoring（起動スクリプト: run_monitoring.py）
  - システムリソース、データ鮮度、注文ログやリスク指標を定期ポーリングして SQLite に記録。
  - KillSwitch による自動停止（drawdown やポジション上限トリガ）とアラート連携が可能。
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
  - 監視は本番 sqlite_path を常に使用（環境にかかわらず）。

- 監視永続化層（monitoring_db.py）
  - system_status / trade_logs / positions / risk_logs / dashboard テーブルを管理。
  - DB マイグレーション（カラム追加）を自動で行う仕組みあり。

- ポートフォリオ構築（portfolio/*）
  - 候補選定、等配分・スコア加重、リスク調整（セクターキャップ、レジーム乗数）、ポジションサイズ計算（ロット丸め等）。

- リサーチ（research/*）
  - DuckDB を用いたファクター計算（モメンタム／ボラティリティ／バリュー）。
  - 将来リターン計算、IC 計算、統計サマリー等の分析ユーティリティ。

- AI モジュール（ai/*）
  - ニュースのセンチメントスコアリング（OpenAI を使用、api_key 必須）。
  - マクロニュース + ETF MA200 を使った市場レジーム判定（LLM と組み合わせて判定、結果を DB に保存）。

- 運用ユーティリティ（utils/*）
  - ロギング設定（stdout + 日次ローテーションファイル）。
  - プロセス優先度・CPU affinity 設定（Windows / POSIX を透過）。
  - .env 自動読み込み・Settings（環境変数ラッパー）。


環境変数（主要）
----------------
- 必須（実行前に設定する）
  - JQUANTS_REFRESH_TOKEN — J-Quants API リフレッシュトークン
  - KABU_API_PASSWORD — kabuステーション API パスワード

- 実行環境
  - KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）

- データベース・ファイルパス
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
  - PID_FILE_PATH — Execution の pid ファイル（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH — Kill Switch の flag ファイル（デフォルト: data/kill.flag）

- Paper Trading 固有
  - PAPER_FILL_MODE — MockBroker の fill モード（instant | partial | never | reject。デフォルト instant）

- ロギング・運用
  - LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
  - LOG_DIR — ログファイル出力先（デフォルト logs/）
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動で消す (0|1, デフォルト 0)

- AI
  - OPENAI_API_KEY — OpenAI API キー（ai モジュールを使う場合に必要）

- Monitoring
  - MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、デフォルト 60）

注: .env / .env.local がプロジェクトルートに存在すれば自動で読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により無効化可能）。自動ロードは OS 環境変数を上書きしない仕様です。

セットアップ手順（ローカル開発向け）
-------------------------------
1. リポジトリをクローン／配置
2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 依存パッケージをインストール
   - requirements.txt がある場合: pip install -r requirements.txt
   - 本コードで想定される主なパッケージ:
     - duckdb, psutil, openai, pyyaml（config 検証で必要）
4. .env を作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - あるいは手動で project_root/.env を作成（.env.example を参照）
5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 警告をエラー扱いにする場合:
     - python -m kabusys.validate_config --strict
6. データディレクトリ作成（必要なら）
   - mkdir -p data logs

起動・使い方
------------

- ExecutionEngine（発注実行）を起動
  - 基本（環境変数を適切に設定していること）
    - python -m kabusys.run_execution
  - Paper Trading（KABUSYS_ENV=paper_trading）:
    - export KABUSYS_ENV=paper_trading
    - python -m kabusys.run_execution
    - Paper トレード時は専用 DB（PAPER_TRADING_SQLITE_PATH）が使われ、本番 DB と分離されます。

  - 停止：
    - プロセスは data/stop_requested.flag の存在を監視します（起動前に既に存在する場合は起動しません）。
    - Kill Switch（監視プロセス等）により data/kill.flag が書き込まれると Execution による継続動作が抑止されます（Settings.kill_flag_clear_on_start に依る自動クリア設定あり）。

- Monitoring（監視ループ）を起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL でポーリング間隔を変更できます（秒; デフォルト 60）。
  - 監視は常に本番用 sqlite_path を使用します（環境に関係なく monitoring DB に書き込み）。

- Paper Trading 検証レポート生成ツール
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH または環境変数 PAPER_TRADING_SQLITE_PATH を使用

- .env ウィザード
  - python -m kabusys.config_setup
  - 対話式に .env を生成・更新できます。

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い（exit 1）になります。

運用上の注意
------------
- ログ: logs/<app_name>.log に日次ローテーションで出力されます（デフォルト 30 日保持）。stdout も同時に出力されます。
- プロセス優先度: 起動スクリプトは最初に set_process_priority("high") を呼びますが、権限不足などで設定できない場合は警告に留まります。
- Kill / Stop:
  - 一時停止や停止用に data/stop_requested.flag（監視・実行ループ両方で参照）と data/kill.flag（KillSwitch 用）があります。
  - kill.flag は KillSwitch.evaluate のトリガ条件（ドローダウン・ポジション上限など）で書き込まれます。clear() で削除可能。
- AI 機能: OPENAI_API_KEY が必須。API エラー時はフェイルセーフでスコア算出をスキップまたは中立値を使います（例: macro_sentiment=0.0）。

主要コマンドまとめ
-----------------
- .env 生成: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config [--strict]
- Execution 起動: python -m kabusys.run_execution
- Monitoring 起動: python -m kabusys.run_monitoring
- Paper 検証レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

ディレクトリ構成（主要ファイル）
-------------------------------
（src/kabusys 以下の主要モジュールを抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings ラッパー（.env 自動ロード含む）
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring ポーリングループ起動スクリプト

  - ai/
    - news_nlp.py            — ニュース NLP（OpenAI）で ai_scores を生成
    - regime_detector.py     — レジーム判定（MA200 + マクロニュース + LLM）

  - monitoring/
    - monitoring_db.py       — SQLite 永続化層（system_status, trade_logs, ...）
    - system_monitor.py      — システム監視（CPU/メモリ/ディスク、データ鮮度）
    - risk_monitor.py        — ドローダウン / ポジション数監視
    - trade_monitor.py       — （注文周りの監視: ファイルに登場するが概要参照）
    - monitoring_engine.py   — 複数 Monitor を束ねるエンジン
    - kill_switch.py         — kill.flag の書き込み・判定
    - alert_manager.py       — （アラート送信管理）

  - execution/
    - execution_engine.py    — 実行エンジン本体（EngineConfig, run_session 等）
    - broker_factory.py      — ブローカークライアント生成
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py

  - portfolio/
    - portfolio_builder.py   — 候補選定・重み計算
    - position_sizing.py     — 株数計算・スケールダウン・ロット丸め
    - risk_adjustment.py     — セクターキャップ・レジーム乗数

  - research/
    - factor_research.py     — momentum/value/volatility 等のファクター計算
    - feature_exploration.py — 将来リターン / IC / 統計サマリー

  - data/                    — データ処理パイプライン（prices_daily 等の読み出しユーティリティ）
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成スクリプト

  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity

補足
----
- この README はコードベースに含まれる docstring／コメントを基に要約しています。実行前に python -m kabusys.validate_config で環境設定の整合性を確認してください。
- 実行環境（特に本番: KABUSYS_ENV=live）では kill_flag や LINE 通知設定など運用保護機構の確認を必ず行ってください。
- OpenAI を用いる機能を有効にする場合は API キーの管理・請求・使用制限に注意してください。

問題・改善提案・追加ドキュメントの要望があれば教えてください。必要に応じて README にサンプル .env、起動手順の詳細（systemd / docker / supervisor 用の例）などを追加します。