# KabuSys — 日本株自動売買システム（README）

簡潔な日本語ドキュメントです。本リポジトリは日本株の自動売買システム（分析・発注・監視・レポート生成など）を構成する Python モジュール群を含みます。以下はプロジェクト概要・機能・セットアップ・使い方・ディレクトリ構成の要約です。

## プロジェクト概要
KabuSys は日本株の自動売買に関連するコンポーネント群を提供します。主な要素は次の通りです：

- ExecutionEngine（発注エンジン、実発注およびペーパートレード対応）
- Monitoring（システム稼働・注文・リスクを監視し Kill Switch を発動可能）
- Research（DuckDB を使ったファクター計算・特徴量解析）
- AI モジュール（ニュースの NLP スコアリング、レジーム判定。OpenAI API 使用）
- ポートフォリオ構築・サイズ計算ロジック（純粋関数群）
- ユーティリティ（ロギング設定、プロセス優先度設定など）
- 運用支援ツール（設定ウィザード、設定検証、Paper Trading 検証レポート）

設計方針の一部：
- データ分析は DuckDB を使用（prices_daily / raw_financials 等を参照）
- 本番 DB と paper_trading_DB を分離（KABUSYS_ENV による切替）
- 外部 API 呼び出し（OpenAI 等）は適切なエラーハンドリングとリトライを実装
- ルックアヘッドバイアス回避のため日付取得の扱いに注意

## 主な機能一覧
- 起動スクリプト
  - run_execution.py: ExecutionEngine の起動（KABUSYS_ENV=paper_trading 時は MockBroker を使用）
  - run_monitoring.py: SystemMonitor のポーリングループ起動（ポーリング間隔は MONITOR_POLL_INTERVAL で上書き可能）
- 設定ツール
  - config_setup.py: 対話式 .env 作成ウィザード
  - validate_config.py: .env や config/*.yaml の起動前検証
- 監視
  - monitoring_engine.py: 各 Monitor を束ねた実行ループ
  - system_monitor.py, trade_monitor.py, risk_monitor.py: システム・注文・リスク監視
  - kill_switch.py: 条件に応じて data/kill.flag を書き込み ExecutionEngine を停止
  - monitoring_db.py: 監視ログ用 SQLite スキーマと読み書き API
- 研究／リサーチ
  - research/factor_research.py: モメンタム / バリュー / ボラティリティ計算
  - research/feature_exploration.py: 将来リターン計算、IC 計算、統計サマリ
- AI
  - ai/news_nlp.py: ニュース記事を OpenAI に送り銘柄別センチメントスコアを生成
  - ai/regime_detector.py: ETF + マクロニュースで市場レジーム（bull/neutral/bear）判定
- ポートフォリオ構築
  - portfolio/portfolio_builder.py: 候補選定・重み計算
  - portfolio/position_sizing.py: 発注株数計算（リスク制約・単元丸め・aggregate cap）
  - portfolio/risk_adjustment.py: セクターキャップ・レジーム乗数
- ツール
  - tools/paper_verification_report.py: Paper Trading DB から検証レポート生成

## 環境変数（主要）
必須・重要なもの：
- JQUANTS_REFRESH_TOKEN — J-Quants API 用
- KABU_API_PASSWORD — kabuステーション API パスワード
- OPENAI_API_KEY — OpenAI API キー（AI モジュール使用時）
- KABUSYS_ENV — 実行環境（development / paper_trading / live）

運用上の主要設定例：
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db） — Monitoring 用
- PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db） — paper_trading 用
- LOG_LEVEL（DEBUG/INFO/...）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（LINE 通知）
- PAPER_FILL_MODE（instant / partial / never / reject）
- KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするか。0/1）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔（秒））

.env をプロジェクトルートに配置すると自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

## セットアップ手順（ローカル開発想定）
1. Python の準備
   - 推奨: Python 3.10 以上（コードは型注釈や最新ライブラリを想定）
2. 依存ライブラリのインストール（例）
   - requirements.txt が無ければ次の主要パッケージをインストールしてください:
     - duckdb
     - psutil
     - openai
     - (オプション) PyYAML（config/*.yaml の構文チェック用）
   - 例:
     ```bash
     pip install duckdb psutil openai pyyaml
     ```
3. プロジェクトルートに .env を作成
   - 対話式に作る場合:
     ```bash
     python -m kabusys.config_setup
     ```
   - 作成後、設定検証:
     ```bash
     python -m kabusys.validate_config
     # 警告を FAIL 扱いにする場合:
     python -m kabusys.validate_config --strict
     ```
4. データディレクトリ作成（必要に応じて）
   - デフォルトでは data/ 下に DB・フラグファイル等を保持します:
     ```bash
     mkdir -p data logs
     ```
5. DB 初期化
   - monitoring 用 SQLite（run_execution / run_monitoring が起動時にテーブルを作成します）
   - DuckDB ファイルはスクリプト側でファイルを作成・アクセスします

## 使い方（主要コマンド例）
- ExecutionEngine 起動（本番またはペーパー）
  - 通常（KABUSYS_ENV に従う）:
    ```bash
    python -m kabusys.run_execution
    ```
  - ペーパートレードに切り替える:
    ```bash
    export KABUSYS_ENV=paper_trading
    python -m kabusys.run_execution
    ```
  - 注意: paper_trading では MockBrokerClient を用い、データは PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に分離保存されます。

- Monitoring 起動（SystemMonitor のポーリング）
  - ポーリング間隔を秒で指定（環境変数で上書き、デフォルト 60 秒）:
    ```bash
    export MONITOR_POLL_INTERVAL=30
    python -m kabusys.run_monitoring
    ```
  - 監視は MonitoringDB（sqlite）にログを保存します。監視は KABUSYS_ENV に関係なく production の sqlite_path を参照します（監視は常に本番 DB を監視）。

- 設定作成・検証
  - ウィザード:
    ```bash
    python -m kabusys.config_setup
    ```
  - 検証:
    ```bash
    python -m kabusys.validate_config
    ```

- Paper Trading 検証レポート生成
  - デフォルト DB 参照:
    ```bash
    python -m kabusys.tools.paper_verification_report
    ```
  - 期間指定・DB 指定:
    ```bash
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11 --db data/paper_trading.db
    ```

- AI 関連（ニューススコア、レジーム判定）
  - news_nlp.score_news / regime_detector.score_regime を呼び出すことで DuckDB 内の raw_news 等を使いスコア生成（OpenAI API キーが必要）。
  - 例（内部 API 呼び出しのため CLI スクリプトは提供されていません。スクリプトから関数を呼ぶ想定）:
    ```python
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, target_date=date.today(), api_key="sk-...")
    ```

- Kill Switch / 停止フラグ
  - 監視側・運用側の保護機構として data/kill.flag を作成すると ExecutionEngine 側で停止が検出されます（KillSwitch は drawdown やポジション上限で書き込みます）。
  - 強制停止フラグ（run_* スクリプトの監視停止）: run_monitoring/run_execution は data/stop_requested.flag をみてループを抜けます（stop_requested.flag の書き込みで安全停止）。

## ログとプロセス管理
- ログ:
  - デフォルトログディレクトリ: logs/
  - ログファイル: logs/<app_name>.log（app_name 例: execution, monitoring）
  - ローテーション: 日次、30 日保持
  - LOG_DIR / LOG_LEVEL 環境変数で変更可能
- プロセス優先度:
  - 起動時に set_process_priority("high") が呼ばれます（psutil を使用。権限がない場合は警告を出してスキップ）
- PID / フラグ:
  - ExecutionEngine は data/execution.pid（デフォルト）を使用して PID 管理
  - 停止判定は data/stop_requested.flag（スクリプトで参照）や data/kill.flag（KillSwitch）

## ディレクトリ構成（概略）
以下はリポジトリ内の主要ファイル・ディレクトリ（抜粋）です。

- src/
  - kabusys/
    - __init__.py
    - config.py
    - config_setup.py
    - validate_config.py
    - run_execution.py
    - run_monitoring.py
    - utils/
      - logging_setup.py
      - process_priority.py
    - monitoring/
      - monitoring_db.py
      - system_monitor.py
      - trade_monitor.py (参照あり)
      - risk_monitor.py
      - kill_switch.py
      - monitoring_engine.py
      - alert_manager.py (参照あり)
    - execution/
      - broker_factory.py (参照あり)
      - execution_engine.py (参照あり)
      - order_manager.py (参照あり)
      - order_repository.py (参照あり)
      - reconciler.py (参照あり)
      - risk_manager.py (参照あり)
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
      - __init__.py
    - research/
      - factor_research.py
      - feature_exploration.py
      - __init__.py
    - ai/
      - news_nlp.py
      - regime_detector.py
      - __init__.py
    - tools/
      - paper_verification_report.py
      - __init__.py
    - data/ (実行時に使用/生成)
      - monitoring.db (default)
      - paper_trading.db (paper_trading 用)
      - kill.flag, stop_requested.flag, execution.pid など
- logs/（実行時に生成されるログディレクトリ）

（上記は現状コードベースから抽出したファイル群の代表的な一覧です。実運用では config/*.yaml や追加スクリプトが存在する可能性があります。）

## 運用上の注意
- KABUSYS_ENV によるモード切替を正しく設定してください（特に live モードは慎重に）。
- OpenAI API を利用する箇所は API キーとコストに注意（リクエスト回数・レート制限）。
- monitoring は常に production の sqlite_path を参照します（環境に関係なく監視対象は production DB）。
- Kill Switch の誤発動を避けるため、本番では KILL_FLAG_CLEAR_ON_START=0 を推奨します。
- .env ファイルは絶対に VCS にコミットしないでください（秘密情報を含むため）。
- DuckDB / SQLite のバックアップ・マイグレーションの運用ポリシーを確立してください。

---

必要であれば以下を追加で作成できます：
- requirements.txt（実行に必要なパッケージの固定）
- systemd / supervisor 用のサービスユニット例
- 詳細な API リファレンス（各モジュールの public 関数一覧と引数説明）
- テストケースと CI 設定

この README を元に導入や運用に関してさらに詳細なドキュメントが必要であれば、どの項目を深掘りするか教えてください。