README
======

概要
----
KabuSys は日本株向けの自動売買 / リサーチ / モニタリング向けライブラリ群です。  
主に以下の機能を持ち、プロダクションやペーパートレードの運用を想定した設計になっています。

- 注文実行エンジン（ExecutionEngine）
- 監視 / アラート / Kill Switch（Monitoring）
- ポートフォリオ構築（候補選定・重み計算・ポジションサイズ決定）
- ファクター計算・特徴量解析（Research）
- ニュースの NLP スコアリング・市場レジーム判定（AI モジュール、OpenAI 使用）
- ペーパートレード検証レポート生成ツール

特徴
----
- 環境変数 / .env による簡単な設定管理（自動読み込み）
- ペーパートレード時は実口座とデータが完全分離（専用 SQLite）
- DuckDB を使ったリサーチ用高速集計
- ロギングは統一的に設定（コンソール + 日次ローテーションファイル）
- プロセス優先度設定、CPU affinity のユーティリティを提供
- モジュールは純粋関数化と副作用の分離を意識して設計

前提・依存
-----------
推奨 Python バージョン: 3.10 以上（Union 型演算子などを使用）。

主なサードパーティ依存:
- duckdb
- psutil
- openai
- PyYAML（config 検証を行う場合に必須。無い場合は警告でスキップされます）

セットアップ手順
----------------

1. リポジトリをクローンしてワークディレクトリにする。

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install duckdb psutil openai PyYAML
   （requirements.txt がある場合は pip install -r requirements.txt）

4. .env を作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - もしくは手動で .env をプロジェクトルートに配置
   - 自動ロード: デフォルトで .env と .env.local が読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）

5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 必要に応じて --strict（警告も失敗扱い）

6. 初期 DB / ディレクトリ
   - monitoring / execution の起動時に必要フォルダ（data/, logs/）は自動作成を試みますが、権限等に注意してください。

主要な環境変数（抜粋）
---------------------
必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード

運用・挙動:
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — ペーパートレードの約定挙動: instant / partial / never / reject（デフォルト: instant）
- OPENAI_API_KEY — OpenAI API キー（AI モジュール使用時）
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、run_monitoring で使用。デフォルト 60）
- KILL_FLAG_CLEAR_ON_START — Execution 起動時に kill.flag を自動でクリアするか（0/1。デフォルト 0）

使用方法
--------

起動スクリプト
- 監視ループ（SystemMonitor）を起動:
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒で上書きできます（例: MONITOR_POLL_INTERVAL=30）。
  - 監視は本番 sqlite_path（Settings.sqlite_path）を常に使用します。

- 実行エンジン（ExecutionEngine）を起動:
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH に記録します。
  - 起動時に data/execution.pid を書き、data/stop_requested.flag / data/kill.flag を使った停止制御をサポートします。

設定関連ツール
- 対話式 .env 作成:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い（exit code 1）

ユーティリティ / ツール
- ペーパートレード検証レポート:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定: --db / 環境変数 PAPER_TRADING_SQLITE_PATH でパス指定可能

ライブラリ API（代表例）
- ポートフォリオ構築:
  - from kabusys.portfolio import select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes
- リサーチ / ファクター:
  - from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary
- AI:
  - from kabusys.ai import score_news
    - score_news(conn, target_date, api_key=None) — DuckDB 接続と日付を渡してニューススコアを生成・DB に書き込む
  - regime_detector.score_regime(conn, target_date, api_key=None) — market_regime を書き込む
- 監視 DB 操作:
  - kabusys.monitoring.monitoring_db.MonitoringDB — system_status / trade_logs / risk_logs / dashboard などへの読み書きを提供

停止・Kill Switch
- 実行系の強制停止は data/kill.flag を書き込んで指示できます（KillSwitch が検出すると ExecutionEngine は安全に停止します）。
- run_monitoring / run_execution は data/stop_requested.flag や data/execution.pid を参照して起動・停止の制御を行います。

ログ
---
- ログはデフォルトで logs/ に出力され、アプリごとに日次ローテーションされます（例: logs/execution.log, logs/monitoring.log）。
- コンソールには標準出力（stdout）へも出力されます。

ディレクトリ構成（主要ファイル）
------------------------------
以下はリポジトリ内の主要なファイル・ディレクトリ構成（抜粋）です:

- pyproject.toml / setup.cfg / requirements.txt (プロジェクトルート)
- .env, .env.local (環境変数ファイル) — .env は絶対に Git にコミットしないでください
- config/
  - system_config.yaml
  - data_config.yaml
  - strategy_config.yaml
  - risk_config.yaml
  - execution_config.yaml
  - monitoring_config.yaml
- data/  (実行時に作られることが多い)
  - monitoring.db (デフォルト)
  - paper_trading.db (ペーパートレード用)
  - kill.flag
  - stop_requested.flag
  - execution.pid
- logs/  (ログファイル)
- src/
  - kabusys/
    - __init__.py
    - config.py
    - config_setup.py
    - validate_config.py
    - run_monitoring.py
    - run_execution.py
    - utils/
      - logging_setup.py
      - process_priority.py
    - monitoring/
      - __init__.py
      - monitoring_db.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - monitoring_engine.py
      - kill_switch.py
      - alert_manager.py
    - execution/  (注文エンジン関連)
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
      - __init__.py
    - tools/
      - paper_verification_report.py

注意事項 / 運用上のヒント
-------------------------
- .env は機密情報（API キー等）を含むため必ず管理に注意してください（Git 管理外へ）。
- 本番運用時は KABUSYS_ENV=live を設定します。validate_config は本番向けの追加チェック（LINE 設定等）を行います。
- Kill Switch 設定（KILL_FLAG_CLEAR_ON_START）を本番で 1 にするのは危険です（自動クリアにより停止命令が取り消される可能性）。
- OpenAI を使う機能は API キーと呼び出しコストが発生するため、使用時に注意してください。API 呼び出しエラーはフェイルセーフ（多くはスコア 0.0 等にフォールバック）で設計されていますが、運用ルールは必ず検討してください。
- DuckDB / SQLite のパスは環境変数で上書き可能。ペーパートレード時には専用 DB を使うことを推奨します。

拡張ポイント
-------------
- broker_factory を差し替えて別ブローカーの実装を追加可能
- research / ai モジュールは DuckDB のテーブル構成に依存しているため、データ取り込みパイプラインを実装すれば即座に利用できます
- monitoring の AlertManager は通知チャネル（LINE 等）をプラグインで追加可能

ライセンス・貢献
----------------
- LICENSE ファイルを参照してください（このリポジトリの配布に従ってください）。
- バグ報告や PR は Issue/PR で受け付けてください。

以上です。必要であれば、README にサンプル .env.example、起動ログ例、よくあるトラブルシューティング（権限エラー、DB ロック、OpenAI タイムアウト等）を追加します。どの情報を補足しますか？