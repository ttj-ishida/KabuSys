README
=====

概要
----
KabuSys は日本株の自動売買システム（リサーチ・ポートフォリオ構築・発注・監視・ペーパートレード対応）を目的とした Python コードベースです。本リポジトリは次の主要機能を持ちます。

- 市場データを用いたファクター計算・特徴量分析（research）
- ポートフォリオ選定・ウェイト算出・株数決定（portfolio）
- 発注エンジン（ExecutionEngine）と注文管理（実環境 / ペーパートレードの分離）
- 監視機構（System / Trade / Risk モニタ）と Kill Switch（自動停止）
- ニュース NLP（OpenAI を利用したセンチメント評価）および市場レジーム判定
- 各種ユーティリティ（ログ設定、プロセス優先度設定、設定ファイルウィザード、設定検証）
- ペーパートレード検証レポート生成ツール

特徴
----
主な機能一覧（抜粋）：
- Execution:
  - 本番 / ペーパートレードを環境変数 KABUSYS_ENV に応じて切り替え
  - ペーパートレードは MockBrokerClient を使い DB を分離（data/paper_trading.db）
- Monitoring:
  - SystemMonitor, TradeMonitor, RiskMonitor を組み合わせた Polling 監視
  - kill.flag による安全停止、stop_requested.flag によるループ停止
- Research:
  - モメンタム / ボラティリティ / バリュー等のファクター計算（DuckDB を利用）
  - 将来リターン、IC 計算、ファクター統計サマリ
- AI:
  - OpenAI（gpt-4o-mini 等）でニュースをスコア化（ai_scores テーブルへ書き込み）
  - 市場レジーム判定（MA200 とマクロニュースの LLM センチメントを合成）
- Portfolio:
  - 候補選定、等金額・スコア加重、リスクベースサイズ決定、セクター制限、レジーム乗数
- ツール:
  - config_setup.py: .env を対話式に作成
  - validate_config.py: 起動前の設定検証
  - tools/paper_verification_report.py: ペーパー取引の検証レポート生成

動作要件
----
- Python 3.10+
- 必要な外部パッケージ（主なもの）:
  - duckdb
  - psutil
  - openai
  - （PyYAML は config 検証で任意）
- SQLite（Python 標準ライブラリで利用）
- ネットワーク接続（OpenAI API 利用時）

セットアップ手順（クイックスタート）
----
1. リポジトリをクローンして移動
   - git clone <repo-url>
   - cd <repo>

2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージのインストール（例）
   - pip install duckdb psutil openai
   - （テスト・分析に PyYAML や他パッケージが必要な場合は別途インストール）

4. .env の作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
   - ウィザードは J-Quants トークンや kabu API パスワード、KABUSYS_ENV 等を順次入力します。
   - 生成された .env は絶対に Git にコミットしないでください。

5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 警告も fail 扱いにする場合:
     - python -m kabusys.validate_config --strict

6. DB 初期化
   - 実行スクリプト（run_monitoring / run_execution）が起動時に必要テーブルを冪等に作成します。
   - DuckDB / SQLite のデフォルトパス:
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（ペーパートレード時）

基本的な使い方
----
実行スクリプト
- 監視ループを起動（ポーリング）
  - MONITOR_POLL_INTERVAL 環境変数で秒数を上書き可（デフォルト: 60）
  - python -m kabusys.run_monitoring

- ExecutionEngine を起動
  - KABUSYS_ENV=paper_trading を設定すると MockBrokerClient を利用し paper DB に記録
  - python -m kabusys.run_execution

停止 / Kill
- graceful stop: プロジェクトルート/data/stop_requested.flag を作成すると run_* スクリプトは次のループで停止します（両スクリプトがチェック）。
- Kill Switch（自動停止）: 監視コンポーネントが条件を満たすと data/kill.flag を書き込みます。ExecutionEngine は kill.flag を検出して停止します。
- PID ファイル: data/execution.pid（実行用 PID 管理に使用）

ツール
- ペーパートレード検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB は環境変数 PAPER_TRADING_SQLITE_PATH か data/paper_trading.db

AI (OpenAI) 機能
- ニュース NLP や regime_detector は OPENAI_API_KEY 環境変数を必要とします。
- API キー未設定時は機能が例外を投げますので .env に設定するか引数で渡してください。

主要な環境変数（抜粋）
----
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN（任意、アラート用）
- LINE_USER_ID（任意、アラート用）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL（デフォルト: INFO）
- KILL_FLAG_CLEAR_ON_START（0/1、デフォルト 0。本番では 0 推奨）
- OPENAI_API_KEY（ai モジュール利用時に必要）
- MONITOR_POLL_INTERVAL（監視ループのポーリング秒数、デフォルト 60）

ファイル・フラグ（主なもの）
----
- data/stop_requested.flag — run_* スクリプトがポーリングで検出して停止するためのフラグ（手動作成）
- data/kill.flag — KillSwitch により自動書込みされる停止フラグ（ExecutionEngine 停止トリガ）
- data/execution.pid — ExecutionEngine の PID ファイル
- logs/<app>.log — ログ出力（setup_logging により生成、デフォルト logs ディレクトリ）

ディレクトリ構成
----
（src/kabusys 以下の主要ファイル群を示します）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定読み込みロジック
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前の設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - data/ (想定ディレクトリ: 生成・格納場所)
    - monitoring.db (デフォルト)
    - paper_trading.db (ペーパートレード用)
    - kabusys.duckdb (DuckDB)
    - execution.pid, kill.flag, stop_requested.flag
  - utils/
    - logging_setup.py        — ロギング設定ユーティリティ
    - process_priority.py     — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py        — SQLite 永続化層
    - system_monitor.py
    - risk_monitor.py
    - trade_monitor.py        — （trade_monitor コードは省略列挙、存在します）
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py        — （アラート送信ロジック）
  - execution/
    - execution_engine.py     — ExecutionEngine 本体（発注ループ等）
    - broker_factory.py       — BrokerClient の生成（実/モック切替）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
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

設計上の注意点 / 運用メモ
----
- KABUSYS_ENV により本番（live）・ペーパートレード（paper_trading）・開発（development）を切替。ペーパートレードは発注 DB を分離。
- run_monitoring は KABUSYS_ENV に関わらず本番用 sqlite_path を使用して監視情報を記録します（監視は常に本番 DB を見る設計）。
- .env は自動ロードされます（プロジェクトルートの .env / .env.local）。必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可。
- OpenAI を用いる AI モジュールは外部 API に依存するため、API エラーはフェイルセーフ（多くの場合フォールバック値で継続）を意識して運用してください。
- 本番環境（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START を 0 にすることを推奨します。clear=1 は Kill Switch を自動クリアしてしまい危険です。
- ログは setup_logging で logs/<app>.log に日次ローテーションで保存されます。ログディレクトリ作成に失敗した場合はコンソールのみにフォールバックします。

例: よく使うコマンド
----
- .env 作成（ウィザード）
  - python -m kabusys.config_setup

- 設定チェック
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 監視をデフォルト間隔で起動
  - python -m kabusys.run_monitoring

- 発注エンジンを起動
  - python -m kabusys.run_execution

- ペーパートレード検証レポート出力
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

最後に
----
この README はコードベースの主要コンポーネントと基本的な運用手順をまとめたものです。詳細な設計・アルゴリズム（PortfolioConstruction.md や StrategyModel.md など）や実装ドキュメントが別にある場合はそちらも参照してください。問題や改善提案があればリポジトリ内の issue / PR をご利用ください。