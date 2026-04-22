# KabuSys

日本株自動売買システム（KabuSys）のリポジトリ用 README。  
この README はコードベース（src/kabusys 以下）を参照して作成されています。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買システムの基本コンポーネント群を提供します。主な機能は以下の通りです。

- 発注エンジン（ExecutionEngine）と注文管理
- 監視（Monitoring）: システム状態、注文ログ、リスクモニタリング、Kill Switch
- ポートフォリオ構築: 候補選定、重み付け、ポジションサイズ算出、セクター制限、レジーム調整
- リサーチ/ファクター計算: モメンタム、バリュー、ボラティリティ、将来リターン、IC計算など
- AI連携: ニュースのNLPによるセンチメントスコアリング、マクロセンチメントによる市場レジーム判定（OpenAI利用）
- 開発支援ツール: .env ウィザード（config_setup）、設定検証（validate_config）、Paper Trading 検証レポート生成ツール など
- 共通ユーティリティ: ログ設定、プロセス優先度設定

設計方針としては「本番 DB と Paper Trading を分離」「ルックアヘッドバイアスを避ける」「フェイルセーフ（API失敗時に継続）」等が取られています。

---

## 主な機能一覧

- run_execution.py
  - ExecutionEngine を起動。KABUSYS_ENV により paper_trading（MockBroker）/ live を切り替え。
  - Paper Trading 時は専用 SQLite（デフォルト: data/paper_trading.db）を使用。
- run_monitoring.py
  - SystemMonitor のポーリングループを起動。MONITOR_POLL_INTERVAL 環境変数で間隔を変更可能（デフォルト 60 秒）。
- config_setup.py
  - 対話式ウィザードで .env を作成・更新。
- validate_config.py
  - 環境変数・config/*.yaml の事前検証。--strict オプションあり。
- monitoring
  - MonitoringDB（SQLite）テーブル初期化 / 永続化 API
  - SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine / KillSwitch / AlertManager（注: AlertManagerの詳細はコード参照）
- portfolio
  - 候補選定（select_candidates）
  - 重み付け（calc_equal_weights / calc_score_weights）
  - ポジションサイズ計算（calc_position_sizes）
  - セクター制限（apply_sector_cap）
  - レジーム乗数（calc_regime_multiplier）
- research
  - ファクター計算（calc_momentum / calc_value / calc_volatility）
  - 特徴量探索（calc_forward_returns / calc_ic / factor_summary / rank）
- ai
  - news_nlp: raw_news を LLM（OpenAI）で評価して ai_scores テーブルへ書き込み
  - regime_detector: ma200 とマクロニュースの LLM 評価を合成して market_regime に書き込み
- tools
  - paper_verification_report: Paper Trading 用ログを解析して PASS/FAIL レポートを生成

---

## セットアップ手順（開発向け）

以下は一般的なセットアップ手順です。プロジェクトに requirements.txt がある場合はそちらを優先してください。

1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo-root>

2. Python 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb psutil openai
   - optional: PyYAML（config/*.yaml の検証をする場合）: pip install pyyaml
   - sqlite3 は標準ライブラリ、duckdb は外部パッケージです。

   （プロジェクトに requirements.txt があれば `pip install -r requirements.txt`）

4. 環境変数設定
   - 対話式で作成する場合:
     - python -m kabusys.config_setup
   - 手動で .env を作る場合はプロジェクトルートに `.env` を配置。
   - 重要な必須環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
   - AI を使う場合:
     - OPENAI_API_KEY を設定（news_nlp / regime_detector が必要）

   参考となる設定項目：
   - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
   - DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
   - SQLITE_PATH: data/monitoring.db（監視 DB）
   - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用）
   - LOG_LEVEL, LOG_DIR, KILL_FLAG_CLEAR_ON_START, PAPER_FILL_MODE（instant/partial/never/reject） 等

   自動 .env ロード:
   - デフォルトで .env/.env.local を自動で読み込みます。無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

5. 設定検証（任意）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります。

---

## 使い方（代表的なコマンド）

- 実行エンジンを起動
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は MockBroker を使い data/paper_trading.db に記録（本番 DB と分離）
    - 起動時に data/stop_requested.flag が存在すると起動しません
    - 実行中に data/stop_requested.flag を作成すると停止シグナルとなります

- 監視ループを起動
  - python -m kabusys.run_monitoring
  - 環境変数:
    - MONITOR_POLL_INTERVAL（秒）: ポーリング間隔（デフォルト 60）
  - stop フラグファイル:
    - data/stop_requested.flag を検知するとループを終了します

- .env ウィザード（初期設定）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート（ツール）
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - --from YYYY-MM-DD --to YYYY-MM-DD
  - DB 指定:
    - --db PATH  または 環境変数 PAPER_TRADING_SQLITE_PATH

- AI / リサーチ関数（プログラムから呼ぶ）
  - Python スクリプト内で import して呼ぶ例:
    - from kabusys.ai import score_news
    - from kabusys.ai.regime_detector import score_regime
    - from kabusys.research import calc_momentum, calc_volatility, calc_value

- ログ
  - setup_logging により stdout と logs/<app_name>.log（日次ローテート、30日保存）へ出力
  - LOG_DIR 環境変数または引数でログ保存先を指定可能
  - LOG_LEVEL でログレベルを制御

---

## 重要な運用上の注意

- KABUSYS_ENV の値:
  - development: 開発・テスト用（発注なし）
  - paper_trading: ペーパートレード（MockBrokerClient、専用 DB）
  - live: 本番（実際に発注）
- Paper Trading は本番 DB と完全分離するよう設計されています。PAPER_TRADING_SQLITE_PATH を適切に設定してください。
- Kill Switch:
  - kill.flag（デフォルト: data/kill.flag）を書き込むことで ExecutionEngine に停止シグナルを送れます。
  - config の KILL_FLAG_CLEAR_ON_START が 1 の場合、起動時に自動クリアされます（本番では 0 推奨）。
- OpenAI など外部 API 使用時はキー管理に注意してください（環境変数 OPENAI_API_KEY）。
- プロセス優先度は起動時に"high"へ設定されます。プラットフォームにより設定が失敗することがあります（権限等）。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要ファイル・モジュールの概略です。

- src/kabusys/
  - __init__.py
  - __version__ = "0.1.0"
  - config.py
    - Settings クラス（環境変数の解決、自動 .env ロード）
  - config_setup.py
    - .env 対話ウィザード
  - validate_config.py
    - 起動前設定検証 CLI
  - run_execution.py
    - ExecutionEngine 起動スクリプト
  - run_monitoring.py
    - SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
      - raw_news を LLM で評価して ai_scores に書き込み
    - regime_detector.py
      - ma200 とマクロニュースを統合して market_regime を決定
  - research/
    - factor_research.py
      - calc_momentum, calc_volatility, calc_value
    - feature_exploration.py
      - calc_forward_returns, calc_ic, factor_summary, rank
  - portfolio/
    - portfolio_builder.py
      - select_candidates, calc_equal_weights, calc_score_weights
    - position_sizing.py
      - calc_position_sizes
    - risk_adjustment.py
      - apply_sector_cap, calc_regime_multiplier
    - __init__.py
  - monitoring/
    - monitoring_db.py
      - SQLite テーブル定義・MonitoringDB クラス
    - system_monitor.py
      - SystemMonitor（CPU/メモリ/ディスク/データ鮮度/プロセス監視）
    - trade_monitor.py
      - TradeMonitor（trade_logs の監視：滞留・約定異常 等）※詳細はコード参照
    - risk_monitor.py
      - RiskMonitor（ドローダウン・ポジション上限監視）
    - kill_switch.py
      - KillSwitch（kill.flag の書き込み/管理）
    - monitoring_engine.py
      - 複数 Monitor を束ねるループ実装
  - execution/
    - broker_factory.py, execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py
      - 発注/注文管理/リスク管理の実装（詳細は各ファイル参照）
  - utils/
    - logging_setup.py
      - ログ設定ユーティリティ（Stream + TimedRotatingFileHandler）
    - process_priority.py
      - プロセス優先度 / CPU affinity 設定（psutil 使用）
    - __init__.py

その他:
- config/*.yaml（system_config.yaml 等） — 存在しない場合は生成スクリプト等で作成する。validate_config が検出・チェックします。
- data/ ディレクトリ（デフォルト DB ファイル、flag、pid ファイルなどを格納）
- logs/ ディレクトリ（ログファイル出力先）

---

## 簡単な .env 例

以下は最低限必要なキーの例（絶対にソース管理にコミットしないでください）。

JQUANTS_REFRESH_TOKEN=your_jquants_token
KABU_API_PASSWORD=your_kabu_password
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
OPENAI_API_KEY=sk-...

---

## 開発・拡張に関するヒント

- DuckDB はリサーチ処理や AI 前処理で多用されます。データテーブル（prices_daily, raw_financials, raw_news など）のスキーマを確認してから関数を呼んでください。
- AI 周り（news_nlp / regime_detector）は外部 API に依存するため、テスト時は _call_openai_api 等をパッチしてモック化することを推奨します（コード内にその旨のコメントあり）。
- monitoring/monitoring_db.py はスキーマ変更時に互換マイグレーション処理を置いています（簡易的な ALTER 等）。既存 DB がある場合は注意してください。
- 実行環境（live）では KILL_FLAG_CLEAR_ON_START の設定や LINE 通知設定を十分に確認してください（validate_config にガードがあります）。

---

この README はコードベースに基づいた概要・手順をまとめたものです。各モジュールの詳細な使い方・パラメータは該当ソースコード内の docstring / コメントを参照してください。必要であれば個別モジュール向けの詳細ドキュメントも作成します。