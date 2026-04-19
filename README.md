# KabuSys

日本株向け自動売買システムのモジュール群。データ処理、リサーチ、ポートフォリオ構築、発注実行、監視、AI（ニュースセンチメント／レジーム判定）などを含む軽量なフレームワークです。

バージョン: 0.1.0

---

## 概要

KabuSys は以下を目的としたコンポーネント群を提供します。

- DuckDB / SQLite を用いた時系列データ処理・分析
- ファクター（モメンタム／バリュー／ボラティリティ等）の計算
- ポートフォリオ構築（候補選定・重み計算・ポジションサイズ決定）
- 発注実行エンジン（実口座／ペーパートレード分離）
- 監視（システム状態・発注ログ・リスク）と Kill Switch
- OpenAI を用いたニュースの NLP スコアリング・市場レジーム判定
- 各種ユーティリティ（ログ設定、プロセス優先度設定、設定ウィザード、設定検証）

設計上の特徴:
- 設定は環境変数／.env で管理（.env 作成用の対話ウィザードあり）
- 本番 DB とペーパートレード DB を分離（KABUSYS_ENV により動作切替）
- 監視は独立したプロセスで動作し、Kill Switch により ExecutionEngine を停止可能
- DuckDB を分析向けに利用、SQLite を監視・発注ログの永続化に利用

---

## 主な機能一覧

- 設定管理
  - .env 自動読み込み（プロジェクトルートに基づく）
  - 対話式設定ウィザード（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）

- 発注系
  - ExecutionEngine（run_execution 起動スクリプト）
  - BrokerClientFactory（本番 / Mock の切り替え）
  - OrderRepository / OrderManager / Reconciler / RiskManager

- 監視系
  - SystemMonitor / TradeMonitor / RiskMonitor
  - MonitoringEngine（ポーリングループ、アラート送信フック）
  - KillSwitch（data/kill.flag による停止シグナル）
  - monitoring DB（SQLite）初期化ユーティリティ

- ポートフォリオ構築
  - 候補選定（select_candidates）
  - 重み計算（等金額 / スコア加重）
  - セクター上限、レジーム乗数適用
  - 発注株数決定（単元株丸め、リスクベース配分、aggregate cap）

- リサーチ
  - ファクター計算（モメンタム / バリュー / ボラティリティ）
  - 将来リターン計算 / IC（Information Coefficient） / 統計サマリー

- AI（OpenAI）
  - ニュース NLP による銘柄別センチメント（kabusys.ai.news_nlp）
  - マクロニュース + ETF MA を用いた市場レジーム判定（kabusys.ai.regime_detector）
  - リトライ、JSON 検証、結果クリッピング等のフェイルセーフ実装

- ツール
  - Paper Trading 検証レポート生成（kabusys.tools.paper_verification_report）

- ユーティリティ
  - 統一ログ設定（logs/<app>.log、日次ローテーション）
  - プロセス優先度 / CPU affinity 設定

---

## セットアップ手順

前提:
- Python 3.9+（ソース上で型注釈等が使われています。実際の要件はプロジェクトで調整してください）
- 必要パッケージ（例）: duckdb, psutil, openai, PyYAML（任意）

例: 仮想環境を作成して依存関係をインストールする手順
1. 仮想環境作成・有効化
   - python -m venv .venv
   - Unix/macOS: source .venv/bin/activate
   - Windows: .venv\Scripts\activate

2. 必要パッケージをインストール（requirements.txt が無い場合は主要パッケージを手動インストール）
   - pip install duckdb psutil openai
   - （YAML 検証を使う場合）pip install pyyaml

3. .env の準備
   - 対話ウィザードを使う:
     - python -m kabusys.config_setup
   - もしくは .env を手動で作成（.env.example を参照して作成）

4. 設定検証（任意）
   - python -m kabusys.validate_config
   - 厳格モード（警告を失敗扱い）: python -m kabusys.validate_config --strict

注:
- .env は絶対に Git にコミットしないでください。
- デフォルトでデータ / ログはプロジェクト内の `data/` と `logs/` に保存されます（環境変数で変更可）。

---

## 環境変数（主要）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主要なオプション（デフォルト値を含む）:
- KABUSYS_ENV : development | paper_trading | live （デフォルト: development）
- DUCKDB_PATH : data/kabusys.duckdb
- SQLITE_PATH : data/monitoring.db
- PAPER_TRADING_SQLITE_PATH : data/paper_trading.db
- LOG_LEVEL : INFO（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR : logs/
- OPENAI_API_KEY : OpenAI API キー（AI 機能を使用する際必須）
- MONITOR_POLL_INTERVAL : 監視ポーリング間隔（秒、run_monitoring で使用。デフォルト 60）
- PAPER_FILL_MODE : instant | partial | never | reject （ペーパートレード時の約定モード。デフォルト "instant"）
- KILL_FLAG_CLEAR_ON_START : 0|1 （Execution 起動時に kill.flag を自動クリアするか、デフォルト 0）

注意:
- Monitoring は KABUSYS_ENV に関わらず本番 sqlite_path を使用します（監視ログは共通で保持）。
- run_execution は KABUSYS_ENV=paper_trading のとき paper_sqlite_path を使い、本番 DB と完全分離します。

---

## 使い方（代表的コマンド）

対話式 .env 作成
- python -m kabusys.config_setup

設定検証
- python -m kabusys.validate_config
- strict モード（警告を FAIL とする）: python -m kabusys.validate_config --strict

監視プロセス起動（SystemMonitor のポーリングループ）
- python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可能（例: export MONITOR_POLL_INTERVAL=30）
  - 停止: プロセスを SIGINT（Ctrl+C） するか、プロジェクト内の data/stop_requested.flag を作成するとループが終了します。

実行エンジン（ExecutionEngine）起動
- python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録します。
  - Execution 側の停止は data/stop_requested.flag を作成するか、監視側の KillSwitch で data/kill.flag を作成する方法があります。
  - 起動時に data/execution.pid（デフォルト）に PID が書き込まれます。

Paper Trading 検証レポート生成
- python -m kabusys.tools.paper_verification_report
- 期間指定:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- DB 指定:
  - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

AI スコアリング（プログラム呼び出し例）
- news_nlp.score_news(conn, target_date, api_key=None)
  - DuckDB 接続（kabusys.ai.news_nlp）を渡し、API key を引数または OPENAI_API_KEY 環境変数で指定
- regime_detector.score_regime(conn, target_date, api_key=None)

ログ設定（全起動スクリプトで共通）
- logs/<app_name>.log に日次ローテーションで出力（デフォルト 30 日保持）
- コンソール出力は stdout に出ます

監視・停止フロー（概略）
- MonitoringEngine が SystemMonitor / TradeMonitor / RiskMonitor を定期実行
- KillSwitch が条件を満たすと data/kill.flag を書き込み（ExecutionEngine はこれを検知して停止）
- Stop フラグ: data/stop_requested.flag を置くと run_* スクリプトは安全に終了する

---

## ディレクトリ構成（主要ファイル）

プロジェクトのルートはおおよそ以下のような構成です（src 配下を抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                  — 環境変数・.env 自動読み込み
  - config_setup.py            — .env 対話ウィザード
  - validate_config.py         — 設定検証 CLI
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py
  - data/  (実行時に生成されることが想定)
  - logs/  (ログ出力)
  - ai/
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py (アラート送信処理等)
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - broker_factory.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - utils/
    - logging_setup.py
    - process_priority.py

（実際のリポジトリでは上記に加えて scripts、config/*.yaml、data 初期ファイル等が存在する可能性があります。）

---

## 注意事項 / 運用上のヒント

- .env をプロジェクトに含めないこと（セキュリティ上の理由）。
- 本番運用時は KABUSYS_ENV=live を設定する前に validate_config で全設定を確認してください。
- OpenAI API を用いる機能は API キーが必須です。API 呼び出しはリトライや JSON バリデーションを行いますが、コストや呼び出し制限に注意してください。
- ペーパートレードでは PAPER_FILL_MODE を設定して約定挙動を調整できます（instant/partial/never/reject）。
- 監視プロセスは MONITOR_POLL_INTERVAL でポーリング間隔を制御します（run_monitoring 起動時に環境変数で上書き可能）。
- kill.flag（デフォルト: data/kill.flag）は安全停止のための重要なスイッチです。本番で自動クリア（KILL_FLAG_CLEAR_ON_START=1）は危険となる場合があるため注意してください。

---

## 参考: よく使うコマンド一覧

- .env を対話的に作る:
  - python -m kabusys.config_setup
- 設定チェック:
  - python -m kabusys.validate_config
- 監視起動:
  - MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
- Execution 起動:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

README にはここに書かれていない細かな実装・API（関数引数の詳細、DB スキーマの変更履歴など）が含まれます。必要であれば、特定モジュール（例: portfolio.position_sizing、ai.news_nlp、monitoring.monitoring_db）の詳細ドキュメントを別途作成します。どのモジュールのドキュメントが必要か教えてください。