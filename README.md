KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株の自動売買を目的としたモジュール群です。  
戦略（シグナル算出）、ポートフォリオ構築、発注エンジン（ExecutionEngine）、監視（Monitoring）、研究用ユーティリティ（DuckDB ベースのファクター計算）および AI を使ったニュース解析機能などを含みます。

主な特徴
--------
- ExecutionEngine（発注処理）と Monitoring（監視）を分離して運用可能
- Paper Trading モード（環境変数 KABUSYS_ENV=paper_trading）で本番 DB と完全に分離された SQLite を使用
- DuckDB を使った高速な研究用集計・ファクター計算モジュール
- ニュースを OpenAI（gpt-4o-mini）でスコアリングして AI スコアを生成する機能
- リスク監視（ドローダウン・ポジション上限）と Kill Switch（flag ファイルによるエンジン停止）
- ログ管理ユーティリティ（コンソール + 日次ローテートファイル）
- 対話式 .env ウィザードと起動前設定検証 CLI

準備（前提）
-----------
- Python 3.9+（型注釈に依存するコードを含みます）
- 必要な Python ライブラリ（例）
  - duckdb
  - psutil
  - openai （AI 機能を使う場合）
  - PyYAML（config/*.yaml の検証を行う場合）
- OS: Linux / macOS / Windows を想定（プロセス優先度設定はプラットフォームにより制約あり）

インストール（例）
-----------------
1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール（プロジェクトの requirements.txt がある場合はそれを利用）
   - pip install duckdb psutil openai pyyaml

環境変数 / 設定
----------------
- .env による設定を想定（プロジェクトルートに .env または .env.local を配置）。自動ロード機能はデフォルトで有効。無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- 主な環境変数
  - JQUANTS_REFRESH_TOKEN（必須）
  - KABU_API_PASSWORD（必須）
  - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
  - LOG_LEVEL（DEBUG/INFO/…、デフォルト: INFO）
  - OPENAI_API_KEY（AI 機能利用時に必要）
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（アラート通知）
  - MONITOR_POLL_INTERVAL（Monitoring ポーリング間隔秒、デフォルト 60）
  - KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするか、0/1、デフォルト 0）
  - PAPER_FILL_MODE（paper_trading の MockBrokerClient の fill 動作: instant | partial | never | reject）

設定の作成・検証
----------------
- 対話式ウィザードで .env を作成 / 更新:
  - python -m kabusys.config_setup
- 起動前に必須設定や config/*.yaml を検証:
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗として扱います

起動・使い方
------------

1. ExecutionEngine（発注エンジン）
   - 役割: 発注・注文管理・リスク管理・リコンサイル等を行うメインエンジン
   - 起動:
     - python -m kabusys.run_execution
   - 挙動:
     - KABUSYS_ENV=paper_trading のときは MockBrokerClient を利用し、PAPER_TRADING_SQLITE_PATH（data/paper_trading.db がデフォルト）へ履歴を記録
     - 起動時に data/stop_requested.flag が存在すれば起動せず終了
     - エンジンは別スレッドで run_session を動かし、data/stop_requested.flag が書き込まれたら停止を試みる
     - 起動時に PID ファイル（data/execution.pid など）を管理
     - プロセス優先度を "high" に設定（psutil を使用、OSによって制約あり）

2. Monitoring（監視プロセス）
   - 役割: システム状態（CPU/メモリ/ディスク）、データ鮮度、発注ログ、リスク指標を定期取得して DB に保存・アラート評価を行う
   - 起動:
     - python -m kabusys.run_monitoring
     - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可（デフォルト 60）
   - 特記事項:
     - Monitoring はどの KABUSYS_ENV でも本番用 sqlite_path（SQLITE_PATH）を使用して監視テーブルを保存します
     - KillSwitch（リスク発動時に data/kill.flag を生成）などを管理可能

3. Paper Trading 検証レポート
   - 機能: ペーパートレード結果（paper_trading DB）から稼働率、注文成功率、レイテンシ指標などを集計してレポートを表示
   - 実行例:
     - python -m kabusys.tools.paper_verification_report
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
     - DB を明示する場合: --db /path/to/paper_trading.db
   - 知っておくこと:
     - デフォルト DB パスは data/paper_trading.db（PAPER_TRADING_SQLITE_PATH で上書き可）

4. AI 機能（ニュース NLP / レジーム判定）
   - OpenAI API を使います。環境変数 OPENAI_API_KEY を必ず設定してください。
   - ニューススコアリング:
     - kabusys.ai.news_nlp.score_news を呼ぶことで ai_scores テーブルへスコアを書き込みます
   - 市場レジーム判定:
     - kabusys.ai.regime_detector.score_regime を呼ぶと market_regime テーブルへ結果を書き込みます
   - 実行時の注意:
     - API のエラー（429, ネットワーク断, 5xx）に対するリトライを備えていますが、キー未設定時は例外が発生します
     - LLM レスポンスのバリデーションやスコアのクリップなど安全策あり

ログ・データ・フラグ
-------------------
- ログ:
  - デフォルトは logs/<app_name>.log（日次ローテート、30 日保持）とコンソール出力
  - LOG_DIR 環境変数でログディレクトリを指定可
- データ:
  - data/ ディレクトリ配下に SQLite / PID / flag ファイル等を保存
  - stop_requested.flag / kill.flag: 停止や Kill Switch 用のフラグファイル
  - execution.pid: 実行エンジンの PID を保存するファイル（名前は Settings.pid_file_path で変更可）
- 注意:
  - .env は絶対に Git にコミットしないでください（config_setup.py でも警告有り）

開発者向けメモ
---------------
- Settings（kabusys.config.Settings）クラスで環境変数をラップしており、アプリ内から安全に参照できます
- 自動的にプロジェクトルートを探索して .env / .env.local を読み込みます（CWD に依存しない設計）
- monitoring_db.py に監視用テーブルの初期化・マイグレーションロジックがあります（冪等）
- process_priority.py は psutil を使い OS 差分を吸収します。権限不足で設定できない場合は警告のみ

ディレクトリ構成（主要ファイル）
-------------------------------
- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数 / Settings
  - config_setup.py               — .env 対話式ウィザード
  - validate_config.py            — 設定検証 CLI
  - run_execution.py              — ExecutionEngine 起動スクリプト
  - run_monitoring.py             — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - utils/
    - logging_setup.py            — 共通ログ設定
    - process_priority.py         — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py            — SQLite 監視 DB 層
    - monitoring_engine.py        — 各 Monitor を束ねる
    - system_monitor.py           — CPU/メモリ/データ鮮度監視
    - risk_monitor.py             — ドローダウン / ポジション上限監視
    - trade_monitor.py            — （発注ログ監視）※実装参照
    - kill_switch.py              — kill.flag の生成 / 管理
    - alert_manager.py            — （アラート送信）※実装参照
  - execution/
    - execution_engine.py         — ExecutionEngine（本体）※実装参照
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py
  - portfolio/
    - portfolio_builder.py        — 候補選定・重み計算
    - position_sizing.py          — 発注株数計算
    - risk_adjustment.py          — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py          — ファクター計算（DuckDB）
    - feature_exploration.py      — IC / 統計等
  - ai/
    - news_nlp.py                 — ニュース NLP（OpenAI）
    - regime_detector.py          — 市場レジーム判定（OpenAI）
  - data/                         — 运行時に作成することが多い（DB, pid, flags 等）

ライセンス・その他
------------------
- 現在のバージョン: 0.1.0（kabusys.__version__ に定義）
- .env やシークレット情報は Git 管理対象に含めないこと
- 実運用での使用前に validate_config による事前チェックを必ず実行してください
- 本リポジトリ内の doc（PortfolioConstruction.md 等）が参照される設計注記が含まれます。運用時は設計文書も確認してください

よくある運用オペレーション
--------------------------
- 新しい環境で初回セットアップ:
  1. python -m kabusys.config_setup
  2. python -m kabusys.validate_config
  3. python -m kabusys.run_monitoring （監視開始）
  4. python -m kabusys.run_execution （必要に応じて）
- 停止:
  - data/stop_requested.flag を作成すると各プロセスは検知して正常停止を試みる
  - Kill Switch によって data/kill.flag が作成されると ExecutionEngine は起動時に失敗するか停止されます（KILL_FLAG_CLEAR_ON_START=1 の場合は起動時に自動クリアされます。production では 0 を推奨）

問い合わせ・貢献
----------------
バグ報告や機能提案は issue を作成してください。プルリクエスト歓迎です。README を拡張する場合は運用手順・セキュリティ注意事項（API キー等の扱い）を明記してください。

--- 
この README はコードベースの主要な機能と運用手順を簡潔にまとめたものです。実行時の詳細挙動は該当モジュールの docstring / ソースコードをご参照ください。