KabuSys — 日本株自動売買システム
================================

このリポジトリは日本株向けの自動売買システム（KabuSys）のコアモジュール群です。  
本 README はコードベースを参照して、プロジェクトの概要、主な機能、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめたものです。

前提
----
- Python 3.10 以上（型注記で PEP 604 の「|」を使用）
- SQLite は標準ライブラリで利用可能
- 必要な追加パッケージ（後述）をインストールしてください

プロジェクト概要
------------
KabuSys は次の主要機能を持つモジュール群で構成されています。

- ExecutionEngine：発注・注文管理・リスク管理を行う実行エンジン（本番／ペーパーの切替対応）
- Monitoring：システム稼働監視、注文ログ・リスクログの永続化、アラート発行、Kill Switch（自動停止）の評価
- Research / Data：DuckDB を利用したファクター計算・特徴量探索（モメンタム・ボラティリティ・バリュー等）
- Portfolio：候補選定、重み付け、ポジションサイズ計算、セクター制限などのポートフォリオ構築ロジック
- AI 補助：ニュースを LLM（OpenAI）でスコアリングして銘柄別スコアを生成／市場レジーム判定
- ユーティリティ：ロギング設定、プロセス優先度設定、環境設定ウィザード、設定検証 CLI、レポート生成ツール など

主な機能一覧
------------
- 環境設定ウィザード（python -m kabusys.config_setup）で .env を対話生成
- 設定検証 CLI（python -m kabusys.validate_config）で起動前チェック
- ExecutionEngine（本番 / paper_trading の切替、MockBroker を用いたペーパートレード）
- MonitoringEngine（SystemMonitor / TradeMonitor / RiskMonitor の定期実行・アラート連携）
- Kill Switch（条件を満たしたら data/kill.flag を書込／ExecutionEngine 停止）
- Paper Trading 検証レポート生成ツール（python -m kabusys.tools.paper_verification_report）
- DuckDB を用いたリサーチ関数（ファクター計算・将来リターン・IC 計算）
- OpenAI を利用したニュース NLP による銘柄スコアリング・レジーム判定（エラーハンドリング・リトライ実装）

セットアップ手順
--------------
1. リポジトリをクローン
   - git clone <repo-url>

2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb psutil openai
   - 追加（推奨 / 任意）: pip install pyyaml
   - （requirements.txt がない場合は上記を直接インストールしてください）

4. .env を作成
   - 対話ウィザード: python -m kabusys.config_setup
   - または手動で .env を作成（.env.example を参考に）

   主要な環境変数（よく使うもの、デフォルト値を含む）:
   - KABUSYS_ENV: execution モード ("development" / "paper_trading" / "live")（default: development）
   - JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
   - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
   - KABU_API_BASE_URL: デフォルト http://localhost:18080/kabusapi
   - DUCKDB_PATH: data/kabusys.duckdb（分析用）
   - SQLITE_PATH: data/monitoring.db（監視 DB）
   - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用 DB）
   - LOG_LEVEL: INFO（DEBUG/INFO/WARNING/ERROR/CRITICAL）
   - LOG_DIR: logs/
   - KILL_FLAG_CLEAR_ON_START: 0（起動時の kill.flag 自動クリアを有効にするなら1。 本番は0推奨）
   - OPENAI_API_KEY: OpenAI を使う機能で必要
   - MONITOR_POLL_INTERVAL: 監視ループの秒間隔（デフォルト 60）

   注意:
   - 自動 .env 読み込みはデフォルトで有効。無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

5. ディレクトリ初期化
   - data/ および logs/ は必要に応じて自動作成されますが、権限等に注意してください。

基本的な使い方
------------

1. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 警告をエラーとして扱う --strict オプションあり

2. 実行エンジン（ExecutionEngine）の起動
   - python -m kabusys.run_execution
   - 説明:
     - KABUSYS_ENV=paper_trading の場合、MockBrokerClient が使用され、データは PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録されます。
     - 実行時に data/stop_requested.flag が存在していると起動をスキップ／停止します。
     - 実行中に停止させたい場合は data/stop_requested.flag を作成する（touch）か、Kill Switch により data/kill.flag が作成されると ExecutionEngine 停止処理が走ります。
     - エンジンは data/execution.pid を PID ファイルとして扱います（Settings.pid_file_path で変更可）。

3. 監視ループ（MonitoringEngine）の起動
   - python -m kabusys.run_monitoring
   - 説明:
     - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能。デフォルト 60 秒。
     - 監視は本番 sqlite_path を使用（KABUSYS_ENV に関わらず）。
     - 停止はプロジェクト直下 data/stop_requested.flag を作成することで監視ループが検知して終了します。

4. Paper Trading 検証レポートの生成
   - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
   - デフォルトの DB は環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

5. AI 関連（ニュース NLP / レジーム判定）
   - kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime を直接呼び出して DB に書き込み可能（OpenAI API キーが必要）。
   - API 呼び出しは冪等性・リトライ・クリッピング等が実装されています。

ログ
----
- デフォルトログディレクトリ: logs/
- ログファイル名はアプリ名プレフィックス（例: execution.log, monitoring.log）
- ログレベルは .env の LOG_LEVEL や setup_logging の引数で制御可能

停止／Kill／PID の取り扱い
-------------------------
- stop フラグ:
  - data/stop_requested.flag を作成すると run_monitoring と run_execution のループで検出して終了します（手動シャットダウン用）。
- kill フラグ（Kill Switch）:
  - KillSwitch によって data/kill.flag が書き込まれると ExecutionEngine 停止トリガーになります（自動停止用の条件は RiskMonitor 等で評価）。
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動クリアします（本番では危険なのでデフォルト 0）。
- PID ファイル:
  - 実行エンジンは data/execution.pid 等に PID を書く設計です（Settings.pid_file_path で変更可能）。

ユーティリティ／CLI 一覧（代表）
-------------------------------
- python -m kabusys.config_setup           : .env を対話式作成
- python -m kabusys.validate_config        : 設定検証
- python -m kabusys.run_execution          : ExecutionEngine 起動スクリプト
- python -m kabusys.run_monitoring         : Monitoring 起動スクリプト
- python -m kabusys.tools.paper_verification_report : Paper Trading 検証レポート生成

ディレクトリ構成（主要ファイル）
-------------------------------
src/kabusys/
- __init__.py
- config.py                      — 環境変数 / Settings 管理
- config_setup.py                — .env ウィザード（対話）
- validate_config.py             — 設定検証 CLI
- run_execution.py               — ExecutionEngine 起動スクリプト
- run_monitoring.py              — Monitoring 起動スクリプト

サブパッケージ（主要なもの）
- ai/
  - news_nlp.py                   — ニュース NLP（OpenAI）で銘柄スコアを生成
  - regime_detector.py            — 市場レジーム判定（LLM + MA）
- monitoring/
  - monitoring_db.py              — SQLite 永続化レイヤ
  - monitoring_engine.py          — Monitor を束ねるエンジン
  - system_monitor.py             — システム観測（CPU/メモリ/Disk/データ鮮度）
  - risk_monitor.py               — ドローダウン・ポジション上限監視
  - kill_switch.py                — Kill Switch の評価・フラグ書込
  - ... (alert_manager, trade_monitor 等が想定される)
- portfolio/
  - portfolio_builder.py          — 候補選定・重み付け
  - position_sizing.py            — 発注株数（lot 集約・スケーリング）
  - risk_adjustment.py            — セクターキャップ、レジーム乗数
- research/
  - factor_research.py            — ファクター計算（momentum / volatility / value）
  - feature_exploration.py        — 将来リターン / IC / 統計サマリー
- tools/
  - paper_verification_report.py  — Paper Trading 検証レポート
- utils/
  - logging_setup.py              — 共通ログ設定
  - process_priority.py           — プロセス優先度 / CPU affinity
  - ...（その他ユーティリティ）

注意事項・運用上のヒント
-----------------------
- 本番 (KABUSYS_ENV=live) ではログ・kill flag の扱い、LINE 通知等を十分に確認してください（validate_config で警告検出あり）。
- OpenAI を利用する機能は API キーとコストに注意。失敗時はフェイルセーフ（0.0 等）で続行する設計ですが、運用方針を決めてください。
- Paper Trading（KABUSYS_ENV=paper_trading）は本番 DB と分離されるように設計されています。PAPER_TRADING_SQLITE_PATH を適切に設定してください。
- DuckDB は分析用途で利用されます。prices_daily / raw_financials / raw_news 等のテーブルが想定されています。データの投入は別途スクリプト（データパイプライン）を用意してください。

開発者向け
---------
- 単体関数群（portfolio/*.py、research/*.py）は副作用なしの純粋関数として設計されています。ユニットテストを書きやすく、モックも容易です。
- OpenAI 呼び出し部分は内部でラップされており、テスト時は該当関数をパッチ（mock）して外部通信を遮断できます（コード内に言及あり）。
- settings オブジェクト（kabusys.config.settings）から簡単に環境設定にアクセスできます。

ライセンス / 貢献
----------------
- 本リポジトリのライセンスやコントリビュート方針は別途 LICENSE / CONTRIBUTING を参照してください（この README には含まれていません）。

以上が KabuSys コードベースの概要と基本的な使い方です。README の内容で不明点や、実際に起動する際の具体的なエラーや追加のセットアップ手順が必要であれば、ログやエラーメッセージを添えて質問してください。