KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株の自動売買フレームワークです。シグナル生成・ポートフォリオ構築・発注実行・監視・レポーティング・研究用ファクター計算などを含むモジュール群で構成されています。設計方針として「本番動作と研究/ペーパートレードを分離」「ルックアヘッドバイアスを避ける」「外部 API 呼び出しは明示的に制御する（OpenAI 等）」を重視しています。

主な機能
--------
- 実行エンジン（ExecutionEngine）
  - 本番 / ペーパートレード切り替え（KABUSYS_ENV）
  - ブローカークライアント抽象化（MockBrokerClient を用いたペーパートレード）
  - 注文管理、リスク管理、再整合（reconciler）
- 監視（Monitoring）
  - SystemMonitor：CPU/メモリ/ディスク、プロセス生存、データ鮮度監視
  - TradeMonitor：注文滞留・約定異常等の監視（trade_logs）
  - RiskMonitor：ドローダウン・ポジション上限監視、ダッシュボード更新
  - KillSwitch：リスクトリガーで data/kill.flag を書き込み Execution を停止
  - MonitoringEngine：上記のポーリング統括、アラート通知フック
  - 永続化：SQLite（monitoring.db）経由でログを保存（monitoring_db）
- ポートフォリオ構築（portfolio モジュール）
  - 候補選定、等金額・スコア重み付け、ポジションサイズ計算、セクター上限適用、レジーム乗数
- 研究（research モジュール）
  - ファクター計算（モメンタム、ボラティリティ、バリュー）
  - 将来リターン、IC 計算、統計要約
  - DuckDB を用いた高速な時系列集計
- AI 連携（ai モジュール）
  - news_nlp: OpenAI を使ったニュース記事センチメントスコアリング（ai_scores）
  - regime_detector: ETF（1321）MA とマクロニュースを組合せた市場レジーム判定
  - OpenAI リトライ・バリデーション・安全フォールバック実装
- ツール
  - config_setup: .env を対話式に作成/更新
  - validate_config: 起動前の設定検証 CLI
  - paper_verification_report: ペーパートレード結果の検証レポート生成

必要条件
--------
- Python 3.9+
- 推奨パッケージ（抜粋）:
  - duckdb
  - psutil
  - openai
  - PyYAML（設定ファイル検証時に必要）
- SQLite（標準ライブラリで利用可）
- ネットワーク接続（本番で外部 API を使用する場合）

セットアップ手順
----------------
1. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)

2. 必要パッケージのインストール（例）
   - pip install duckdb psutil openai PyYAML

   ※ requirements.txt があればそれを利用してください。

3. プロジェクトルート直下に data/ および logs/ ディレクトリを作成（通常はコードが自動作成しますが明示的に作ると権限エラーを回避できます）
   - mkdir -p data logs

4. 環境変数の初期化
   - python -m kabusys.config_setup
     - 対話式ウィザードが .env を生成します（.env を絶対に git にコミットしないでください）
   - 設定を検証:
     - python -m kabusys.validate_config
     - --strict を付けると警告も失敗扱いになります

5. データベースの初期化
   - 実行時に必要なテーブルは自動で作成されます（monitoring_db.init_monitoring_db 等）。ただし DuckDB 用のスキーマ作成や prices データ等は別のスクリプト／ETL で準備してください。

主要な環境変数（抜粋）
---------------------
必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード

主要な任意 / デフォルト:
- KABUSYS_ENV — 実行環境: development | paper_trading | live (default: development)
- LOG_LEVEL — ログレベル（default: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（default: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視）DB パス（default: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（paper_trading 時）
- PAPER_FILL_MODE — ペーパートレード時の約定モード（instant|partial|never|reject）
- PID_FILE_PATH — ExecutionEngine 用 pid ファイルパス（default: data/execution.pid）
- KILL_FLAG_PATH — Kill Switch フラグ（default: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動でクリア（「1」で有効）
- OPENAI_API_KEY — OpenAI API キー（ai.news_nlp / regime_detector で使用）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、default: 60）

使い方（コマンド例）
------------------
- 環境設定ウィザード（.env の作成/更新）
  - python -m kabusys.config_setup

- 設定の検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine 起動
  - python -m kabusys.run_execution
  - 実行中に data/stop_requested.flag が存在すると起動しない・実行中はフラグ検知でエンジンを停止します。
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db を使って本番DBと分離します。

- Monitoring 起動（ポーリング監視）
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    - MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書きできます（デフォルト 60 秒）。
  - 監視は sqlite_path を常に本番パスで使用します（設定に依らず監視 DB を共有しない設計上の注意あり）。

- ペーパートレード検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

- AI 機能（Python API）
  - ニューススコアリング:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key="...")
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key="...")

監視と停止フラグの挙動
---------------------
- stop_requested.flag (data/stop_requested.flag)
  - run_monitoring と run_execution はこのファイルを参照してループを終了またはエンジン停止します。運用時にサービスを安全に止めたい場合に利用します。

- kill.flag (Settings.kill_flag_path、デフォルト data/kill.flag)
  - KillSwitch がリスク条件（ドローダウン超過、ポジション上限超過等）を検出すると書き込みます。ExecutionEngine はこのフラグを検出して安全に停止します。
  - KILL_FLAG_CLEAR_ON_START が 1 の場合、Execution 起動時にこのフラグを自動でクリアします（本番環境では 0 推奨）。

ログ・プロセス優先度
-------------------
- ログは kabusys.utils.logging_setup.setup_logging により標準出力（stdout）と日次ローテートファイル（logs/<app_name>.log）に出力されます。
- 起動スクリプトは最初に set_process_priority("high") を呼んでプロセス優先度を上げます（psutil を利用）。権限がない場合は警告を出してスキップします。

開発・検証フロー
----------------
- .env を作成 → python -m kabusys.validate_config で検証
- DuckDB に価格・財務データをロードして research モジュールを実行し、ファクターの妥当性を確認
- ペーパートレードで ExecutionEngine を動かし trade_logs / monitoring DB を確認
- 必要に応じて ai モジュールを API キー付きで実行してニューススコアやレジーム判定を検証

ディレクトリ構成（主要ファイル）
------------------------------
プロジェクトルートの src/kabusys 配下の主要構成:

- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py       — Monitoring ポーリング起動スクリプト
- config.py               — Settings 管理（.env 自動ロード・検証ユーティリティ）
- config_setup.py         — .env 対話式ウィザード
- validate_config.py      — 設定検証 CLI
- __init__.py

パッケージ / サブモジュール:
- ai/
  - news_nlp.py
  - regime_detector.py
- monitoring/
  - monitoring_db.py
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - monitoring_engine.py
  - alert_manager.py (参照インポートあり)
- execution/                (ExecutionEngine 本体・ブローカーファクトリ等)
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- tools/
  - paper_verification_report.py
- utils/
  - logging_setup.py
  - process_priority.py

補足・運用注意
--------------
- .env は機密情報を含むため絶対にリポジトリにコミットしないでください。
- KABUSYS_ENV を誤って live に設定すると実際の発注が行われます。起動前に validate_config で確認してください。
- OpenAI を使う機能は API コストとレイテンシの影響を考慮してください。失敗時はフェイルセーフで継続する設計ですが、運用ポリシーを検討してください。
- DuckDB / SQLite ファイルは適切なバックアップ・権限設定を行ってください。

ライセンス・バージョン
---------------------
- パッケージバージョンは kabusys.__version__ で管理（例: 0.1.0）
- ライセンス情報はリポジトリの LICENSE ファイルを参照してください（含まれていない場合はプロジェクトポリシーに従って追加してください）。

以上。セットアップや運用で不明点があれば、どの箇所を詳しく知りたいか教えてください。README の追記や CLI 使い方の詳細（例: ExecutionEngine のログ確認方法、DB スキーマの詳細など）も作成できます。