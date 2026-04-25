# KabuSys

日本株自動売買システムのライブラリ/スクリプト群の README（日本語）

このリポジトリは、自動売買のコアロジック、監視、ペーパートレード検証、AI（ニュースセンチメント／レジーム判定）などを含むモジュール群です。下記は開発者・運用担当者向けの概要、セットアップ、使い方、ディレクトリ構成の説明です。

---

目次
- プロジェクト概要
- 主な機能一覧
- 前提・依存ライブラリ
- セットアップ手順
- 使い方（主要コマンド・スクリプト）
- 環境変数一覧（主要）
- 監視・停止フラグについて
- ディレクトリ構成

---

プロジェクト概要
- KabuSys は日本株の自動売買システムのコンポーネント群です。
- 戦略・ポートフォリオ構築、ポジションサイズ計算、発注実行（ExecutionEngine）、監視（Monitoring）、AI によるニュースセンチメントおよび市場レジーム判定、研究用ファクター計算、ペーパートレード検証レポートなどを含みます。
- DuckDB を使った時系列/財務データ処理、SQLite を用いた監視ログ／発注ログの永続化が行われます。
- 実行スクリプトはモジュール化され、ログ設定・プロセス優先度設定など共通ユーティリティが用意されています。

主な機能一覧
- 実行エンジン起動: run_execution.py
  - 本番／ペーパートレード（KABUSYS_ENV=paper_trading）に応じて動作を分離
  - RiskManager、OrderManager、Reconciler、ExecutionEngine の組み立てと実行
  - ペーパートレード時は MockBrokerClient を使用し、別 DB（data/paper_trading.db）に記録
- 監視エンジン: run_monitoring.py / MonitoringEngine
  - SystemMonitor / TradeMonitor / RiskMonitor を定期実行し、アラート・Kill Switch を評価
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を制御（デフォルト 60 秒）
- 設定ウィザード: config_setup.py
  - .env ファイルの対話式作成/更新を支援
- 設定検証 CLI: validate_config.py
  - .env と config/*.yaml（存在する場合）を起動前に検証。--strict で警告を FAIL 扱いに
- ペーパートレード検証レポート: tools/paper_verification_report.py
  - paper_trading DB から稼働率、注文成功率、API レイテンシ等の指標を集計・判定
- AI モジュール:
  - ai.news_nlp: raw_news を LLM（OpenAI）で評価し ai_scores に書き込み
  - ai.regime_detector: ETF（1321）等の MA とマクロニュースを組み合わせて市場レジーム判定
- 研究モジュール:
  - research.factor_research / feature_exploration: ファクター計算、将来リターン、IC など
- ポートフォリオ構築:
  - portfolio.*: 候補選定、重み計算、リスク調整、ポジションサイズ算出
- 共通ユーティリティ:
  - utils.logging_setup: 一貫したログ出力（stdout + 日次ローテートファイル）
  - utils.process_priority: プロセス優先度 / CPUアフィニティ設定

前提・依存ライブラリ（例）
- Python 3.10+
- 必須（起動する機能に応じて）:
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
- 任意:
  - PyYAML（validate_config で config/*.yaml のパース検証を行う場合に推奨）
- インストール例:
  - pip install duckdb psutil openai pyyaml

セットアップ手順（開発・ローカル運用向け）
1. リポジトリをクローンし、Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)
2. 必要なパッケージをインストール
   - pip install duckdb psutil openai pyyaml
   - （プロジェクトに requirements.txt があればそれを使ってください）
3. 環境変数の準備
   - 対話式ウィザードで .env を作成:
     - python -m kabusys.config_setup
   - ウィザードで作成した .env に必須の値（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD 等）を設定する
4. 設定検証
   - python -m kabusys.validate_config
   - 起動前にエラー・警告を確認します。重要項目は修正してください。

使い方（主要スクリプト）
- 設定ウィザード
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード（警告を FAIL 扱い）: python -m kabusys.validate_config --strict
- 実行エンジン起動（ローカル起動例）
  - python -m kabusys.run_execution
  - 注意: 起動時に data/stop_requested.flag が存在すると起動を行いません
  - ペーパートレード環境:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - ペーパートレード DB は PAPER_TRADING_SQLITE_PATH 環境変数で上書き可（デフォルト data/paper_trading.db）
- 監視ループ起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔を環境変数で変更:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring  （30秒間隔）
- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を明示する場合:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
- AI スコアリング（プログラム的に）
  - ai.news_nlp.score_news(conn, target_date, api_key=None)
    - api_key が None の場合は OPENAI_API_KEY 環境変数を参照
  - ai.regime_detector.score_regime(conn, target_date, api_key=None)
- ログ
  - デフォルトログディレクトリ: logs/
  - ログファイル名: <app_name>.log（例: execution.log, monitoring.log）
  - 環境変数 LOG_DIR / LOG_LEVEL で上書き可能

環境変数（主要）
- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
  - KABU_API_PASSWORD — kabuステーション API パスワード
- 実行環境関連
  - KABUSYS_ENV — "development" | "paper_trading" | "live"（デフォルト: development）
- DB パス
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — SQLite（監視）ファイルパス（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- ログ
  - LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）
  - LOG_DIR — ログ保存ディレクトリ（デフォルト: logs/）
- AI
  - OPENAI_API_KEY — OpenAI API キー（ai.news_nlp / ai.regime_detector で使用）
- 監視・停止フラグ
  - PID_FILE_PATH — 実行エンジンの PID ファイルパス（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH — Kill Switch 用 flag ファイル（デフォルト: data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START — 起動時に Kill Flag を自動クリアするか（"1" で有効、デフォルト "0"）
- 監視チューニング
  - CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT — 監視しきい値
  - MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒、run_monitoring.py はデフォルト 60 秒）

停止・Kill Switch について
- 停止フラグ（run_monitoring/run_execution）
  - data/stop_requested.flag が存在すると、run_monitoring と run_execution のメインループは停止シグナルとして検出し、順次終了します。
  - 停止フラグは運用側で作成（空ファイル作成）することで外部から安全に停止させられます。
- Kill Switch（監視 → Execution 停止）
  - KillSwitch（monitoring.kill_switch） はルール（例: ドローダウン超過、ポジション上限超過）により KILL_FLAG_PATH（デフォルト data/kill.flag）を生成します。
  - ExecutionEngine 側は start 時に kill flag を検出して動作を制御する仕組みがあります。KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に自動でクリアする動作が利用可能ですが、本番では 0（クリアしない）を推奨します。
- 実行中のプロセス優先度
  - run_execution/run_monitoring は起動時にプロセス優先度を "high" に設定しようとします（utils.process_priority）。権限がない場合は警告を出してスキップします。

データベース（マイグレーション）
- monitoring_db.init_monitoring_db(conn) は監視用 SQLite に必要なテーブルを冪等に作成します。
- マイグレーション: 既存 dashboard テーブルに peak_value カラムがなければ追加、trade_logs に latency_ms カラムがなければ追加されます。

開発者向けノート / 実装上のポイント
- .env 自動読み込み: config.py はプロジェクトルート（.git または pyproject.toml）を起点に .env / .env.local を自動読み込みします。テストで無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- ログ出力: utils.logging_setup.setup_logging を全スクリプトで使用しているため、ログは一貫したフォーマットで stdout と日次ローテートファイルに出力されます。
- DuckDB を使った研究モジュールは conn（DuckDB 接続）を受け取り SQL を実行して結果を返す設計です（外部 API へアクセスしません）。
- AI モジュールは LLM 呼び出し部分を内部でラップしており、429 / タイムアウト / 5xx に対する指数バックオフ等の耐障害処理を実装しています。API キーは環境変数または引数で渡します。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数/設定管理（.env 自動読み込み）
  - config_setup.py              — .env 作成・更新ウィザード
  - validate_config.py           — 起動前検証 CLI
  - run_execution.py             — ExecutionEngine 起動スクリプト
  - run_monitoring.py            — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - ai/
    - news_nlp.py                — ニュースセンチメント（OpenAI）
    - regime_detector.py         — 市場レジーム判定（OpenAI）
  - monitoring/
    - monitoring_db.py           — 監視用 SQLite 永続化層
    - monitoring_engine.py       — 各 Monitor を束ねるエンジン
    - system_monitor.py          — CPU/メモリ/ディスク/データ鮮度監視
    - risk_monitor.py            — ドローダウン / ポジション制限監視
    - kill_switch.py             — Kill Switch 実装
    - (trade_monitor.py, alert_manager.py 等 — 実装あり)
  - execution/
    - execution_engine.py        — ExecutionEngine 本体（起動・セッション管理）
    - broker_factory.py          — ブローカークライアント生成（実ブローカ / モック）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - data/ (運用時に生成される)
    - monitoring.db (デフォルト SQLITE_PATH)
    - paper_trading.db (ペーパートレード用)
    - stop_requested.flag
    - execution.pid
  - utils/
    - logging_setup.py
    - process_priority.py

（上は主要ファイルのみ抜粋。ソース内に詳細な docstring / コメントがあります。）

トラブルシューティング
- .env を設定しても validate_config でエラーが出る場合:
  - 必須 env（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD）が正しく設定されているかを確認してください。
  - KABUSYS_ENV が正しい値（development / paper_trading / live）になっているか確認してください。
- DuckDB / SQLite のファイルパスの親ディレクトリが存在しない場合、validate_config は警告を出しますが、起動時に自動作成されることがあります。
- OpenAI 呼び出しが失敗する場合:
  - OPENAI_API_KEY の設定を確認
  - ネットワーク、レート制限、モデル名（既定 gpt-4o-mini）を確認

ライセンス・その他
- 簡潔な説明やライセンス情報は別途プロジェクトルートの LICENSE / NOTICE を参照してください（このリポジトリには含まれている想定）。

---

この README はコードの docstring を元に要点をまとめたものです。各モジュールの詳細な使い方やパラメータは該当ソースファイルの docstring コメントを参照してください。必要であれば、起動例・運用手順・監視ランブック（SOP）などの追加ドキュメントを作成できます。