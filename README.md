README
======

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤を想定した Python パッケージです。本リポジトリは次の機能群を含みます:

- 実行エンジン起動スクリプト（ExecutionEngine）
- 監視（Monitoring）ループ（System / Trade / Risk）
- ペーパートレード向け分離 DB と検証レポート生成ツール
- ファクター計算や特徴量探索の研究用モジュール（DuckDB ベース）
- ニュースの LLM（OpenAI）によるセンチメント評価・レジーム判定モジュール
- 環境設定ウィザード・設定検証ツール
- ログ設定・プロセス優先度ユーティリティ 等

目標は「実運用を意識した自動売買プラットフォームのコア部」を提供することです。設計上、DB の永続化や外部 API 呼び出しは明示的に分離・抽象化されています。

主な機能一覧
--------------
- 実行エンジン起動 (src/kabusys/run_execution.py)
  - KABUSYS_ENV に応じて本番/ペーパートレードを切り替え
  - ブローカークライアントのファクトリを用いた依存注入
  - ExecutionEngine をスレッドで実行し、停止フラグで安全に終了

- 監視ループ起動 (src/kabusys/run_monitoring.py)
  - SystemMonitor / TradeMonitor / RiskMonitor を定期実行
  - MONITOR_POLL_INTERVAL でポーリング間隔を設定可能（デフォルト 60 秒）
  - stop_requested.flag によりループ終了

- 監視永続化層 (src/kabusys/monitoring/monitoring_db.py)
  - system_status / trade_logs / positions / risk_logs / dashboard テーブルを管理
  - マイグレーション（カラム追加）を起動時に自動適用

- Kill Switch（監視 → Execution 停止フラグ） (src/kabusys/monitoring/kill_switch.py)
  - 条件に応じて data/kill.flag を書き込み、ExecutionEngine に停止指示

- Risk / Position / Sector 制御（portfolio/*）
  - 候補選定、重み計算、ポジションサイズ算出、セクター上限適用など純粋関数群

- 研究用ファクター計算（research/*）
  - モメンタム、ボラティリティ、バリュー、将来リターン、IC 計算など（DuckDB 接続を受ける）

- ニュース NLP（ai/news_nlp.py）・レジーム判定（ai/regime_detector.py）
  - OpenAI API（デフォルト gpt-4o-mini）でニュースをスコア化し ai_scores に保存
  - マクロ記事 + ETF MA200 乖離を組み合わせて日次レジームを判定

- ツール
  - 環境設定ウィザード: python -m kabusys.config_setup（.env を生成/更新）
  - 設定検証: python -m kabusys.validate_config（起動前チェック）
  - ペーパートレード検証レポート: python -m kabusys.tools.paper_verification_report

セットアップ手順
-----------------
1. Python と仮想環境
   - Python 3.9+ を推奨
   - 仮想環境を作る: python -m venv .venv
   - アクティベート:
     - macOS / Linux: source .venv/bin/activate
     - Windows (PowerShell): .venv\Scripts\Activate.ps1

2. 依存ライブラリのインストール
   - requirements.txt がある場合:
       pip install -r requirements.txt
   - 主要ライブラリ（手動インストール例）:
       pip install duckdb psutil openai
   - 研究・設定検証で YAML を使う場合:
       pip install pyyaml

3. 環境変数の準備（.env）
   - 対話式ウィザードを使うと簡単です:
       python -m kabusys.config_setup
   - 必須項目:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 主要な環境変数（省略可 / デフォルトあり）:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト development）
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用）
     - LOG_LEVEL: INFO|DEBUG|...
     - OPENAI_API_KEY: OpenAI を使う場合に必要
     - PAPER_FILL_MODE: instant|partial|never|reject（ペーパー埋め方）
     - KILL_FLAG_CLEAR_ON_START: 0|1（起動時に kill.flag を自動クリアするか）

   - 自動ロード:
     - プロジェクトルートに .env または .env.local があると自動でロードされます。
     - 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

4. 設定検証
   - 作成した .env と config/*.yaml（存在する場合）を検証:
       python -m kabusys.validate_config
   - --strict オプションで警告も失敗扱いにできます。

5. ディレクトリ権限 / data ディレクトリ
   - 実行時に data/ や logs/ を自動作成するため、実行ユーザーに書き込み権限が必要です。

使い方（主要コマンド）
---------------------

- 実行エンジン起動（ExecutionEngine）
  - 通常起動:
      python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い paper_trading DB（PAPER_TRADING_SQLITE_PATH）へ記録
    - 起動時に data/stop_requested.flag があると起動せず終了
    - 実行中は data/execution.pid に PID を書きます
    - 停止は data/stop_requested.flag を作成するか、監視側の kill.flag を書くと ExecutionEngine が停止します

- 監視ループ起動（Monitoring）
    python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可（デフォルト 60 秒）
  - 監視は Settings に従い本番 sqlite_path を使用（Monitoring の DB は環境に依らず本番監視 DB を利用）
  - 停止はプロジェクトルート/data/stop_requested.flag を作成することでループ終了

- 環境設定ウィザード
    python -m kabusys.config_setup
  - .env の生成・更新を対話式で行います

- 設定検証
    python -m kabusys.validate_config
    python -m kabusys.validate_config --strict

- ペーパートレード検証レポート
    python -m kabusys.tools.paper_verification_report
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB のパスは環境変数 PAPER_TRADING_SQLITE_PATH または --db オプションで指定

- 研究用関数（Python 呼び出し例）
  - DuckDB 接続を渡してファクター計算:
      from kabusys.research import calc_momentum
      import duckdb
      conn = duckdb.connect("data/kabusys.duckdb")
      recs = calc_momentum(conn, date(2026,4,1))

注意事項 / 実運用上のポイント
--------------------------------
- DB 分離
  - 実行エンジンは paper_trading の場合は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を使用し、本番 DB と分離します。
  - 監視は常に sqlite_path（本番監視 DB）を使用します。

- Kill Switch / stop flag
  - 監視が条件を満たすと data/kill.flag を書き込み、ExecutionEngine はそれを確認して安全に停止します。
  - ExecutionEngine の停止は stop_requested.flag（監視とランナー間のローカル停止指令）でも可能です。
  - KILL_FLAG_CLEAR_ON_START=1 を本番で設定すると危険（推奨は 0）。

- ログ
  - デフォルト logs/ ディレクトリに日次ローテーションでログを出力します（TimedRotatingFileHandler）。
  - LOG_DIR, LOG_LEVEL 環境変数で制御可能。

- 権限
  - process priority 設定には OS の権限制約があり、失敗すると警告が出ます（スキップして続行）。

- LLM 関連
  - OpenAI API を使用する機能（news_nlp, regime_detector）は OPENAI_API_KEY が必要
  - API 失敗時はフェイルセーフ（ゼロスコアやスキップ）で継続する設計です
  - 実行時に API コストとレート制限を考慮してください

- マイグレーション
  - monitoring_db.init_monitoring_db() は起動時に必要テーブルを作成し、必要に応じてカラム追加を行います（冪等）。

ディレクトリ構成（抜粋）
-----------------------
以下は主要なファイル・ディレクトリの構成（src/kabusys 配下）です:

- src/kabusys/
  - __init__.py
  - config.py                  — 環境変数 / Settings 管理（自動 .env ロード含む）
  - config_setup.py            — .env 対話式ウィザード
  - validate_config.py         — 起動前設定検証 CLI
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — Monitoring ループ起動スクリプト

  - ai/
    - news_nlp.py              — ニュースセンチメントスコア算出（OpenAI）
    - regime_detector.py       — 市場レジーム判定（ETF + マクロセンチメント）
  - monitoring/
    - monitoring_db.py         — SQLite 永続化層（system_status 等）
    - system_monitor.py        — システム状態 / データ鮮度チェック
    - risk_monitor.py          — ドローダウン / ポジション監視
    - trade_monitor.py         — （発注監視/遅延/異常検出、実装参照）
    - kill_switch.py           — kill.flag 管理
    - monitoring_engine.py     — 各 Monitor を束ねるエンジン
    - alert_manager.py         — （LINE 通知等の抽象化、実装参照）

  - execution/                 — Execution エンジン関連（OrderManager 等）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py         — ログ初期化ユーティリティ
    - process_priority.py      — プロセス優先度 / CPU affinity 設定
  - data/                      — デフォルトの DB/log/pid/flag を置く想定ディレクトリ（実行時作成）

補足: ファイル / フラグ
- data/execution.pid: ExecutionEngine が起動時に書き込む PID ファイル
- data/stop_requested.flag: 手動停止要求（run_monitoring/run_execution が参照）
- data/kill.flag: 監視からの Kill Switch 信号（ExecutionEngine による検出で停止）

開発者向け
----------
- テストや CI では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動 .env ロードを無効化できます。
- OpenAI 呼び出しは _call_openai_api をモックすることでテスト可能に設計されています。
- DuckDB 接続を受け取る関数は副作用を持たない純粋関数群として実装されているため、ユニットテストが容易です。

ライセンス / バージョン
-----------------------
- パッケージバージョン: kabusys.__version__ = "0.1.0"
- ライセンス情報はリポジトリのルート (LICENSE) を参照してください（存在する場合）。

以上がこのコードベースの README（日本語）です。必要があれば「導入手順の簡略化（例: systemd ユニット、Docker Compose 設定）」「各モジュールの詳細な API ドキュメント（関数引数・戻り値）」などを追加できます。どの情報を優先して追記しますか？