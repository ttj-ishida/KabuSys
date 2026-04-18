# KabuSys

日本株向け自動売買システムの内部ライブラリ群および起動スクリプト群。  
このリポジトリは、取引実行エンジン、監視（Monitoring）、ポートフォリオ構築、リサーチ（ファクター計算）、
AIベースのニュース・レジーム判定、およびユーティリティ群を含みます。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（主要コマンド例）
- 環境変数（主な設定）
- ファイル / ディレクトリ構成

---

プロジェクト概要
- KabuSys は日本株の自動売買システム向けに設計されたコードベースです。
- 主要コンポーネント：
  - ExecutionEngine: 注文の作成・管理・実行（kabuステーション等のブローカークライアント経由）
  - Monitoring: システム状態・注文状況・リスク監視、必要に応じて Kill Switch を発動
  - Portfolio: 候補銘柄選定、重み付け、ポジションサイズ計算、セクター制約等
  - Research: DuckDB を用いたファクター（モメンタム・バリュー・ボラティリティ）や特徴量解析
  - AI モジュール: ニュースの NLP スコアリング（OpenAI を利用）、市場レジーム判定
  - Tools: ペーパートレード検証レポート生成等のユーティリティ

---

機能一覧
- 環境設定ウィザード（.env 生成支援）
  - python -m kabusys.config_setup
- 設定検証 CLI
  - python -m kabusys.validate_config
- Execution 起動スクリプト（本番 / ペーパートレード判別）
  - python -m kabusys.run_execution
  - Paper trading モードでは専用の SQLite（data/paper_trading.db）を使用して完全分離
- Monitoring ポーリング（SystemMonitor のループ）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL でポーリング間隔上書き可能（デフォルト 60 秒）
- AI:
  - ニュースセンチメントを算出して ai_scores テーブルへ書き込む（OpenAI）
    - kabusys.ai.score_news（プログラムから呼び出し可能）
  - 市場レジーム判定（ma200 + マクロセンチメント）
    - kabusys.ai.regime_detector.score_regime
- Portfolio 機能（純粋関数群）
  - 候補選定、等配分/スコア配分、リスク基づくポジションサイズ計算
- Tools:
  - paper_verification_report: ペーパートレード結果の PASS/FAIL レポート生成

---

セットアップ手順（開発 / 実行環境）
1. Python 環境準備（想定: Python 3.10+）
2. 依存パッケージをインストール
   - 主な依存:
     - duckdb
     - psutil
     - openai
     - PyYAML（config 検証で YAML の解析を行う場合）
   - 例:
     - pip install duckdb psutil openai pyyaml
3. プロジェクトルートで .env を作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - 生成後、設定を検証:
     - python -m kabusys.validate_config
4. データディレクトリ等の作成
   - .env の DUCKDB_PATH / SQLITE_PATH の親ディレクトリ（デフォルトは data/）を作成してください。
   - ログディレクトリ（LOG_DIR またはデフォルト logs/）も自動作成されますが、権限に注意してください。
5. OpenAI を利用する場合
   - 環境変数 OPENAI_API_KEY を設定してください（または関数呼び出し時に渡す）。

注意:
- .env は決してリポジトリにコミットしないでください（config_setup のヘッダにも明記）。
- KABUSYS_ENV により挙動が変わります（development / paper_trading / live）。

---

使い方（主要コマンド例）

- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告もエラー扱いにして exit(1) します。

- Execution エンジン起動
  - python -m kabusys.run_execution
  - 振る舞い:
    - KABUSYS_ENV=paper_trading のとき、MockBrokerClient を使用して data/paper_trading.db に書き込む（本番 DB と分離）
    - data/execution.pid に PID を書き込みます（PID ファイルパスは Settings から上書き可）
    - data/stop_requested.flag が既に存在すると起動せず終了します
    - 停止は監視側が data/kill.flag を書くか、 stop_requested.flag を立てることで制御できます

- Monitoring 起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒数で上書き可能（デフォルト 60）
  - 監視は常に本番 sqlite_path（Settings.sqlite_path）を使用して監視ログを出力します
  - run_monitoring は data/stop_requested.flag の存在でループを抜けます

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション --db で SQLite ファイルを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH も利用可）

- ライブラリ関数（プログラムから呼び出し）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - ポートフォリオ/リサーチ関数は kabusys.portfolio / kabusys.research 以下の関数群を直接呼べます。

ログ
- ロギングは kabusys.utils.logging_setup.setup_logging を通して統一されます。
- default: logs/<app_name>.log（日次ローテート、30日保持） + stdout（コンソール）に出力。

停止・Kill スイッチ
- kill.flag（Settings.kill_flag_path, デフォルト data/kill.flag）: ExecutionEngine に対する安全停止シグナル（監視ロジックが書き込む）
- stop_requested.flag（data/stop_requested.flag）: run_monitoring / run_execution の外部停止トリガ（存在を検出するとプロセスを終了）
- PID ファイル: data/execution.pid（ExecutionEngine が書き込み）

---

主な環境変数（抜粋）
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 運用（推奨／任意）:
  - KABUSYS_ENV: execution のモード。development / paper_trading / live（デフォルト development）
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
  - PAPER_FILL_MODE: ペーパートレード時の約定挙動（instant|partial|never|reject、デフォルト instant）
  - LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
  - LOG_DIR: ログ保存先ディレクトリ（デフォルト logs/）
  - OPENAI_API_KEY: OpenAI API キー（AI モジュールで使用）
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: 本番でのアラート通知に使用（任意）
  - MONITOR_POLL_INTERVAL: run_monitoring スクリプトのポーリング間隔（秒）
  - KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0）

詳しくは kabusys.config.Settings のプロパティ実装を参照してください。

---

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数・設定読み込みロジック
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層（監視ログ）
    - system_monitor.py      — システム状態・データ鮮度監視
    - trade_monitor.py       — （注文監視用モジュール）
    - risk_monitor.py        — ドローダウン / ポジション上限監視
    - kill_switch.py         — kill.flag 操作用ユーティリティ
    - monitoring_engine.py   — 各 Monitor を束ねるエンジン
    - alert_manager.py       — （LINE 等への通知管理）
  - execution/               — Execution エンジン関連（OrderManager 等）
    - execution_engine.py
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
    - news_nlp.py            — ニュース NLP スコアリング（OpenAI 呼び出し）
    - regime_detector.py     — 市場レジーム判定
  - data/                    — 実行時に使用するファイル（data/*.db, pid/flags 等）
  - tools/
    - paper_verification_report.py

（注）一部ファイルはこの README 作成時点での抜粋です。実際の実装ではさらに細分化されたモジュールや補助スクリプトが存在する可能性があります。

---

開発上の注意
- 本番モード（KABUSYS_ENV=live）での実行は慎重に。validate_config が本番用の警告を出す仕組みあり。
- .env の自動ロードはプロジェクトルート判定に .git または pyproject.toml を使っています。パッケージ化後は自動ロード挙動が変わる場合があります。
- AI モジュールは外部 API（OpenAI）に依存。API 失敗時にフォールバック動作を持つよう設計されていますが、鍵の管理・費用に注意してください。
- DuckDB / SQLite への書き込み時の互換性（例: executemany の空リスト）に注意した実装が行われています。DB バージョン差により挙動が変わることがあります。

---

トラブルシューティング（よくある問題）
- ログファイルや data ディレクトリに書き込めない
  - 権限を確認してください。LOG_DIR / data の親ディレクトリが存在するかも確認します。
- OpenAI が動作しない / キーエラー
  - OPENAI_API_KEY を .env に設定するか、関数呼び出し時に api_key を渡してください。
- run_monitoring が即終了する
  - data/stop_requested.flag が存在すると即終了します。不要なら削除してください。

---

ライセンス / コントリビュート
- README 作成時点ではライセンス情報はリポジトリ内に明示されていません。公開・配布する場合は適切なライセンスファイルを追加してください。

---

何か README に追記してほしい点（例: 実行例のログ抜粋、より詳細なディレクトリツリー、特定モジュールの API ドキュメントなど）があれば教えてください。