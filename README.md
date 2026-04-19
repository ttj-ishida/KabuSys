README
=====

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤です。  
主な機能として以下を持ちます。

- 発注・注文管理を行う ExecutionEngine（実運用 / ペーパートレード対応）
- システム稼働状況・注文状態・リスク監視（Monitoring）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算）
- ファクター計算・特徴量解析（DuckDB を用いたオンディスク分析）
- ニュース NLP によるセンチメント評価（OpenAI API 利用）
- 市場レジーム判定（ETF とマクロニュースの合成）
- ペーパートレード検証レポート生成ツール
- .env 対話式設定ウィザード / 起動前設定検証 CLI

設計方針の要点
- 本番（live）とペーパートレード（paper_trading）で DB を分離。
- 可能な限りフェイルセーフ（API 失敗はフォールバックして継続）。
- ルックアヘッドバイアス回避のため日時の扱いに配慮。
- ログはコンソールと日次ローテートファイルの両方に出力。

主な機能一覧
----------------
- Execution
  - ExecutionEngine：ブローカークライアントを使って発注を実行・監視
  - Paper trading：KABUSYS_ENV=paper_trading で MockBrokerClient を使用、data/paper_trading.db に記録
  - 停止制御：data/stop_requested.flag（手動停止）および data/kill.flag（Kill Switch）

- Monitoring
  - SystemMonitor：CPU/メモリ/ディスク・データ鮮度・Execution プロセス監視
  - TradeMonitor：注文の滞留・約定異常の検出（コード内に該当実装あり）
  - RiskMonitor：ドローダウン / ポジション上限のチェックとリスクログ記録
  - MonitoringEngine：上記をまとめてポーリング、アラート管理・Kill Switch 発動

- Portfolio
  - 候補選定（select_candidates）
  - 等金額・スコア加重の重み計算
  - ポジションサイズ決定（リスクベース含む）
  - セクター集中制限、レジーム乗数適用

- Research / Tools
  - ファクター計算（モメンタム、ボラティリティ、バリュー等）
  - Feature exploration（IC, 統計サマリ等）
  - Paper Trading 検証レポート生成（kabusys.tools.paper_verification_report）

- AI
  - news_nlp: OpenAI を用いたニュースセンチメントの銘柄別スコア化（ai_scores 書き込み）
  - regime_detector: MA200 とマクロニュースを合成した市場レジーム判定

セットアップ手順
----------------

前提
- Python 3.9+ を推奨（duckdb / psutil / openai 等が必要）
- システムに応じて psutil の一部機能は管理者権限を要する場合があります

1) 仮想環境の作成（推奨）
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate

2) 依存パッケージのインストール
   pip install duckdb psutil openai

   補足:
   - PyYAML を入れると config/*.yaml の構文チェックが可能になります（validate_config が利用）
   - requirements.txt がない場合は上記の主要パッケージを個別に追加してください

3) プロジェクトルートに data と logs ディレクトリを用意（多くのスクリプトが自動作成するため任意）
   mkdir -p data logs

4) .env の作成
   - 対話式ウィザードを使う:
     python -m kabusys.config_setup
   - 必須環境変数（例）:
     JQUANTS_REFRESH_TOKEN（必須）
     KABU_API_PASSWORD（必須）
     その他: KABUSYS_ENV, DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL, LINE_* など
   - デフォルト:
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     KABUSYS_ENV=development

5) 設定検証（任意だが推奨）
   python -m kabusys.validate_config
   --strict を付けると警告も失敗として扱います。

使い方（主要なコマンド）
-----------------------

起動スクリプト（パッケージモジュールとして実行）
- ExecutionEngine を起動（デーモン / フォアグラウンド問わず）
  python -m kabusys.run_execution

  動作ポイント:
  - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録
  - 起動時に data/stop_requested.flag が存在する場合は起動せず終了
  - 実行中に data/stop_requested.flag を作成すると安全に停止する
  - 実行中は data/execution.pid に PID を書き込みます（設定で変更可）

- Monitoring を起動
  python -m kabusys.run_monitoring

  オプション/環境変数:
  - MONITOR_POLL_INTERVAL: ポーリング間隔を秒で上書き（デフォルト: 60）
  - Monitoring は KABUSYS_ENV に関係なく本番 sqlite_path を使用して監視ログを記録します

ツール / ヘルパー
- 環境設定ウィザード（.env を生成）
  python -m kabusys.config_setup

- 設定検証
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- Paper Trading 検証レポート生成
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  オプション: --db で SQLite ファイルパスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

AI 機能（プログラムから呼び出す）
- news_nlp.score_news / regime_detector.score_regime は DuckDB 接続を受け取って動作します。直接 CLI エントリは実装されていないため、スクリプトやジョブからインポートして利用してください。
- OpenAI API キー: 環境変数 OPENAI_API_KEY、または関数引数で指定可能

停止・Kill Switch
- 手動停止（即時・安全停止）:
  - data/stop_requested.flag を作成すると run_execution/run_monitoring は検知して停止します
- Kill Switch（自動停止トリガ）:
  - RiskMonitor 等が条件を満たすと data/kill.flag を書き込みます。ExecutionEngine は起動時にこれを検出し、また明示的に存在をチェックして停止判定を行います
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動でクリアします（本番では 0 推奨）

設定項目（主な環境変数）
- JQUANTS_REFRESH_TOKEN — 必須（J-Quants API）
- KABU_API_PASSWORD — 必須（kabuステーション API）
- KABUSYS_ENV — execution モード: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（デフォルト: INFO）
- OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector で使用）
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0）

ディレクトリ構成
----------------
以下は主要ファイル・ディレクトリの抜粋（src/kabusys 以下を想定）。

- src/kabusys/
  - __init__.py
  - run_execution.py            # ExecutionEngine 起動スクリプト
  - run_monitoring.py          # Monitoring 起動スクリプト
  - config.py                  # 環境変数 / 設定読み込みロジック
  - config_setup.py            # .env 対話式ウィザード
  - validate_config.py         # 起動前設定検証 CLI
  - utils/
    - logging_setup.py         # ログ設定ユーティリティ（console + 日次ローテート）
    - process_priority.py      # プロセス優先度 / CPU affinity 設定
  - execution/                 # 発注・注文管理関連（BrokerFactory 等）
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - risk_manager.py
    - reconciler.py
    - broker_factory.py
  - monitoring/
    - monitoring_db.py         # SQLite schema + 永続化ロジック
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
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
  - data/                      # 実行時に作成される想定のローカルデータディレクトリ
  - logs/                      # デフォルトログディレクトリ（ログは日次ローテート）

データベース・ログ
- DuckDB（分析用）: data/kabusys.duckdb（環境変数 DUCKDB_PATH）
- SQLite（監視）: data/monitoring.db（環境変数 SQLITE_PATH）
- SQLite（ペーパートレード）: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH）
- ログ: logs/<app_name>.log（TimedRotatingFileHandler、日次、30日保持）

開発者向けメモ
- Logging: setup_logging(app_name="...") を各起動ポイントで呼んで統一したログ出力を行う
- process priority: 起動直後に set_process_priority("high") を呼んで重要プロセスの優先度を上げる設計
- DB スキーマ: monitoring_db.init_monitoring_db で必要テーブルとマイグレーションを作成
- テスト: モジュール化されているため個別関数のユニットテストが書きやすい（外部 API はモック可能）

よくある質問（Q&A）
- Q: 本番とペーパートレードの DB は分離されていますか？
  - A: はい。KABUSYS_ENV=paper_trading の場合、Execution は paper_sqlite_path（デフォルト data/paper_trading.db）を使用します。Monitoring は常に本番 sqlite_path を参照します。

- Q: 監視プロセスのポーリング間隔を変えたい
  - A: MONITOR_POLL_INTERVAL 環境変数で秒を設定します（最小 1 秒）。不正値はデフォルト 60 秒にフォールバックします。

- Q: Kill Switch の自動クリアを無効にしたい
  - A: KILL_FLAG_CLEAR_ON_START=0（デフォルト）を設定してください。本番環境では 0 を推奨します。

ライセンス / バージョン
- パッケージバージョンは kabusys.__version__ にて管理（現在: 0.1.0）

最後に
------
この README はコードベースの主要機能と運用上のポイントをまとめたものです。詳細な実装や追加のユーティリティについては各モジュール（例: monitoring/*.py, ai/*.py, portfolio/*.py）を参照してください。質問や改善提案があれば README の更新やコードコメントの追加を検討してください。