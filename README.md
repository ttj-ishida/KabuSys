README
======

概要
----
KabuSys は日本株向けの自動売買・研究プラットフォームのコアライブラリ群です。
このリポジトリには以下の主要コンポーネントが含まれます。

- 実行エンジン (ExecutionEngine) — 発注・注文管理・リスク制御
- 監視コンポーネント (Monitoring) — システム状態・注文状態・リスク監視、Kill Switch
- ポートフォリオ構築ユーティリティ — 候補選定・配分・サイズ決定
- リサーチ機能 — ファクター計算・特徴量解析
- AI ユーティリティ — ニュース NLP によるセンチメント / レジーム判定
- 運用支援ツール — .env ウィザード、設定検証、Paper Trading レポート等

主な機能
--------
- 環境変数ベースの設定管理（.env 自動読み込み）
- 実行環境切替: development / paper_trading / live
  - paper_trading 時はモックブローカーと専用 SQLite（data/paper_trading.db）を使用して本番 DB と隔離
- 監視ループ（System / Trade / Risk）とアラート / Kill Switch の評価
- Paper Trading 検証レポート生成ツール
- DuckDB を用いたファクター計算・リサーチ関数群
- OpenAI を用いたニュースセンチメント評価（score_news）・レジーム判定（score_regime）
- ログ出力は console (stdout) + 日次ローテートファイル (logs/<app>.log)

前提（推奨）
------------
- Python 3.10+
- 必要な外部ライブラリ（主要なもの）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config/*.yaml の検証を行う場合）
- OS: Linux / macOS / Windows のいずれでも動作する設計

セットアップ手順
---------------
1. リポジトリをクローンし、仮想環境を作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存ライブラリをインストール
   - requirements.txt があれば: pip install -r requirements.txt
   - 無ければ主なパッケージを個別に:
     - pip install duckdb psutil openai PyYAML

3. .env を作成（対話ウィザード推奨）
   - python -m kabusys.config_setup
   - 生成後、設定を検証:
     - python -m kabusys.validate_config
     - --strict を付けると警告もエラー扱いになる: python -m kabusys.validate_config --strict

4. 必要ディレクトリの作成（通常はスクリプトが自動作成するが事前に作ることも可）
   - data/
   - logs/

主な環境変数（抜粋）
--------------------
- KABUSYS_ENV (default: development)
  - 有効値: development, paper_trading, live
  - paper_trading: 発注はモック、paper_trading 用 SQLite を使用
  - live: 本番動作（注意して設定を確認すること）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)
- PAPER_FILL_MODE (paper_trading 用、default: instant) — instant / partial / never / reject
- LOG_LEVEL (default: INFO)
- LOG_DIR (default: logs/)
- PID_FILE_PATH (default: data/execution.pid)
- KILL_FLAG_PATH (default: data/kill.flag)
- KILL_FLAG_CLEAR_ON_START (0/1) — 起動時に kill.flag を自動消去するか（本番では 0 推奨）
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、run_monitoring 用。デフォルト 60 秒）
- OPENAI_API_KEY — OpenAI を使う処理（news_nlp / regime_detector）で必要

重要な運用ファイル
------------------
- data/kill.flag — Kill Switch が書き込む停止フラグ（存在すると ExecutionEngine は停止扱い）
- data/stop_requested.flag — run_monitoring / run_execution がループ終了のために参照する停止フラグ
- data/execution.pid — ExecutionEngine の PID ファイル（run_execution にて使用）
- logs/<app>.log — 日次ローテーションされるログファイル（app は execution / monitoring 等）

起動・使い方
------------

- 実行エンジン（ExecutionEngine）を起動
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合、settings.paper_sqlite_path（デフォルト data/paper_trading.db）を使用
    - プロセス優先度を "high" に設定し、別スレッドで engine.run_session を実行
    - data/stop_requested.flag を検知するとエンジン停止処理を呼ぶ

- 監視ループ（SystemMonitor のポーリング）を起動
  - python -m kabusys.run_monitoring
  - オプション/環境:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き（秒、デフォルト 60）
    - 監視は KABUSYS_ENV に関係なく settings.sqlite_path（本番監視 DB）を使用する
  - 挙動:
    - プロセス優先度を "high" に設定
    - SystemMonitor.check_once() を定期実行し system_status 等を記録
    - data/stop_requested.flag を検知するとループを抜ける

- .env の初期作成（ウィザード）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗 (exit code 1) にする

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間を指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスは --db で指定可能（優先度: --db > 環境変数 PAPER_TRADING_SQLITE_PATH > data/paper_trading.db）

- AI（ニュース NLP / レジーム判定）
  - ライブラリ関数として提供されています（直接 CLI はありません）
  - 例（Python スニペット）:
    - from datetime import date
      import duckdb
      from kabusys.ai.news_nlp import score_news
      conn = duckdb.connect("data/kabusys.duckdb")
      score_news(conn, target_date=date(2026,4,1), api_key="sk-...")

運用上の注意
------------
- KILL_FLAG_CLEAR_ON_START を 1 にすると起動時に kill.flag を自動で削除しますが、本番では危険（誤って Kill Switch を無効化してしまう可能性がある）ため 0 を推奨します。
- run_monitoring は監視用の SQLite（settings.sqlite_path）を使用します。paper_trading 設定中でも監視 DB は本番用パスを使う点に注意してください（コードの仕様）。
- OpenAI を用いる処理には API キー（OPENAI_API_KEY）が必要です。API 呼び出しに失敗した場合は安全側のデフォルト（0.0 など）で続行する設計ですが、実運用ではレート制限や料金に注意してください。
- プロセス優先度や CPU affinity 設定はプラットフォーム依存で失敗する場合があります（アクセス権限に依存）。失敗時は警告を出してスキップします。

ディレクトリ構成（抜粋）
-----------------------
src/
  kabusys/
    __init__.py
    config.py                # 環境変数読み込み / Settings
    config_setup.py          # .env 対話ウィザード
    validate_config.py       # 起動前チェック CLI
    run_execution.py         # ExecutionEngine 起動スクリプト
    run_monitoring.py        # SystemMonitor ポーリング起動スクリプト

    ai/
      news_nlp.py            # ニュース NLP スコアリング
      regime_detector.py     # レジーム判定ロジック
      __init__.py

    monitoring/
      monitoring_db.py       # SQLite 永続化層
      system_monitor.py      # システム監視
      trade_monitor.py       # （トレード監視）
      risk_monitor.py
      monitoring_engine.py
      kill_switch.py
      alert_manager.py       # （アラート送信）※実装参照

    execution/
      execution_engine.py
      order_manager.py
      order_repository.py
      broker_factory.py
      reconciler.py
      risk_manager.py
      ...

    portfolio/
      portfolio_builder.py
      position_sizing.py
      risk_adjustment.py
      __init__.py

    research/
      factor_research.py
      feature_exploration.py
      __init__.py

    data/
      pipeline.py             # DuckDB prices 取得補助等
      stats.py                # 正規化ユーティリティ等

    tools/
      paper_verification_report.py
      __init__.py

    utils/
      logging_setup.py        # 共通ログ設定
      process_priority.py     # プロセス優先度設定
      __init__.py

その他
-----
- DB スキーマやテーブルはコード内で冪等に作成/マイグレーションされます（例: monitoring_db.init_monitoring_db）。
- config/*.yaml 系ファイルのテンプレート生成スクリプトやサンプルがある場合はそれを利用して環境を整えてください（validate_config が存在をチェックします）。
- この README はコードベースの説明に基づく要約です。細かな動作や拡張箇所は該当ソース（各モジュールの docstring）を参照してください。

問い合わせ / 貢献
-----------------
バグ報告や改善提案は Issue を立ててください。拡張や修正はプルリクエストで歓迎します。