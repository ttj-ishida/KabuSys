KabuSys
=======
日本株向けの自動売買／リサーチ基盤ライブラリおよび実行用スクリプト群です。本リポジトリは以下の責務を持ちます：

- データ（DuckDB）を用いたファクター計算・研究機能
- ポートフォリオ構築・ポジションサイズ計算ユーティリティ
- ExecutionEngine（発注エンジン）起動スクリプト（paper/live 切替対応）
- Monitoring（監視）コンポーネント（システム健全性、注文状況、リスク監視、Kill Switch）
- AI 支援モジュール（ニュースのセンチメント評価、レジーム判定）
- 開発者向けユーティリティ（.env ウィザード、設定検証、レポート生成）

はじめに
--------
この README は src/kabusys 以下のコード構成に基づき作成しています。実行には Python といくつかの外部ライブラリ（duckdb, psutil, openai など）が必要です。実行前に .env を作成し、必須の環境変数を設定してください（J-Quants / kabuステーション のクレデンシャル等）。

主な機能
--------
- Execution
  - 実際の発注を行う ExecutionEngine を起動（KABUSYS_ENV により paper_trading / live / development 切替）
  - paper_trading 時は MockBrokerClient を用いて paper_trading.db に完全分離して記録
- Monitoring
  - SystemMonitor：CPU/メモリ/ディスク、Execution プロセス存在、データ鮮度を監視して SQLite に記録
  - TradeMonitor / RiskMonitor：注文滞留、約定異常、ドローダウンやポジション上限を監視し risk_logs に記録
  - KillSwitch：重大なリスクが検出された場合 data/kill.flag を書き込み ExecutionEngine を停止させる仕組み
  - MonitoringEngine：各モニタを統合し定期ポーリング、アラート発火
- Portfolio（ポートフォリオ構築）
  - 候補抽出、等金額・スコア加重の重み計算、セクター上限適用、ポジションサイズ決定（単元丸め・規模調整）
- Research（リサーチ）
  - ファクター計算（Momentum / Volatility / Value 等）
  - 特徴量探索、Forward Returns / IC（Spearman） / 統計サマリ
- AI（LLM 統合）
  - news_nlp: raw_news を集約して OpenAI API で銘柄ごとのセンチメントを計算し ai_scores に書き込む
  - regime_detector: ETF（1321）MA とマクロニュースの LLM スコアを合成して市場レジーム判定
- ユーティリティ
  - .env ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading 検証レポート生成ツール（tools/paper_verification_report）

セットアップ手順
----------------
1. Python 環境（推奨: 3.9+）を用意し、仮想環境を作成・有効化します。
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate  (Linux/macOS)
     - .venv\Scripts\activate     (Windows)

2. 必要パッケージをインストールします（プロジェクトに requirements.txt が無い場合は最低限以下を入れてください）。
   - pip install duckdb psutil openai

   （開発用途で YAML 検証を行う場合は PyYAML も追加: pip install pyyaml）

3. .env の作成
   - 対話式ウィザードを使う（推奨）:
     - python -m kabusys.config_setup
   - または手動で .env を作成。最低限必須:
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - KABUSYS_ENV=development|paper_trading|live
   - デフォルト DB パス:
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db

4. 設定検証
   - python -m kabusys.validate_config
   - 警告もエラー扱いにする場合: python -m kabusys.validate_config --strict

5. ログディレクトリ
   - デフォルト logs/ に app ごとのログを出力します。LOG_DIR 環境変数で変更可能。

使い方（実行例）
----------------
- ExecutionEngine を起動（通常）
  - python -m kabusys.run_execution
  - paper_trading モードで起動する場合:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - 起動時に data/stop_requested.flag が存在すると起動をスキップします。
  - 実行中は data/execution.pid（デフォルト）に PID を書きます。

- Monitoring を起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔を環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60秒）
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視は常に本番 sqlite_path を使用（環境に依らず監視 DB を共有）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db --from 2026-04-01 --to 2026-04-11
  - デフォルト DB は env/PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

- .env ウィザード（再掲）
  - python -m kabusys.config_setup

- 設定検証（再掲）
  - python -m kabusys.validate_config [--strict]

ライブラリとしての利用
---------------------
- 研究・ポートフォリオ機能はライブラリ関数として利用できます。主なエクスポート：
  - kabusys.research: calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank, zscore_normalize (zscore_normalize は kabusys.data.stats 経由)
  - kabusys.portfolio: select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes, apply_sector_cap, calc_regime_multiplier
  - kabusys.ai.score_news(target_date, conn, api_key=...)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=...)

重要な環境変数（主なもの）
-------------------------
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）
- LOG_LEVEL（デフォルト: INFO）
- OPENAI_API_KEY（AI 機能利用時必須）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング秒数上書き）
- PAPER_FILL_MODE（paper_trading の約定動作: instant|partial|never|reject）

運用上の注意
-----------
- KABUSYS_ENV=live は本番環境です。設定（API トークン・Kill Switch 等）を慎重に確認してください。
- .env ファイルは絶対にリポジトリにコミットしないでください。
- Kill Switch:
  - RiskMonitor 等が致命的条件を検出すると data/kill.flag を書き込みます（ExecutionEngine はこのファイルを検知して安全停止します）。
  - 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると自動クリアされますが、本番では 0 を推奨します。
- Paper Trading:
  - paper_trading は MockBrokerClient を使用し、data/paper_trading.db に完全分離して記録します（本番 DB とは別扱い）。

ディレクトリ構成（抜粋）
-----------------------
以下は src/kabusys 内の主なファイル・モジュール（本リポジトリの一部）です。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数・設定管理
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — 優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - risk_monitor.py
    - trade_monitor.py (参照用)
    - kill_switch.py
    - alert_manager.py (参照用)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py

（注）ここに記載のない補助モジュールや外部参照ファイル（data pipeline, execution internals, broker implementations 等）が同階層に存在する想定です。

開発者向けヒント
-----------------
- ログ設定は kabusys.utils.logging_setup.setup_logging を各起動スクリプトで呼んで統一しています。ログファイルは logs/<app_name>.log に日次ローテーションで保存されます。
- 優先度設定（高優先度）は起動直後に set_process_priority("high") しています。権限がない環境では警告を出してスキップします。
- DuckDB 接続は研究系の大規模集計で使うことを想定しています。テーブル名（prices_daily, raw_financials, raw_news, ai_scores 等）が使用されます。
- OpenAI 呼び出しは堅牢化（429/タイムアウト/5xx に対するリトライ等）されていますが、APIキーとコストに注意して運用してください。

バージョン
--------
パッケージ変数 __version__ = "0.1.0"

ライセンス
---------
本ドキュメントではライセンス情報を含めていません。配布元のライセンス方針に従ってください。

サポート
-------
実装や使い方について不明点があれば、該当モジュールの docstring を参照してください。例えば各モジュールの先頭に使い方や設計方針が書かれています。

以上が本コードベースの概要と利用ガイドです。必要があれば「実行コマンドのより詳細な例」や「.env のテンプレート（例）」を追記します。どの情報を優先して追記すべきか教えてください。