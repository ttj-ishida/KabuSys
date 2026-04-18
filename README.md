README
=====

概要
----
KabuSys は日本株向けの自動売買システムのコアライブラリ群です。  
システム監視、注文実行エンジン、ポートフォリオ構築、リサーチ（ファクター算出）や
ニュース NLP を使ったスコアリング、ペーパートレード検証ツールなどを含みます。

このリポジトリはライブラリ／ランタイムスクリプトの集合であり、実際の発注は設定に応じて
kabuステーション API（本番）または MockBrokerClient（ペーパートレード）経由で行われます。

主な機能
--------
- システム監視（SystemMonitor／MonitoringEngine）
  - CPU・メモリ・ディスク・データ鮮度・Execution プロセス監視
  - 監視ログの永続化（SQLite）
  - Kill Switch（リスク条件に応じた停止フラグ生成）
- 注文実行エンジン（ExecutionEngine 起動スクリプト）
  - ブローカークライアント選択（本番/ペーパートレードの自動分離）
  - リスク管理、注文管理、約定整合（Reconciler）等
- ポートフォリオ構築（選定・重み算出・ポジションサイズ計算）
  - 等金額・スコア加重・リスクベースの株数算出
  - セクターキャップ、レジームに応じた乗数調整
- リサーチ（ファクター計算・特徴量探索）
  - Momentum / Value / Volatility 等のファクター算出
  - 将来リターン・IC 計算・統計サマリ
- ニュース NLP（OpenAI を利用したニュースセンチメント）
  - 銘柄単位のスコアリング（ai_scores テーブルへ書込可）
  - マクロニュースを用いた市場レジーム判定（regime_detector）
- ユーティリティ
  - .env 対話式生成ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - ペーパートレード検証レポート出力ツール

前提条件
--------
- Python 3.10+
- 必要な外部ライブラリ（例）
  - duckdb
  - psutil
  - openai
  - PyYAML（config/*.yaml の検証に必要だが必須ではない）
- kabuステーション API や J‑Quants など本番連携をする場合はそれぞれの資格情報

インストール
------------
1. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存関係をインストール（プロジェクトに requirements.txt がある想定）
   - pip install -r requirements.txt
   - ない場合は最低限: pip install duckdb psutil openai pyyaml

設定（.env）
-----------
1. 対話式ウィザードで .env を作成・更新:
   - python -m kabusys.config_setup
   - ウィザードは JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD 等の必須項目を案内します。

2. 設定検証:
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit code 1）になります。

重要な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABUSYS_ENV: 実行環境 ("development" | "paper_trading" | "live")。paper_trading は DB 分離／MockBroker 利用
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（paper_trading 用）
- OPENAI_API_KEY: OpenAI を使う機能（news_nlp / regime_detector）で必要
- LOG_LEVEL: ログレベル（例: INFO）
- LOG_DIR: ログ保存ディレクトリ（デフォルト logs/）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- PID_FILE_PATH / KILL_FLAG_PATH など監視関連パス

実行方法（主要スクリプト）
--------------------------
各スクリプトはパッケージモジュールとして起動できます。

- 監視ループ起動（常駐監視）
  - MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（秒）
  - python -m kabusys.run_monitoring

  特徴:
  - Settings に基づき SQLite（monitoring）と DuckDB に接続
  - SystemMonitor.check_once() を定期実行して system_status 等に記録
  - data/stop_requested.flag を置くと監視ループを停止

- ExecutionEngine 起動（注文実行）
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、data/paper_trading.db に記録
  - python -m kabusys.run_execution

  特徴:
  - 起動時に PID ファイルを作成（設定によりパス変更可）
  - data/stop_requested.flag が既に存在する場合は起動せず終了
  - 実行中に stop flag を置くとエンジン停止を指示

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスは --db または 環境変数 PAPER_TRADING_SQLITE_PATH で指定可能

AI / OpenAI 関連
- news_nlp.score_news: raw_news を用いて銘柄別センチメントを ai_scores に書き込む
  - OPENAI_API_KEY が必要。失敗耐性（リトライ・部分書込）実装済み。
- regime_detector.score_regime: ETF（1321）の MA200 とマクロニュース LLM センチメントの
  重み合成でレジーム判定を行い market_regime テーブルに書込む
  - こちらも OPENAI_API_KEY が必要

ログ・データファイル
--------------------
- デフォルトログ: logs/<app_name>.log（TimedRotatingFileHandler 日次ローテーション、30日保持）
  - ログ出力は stdout にも同時出力されます。
- データディレクトリ（例）:
  - data/monitoring.db         — 監視用 SQLite（監視ログ / trade_logs / dashboard 等）
  - data/paper_trading.db      — ペーパートレード用（KABUSYS_ENV=paper_trading）
  - data/kabusys.duckdb        — DuckDB（時系列価格等分析用）
  - data/execution.pid         — 実行エンジンの PID（デフォルト）
  - data/kill.flag             — Kill Switch が書き込む停止フラグ
  - data/stop_requested.flag   — 外部からの stop 要求（run_* スクリプトが監視）

運用上のメモ
-------------
- run_* スクリプトは最初に set_process_priority("high") を呼び出してプロセス優先度を上げます。
  実行環境によって権限が不足すると警告を出してスキップします。
- Monitoring は KABUSYS_ENV に依らず「本番 sqlite_path」を使用する設計です（監視 DB は本番と共有）。
- ExecutionEngine は paper_trading のときに SQLite を分離し、実際の発注を行わない MockBroker を使用します。
- Kill Switch はリスク条件（例: ドローダウン超過・ポジション上限）で data/kill.flag を作成します。
  本番では KILL_FLAG_CLEAR_ON_START を 0 にすることを推奨します。

ディレクトリ構成
--------------
（主要ファイル・モジュールの説明付き）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings（.env 自動読み込みロジック含む）
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_monitoring.py         — SystemMonitor ポーリング起動スクリプト
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - utils/
    - logging_setup.py        — ログ設定ユーティリティ（stdout + 日次ファイル）
    - process_priority.py     — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py        — SQLite 操作（監視テーブルの作成・読み書き）
    - system_monitor.py       — システム / データ鮮度監視
    - trade_monitor.py        — （注文ログ監視等）※実装ファイルあり
    - risk_monitor.py         — ドローダウン・ポジション数監視
    - kill_switch.py          — フラグファイル生成ロジック
    - monitoring_engine.py    — 各 monitor を束ねるランナー
    - alert_manager.py        — （LINE 等通知管理）※実装ファイルあり
  - execution/
    - execution_engine.py     — 実行エンジン本体（EngineConfig / run_session）
    - order_manager.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py       — BrokerClient の生成（Mock / 実ブローカー）
    - order_repository.py
  - portfolio/
    - portfolio_builder.py    — 候補選定・重み計算
    - position_sizing.py      — 株数計算・単元丸め・キャップ処理
    - risk_adjustment.py      — セクター制限・レジーム乗数
  - research/
    - factor_research.py      — Momentum/Value/Volatility 等
    - feature_exploration.py  — 将来リターン・IC・統計サマリ
  - ai/
    - news_nlp.py             — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py      — マクロ+ETF でレジーム判定
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成スクリプト

貢献・開発
----------
- 新しい構成ファイルを追加したら validate_config で検証を行ってください。
- DuckDB や SQLite のスキーマ変更は monitoring_db.init_monitoring_db 等に移行処理を追加してください（既存 DB へのマイグレーション対応あり）。
- OpenAI API 呼び出し周りはネットワーク障害・429・5xx を考慮した耐障害実装になっています。テスト時は API 呼び出し関数をモックしてください。

ライセンス
---------
プロジェクトのライセンス情報をここに記載してください（このサンプルには記載がありません）。

補足
----
より具体的な利用例や ExecutionEngine の内部仕様・戦略設計（PortfolioConstruction.md、StrategyModel.md 等）は
プロジェクト内ドキュメントを参照してください。

---

必要であれば README に含める特定のコマンド例、.env のサンプル、もしくは各モジュールの詳細ドキュメント（関数一覧や引数仕様）を追加します。どの情報を優先的に補完しますか？