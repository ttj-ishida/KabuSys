KabuSys — 日本株自動売買システム
==============================

概要
----
KabuSys は日本株向けの自動売買/リサーチ基盤の簡易実装です。  
主な機能は発注エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築ロジック、リサーチ用ファクター計算、LLM を用いたニュースセンチメント評価・レジーム判定、および各種ユーティリティ／ツール群です。

特徴
----
- ExecutionEngine（実取引 / ペーパートレード両対応）
  - KABUSYS_ENV=paper_trading 時は MockBrokerClient を使い、paper_trading 用 DB に記録
  - リスク管理（Rate limit / position limits / drawdown など）
- Monitoring
  - システムリソース・データ鮮度・注文ログのポーリングと永続化（SQLite）
  - Kill Switch（条件を満たすと data/kill.flag を書き込み ExecutionEngine を停止）
  - アラート送信フック（LINE 等）
- ポートフォリオ構築（候補抽出、重み付け、ポジションサイズ計算、セクター制限）
- リサーチ／ファクター計算（DuckDB を用いた momentum/value/volatility 等）
- AI モジュール
  - ニュース NLP（OpenAI を用いた銘柄ごとのセンチメントスコア生成）
  - レジーム判定（ETF とマクロニュースを合成して bull/neutral/bear を判定）
- ユーティリティ
  - ログ設定共通化（コンソール + 日次ローテーティングファイル）
  - プロセス優先度 / CPU affinity 設定
  - .env 対話式作成ウィザード、設定検証 CLI
- ツール
  - Paper Trading 検証レポート生成スクリプト

セットアップ手順
----------------
1. Python 環境を用意（推奨: venv）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows は .venv\Scripts\activate）

2. 依存パッケージをインストール
   - 必要パッケージ（例）
     - duckdb
     - psutil
     - openai
     - PyYAML（config 検証で任意）
   - 例:
     - pip install duckdb psutil openai PyYAML

   （プロジェクトに requirements.txt がある場合は pip install -r requirements.txt を使用）

3. .env を作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - または手動でプロジェクトルートに .env を作成
   - 必須環境変数（主なもの）
     - JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン（必須）
     - KABU_API_PASSWORD — kabuステーション API パスワード（必須）
     - KABUSYS_ENV — 実行環境: development / paper_trading / live
     - OPENAI_API_KEY — LLM を使う場合
   - デフォルト値や追加設定は config_setup のウィザードや .env.example を参照

4. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - 厳格モード（警告を FAIL 扱い）:
     - python -m kabusys.validate_config --strict

5. データディレクトリの準備
   - デフォルトで使用されるパス:
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper trading SQLite: data/paper_trading.db
     - ログディレクトリ: logs/
   - 起動時に自動作成されることが多いですが、必要に応じて手動で作成してください。

基本的な使い方
--------------

起動スクリプト
- ExecutionEngine（発注エンジン）起動
  - python -m kabusys.run_execution
  - 実行環境切替:
    - KABUSYS_ENV=paper_trading を設定すると MockBrokerClient を使用し、paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH または data/paper_trading.db）に記録されます。

  - 起動/停止制御:
    - 起動時に data/stop_requested.flag が存在する場合は起動しません
    - 実行中に data/stop_requested.flag が作成された場合はエンジンが安全に停止します
    - Kill Switch は data/kill.flag を書き込み、外部から停止をトリガーします
    - PID ファイルは Settings.pid_file_path（デフォルト data/execution.pid）に書き込まれます

- Monitoring（監視ループ）起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き（デフォルト 60 秒）
  - 監視は常に本番 sqlite_path を使用（環境に関わらず）

CLI / ツール
- .env 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い（exit code 1）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH（PAPER_TRADING_SQLITE_PATH 環境変数でも可）

AI モジュール（Python API）
- ニューススコアリング（プログラムから呼ぶ）
  - from kabusys.ai.news_nlp import score_news
  - score_news(duckdb_conn, target_date, api_key="...")

- レジーム判定（プログラムから呼ぶ）
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(duckdb_conn, target_date, api_key="...")

ログと監視
- ログ出力は共通の setup_logging により行われます
  - コンソール（stdout）出力と日次ローテーションファイル（logs/<app_name>.log）を使用
  - デフォルト保持期間は 30 日

停止・Kill Switch
- ExecutionEngine の停止は次のいずれかで行います:
  - data/stop_requested.flag を作成 → run_execution の監視ループが検知して停止
  - Kill Switch 条件成立（監視モジュールが data/kill.flag を書き込む） → エンジンは停止条件を検知して停止
- KILL_FLAG_CLEAR_ON_START 環境変数 (0/1)：
  - 本番では 0 推奨（起動時に自動で kill.flag を消さない）

よく使う環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN — J-Quants API
- KABU_API_PASSWORD — kabuステーション API
- KABUSYS_ENV — execution 環境（development | paper_trading | live）
- OPENAI_API_KEY — OpenAI API キー（AI機能使用時）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL — 監視のポーリング間隔（秒、run_monitoring 用）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1）

ディレクトリ構成（主要ファイル）
--------------------------------
以下は src/kabusys 配下の主要モジュール例です。

- kabusys/
  - __init__.py
  - config.py                 — 環境変数 / 設定読み込みロジック
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — Monitoring 起動スクリプト
  - monitoring/
    - monitoring_db.py        — SQLite 永続化レイヤ（system_status, trade_logs, ...）
    - system_monitor.py       — システム状態・データ鮮度監視
    - trade_monitor.py        — （注文滞留・約定異常などの監視）※実装詳細ファイルあり
    - risk_monitor.py         — ドローダウン・ポジション上限監視
    - kill_switch.py          — Kill Switch 制御
    - monitoring_engine.py    — 各 Monitor を束ねるエンジン
    - alert_manager.py        — 通知送信（LINE など）※要設定
  - execution/
    - execution_engine.py     — 発注エンジン本体
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - broker_factory.py       — ブローカークライアントの生成（本番/Mock 切替）
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py      — momentum/value/volatility 等
    - feature_exploration.py  — IC / forward returns / 統計サマリー
  - ai/
    - news_nlp.py             — ニュース NLP（OpenAI）
    - regime_detector.py      — レジーム判定（OpenAI + ETF MA）
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py        — 共通ログ設定
    - process_priority.py     — プロセス優先度 / CPU affinity ユーティリティ

注意事項 / 運用上のヒント
------------------------
- 本プロジェクトは実際の発注処理を行う設計になっています。KABUSYS_ENV を適切に設定し、実運用前に設定検証・テストを十分に行ってください（validate_config を活用）。
- .env は機密情報を含むため絶対にリポジトリへコミットしないでください。
- OpenAI 等外部 API を使用する機能は API キーとコスト（API 呼び出し回数）に注意してください。
- 監視モジュールは SQLite の監視 DB を使用します（init_monitoring_db が起動時にテーブルを作成）。既存 DB のマイグレーション処理も一部含まれます。
- プロセス優先度や CPU affinity の設定は os/privilege に依存します。実行環境での権限に注意してください。

付録: 主要コマンドまとめ
-----------------------
- .env ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config [--strict]
- Execution 起動:
  - python -m kabusys.run_execution
- Monitoring 起動:
  - python -m kabusys.run_monitoring
- Paper レポート:
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

以上がこのコードベースの README 概要です。必要であれば、インストール用 requirements.txt の推奨一覧や各種 CLI の実行例（環境変数を付けたワンライナー）を追記します。どの情報を優先して追記しますか？