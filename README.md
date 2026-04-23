KabuSys — 日本株自動売買システム
================================

このリポジトリは、J‑Quants／kabuステーションを利用した日本株の自動売買システム（プロトタイプ実装）です。  
主に以下の機能を含みます: データ処理・ファクター計算、ポートフォリオ構築、発注実行エンジン、監視／アラート、ペーパートレード検証、LLM を用いたニュースセンチメント解析 等。

要点
- Python パッケージ名: kabusys
- 起動用スクリプト（モジュール実行）:
  - 実行エンジン: python -m kabusys.run_execution
  - 監視ループ:     python -m kabusys.run_monitoring
  - 環境設定ウィザード: python -m kabusys.config_setup
  - 設定検証:      python -m kabusys.validate_config
  - ペーパートレード検証レポート: python -m kabusys.tools.paper_verification_report

機能一覧
- ExecutionEngine
  - 実際のブローカークライアント（本番）または MockBrokerClient（KABUSYS_ENV=paper_trading）を用いた発注処理
  - OrderManager / RiskManager / Reconciler の組み合わせによる発注制御・整合性維持
  - paper_trading モードでは本番 DB と分離して data/paper_trading.db に記録
- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク、プロセス稼働、データ鮮度を監視して monitoring DB（SQLite）に記録
  - TradeMonitor / RiskMonitor / KillSwitch / AlertManager によるリスク監視・Kill Flag 発動
  - run_monitoring 起動スクリプトでポーリングループ実行（MONITOR_POLL_INTERVAL 環境変数で間隔指定可能）
- Data & Research
  - DuckDB を使ったファクター計算（momentum, volatility, value 等）
  - 特徴量探索・IC 計算などの研究用ユーティリティ
- Portfolio construction
  - 銘柄選定、等金額・スコア加重配分、リスク調整、ポジションサイズ計算（単元株丸め含む）
- AI（LLM）機能
  - news_nlp: raw_news を OpenAI API（gpt-4o-mini 想定）でスコアリングして ai_scores 書き込み
  - regime_detector: ma200 とマクロニュースの LLM スコアを合わせて市場レジーム判定
- Tools
  - paper_verification_report: ペーパートレード DB を解析して稼働率・注文成功率・レイテンシ等の検証レポートを出力

セットアップ手順（開発用 / ローカル）
---------------------------------

1. Python バージョン
   - Python 3.10 以上を推奨（型アノテーションに | が使われています）。

2. 依存パッケージをインストール
   - requirements.txt がある場合: pip install -r requirements.txt
   - 主要なライブラリ例（明示的に必要）:
     - duckdb
     - psutil
     - openai
     - PyYAML（config 検証用。なくても動作する箇所あり）
   例:
     pip install duckdb psutil openai pyyaml

3. リポジトリルートに移動し、data/logs 等のディレクトリを作成（権限確認）
   - 通常はスクリプトが自動で作成しますが、必要に応じて手動作成:
     mkdir -p data logs

4. .env の作成
   - 対話式ウィザード: python -m kabusys.config_setup
   - もしくは .env を手動で作成（以下の主要キーを設定してください）:

主要な環境変数（抜粋）
- KABUSYS_ENV: 実行環境（development | paper_trading | live）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabuステーションのベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector 使用時）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 DB（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- LOG_DIR: ログ保存先（デフォルト: logs）
- PAPER_FILL_MODE: paper_trading 時の約定モード（instant|partial|never|reject）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1、本番は 0 推奨）

5. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いして exit(1)

使い方（起動例）
----------------

- 実行エンジン（発注実行）
  - 本番／ペーパー共通起動:
    python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH に書き込む（本番 DB と分離）
    - 起動時に data/stop_requested.flag が存在すると起動せず終了する
    - 実行中は data/stop_requested.flag をチェックして停止する

- 監視ループ
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書きできる（デフォルト 60）
    例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視は常に本番 sqlite_path を参照（環境にかかわらず監視 DB は production path を使います）

- 設定ウィザード / 検証
  - .env 作成: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config [--strict]

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- ログ
  - デフォルトで stdout とファイル（logs/<app_name>.log）へ出力します。
  - ログ設定は kabusys.utils.logging_setup.setup_logging() で一元管理されています。

監視・停止フラグについて
- Kill Switch / stop flag:
  - KillSwitch は条件を満たした場合に data/kill.flag を書き込み（理由がテキストで格納）ExecutionEngine に停止シグナルを送ります。
  - run_execution/run_monitoring は stop_requested.flag（data/stop_requested.flag）を監視することで外部からの終了要求に応答します。
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動的に削除します（本番環境では推奨しません）。

開発・テスト向けポイント
- paper_trading モード: 実際の発注を行わないペーパートレード用の分離された DB を使用し、動作検証が可能です。
- LLM 関連は OpenAI API キーが必要。テスト時は該当関数（_call_openai_api 等）をモックしてテストしてください。
- DuckDB を利用して高速にファクター計算や集計ができます。prices_daily / raw_financials 等のテーブルを前提にしています。

ディレクトリ構成（主なファイル）
--------------------------------
（src/kabusys 以下を抜粋）

- __init__.py
- config.py                — 環境変数 / Settings クラス（自動 .env 読み込み含む）
- config_setup.py          — .env 作成ウィザード（CLI）
- validate_config.py       — 設定検証 CLI
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — SystemMonitor ポーリング起動スクリプト

- execution/
  - execution_engine.py
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - risk_manager.py
  - broker_factory.py

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

- data/ (ランタイムで作成)
  - monitoring.db (デフォルト)
  - paper_trading.db (paper_trading モード)
  - kill.flag / stop_requested.flag / execution.pid

- tools/
  - paper_verification_report.py

ユーティリティ
- utils/logging_setup.py   — ログの一括設定（コンソール + 日次ローテートファイル）
- utils/process_priority.py — プロセス優先度・CPU affinity 設定ユーティリティ

運用上の注意
- 本番環境（KABUSYS_ENV=live）では .env の情報を慎重に管理し、LINE のアラート設定等を必ず確認してください。
- KILL_FLAG_CLEAR_ON_START の自動クリアは本番で危険です（誤って Kill Switch を無効化する可能性）。
- LLM（OpenAI）利用は API コストとレート制限に注意してください。news_nlp/regime_detector はリトライとフェイルセーフを備えていますが、設定と運用ルールを決めてください。
- DB ファイル（DuckDB / SQLite）は定期的なバックアップを推奨します。

貢献 / 拡張案
- 銘柄別の lot_size を外部マスタで管理して position_sizing を拡張
- strategy_config.yaml に基づく動的な戦略パラメータ読み込み
- テスト用のモック実装（BrokerClient のインタフェースを用いたユニットテスト）拡充
- CI で validate_config を実行して設定不備を検出

ライセンス / バージョン
- パッケージバージョンは kabusys.__version__ = "0.1.0"
- ライセンス情報はリポジトリのトップレベルに記載してください（本リポジトリには含まれていないため注意）。

以上がこのコードベースの概要と利用手順のまとめです。README に追加したい実行例や環境変数のテンプレート（.env.example）を生成するなどが必要であればお手伝いします。