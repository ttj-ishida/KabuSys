KabuSys
=======

日本株自動売買システム（KabuSys）の実装リポジトリ。  
この README はコードベースに含まれる主要モジュールの概要、機能、セットアップ手順、利用方法、ディレクトリ構成を日本語でまとめたものです。

プロジェクト概要
--------------
KabuSys は日本株向けの自動売買プラットフォームのコア部分を実装したライブラリ／スクリプト群です。主な責務は次の通りです。

- ExecutionEngine：発注（実口座／ペーパートレード）の実行管理
- Monitoring：システム状態・取引状況・リスク監視、必要時に Kill Switch を発動
- Research：DuckDB 上の価格・財務データを使ったファクター計算・特徴量解析
- Portfolio：銘柄選定、重み付け、ポジションサイズ計算（等分／スコア加重／リスクベース）
- AI モジュール：ニュースを LLM で評価して銘柄スコアや市場レジーム判定を行う（OpenAI）
- ユーティリティ：ログ設定、プロセス優先度設定、設定読み込みウィザード、設定検証ツール 等

機能一覧
--------
主要な機能・モジュール（抜粋）：

- 実行（run_execution.py）
  - 実口座 / ペーパートレード（KABUSYS_ENV=paper_trading で MockBroker を使用）
  - ペーパートレードは data/paper_trading.db に記録して本番 DB と分離
  - ExecutionEngine をデーモン的に起動し、停止フラグで終了可能
- 監視（run_monitoring.py, monitoring/*）
  - SystemMonitor: CPU/メモリ/ディスク/プロセス監視、データ鮮度チェック
  - TradeMonitor: 発注ログの監視（滞留・約定異常など）
  - RiskMonitor: ドローダウン／ポジション上限監視、ダッシュボード更新・リスクログ
  - MonitoringEngine: 各モニタをまとめポーリング。KillSwitch による停止信号の発行
  - MonitoringDB: SQLite に監視ログを永続化（テーブル作成・マイグレーションを含む）
- AI（kabusys.ai）
  - news_nlp.score_news: ニュース記事を集約して OpenAI に投げ、銘柄ごとに -1..1 のスコアを ai_scores に書き込み
  - regime_detector.score_regime: ETF(1321) の MA とマクロニュースの LLM スコアを合成して market_regime を算出・永続化
- Research（kabusys.research）
  - calc_momentum / calc_volatility / calc_value: DuckDB の prices_daily / raw_financials からファクターを計算
  - calc_forward_returns / calc_ic / factor_summary: 特徴量探索・IC 計算・統計要約
- Portfolio（kabusys.portfolio）
  - select_candidates, calc_equal_weights, calc_score_weights
  - calc_position_sizes: リスクベース・等分・スコアに基づく単元丸めを含む株数算出
  - apply_sector_cap, calc_regime_multiplier: セクターキャップ適用・レジームによる乗数
- 設定管理
  - config_setup.py: .env を対話的に作成/更新するウィザード
  - validate_config.py: 起動前に必要な環境変数や config/*.yaml を検証する CLI
  - config.Settings: 環境変数をラップした設定アクセス機能
- ツール
  - tools.paper_verification_report: ペーパートレード DB を解析して検証レポートを生成

セットアップ手順
----------------
以下は一般的な開発／運用環境のセットアップ手順の例です（requirements.txt はこの README に含まれていないため、プロジェクトの実際の依存ファイルに合わせてください）。

1. Python 環境
   - Python 3.10 以上を推奨（duckdb / 型指定の観点から）。プロジェクトに合わせて仮想環境を作成してください。
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存ライブラリをインストール
   - 代表的な依存:
     - duckdb
     - psutil
     - openai
     - PyYAML（config 検証でオプション）
   - 例:
     - pip install duckdb psutil openai PyYAML

3. .env の作成
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - 主要な必須環境変数（validate_config / Settings 参照）:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - OPENAI_API_KEY: AI 機能を使う場合は必須
   - DB / ログ関連の既定値:
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading モード用）
     - LOG_DIR: logs/
     - LOG_LEVEL: INFO（必要に応じて変更）

4. データディレクトリの準備
   - data/ および logs/ は自動的に作成されますが、権限等で作成に失敗する場合は手動で作成してください。

5. 設定検証（必須ではないが推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります。

使い方
------
主要な実行方法はモジュールを直接実行する方法です。各スクリプトは __main__ エントリポイントを持ちます。

- 実行エンジン（ExecutionEngine）起動:
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading のときは MockBrokerClient が使われ、data/paper_trading.db に記録されます。
  - 起動時に data/stop_requested.flag が存在すると起動せず終了します。
  - 実行中に stop フラグ（data/stop_requested.flag）や kill.flag（設定次第）で停止できます。
  - PID ファイル: data/execution.pid（Settings.pid_file_path で変更可能）

- 監視ループ起動:
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60）。
  - 監視は monitoring DB（Settings.sqlite_path）を使用。Monitoring は環境にかかわらず本番 sqlite_path を参照します（監視対象は本番 DB 側想定）。
  - 停止は data/stop_requested.flag の作成で検知します。

- 設定ウィザード:
  - python -m kabusys.config_setup
  - .env を対話式に作成/更新します。

- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ペーパートレード検証レポート:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パス指定:
    - --db /path/to/paper_trading.db
    - または環境変数 PAPER_TRADING_SQLITE_PATH を使用

- AI 機能（スクリプト経由 / ライブラリ呼び出し）
  - OpenAI の API キー（OPENAI_API_KEY）が必要です。
  - ニューススコア付与:
    - Python API: from kabusys.ai import score_news
      - score_news(conn, target_date, api_key=None)
    - 内部で gpt-4o-mini を使用。バッチ処理、リトライ・バリデーションを行い ai_scores テーブルに書き込みます。
  - レジーム判定:
    - regime_detector.score_regime(conn, target_date, api_key=None)

重要な環境変数（抜粋）
--------------------
- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 実行環境
  - KABUSYS_ENV: development | paper_trading | live
- DB / パス
  - DUCKDB_PATH (default: data/kabusys.duckdb)
  - SQLITE_PATH (default: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)
  - PID_FILE_PATH (default: data/execution.pid)
  - KILL_FLAG_PATH (default: data/kill.flag)
- ログ / 運用
  - LOG_LEVEL (default: INFO)
  - LOG_DIR (default: logs/)
  - MONITOR_POLL_INTERVAL (監視のポーリング間隔、秒、デフォルト 60)
  - KILL_FLAG_CLEAR_ON_START (0/1) — 本番で 1 は危険
- AI
  - OPENAI_API_KEY（AI 機能を使うために必須）
- Paper Trading 動作
  - PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）

ファイル/停止フラグ
------------------
- data/stop_requested.flag
  - run_execution / run_monitoring が停止判定に利用するフラグファイルの例（コードによりパス変数が定義されています）。
- data/kill.flag
  - KillSwitch が書き込むファイル。Production 環境での自動停止に使います。KILL_FLAG_CLEAR_ON_START に注意。

ログ
---
- ログは標準出力（stdout）と日次ローテーションされるファイル（logs/<app_name>.log）に出力されます。
- ログ設定は kabusys.utils.logging_setup.setup_logging を経由して統一的に行われます。
- LOG_DIR 環境変数でログ保存先を変更できます。

ディレクトリ構成
----------------
以下は src/kabusys 以下の主要ファイルとディレクトリの一覧（本リポジトリに含まれるファイルに基づく抜粋）です。

- src/kabusys/
  - __init__.py                     — パッケージ定義（__version__ 等）
  - config.py                        — Settings / .env 自動読み込みロジック
  - config_setup.py                  — .env 対話式ウィザード
  - validate_config.py               — 設定検証 CLI
  - run_execution.py                 — ExecutionEngine 起動スクリプト
  - run_monitoring.py                — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py   — ペーパートレード検証レポート生成ツール
  - ai/
    - news_nlp.py                    — ニュース NLP スコアリング（OpenAI 呼び出し）
    - regime_detector.py             — 市場レジーム判定
    - __init__.py
  - research/
    - factor_research.py             — ファクター計算（momentum/volatility/value）
    - feature_exploration.py          — 将来リターン・IC 等
    - __init__.py
  - portfolio/
    - portfolio_builder.py           — 候補選定・重み計算
    - position_sizing.py             — 株数決定・スケーリング・単元丸め
    - risk_adjustment.py             — セクターキャップ・レジーム乗数
    - __init__.py
  - monitoring/
    - monitoring_db.py               — SQLite 永続化層（テーブル作成・アクセス）
    - system_monitor.py              — システム状態・データ鮮度監視
    - trade_monitor.py               — 取引ログ監視（存在ファイルベースでの監視ロジックが入る想定）
    - risk_monitor.py                — ドローダウン・ポジション上限監視
    - kill_switch.py                 — kill.flag 書き込みロジック
    - monitoring_engine.py           — 各 Monitor を束ねるエンジン
    - alert_manager.py               —（アラート送信ラッパー、実装参照）
  - utils/
    - logging_setup.py               — ログ設定ユーティリティ
    - process_priority.py            — プロセス優先度 / CPU affinity 設定
    - __init__.py
  - execution/                       — Execution 関連（Engine・OrderManager 等。参照あり）
    - (実装ファイル群、エンジン/ブローカーファクトリ等)
  - monitoring/                      — 監視周り（上記）
  - data/ (プロジェクトルート)
    - *.db                           — 実際の DB ファイル（data/kabusys.duckdb、data/monitoring.db 等）
    - kill.flag / stop_requested.flag / execution.pid などのフラグ/PID ファイルが置かれる想定
  - config/                          — YAML コンフィグ（system_config.yaml などを置くディレクトリ）

開発者向け注意事項 / 運用上のポイント
------------------------------------
- .env は決して Git にコミットしないこと（config_setup にもその旨の注意書きがあります）。
- KABUSYS_ENV=live では本番影響がある設定（LINE トークン未設定、KILL_FLAG_CLEAR_ON_START=1 など）について validate_config が警告を出します。慎重に扱ってください。
- Monitoring は常に Settings.sqlite_path（本番監視 DB）を参照するため、監視対象 DB の切り替えには注意が必要です。
- Paper Trading は発注挙動を分離するため PAPER_TRADING_SQLITE_PATH を使います。実 DB と混同しないようにしてください。
- AI 機能を使う場合は OPENAI_API_KEY が必須。API 呼び出しはレート制限やエラーを考慮してリトライ・クリッピング等の保護ロジックが入っていますが、API 使用料やモデル変更には注意してください。

付録：よく使うコマンド例
-----------------------
- .env 作成
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- 実行エンジン起動（本番/ペーパートレードは KABUSYS_ENV で切り替え）
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- 監視エンジン起動
  - python -m kabusys.run_monitoring
- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

最後に
------
この README はリポジトリ内のソースコードに基づいて作成しています。実際の運用・デプロイ時は組織の運用ルール、API キー管理方針、テスト環境での十分な検証を行ってください。質問や補足があれば必要な箇所を指定していただければ追記します。