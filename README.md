KabuSys — 日本株自動売買システム（簡易 README）
概要
- KabuSys は日本株向けの自動売買・リサーチ基盤のコード群です。  
  主な機能は「注文実行エンジン」「監視（モニタリング）」「ポートフォリオ構築」「ファクター計算」「AI を用いたニュースセンチメント評価」などを含みます。
- 実行スクリプトはパッケージ内モジュールとして提供され、環境変数（.env）で挙動を制御します。
- データ永続化には SQLite（監視/ペーパートレード）と DuckDB（時系列・分析用）を使用します。

主な機能一覧
- ExecutionEngine（実行エンジン）
  - 実際のブローカークライアントまたはペーパートレード用 Mock を用いた発注処理
  - リスク管理、オーダーマネージャ、レコンシリエーション等の統合
- Monitoring（監視）
  - SystemMonitor：プロセス生存・CPU/メモリ/ディスク・データ鮮度監視
  - TradeMonitor：滞留注文・約定異常の検出
  - RiskMonitor：ドローダウン・ポジション上限の監視と kill-switch（停止フラグ）連携
  - AlertManager：LINE Messaging API を用いた一方向アラート（任意）
- Portfolio（ポートフォリオ構築）
  - 候補選定、重み計算、セクター制約、ポジションサイジング等の純粋関数（副作用なし）
- Research（リサーチ）
  - ファクター計算（モメンタム・バリュー・ボラティリティ）、将来リターン、IC 計算、統計サマリ
- AI（ニュースNLP / レジーム判定）
  - OpenAI を用いたニュースのセンチメント評価（ai_scores）
  - マクロニュースと ETF MA を組み合わせた市場レジーム判定
- Tools
  - paper_verification_report：ペーパートレード DB を集計して PASS/FAIL 判定レポートを出力
- CLI ヘルパー
  - config_setup：.env を対話式で生成/更新
  - validate_config：.env と config/*.yaml の簡易検証

セットアップ手順（概略）
1. Python 環境
   - Python 3.9+ を推奨（コードは型ヒントを多用）
2. 必要パッケージ（例）
   - duckdb, psutil, requests, openai, PyYAML（config YAML 検証に必要）
   - インストール例:
     pip install duckdb psutil requests openai pyyaml
   - （プロジェクト固有の requirements.txt がある場合はそちらを使用）
3. リポジトリルートでの初期設定
   - 対話式で .env を作る:
     python -m kabusys.config_setup
   - あるいは .env を手動で作成する（下記「環境変数」を参照）
4. 設定検証（任意）
   - python -m kabusys.validate_config
   - 警告もエラー扱いにする場合:
     python -m kabusys.validate_config --strict
5. データディレクトリ等
   - デフォルトの DB/フラグファイルは data/ に置かれます。必要に応じて .env でパスを上書きしてください。
6. 実行
   - 実行方法は下の「使い方」を参照

重要な環境変数（要・推奨・デフォルト）
- 必須（起動前に設定）
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用トークン
  - KABU_API_PASSWORD — kabuステーション API パスワード
- 任意 / 推奨（デフォルト値あり）
  - KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
    - paper_trading: MockBroker を使用し、ペーパートレード用 DB（PAPER_TRADING_SQLITE_PATH）に記録
    - live: 本番（注意: アラートや kill フラグ設定等の確認必須）
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
  - LOG_LEVEL — ログレベル（DEBUG/INFO/…、デフォルト: INFO）
  - OPENAI_API_KEY — OpenAI API キー（AI モジュール使用時必須）
  - PAPER_FILL_MODE — ペーパートレード時の約定モード:
    - instant | partial | never | reject（デフォルト: instant）
  - MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒、デフォルト: 60）
  - KILL_FLAG_CLEAR_ON_START — 本番での自動 kill_flag クリア（0/1、デフォルト: 0）
- ファイル / フラグ（デフォルト場所）
  - data/execution.pid — ExecutionEngine の PID（存在チェックに使用）
  - data/kill.flag — KillSwitch による停止要求（Execution が検出して停止）
  - data/stop_requested.flag — run_monitoring / run_execution が監視する即時停止フラグ
  - これらの場所は .env で一部上書き可能（Settings.kill_flag_path, pid_file_path など）

使い方（主要コマンド）
- .env を対話式で作成/更新
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- 監視プロセス起動（SystemMonitor のポーリングループ）
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 備考: run_monitoring はドキュメント通り、MONITOR_POLL_INTERVAL で間隔を上書きできます（デフォルト 60秒）。Monitoring は本番 sqlite_path を使用します（環境にかかわらず）。
- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - 備考: KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して data/paper_trading.db に記録します。本番環境では実ブローカークライアントが使用されます。
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - または DB 指定:
    python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
- AI 関連（プログラム的呼び出し）
  - kabusys.ai.score_news(...) — raw_news を評価し ai_scores に書き込む（OpenAI API キー必須）
  - kabusys.ai.regime_detector.score_regime(...) — market_regime を判定して書き込む

運用時の注意点 / 動作の重要ポイント
- kill.flag / stop_requested.flag:
  - KillSwitch は RiskMonitor の結果（ドローダウン、ポジション上限）に応じて data/kill.flag を書き込み、ExecutionEngine 側はこれを検出して安全に停止します。
  - run_monitoring / run_execution は data/stop_requested.flag の存在で停止します（管理者が即時停止したい場合に書く）。
- DB スキーマの自動初期化:
  - monitoring_db.init_monitoring_db() により必要な監視テーブルが作成されます。マイグレーション的にカラムを追加する処理も含む（例: latency_ms, peak_value）。
- 権限とプロセス優先度:
  - 実行スクリプトは開始時に set_process_priority("high") を呼びます。psutil の権限不足・未対応プラットフォームでは警告が出てスキップされます。
- データ鮮度:
  - SystemMonitor は DuckDB の get_last_price_date() を参照し、データ鮮度が規定日数（_FRESHNESS_DAYS）以内かチェックします。
- OpenAI 呼び出し:
  - API エラー（429・タイムアウト・5xx）は指数バックオフでリトライします。パース失敗・非回復エラーはフェイルセーフ（0.0 やスキップ）で処理します。

サンプル .env（config_setup 生成内容の抜粋）
- .env は秘密情報を含むため絶対にリポジトリにコミットしないでください。
例:
  JQUANTS_REFRESH_TOKEN=your_token_here
  KABU_API_PASSWORD=your_kabu_password_here
  KABU_API_BASE_URL=http://localhost:18080/kabusapi
  DUCKDB_PATH=data/kabusys.duckdb
  SQLITE_PATH=data/monitoring.db
  KABUSYS_ENV=development
  LOG_LEVEL=INFO
  KILL_FLAG_CLEAR_ON_START=0

ディレクトリ構成（主要ファイル・モジュール）
- src/kabusys/
  - __init__.py
  - config.py               — 環境変数/.env ロードと Settings
  - config_setup.py         — .env 対話ウィザード
  - validate_config.py      — 設定検証 CLI
  - run_execution.py        — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py           — ニュース NLP / OpenAI 統合
    - regime_detector.py    — マーケットレジーム判定
  - monitoring/
    - monitoring_db.py      — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
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
  - utils/
    - process_priority.py
  - その他: execution/（注文関連）, data/, strategy/ 等（このリポジトリ全体を参照）

開発・拡張メモ
- DuckDB は分析用（prices_daily, raw_financials, raw_news 等）で利用。AI モジュールやリサーチモジュールは DuckDB 接続を受け取り SQL と Python を組み合わせて計算します。
- portfolio / position sizing の関数群は純粋関数（副作用なし）でユニットテストを書きやすい設計です。
- OpenAI を利用する箇所は鍵・エラー制御・レスポンスバリデーションを重視しています。テストでは API 呼び出しをモックすることを想定しています。

トラブルシュート
- .env 自動ロードに失敗する場合:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できます（テスト用途）。
- DuckDB / SQLite のファイルパスが存在しない親ディレクトリの場合:
  - validate_config は親ディレクトリの存在を警告します。起動時に自動作成されることが多いですが、手動で data/ ディレクトリを作成してください。
- 実行時に権限エラーや psutil の例外が出る場合:
  - 管理者権限や適切な OS 対応を確認してください。優先度設定は失敗してもスキップされます。

最後に
- 本 README はコードベース内の主要な挙動と使い方の要点をまとめたものです。実運用前に python -m kabusys.validate_config により設定の検証を行い、特に KABUSYS_ENV=live の場合はアラート設定・kill switch 設定を十分に確認してください。