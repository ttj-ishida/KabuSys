README
======

概要
----
KabuSys は日本株向けの自動売買／リサーチ／監視ユーティリティ群をまとめた Python コードベースです。
主に以下の機能を持ちます。

- 注文実行エンジン（ExecutionEngine）とモニタリングループ
- 監視ログの永続化（SQLite）および分析用 DuckDB の利用
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ決定）
- リサーチ（ファクター計算、特徴量探索）
- AI を使ったニュースセンチメント評価・市場レジーム判定（OpenAI）
- ペーパートレード用の分離された DB とモックブローカーサポート
- 各種 CLI ツール（設定ウィザード、設定検証、ペーパー検証レポート 等）

各モジュールは「フェイルセーフ」「ルックアヘッドバイアス対策」「冪等性」に配慮して設計されています。

主な機能一覧
--------------
- Execution
  - 実際の発注またはペーパートレード（KABUSYS_ENV=paper_trading）での実行
  - リスク制御（RiskManager）・注文管理（OrderManager）・再整合（Reconciler）
- Monitoring
  - SystemMonitor：CPU / メモリ / ディスク、データ鮮度、PID 生存確認
  - TradeMonitor：滞留注文・約定異常価格の検出
  - RiskMonitor：ドローダウン監視・ポジション上限監視・ダッシュボード更新
  - KillSwitch：条件により ExecutionEngine 停止用のキルフラグ（data/kill.flag）を書き込む
  - AlertManager（アラート送信のハブ、LINE 等と連携可能）
- Portfolio（純粋関数群）
  - 候補選定、等重/スコア重みの計算、単元・資金制約を考慮した発注株数計算、セクター上限適用、レジーム乗数
- Research
  - ファクター計算（モメンタム・バリュー・ボラティリティ）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
- AI（OpenAI）
  - news_nlp.score_news: ニュースを LLM でスコアリングして ai_scores テーブルへ書き込み
  - regime_detector.score_regime: ETF / マクロニュースを組み合わせて市場レジーム判定を行い保存
- Tools
  - ペーパートレード検証レポート生成スクリプト（tools.paper_verification_report）

セットアップ手順
----------------
前提
- Python >= 3.10（型ヒントの union 表記などを利用）
- git ワークツリーまたは pyproject.toml でプロジェクトルートが検出されます

1. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  または  .venv\Scripts\activate

2. 依存ライブラリのインストール（例）
   - pip install duckdb psutil openai PyYAML
   - 実際のプロジェクトでは requirements.txt や pyproject.toml を使って管理してください。

3. 初期環境変数 (.env) の作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
     - これによりプロジェクトルートの .env を生成・更新できます。
   - .env を直接作成する場合は .env.example を参考にしてください（必須項目は後述）。

4. 設定検証
   - python -m kabusys.validate_config
   - 問題があればここで指摘されます。--strict を付けると警告も失敗扱いになります。

5. データディレクトリの作成（必要なら）
   - デフォルトでは data/ 以下に DB や PID/フラグファイルを作成します。
   - 例: mkdir -p data

主要な環境変数（代表）
--------------------
（多くは .env で設定します。必須のものは validate_config でもチェックされます）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants API 用
- KABU_API_PASSWORD (必須) — kabuステーション API 用パスワード
- KABUSYS_ENV — 実行環境。development / paper_trading / live（デフォルト: development）
  - paper_trading の場合、Execution は MockBroker を使用し、別 SQLite（PAPER_TRADING_SQLITE_PATH）を使用します
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視）DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- OPENAI_API_KEY — OpenAI を使う機能で必要
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — LINE 通知（任意）
- LOG_LEVEL — ログレベル（DEFAULT: INFO）
- KILL_FLAG_CLEAR_ON_START — Execution 起動時に既存 kill.flag を削除するか（0/1、デフォルト: 0）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト: 60）

使い方（主要な実行例）
---------------------

1) 環境設定ウィザード
   - python -m kabusys.config_setup
   - 作成された .env を編集して必要なシークレットやパスを確認してください。

2) 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告でも exit(1) になります。

3) ExecutionEngine（発注エンジン）起動
   - python -m kabusys.run_execution
   - 注意:
     - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）へ記録します。
     - ExecutionEngine の停止は data/stop_requested.flag を作成するか（run_execution は起動時にこのフラグをチェック）、KillSwitch により data/kill.flag が作られるとエンジン側で停止処理が行われます。
     - 実行中の PID は data/execution.pid に書き出されます。

4) Monitoring（監視ループ）起動
   - python -m kabusys.run_monitoring
   - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可（秒、デフォルト 60）。
   - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用して監視データを記録します。
   - 停止: プロジェクトルート/data/stop_requested.flag を作成すると監視ループは検知して終了します。

5) ペーパートレード検証レポート生成
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - またはデフォルト DB を上書く場合:
     - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

6) AI 機能（プログラムから呼び出し）
   - OpenAI API キーを設定していること（OPENAI_API_KEY）
   - 例（Python から）:
     - from kabusys.ai.news_nlp import score_news
       - score_news(conn, target_date, api_key=None)
     - from kabusys.ai.regime_detector import score_regime
       - score_regime(duckdb_conn, target_date, api_key=None)
   - API 呼び出しはリトライや JSON バリデーションなど堅牢化されていますが、キーが無い場合は ValueError が発生します。

停止とフラグ
------------
- run_execution や run_monitoring はプロジェクトルートの data/stop_requested.flag を監視し、存在するとループを終了します。
- KillSwitch は条件（ドローダウン等）で data/kill.flag を作成し、ExecutionEngine 側で停止をトリガーします。KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に自動でクリアされます（本番では推奨されません）。

データベース自動初期化
--------------------
- run_* モジュールや Execution/Monitoring の初期化時に monitoring_db.init_monitoring_db() を呼び出して必要なテーブル・インデックスを冪等に作成します。
- 既存 DB にカラムがなければマイグレーション（ALTER TABLE ADD COLUMN）も実行されます。

ディレクトリ構成（抜粋）
---------------------
以下は src/kabusys 配下の主要ファイルとサブパッケージの一覧です（実際のリポジトリに合わせて調整してください）:

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / Settings 管理、自動 .env ロード
  - config_setup.py              — .env 対話ウィザード
  - validate_config.py           — 設定検証 CLI
  - run_execution.py             — ExecutionEngine 起動スクリプト
  - run_monitoring.py            — SystemMonitor ポーリング起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py
  - ai/
    - __init__.py
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
  - execution/                    (発注エンジン実装群: broker_factory, execution_engine, order_manager, order_repository, reconciler, risk_manager 等)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - utils/
    - process_priority.py
  - monitoring/                   （前述）
  - data/                         （ランタイム生成: DB、pid、flag ファイルなど）

注意事項 / 運用上のヒント
------------------------
- 本番運用時は KABUSYS_ENV=live に注意深く設定してください（validate_config は live 時に追加の警告を出します）。
- Kill Switch（data/kill.flag）は本番では強力な手段です。KILL_FLAG_CLEAR_ON_START は本番では 0 にしてください。
- OpenAI を利用する機能は API 料金が発生します。API キー管理とコストに注意してください。
- psutil でプロセス優先度や CPU affinity を設定しますが、権限によっては失敗（警告）します。
- DuckDB / SQLite のファイルパスはデフォルトで data/ 以下です。適切なパスやバックアップ戦略を用意してください。

ライセンス・バージョン
----------------------
- パッケージバージョンは kabusys.__version__ で管理（現在: 0.1.0 相当）。
- ライセンス情報はリポジトリの LICENSE ファイルを参照してください（存在する場合）。

サポート / 変更
----------------
- 新規機能追加や修正を行う場合は、まず validate_config と各種ユニットテスト（存在する場合）を実行してください。
- DB スキーマの変更は既存データの互換性に配慮してください（現状いくつかの簡単なマイグレーション処理が組み込まれています）。

以上。必要であれば README を英語版に変換したり、実行フロー図や具体的な運用手順（systemd / Supervisor 用のユニット例）を追加で作成します。どの情報を追加したいか教えてください。