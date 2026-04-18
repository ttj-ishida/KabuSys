README — KabuSys
=================

概要
----
KabuSys は日本株向けの自動売買／リサーチ基盤です。価格・財務データの処理、ファクター計算、ポートフォリオ構築、発注実行（ExecutionEngine）、稼働監視（Monitoring）や AI を使ったニュースセンチメント評価などを備えたモジュール群で構成されています。

主な設計方針:
- DuckDB を分析用 DB、SQLite を監視・発注ログ用に使用（Paper Trading は専用 SQLite を使用して本番と分離）。
- 外部 API（例: OpenAI）は明示的に API キーを渡すか環境変数で設定。
- 起動スクリプトは python -m で実行できる CLI 形式。
- .env による設定を想定（自動ロード機能あり／テスト用に無効化可能）。

機能一覧
--------
- 環境設定ウィザード: kabusys.config_setup（.env の対話生成）
- 設定検証: kabusys.validate_config（.env / config/*.yaml のチェック）
- 発注実行エンジン: run_execution（本番 / ペーパートレード対応、ブローカ抽象化）
- 監視ループ: run_monitoring（システム状態・データ鮮度・トレード状態・リスク監視）
- モニタリング永続化: monitoring.monitoring_db（SQLite スキーマ・読み書き）
- Kill Switch: monitoring.kill_switch（ドローダウン等で kill.flag を書き込み Execution に停止シグナル）
- ポートフォリオ構築: portfolio パッケージ（候補選定・重み付け・ポジションサイズ計算・セクターキャップ）
- リサーチ: research（ファクター計算、将来リターン、IC など）
- AI モジュール: ai.news_nlp / ai.regime_detector（OpenAI を使ったニューススコアリング・市場レジーム判定）
- ツール: tools.paper_verification_report（Paper Trading の検証レポート生成）

前提条件 / 必要ライブラリ
------------------------
主な依存（プロジェクトに requirements.txt がない場合の例）:
- Python 3.9+
- duckdb
- psutil
- openai
- PyYAML（config YAML の検証を行う場合に必要）
これらは pip でインストールできます:
pip install duckdb psutil openai pyyaml

セットアップ手順
---------------
1. リポジトリのクローン・作業ディレクトリへ移動
   - git clone ... && cd <project>

2. 仮想環境（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージのインストール
   - pip install duckdb psutil openai pyyaml

4. データ/ログ用ディレクトリ作成（権限等に注意）
   - mkdir -p data logs

5. .env を作成（自動生成ウィザード推奨）
   - python -m kabusys.config_setup
     → 対話式に必要な環境変数を入力し .env を生成します。

6. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 問題があれば .env や config/*.yaml を修正します。
   - --strict を付けると警告も失敗扱いになります:
     python -m kabusys.validate_config --strict

環境変数（主要なもの）
--------------------
主な環境変数（.env に設定する想定）:
- JQUANTS_REFRESH_TOKEN: J-Quants API のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（ai モジュール使用時）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- KABUSYS_ENV: 実行環境（development | paper_trading | live）デフォルト: development
- LOG_LEVEL: ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、run_monitoring 用。デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動クリアするか（1: 自動クリア、0: クリアしない。live 環境では注意）

自動 .env 読み込み:
- 起動時にプロジェクトルート（.git または pyproject.toml を基準）を探して .env / .env.local を自動読み込みします。
- 自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト用途）。

使い方（起動サンプル）
--------------------

1) 環境作成・確認
- .env を用意後、設定検証:
  python -m kabusys.validate_config

2) ExecutionEngine（発注エンジン）起動
- 本番（KABUSYS_ENV=live）
  KABUSYS_ENV=live python -m kabusys.run_execution
- ペーパートレード（MockBroker を使用、DB を data/paper_trading.db に分離）
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution

仕様・挙動:
- 起動直後に process 優先度を high に設定します（psutil を使用）。
- ペーパートレード時は settings.paper_sqlite_path を使用して本番 DB と分離。
- 起動時に data/stop_requested.flag が存在するとエンジンは起動せず終了します。
- エンジンは data/execution.pid に PID を書きます（設定により変更可）。

停止:
- Kill Switch（監視側）や手動で data/kill.flag を書くと ExecutionEngine に停止シグナルが送られます。
- run_execution のループは停止フラグを検知して安全に停止します。

3) Monitoring（監視ループ）起動
- デフォルトポーリング 60 秒:
  python -m kabusys.run_monitoring
- ポーリング間隔を変更:
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

仕様・挙動:
- 監視は Settings.sqlite_path（環境にかかわらず本番 sqlite_path）を使用してログを残します。
- 停止: プロジェクトルート/data/stop_requested.flag を作成するとループが終了します。
- 監視モジュールは SystemMonitor / TradeMonitor / RiskMonitor を組み合わせ、KillSwitch と AlertManager を使って通知・停止判定を行います。

4) Paper Trading 検証レポート
- 過去期間のレポート生成:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- DB 指定:
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

5) AI / リサーチ呼び出し（スクリプトから利用）
- ai.score_news, ai.regime_detector.score_regime などは DuckDB 接続と target_date を渡して呼び出します。
- OpenAI API キーは引数で渡すか OPENAI_API_KEY 環境変数を利用します。

運用上のフラグとファイル
------------------------
- data/kill.flag: Kill Switch が書き込むファイル。存在すると ExecutionEngine 停止を指示。
- data/stop_requested.flag: run_monitoring / run_execution の外部制御用停止フラグ（ループの即時終了）。
- data/execution.pid: ExecutionEngine が起動時に書き込む PID ファイル（場所は Settings.pid_file_path）。

ディレクトリ構成（主要ファイル）
------------------------------
src/
  kabusys/
    __init__.py
    config.py                — 環境変数・設定読み込み
    config_setup.py          — .env 対話式ウィザード
    validate_config.py       — 設定検証 CLI
    run_execution.py         — ExecutionEngine 起動スクリプト
    run_monitoring.py        — SystemMonitor ポーリング起動スクリプト

    utils/
      logging_setup.py       — 統一的ログ設定ユーティリティ
      process_priority.py    — 優先度 / CPU affinity 設定ユーティリティ

    monitoring/
      monitoring_db.py       — 監視用 SQLite スキーマ・永続化 API
      monitoring_engine.py   — Monitor を束ねるポーリングエンジン
      system_monitor.py      — システム状態 / データ鮮度監視
      risk_monitor.py        — ドローダウン / ポジション数監視
      kill_switch.py         — kill.flag の書き込みと評価
      ...                    — TradeMonitor, alert_manager 等（ソース内に存在）

    execution/
      （発注エンジン・OrderManager 等の実装。ブローカーファクトリ経由で Mock/実ブローカを切替）

    portfolio/
      portfolio_builder.py   — 候補選定、等重/スコア重み
      position_sizing.py     — 株数決定・cap・スケール
      risk_adjustment.py     — セクターキャップ、レジーム乗数
      __init__.py

    research/
      factor_research.py     — Momentum / Volatility / Value 等のファクター計算
      feature_exploration.py — 将来リターン、IC、統計サマリー
      __init__.py

    ai/
      news_nlp.py            — ニュースを LLM でスコアリング
      regime_detector.py     — マクロ + MA200 を用いたレジーム判定
      __init__.py

    tools/
      paper_verification_report.py — Paper Trading の検証レポート生成
      __init__.py

data/           — 実行時に用いる DB / フラグファイル等（プロジェクトルート）
logs/           — ログファイル（デフォルト logs/<app_name>.log）

補足・注意点
--------------
- 本プロジェクトは「本番発注」を行う機能を含みます。KABUSYS_ENV=live 設定時は取り扱いに十分注意してください（validate_config は live 用ガードも用意）。
- .env は機密情報を含むため Git にはコミットしないでください。
- OpenAI 等外部 API 呼び出しは失敗時にフェイルセーフな動作を念頭に置いて設計されていますが、API キーやコスト管理は運用者側で行ってください。
- ログディレクトリ作成に失敗した場合はコンソール出力のみになります。必要があれば logs/ に書き込み権限を付与してください。

ライセンスや貢献方法についてはリポジトリのトップレベルドキュメント（LICENSE / CONTRIBUTING）をご参照ください（なければプロジェクト管理者へお問い合わせください）。

以上が README の概要です。README に追加したいコマンド例や運用手順（システムdユニット、cron 登録例、モニタリング通知先設定など）があれば追記します。