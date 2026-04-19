# KabuSys — README (日本語)

概要
---
KabuSys は日本株の自動売買・研究・監視のための軽量フレームワークです。本リポジトリは以下の主要機能を持ちます。

- 発注エンジン（ExecutionEngine、paper/live 切替）
- 監視（System / Trade / Risk のポーリングとアラート / Kill Switch）
- ポートフォリオ構築（候補選定・重み付け・株数決定）
- 研究用モジュール（ファクター計算・将来リターン・IC 等）
- AI 補助（ニュースセンチメント、レジーム判定）
- 運用支援ツール（環境設定ウィザード、設定検証、Paper Trading 検証レポート）

ライセンスや商用利用のルールはリポジトリのトップ（別途用意）を参照してください。

主な機能一覧
---
- 設定管理
  - Settings クラスで環境変数/.envから設定を取得
  - .env の自動ロード（プロジェクトルート検出）。無効化可能: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- 起動スクリプト
  - run_execution.py: 発注エンジンの起動（KABUSYS_ENV=paper_trading 時は MockBroker を使用し Paper DB に分離）
  - run_monitoring.py: 監視ループ（MONITOR_POLL_INTERVAL でポーリング間隔を変更可能）
- 監視・Kill Switch
  - system_monitor / trade_monitor / risk_monitor を束ねる monitoring_engine
  - KillSwitch により条件を満たすと data/kill.flag を書き込みエンジン停止を指示
- ポートフォリオ構築
  - 候補選定、等重・スコア重み、ポジションサイジング、セクター上限適用、レジーム乗数
- 研究機能
  - DuckDB を用いたファクター計算（momentum / volatility / value）
  - 将来リターン、IC 計算、統計サマリー
- AI 機能（OpenAI）
  - news_nlp: ニュース記事を集約して LLM でセンチメントスコアを取得、ai_scores に書き込み
  - regime_detector: ETF (1321) の MA200 とマクロセンチメントを合成して日次レジーム判定
- 運用ツール
  - config_setup.py: 対話式で .env を作成/更新
  - validate_config.py: .env と config/*.yaml の検証
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成

セットアップ手順
---
前提: Python 3.10+ を想定（typing や構文に依存）。環境は仮想環境を推奨します。

1. リポジトリをクローンし仮想環境を作成・有効化
   ```bash
   git clone <repo-url>
   cd <repo-dir>
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```

2. 必要なパッケージをインストール
   - 本リポジトリは以下の外部ライブラリを利用します（最小限）:
     - duckdb
     - psutil
     - openai (AI 機能を使用する場合)
     - PyYAML（config の内容チェックを有効にする場合）
   - 例:
   ```bash
   pip install duckdb psutil openai PyYAML
   ```
   - 実運用では requirements ファイルを用意している場合はそちらを使用してください。

3. .env を作成（対話ウィザード推奨）
   ```bash
   python -m kabusys.config_setup
   ```
   - ウィザードは .env を生成します。生成後、`python -m kabusys.validate_config` で検証してください。
   - 自動ロードを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します（テスト時等）。

主要な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の約定モード（instant/partial/never/reject、デフォルト: instant）
- OPENAI_API_KEY: OpenAI を使う場合に設定
- LOG_LEVEL, LOG_DIR など

使い方（起動・実行）
---
- 設定検証
  ```bash
  python -m kabusys.validate_config
  # 警告もエラーにしたい場合:
  python -m kabusys.validate_config --strict
  ```

- 実行エンジンの起動（ExecutionEngine）
  ```bash
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、データは PAPER_TRADING_SQLITE_PATH（既定: data/paper_trading.db）へ分離保存されます。
  - 起動時に data/stop_requested.flag が存在する場合は起動を行わず終了します。
  - 実行エンジンは data/execution.pid（デフォルト）を PID ファイルとして利用します。

- 監視ループの起動（SystemMonitor）
  ```bash
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔を環境変数で上書き可能:
    ```bash
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    ```
    （デフォルトは 60 秒。1 秒以上の正の整数を指定）
  - 監視は monitoring.db（Settings.sqlite_path）を使用し、init_monitoring_db により必要なテーブルの作成/マイグレーションが行われます。
  - 監視は常に本番の sqlite_path を使う点に注意（monitoring は環境にかかわらず本番 DB を参照する実装）。

- Paper Trading 検証レポート生成
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - デフォルト DB は data/paper_trading.db。別パスを使う場合は --db で指定、または環境変数 PAPER_TRADING_SQLITE_PATH を設定。

- AI 機能（ニューススコア・レジーム判定）
  - news_nlp.score_news(conn, target_date, api_key=None) を利用。OpenAI API キーは引数か OPENAI_API_KEY 環境変数で指定。
  - regime_detector.score_regime(conn, target_date, api_key=None) も同様。
  - 実行スクリプトは提供されていないため、DuckDB 接続を作って Python から呼び出します。

運用上のファイル / フラグ
- data/stop_requested.flag — 実行スクリプトの外部停止（run_* スクリプトが起動中に存在を検知）
- data/kill.flag — KillSwitch による Execution エンジン停止要求（監視側が書き込み）
- data/execution.pid — ExecutionEngine の PID を出力（起動スクリプトで使用）
- ログ: デフォルトは logs/<app_name>.log（日次ローテーション、30日保持）

実装上の注意点
- Settings は起動時に .env を自動ロードします（プロジェクトルート検出）。テスト等で自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- run_execution は paper_trading の場合に paper_sqlite_path を使用して本番 DB と分離します。誤って本番 DB を上書きしないよう注意してください。
- monitoring 側は環境にかかわらず本番 sqlite_path を使用する実装になっています。運用時は設定を確認してください。
- OpenAI を使う処理は外部 API 依存のため、API エラー時はフェイルセーフ（代替値やスキップ）をとるよう設計されていますが、API キーの管理には注意してください。
- logging_setup でログディレクトリ作成に失敗した場合はコンソール出力にフォールバックします。

ディレクトリ構成（主なファイル）
---
src/kabusys/
- __init__.py
- config.py — 環境変数/.env ロード、Settings クラス
- config_setup.py — .env 対話ウィザード
- validate_config.py — 起動前設定検証ツール
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト

サブパッケージ
- ai/
  - news_nlp.py — ニュースセンチメント（OpenAI）
  - regime_detector.py — 市場レジーム判定（OpenAI + MA）
- monitoring/
  - monitoring_db.py — SQLite テーブル作成・永続化層
  - system_monitor.py, trade_monitor.py, risk_monitor.py — 各種モニタ
  - monitoring_engine.py — モニタまとめ、KillSwitch/Alert 管理
  - kill_switch.py, alert_manager.py（アラート系）
- execution/ (発注関連コンポーネント — BrokerFactory 等)
  - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py
- portfolio/
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py
- research/
  - factor_research.py, feature_exploration.py
- tools/
  - paper_verification_report.py — Paper Trading レポート
- utils/
  - logging_setup.py — ログ設定ユーティリティ
  - process_priority.py — プロセス優先度 / CPU affinity
- monitoring/monitoring_db.py etc.

（上記は主要ファイルの抜粋です。詳細はソースツリーを参照してください。）

開発・デバッグヒント
---
- ログレベルは LOG_LEVEL 環境変数で指定できます（DEBUG/INFO/WARNING/ERROR/CRITICAL）。
- run_monitoring などは MONITOR_POLL_INTERVAL を短くしてテストするのが便利です（ただし実運用では標準 60 秒推奨）。
- .env は絶対にバージョン管理に含めないでください（機密情報を含むため）。
- DuckDB を使った研究関数は副作用がなく、安全にローカルで分析できます。テスト時は小さな DuckDB ファイルを使って検証してください。

おわりに
---
この README はリポジトリの主要な使い方と構成を簡潔にまとめたものです。各モジュールの詳細な挙動・パラメータはソース内の docstring を参照してください。運用時は validate_config による検証を行い、.env の設定とログ出力を必ず確認してください。質問や追加のドキュメントが必要であればお知らせください。