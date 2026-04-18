README
======

概要
----
KabuSys は日本株向けの自動売買 / 研究用フレームワークです。  
ポートフォリオ構築、ポジションサイジング、リスク制御、監視（Monitoring）、および
AI を使ったニュースセンチメント評価など、トレーディングに必要な主要コンポーネント群を含みます。

主な設計方針:
- 実運用とペーパートレードを分離（paper_trading モードでは専用 DB / モックブローカーを使用）
- DuckDB を使った分析と SQLite を使った監視/履歴の永続化
- OpenAI（gpt-4o-mini 等）を利用したニュース NLP / レジーム判定（API キー必須）
- 起動スクリプトから統一されたログ出力・プロセス優先度設定を行う

機能一覧
--------
- 実行エンジン起動スクリプト（run_execution.py）
  - 本番 / ペーパートレードの切替、ブローカー抽象化、ExecutionEngine の起動
  - 停止フラグ / PID ファイルの管理
- 監視ループ起動スクリプト（run_monitoring.py）
  - System / Trade / Risk の監視（ポーリングで実行）、監視ログを SQLite に永続化
  - MONITOR_POLL_INTERVAL によるポーリング間隔の調整（デフォルト 60 秒）
- 設定ウィザード（config_setup.py）
  - .env を対話式に生成・更新するユーティリティ
- 設定検証 CLI（validate_config.py）
  - 環境変数・config/*.yaml の存在・基本妥当性をチェック（--strict オプションあり）
- Paper Trading 検証レポート（tools/paper_verification_report.py）
  - ペーパートレード DB から稼働率・約定率・レイテンシ等のレポートを生成
- ポートフォリオ構築モジュール（portfolio/*）
  - 候補選定、等比重/スコア加重の重み計算、セクター上限適用、位置サイズ計算
- 研究用モジュール（research/*）
  - ファクター計算（モメンタム・ボラティリティ・バリュー）、将来リターン、IC 計算
- AI モジュール（ai/*）
  - ニュースセンチメント（news_nlp）、市場レジーム判定（regime_detector）
  - OpenAI API 呼び出しはリトライや出力バリデーションを備える
- ユーティリティ（utils/*）
  - ログ設定（ファイルローテート + コンソール出力）
  - プロセス優先度・CPU affinity 設定

前提条件
--------
- Python 3.10+
- 必須パッケージ（最小）:
  - duckdb
  - psutil
  - openai
- 任意（機能に応じて）:
  - PyYAML（config/*.yaml の内容検証に使用）
- ネットワーク接続（OpenAI を使う場合）
- .env（環境変数）に JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD 等を設定

セットアップ手順
----------------

1. リポジトリをクローン
   - git clone ...（省略）

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要なライブラリをインストール
   - pip install duckdb psutil openai
   - YAML チェックを使う場合: pip install PyYAML

   （プロジェクトに requirements.txt があればそちらを使用してください）

4. 初期設定ファイル (.env) を作成
   - 対話式ウィザードを使用:
     - python -m kabusys.config_setup
   - 生成された .env は絶対に Git にコミットしないでください（API キーやパスワードを含むため）。

5. 設定の検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗として扱います:
     - python -m kabusys.validate_config --strict

6. ディレクトリ（data/ logs/）の確認
   - デフォルトの DB / PID / フラグ・ログパスは .env の値で上書きできます。デフォルト:
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper trading SQLite: data/paper_trading.db
     - PID: data/execution.pid
     - Kill flag: data/kill.flag
     - Stop flag for monitoring/execution: data/stop_requested.flag
   - ログは logs/<app_name>.log（TimedRotatingFileHandler で日次ローテーション）に出力

使い方
------

基本的な起動例（パッケージモジュールとして実行）

- ExecutionEngine（実行エンジン）を起動:
  - python -m kabusys.run_execution
  - 注意: KABUSYS_ENV=paper_trading の場合、MockBrokerClient が使われ、データは data/paper_trading.db に分離されます。

- Monitoring（監視ループ）を起動:
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更するには環境変数 MONITOR_POLL_INTERVAL を設定（秒）。例:
    - export MONITOR_POLL_INTERVAL=30
    - python -m kabusys.run_monitoring
  - 監視は監視用 SQLite（settings.sqlite_path）を使用します。Monitoring は環境に関係なく本番 sqlite_path を参照します（設計上の注意点）。

- 一時停止 / 強制停止制御:
  - ExecutionEngine の停止指示は data/kill.flag（KillSwitch）または data/stop_requested.flag によるフラグファイルで制御します。
  - stop_requested.flag が存在すると run_execution/run_monitoring は起動を抑制またはループを終了します。
  - .env の KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動でクリアします（本番では 0 推奨）。

- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: env または data/paper_trading.db

AI 機能（ニュース NLP / レジーム判定）
- 使用には OpenAI API キーが必要（環境変数 OPENAI_API_KEY または関数引数で指定）
- API 呼び出しはリトライ、レスポンス検証、スコアのクリップ等の安全機構を備えています
- OpenAI を使う処理はフェイルセーフで、失敗時は中立値（0.0 等）でフォールバックする設計です

便利なコマンド（例）
- .env を作成: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config
- 実行開始: python -m kabusys.run_execution
- 監視開始: python -m kabusys.run_monitoring
- ペーパートレード検証レポート: python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

ディレクトリ構成（主要ファイル）
-------------------------------

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数の自動読み込み、Settings クラス（各種パス・フラグの取得）
  - config_setup.py
    - .env を対話式に作るウィザード
  - validate_config.py
    - 起動前の設定検証 CLI
  - run_execution.py
    - ExecutionEngine 起動スクリプト（本番 / paper_trading 切替・PID/停止フラグ管理）
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL）
  - utils/
    - logging_setup.py — ログ設定（stdout + 日次ローテート）
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ
  - monitoring/
    - monitoring_db.py — SQLite 永続化レイヤ（テーブル作成・読み書き）
    - system_monitor.py — CPU/メモリ/ディスク・プロセス・データ鮮度監視
    - risk_monitor.py — ドローダウン / ポジション数監視
    - trade_monitor.py — （注文滞留・約定異常などの監視; 実装あり）
    - kill_switch.py — kill.flag 管理（Execution 停止）
    - monitoring_engine.py — 各 Monitor を束ねるループ
    - alert_manager.py — （通知/アラート送信管理; 実装あり）
  - execution/
    - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py
    - ブローカー抽象、発注・注文管理、リスク判定等（実装あり）
  - portfolio/
    - portfolio_builder.py — 候補選定・配分
    - position_sizing.py — 株数計算（lot 単位で丸め、aggregate cap）
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — モメンタム・ボラティリティ・バリュー等ファクター計算
    - feature_exploration.py — 将来リターン、IC、統計サマリ
  - ai/
    - news_nlp.py — ニュースを LLM で評価して ai_scores に書き込む
    - regime_detector.py — ma200 + LLM で市場レジームを判定して market_regime に書き込む
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成スクリプト

運用上の注意
--------------
- .env / シークレットは絶対にリポジトリにコミットしないこと
- KABUSYS_ENV が "live" の場合は十分に注意して設定を確認してください（validate_config の警告機能を利用）
- Monitoring は設計上、本番 sqlite_path を参照します（環境に依らず同じ監視 DB を使う）。必要なら .env でパスを分けてください
- run_execution/run_monitoring は stop_requested.flag / kill.flag によるファイルフラグで制御できます。自動化・プロセスマネージャーから起動する場合はフラグファイルの扱いに注意してください

貢献
----
バグ修正・機能追加はプルリクエストを送ってください。テストと validate_config のチェックを追加するとレビューが通りやすくなります。

ライセンス
---------
（プロジェクトに合わせて適切なライセンスをここに追記してください）

以上。README の内容で不足している情報（例: 依存パッケージのバージョンや実行時の追加オプションなど）があれば教えてください。必要に応じて追記します。