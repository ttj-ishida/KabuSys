# KabuSys

日本株向けの自動売買 / 研究基盤ライブラリです。  
本リポジトリは発注エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、ファクター計算、AI（ニュースセンチメント／レジーム判定）などのコンポーネントを含みます。

バージョン: 0.1.0

---

## 概要

- 複数コンポーネントで構成された日本株自動売買システムのコアモジュール群。
- 発注処理は実際のブローカー接続／ペーパートレードの切替が可能（KABUSYS_ENV により制御）。
- 監視・アラート機構および Kill Switch により、ドローダウンやポジション上限超過で安全停止できる。
- DuckDB を用いた研究（ファクター計算、特徴量解析）機能、OpenAI を使ったニュースセンチメント評価機能を備える。
- シンプルな .env ウィザードと設定検証 CLI を提供。

---

## 主な機能一覧

- Execution
  - ExecutionEngine 起動スクリプト（kabusys.run_execution）
  - paper_trading 環境での MockBroker を使った分離 DB（data/paper_trading.db）
  - RiskManager / OrderManager / Reconciler 等による発注管理
- Monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - Monitoring 用 SQLite（監視ログ）初期化・永続化（monitoring_db）
  - Kill Switch（data/kill.flag）で ExecutionEngine を停止
- Portfolio construction
  - 候補選定、等配分・スコア配分、ポジションサイズ計算、セクター制限、レジーム乗数
- Research
  - DuckDB 上でのファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC 計算、統計サマリ
- AI（オプション）
  - ニュース NLP（OpenAI）により銘柄ごとの sentiment を ai_scores に書き込む
  - レジーム判定（ETF ma200 とマクロニュースの LLM 評価を合成）
- ツール
  - Paper Trading の検証レポート生成スクリプト（kabusys.tools.paper_verification_report）
- ユーティリティ
  - ロギング初期化（logs/、日次ローテーション）
  - プロセス優先度・CPU affinity 設定ユーティリティ
  - .env 対話式ウィザード、設定検証 CLI

---

## セットアップ手順

1. Python バージョン
   - Python 3.9+ を推奨（f string/型注釈などを利用）。実行環境に合わせて仮想環境を作成してください。

2. 仮想環境作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  # Windows: .venv\Scripts\activate

3. 必要パッケージをインストール
   - 最低限必要なパッケージ:
     - duckdb
     - psutil
     - openai (AI 機能を使う場合)
     - PyYAML （config 検証で YAML 検査を行いたい場合）
   - 例:
     - pip install duckdb psutil openai PyYAML

4. .env の用意
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - もしくはリポジトリルートに `.env` を作成して必要な環境変数を設定してください（下に主要変数の例あり）。

5. 設定検証
   - python -m kabusys.validate_config
   - 警告も FAIL 扱いにする場合: python -m kabusys.validate_config --strict

6. データディレクトリ
   - デフォルトの DB / PID / flag 等は `data/` 配下に作成されます。必要に応じて `DUCKDB_PATH` / `SQLITE_PATH` を .env で設定してください。

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABUSYS_ENV: 実行環境（development / paper_trading / live） デフォルト: development
  - paper_trading の場合、発注は MockBroker に差し替わり DB は data/paper_trading.db を使用
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（例: INFO）
- LOG_DIR: ログ出力先ディレクトリ（デフォルト: logs/）
- OPENAI_API_KEY: OpenAI を使う場合に必要
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒）：デフォルト 60
- PID_FILE_PATH / KILL_FLAG_PATH: 実稼働時に使用するファイルパス（.env で上書き可能）
- PAPER_FILL_MODE: paper_trading 時のフィルモード（instant | partial | never | reject）

簡単な .env 例（実際には機密情報はマスクしてください）:
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-...

---

## 使い方（起動 / 実行）

- 設定ウィザード（.env の作成／更新）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告もエラー扱い（exit 1）

- ExecutionEngine（発注エンジン）の起動
  - python -m kabusys.run_execution
  - 特徴:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、Paper 用 DB に記録します（本番 DB と完全分離）。
    - 起動時に data/stop_requested.flag が存在すると起動せず終了します。
    - 実行中に data/stop_requested.flag が現れるとエンジンに停止シグナルを送り安全終了します。
    - 実行中の PID は data/execution.pid に書き出されます（設定で変更可）。

- Monitoring（監視ループ）の起動
  - python -m kabusys.run_monitoring
  - 特徴:
    - 環境にかかわらず監視は本番 sqlite_path を使用します（監視専用 DB）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（秒、デフォルト 60）。
    - stop_requested.flag を検知するとループを終了します。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD, --to YYYY-MM-DD, --db PATH
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

- AI 機能（ニュースセンチメント / レジーム判定）
  - kabusys.ai.score_news（プログラム呼び出し）
    - 引数に DuckDB 接続と target_date を与える API
    - 環境変数 OPENAI_API_KEY または引数で API キーを指定
  - kabusys.ai.regime_detector.score_regime も同様に使用

- ログ
  - デフォルト出力先: logs/<app_name>.log（日次ローテーション、30日保持）
  - 標準出力にも出力されます（StreamHandler は stdout を使用）

---

## 停止 / Kill Switch

- 監視側からの停止シグナル:
  - KillSwitch は条件を満たすと data/kill.flag に理由を書き込みます。ExecutionEngine は起動中にこのファイルの有無を参照して停止します。
  - Execution 停止リクエスト（外部）: data/stop_requested.flag を作成すると run_execution/run_monitoring のループが検知して終了します。

- kill.flag の自動クリア
  - .env の KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動でクリアします（本番では 0 を推奨）。

---

## ロギング設定

- 共通ユーティリティ: kabusys.utils.logging_setup.setup_logging(app_name="execution" 等)
- LOG_DIR / LOG_LEVEL は環境変数で制御可能。デフォルト LOG_DIR=logs、LOG_LEVEL=INFO

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数読み込み・Settings クラス（.env 自動ロード含む）
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - utils/
    - logging_setup.py — ログ設定ユーティリティ
    - process_priority.py — 優先度 / CPU affinity 設定
  - execution/  (発注関連コンポーネント)
    - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py, ...
  - monitoring/
    - monitoring_db.py — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py — システム状態・データ鮮度チェック
    - trade_monitor.py — 発注ログ監視（滞留注文等）
    - risk_monitor.py — ドローダウン / ポジション上限監視
    - kill_switch.py — kill.flag の書き込みクラス
    - monitoring_engine.py — 各モニタの束ね
    - alert_manager.py — （アラート送信管理、LINE等)
  - portfolio/
    - portfolio_builder.py, position_sizing.py, risk_adjustment.py — ポートフォリオ構築ロジック
  - research/
    - factor_research.py, feature_exploration.py — ファクター / 研究ユーティリティ
  - ai/
    - news_nlp.py — ニュース NLU（OpenAI 呼び出し、バッチ処理、検証・書き込み）
    - regime_detector.py — レジーム判定
  - data/（実行時に生成されることが多い）
    - monitoring.db（デフォルト） / paper_trading.db（ペーパートレード）
    - execution.pid, kill.flag, stop_requested.flag

※ 実際のファイルツリーはリポジトリのルート構成に依存します。上は主要モジュールの一覧です。

---

## 開発者向けメモ / 注意点

- Settings（config.py）はリポジトリルートを自動検出して .env / .env.local を読み込みます。テスト時に自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Monitoring は設定にかかわらず監視用 sqlite_path を参照します（本番の監視は常に同じ DB を使う設計）。
- Paper Trading は本番 DB と分離されるよう設計されています（PAPER_TRADING_SQLITE_PATH）。
- OpenAI API 呼び出しはリトライ・バリデーション実装あり。API キーが未設定の場合は明示的なエラーを発生させます。
- DuckDB への executemany 空引数は一部バージョンで制約があるため、空チェックを行っています。

---

必要であれば README に含めるサンプル .env、運用フロー（起動順序: まず execution → monitoring、もしくは監視単独での稼働）やトラブルシュート（ログ参照箇所、kill.flag の扱い等）を追加で作成します。どの情報をさらに詳しくしたいか教えてください。