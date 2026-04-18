README
======

概要
----
KabuSys は日本株の自動売買・研究・監視を目的とした小規模なシステム群です。本リポジトリには以下の主要機能が含まれます。

- 発注実行エンジン（ExecutionEngine）
- 監視・アラート系（Monitoring）
- ポートフォリオ構築・ポジションサイズ計算（portfolio）
- ファクター/リサーチ計算（research）
- ニュース NLP / レジーム判定（AI モジュール）
- 開発向けツール（設定ウィザード・設定検証・ペーパートレード検証レポート）

設計方針の要点
- 環境変数（.env）で設定を管理。Settings クラスで一元取得。
- paper_trading モードは本番 DB と分離（data/paper_trading.db）。
- ロギングは統一的に setup_logging() を使用し、console と日次ローテートファイル出力を提供。
- OpenAI を利用する処理は API キーを外部から渡すか環境変数で指定。失敗時はフォールバックして継続する設計。

機能一覧
--------
主な機能と CLI / API:
- 設定ウィザード: python -m kabusys.config_setup
  - 対話式に .env を作成 / 更新します。
- 設定検証: python -m kabusys.validate_config [--strict]
  - .env および config/*.yaml を起動前にチェック。
- 実行エンジン起動: python -m kabusys.run_execution
  - KABUSYS_ENV に応じて実際のブローカー or MockBroker を利用。
  - paper_trading の場合は data/paper_trading.db を使用（本番 DB と完全分離）。
- 監視プロセス起動: python -m kabusys.run_monitoring
  - SystemMonitor をポーリングして system_status / risk_logs / trade_logs 等を記録。
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可能（デフォルト 60）。
- Paper Trading 検証レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - ペーパートレード DB を解析して稼働率・約定率・レイテンシ等を出力。
- ポートフォリオ構築関数群:
  - select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes, apply_sector_cap, calc_regime_multiplier
- AI 系:
  - kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime
  - OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント / レジーム判定（API キー必要）

セットアップ手順
----------------
1. Python 環境
   - Python 3.9+ を推奨（コードは型ヒントで pathlib / typing を使用）
2. 依存パッケージのインストール（一例）
   - pip install -r requirements.txt
   - main な依存（プロジェクト内で参照されているもの）:
     - duckdb
     - psutil
     - openai
     - PyYAML（config ファイル検証を行いたい場合）
   - （requirements.txt がない場合は上記を個別にインストールしてください）
3. .env の準備
   - 対話式で作る: python -m kabusys.config_setup
   - あるいは .env.example を参考に手動で作成。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - OpenAI を使う場合:
     - OPENAI_API_KEY を設定（score_news / score_regime に必要）
4. データディレクトリ
   - デフォルトの DB / PID / flag はプロジェクト内の data/ に置かれます。
   - ログは logs/ ディレクトリに出力されます（setup_logging が自動で作成します）。
5. 設定検証（任意）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いで exit(1)

主要な環境変数（抜粋）
---------------------
- KABUSYS_ENV: execution モード（development, paper_trading, live）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能で必要）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 DB（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の約定モード（instant|partial|never|reject）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: ExecutionEngine 起動時に kill.flag を自動クリア（0/1）

使い方（実行例）
----------------
- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- ExecutionEngine を起動（フォアグラウンド）
  - python -m kabusys.run_execution
  - 注意: KABUSYS_ENV=paper_trading を指定すると MockBroker で data/paper_trading.db に記録されます。
- Monitoring を起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Paper Trading 検証レポート（例）
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を明示する: python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
- AI 機能を直接実行（Python スクリプト、REPL から）
  - from kabusys.ai import score_news
  - score_news(duckdb_conn, target_date, api_key="...")

停止／Kill Switch の取り扱い
---------------------------
- kill.flag: data/kill.flag を作成すると ExecutionEngine に停止シグナルを送る仕組みがあります（KillSwitch）。
- stop_requested.flag: run_monitoring / run_execution が監視している停止フラグ（プロセス単位の手動停止など）。
- ExecutionEngine は起動時に KILL_FLAG_CLEAR_ON_START により kill.flag を自動クリアするオプションがあります（本番では 0 推奨）。

ログ
---
- logs/<app_name>.log に日次ローテートでログが出力されます（デフォルト 30 日保持）。
- setup_logging を各起動スクリプトが最初に呼び出しているため、ログ出力は統一されています。

ディレクトリ構成（抜粋）
-----------------------
リポジトリの主要なファイル構成を示します（src/kabusys 以下）:

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings 管理
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor 起動スクリプト
  - data/                     — データ関連（DuckDB / SQLite 等を置く想定）
  - logs/                     — ログ保存先（自動作成）
  - execution/
    - execution_engine.py     — 実行エンジン本体（エントリポイントは run_execution）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py
  - monitoring/
    - monitoring_db.py        — SQLite の永続化層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
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

注意事項 / 運用上のヒント
------------------------
- 本番運用時は KABUSYS_ENV=live を指定し、LINE 通知設定等を十分に確認してください（validate_config は live 時の注意点を警告します）。
- .env は機密情報を含むため絶対に Git にコミットしないでください（config_setup のヘッダにも注意喚起あり）。
- OpenAI の利用はコストとレイテンシに注意。API エラーやレート制限に対してリトライ処理を含む設計ですが、運用ルールを決めてください。
- psutil によるプロセス優先度設定や CPU affinity は権限が必要な場合があります。アクセス権限がないと警告を出してスキップされます。

貢献・拡張案
------------
- stocks マスタに単元（lot_size）や銘柄別メタ情報を持たせ、position_sizing を拡張する。
- Paper Trading 検証を CI に組み込み、定期レポートを自動化する。
- AI 部分のテストカバレッジ強化（外部 API 呼び出しをモックしてユニットテストを整備）。

ライセンス
---------
（プロジェクトのライセンス情報をここに記載してください）

以上。README の内容で不足している点や、特定スクリプトの使い方を詳しく知りたい箇所があれば教えてください。追加でサンプル .env テンプレートや具体的な起動例を作成します。