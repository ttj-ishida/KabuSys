KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤の軽量なプロジェクト構成です。本リポジトリには以下の主要機能を持つモジュール群が含まれます。

- 実行エンジン（ExecutionEngine）と監視モジュール（Monitoring）
- ペーパートレード用の分離DB／MockBroker クライアント対応
- ポートフォリオ構築（候補選定、重み付け、株数決定）
- リサーチ（ファクター計算、特徴量解析）
- ニュースNLP / レジーム検出（OpenAI を用いたスコアリング）
- 各種ユーティリティ（ログ設定、プロセス優先度設定）
- コマンドラインヘルパー（環境設定ウィザード、設定検証、検証レポート生成）

バージョン
----------
パッケージバージョン: src/kabusys/__init__.py の __version__ = "0.1.0"

主な機能一覧
-------------
- 実行／監視
  - run_execution: ExecutionEngine を起動（KABUSYS_ENV により paper_trading と本番を切り替え）
  - run_monitoring: SystemMonitor のポーリングループを起動（MONITOR_POLL_INTERVAL で間隔指定）
  - Kill Switch／監視ログ永続化（SQLite）
- ポートフォリオ
  - 候補選定（スコア順）、等重・スコア重みの計算
  - リスク調整（セクターキャップ、レジーム乗数）
  - ポジションサイズ決定（単元株整形、aggregate cap）
- リサーチ
  - ファクター（モメンタム／バリュー／ボラティリティ）計算（DuckDB を使用）
  - 将来リターン・IC や統計サマリー
- AI（OpenAI）
  - news_nlp: ニュース記事を LLM でセンチメント評価して ai_scores に書き込み
  - regime_detector: ETF とマクロニュースを合成して市場レジーム判定
- ツール
  - config_setup: 対話式で .env を生成 / 更新
  - validate_config: 起動前の設定検証（.env、config/*.yaml、パス等）
  - paper_verification_report: ペーパートレード DB からの検証レポート生成
- ユーティリティ
  - logging_setup: stdout + 日次ローテートファイルの統一設定
  - process_priority: クロスプラットフォームでプロセス優先度設定（psutil 必須）

セットアップ手順
----------------

1. Python 環境作成（推奨: venv）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存ライブラリのインストール
   - 必要ライブラリの例:
     - duckdb
     - psutil
     - openai (AI 機能を使う場合)
     - pyyaml (validate_config で YAML 検証を行いたい場合)
   - 例:
     - pip install duckdb psutil openai pyyaml

   （requirements.txt がない場合は上記を適宜インストールしてください）

3. プロジェクトルートの確認
   - リポジトリをクローンすると src/ 以下にパッケージが配置されています。
   - 実行時に .env を使う場合はプロジェクトルートに .env を作成します（config_setup 参照）。

4. 環境変数の設定（最低限必要なもの）
   - JQUANTS_REFRESH_TOKEN（必須）
   - KABU_API_PASSWORD（必須）
   - OPENAI_API_KEY（AI 機能を利用する場合）
   - KABUSYS_ENV: development / paper_trading / live（省略時は development）
   - その他（デフォルト値あり）:
     - DUCKDB_PATH (default: data/kabusys.duckdb)
     - SQLITE_PATH (default: data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (paper_trading のときの DB、default: data/paper_trading.db)
     - LOG_LEVEL, LOG_DIR, PID_FILE_PATH, KILL_FLAG_CLEAR_ON_START など

.env 作成（対話式）
- python -m kabusys.config_setup
  - ウィザード形式で .env を生成／更新します。

設定検証
- python -m kabusys.validate_config
  - --strict を付けると警告も失敗（exit 1）扱いになります。

使い方（実行例）
----------------

- 実行エンジン（ExecutionEngine）起動
  - python -m kabusys.run_execution
  - 動作:
    - 起動時にプロセス優先度を高く設定（可能なら）
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の SQLite(PAPER_TRADING_SQLITE_PATH) を使用し MockBrokerClient を利用
    - 停止シグナル: data/stop_requested.flag の存在を監視し停止
    - PID ファイル: data/execution.pid（設定で変更可能）

- 監視モジュール起動
  - python -m kabusys.run_monitoring
  - 説明:
    - SystemMonitor のポーリングループを実行
    - ポーリング間隔を環境変数 MONITOR_POLL_INTERVAL で上書き可能（秒、デフォルト 60）
    - 監視は本番 sqlite_path を常に使用（環境に関係なく監視 DB は本番のパスを参照）
    - 停止フラグ: data/stop_requested.flag

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH （PAPER_TRADING_SQLITE_PATH を上書き）
  - 出力: 標準出力にレポートをテキスト表示（稼働率・成功率・レイテンシ等）

- AI 関連（ニュース NLP / レジーム検出）
  - OpenAI API キーが必要（OPENAI_API_KEY）。関数はプログラムから呼び出す API を提供します。
  - 例: kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime を使用。

停止・Kill Switch
- ディスク上のフラグファイルで停止や強制停止を実現しています。
  - data/stop_requested.flag : 起動スクリプト run_execution/run_monitoring が監視している「停止要求」フラグ
  - data/kill.flag : KillSwitch によりExecutionEngineを停止するためのフラグ（KillSwitch は監視結果に応じて書き込み）
- KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動クリアします（本番では 0 推奨）。

ロギング
- ログは stdout（StreamHandler）とファイル（logs/<app_name>.log、日次ローテーション）に出ます。
- 環境変数:
  - LOG_LEVEL（例: DEBUG/INFO）
  - LOG_DIR（ログ出力先、デフォルト logs/）
- logging 設定は kabusys.utils.logging_setup.setup_logging で統一的に行われます。

注意事項 / 動作想定
- Paper Trading（KABUSYS_ENV=paper_trading）は本番 DB とデータ分離され、data/paper_trading.db を使用します。発注は MockBrokerClient を使うため実際の発注は行われません。
- OpenAI を利用する処理（news_nlp, regime_detector）はネットワークや API に依存します。API エラー時はフェイルセーフ（0 等のフォールバック）を行う設計ですが、API キー必須です。
- process_priority.set_process_priority は psutil を使います。権限不足等で設定できない場合は警告ログを出して継続します。
- DuckDB を使ったリサーチ関数は DuckDB 接続を受け取り SQL を実行します。prices_daily / raw_financials 等のテーブルが前提です。

ディレクトリ構成（抜粋）
--------------------

src/
  kabusys/
    __init__.py
    config.py                 -- 環境変数 / .env ロードロジック、Settings クラス
    config_setup.py           -- .env 対話式ウィザード
    validate_config.py        -- 設定検証 CLI
    run_execution.py          -- ExecutionEngine 起動スクリプト
    run_monitoring.py         -- SystemMonitor 起動スクリプト
    tools/
      __init__.py
      paper_verification_report.py
    ai/
      __init__.py
      news_nlp.py
      regime_detector.py
    monitoring/
      __init__.py (implicit)
      monitoring_db.py
      monitoring_engine.py
      system_monitor.py
      trade_monitor.py
      risk_monitor.py
      kill_switch.py
      alert_manager.py (参照実装があれば)
    execution/
      broker_factory.py
      execution_engine.py
      order_manager.py
      order_repository.py
      reconciler.py
      risk_manager.py
    portfolio/
      portfolio_builder.py
      risk_adjustment.py
      position_sizing.py
      __init__.py
    research/
      factor_research.py
      feature_exploration.py
      __init__.py
    utils/
      __init__.py
      logging_setup.py
      process_priority.py
    data/                      -- 実行時に生成されることが多いディレクトリ（DB・フラグ・PID）
  config/                      -- YAML テンプレート（system_config.yaml 等）

代表的なファイル・パス
- デフォルト DuckDB: data/kabusys.duckdb
- デフォルト 監視 SQLite: data/monitoring.db
- Paper trading SQLite: data/paper_trading.db
- PID ファイル（execution）: data/execution.pid
- 停止フラグ: data/stop_requested.flag
- Kill フラグ: data/kill.flag
- ログディレクトリ: logs/

よく使うコマンド一覧
--------------------
- .env を作成:
  - python -m kabusys.config_setup

- 設定を検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行エンジン起動:
  - python -m kabusys.run_execution

- 監視起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- ペーパートレード検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

環境変数（主なもの）
-------------------
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- OPENAI_API_KEY (AI 機能を使う場合)
- KABUSYS_ENV (development | paper_trading | live) — default: development
- DUCKDB_PATH — default: data/kabusys.duckdb
- SQLITE_PATH — default: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — default: data/paper_trading.db
- LOG_LEVEL — default: INFO
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング秒数（整数）
- KILL_FLAG_CLEAR_ON_START — 0/1（本番では 0 推奨）

追加情報 / 開発メモ
------------------
- config/*.yaml はサンプルが提供されている想定（validate_config は YAML の存在とパースをチェックします）。PyYAML が無い場合は YAML 検証はスキップされます。
- DuckDB に依存するリサーチコードは、prices_daily / raw_financials 等のテーブル定義に依存します。データ投入を忘れないでください。
- monitoring_db.init_monitoring_db は監視用テーブル作成と簡単なマイグレーションを行います。既存 DB への互換性を保つためのコードが含まれます。

お問い合わせ
------------
実装・設計に関する不明点やドキュメント改善の提案があれば README の更新をお願いします。README に記載した手順や環境変数はコード内の docstring/comment を参照して最新化してください。