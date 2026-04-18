README.md

KabuSys — 日本株自動売買システム（簡易ドキュメント）
==================================

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤の一部を実装した Python コードベースです。
主要な機能は「バックエンドの実行エンジン（ExecutionEngine）」「監視（Monitoring）」「ポートフォリオ構築」「ファクター計算／リサーチ」「ニュース NLP / レジーム判定」などです。  
DuckDB（分析用）と SQLite（監視 / 発注履歴用）を併用し、OpenAI での NLP 集約やローカルのペーパートレード動作もサポートします。

主な特徴 / 機能一覧
-----------------
- 実行エンジン（run_execution.py）
  - 実際のブローカーまたはモック（KABUSYS_ENV=paper_trading）での発注処理を行う
  - RiskManager / OrderManager / Reconciler 等の組み合わせによる発注制御
  - 起動時に PID ファイルを書き / 停止フラグ（data/stop_requested.flag）を監視して安全停止

- 監視（run_monitoring.py、monitoring/*）
  - システムリソース（CPU/メモリ/ディスク）、プロセス生存、データ鮮度のチェック
  - 注文ログ・リスクログ・ダッシュボード等の永続化（SQLite）
  - Kill Switch（閾値を超えたら data/kill.flag を書込んで Execution 停止）
  - MonitoringEngine によるポーリングループ

- ポートフォリオ構築（portfolio/*）
  - 候補選定、重み計算（等金額・スコア加重）、ポジションサイズ算出（lot 丸め、リスク制約）
  - セクター集中制限・レジーム乗数適用

- リサーチ / ファクター計算（research/*）
  - Momentum / Volatility / Value 等のファクター計算（DuckDB を利用）
  - 将来リターン計算、IC（Information Coefficient）などの解析ユーティリティ

- ニュース NLP / レジーム判定（ai/*）
  - raw_news を集約して OpenAI（gpt-4o-mini など）でセンチメント評価、ai_scores へ格納
  - ETF（1321）の MA200 とマクロニュースの LLM センチメントを合成して市場レジーム判定

- ユーティリティ
  - .env 対話式ウィザード（config_setup.py）
  - 起動前設定検証 CLI（validate_config.py）
  - ログ設定ユーティリティ（utils/logging_setup.py）
  - process priority / CPU affinity ヘルパ（utils/process_priority.py）
  - Paper Trading 検証レポート生成スクリプト（tools/paper_verification_report.py）

セットアップ手順
---------------
前提
- Python 3.10 以上（型注釈に PEP 604 の | 表記を使用）
- システムに duckdb, psutil, openai（OpenAI SDK）、および開発時に PyYAML（config 検証用）が必要です

1. レポジトリを取得
   - git clone ... などで取得

2. 仮想環境の作成と依存パッケージのインストール
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
   - pip install duckdb psutil openai
   - （開発用）pip install pyyaml

   ※ requirements.txt がある場合はそれを利用してください。

3. .env の初期生成（対話式ウィザード）
   - python -m kabusys.config_setup
   - ウィザードで J-Quants トークン、kabu API パスワード等を入力して .env を生成します。
   - .env は絶対に Git にコミットしないでください（ウィザードの注記あり）。

4. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗とみなして exit(1)

5. データ / ログディレクトリ
   - デフォルトでは data/ と logs/ を使います。必要に応じて .env の DUCKDB_PATH / SQLITE_PATH / LOG_DIR を変更してください。
   - monitoring / execution は起動時にデータベースファイルの親ディレクトリを作成しますが、権限等に注意してください。

環境変数（主なもの）
--------------------
- KABUSYS_ENV: 実行環境（development / paper_trading / live）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: SQLite 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- OPENAI_API_KEY: OpenAI API キー（ai モジュールで使用）
- PAPER_FILL_MODE: paper_trading の MockBroker の挙動（instant/partial/never/reject）

使い方（コマンド例）
------------------
- 環境ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 監視プロセス起動（ポーリングループ）
  - 環境変数でポーリング間隔を設定可能: MONITOR_POLL_INTERVAL（秒、デフォルト 60）
  - python -m kabusys.run_monitoring
  - 実行中は data/stop_requested.flag を作成するとループを終了して停止できます

- 実行エンジン起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 DB に記録します
  - エンジンは data/stop_requested.flag を検知すると停止します
  - 実行は内部でデーモンスレッドを起動し、PID は data/execution.pid に書き込まれます

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション: --from YYYY-MM-DD --to YYYY-MM-DD --db PATH

- ライブラリ的な利用
  - ai.score_news / ai.regime_detector.score_regime などはプログラム内から DuckDB 接続を渡して呼び出せます
  - portfolio.calc_position_sizes 等は純粋関数群なのでユニットテストやシミュレーションで直接利用可能

運用に関する注意
----------------
- 監視（monitoring）は監視用 SQLite DB（デフォルト data/monitoring.db）へ書き込みます。monitoring は KABUSYS_ENV に関係なく本番 sqlite_path を使用します。
- ペーパートレード（paper_trading）は本番 DB と分離するため専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使います。
- Kill Switch:
  - RiskMonitor が閾値を満たすと KillSwitch が data/kill.flag を作成します。ExecutionEngine は起動時/稼働中に kill.flag の存在をチェックして安全停止できます（設定次第）。
  - 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると自動クリアされますが、本番では推奨されません。
- ロギング:
  - setup_logging(app_name=...) を各スクリプトで呼んでおり、デフォルトで logs/<app_name>.log（日次ローテーション、30日保持）と stdout に出力します。
- 権限・優先度:
  - 起動スクリプトは set_process_priority("high") を呼びますが、権限不足で失敗することがあります（警告ログに留まります）。

主要ディレクトリ構成
-------------------
（src/kabusys 以下を簡易表示）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理（.env 自動ロード）
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト

  - ai/
    - news_nlp.py            — ニュースの OpenAI スコアリング
    - regime_detector.py     — 市場レジーム判定

  - monitoring/
    - monitoring_db.py       — SQLite のスキーマ定義 / DB ラッパー
    - system_monitor.py      — システム・データ鮮度監視
    - trade_monitor.py       — （注文周りの監視ロジック）
    - risk_monitor.py        — ドローダウン / ポジション上限監視
    - kill_switch.py         — kill.flag 書込みユーティリティ
    - monitoring_engine.py   — 各 Monitor をまとめる

  - portfolio/
    - portfolio_builder.py   — 候補選定 / 重み付け
    - position_sizing.py     — 発注株数計算（単元丸め・スケールダウン）
    - risk_adjustment.py     — セクターキャップ・レジーム乗数
    - __init__.py

  - research/
    - factor_research.py     — Momentum / Value / Volatility 等の計算（DuckDB）
    - feature_exploration.py — 将来リターン / IC /統計サマリ
    - __init__.py

  - utils/
    - logging_setup.py       — ログ設定ヘルパ
    - process_priority.py    — プロセス優先度 / CPU affinity
    - __init__.py

  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成

- config/
  - system_config.yaml, strategy_config.yaml, ...（ランタイム用設定ファイル、テンプレ生成あり）

- data/
  - （デフォルト DB やフラグファイル: monitoring.db, paper_trading.db, stop_requested.flag, kill.flag, execution.pid など）

- logs/
  - （ログファイル出力先）

補足（開発 / テスト）
--------------------
- .env 読み込みは自動で行われますが、テストや特殊用途で無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- YAML の構文チェックは PyYAML がインストールされている場合のみ行われます（validate_config.py）。
- OpenAI API 呼び出し箇所はリトライ／フォールバック処理を含みますが、API キー未設定時は例外を投げます。CI 等で実行する際はキーを設定しないか、該当処理をモックしてください。

以上がこのコードベースの概要と基本的な使い方です。詳細な API（関数引数や挙動）は各モジュールの docstring を参照してください。必要であれば、特定モジュールの詳しい説明や起動スクリプトのユースケース例（systemd / cron / Docker での運用案など）も作成します。