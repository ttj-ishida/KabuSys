# KabuSys — README

KabuSys は日本株向けの自動売買・リサーチ基盤の一部を実装したパッケージです。本リポジトリには、発注実行エンジン、監視コンポーネント、ポートフォリオ構築ロジック、ファクター計算、LLM を使ったニュースセンチメント／レジーム判定などの主要機能が含まれます。

以下はこのコードベースの概要、機能、セットアップ手順、使い方、ディレクトリ構成の説明です。

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（主要サブコマンド）
- 重要な環境変数（抜粋）
- 実行時のプロセス／フラグファイル挙動
- ディレクトリ構成

---

## プロジェクト概要
KabuSys は日本株向けの自動売買システムのコンポーネント群です。設計方針としては
- 発注／リスク管理／注文リポジトリなどの Execution コンポーネント
- システム監視・アラート・Kill Switch を含む Monitoring コンポーネント
- ポートフォリオ構築（候補選定、配分、サイズ計算、セクター制約など）の純粋関数群
- DuckDB を用いたリサーチ（ファクター計算、特徴量探索）
- OpenAI を用いたニュース NLP（センチメント）とレジーム判定（LLM を API 経由で利用）
- 各種ユーティリティ（ロギング設定、プロセス優先度設定、設定管理 CLI）

を提供します。コードベースはモジュール化されており、ペーパートレード向けの分離（専用 SQLite）や設定検証・ウィザードも用意されています。

---

## 機能一覧（主なもの）
- Execution
  - ExecutionEngine を起動して注文処理を実行（BrokerClientFactory により本番/モック切替）
  - RiskManager / OrderManager / Reconciler 等による発注制御
  - Paper trading モードでは MockBrokerClient を使用し専用 DB（data/paper_trading.db）へ記録
- Monitoring
  - SystemMonitor: CPU／メモリ／ディスク／プロセス状態・データ鮮度の監視
  - TradeMonitor: 注文滞留・約定異常等の検出
  - RiskMonitor: ドローダウン／ポジション上限監視（リスクログ、ダッシュボード更新）
  - KillSwitch: 条件に従い data/kill.flag を書き込んで ExecutionEngine を停止させる仕組み
  - MonitoringEngine: 上記モニタを統合してポーリング実行
  - SQLite を用いる監視 DB（monitoring_db.py）: system_status / trade_logs / positions / risk_logs / dashboard
- Portfolio（純粋関数）
  - 候補選定、等配分／スコア配分、ポジションサイズ計算、セクターキャップ、レジーム乗数
- Research
  - DuckDB 接続でのファクター計算（momentum, volatility, value）
  - 将来リターン計算、IC（Information Coefficient）等の解析ユーティリティ
- AI（LLM 経由）
  - news_nlp.score_news: raw_news を集計して OpenAI（gpt-4o-mini 等）でセンチメント評価し ai_scores に書き込み
  - regime_detector.score_regime: ETF の MA 乖離とマクロニュースの LLM 評価を合成して market_regime を算出・書き込み
- ツール
  - 設定ウィザード: kabusys.config_setup で .env を対話式作成
  - 設定検証: kabusys.validate_config で .env と config/*.yaml のチェック
  - ペーパートレード検証レポート: kabusys.tools.paper_verification_report による集計レポート生成
- ユーティリティ
  - 統一的なロギング設定（stdout + 日次ローテートファイル）
  - プロセス優先度・CPU affinity 設定ユーティリティ
  - .env 自動読み込み（プロジェクトルートの .env / .env.local）

---

## セットアップ手順（開発・実行のための基本）
1. Python 環境
   - Python 3.9+ を推奨（コードは型注釈に modern syntax を使用）
   - 仮想環境を作成して有効化してください（venv / pyenv 等）

2. 依存ライブラリのインストール（例）
   - 必須（少なくとも以下を入れる）
     - duckdb
     - psutil
     - openai
   - 任意（機能拡張や検証）
     - PyYAML（config/*.yaml のパース検証用）
   - 例:
     pip install duckdb psutil openai PyYAML

   - sqlite3 は標準ライブラリに含まれます。

3. プロジェクト設定 (.env)
   - 初回は .env を作成する必要があります。対話式ウィザードを使う:
     python -m kabusys.config_setup
   - あるいは .env.example や README を参考に .env を作成してください。
   - 自動ロード: kabusys.config モジュールはプロジェクトルート（.git または pyproject.toml）を検出し .env/.env.local を読み込みます。自動読み込みを無効化する場合:
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

4. 設定検証（起動前チェック）
   - 全体チェック:
     python -m kabusys.validate_config
   - 警告も失敗としたい場合（--strict）:
     python -m kabusys.validate_config --strict

5. データディレクトリ / ログディレクトリ
   - デフォルトで以下を想定します:
     - data/（SQLite, pid, flag 等）
     - logs/（ログファイル）
   - 必要なら環境変数で上書きしてください（例: SQLITE_PATH, DUCKDB_PATH, LOG_DIR）

---

## 使い方（主要なコマンド例）
- 設定ウィザード（.env 作成）
  python -m kabusys.config_setup

- 設定検証
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- ExecutionEngine（発注エンジン）起動
  python -m kabusys.run_execution
  - KABUSYS_ENV によって本番 / paper_trading が切り替わります。
  - paper_trading の場合、MockBrokerClient が使われ、デフォルトで data/paper_trading.db を使用します。
  - 起動前に data/stop_requested.flag が存在すると起動をスキップします。

- Monitoring（監視ループ）起動
  python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で変更できます（デフォルト: 60）。
    例: export MONITOR_POLL_INTERVAL=30
  - 監視は常に本番用 sqlite_path（Settings.sqlite_path）を使用します。

- Paper Trading 検証レポート
  python -m kabusys.tools.paper_verification_report
  オプション:
    --from YYYY-MM-DD 期間開始
    --to YYYY-MM-DD   期間終了
    --db PATH         SQLite DB ファイルパス（PAPER_TRADING_SQLITE_PATH 環境変数でも指定可）
  例:
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

- LLM 関連（プログラム内 API）
  - ai.score_news / ai.regime_detector は Python API として提供されています。使用するには OpenAI API キー（環境変数 OPENAI_API_KEY）を設定してください。
  - 例（簡単な呼び出しイメージ）:
      from kabusys.ai.news_nlp import score_news
      import duckdb, datetime
      conn = duckdb.connect("data/kabusys.duckdb")
      score_news(conn, datetime.date(2026, 4, 11), api_key="sk-...")

  - 実行時は API 呼び出しのリトライやフェイルセーフが組み込まれています（失敗時はスキップして継続）。

---

## 重要な環境変数（抜粋）
- 基本
  - KABUSYS_ENV: 実行環境（development / paper_trading / live）。デフォルト: development
  - LOG_LEVEL: ログレベル（DEBUG/INFO/...）。デフォルト: INFO

- API キー
  - JQUANTS_REFRESH_TOKEN（必須）
  - KABU_API_PASSWORD（必須）
  - OPENAI_API_KEY（LLM 機能を使う場合）

- DB/ファイルパス
  - DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
  - PID_FILE_PATH: Execution pid ファイル（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH: Kill Switch フラグパス（デフォルト: data/kill.flag）
  - LOG_DIR: ログ出力先（デフォルト: logs/）

- Monitoring
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング秒数（デフォルト: 60）
  - CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT: 監視閾値（%）

- Paper trading
  - PAPER_FILL_MODE: MockBroker の fill 動作（instant / partial / never / reject）（デフォルト: instant）

- 自動ロード
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 にすると .env の自動読み込みを無効化

---

## 実行時のプロセス／フラグファイル挙動
- stop_requested.flag
  - run_execution / run_monitoring はプロジェクトルートの data/stop_requested.flag（各スクリプトが参照する位置はコードに依存）を監視しており、存在するとループを終了または起動をスキップします。
- kill.flag（Kill Switch）
  - KillSwitch（監視ロジック）が条件を満たすと data/kill.flag を書き込み、ExecutionEngine 側でこれを検知して停止できます。Settings によってパスは変更可能。
- PID ファイル
  - ExecutionEngine は pid_file を生成します（デフォルト: data/execution.pid）。
- プロセス優先度
  - 起動スクリプトは起動直後に set_process_priority("high") を試みます（プラットフォーム依存でスキップされる場合あり）。

---

## ディレクトリ構成（主要ファイルの説明）
以下は src/kabusys/ 配下の主要ファイル／モジュールと簡単な説明です。

- kabusys/
  - __init__.py — パッケージ定義（__version__ 等）
  - config.py — Settings クラス（環境変数読み込み、自動 .env ロード、デフォルト、バリデーション）
  - config_setup.py — 対話式 .env 作成ウィザード（CLI）
  - validate_config.py — 起動前設定検証 CLI（--strict）
  - run_execution.py — ExecutionEngine 起動スクリプト（メイン実行入口）
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
- ai/
  - news_nlp.py — ニュースセンチメント（OpenAI を利用）処理と ai_scores への書き込みロジック
  - regime_detector.py — 市場レジーム判定（MA + マクロセンチメント）
- monitoring/
  - monitoring_db.py — SQLite 監視 DB テーブル初期化と CRUD ヘルパー（MonitoringDB）
  - system_monitor.py — システム・データ鮮度監視
  - trade_monitor.py — （注文滞留・約定異常検出）※ファイル内関数あり
  - risk_monitor.py — ドローダウン・ポジション数監視とリスクログ出力
  - kill_switch.py — Kill Switch（kill.flag の書き込み/クリア）
  - monitoring_engine.py — 各 Monitor の統合ランナー
  - alert_manager.py — （アラート送信管理。LINE 等の実装が想定される）
- execution/
  - execution_engine.py — ExecutionEngine 実装（Run / run_session など）
  - broker_factory.py — Broker クライアント生成（本番 / モック判定）
  - order_manager.py, order_repository.py, reconciler.py, risk_manager.py — 発注管理関連
- portfolio/
  - portfolio_builder.py — 候補選定、重み計算
  - position_sizing.py — 株数計算・単元丸め・集計キャップ
  - risk_adjustment.py — セクターキャップ・レジーム乗数
- research/
  - factor_research.py — Momentum/Volatility/Value 等のファクター計算（DuckDB）
  - feature_exploration.py — 将来リターン計算、IC、統計サマリ等
- data/
  - （実行時に利用する SQLite / DuckDB ファイル、pid、flag 等を格納）
- tools/
  - paper_verification_report.py — ペーパートレード検証レポート生成用 CLI

（各ファイル中の docstring に詳細設計・注意点が含まれています。実装の詳細は該当モジュールをご参照ください。）

---

## 補足・運用上の注意
- 本番起動（KABUSYS_ENV=live）時は設定ミスが致命的になり得ます。validate_config でのチェックや .env の管理には十分に注意してください。
- .env ファイルは絶対にバージョン管理にコミットしないでください（config_setup の出力ヘッダも同様に警告があります）。
- LLM を利用する機能（news_nlp, regime_detector）は外部 API 呼び出しを行います。API キー管理、コスト管理、レートリミット対策に留意してください。
- DuckDB / SQLite のパスは環境変数で変更可能です。Paper trading は専用 DB を使用して本番 DB と分離されています。
- ログは stdout（常に出力）および logs/<app_name>.log（日次ローテート）へ保存されます。LOG_DIR 環境変数で変更可能です。

---

以上がこのリポジトリの README 相当の説明です。必要であれば、起動シーケンス図、各モジュールの API 使用例（コードスニペット）、あるいは運用時の具体的手順（systemd / systemctl ユニット例や Dockerfile など）を追加で作成できます。どの情報を優先して追加しますか？