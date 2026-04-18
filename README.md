README.md

KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株の自動売買・リサーチ・監視を行うための Python ベースのコードベースです。
設計方針として以下を重視しています:

- 本番とペーパートレードを分離（環境変数 KABUSYS_ENV）
- DuckDB を用いた分析、SQLite を用いた監視ログ永続化
- LLM（OpenAI）を利用したニュースセンチメント / レジーム判定（オプション）
- 簡単な CLI ウィザードで .env を生成し、起動前に設定検証が可能

主な機能
--------
- ExecutionEngine 起動スクリプト（run_execution.py）
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、data/paper_trading.db に完全分離して記録
  - PID ファイル / 停止フラグ対応
- Monitoring（run_monitoring.py）
  - SystemMonitor / TradeMonitor / RiskMonitor をポーリングし、監視ログ（SQLite）へ保存
  - Kill Switch による ExecutionEngine 停止（data/kill.flag）
  - MONITOR_POLL_INTERVAL によるポーリング間隔上書き
- 設定支援
  - 対話式 .env ウィザード（python -m kabusys.config_setup）
  - 設定検証 CLI（python -m kabusys.validate_config）
- Research / Portfolio
  - ファクター計算（momentum, volatility, value 等）
  - ポートフォリオ構築（候補選定、重み計算、ポジションサイジング、セクター制限）
- AI モジュール（任意）
  - ニュース NLP（kabusys.ai.news_nlp.score_news）
  - レジーム判定（kabusys.ai.regime_detector.score_regime）
  - いずれも OpenAI API キー（OPENAI_API_KEY）が必要
- ツール
  - ペーパートレード検証レポート生成（python -m kabusys.tools.paper_verification_report）

必要条件（主要な外部ライブラリ）
--------------------------------
（プロジェクトの requirements.txt がある場合はそちらを優先してください）
- Python 3.9+
- duckdb
- psutil
- openai (AI 機能利用時)
- PyYAML（config/*.yaml の内容検証を行う場合）
- その他: 標準ライブラリ

セットアップ手順
----------------
1. リポジトリをクローンし、仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install -r requirements.txt
   - requirements.txt が無い場合は少なくとも duckdb, psutil をインストールしてください:
     - pip install duckdb psutil

3. .env の作成（対話式ウィザード）
   - python -m kabusys.config_setup
   - ウィザードは J-Quants トークンや kabuAPI パスワード等の環境変数を対話式に作成します。
   - 生成した .env は絶対に Git にコミットしないでください。

4. 設定検証（起動前に必ず実行推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります:
     - python -m kabusys.validate_config --strict

使い方（実行例）
----------------

基本的な起動
- Execution エンジンを起動:
  - python -m kabusys.run_execution
  - 実行中は data/execution.pid を生成します。停止は data/stop_requested.flag を作成するか kill.flag に依る停止シグナル（監視側から生成）で行います。

- Monitoring を起動（監視ループ）:
  - python -m kabusys.run_monitoring
  - デフォルトのポーリング間隔は 60 秒。環境変数で上書き可能:
    - export MONITOR_POLL_INTERVAL=30
    - python -m kabusys.run_monitoring

停止・Kill スイッチ
- 単純停止フラグ（run_execution/run_monitoring が参照）
  - data/stop_requested.flag を作成すると、run_monitoring/run_execution のループ/スレッドが検知して終了します。
- Kill Switch（運用上の強制停止）
  - monitoring の KillSwitch はリスク・ドローダウン等の条件により data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送ります。
  - Settings.kill_flag_clear_on_start が 1 のときは起動時に自動で kill.flag をクリアします（本番では 0 を推奨）。

Paper Trading（ペーパートレード）
- KABUSYS_ENV=paper_trading を設定すると、Execution は MockBrokerClient を使用し paper_trading 用 DB に記録します:
  - PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）でパスを変更可能

AI 機能
- OPENAI_API_KEY 環境変数が必要です（または関数引数で渡す）
- ニューススコアリング:
  - 実装: kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
- レジーム判定:
  - 実装: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
- API 呼び出しは失敗耐性を持ちますが、API キー未設定時は ValueError を送出します。

ツール
- ペーパートレード検証レポート:
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH  （PAPER_TRADING_SQLITE_PATH を上書き）

重要な環境変数（主なもの）
--------------------------
設定は .env や環境変数で行います。主なキー:

必須（最低限）
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

推奨 / 既定値あり
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL
- LOG_DIR: ログの出力ディレクトリ（デフォルト: logs）
- OPENAI_API_KEY: OpenAI API キー（AI 機能利用時）
- MONITOR_POLL_INTERVAL: 監視ループの秒間隔（run_monitoring 用）
- PAPER_FILL_MODE: ペーパー発注の fill モード ("instant"/"partial"/"never"/"reject")
- KILL_FLAG_CLEAR_ON_START: 起動時に data/kill.flag を自動クリアするか ("0" / "1")

ディレクトリ構成（主要ファイル）
--------------------------------
（リポジトリの src/kabusys をルートとした抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings クラス
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring ポーリング起動スクリプト

  - execution/               — 発注関連（Engine, OrderManager, BrokerFactory 等）
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py      — システム状態 / データ鮮度チェック
    - trade_monitor.py       — （発注ログ監視等 - 実装参照）
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - monitoring_engine.py   — モニター群の統合ループ
    - kill_switch.py         — kill.flag の書き込みロジック
    - alert_manager.py       — 通知管理（LINE 等へ通知する想定）
  - portfolio/
    - portfolio_builder.py   — 候補選定、重み付け
    - position_sizing.py     — 株数決定、リスク制限、単元丸め
    - risk_adjustment.py     — セクターキャップ、レジーム乗数
  - research/
    - factor_research.py     — ファクター計算（momentum/value/volatility）
    - feature_exploration.py — 将来リターン / IC / 統計サマリー
  - ai/
    - news_nlp.py            — ニュースセンチメント（OpenAI 呼び出し）
    - regime_detector.py     — 市場レジーム判定（MA + マクロセンチメント）
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - utils/
    - logging_setup.py       — 統一ロギング設定（console + 日次ローテートファイル）
    - process_priority.py    — プロセス優先度・CPU affinity 設定

運用上の注意
------------
- 本番（KABUSYS_ENV=live）では必ず .env を慎重に管理し、LINE 通知設定（LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID）などを確認してください。
- KILL_FLAG_CLEAR_ON_START=1 は本番では危険です（kill.flag が起動時に自動でクリアされます）。
- run_execution/run_monitoring は stop フラグ / kill.flag / PID ファイルを用いるため、運用スクリプトや systemd / supervisor 等での管理が容易です。
- DuckDB / SQLite のパスは .env で変更できます。バックアップや権限設定に注意してください。
- AI（OpenAI）呼び出しはコストとレイテンシが発生します。API 利用料・レート制限を考慮してください。

開発メモ
--------
- config/*.yaml（system_config.yaml 等）が存在しない場合、validate_config は警告を出します。yaml の内容検証には PyYAML が必要です。
- ログはデフォルトで logs/<app_name>.log に日次ローテーションで保存されます。ログディレクトリの作成に失敗するとコンソールのみ出力になります。
- 処理の多くは DuckDB 接続を受け取り SQL で計算する設計です（研究用途での再利用を想定）。

ライセンス / バージョン
-----------------------
- パッケージバージョンは src/kabusys/__version__ に定義されています（現在 0.1.0）。

付録：よく使うコマンド一覧
-------------------------
- .env 作成（ウィザード）:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- 実行エンジン起動:
  - python -m kabusys.run_execution
- 監視ループ起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- ペーパー検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- AI スコアリング（プログラム内呼び出し）:
  - kabusys.ai.score_news(conn, date(2026,4,1), api_key=os.environ["OPENAI_API_KEY"])

以上。README を参照して環境構築・起動を行ってください。不明点や実行時のエラーがあれば、該当するログ（logs/）と .env 設定を確認の上お問い合わせください。