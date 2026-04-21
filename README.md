KabuSys — 日本株自動売買システム
=============================

概要
----
KabuSys は日本株の自動売買／リサーチ基盤を想定した Python パッケージです。  
主な目的は次のとおりです。

- 売買シグナルに基づくポートフォリオ構築と発注（ExecutionEngine）
- システム稼働状況・注文動作・リスク監視（Monitoring）
- DuckDB を用いたファクタ計算・リサーチ機能（Research）
- ニュースの NLP スコアリングや市場レジーム判定などの AI 支援機能
- ペーパートレード用の分離された DB と検証ツール

本リポジトリはライブラリとしての純粋関数群（ポートフォリオ構築・ポジションサイズ計算等）と、起動スクリプト／CLI ツール群（実行エンジン、監視ループ、設定ウィザード、検証レポート等）を含みます。

主な機能
--------
- ExecutionEngine 起動スクリプト（run_execution.py）
  - KABUSYS_ENV に応じて本番/ペーパートレードを切替
  - BrokerClientFactory によるブローカー抽象化
  - リスク管理（RiskManager）、注文管理（OrderManager）、突合（Reconciler）等と連携
- Monitoring（run_monitoring.py / monitoring package）
  - SystemMonitor: CPU/メモリ/ディスク使用率、データ鮮度、Execution プロセス検出
  - TradeMonitor: 発注ログの監視（滞留注文、約定異常等）
  - RiskMonitor: ドローダウン・ポジション上限監視と警告
  - KillSwitch: フラグファイルにより ExecutionEngine を停止させる仕組み
  - AlertManager（通知送信機能）を経由したアラート発行（実装場所）
- Research（research package）
  - ファクター計算（momentum, volatility, value 等）
  - 将来リターン、IC 計算、統計サマリーなどの分析ユーティリティ
- Portfolio（portfolio package）
  - 銘柄選定、等ウェイト/スコア加重、リスク調整（セクター上限、レジーム乗数）
  - ポジションサイズ計算（単元丸め、aggregate cap 処理）
- AI（ai package）
  - news_nlp: OpenAI を使ったニュースセンチメントスコア生成（ai_scores テーブルへ書き込み）
  - regime_detector: ETF とマクロニュースを合成して市場レジーム判定
- Tools
  - paper_verification_report: ペーパートレード検証レポート生成 CLI
- 設定管理・検証
  - config_setup.py: .env を対話的に作成
  - validate_config.py: 環境変数・config/*.yaml の静的検証

前提条件 / 依存関係
-------------------
- Python 3.10+
- 推奨ライブラリ（pip でインストール）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config/*.yaml の検証を行う場合）
- 組み込み DB: SQLite（標準ライブラリ）
- そのほか、実環境では kabuステーション API 接続などの外部要素が必要

セットアップ手順
----------------

1. リポジトリをクローンし、仮想環境を作成
   - python -m venv .venv
   - source .venv/bin/activate（Windows: .venv\Scripts\activate）

2. 依存パッケージをインストール
   - pip install duckdb psutil openai PyYAML
   - （必要に応じてその他のパッケージを追加）

3. .env の作成（対話ウィザード推奨）
   - python -m kabusys.config_setup
   - ウィザードでは必須項目として JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD などを入力してください。
   - 生成した .env は Git にコミットしないでください。

4. 設定の検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります（exit code 1）。

5. データディレクトリ・ログディレクトリ
   - デフォルトの DB / ファイルパスは data/、ログは logs/ に出力されます。
   - 必要に応じて .env の DUCKDB_PATH / SQLITE_PATH / LOG_DIR 等を調整してください。

環境変数（主要）
----------------
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV（development | paper_trading | live） — 環境切替
  - paper_trading: MockBroker を使用し data/paper_trading.db に記録
- OPENAI_API_KEY — news_nlp / regime_detector 実行時に必要
- DUCKDB_PATH（既定: data/kabusys.duckdb）
- SQLITE_PATH（既定: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（既定: data/paper_trading.db、paper_trading モード時）
- LOG_LEVEL（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL（監視ループの間隔秒数、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START（ExecutionEngine 起動時に kill.flag を自動クリアするか、0/1）

使い方（主要 CLI / 起動スクリプト）
-------------------------------

- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine を起動（取引実行）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合はペーパートレード用の DB を使用します
  - 起動時に data/stop_requested.flag が存在するとエンジンは起動しません
  - 実行中に data/stop_requested.flag を作成するとエンジン停止を試みます

- Monitoring を起動（ポーリング監視）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数で監視間隔を秒単位で上書き可能（デフォルト 60）
  - 監視は常に本番の sqlite_path を参照（環境にかかわらず）

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - オプション: --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
  - 簡易的に稼働率・約定率・レイテンシ等を集計して PASS/FAIL を出力

- AI / Research API（ライブラリとして利用）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - kabusys.research.calc_momentum(conn, date), calc_volatility, calc_value 等
  - DuckDB 接続（duckdb.connect）を渡して利用します

監視・停止フラグ
----------------
- data/kill.flag: KillSwitch により書き込まれるファイル。存在すると ExecutionEngine は停止対象に（停止はフラグ読み取りの実装に依存）。
- data/stop_requested.flag: run_monitoring/run_execution で外部からの停止要求を検知するために使用。
- PID ファイル: data/execution.pid（ExecutionEngine が使用）

ログ
----
- ログはデフォルトで logs/<app_name>.log に日次ローテーション（30日保存）で出力されます
- setup_logging() により標準出力（stdout）にも出力されます

ディレクトリ構成（主要ファイル）
-------------------------------

- src/kabusys/
  - __init__.py — パッケージ定義
  - config.py — 環境変数ロード・Settings クラス
  - config_setup.py — .env 対話ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - ai/
    - news_nlp.py — ニュース NLP スコアリング（OpenAI 経由）
    - regime_detector.py — 市場レジーム判定（MA + LLM）
  - research/
    - factor_research.py — モメンタム/ボラティリティ/バリュー等
    - feature_exploration.py — forward returns / IC / summary
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数計算・スケーリング
    - risk_adjustment.py — セクター上限・レジーム乗数
  - monitoring/
    - monitoring_db.py — SQLite 永続化層（テーブル作成 + CRUD）
    - system_monitor.py — CPU/メモリ/ディスク・データ鮮度・プロセス検出
    - trade_monitor.py — (注文ログ監視: 実装参照)
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — フラグファイル生成ロジック
    - monitoring_engine.py — 監視コンポーネントの統合
  - utils/
    - logging_setup.py — ロギング初期化ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ
  - portfolio/, research/, ai/ の __init__.py で便利関数をエクスポート

注意事項 / 実運用上のポイント
----------------------------
- 本リポジトリは設計・実装の参考となるサンプル基盤です。実際に実運用する場合は API キー・認証情報の管理、堅牢なエラーハンドリング、より厳密なテスト、監査ログの整備などが必要です。
- KABUSYS_ENV=live を指定する場合は特に注意して設定を確認してください（validate_config の live ガードが警告を出します）。
- OpenAI 等の外部 API を利用する箇所は API 制限・課金に注意して運用してください。
- データベースやログのバックアップ、アクセス権限、権限昇格（set_process_priority）時の権限不足に対する対処を行ってください。

ライセンス / バージョン
-----------------------
- パッケージバージョン: __version__ = "0.1.0"（src/kabusys/__init__.py）
- ライセンス情報は本リポジトリに同梱されている LICENSE ファイル（存在する場合）を参照してください。

フィードバック・拡張
-------------------
- 監視アラートの通知先（LINE 等）は設定に依存します。LINE の設定は .env の LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID を使用します。
- ポートフォリオ構成やポジションサイズのロジックは pure function で実装されているため、戦略部分の入れ替えや単体テストが容易です。
- DuckDB を使った分析パイプラインはスケジュールバッチや Jupyter 等での利用を想定しています。

以上。プロジェクト固有の詳細は各モジュールの docstring・コード内コメントを参照してください。README の補足や具体的なデプロイ手順（systemd / supervisor / Docker 等）をご希望であれば、環境情報を教えてください。