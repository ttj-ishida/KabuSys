# KabuSys — 日本株自動売買システム

このリポジトリは、ローカル/ペーパートレード/本番に対応した日本株自動売買システムのコア実装です。戦略リサーチ、ポートフォリオ構築、ポジションサイジング、実行エンジン、監視・キルスイッチ、AI によるニュース解析などの機能を含みます。

この README はプロジェクト概要、主な機能、セットアップ手順、基本的な使い方、ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は以下を目的としたモジュール群で構成された自動売買フレームワークです。

- ファクター計算・特徴量生成（DuckDB を用いた履歴データ処理）
- ポートフォリオ構築（候補選定・重み計算）
- ポジションサイジング（リスク制約・単元丸め・スケール調整）
- ExecutionEngine による発注処理（本番 / ペーパートレード分離）
- 監視（SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch）
- ニュース NLP（OpenAI を用いた銘柄別センチメント）
- 市場レジーム判定（MA + マクロセンチメント合成）
- 運用補助ツール（設定ウィザード、設定検証、ペーパートレード検証レポート等）

設計上の特徴：
- 本番 DB とペーパートレード DB を分離（KABUSYS_ENV に依存）
- DuckDB を分析用 DB として利用
- .env による環境設定 + 対話式ウィザード
- ログはコンソール（stdout）＋日次ローテートファイル出力
- フェイルセーフ（API 失敗やデータ欠損時は安全なフォールバックを行う）

---

## 主な機能一覧

- 設定管理
  - .env の自動読み込み/対話式生成（kabusys.config_setup）
  - 起動前の構成検証（kabusys.validate_config）
- 実行（Execution）
  - run_execution: ExecutionEngine の起動（KABUSYS_ENV=paper_trading 時は MockBroker 使用、専用 SQLite に記録）
  - 発注履歴の記録 / OrderManager / RiskManager（サーキットブレーカー等）
- 監視（Monitoring）
  - run_monitoring: SystemMonitor のポーリングループ（MONITOR_POLL_INTERVAL で間隔指定可能）
  - MonitoringDB（SQLite）への system_status、trade_logs、risk_logs、dashboard 保存
  - KillSwitch による停止フラグ（data/kill.flag）
- ポートフォリオ構築
  - 候補選出、等重/スコア重み付け、セクターキャップ、レジーム乗数
  - ポジションサイズ算出（単元丸め、aggregate cap、cost_buffer）
- リサーチ/ファクター
  - Momentum / Volatility / Value 等のファクター計算（DuckDB）
  - 将来リターン、IC、統計サマリー（外部依存を最小化）
- AI（OpenAI）
  - ニュース記事を LLM（gpt-4o-mini 等）でセンチメント評価し ai_scores に格納
  - マクロニュース + ETF MA による市場レジーム判定
- ツール
  - paper_verification_report: ペーパートレード DB を解析して Pass/Fail レポートを生成

---

## セットアップ手順（ローカル開発向け）

以下は開発マシンでの基本的なセットアップ例です。

1. リポジトリをクローンし Python 仮想環境を作成
   ```bash
   git clone <repo-url>
   cd <repo-root>
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   pip install --upgrade pip
   ```
   必要なパッケージは requirements.txt / pyproject.toml に合わせてインストールしてください（本リポジトリでは明示的な manifest がないため、使用する機能に応じて duckdb, psutil, openai, PyYAML 等を追加してください）。

2. .env を作成（対話式ウィザード推奨）
   ```bash
   python -m kabusys.config_setup
   ```
   ウィザードに従って J-Quants トークンや kabuステーション API パスワード等を入力して `.env` を作成します。

   もしくは手動で `.env` を作成します（最小必須）:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_token
   KABU_API_PASSWORD=your_kabu_password
   KABUSYS_ENV=development
   SQLITE_PATH=data/monitoring.db
   DUCKDB_PATH=data/kabusys.duckdb
   LOG_LEVEL=INFO
   ```

   必須環境変数:
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD

   オプション / 注意:
   - OPENAI_API_KEY は AI 機能（news_nlp / regime_detector）を使う場合に必要
   - KABUSYS_ENV: development | paper_trading | live
     - paper_trading: MockBroker を使用し、データは data/paper_trading.db に記録されます
     - live: 実際に発注が行われます（本番用設定に注意）

3. 設定検証
   ```bash
   python -m kabusys.validate_config
   # 警告を FAIL 扱いにする場合:
   python -m kabusys.validate_config --strict
   ```

4. データディレクトリ・ログディレクトリの準備（通常は自動作成されます）
   - data/ : DB や PID / flag ファイルを格納
   - logs/ : アプリケーションログ（app_name ごとにファイル生成）

---

## 使い方（起動コマンド・主なスクリプト）

- 実行エンジン（ExecutionEngine）を起動
  - 本番 / ペーパートレードは KABUSYS_ENV に依存
  ```bash
  python -m kabusys.run_execution
  ```
  - 実行中は data/execution.pid が使用されます。data/stop_requested.flag が作成されると Engine を停止します。

- 監視を起動（SystemMonitor のポーリング）
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60 秒）
  ```bash
  export MONITOR_POLL_INTERVAL=30
  python -m kabusys.run_monitoring
  ```

- 設定ウィザード（.env の生成/更新）
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  ```

- ペーパートレード検証レポート生成
  ```bash
  # デフォルト DB: data/paper_trading.db
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB パスを指定する場合:
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

- AI 関連（ニューススコア / レジーム判定）を呼び出す
  - OPENAI_API_KEY を設定した上で、該当モジュールの関数を呼び出す（例: kabusys.ai.score_news, kabusys.ai.regime_detector.score_regime）。これらはスクリプト化して起動することも可能です。

---

## 主要ファイル・重要な挙動メモ

- run_monitoring.py
  - MONITOR_POLL_INTERVAL（秒）でループ
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用（監視用は本番 DB を参照）
  - 停止は data/stop_requested.flag により検出

- run_execution.py
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用、データは data/paper_trading.db に記録
  - 停止フラグ: data/stop_requested.flag
  - PID 管理: data/execution.pid

- config.py
  - 環境変数読み込みロジック、.env/.env.local 自動読み込み（プロジェクトルート検出あり）
  - Settings クラスで各種パスやフラグを取得する API を提供

- monitoring/
  - monitoring_db.py: SQLite テーブル定義と MonitoringDB（読み書き API）
  - system_monitor.py / trade_monitor.py / risk_monitor.py / kill_switch.py / monitoring_engine.py: 監視スタック

- ai/
  - news_nlp.py: 銘柄別ニュースを LLM に送信し ai_scores に書込み
  - regime_detector.py: ETF(1321) の MA とマクロニュース LLM 結果を合成して市場レジーム判定

- portfolio/
  - portfolio_builder.py / risk_adjustment.py / position_sizing.py: 候補選択・重み計算・ポジション数決定ロジック

- research/
  - factor_research.py / feature_exploration.py: ファクター計算・IC・統計サマリー

- utils/
  - logging_setup.py: 標準化されたログ設定（stdout + TimedRotatingFileHandler）
  - process_priority.py: クロスプラットフォームでのプロセス優先度設定（psutil 依存）

---

## ディレクトリ構成

（src/kabusys 以下の主要ファイル群の概略）

- src/
  - kabusys/
    - __init__.py
    - config.py
    - config_setup.py
    - validate_config.py
    - run_execution.py
    - run_monitoring.py
    - data/                # （実行時に使用される）DB や flag、pid ファイルを格納するディレクトリ（プロジェクトルート直下）
    - logs/                # ログディレクトリ（デフォルト）
    - execution/
      - broker_factory.py
      - execution_engine.py
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - risk_manager.py
    - monitoring/
      - monitoring_db.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - monitoring_engine.py
      - alert_manager.py
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - factor_research.py
      - feature_exploration.py
    - ai/
      - news_nlp.py
      - regime_detector.py
    - tools/
      - paper_verification_report.py
    - utils/
      - logging_setup.py
      - process_priority.py
    - monitoring/          # 監視関連（上記）
    - research/            # リサーチ用コード
    - portfolio/           # ポートフォリオ構築コード

（実際のリポジトリではさらにサブモジュールや補助スクリプトが存在します。上は主要モジュールの抜粋です。）

---

## 環境変数（主要）

- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 動作モード
  - KABUSYS_ENV (development | paper_trading | live)
- DB パス
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (監視用, デフォルト: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (PAPER トレード用 DB, デフォルト: data/paper_trading.db)
- ログ
  - LOG_LEVEL (DEBUG/INFO/...)
  - LOG_DIR
- AI
  - OPENAI_API_KEY (news_nlp / regime_detector で使用)
- 監視・制御
  - MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔）
  - PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START

詳細は `src/kabusys/config.py` を参照してください。

---

## 運用上の注意

- KABUSYS_ENV=live に設定する場合は特に注意して各種認証情報・通知設定（LINE）・KILL SW の挙動を確認してください。validate_config は live 時に追加の警告を出します。
- run_execution はデフォルトで高優先度プロセスに設定しようとします（OS によっては権限不足で失敗する場合があります）。
- monitoring は監視 DB（SQLite）へ永続化します。必要に応じて DB ファイルのバックアップを行ってください。
- OpenAI を利用する機能は API コストが発生します。API キーの管理とコスト管理にご注意ください。
- .env は機密情報を含むため絶対にリポジトリにコミットしないでください。

---

## 参考コマンドまとめ

- .env ウィザード
  ```bash
  python -m kabusys.config_setup
  ```
- 設定検証
  ```bash
  python -m kabusys.validate_config
  ```
- ExecutionEngine 起動
  ```bash
  python -m kabusys.run_execution
  ```
- Monitoring 起動
  ```bash
  MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
  ```
- Paper Trading レポート
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

必要であれば、この README をベースに「運用マニュアル（デプロイ手順、systemd / supervisor 設定例、バックアップ手順、ロギング・アラート設定）」や「開発者向けドキュメント（モジュール別 API 詳細）」を追加作成できます。どの情報を追加したいか教えてください。