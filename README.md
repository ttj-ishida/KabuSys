KabuSys — 日本株自動売買システム
===============================

このリポジトリは日本株向けの自動売買／リサーチ基盤（KabuSys）の主要モジュール群を含みます。
以下はコードベースの使い方、セットアップ手順、主要機能の概要です。

プロジェクト概要
----------------
KabuSys は以下の責務を持つコンポーネント群から構成されています。

- ExecutionEngine: 発注／注文管理／リスク管理を行うエンジン（本番 / ペーパートレード対応）
- Monitoring: システム稼働状況・注文ログ・リスク指標を定期的にチェックし、アラート・Kill Switch を制御
- Research / Factors: DuckDB の価格データを使ったファクター計算、特徴量解析
- AI モジュール: ニュースセンチメント（OpenAI）によるスコアリング、レジーム判定
- Tools: ペーパートレードの検証レポート生成などのユーティリティ
- 設定ユーティリティ: .env ウィザードと起動前設定検証 CLI

主な機能一覧
-------------
- 実行エンジン（run_execution）:
  - live / paper_trading / development 環境対応
  - リスク管理（ポジション上限・ドローダウン等）
  - 注文履歴の永続化（SQLite）、分析用 DuckDB 出力
- 監視（run_monitoring）:
  - CPU / メモリ / ディスク、プロセス生存チェック、データ鮮度チェック
  - トレード／リスク監視、Kill Switch 書き込み（data/kill.flag）
  - ポーリング間隔は環境変数で上書き可能
- 研究用（research）:
  - モメンタム、ボラティリティ、バリュー等のファクター計算（DuckDB）
  - フォワードリターン計算、IC（Information Coefficient）等の評価指標
- AI（ai）:
  - ニュースのセンチメントを OpenAI（gpt-4o-mini）で解析して ai_scores に保存
  - マーケットレジーム判定（ETF ma200 乖離 + マクロセンチメント）
- ポートフォリオ構築（portfolio）:
  - 候補選定、等金額／スコア加重配分、リスク調整、ポジションサイズ計算
- ツール:
  - paper_verification_report: ペーパートレード DB を集計して PASS/FAIL レポートを表示
- 設定支援:
  - config_setup: 対話式に .env を作成
  - validate_config: .env や config/*.yaml の事前検証

必要条件（主要パッケージ）
--------------------------
※プロジェクトに requirements.txt は含まれていない場合があります。下記は主要依存の例です。

- Python 3.9+
- duckdb
- psutil
- openai
- pyyaml （config YAML 検証時に任意）
- （標準ライブラリ: sqlite3 等）

セットアップ手順
----------------

1. リポジトリをクローンし、仮想環境を作成
   - git clone ...
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb psutil openai pyyaml

   （プロジェクトで requirements.txt を用意している場合は pip install -r requirements.txt を使用）

3. .env の作成（対話式ウィザード）
   - python -m kabusys.config_setup
   - ウィザードは J-Quants のトークンや kabuAPI パスワード、KABUSYS_ENV、DB パスなどを設定します。
   - 生成された .env は絶対に Git にコミットしないでください。

4. 設定の検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります:
     python -m kabusys.validate_config --strict

5. データディレクトリ等の準備
   - デフォルトの DB/ログパスは data/、logs/ 下です。必要に応じて手動で作成してください。logging setup は自動でディレクトリを作成しようとしますが、権限等で失敗する場合があります。

主要環境変数（抜粋）
-------------------
- KABUSYS_ENV: 実行環境 (development | paper_trading | live)
  - paper_trading の場合、Execution は MockBrokerClient を使用し PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録します
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（ai.news_nlp / regime_detector を使う際に必要）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL / LOG_DIR: ログ出力設定
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒。デフォルト 60）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START: 監視／停止制御関連

使い方（起動方法）
-----------------

- ExecutionEngine（トレードエンジン）起動
  - python -m kabusys.run_execution
  - 実行前に KABUSYS_ENV を .env で設定しておくこと
  - paper_trading の場合、本番 DB と分離されたペーパートレード DB を使用します

- Monitoring（監視ループ）起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更するには環境変数 MONITOR_POLL_INTERVAL を設定（秒）
    例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視は常に本番の sqlite_path を参照する（KABUSYS_ENV に依らず）

- 設定検証（起動前チェック）
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱いになります

- .env ウィザード
  - python -m kabusys.config_setup

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を明示する場合:
    - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

停止方法 / Kill Switch
----------------------
- 手動停止フラグ:
  - run_execution / run_monitoring ではプロジェクトルート下の data/stop_requested.flag を監視し、存在すると安全に終了します。
- Kill Switch:
  - 監視モジュール（KillSwitch）は data/kill.flag を書き込むことで ExecutionEngine に停止シグナルを送ります。KillSwitch はドローダウンやポジション上限などの条件で発動します。
  - kill.flag は Settings.kill_flag_clear_on_start が 1 の場合に起動時自動クリアされる可能性があるため、本番では通常 0 を推奨します。

ログ
---
- 共通ログ設定は kabusys.utils.logging_setup.setup_logging で行います。
- デフォルト出力先:
  - 標準出力（stdout）
  - 日次ローテートファイル: logs/<app_name>.log（30日分保持）
- LOG_LEVEL, LOG_DIR 環境変数でカスタマイズ可能

AI 機能（注意点）
----------------
- news_nlp / regime_detector は OpenAI API（gpt-4o-mini 等）を使用します。実行には OPENAI_API_KEY が必要です。
- API 呼び出しはリトライやフォールバックロジックを持ちますが、APIキー未設定時は例外を送出します。
- モジュールはルックアヘッドバイアスを避けるために日付参照ルールを厳格に実装しています（target_date を明示的に渡す設計）。

ペーパートレード挙動
-------------------
- KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して発注をシミュレートし、ペーパートレード専用の SQLite DB（PAPER_TRADING_SQLITE_PATH）に記録します。
- PAPER_FILL_MODE により約定モデルを制御できます（instant / partial / never / reject）。

開発用ヒント / トラブルシュート
---------------------------
- .env の自動ロードはデフォルトで有効です。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト等で使用）。
- PyYAML がないと config/*.yaml の内容検証はスキップされます（validate_config が警告を出します）。
- DuckDB / SQLite のファイルパスが存在しない親ディレクトリの場合、起動時に自動作成されることがありますが、権限等で失敗した場合はエラーになります。事前に data/ や logs/ を作成しておくと確実です。
- psutil の権限によっては process priority / cpu affinity の設定が失敗します（警告になりスキップされます）。

ディレクトリ構成（主要ファイル）
--------------------------------
(以下は src/kabusys 以下の主要モジュール一覧の抜粋)

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定の読み込み
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - execution/               — 発注エンジン関連（Engine, OrderManager 等）
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - data/                    — （想定）データパイプライン・DuckDB 用コード
  - ai/
    - news_nlp.py
    - regime_detector.py

（プロジェクトルートには data/、logs/、config/、pyproject.toml などが存在する想定です。）

ライセンス・貢献
----------------
本 README ではライセンス情報は含まれていません。実際の運用・公開時には LICENSE ファイルを追加してください。
プルリクやバグ報告は GitHub のリポジトリ管理ポリシーに従ってください。

補足：よく使うコマンド例
-----------------------
- .env 作成: python -m kabusys.config_setup
- 設定確認: python -m kabusys.validate_config
- エンジン起動: python -m kabusys.run_execution
- 監視起動: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- ペーパーレポート: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

以上がこのコードベースの概要と基本的な使い方です。追加で README に記載したい具体的な設定例やコマンド（例: .env テンプレート、systemd ユニットファイル、docker-compose 設定など）があれば教えてください。必要に応じて追記します。