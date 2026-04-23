# KabuSys — 日本株自動売買システム

このリポジトリは日本株向けの自動売買システム（KabuSys）の実装です。戦略・ポートフォリオ構築・実行エンジン・監視・研究ツール・AI（ニュースセンチメント／レジーム判定）などのコンポーネントを含みます。

概要
- 目的: 日本株の自動売買に必要なコンポーネント群を提供する（シグナル生成は Research / Strategy 層、発注は Execution 層、稼働監視は Monitoring 層）。
- 設計方針:
  - 本番（live）とペーパートレード（paper_trading）を明確に分離（DBやブローカークライアントを分ける）。
  - DuckDB を分析（prices_daily / raw_financials 等）に使用、SQLite を監視／発注ログに使用。
  - OpenAI を使ったニュース NLP / レジーム判定はフェイルセーフ設計（API失敗時は安全側フォールバック）。
  - .env ベースの設定管理（自動読み込み、対話式ウィザード、検証ツールあり）。

主な機能一覧
- 実行（Execution）
  - ExecutionEngine：ブローカー連携、オーダー管理、リスク管理、再整合処理（Reconciler）。
  - BrokerClientFactory：本番/ペーパーに応じたブローカークライアント生成（ペーパーは MockBrokerClient）。
  - ペーパートレード専用 SQLite（data/paper_trading.db）で本番DBと完全分離。
- 監視（Monitoring）
  - SystemMonitor / TradeMonitor / RiskMonitor：システム状態、注文状態、ドローダウンやポジション上限を監視。
  - MonitoringEngine：各 Monitor を束ねて周期的に実行、アラート送信／Kill Switch 評価。
  - Kill Switch：条件（例: ドローダウン超過）で data/kill.flag を書き、実行エンジンに停止信号を送る。
  - 永続化：SQLite に system_status, trade_logs, positions, risk_logs, dashboard テーブルを持つ。
- ポートフォリオ構築（Portfolio）
  - 候補選定、重み計算（等分／スコア加重）、セクターキャップ、レジーム乗数、株数決定（単元丸め・リスクベース等）。
- 研究（Research）
  - ファクター計算（Momentum / Volatility / Value 等）、将来リターン計算、IC（Information Coefficient）、統計サマリー。
  - DuckDB を直接参照して高速に集計・計算。
- AI（OpenAI）
  - news_nlp: raw_news を OpenAI に渡して銘柄ごとのセンチメント（ai_scores）を生成・保存。
  - regime_detector: ETF（1321）200日MA乖離＋マクロニュースセンチメントを合成して市場レジーム判定を行い DB に保存。
  - いずれも API 失敗時は安全側のフォールバックを採る。
- ツール
  - config_setup: 対話式 .env ウィザードで初期設定を手助け。
  - validate_config: .env / config/*.yaml の整合性チェック（--strict オプションあり）。
  - paper_verification_report: ペーパートレード DB を集計して検証レポート（稼働率・注文成功率・レイテンシ等）を生成。

セットアップ手順（ローカル開発向け）
1. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール（代表的な依存）
   - pip install duckdb psutil openai
   - 任意: PyYAML（config/*.yaml の検証を行う場合）: pip install PyYAML
   - 実プロジェクトでは requirements.txt / pyproject.toml を用意している想定です。ない場合は上記パッケージを手動で入れてください。

3. プロジェクトルートを確認
   - repository のルートに .env や config/ ディレクトリ、data/、logs/ が存在する想定です。初回は data/ と logs/ を作成しておくと安全です。
     - mkdir -p data logs

4. 対話式ウィザードで .env を作成
   - python -m kabusys.config_setup
   - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD。KABUSYS_ENV を paper_trading や live に設定可能。

5. 設定検証
   - python -m kabusys.validate_config
   - --strict をつけると警告も失敗扱いになります。

環境変数（主なもの）
- 必須（最低限）:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 実行環境関連:
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト: INFO）
- DB / パス:
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（ペーパートレード用 DB、デフォルト: data/paper_trading.db）
  - PID_FILE_PATH（Execution の pid ファイルパス、デフォルト: data/execution.pid）
  - KILL_FLAG_PATH（Kill Switch の flag パス、デフォルト: data/kill.flag）
- ペーパートレード挙動:
  - PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）
- OpenAI:
  - OPENAI_API_KEY（AI モジュール実行時に必要）
- その他:
  - MONITOR_POLL_INTERVAL（監視ポーリング間隔 秒。run_monitoring で利用。デフォルト: 60）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1（.env の自動読み込みを無効化）

使い方（代表コマンド）
- .env の作成（対話式）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード: python -m kabusys.validate_config --strict

- 実行エンジン起動
  - 本番またはペーパーは KABUSYS_ENV によって切替
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - 実行中に停止させるにはプロジェクト data/stop_requested.flag を作成するとスレッドが検知して停止します（スクリプトは起動時にこのフラグを確認します）。

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変えたい場合:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Paper Trading 検証レポート生成（ツール）
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を明示する場合: python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

- AI スコアリング / レジーム判定（プログラム的呼び出し）
  - kabusys.ai.score_news(conn, target_date, api_key) など。APIキーが環境変数 OPENAI_API_KEY に設定されている必要があります。

ログ
- ロギングは kabusys.utils.logging_setup.setup_logging を通して統一されます。
- デフォルトログディレクトリ: logs/
- 各アプリ名（例: execution, monitoring）ごとに日次ローテートされたログファイルが生成されます（TimedRotatingFileHandler、30日保持）。

停止・Kill Switch の取り扱い
- 手動停止フラグ: data/stop_requested.flag を作成すると run_execution/run_monitoring のループが検知して終了します。
- 自動 Kill Switch: RiskMonitor 等が条件を満たすと KillSwitch が data/kill.flag を書き、Execution 側で早期停止やアラート送信が行われます。
- 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動で消す挙動になります（本番では 0 を推奨）。

ディレクトリ構成（主要ファイル・概観）
- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数自動読み込み／Settings クラスを提供
  - config_setup.py
    - .env 対話式ウィザード
  - validate_config.py
    - 起動前チェック CLI
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト
  - execution/
    - broker_factory.py, execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py
    - 実行用コンポーネント群（ブローカー抽象化・リスク制御・注文管理）
  - monitoring/
    - monitoring_db.py: SQLite テーブル作成・永続化 API
    - system_monitor.py, trade_monitor.py, risk_monitor.py, kill_switch.py, monitoring_engine.py, alert_manager.py
    - 監視・アラート・Kill Switch 周り
  - portfolio/
    - portfolio_builder.py, position_sizing.py, risk_adjustment.py
    - 候補選定、重み付け、ポジションサイズ計算、セクター上限、レジーム乗数
  - research/
    - factor_research.py, feature_exploration.py
    - ファクター計算・将来リターン・IC・統計サマリー
  - ai/
    - news_nlp.py, regime_detector.py
    - OpenAI を用いたニュースセンチメント/レジーム判定
  - data/（実行時生成想定）
    - data/monitoring.db（デフォルト）など
    - data/paper_trading.db（paper_trading 時に使用）
    - data/execution.pid, data/kill.flag, data/stop_requested.flag
  - logs/（実行時生成想定）
    - execution.log, monitoring.log 等（日次ローテーション）

注意事項 / 運用上のヒント
- .env は絶対にリポジトリにコミットしないでください（config_setup でも警告あり）。
- KABUSYS_ENV を live にした場合は本番挙動（実際の発注）になります。LINE 通知などの設定を必ず確認してください（validate_config の live ガード機能）。
- OpenAI を使う機能は API 負荷やコストが発生します。呼び出しはバッチ化／リトライ／レート制御の実装が組み込まれていますが運用時は注意してください。
- DuckDB / SQLite のパスは Settings で指定できます。複数環境（ローカル・ステージング・本番）でファイルパスが衝突しないよう注意してください。
- psutil によるプロセス優先度／CPU affinity 設定は OS 権限に依存します。アクセス権限不足の場合は警告ログを出してスキップします。

開発者向け
- 単体関数は比較的純粋関数（副作用少なめ）で実装されており、ユニットテストが書きやすく設計されています（例: portfolio モジュール、research モジュール）。
- OpenAI 呼び出し部分はラップされており、テスト時は該当関数をモックして外部依存を切り離せます（news_nlp._call_openai_api 等を patch）。

貢献
- Issue 提出・Pull Request を歓迎します。セキュリティに関する情報や秘密情報は公開しないでください。

以上。必要であれば README の英語版や CI/デプロイ手順、docker-compose などの追加セクションを生成します。どの情報をより詳しく補足しますか？