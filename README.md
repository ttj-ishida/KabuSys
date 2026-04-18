README
======

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤です。本リポジトリは以下を含むコンポーネント群を提供します。

- 実際の発注ロジックを持つ ExecutionEngine（本番 / ペーパートレード対応）
- システム稼働性・注文状況・リスク監視（Monitoring）
- ポートフォリオ構築・ポジションサイジング・リスク調整ユーティリティ（純粋関数）
- DuckDB を用いたファクター計算 / リサーチ機能
- OpenAI を使ったニュース NLP / レジーム判定（任意）
- 運用補助スクリプト（.env ウィザード、設定検証、Paper Trading レポート生成 等）

特徴
----
- 本番 / ペーパートレードを厳格に分離（ペーパートレードは別 SQLite DB に記録）
- 監視ループ（Monitoring）でプロセス監視、データ鮮度チェック、リスク（ドローダウン・ポジション上限）監視を実行
- Kill Switch（data/kill.flag）で安全に ExecutionEngine を停止可能
- DuckDB を使った高速なファクター計算・リサーチ機能
- OpenAI（gpt-4o-mini 等）を利用したニュースセンチメント評価・市場レジーム判定（API キー必要）
- ログはコンソール + ローテートファイル（logs/<app_name>.log）で管理

前提 / 必要条件
---------------
- Python 3.10 以上（型記法に | を使用）
- 必須 Python パッケージ（一部機能）:
  - duckdb
  - psutil
  - openai（AI 機能を使う場合）
  - PyYAML（config/*.yaml の内容検証を行う場合、必須ではない）
- 推奨: 仮想環境（venv / conda）

インストール（例）
-----------------
1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb psutil openai PyYAML

   （プロジェクトに requirements.txt がある場合はそちらを使用してください）

設定 (.env)
----------
起動前に環境変数を用意します。簡易ウィザードを用意しています:

- 対話式ウィザード
  - python -m kabusys.config_setup
  - これによりプロジェクトルートに .env を作成 / 更新できます。

- 必須環境変数（抜粋）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- AI 機能を使う場合
  - OPENAI_API_KEY を設定してください（score_news / score_regime などで使用）

- ペーパートレード関連
  - KABUSYS_ENV=paper_trading を指定すると MockBrokerClient を使用し、デフォルトで data/paper_trading.db に記録されます。
  - PAPER_FILL_MODE（instant / partial / never / reject）
  - PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）

- ログ・DB 関連デフォルト
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - LOG_DIR: logs/
  - LOG_LEVEL: INFO

設定検証
--------
起動前に設定ファイル・環境変数をチェックできます:

- python -m kabusys.validate_config
- 警告も失敗扱いにする: python -m kabusys.validate_config --strict

主な使い方
----------
1. ExecutionEngine（発注エンジン）を起動
   - python -m kabusys.run_execution
   - KABUSYS_ENV によって挙動が変わります:
     - live: 実際のブローカークライアントを使用（本番）
     - paper_trading: MockBrokerClient を使用し、記録は data/paper_trading.db に行われます
   - 実行前に data/stop_requested.flag が存在すると起動をスキップします
   - 実行中に data/stop_requested.flag を作成すると安全に停止します

2. Monitoring（監視ループ）起動
   - python -m kabusys.run_monitoring
   - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で変更可能（デフォルト 60）
   - 監視は常に production 相当の sqlite_path を使用（環境に依らず）
   - 監視は system / trade / risk の各モニタを呼び出し、KillSwitch の評価・アラート送信等を行います

3. Paper Trading 検証レポート
   - python -m kabusys.tools.paper_verification_report
   - 期間指定: --from YYYY-MM-DD --to YYYY-MM-DD
   - DB 指定: --db PATH または 環境変数 PAPER_TRADING_SQLITE_PATH

4. AI 機能
   - ニュース NLP スコア付与: kabusys.ai.score_news（内部では OpenAI API を使用）
   - 市場レジーム判定: kabusys.ai.regime_detector.score_regime（OpenAI API 使用）
   - これらを CLI から直接呼ぶラッパーはありませんが、モジュール関数をスクリプト/ジョブから呼べます
   - OpenAI API のレート制限・エラーには指数バックオフで対応する実装があります

運用上のポイント
----------------
- Kill Switch: KillSwitch は data/kill.flag を作成すると ExecutionEngine を停止させます。Execution 起動時の設定で KILL_FLAG_CLEAR_ON_START=1 にすると自動クリアされますが、本番では 0 を推奨します。
- PID / stop フラグ:
  - data/execution.pid: ExecutionEngine の PID ファイル
  - data/stop_requested.flag: 手動停止要求（起動スクリプトで監視）
- ログ:
  - logs/<app_name>.log（TimedRotatingFileHandler により日次ローテーション、30日保持）
  - setup_logging 関数で stdout とファイル両方に出力します
- プロセス優先度:
  - run_* スクリプトは起動直後に set_process_priority("high") を呼びます（psutil による OS 依存設定。権限不足で警告になることがあります）

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py                 — 環境変数 / 設定読み込みロジック（自動 .env ロード）
- config_setup.py           — .env 対話式ウィザード
- validate_config.py        — 起動前設定検証 CLI
- run_execution.py          — ExecutionEngine 起動スクリプト
- run_monitoring.py         — SystemMonitor ポーリング起動スクリプト

サブパッケージ:
- ai/
  - news_nlp.py             — ニュースを OpenAI でスコアリングして ai_scores に書き込み
  - regime_detector.py      — マクロ + ETF MA を用いた市場レジーム判定
- portfolio/
  - portfolio_builder.py    — 候補選定、等配分/スコア配分
  - position_sizing.py      — 発注株数計算（risk-based / equal / score）
  - risk_adjustment.py      — セクターキャップ、レジーム乗数
- research/
  - factor_research.py      — momentum / value / volatility 等のファクター計算（DuckDB）
  - feature_exploration.py  — 将来リターン計算、IC 等の統計ユーティリティ
- monitoring/
  - monitoring_db.py        — SQLite 監視 DB のスキーマ初期化・CRUD
  - system_monitor.py       — CPU/メモリ/ディスク/データ鮮度監視
  - trade_monitor.py        — （注文の滞留・約定異常の検出など）※実装ファイルあり
  - risk_monitor.py         — ドローダウン / ポジション上限監視
  - kill_switch.py          — Kill Switch 実装（data/kill.flag 書込）
  - monitoring_engine.py    — 各 monitor をまとめるループ実装
  - alert_manager.py        — アラート送信（LINE 等）※実装ファイルあり
- utils/
  - logging_setup.py        — ログ設定ユーティリティ（console + file）
  - process_priority.py     — プロセス優先度 / CPU affinity 設定ユーティリティ
- tools/
  - paper_verification_report.py — ペーパートレードの検証レポート生成スクリプト
- data/                     — 実行時に使用するデータ・フラグ類（デフォルトパス）
  - monitoring.db (SQLITE_PATH)
  - kabusys.duckdb (DUCKDB_PATH)
  - paper_trading.db (PAPER_TRADING_SQLITE_PATH)
  - kill.flag, stop_requested.flag, execution.pid

開発 / テストのヒント
--------------------
- .env は絶対に Git にコミットしないでください（config_setup.py のヘッダに注意書きあり）。
- PyYAML がインストールされていない場合、validate_config は YAML 内容チェックをスキップします（警告）。
- AI 呼び出し部分は外部 API 依存・ネットワーク失敗の可能性があるため、unittest.mock.patch で _call_openai_api を差し替えてユニットテスト可能です。
- DuckDB 接続をテスト用にメモリ上で作成し、prices_daily / raw_financials など必要テーブルを用意すれば研究モジュールの単体テストが可能です。

ライセンス / バージョン
----------------------
- パッケージバージョン: __version__ = "0.1.0"
- ライセンス情報はリポジトリルートの LICENSE を参照してください（存在する場合）。

よくある運用コマンド（まとめ）
------------------------------
- .env 作成: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config [--strict]
- Execution 起動: python -m kabusys.run_execution
- Monitoring 起動: python -m kabusys.run_monitoring (MONITOR_POLL_INTERVAL=30 等で上書き可)
- Paper レポート: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

補足
----
細かな実装や運用ルール（例えば OrderManager / ExecutionEngine の詳細、外部ブローカークライアントの実装、alert_manager の通知先など）は各モジュールの docstring / コメントを参照してください。質問や追加のドキュメント化が必要であれば、どの箇所を詳述するか教えてください。