# KabuSys

日本株向け自動売買システムのコアライブラリ群（サンプル実装）。  
このリポジトリは取引エンジン、監視、ポートフォリオ構築、リサーチ、AI（ニュース NLP / レジーム判定）などのコンポーネントを含みます。

以下はこのコードベースに基づく README（日本語）です。

---

目次
- プロジェクト概要
- 主な機能一覧
- 必要条件 / 依存パッケージ
- セットアップ手順
- 使い方（主要コマンド例）
- 環境変数一覧（主要なもの）
- 停止・Kill フラグの扱い
- ディレクトリ構成（主要ファイルの説明）

---

プロジェクト概要
- KabuSys は日本株自動売買のためのコンポーネント群のサンプル実装です。
- 機能ごとにモジュールが分離されており、監視・発注・リスク管理・ポートフォリオ構築・因子計算・ニュース NLP 等を含みます。
- SQLite（監視/発注用）および DuckDB（分析用）を利用します。OpenAI を使った NLP 機能も一部実装されています（APIキーが必要）。

主な機能一覧
- ExecutionEngine 起動（run_execution.py）
  - 実際のブローカークライアント（またはペーパートレーディング時は Mock）を使ってセッションを実行
  - リスク管理、オーダー管理、リコンシリエーション等を統合
  - paper_trading 環境では専用 SQLite（data/paper_trading.db）に記録して本番 DB と分離
- Monitoring（run_monitoring.py）
  - SystemMonitor / TradeMonitor / RiskMonitor を定期ポーリングしてログ保存・アラート判定・Kill Switch 評価
  - 監視メトリクスを SQLite（data/monitoring.db）に保存
- 設定ウィザード（config_setup.py）
  - 対話式に .env を作成・更新する補助ツール
- 設定検証 CLI（validate_config.py）
  - .env および config/*.yaml の存在や形式を起動前にチェック
- Paper Trading 検証レポート（tools/paper_verification_report.py）
  - ペーパートレード用 DB を解析して稼働率・注文成功率・レイテンシ等のレポートを生成
- ポートフォリオ構築（kabusys.portfolio）
  - 候補選定、重み算出、ポジションサイズ計算、セクター制限、レジーム乗数などの純粋関数実装
- リサーチ（kabusys.research）
  - ファクター計算（モメンタム・ボラティリティ・バリュー）、forward returns、IC、統計サマリー等
- AI（kabusys.ai）
  - ニュースのセンチメントスコアリング（OpenAI を利用）
  - 市場レジーム判定（ETF の MA とマクロニュースのセンチメントを合成）
- 汎用ユーティリティ
  - logging_setup（統一ログ設定）
  - process_priority（プロセス優先度 / CPU affinity 設定）
  - 環境変数の自動ロードおよび Settings クラス（kabusys.config）

必要条件 / 依存パッケージ
- Python 3.10+（型記法（|）を利用しているため）
- 推奨ライブラリ（少なくとも以下は必要/推奨）
  - duckdb
  - psutil
  - openai （AI 機能を使う場合）
  - PyYAML（validate_config で YAML 検証を行う場合、任意）
- 例（開発環境で最低限インストールする場合）:
  pip install duckdb psutil openai pyyaml

セットアップ手順（ローカル開発向け）
1. リポジトリをクローンして作業ディレクトリへ移動
2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install duckdb psutil openai pyyaml
   - （requirements.txt がある場合は pip install -r requirements.txt）
4. .env の作成
   - python -m kabusys.config_setup
     - 対話式で J-Quants トークン、kabu API パスワード等を設定します。
   - 自動ロード: kabusys.config はプロジェクトルートで .env / .env.local を自動で読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
5. 設定検証（推奨）
   - python -m kabusys.validate_config
   - --strict をつけると警告も失敗扱いになります
6. データディレクトリやログディレクトリの作成（自動作成される場合あり）
   - デフォルト DB / ログパス:
     - data/monitoring.db（SQLite）
     - data/paper_trading.db（paper_trading 用）
     - data/kabusys.duckdb（DuckDB）
     - logs/（ログ）

使い方（主要コマンド例）
- 設定ウィザード
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード: python -m kabusys.validate_config --strict
- 実行エンジン（ExecutionEngine）起動
  - python -m kabusys.run_execution
  - 注意: 起動前に kill.flag の自動クリア挙動（KILL_FLAG_CLEAR_ON_START）や stop フラグを確認してください
  - 実行時は Settings によって KABUSYS_ENV が "paper_trading" の場合はペーパーブローカー（Mock）を使用し、専用 DB に記録します
- 監視プロセス起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）
- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定: --from YYYY-MM-DD --to YYYY-MM-DD
  - DB 指定: --db PATH もしくは環境変数 PAPER_TRADING_SQLITE_PATH
- AI 機能（ニューススコア・レジーム判定）はモジュール関数として呼び出し可能
  - 例: kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime
  - OpenAI API キー（OPENAI_API_KEY）を環境変数または引数で指定する必要あり

主要な環境変数（一覧・説明）
- 必須（実際の運用で必要）
  - JQUANTS_REFRESH_TOKEN: J-Quants API 用リフレッシュトークン
  - KABU_API_PASSWORD: kabuステーション API パスワード
- 実行環境指定
  - KABUSYS_ENV: development | paper_trading | live（デフォルト development）
    - paper_trading: 発注はモック、記録は data/paper_trading.db
    - live: 実取引
- データベース / パス
  - DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH: SQLite 監視 DB（デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
  - PID_FILE_PATH: ExecutionEngine 用 pid ファイルパス（デフォルト data/execution.pid）
  - KILL_FLAG_PATH: Kill Switch 用フラグファイル（デフォルト data/kill.flag）
- ログ / 動作
  - LOG_LEVEL: DEBUG/INFO/...（デフォルト INFO）
  - LOG_DIR: ログ出力ディレクトリ（デフォルト logs/）
  - KILL_FLAG_CLEAR_ON_START: 1 にすると起動時に kill.flag を自動クリア（本番では 0 推奨）
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）
- OpenAI（AI 機能利用時）
  - OPENAI_API_KEY: OpenAI API キー
- PAPER_FILL_MODE（paper_trading の注文振る舞い）
  - instant | partial | never | reject（デフォルト instant）

停止 / Kill フラグの扱い
- run_execution / run_monitoring はフラグファイルをチェックして安全に停止できる仕組みを持ちます。
  - stop_requested.flag: 両スクリプトともこのフラグファイルの存在をチェックして終了処理を行います（スクリプト内でのパスに依存）。
  - kill.flag: KillSwitch が条件を満たすとこのファイルを書き込み、ExecutionEngine 停止のシグナルとして機能します（Settings.kill_flag_path で指定可能）。
- KillSwitch はドローダウンやポジション上限等の重大なリスクを検出したときに kill.flag を書き込みます。既に存在する場合は再書込しません（冪等）。

データベース初期化
- run_* スクリプトは起動時に必要なテーブルを作成する init_monitoring_db を呼びます（冪等）。
- monitoring_db.py にて schema 作成・マイグレーション処理（列追加）を行います。

ディレクトリ構成（主要ファイルと簡単な説明）
- src/kabusys/
  - __init__.py: バージョンと公開 API
  - config.py: Settings クラス（環境変数読み込み・検証、自動 .env ロード）
  - config_setup.py: 対話式 .env 作成ウィザード
  - validate_config.py: 起動前検証ツール
  - run_execution.py: ExecutionEngine 起動スクリプト（PID / stop flag 管理、paper_trading 分離）
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL 対応）
  - tools/
    - paper_verification_report.py: ペーパートレード検証レポート生成
  - ai/
    - news_nlp.py: ニュース記事の LLM ベースセンチメントスコア取得ロジック
    - regime_detector.py: 市場レジーム判定ロジック（MA + マクロセンチメント）
  - monitoring/
    - monitoring_db.py: SQLite ベースの監視ログ永続化層（スキーマ作成・読み書き）
    - system_monitor.py: CPU/メモリ/DISK・プロセス・データ鮮度監視
    - risk_monitor.py: ドローダウン・ポジション上限監視
    - trade_monitor.py: （コード参照）注文滞留・約定異常等の監視（ファイル内に定義）
    - kill_switch.py: Kill Switch 書き込みロジック
    - monitoring_engine.py: 各 Monitor を束ねるポーリングエンジン
    - alert_manager.py: （実装により通知管理）
  - execution/
    - execution_engine.py: ExecutionEngine 実装（セッション実行ロジック）
    - broker_factory.py: ブローカークライアント生成
    - order_manager.py / order_repository.py / reconciler.py / risk_manager.py: 発注関連コンポーネント
  - portfolio/
    - portfolio_builder.py: 候補選定・重み計算
    - position_sizing.py: 株数決定・単元丸め・資金配分
    - risk_adjustment.py: セクター上限・レジーム乗数
  - research/
    - factor_research.py: モメンタム・ボラティリティ・バリュー等の因子計算
    - feature_exploration.py: 将来リターン・IC・統計サマリー
  - utils/
    - logging_setup.py: 共通ログ設定
    - process_priority.py: プロセス優先度 / CPU affinity 設定
- data/: 実行時に使用する DB/フラグファイル等（デフォルト）
  - data/monitoring.db
  - data/paper_trading.db
  - data/kabusys.duckdb
  - data/execution.pid
  - data/stop_requested.flag
  - data/kill.flag
- logs/: ログファイルを日次ローテーションで保存（例: logs/execution.log, logs/monitoring.log）

開発上の注意点 / 補足
- 本実装はサンプル設計に沿った実装が多く含まれます。特に live 環境での起動時は設定（API キー・パスワード・Kill Switch 設定）を慎重に確認してください。
- デフォルトで .env はプロジェクトルートの .env / .env.local を自動読み込みします（OS 環境変数を上書きしない / .env.local は override=True で上書き可能）。自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI や外部 API を利用する機能は API のレート制限やエラーを考慮したリトライ実装を含みますが、本番で利用する場合は API 使用量・コストに注意してください。
- ログディレクトリや DB 保存先に書き込み権限が必要です。起動時に指定のディレクトリが作れない場合、ファイル出力は抑制されコンソールのみのログになります。

---

問題や追加ドキュメント（例: API 詳細、設定例、運用手順など）が必要であれば、どの部分を深掘りしたいか教えてください。README の英語版やサンプル .env.example の自動生成テンプレートも作成できます。