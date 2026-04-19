# KabuSys

日本株向け自動売買システムのコードベース（軽量なランタイム／監視／リサーチ／ペーパートレード支援ツール群）。

このリポジトリは、発注エンジン、監視（Monitoring）、ポートフォリオ構築、リサーチ、AI を用いたニュース解析などのコンポーネントで構成されています。各モジュールは可能な限り副作用を抑え、設定は環境変数 / .env で管理します。

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（主要コマンド例）
- 環境変数（主要項目）
- ディレクトリ構成（主要ファイルの説明）
- 運用上の注意点

---

プロジェクト概要
- KabuSys は日本株自動売買のための小規模なフレームワークです。発注ロジック（ExecutionEngine）、監視（MonitoringEngine）、ポートフォリオ構築、リサーチ（DuckDB を使ったファクター計算）、AI によるニュースセンチメント評価などの機能を含みます。
- 設定は環境変数または .env（プロジェクトルート）から読み込みます。`.env` を生成・更新する対話式ウィザードと、設定検証ツールを提供します。

機能一覧
- Execution
  - ExecutionEngine を起動して発注セッションを実行（KABUSYS_ENV により paper_trading と live を切替）
  - BrokerClientFactory によるブローカークライアント切替（paper_trading では MockBrokerClient を使用）
  - risk_manager / order_manager / reconciler 等の統合
- Monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor を定期的に実行する監視ループ
  - kill.flag による外部停止（Kill Switch）
  - 監視ログを SQLite（monitoring.db）へ永続化
- Portfolio construction
  - 候補選定、等金額／スコア加重、リスクベースのポジションサイジング、セクターキャップ、レジーム乗数
- Research
  - DuckDB を用いたファクター計算（モメンタム、ボラティリティ、バリューなど）
  - 特徴量探索、将来リターン計算、IC 計算、統計サマリ
- AI（OpenAI）
  - ニュース記事を LLM（gpt-4o-mini 想定）でセンチメント評価し ai_scores テーブルへ保存
  - 市場レジーム判定モジュール（ETF MA + マクロニュースセンチメントの合成）
- Tools
  - Paper Trading 検証レポート生成（過去期間の uptime / fill rate / レイテンシなどを算出）
- 設定管理
  - 対話式 .env ウィザード（config_setup）
  - 設定検証 CLI（validate_config）

セットアップ手順（ローカル実行向け）
1. Python 環境を用意（推奨: 3.10+）
2. 依存ライブラリをインストール
   - required（主なもの）: duckdb, psutil, openai（AI 機能を使う場合）, PyYAML（config ファイル検証を行う場合）
   - 例:
     - pip install duckdb psutil openai pyyaml
3. プロジェクトルートに `.env` を作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
   - もしくは .env.example 等を参考に環境変数を設定
4. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります
5. 必要に応じてデータディレクトリを作成（ログ/DB）
   - デフォルト：data/（SQLite）, logs/（ログ）, data/kabusys.duckdb（DuckDB）

使い方（主要コマンド）
- ExecutionEngine を起動する
  - python -m kabusys.run_execution
  - 処理概要:
    - Settings を読み、psutil でプロセス優先度を high に設定
    - DB 接続: KABUSYS_ENV=paper_trading なら paper_sqlite_path（デフォルト data/paper_trading.db）を使用、それ以外は sqlite_path（data/monitoring.db）
    - BrokerClientFactory でブローカークライアントを作成しエンジンを起動
    - 停止フラグ（data/stop_requested.flag）があれば起動をスキップまたは停止
- Monitoring を起動する（常時ポーリング）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を変更可能（デフォルト 60）
  - 監視は本番 sqlite_path（data/monitoring.db）を参照（KABUSYS_ENV にかかわらず本番 DB を使う設計）
- 設定ウィザード
  - python -m kabusys.config_setup
- 設定検証 CLI
  - python -m kabusys.validate_config
  - 主要な環境変数や config/*.yaml の存在／簡易パースをチェック
- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - または環境変数 PAPER_TRADING_SQLITE_PATH で DB を指定可能

主要な環境変数（デフォルトを含む）
- 必須
  - JQUANTS_REFRESH_TOKEN … J-Quants API のリフレッシュトークン（必須）
  - KABU_API_PASSWORD … kabuステーション API パスワード（必須）
- 実行環境
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- データベース
  - DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
  - SQLITE_PATH: data/monitoring.db（監視 DB、デフォルト）
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用 DB）
- ログ / PID / Kill
  - LOG_LEVEL: INFO（デフォルト）
  - LOG_DIR: logs/（デフォルト）
  - PID_FILE_PATH: data/execution.pid（デフォルト）
  - KILL_FLAG_PATH: data/kill.flag（Kill Switch 用）
  - KILL_FLAG_CLEAR_ON_START: 0 / 1（起動時に kill.flag を自動クリアするか）
- Monitoring
  - MONITOR_POLL_INTERVAL: ポーリング間隔（秒、デフォルト 60）
  - CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT（監視閾値）
- Paper Trading
  - PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）
- OpenAI（AI 機能を利用する場合）
  - OPENAI_API_KEY: OpenAI API キー（必須。ai.news_nlp / ai.regime_detector が必要とする）

自動 .env 読み込みの挙動
- 起動時にプロジェクトルート（.git または pyproject.toml を基準）を探索して .env と .env.local を自動読み込みします。
- OS 環境変数が優先され、.env.local は .env より優先して上書きします。
- 自動読み込みを無効化するには: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

ログ
- ログは setup_logging によって stdout と日次ローテートされるファイル（logs/<app_name>.log）に出力されます。
- ローテーションは TimedRotatingFileHandler（デフォルト 30 日保持）。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py — パッケージ定義、__version__（0.1.0）
  - config.py — 環境変数/設定読み込み・Settings クラス
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート出力
  - ai/
    - news_nlp.py — ニュース NLP（OpenAI で銘柄別センチメントを算出）
    - regime_detector.py — 市場レジーム判定（MA + マクロセンチメント）
  - monitoring/
    - monitoring_db.py — SQLite 監視 DB のスキーマ初期化・永続化ラッパー
    - system_monitor.py — システム状態とデータ鮮度のチェック
    - trade_monitor.py — （存在）取引ログ監視（コードベース参照）
    - risk_monitor.py — ドローダウン／ポジション上限監視
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
    - kill_switch.py — kill.flag を書き込む KillSwitch 実装
    - alert_manager.py — （存在）通知管理（LINE など）
  - execution/（発注関連）
    - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py（実装参照）
  - portfolio/
    - portfolio_builder.py — 候補選定、重み計算
    - position_sizing.py — 株数計算・キャップ・スケールダウン
    - risk_adjustment.py — セクター制限・レジーム乗数
  - research/
    - factor_research.py — ファクター計算（DuckDB）
    - feature_exploration.py — IC / 統計サマリ
  - data/（実行時に生成されるサブディレクトリを想定）
    - デフォルト DB やフラグファイル（例: data/monitoring.db, data/paper_trading.db, data/kill.flag, data/stop_requested.flag, data/execution.pid）
  - utils/
    - logging_setup.py — ログ初期化ユーティリティ
    - process_priority.py — psutil を使った優先度設定 / CPU affinity

運用上の注意点
- 必須環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）は必ず設定してください。validate_config で事前チェックできます。
- KABUSYS_ENV を live にすると本番モードになります。LINE 通知や Kill Switch 等の設定を本番用に確認してください（validate_config の live ガードが警告を出します）。
- run_monitoring は MONITOR_POLL_INTERVAL（秒）でポーリングします。0 以下や不正な値はデフォルト 60 秒にフォールバックします。
- run_monitoring は監視用 DB に常に本番 sqlite_path を使う設計です（環境にかかわらず監視 DB は共通で永続化されます）。
- run_execution は paper_trading 環境であれば paper_trading 用の SQLite を使用して本番 DB と分離します。
- Kill Switch（data/kill.flag）は存在すると ExecutionEngine を停止・起動スキップするため、特に本番運用時は扱いに注意してください。KILL_FLAG_CLEAR_ON_START を 1 にすると起動時に自動クリアしますが、本番では 0 推奨です。
- AI 機能を利用するには OPENAI_API_KEY が必要です。API 呼び出し失敗時はフェイルセーフでスコアを 0 や処理スキップする実装ですが、API の利用制限やコストに注意してください。
- ログディレクトリ作成に失敗した場合はコンソール出力のみで継続します（エラーにならない設計）。

付録：よく使うコマンド例
- .env の対話式作成:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- 実行エンジン起動:
  - python -m kabusys.run_execution
- 監視ループ起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - または python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

以上が本リポジトリの README です。実行時の挙動や設計方針の詳細は各モジュールの docstring を参照してください。必要ならば導入手順（Dockerfile や systemd ユニット例）、運用プレイブック、さらに詳しい開発者向けドキュメントも作成できます。必要であれば教えてください。