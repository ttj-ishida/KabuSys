KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買システム／研究ツール群のコードベースです。  
このリポジトリには、以下のような主要機能を提供するモジュールが含まれます。

- ExecutionEngine（発注・注文管理・リスク管理）
- Monitoring（システム稼働監視・アラート・Kill Switch）
- Portfolio 建設（候補選定・重み算出・ポジションサイジング）
- Research（ファクター計算・特徴量解析）
- AI（ニュース NLP によるセンチメント、レジーム判定）
- 各種ユーティリティ（ログ設定・プロセス優先度設定・設定ウィザード）
- 運用支援ツール（Paper Trading レポート等）

機能一覧
--------
主な機能と特徴（抜粋）：

- 環境設定管理
  - .env 自動ロード（プロジェクトルートに基づく）
  - 対話式設定ウィザード（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）
- 実行エンジン
  - 本番 / ペーパートレードを切り替え可能（KABUSYS_ENV）
  - Paper Trading 時は MockBroker を使い data/paper_trading.db に分離保存
  - 発注履歴・トレードログを SQLite ／ DuckDB に保存
- 監視（Monitoring）
  - system / trade / risk の各種モニタリング
  - Kill Switch（条件達成時に data/kill.flag を書き込み ExecutionEngine を停止）
  - 監視ループ (run_monitoring) は MONITOR_POLL_INTERVAL で間隔指定可
- ポートフォリオ構築
  - 候補選定、等配分・スコア加重配分、ポジションサイジング、セクターキャップ、レジーム乗数
- 研究（Research）
  - Momentum / Value / Volatility 等のファクター計算（DuckDB ベース）
  - 将来リターン・IC・統計サマリーなど
- AI（OpenAI）
  - ニュースをまとめて LLM でセンチメント評価し ai_scores テーブルへ格納
  - レジーム判定（ETF MA200 + マクロニュースの LLM 評価）
  - OpenAI API の呼び出しはリトライ・バックオフ済みの安全実装
- ツール
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）

前提 / 依存（代表例）
-------------------
主な Python ライブラリ（環境によって差分あり）:

- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML（config/*.yaml の検証を行う場合に推奨）

セットアップ手順
----------------

1. リポジトリをクローンして作業ディレクトリへ移動
   - 例: git clone ... && cd <repo>

2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - On Unix/macOS: source .venv/bin/activate
   - On Windows: .venv\Scripts\activate

3. 必要パッケージをインストール
   - pip install -r requirements.txt
   - （requirements.txt が無い場合は最低限: pip install duckdb psutil openai）

4. データ・ログディレクトリ作成（自動的に作るコードが多いですが予め用意する場合）
   - mkdir -p data logs

5. .env を作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
   - ウィザードは J-Quants トークンや kabuAPI のパスワード等を対話式で設定して .env を生成します。

6. 設定検証
   - python -m kabusys.validate_config
   - 警告もエラー扱いにしたい場合は --strict を付ける

主な環境変数（代表）
-------------------
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db） — Monitoring は環境に関わらず本番 sqlite_path を使う
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading 時のフィル（instant|partial|never|reject）
- OPENAI_API_KEY: OpenAI を使う場合に必要
- LOG_LEVEL / LOG_DIR
- KILL_FLAG_CLEAR_ON_START: 起動時に data/kill.flag を自動でクリアするか (0/1)

使い方（主なスクリプト）
-----------------------

- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳格モード: python -m kabusys.validate_config --strict

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - 振る舞い:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db に保存（本番 DB と分離）
    - プロセス優先度を "high" に設定し、PID ファイル(data/execution.pid) を管理
    - data/stop_requested.flag が存在すると起動を中止または実行中に停止

- 監視ループ起動（Monitoring）
  - MONITOR_POLL_INTERVAL によりポーリング間隔を秒で上書き可能（デフォルト 60）
  - python -m kabusys.run_monitoring
  - 監視は Settings にある sqlite_path を常に使用（環境に関係なく本番監視 DB を利用）
  - 監視処理は system/trade/risk を順次実行し、KillSwitch の評価やアラート通知を行う

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 範囲指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH （PAPER_TRADING_SQLITE_PATH 環境変数で指定可能）

停止・Kill フラグの使い分け
-------------------------
- run_execution / run_monitoring の両方が参照する停止フラグ: data/stop_requested.flag
  - このファイルが存在すると起動を中止、または実行中にループを抜けて終了します。
- Kill Switch（自動停止判定）: data/kill.flag
  - Monitoring 側で条件を満たすと kill.flag を書き込み、ExecutionEngine 停止トリガーになる仕組みです。
  - Settings.kill_flag_clear_on_start = 1 の場合、Execution 起動時に kill.flag を自動削除する設定があります（本番では 0 推奨）。

ログ
----
- ログはデフォルトで logs/<app_name>.log に日次ローテートで保存されます（30日分保持）。
- 標準出力にもログが出力されます（StreamHandler は stdout を使用）。
- ログレベルは LOG_LEVEL 環境変数で調整可能（デフォルト: INFO）。

AI 機能
-------
- news_nlp / regime_detector は OpenAI API を利用します。OPENAI_API_KEY を設定してください。
- OpenAI 呼び出しはリトライ・バックオフ・レスポンス検証（JSON 検証）を含む実装です。
- API キー未設定時は ValueError を発生させるか、フォールバック値（0.0）で継続する実装があるため、挙動に注意してください。

DuckDB / データベース
---------------------
- DuckDB は主に研究・ファクター計算、AI バッチ処理の中間集計に使用します（settings.duckdb_path）。
- 監視・注文ログは SQLite（settings.sqlite_path / paper_sqlite_path）に保存されます。
- monitoring_db.init_monitoring_db は初期テーブル作成・簡易マイグレーションを行います（冪等実行）。

ディレクトリ構成（主なファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py                 — 環境変数・設定取得ロジック
- config_setup.py           — 対話式 .env ウィザード
- validate_config.py        — 設定検証 CLI
- run_execution.py          — ExecutionEngine 起動スクリプト
- run_monitoring.py         — Monitoring 起動スクリプト

サブパッケージ（主要）
- ai/
  - news_nlp.py             — ニュース NLP（センチメント）処理
  - regime_detector.py      — レジーム判定
- monitoring/
  - monitoring_db.py        — SQLite 永続化レイヤ
  - monitoring_engine.py
  - system_monitor.py
  - trade_monitor.py        — （trade_monitor 実装あり）
  - risk_monitor.py
  - kill_switch.py
  - alert_manager.py        — （アラート送信ロジック）
- execution/
  - execution_engine.py
  - order_manager.py
  - order_repository.py
  - broker_factory.py
  - reconciler.py
  - risk_manager.py
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- utils/
  - logging_setup.py
  - process_priority.py
- tools/
  - paper_verification_report.py

（プロジェクトルート）
- .env.example (想定)
- config/ (yaml 設定ファイル群)
- data/ (runtime DB / flag / pid 等を置く)
- logs/ (ログファイル)

運用上の注意
------------
- 本番（KABUSYS_ENV=live）では設定を慎重に確認してください。validate_config は本番向けの追加警告を出します。
- kill.flag の自動クリア設定（KILL_FLAG_CLEAR_ON_START）は、本番では無効（0）を推奨します。
- OpenAI を使う処理は API コストとレイテンシを伴います。キー管理と呼び出し頻度に注意してください。
- Paper Trading は本番 DB と分離される設計ですが、設定ミスで DB を混在させないよう注意してください（PAPER_TRADING_SQLITE_PATH を確認）。

開発者向けメモ
--------------
- 設定ファイル（config/*.yaml）の生成スクリプトが用意されている場合はそれを使って作成してください（validate_config は存在チェックと YAML パース検証を行います。PyYAML が無ければ YAML 検証はスキップされます）。
- ロギングは全起動スクリプトから setup_logging を呼ぶことで統一されます。
- プロセス優先度 / CPU affinity の設定は utils.process_priority に集約されています（psutil に依存）。

ライセンス / バージョン
-----------------------
- パッケージバージョン: __version__ = "0.1.0"（src/kabusys/__init__.py）

以上が本リポジトリの概要・セットアップ・使い方の要点です。  
必要であれば、README に加えて .env.example のサンプルや systemd / supervisord 用の起動例、運用手順（デプロイ・ロールバック・監視アラート対応フロー）などの追加章を作成します。どの内容を追加したいか教えてください。