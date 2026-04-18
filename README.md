# KabuSys

日本株自動売買システムのコードベース README（日本語）。

この README ではプロジェクト概要、主要機能、セットアップ手順、基本的な使い方、ディレクトリ構成を説明します。

注意: 本リポジトリは複数の実行スクリプト（ExecutionEngine / Monitoring 等）と分析・AI モジュールを含みます。実行前に .env を適切に設定し、必須の外部ライブラリ（duckdb, psutil, openai など）をインストールしてください。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買システム向けユーティリティ群と実行エンジン群を含むソフトウェアです。主要な責務は以下です。

- 注文発行・注文管理・リスク管理を行う ExecutionEngine（本番 / ペーパートレード対応）。
- システム稼働状況・データ鮮度・注文ログなどを監視する Monitoring（ポーリング）。
- ポートフォリオ構築（銘柄選定、重み付け、ポジションサイズ決定）用の純粋関数群。
- リサーチ用のファクター計算・特徴量解析モジュール（DuckDB を使った計算）。
- ニュースを LLM で評価して scoring を行う AI モジュール（OpenAI）。
- 運用支援ツール（.env 設定ウィザード、設定検証、ペーパートレーディング検証レポート生成 等）。

設計上のポイント:
- 設定は主に環境変数（.env）で管理。自動ロード機能あり（プロジェクトルートに .env / .env.local がある場合）。
- データベースは DuckDB（分析用）と SQLite（監視・発注ログ）を使用。
- Paper Trading（KABUSYS_ENV=paper_trading）は本番 DB から分離された専用 SQLite を使用。
- OpenAI との連携は外部 API キー（OPENAI_API_KEY）で設定。API 呼び出しはフェイルセーフなリトライとバリデーションを実装。

---

## 機能一覧

- 実行 / 発注
  - ExecutionEngine 起動スクリプト（python -m kabusys.run_execution）
  - Paper Trading モード（MockBrokerClient + data/paper_trading.db）
  - プロセス優先度設定（高優先）・PID ファイル管理

- 監視
  - SystemMonitor（CPU/メモリ/ディスク・プロセス生存・データ鮮度）
  - TradeMonitor（注文滞留・約定異常など）※実装モジュールあり
  - RiskMonitor（ドローダウン、ポジション数制限）
  - KillSwitch（重大なリスク検出時に data/kill.flag を書き込み ExecutionEngine を停止）
  - MonitoringEngine / run_monitoring スクリプト（定期ポーリング）

- ポートフォリオ構築（純粋関数）
  - 銘柄候補選定 (select_candidates)
  - 等金額 / スコア加重重み計算
  - セクター上限適用（apply_sector_cap）
  - レジーム乗数（calc_regime_multiplier）
  - ポジションサイズ算出（calc_position_sizes）

- リサーチ
  - momentum / volatility / value のファクター計算（DuckDB）
  - 将来リターン計算、IC（Information Coefficient）等の統計解析

- AI（ニュース NLP / レジーム判定）
  - raw_news を集約して OpenAI（gpt-4o-mini 等）でセンチメント評価
  - ai_scores / market_regime への書き込み（冪等処理・リトライ/バックオフ実装）
  - スコアのバリデーション・クリップ

- ユーティリティ
  - .env 対話式ウィザード（python -m kabusys.config_setup）
  - 設定検証 CLI（python -m kabusys.validate_config）
  - ペーパートレード検証レポート生成（python -m kabusys.tools.paper_verification_report）

---

## セットアップ手順（開発 / ローカル実行向け）

1. Python 環境
   - Python 3.10+ を推奨（ソースは型注釈などを使用）
   - 仮想環境を作成して有効化することを推奨

   例:
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS/Linux
   .venv\Scripts\activate      # Windows
   ```

2. 依存パッケージのインストール
   - 必要なパッケージ（主要なもの）:
     - duckdb
     - psutil
     - openai
     - PyYAML（config 検証で任意）
   - requirements.txt が無い場合は手動でインストール:
   ```
   pip install duckdb psutil openai PyYAML
   ```

3. プロジェクトルートとディレクトリ作成
   - デフォルトで使用するディレクトリ:
     - data/（SQLite DB, PID, フラグ等）
     - logs/（ログ出力）
   ```
   mkdir -p data logs
   ```

4. .env の作成
   - 対話式ウィザードで作成:
   ```
   python -m kabusys.config_setup
   ```
   - またはプロジェクトルートに .env を直接作成してください。
   - 自動ロード: プロジェクトルートに .env / .env.local があると自動で環境変数に読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

5. 設定検証（起動前に実行推奨）
   ```
   python -m kabusys.validate_config
   ```
   - --strict を付けると警告もエラー扱いになります。

---

## 使い方（主要コマンド、環境変数）

基本的にスクリプトはモジュール実行で起動します。

- ExecutionEngine（発注エンジン）起動:
  - 本番 / 開発 / ペーパーは KABUSYS_ENV に依存
  - Paper Trading は settings.paper_sqlite_path（デフォルト data/paper_trading.db）を使用
  ```
  # デフォルト: KABUSYS_ENV=development
  python -m kabusys.run_execution

  # ペーパートレード
  export KABUSYS_ENV=paper_trading
  python -m kabusys.run_execution
  ```

  注意:
  - 起動時に data/stop_requested.flag が既に存在する場合は起動せず終了します。
  - 実行中は data/execution.pid に PID が保存されます（settings.pid_file_path）。

- Monitoring（監視）起動:
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒で上書き（デフォルト 60 秒）
  ```
  export MONITOR_POLL_INTERVAL=30
  python -m kabusys.run_monitoring
  ```
  - run_monitoring は監視用 SQLite（settings.sqlite_path：デフォルト data/monitoring.db）を常に使用します（KABUSYS_ENV に依存しません）。
  - 停止するには data/stop_requested.flag を作成するか Ctrl+C。

- .env 対話式セットアップ:
  ```
  python -m kabusys.config_setup
  ```

- 設定検証:
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- ペーパートレード検証レポート:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # --db で DB パス上書き可。環境変数 PAPER_TRADING_SQLITE_PATH でも指定可。
  ```

- AI / リサーチ機能のプログラム呼び出し例（Python から直接使用）:
  ```py
  from kabusys.ai import score_news
  from kabusys.research import calc_momentum

  # DuckDB 接続を渡して使う（例）
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  score_count = score_news(conn, target_date=date(2026,4,10), api_key="sk-...")
  ```

主要な環境変数（抜粋）:
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV (development | paper_trading | live) — デフォルト development
- DUCKDB_PATH（デフォルト data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（ペーパー用 DB、デフォルト data/paper_trading.db）
- LOG_LEVEL（DEBUG/INFO/...、デフォルト INFO）
- OPENAI_API_KEY（AI 機能利用時に必要）
- MONITOR_POLL_INTERVAL（監視ポーリング秒数、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START（Execution 起動時に既存 kill.flag を自動クリアするか。0/1。デフォルト 0）

運用上のフラグファイル:
- data/stop_requested.flag — run_execution / run_monitoring はこの存在を監視し、存在するとループを終了します（手動停止用）。
- data/kill.flag — KillSwitch が書き込むことで ExecutionEngine に停止を促す（Settings.kill_flag_path で上書き可）。

ログ:
- ログはデフォルトで logs/<app_name>.log に日次ローテーションで出力されます。
- setup_logging(app_name="execution") などの呼び出しで統一されたログ設定になります。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要なモジュールと役割の一覧です。

- kabusys/
  - __init__.py — パッケージ定義（__version__）
  - config.py — 環境変数 / 設定読み込みと Settings クラス
  - config_setup.py — .env 対話式ウィザード CLI
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成スクリプト
  - utils/
    - logging_setup.py — 共通ロギング設定ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ
  - monitoring/
    - monitoring_db.py — SQLite 永続化（system_status / trade_logs / positions / risk_logs / dashboard）
    - system_monitor.py — CPU/メモリ/ディスク/データ鮮度/プロセス監視
    - risk_monitor.py — ドローダウン / ポジション数監視
    - kill_switch.py — Kill Switch（データ/ファイルフラグ）
    - monitoring_engine.py — 各 monitor を束ねるエンジン
    - (その他 alert_manager, trade_monitor 等が存在)
  - execution/
    - execution_engine.py — ExecutionEngine 本体（起動 / セッション管理）
    - order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py
      （発注・リスク管理周り）
  - portfolio/
    - portfolio_builder.py — 候補選定 / 重み計算
    - position_sizing.py — 発注株数決定・キャップ処理
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — モメンタム / ボラティリティ / バリュー計算（DuckDB）
    - feature_exploration.py — 将来リターン・IC・統計サマリー
  - ai/
    - news_nlp.py — ニュースセンチメントを OpenAI で評価して ai_scores に書き込み
    - regime_detector.py — マクロニュース + ETF ma200 で市場レジーム判定

その他:
- data/ — 実行時に使用する SQLite/フラグ/PID を置く（デフォルト、リポジトリに含めないこと）
- logs/ — ログファイル出力先（デフォルト）

---

## 運用上の注意・ベストプラクティス

- 本番環境（KABUSYS_ENV=live）では .env に機密情報が含まれるため Git にコミットしないでください（config_setup でも注意喚起あり）。
- validate_config を使って必須環境変数や DB パス等を起動前に確認してください。
- Monitoring は settings.sqlite_path（監視 DB）を本番 DB として常に参照します。ペーパートレードとは分離して運用してください。
- KillSwitch / kill.flag の動作を理解し、安全に停止できる運用手順を整備してください。KILL_FLAG_CLEAR_ON_START=1 を本番で有効にするのは危険です（自動クリアされるため）。
- OpenAI を使用する機能は API 使用料とレイテンシを考慮してください。API キーは安全に管理してください。
- ログディレクトリ作成に失敗した場合はコンソール出力のみで継続しますが、監査のためログ保存先を確実に確保してください。

---

必要があれば、README に含めるサンプル .env のテンプレートや、ExecutionEngine / Monitoring のより詳しい設定項目（risk config や EngineConfig のチューニングパラメータ）、およびユニットテストの実行方法などを追加できます。どの情報を優先して追加しますか？