README
======

概要
----
KabuSys は日本株の自動売買・リサーチ基盤を想定した Python パッケージ群です。
主に以下の機能を持ち、実行・監視・検証ツールを含みます。

- 実行エンジン（ExecutionEngine）の起動スクリプト
- 監視ループ（MonitoringEngine）とアラート/Kill Switch
- ポートフォリオ構築（候補選定・重み計算・株数算出）
- リサーチ（ファクター計算・特徴量解析）
- AI ベースのニュースセンチメント・レジーム判定（OpenAI 経由）
- ペーパートレード検証レポート生成ツール
- .env 対話式ウィザードと設定検証 CLI

主な機能
--------
- 環境ごとの DB 分離（本番 / ペーパートレード）
- Monitoring によるシステム・トレード・リスク監視と kill.flag 発行
- ExecutionEngine のリスク制御（ポジション上限・ドローダウン監視など）
- ポートフォリオ構築モジュール（等金額／スコア重み／リスクベース）
- DuckDB を用いた時系列データ処理（prices_daily, raw_financials 等を想定）
- OpenAI を使用したニュース NLP と市場レジーム判定（フェイルセーフ実装）
- 各種ユーティリティ（ログ設定・プロセス優先度設定・設定読み込み）

前提条件
--------
- Python 3.9+（ソースは型注釈を用いているため 3.9 以降を想定）
- 必要な外部パッケージ（例）
  - duckdb
  - psutil
  - openai (AI 機能利用時)
  - PyYAML (config/*.yaml の構文チェックを行う場合)
- ローカルで data/, logs/ 等のディレクトリに書き込み可能であること

セットアップ手順
----------------

1. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージのインストール（例）
   - pip install duckdb psutil openai pyyaml

   注意: requirements.txt はプロジェクトに含まれていないため、上記パッケージを必要に応じて調整してください。

3. .env の作成
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - もしくは .env.example（存在する場合）を参考に手動作成
   - 自動読み込みはデフォルトで有効（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）

4. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります。

5. データディレクトリ
   - デフォルトの DB / ファイルパス:
     - DuckDB: data/kabusys.duckdb（Settings.duckdb_path）
     - SQLite (monitoring): data/monitoring.db（Settings.sqlite_path）
     - Paper trading SQLite: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH）
     - PID / flag: data/execution.pid, data/kill.flag, data/stop_requested.flag
   - 必要に応じて .env で上書きしてください。

使い方（実行例）
----------------

- ExecutionEngine を起動（本番 or paper_trading は KABUSYS_ENV に依存）
  - python -m kabusys.run_execution
  - 注意: KABUSYS_ENV=paper_trading の場合、MockBrokerClient が使用され、データは paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）に記録されます。

- Monitoring を起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL （秒）で上書き可（デフォルト 60 秒）。
  - Monitoring は KABUSYS_ENV にかかわらず Settings.sqlite_path（監視 DB）を使用します。

- 停止制御（Kill / Stop）
  - 実行中のエンジンを外部から停止したい場合は data/stop_requested.flag を作成するとループが検知して終了します（run_monitoring / run_execution が参照）。
  - Kill Switch（監視からの強制停止）で発動するのは data/kill.flag（Settings.kill_flag_path）。KillSwitch は条件を満たすとこのファイルを書き込みます。
  - Settings.kill_flag_clear_on_start が 1 の場合、起動時に kill.flag を自動クリアします（本番環境では 0 を推奨）。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション --db で SQLite パスを指定可能。環境変数 PAPER_TRADING_SQLITE_PATH も優先されます。

- AI 機能（ニューススコア / レジーム判定）
  - OpenAI API キーが必要（環境変数 OPENAI_API_KEY または関数引数）。
  - ライブラリ関数を直接呼ぶ例（簡易）:
    - from datetime import date
      import duckdb
      from kabusys.ai.news_nlp import score_news
      conn = duckdb.connect("data/kabusys.duckdb")
      score_news(conn, date(2026, 4, 1))
  - 失敗時はフォールバック（例: スコア 0.0）して続行する設計です。

ログ
---
- ログは kabusys.utils.logging_setup.setup_logging を通じて統一的に設定されます。
- デフォルトで stdout と logs/<app_name>.log（日次ローテーション、30日保管）に出力します。
- LOG_DIR / LOG_LEVEL は .env で設定可能。

重要な環境変数（抜粋）
--------------------
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB）
- OPENAI_API_KEY（AI 機能利用時）
- LOG_LEVEL（例: INFO）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔）
- KILL_FLAG_CLEAR_ON_START（Execution 起動時に kill.flag を自動クリアするか）

ディレクトリ構成
----------------
（主要なファイル/モジュールのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数/設定管理
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前の設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト
  - utils/
    - logging_setup.py
    - process_priority.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
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
  - ai/
    - news_nlp.py
    - regime_detector.py
  - tools/
    - paper_verification_report.py

運用上の注意
------------
- Monitoring は監視 DB（Settings.sqlite_path）へログを書きます。監視と実行が同一 DB を使う設計が必要な場合は設定を合わせてください。
- run_execution は KABUSYS_ENV=paper_trading のときにペーパートレード用 DB を使うなど、環境に応じた分離を行います。実運用時は .env を適切に管理してください（.env は Git 管理対象外にすること）。
- OpenAI など外部 API を利用する機能は、API コスト・レート制限に注意してください。実装はリトライやフェイルセーフを入れていますが、運用ポリシーを設定してください。
- process_priority.set_process_priority は OS による実行権限の問題で失敗する場合があります（警告ログのみ）。

開発・拡張
----------
- DuckDB 上のテーブル（prices_daily, raw_financials, raw_news, news_symbols 等）を整備すると research / ai 機能がフル活用できます。
- monitoring_db.init_monitoring_db は既存 DB に対してマイグレーション（カラム追加）も行います。
- ユニットテストや CI は含まれていません。環境変数の自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください（テストで便利です）。

バージョン
---------
- パッケージバージョンは kabusys.__version__ で管理されています（現状 0.1.0）。

サポート / 参照
----------------
- コード内に多数の docstring・設計ノートが記載されています。各モジュールの先頭コメントを参照すると設計思想や制約がわかります。
- 不明点があれば該当モジュールの docstring を先に確認してください（例: portfolio/*.py、ai/*.py、monitoring/*.py）。

以上。