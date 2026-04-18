# KabuSys

日本株向け自動売買 / リサーチパイプラインのサンプル実装です。  
本リポジトリは注文実行エンジン、監視（Monitoring）、ファクター計算やポートフォリオ構築、AI を利用したニュースセンチメント等、複数のコンポーネントで構成されています。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 機能一覧
- 前提（環境）
- セットアップ手順
- 使い方（主要スクリプト・コマンド）
- 設定（環境変数 / .env）
- 運用上の注意
- ディレクトリ構成

---

プロジェクト概要
- KabuSys は日本株向けの自動売買システムの骨格実装です。
- 発注ロジックそのものは Strategy / Execution 層で分離されており、監視・リスク管理・ログ永続化・AI を利用したニュース評価・ファクター計算などの補助コンポーネントを備えます。
- 実働（live）・ペーパートレード（paper_trading）・開発（development）を想定した環境判定や、環境毎に DB を分離する仕組みを持ちます。

機能一覧
- ExecutionEngine 起動スクリプト（run_execution）
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、paper_trading 用 SQLite DB に記録して本番 DB と分離
  - スレッドでエンジンを起動して停止フラグ（data/stop_requested.flag）で安全終了
- Monitoring（run_monitoring / MonitoringEngine）
  - SystemMonitor, TradeMonitor, RiskMonitor を組み合わせたポーリング監視
  - SQLite に監視ログ（system_status, trade_logs, risk_logs, positions, dashboard）を永続化
  - Kill Switch（条件を満たした時に data/kill.flag を作成して Execution 停止を誘発）
- 環境設定ウィザード（config_setup）
  - 対話式に .env を生成・更新
- 設定検証 CLI（validate_config）
  - .env の必須項目や config/*.yaml の存在・パースをチェック（PyYAML があると中身も検査）
- Tools
  - paper_verification_report: Paper Trading の検証レポート生成（稼働率・注文成功率・レイテンシ等）
- Research / Portfolio / AI
  - DuckDB を使ったファクター計算（momentum, volatility, value 等）
  - ポートフォリオ構築・重み算出・単元株丸め・リスク調整（セクターキャップ・レジーム乗数）
  - AI モジュール: ニュースセンチメント（OpenAI を利用）、市場レジーム判定（MA＋マクロセンチメント合成）
- ユーティリティ
  - 統一的なログセットアップ（logs/<app>.log 日次ローテーション）
  - プロセス優先度 / CPU affinity 設定ユーティリティ（psutil ベース）
  - DB 初期化とマイグレーション小物（monitoring_db）

前提（環境）
- Python 3.10 以上（ソース内の型注釈に Python 3.10 の union 演算子 `|` を使用）
- 必要な Python パッケージ（一例）
  - duckdb
  - psutil
  - openai
  - PyYAML（config の YAML 検証を行う場合）
- 実行はローカルもしくはサーバ上で可能。OpenAI を利用する機能は有効な API キーが必要。

セットアップ手順
1. リポジトリをクローン / 展開
2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要なパッケージをインストール
   - 例: pip install duckdb psutil openai PyYAML
   - （プロジェクトで requirements.txt を用意している場合はそれを使用）
4. 初期設定
   - python -m kabusys.config_setup を実行して .env を生成（対話式）
   - もしくは .env を手動で作成（下記「設定」を参照）
5. 設定検証（任意）
   - python -m kabusys.validate_config
   - 警告も fail としたい場合: python -m kabusys.validate_config --strict
6. data ディレクトリ関連
   - デフォルト DB / pid / flag は data/ 以下に置かれることを想定。必要に応じて .env で上書きしてください。

使い方（主要スクリプト）
- 環境セットアップウィザード（対話式）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
- ExecutionEngine を起動（発注エンジン）
  - python -m kabusys.run_execution
  - KABUSYS_ENV 環境変数により動作モードを切替（development / paper_trading / live）
  - paper_trading の場合は settings.paper_sqlite_path（デフォルト data/paper_trading.db）を使用
- Monitoring を起動（監視ループ）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き（秒、デフォルト 60）
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to   YYYY-MM-DD
    - --db PATH （PAPER_TRADING_SQLITE_PATH 環境変数より優先して使用）
  - 例: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-10
- AI / Research の関数はライブラリ的に import して利用
  - 例: from kabusys.ai.news_nlp import score_news
  - OpenAI を呼ぶ処理は環境変数 OPENAI_API_KEY を必要とする（あるいは関数引数でキーを渡す）

設定（環境変数 / .env）
主な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV（development | paper_trading | live、デフォルト development）
- DUCKDB_PATH（デフォルト data/kabusys.duckdb）
- SQLITE_PATH（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト data/paper_trading.db）
- PAPER_FILL_MODE（paper_trading の MockBroker 動作、instant|partial|never|reject、デフォルト instant）
- LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト INFO）
- LOG_DIR（ログ出力先ディレクトリ、デフォルト logs/）
- OPENAI_API_KEY（AI 機能で必要）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（アラート通知に使用、任意）
- KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアする。開発用。0/1、デフォルト 0）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env の自動ロードを抑制
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔を秒で上書き）

.env の取り扱い
- .env は機密情報（API トークン等）を含むため、絶対に Git にコミットしないでください。
- config_setup.py で対話的に生成できます。
- validate_config で必須項目の有無を事前チェックできます。

運用上の注意
- process priority / cpu affinity を設定するために psutil を使用します。権限不足で設定に失敗する場合は警告が出ますが実行自体は継続します。
- Monitoring はデフォルトで本番用の sqlite_path を使用します（環境に依存しない設計）。ExecutionEngine は paper_trading 時に専用 DB を使います。
- 停止フラグ
  - run_execution / run_monitoring はプロジェクト内 data/stop_requested.flag を検出すると安全に停止します（起動時・ループ内でチェック）。
  - KillSwitch は条件に応じて data/kill.flag を作成し、ExecutionEngine に停止を促します。kill.flag のクリアは手動で削除するか、KILL_FLAG_CLEAR_ON_START を使う（開発のみ推奨）。
- OpenAI API 呼び出し
  - rate limit・一時エラーを考慮して指数バックオフでリトライする実装が入っていますが、API キーの適切な管理とコスト管理を行ってください。
- DuckDB / SQLite
  - データストアへの書き込みはそれぞれのモジュールでトランザクション制御（BEGIN/COMMIT/ROLLBACK）を使っています。DB のバックアップ・保守を行ってください。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py            — 環境変数 / Settings
  - config_setup.py      — .env 対話生成ウィザード
  - validate_config.py   — 設定検証 CLI
  - run_execution.py     — ExecutionEngine 起動スクリプト
  - run_monitoring.py    — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py   — ログセットアップ（Stream + 日次ローテーション）
    - process_priority.py— プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py (省略コード参照)
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py (省略コード参照)
  - execution/
    - execution_engine.py (実行エンジン本体; 依存を注入する設計)
    - order_manager.py
    - order_repository.py
    - broker_factory.py
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

（コード全体は src/kabusys 以下に多数のモジュールがあり、上記は主要コンポーネントの抜粋です）

補足（よくあるコマンド例）
- .env を作る（対話式）
  - python -m kabusys.config_setup
- 設定チェック
  - python -m kabusys.validate_config
- Execution 起動（paper_trading 等は .env で設定）
  - python -m kabusys.run_execution
- Monitoring 起動（MONITOR_POLL_INTERVAL を変更）
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Paper Trading レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

ライセンス・貢献
- 本リポジトリのライセンス情報はプロジェクトルートの LICENSE を参照してください（存在しない場合は作成してください）。
- コード改善の際は .env を含めないよう注意し、機密情報は提供しないでください。

---

以上が README の概要です。README に追加したい具体的な内容（例: README 内に .env.example のサンプル、実行ログ例、CI 設定、Dockerfile など）があれば教えてください。必要に応じて追記・整形します。