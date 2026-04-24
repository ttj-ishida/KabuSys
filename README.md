README — KabuSys（日本株自動売買システム）
======================================

概要
----
KabuSys は日本株向けの自動売買／リサーチ基盤のサンプル実装です。本プロジェクトは以下の主要機能を備えます。
- 実際の発注を行う ExecutionEngine（本番 / ペーパートレード切替対応）
- システム稼働監視・アラート・Kill Switch
- ポートフォリオ構築（銘柄選定、重み付け、ポジションサイズ計算）
- リサーチ（ファクター計算、特徴量探索、IC 計算）
- ニュースの LLM（OpenAI）によるセンチメント解析と市場レジーム判定
- ペーパートレード検証用レポート生成ツール

設計上のポイント
- ペーパートレード（KABUSYS_ENV=paper_trading）は本番データベースと完全分離（data/paper_trading.db を使用）
- 設定は .env ファイルまたは環境変数で管理。config_setup.py による対話式ウィザードと validate_config.py による事前検証あり
- DuckDB を分析用に利用、SQLite を監視／トレードログ保存用に利用
- OpenAI を利用した NLP 部分は API キーが必要。失敗時はフェイルセーフ（フォールバック）動作

主な機能一覧
---------------
- run_execution.py: ExecutionEngine 起動スクリプト（KABUSYS_ENV により本番 / ペーパートレード切替）
- run_monitoring.py: SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で間隔調整）
- monitoring/*: system / trade / risk の各種モニタ、MonitoringDB（SQLite 永続化）、KillSwitch、AlertManager（通知）
- portfolio/*: 候補選定、重み付け、リスク調整、ポジションサイジング
- research/*: ファクター計算（momentum, volatility, value 等）、特徴量探索、IC 計算
- ai/news_nlp.py: OpenAI でニュース記事を銘柄ごとにスコアリングして ai_scores へ書き込み
- ai/regime_detector.py: ETF（1321）MA とマクロニュースを使った日次市場レジーム判定
- tools/paper_verification_report.py: ペーパートレード結果の検証レポート出力
- config_setup.py: .env 対話式生成ウィザード
- validate_config.py: .env / config/*.yaml の起動前チェック

必要条件
--------
- Python 3.10+
- 主要依存ライブラリ（例）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config.yaml の検証を行う場合に必要）
- SQLite（標準ライブラリで使用）
- ネットワーク接続（kabuステーション API / OpenAI などを利用する場合）

推奨インストール例
-----------------
1. リポジトリをクローン
   - git clone <repo-url>
2. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール（例）
   - pip install duckdb psutil openai PyYAML
   （プロジェクトに requirements.txt があればそれを使用してください）
4. data/ と logs/ ディレクトリを作成（自動作成する箇所もありますが手動で作ると明示的）
   - mkdir -p data logs

環境設定（.env）
----------------
- 推奨手順: 対話式ウィザードで .env を作成
  - python -m kabusys.config_setup
- 主な環境変数（例・説明）
  - JQUANTS_REFRESH_TOKEN (必須) — J-Quants API 用
  - KABU_API_PASSWORD (必須) — kabuステーション API パスワード
  - KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
  - OPENAI_API_KEY — OpenAI を使う機能で必要
  - KABUSYS_ENV — 実行環境: development | paper_trading | live （デフォルト: development）
  - PAPER_FILL_MODE — paper_trading 時のマッチング動作: instant | partial | never | reject
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite DB（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
  - LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
  - LOG_DIR — ログ出力ディレクトリ（デフォルト: logs/）
  - KILL_FLAG_CLEAR_ON_START — (0/1) 起動時に kill.flag を自動クリアするか（本番では 0 推奨）

設定検証
--------
作成した .env や config/*.yaml の基本チェックを実行:
- python -m kabusys.validate_config
- --strict を付けると警告も失敗扱いになります

使い方（主要コマンド）
---------------------
- 環境ウィザード（.env 作成）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config [--strict]
- ExecutionEngine（システムのメイン発注エンジン）起動
  - python -m kabusys.run_execution
  - 補足: KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH に記録
  - 起動時に data/stop_requested.flag があれば起動を中止
  - 実行中に data/stop_requested.flag を作成すると安全に停止できます
- Monitoring（監視ループ）起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を変更可能（デフォルト 60）
  - 監視は本番 sqlite_path を常に使用（KABUSYS_ENV に依存せず）
- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD
  - --db オプションで DB を指定可能（環境変数 PAPER_TRADING_SQLITE_PATH が優先されます）
- AI 関連（スクリプト内 API 呼び出し）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらを呼び出すには OpenAI API キーが必要（api_key 引数または OPENAI_API_KEY 環境変数）

運用に関する注意
----------------
- ペーパートレードモードは本番データベースと分離されます。デフォルトで data/paper_trading.db を使用。
- Kill Switch: リスク超過（ドローダウン／ポジション上限）等により data/kill.flag を書き込むと ExecutionEngine に停止指示を送れます。
- stop_requested.flag（data/stop_requested.flag）を作成すると run_execution/run_monitoring は安全にシャットダウンします。
- ログは logs/<app_name>.log に日次ローテーションで出力されます。ログ出力に失敗した場合はコンソール出力のみで継続します。
- process priority の設定は psutil を使用します。権限不足や未対応 OS の場合は警告を出してスキップします。
- AI（OpenAI）を利用する箇所は外部 API 依存のため課金やレート制限に注意してください。429・一時エラー時は指数バックオフでリトライ実装がありますが、長時間失敗する場合はフェイルセーフで処理を継続します。

ディレクトリ構成（抜粋）
-----------------------
src/kabusys/
- __init__.py
- config.py                    — 環境変数 / Settings 管理
- config_setup.py              — .env 対話ウィザード
- validate_config.py           — 設定検証 CLI
- run_execution.py             — ExecutionEngine 起動スクリプト
- run_monitoring.py            — SystemMonitor 起動スクリプト
- tools/
  - paper_verification_report.py — ペーパートレード検証レポート
- utils/
  - logging_setup.py            — ログ設定ユーティリティ
  - process_priority.py         — プロセス優先度設定ユーティリティ
- monitoring/
  - monitoring_db.py            — SQLite スキーマと永続化 API
  - monitoring_engine.py        — 各 Monitor を束ねるエンジン
  - system_monitor.py           — システム稼働・データ鮮度監視
  - trade_monitor.py            — 発注／注文監視（存在）
  - risk_monitor.py             — ドローダウン・ポジション上限監視
  - kill_switch.py              — kill.flag 管理
  - alert_manager.py            — 通知管理（存在）
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- ai/
  - news_nlp.py                 — ニュース NLP（OpenAI）スコアリング
  - regime_detector.py          — 市場レジーム判定
- execution/                    — Execution 周りの実装（broker_factory, engine, order_manager 等）
- data/                         — データパイプライン / DB マイグレーション等（存在）

補足（トラブルシューティング）
-----------------------------
- .env 自動読み込み:
  - config.py はプロジェクトルート（.git または pyproject.toml を基準）を探索して .env/.env.local を自動読み込みします。
  - テストなどで自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Python バージョン: 本コードは | 型（Union シンタックス）などを使っているため Python 3.10 以上を想定しています。
- DuckDB バインドの挙動や executemany の仕様はバージョンによる差異があるため、DB 操作で問題があれば duckdb のバージョンを確認してください。
- OpenAI SDK のバージョン差異により例外クラス名やレスポンス形式が変わる場合があります。テスト時は _call_openai_api をモックすることを想定しています。

ライセンス・貢献
----------------
（プロジェクトのライセンス・貢献に関する情報をここに記載してください）

以上。セットアップや実行で不明点があれば、使用したいユースケース（本番/ペーパー、AI を使うか等）を教えてください。具体的なコマンドや .env のサンプルを用意します。