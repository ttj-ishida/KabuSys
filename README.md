README
======

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤です。本リポジトリには以下の主要コンポーネントが含まれます。

- 実行エンジン起動スクリプト（ExecutionEngine 起動）
- 監視（Monitoring）コンポーネントとポーリングループ
- ポートフォリオ構築（候補選定・重み付け・株数決定）
- リサーチ用ファクター計算（DuckDB を利用）
- ニュース NLP（OpenAI を使ったセンチメント評価）
- ユーティリティ（プロセス優先度設定、設定ウィザード、設定検証、レポート生成 等）

主要な設計方針として、発注ロジックとデータ処理（DuckDB）を分離し、Paper Trading モードでは本番 DB と分離して安全に検証できるようになっています。

機能一覧
--------
- 実行（Execution）:
  - ExecutionEngine の起動 / 停止管理（stop フラグ・PID ファイル）
  - Paper Trading モード対応（モックブローカー・専用 SQLite）
  - リスク管理（注文レート制限・資金配分等の調整）

- 監視（Monitoring）:
  - システム状態監視（CPU/メモリ/ディスク、実行プロセスの生存、データ鮮度）
  - 注文監視（滞留注文・約定価格異常）
  - リスク監視（ドローダウン・ポジション上限監視）
  - Kill Switch（条件を満たすと data/kill.flag を書き込み、ExecutionEngine を停止）

- リサーチ / ファクター:
  - Momentum / Volatility / Value 等のファクター計算（DuckDB を使用）
  - 将来リターン、IC（Information Coefficient）、統計サマリー

- AI（OpenAI 統合）:
  - ニュース記事の銘柄ごとのセンチメントスコアを生成して ai_scores に書き込む
  - マクロニュースと ETF の MA 乖離を組み合わせた市場レジーム判定

- ツール:
  - 設定ウィザード（.env の作成 / 更新）
  - 設定検証 CLI（必須環境変数・config/*.yaml 等を事前検証）
  - Paper Trading 検証レポート生成（期間指定で統計を集計）

セットアップ手順
--------------
前提
- Python 3.10 以上を推奨（コード内で新しい型記法を使用）
- SQLite（標準ライブラリに含まれる）
- DuckDB, psutil, openai, requests, PyYAML（オプション）

例: 仮想環境の作成と必要パッケージのインストール
1. 仮想環境作成・有効化
   - macOS / Linux:
     python -m venv .venv
     source .venv/bin/activate
   - Windows (PowerShell):
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1

2. 必要パッケージをインストール（最低限）
   pip install duckdb psutil openai requests

   YAML 検証を行う場合:
   pip install pyyaml

プロジェクト設定 (.env)
- プロジェクトルートに .env を置くと自動で読み込まれます（デフォルトで .env → .env.local の順、OS 環境変数は保護されます）。
- 自動読み込みを抑制するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 主要な環境変数（例）:
  - JQUANTS_REFRESH_TOKEN (必須)
  - KABU_API_PASSWORD (必須)
  - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
  - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
  - SQLITE_PATH — 監視 DB: デフォルト data/monitoring.db （Monitoring は環境にかかわらず本番 sqlite_path を使用）
  - PAPER_TRADING_SQLITE_PATH — Paper Trading 用 DB: デフォルト data/paper_trading.db
  - PAPER_FILL_MODE — paper_trading 時の約定挙動: instant | partial | never | reject（デフォルト: instant）
  - LOG_LEVEL — DEBUG|INFO|WARNING|ERROR|CRITICAL
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — アラート通知用（任意）
  - OPENAI_API_KEY — OpenAI を使う機能で必要（nlp / regime 判定）

設定ウィザード / 検証
- 対話式に .env を作成・更新する:
  python -m kabusys.config_setup

- 設定検証（起動前チェック）:
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict  # 警告も FAIL 扱い

使い方
------
起動 / 停止関連
- ExecutionEngine を起動する:
  python -m kabusys.run_execution

  注意:
  - KABUSYS_ENV=paper_trading のときは MockBroker を使用し、data/paper_trading.db に記録します（本番 DB と分離）。
  - 起動時に data/stop_requested.flag が既に存在する場合はエンジンを起動しません。
  - 実行中は data/execution.pid（デフォルト）に PID を書きます。

- Monitoring（ポーリングループ）を起動する:
  python -m kabusys.run_monitoring

  環境変数:
  - MONITOR_POLL_INTERVAL — ポーリング間隔（秒）。デフォルト 60 秒。無効値（0 や負数）を与えるとデフォルトにフォールバックします。

停止 / Kill
- 実行エンジンを外部から停止させたい場合:
  - Kill Switch を発動させると data/kill.flag が書き込まれ（監視側で条件検出時）、ExecutionEngine が停止します。
  - 手動で停止する場合やテスト的に停止させたい場合は data/stop_requested.flag を作成すると run_execution/run_monitoring のループが検出して終了します。
- kill.flag をクリアする:
  rm data/kill.flag もしくは Monitoring モジュールの KillSwitch.clear() を呼ぶ（プログラム内処理）。

Paper Trading レポート
- Paper Trading の検証レポートを生成:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  オプション --db で SQLite ファイルを指定できます（環境変数 PAPER_TRADING_SQLITE_PATH でも指定可能）。

AI / レジーム関係（プログラム的利用）
- ニュースセンチメントスコア:
  - 関数: kabusys.ai.score_news(conn, target_date, api_key=None)
  - DuckDB 接続（duckdb.connect(...））と target_date（日付）を渡します。api_key は OPENAI_API_KEY を上書きできます。

- 市場レジーム判定:
  - 関数: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

ライブラリ的利用
- ポートフォリオ作成 API（純粋関数で副作用なし）:
  - select_candidates, calc_equal_weights, calc_score_weights
  - calc_position_sizes
  - apply_sector_cap, calc_regime_multiplier

監視 DB（自動マイグレーション）
- monitoring_db.init_monitoring_db(conn) は必要なテーブルを冪等に作成します（system_status, trade_logs, positions, risk_logs, dashboard 等）。
- 旧スキーマからの簡易マイグレーション処理（カラム追加）も組み込まれています。

よく使うコマンドまとめ
- 環境設定ウィザード:
  python -m kabusys.config_setup

- 設定検証:
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- ExecutionEngine 起動:
  python -m kabusys.run_execution

  Paper Trading で起動する例:
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- Monitoring 起動:
  python -m kabusys.run_monitoring
  例: MONITOR_POLL_INTERVAL=120 python -m kabusys.run_monitoring

- Paper Trading レポート:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  または
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

ディレクトリ構成
----------------
（主要ファイルを抜粋）

src/
  kabusys/
    __init__.py
    config.py                # 環境変数読み込み・Settings クラス
    config_setup.py          # .env 対話式ウィザード
    validate_config.py       # 設定検証 CLI
    run_execution.py         # ExecutionEngine 起動スクリプト
    run_monitoring.py        # Monitoring ポーリング起動スクリプト

    ai/
      __init__.py
      news_nlp.py            # ニュースセンチメント（OpenAI 統合）
      regime_detector.py     # レジーム判定（MA + マクロセンチメント）

    monitoring/
      monitoring_db.py       # SQLite 永続化層 + MonitoringDB クラス
      system_monitor.py      # システム・データ鮮度監視
      trade_monitor.py       # 注文滞留・約定異常監視
      risk_monitor.py        # ドローダウン・ポジション上限監視
      kill_switch.py         # Kill Switch ロジック（flag ファイル）
      monitoring_engine.py   # 各 Monitor を束ねるエンジン
      alert_manager.py       # LINE 通知用（requests）

    portfolio/
      portfolio_builder.py   # 候補選定・重み計算
      position_sizing.py     # 株数決定・スケーリング
      risk_adjustment.py     # セクターキャップ・レジーム乗数
      __init__.py

    research/
      factor_research.py     # Momentum / Volatility / Value 等
      feature_exploration.py # IC 等の統計解析
      __init__.py

    tools/
      __init__.py
      paper_verification_report.py  # Paper Trading 検証レポート生成

    utils/
      __init__.py
      process_priority.py    # psutil を使った優先度/affinity 設定

補足 / 注意点
-------------
- Monitoring は設定にかかわらず「本番用の sqlite_path」を使います（run_monitoring の実装上）。
- Paper Trading は paper_sqlite_path（デフォルト data/paper_trading.db）に完全分離して記録されます。
- OpenAI API を利用する機能を動かす場合は OPENAI_API_KEY の設定が必須です。API 呼び出しの失敗時は多くの箇所でフォールバック（スコア 0.0 など）する実装がありますが、結果精度のために正しい API キーとレート管理を行ってください。
- .env は機密情報を含むため絶対にリポジトリにコミットしないでください（config_setup.py のヘッダーに注意書きあり）。

問題報告 / 変更提案
------------------
- バグ報告や機能改善は Issue を作成してください。README の更新も歓迎します。

以上が本リポジトリの主要な使い方と構成です。必要に応じて各モジュールのドキュメントや docstring を参照してください。