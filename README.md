KabuSys — 日本株自動売買システム
=================================

概要
----
KabuSys は日本株向けの自動売買システム / 研究用ライブラリ群です。本リポジトリには、
- 実行エンジン（ExecutionEngine）／発注ロジック
- 監視コンポーネント（Monitoring）
- ポートフォリオ構築ユーティリティ（候補選定・配分・ポジションサイズ）
- 研究用ファクター計算・特徴量解析
- ニュース NLP / レジーム判定（OpenAI を利用）
- 環境設定ウィザード・設定検証ツール
- ペーパートレード検証レポート生成ツール
などが含まれます。

主要な設計方針
- 実行（本番）とペーパートレード（paper_trading）を分離（専用 SQLite DB を使用）
- DuckDB を分析用 DB として利用
- .env による環境変数管理（config_setup で対話的生成）
- OpenAI API 呼び出しはフェイルセーフ設計（リトライ、部分失敗保護）
- 監視はファイルフラグ（data/kill.flag, data/stop_requested.flag）で外部制御可能

機能一覧
--------
- 環境設定ウィザード: python -m kabusys.config_setup
- 設定検証 CLI: python -m kabusys.validate_config
- 実行エンジン起動スクリプト: src/kabusys/run_execution.py
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い data/paper_trading.db を使用
  - 停止は data/stop_requested.flag を作ることで行える
- 監視ループ起動スクリプト: src/kabusys/run_monitoring.py
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）
  - 監視は本番 sqlite_path を参照（環境にかかわらず）
- 監視 DB 永続化層（SQLite）: kabusys.monitoring.monitoring_db
  - system_status, trade_logs, positions, risk_logs, dashboard テーブルを管理
- MonitoringEngine: 各種 Monitor（System / Trade / Risk）を束ねてポーリングとアラート発火
- ポートフォリオ構築:
  - 候補選定・スコア順ソート（select_candidates）
  - 等配分 / スコア加重配分（calc_equal_weights, calc_score_weights）
  - ポジションサイズ計算（calc_position_sizes） — リスク制約・単元株丸め含む
  - セクターキャップ適用、レジーム乗数（apply_sector_cap, calc_regime_multiplier）
- 研究モジュール:
  - ファクター計算（momentum / value / volatility）
  - 将来リターン計算、IC 計算、統計サマリー
- AI 関連:
  - ニュース NLP による銘柄別センチメントスコア生成（kabusys.ai.news_nlp.score_news）
  - レジーム判定（kabusys.ai.regime_detector.score_regime）
  - OpenAI を呼ぶ際は API キーを利用し、リトライ・検証ロジックを備える
- ツール:
  - Paper Trading 検証レポート生成（kabusys.tools.paper_verification_report）

セットアップ手順
--------------
前提
- Python 3.10 以上（ファイル内の型表記に union 型（|）を使用しているため）
- システムに sqlite3 が利用可能
- 必要な外部パッケージ（例、duckdb, psutil, openai, PyYAML（任意: config 検証用））をインストールしてください。

例: pip を使ったインストール（仮想環境推奨）
- 必要パッケージ（一例）
  pip install duckdb psutil openai

- PyYAML は config/*.yaml のパース検証を行う場合に必要:
  pip install pyyaml

環境変数設定（.env）
- 推奨フロー:
  1. python -m kabusys.config_setup を実行して対話式に .env を生成
  2. python -m kabusys.validate_config で検証

- 重要な環境変数（必須）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 主なオプション / デフォルト
  - KABUSYS_ENV: development | paper_trading | live  （デフォルト: development）
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
  - LOG_LEVEL: INFO（DEBUG / INFO / WARNING / ERROR / CRITICAL）
  - LOG_DIR: デフォルトは logs/
  - OPENAI_API_KEY: OpenAI を使う機能（news_nlp, regime_detector）で必要

設定ファイルの自動ロード
- プロジェクトルート（.git または pyproject.toml を基準）にある .env, .env.local を自動ロードします。
- 自動読み込みを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

使い方
------

1) 設定ウィザード・検証
- .env 作成（対話式）
  python -m kabusys.config_setup
- 設定検証
  python -m kabusys.validate_config
  --strict を付けると警告も FAIL 扱い（exit code 1）

2) 実行エンジン起動（Execution）
- 単純起動（既定の環境に従う）
  python -m kabusys.run_execution
- ペーパートレードで起動する場合は .env の KABUSYS_ENV=paper_trading を設定。paper_trading では MockBrokerClient を使い data/paper_trading.db に記録されます。
- 停止方法:
  - 外部から停止フラグを立てる: data/stop_requested.flag を作成すると起動中のエンジンが検知して終了します。
  - 実行中は data/execution.pid に PID を書きます（設定によりパスは変更可）。

3) 監視ループ起動（Monitoring）
- 起動:
  python -m kabusys.run_monitoring
- ポーリング間隔の変更:
  MONITOR_POLL_INTERVAL 環境変数で秒を設定（例: MONITOR_POLL_INTERVAL=30）
- 監視は常に本番 sqlite_path を参照（監視用 DB は環境にかかわらず同じパスを使います）。
- 停止フラグ:
  data/stop_requested.flag を検知するとループを終了します。

4) Paper Trading 検証レポート
- 例:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- DB パスは環境変数 PAPER_TRADING_SQLITE_PATH または --db で指定可能。

5) AI 機能（プログラムから呼ぶ場合）
- ニュース NLP（銘柄別センチメント）:
  from kabusys.ai.news_nlp import score_news
  score_news(duckdb_conn, target_date, api_key="...")

- レジーム判定:
  from kabusys.ai.regime_detector import score_regime
  score_regime(duckdb_conn, target_date, api_key="...")

- 注意: API キーは引数か環境変数 OPENAI_API_KEY で渡す必要があります。

ログ
---
- ログ出力は kabusys.utils.logging_setup.setup_logging を通じて設定されます。
- デフォルトログディレクトリ: logs/
- ログローテーション: 日次、30 日分保持
- ログレベルは LOG_LEVEL 環境変数で制御

監視 / Kill Switch
-----------------
- KillSwitch（kabusys.monitoring.kill_switch）はリスク条件が満たされた場合に data/kill.flag を作成し、ExecutionEngine に停止シグナルを送ります。
- 設定 KILL_FLAG_CLEAR_ON_START=1 を設定するとエンジン起動時に kill.flag を自動でクリアします（本番では 0 推奨）。

ディレクトリ構成（主要ファイル）
------------------------------
以下は src/kabusys 以下の主要モジュール一覧（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理（.env 自動ロード含む）
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py             — ニュース NLP / OpenAI 呼び出し
    - regime_detector.py      — 市場レジーム判定（ma200 + macro sentiment）
  - monitoring/
    - monitoring_db.py       — SQLite テーブル定義 / MonitoringDB
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
  - execution/                — 実行エンジン関連（発注/リスク/リコンシリエーション等）
    - (各種モジュール: execution_engine, order_manager, broker_factory, ...)
  - utils/
    - logging_setup.py
    - process_priority.py
  - data/ (ランタイムで作成されるディレクトリ)
    - monitoring.db (デフォルト SQLITE_PATH)
    - paper_trading.db (PAPER_TRADING_SQLITE_PATH)
    - kabusys.duckdb (デフォルト DUCKDB_PATH)
    - kill.flag, stop_requested.flag, execution.pid などの制御ファイル

注意事項 / ベストプラクティス
----------------------------
- .env は機密情報（API キーやパスワード）を含むためリポジトリにコミットしないでください。
- 本番運用時は KABUSYS_ENV=live を慎重に設定してください。validate_config は本番用の追加警告を出します。
- OpenAI API を利用する機能はコストが発生します。API キーの管理と呼び出し回数に注意してください。
- Windows / Linux 両方で動くユーティリティを提供しますが、一部のプロセス優先度設定・CPU affinity は OS 権限により失敗する場合があります（警告ログが出てスキップされます）。

トラブルシューティング
----------------------
- .env がロードされない、或いは自動ロードを止めたい:
  KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを無効化できます。
- データベースのテーブルやカラムが足りないとき:
  monitoring_db.init_monitoring_db は冪等でテーブルを作成・簡単なマイグレーションを行います。
- OpenAI 呼び出しで頻繁に失敗する場合:
  rate limit / ネットワークの問題に起因します。news_nlp/regime_detector はリトライ実装済みですが、しきい値を超えるとスキップします。

ライセンス / 貢献
-----------------
（この README にライセンス情報やコントリビューション手順を追加してください）

最後に
------
この README はコード内ドキュメント（docstring）を元に作成しています。より詳しい設計意図やアルゴリズム（PortfolioConstruction.md など）がプロジェクト内にある場合は、そちらも参照してください。何か不明点があれば具体的な箇所を指定して質問してください。