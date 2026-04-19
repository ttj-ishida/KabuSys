# KabuSys — 日本株自動売買システム

このリポジトリは日本株向けの自動売買システムのコードベースです。戦略・ポートフォリオ構築・発注（ExecutionEngine）・監視（Monitoring）・リサーチ（DuckDB ベースのファクター計算）・AI 支援（ニュース NLP / レジーム判定）などの主要コンポーネントを含んでいます。

## 概要（Project overview）
- 設計方針: 本番とペーパートレードを明確に分離し、DB やオーダー処理が混ざらないようにしている。DuckDB を分析用データベース、SQLite を監視・注文ログ用に使用。
- 環境設定は `.env` から読み込み（自動読み込み機能あり）。対話式ウィザードで `.env` を生成できる。
- 監視は別プロセスでポーリング実行し、条件に応じて ExecutionEngine を停止（kill switch）する仕組みを持つ。
- OpenAI（gpt-4o-mini）を使ったニュースセンチメントやマクロセンチメントを利用する機能を備える（API キー必須）。

## 主な機能一覧（Features）
- ExecutionEngine（発注エンジン）
  - 本番 / ペーパートレードを環境変数で切替可能（KABUSYS_ENV）
  - BrokerClientFactory により実際のブローカ or MockBroker を使い分け
  - リスクマネージャ、OrderManager、Reconciler 等を含む実行フロー
- Monitoring（監視）
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - system_status / trade_logs / risk_logs / dashboard 等の永続化
  - KillSwitch によるフラグファイル書き込みで ExecutionEngine を停止
  - 停止フラグ: data/stop_requested.flag（スクリプト終了）、data/kill.flag（エンジン停止）
- Portfolio モジュール
  - 候補選定、等金額 / スコア加重、リスク調整（セクター上限、レジーム乗数）、ポジションサイズ計算
- Research（DuckDB ベース）
  - ファクター計算（モメンタム・ボラティリティ・バリュー等）
  - 将来リターン、IC（スピアマンランク相関）、統計サマリー
- AI（OpenAI）
  - news_nlp: ニュース記事を LLM でスコアリングして ai_scores に保存
  - regime_detector: ETF (1321) の MA200 とマクロニュースの LLM 結果を合成して市場レジーム判定
- ツール
  - 環境設定ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading 検証レポート生成スクリプト（tools.paper_verification_report）
- ユーティリティ
  - ロギング統一設定（TimedRotatingFileHandler）
  - プロセス優先度 / CPU affinity 設定ユーティリティ

## 必要条件（Requirements）
- Python 3.10+
- 推奨パッケージ（例）
  - duckdb
  - psutil
  - openai
  - （任意）PyYAML（config 検証時に YAML ファイルのパースを行う）
- その他、ブローカ固有の依存がある場合は個別に追加

（requirements.txt がある場合はそれを使用してください。なければ上のパッケージをインストールしてください）

## セットアップ手順（Setup）
1. リポジトリをクローンして作業ディレクトリへ移動
   - git clone <repo-url>
   - cd <repo-root>

2. 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  # Unix
   - .venv\Scripts\activate     # Windows

3. 必要パッケージをインストール
   - pip install duckdb psutil openai
   - （必要なら）pip install pyyaml

4. データ / ログ用ディレクトリを作成
   - mkdir -p data logs

5. `.env` の作成（推奨: 対話式ウィザードを使用）
   - python -m kabusys.config_setup
     - ウィザードに従い J-Quants トークン / kabu API パスワード 等を入力してください。
   - 手動で作成する場合は `.env.example` を参照して `.env` を作成してください（このプロジェクトは .env を Git にコミットしてはいけません）。

6. 設定の検証（任意）
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱いになります。

## 主要な環境変数（重要なもの）
- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用
  - KABU_API_PASSWORD — kabuステーション API パスワード
- 実行環境
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
    - paper_trading の場合、MockBroker を使用し paper_trading.db を利用
- データベース / ログ
  - DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
  - LOG_LEVEL: ログレベル（DEBUG/INFO/...）
  - LOG_DIR: ログ保存ディレクトリ（デフォルト logs/）
- AI
  - OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector 等で使用）
- Monitoring
  - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
  - PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START 等（Settings 参照）
- Paper trading 動作
  - PAPER_FILL_MODE: instant | partial | never | reject（mock ブローカーのフィル挙動）

## 使い方（Usage）

- 環境設定ウィザード
  - python -m kabusys.config_setup
  - 対話形式で `.env` を生成します。

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告があると exit(1) になります。

- ExecutionEngine を起動（発注エンジン）
  - python -m kabusys.run_execution
  - 注意:
    - KABUSYS_ENV=paper_trading の場合は MockBroker を使い、PAPER_TRADING_SQLITE_PATH に記録されます。
    - 起動時に data/stop_requested.flag が存在する場合は起動を行わず終了します。
    - 実行中は data/execution.pid に PID を書き込む（設定により）。

- Monitoring を起動（監視プロセス）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（秒、デフォルト 60）
  - 監視は常に本番用 sqlite_path（Settings.sqlite_path）を使用して監視ログを保持します。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH （PAPER_TRADING_SQLITE_PATH 環境変数を上書き）
  - レポートは稼働率 / 注文成功率 / レイテンシ等を計算して PASS/FAIL 判定を出力します。

- AI / レジーム判定
  - kabusys.ai.score_news / score_regime 等の関数は DuckDB 接続と target_date / API key を受け取り、ai_scores / market_regime テーブルへ書き込みます。
  - 実行例（スクリプト化されていれば同様にモジュールから呼ぶ）:
    - 呼び出し: kabusys.ai.news_nlp.score_news(conn, target_date, api_key=...)
    - 必ず OPENAI_API_KEY を設定してください。

- kill.flag / stop 制御
  - KillSwitch は data/kill.flag を書き込むことで ExecutionEngine に停止を要求します（ExecutionEngine は起動時 / ループ中にこのフラグを確認して停止します）。
  - run_monitoring/run_execution はそれぞれ data/stop_requested.flag を使って外部からスクリプトを終了させるための簡易フラグを参照します。

## 運用メモ
- ログ:
  - デフォルトで logs/<app_name>.log に日次ローテーションで出力されます（30日保持）。
  - setup_logging() によりコンソール（stdout）とファイルに統一して出力されます。
- DB マイグレーション:
  - monitoring_db.init_monitoring_db は冪等でテーブル作成し、既存 DB にカラムがなければ ALTER TABLE で追加します。
- 保護設定:
  - 本番（KABUSYS_ENV=live）の場合、KILL_FLAG_CLEAR_ON_START を 1 にすることは危険（ウィザード内でも注意喚起あり）。

## ディレクトリ構成（抜粋）
以下は主要なパッケージ・モジュールの一覧と簡単な説明です（src/kabusys 配下）。

- kabusys/
  - __init__.py — パッケージ定義・バージョン
  - config.py — Settings クラス（環境変数の読み込み・検証）
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成
  - utils/
    - logging_setup.py — ログ設定ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ
  - execution/  (発注関連: BrokerFactory, ExecutionEngine, OrderManager, Reconciler 等)
  - monitoring/
    - monitoring_db.py — monitoring 用 SQLite 永続化レイヤ
    - system_monitor.py — システム状態監視
    - trade_monitor.py — 注文ログ監視（省略ファイルあり）
    - risk_monitor.py — ドローダウン/ポジション監視
    - monitoring_engine.py — 複数 Monitor の統合
    - kill_switch.py — フラグ書き込みによる停止制御
    - alert_manager.py — アラート送信管理（LINE 等）（実装あり）
  - portfolio/
    - portfolio_builder.py — 候補選定 / 重み計算
    - position_sizing.py — 発注株数計算・制限
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — ファクター計算（momentum/volatility/value）
    - feature_exploration.py — 将来リターン / IC / 統計サマリ
  - ai/
    - news_nlp.py — ニュース NLP（OpenAI）で銘柄ごとのスコアを生成
    - regime_detector.py — マクロ + MA200 でレジーム判定
  - data/  （実行時に生成されるデータファイルや flag/pid を想定）
    - monitoring.db (SQLITE_PATH)
    - paper_trading.db (PAPER_TRADING_SQLITE_PATH)
    - kabusys.duckdb (DUCKDB_PATH)
    - kill.flag / stop_requested.flag / execution.pid

（実際のファイル構成はリポジトリルートの src/kabusys を参照してください）

## 開発者向け補足
- 自動環境変数読み込み:
  - config.py はプロジェクトルート（.git または pyproject.toml を探索）を基に `.env`/.env.local を自動で読み込みます。
  - テストで自動ロードを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- テスト・モック:
  - OpenAI 呼び出し部分はテスト容易性のため内部呼び出しを patch して差し替えられるようになっています（例: unittest.mock.patch）。
- パフォーマンス:
  - research モジュールは DuckDB による SQL 集約と Python 処理の組合せを用いて高速に大量データを処理する設計です。

---

問題や実行時に不明点があれば、どのコンポーネント（例: run_execution / run_monitoring / ai.news_nlp / research.calc_momentum 等）について知りたいか教えてください。具体的な使い方や設定例を追加で用意します。