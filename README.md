# KabuSys — 日本株自動売買システム

このリポジトリは日本株向けの自動売買システム（プロトタイプ）です。戦略・ポートフォリオ構築、発注処理（本番 or ペーパートレード）、監視、Research/AI 補助ツールを含みます。

README は日本語で主要な概要・機能・セットアップ・使い方・ディレクトリ構成を示します。

---

目次
- プロジェクト概要
- 主な機能
- 必要要件（依存）
- セットアップ手順
- 使い方（主要コマンド）
- 環境変数（主要）
- 制御ファイル（フラグ / PID）
- ディレクトリ構成（主要ファイルと役割）
- 注意事項 / セキュリティ

---

プロジェクト概要
- KabuSys は日本株の自動売買を想定したシステム群です。
- コンポーネントは発注エンジン（ExecutionEngine）、監視（MonitoringEngine / SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch）、ポートフォリオ構築、ファクター/リサーチ、AI（ニュースセンチメント / レジーム判定）などに分かれています。
- データ永続化には SQLite（監視・発注ログ等）と DuckDB（時系列価格・分析）を利用します。
- 設計方針として「本番用コードとペーパートレードを分離」「ルックアヘッドバイアスを排除」「フェイルセーフ（API失敗時の安全側フォールバック）」が採用されています。

---

主な機能
- Execution
  - 実際の発注処理（kabuステーション API 経由）またはペーパートレード（MockBrokerClient）での動作切替
  - リスク管理（最大ポジション比率、利用率、サーキットブレーカーなど）
  - 注文管理・リコンシリエーション
- Monitoring
  - システムの CPU / メモリ / ディスク使用率と Execution プロセスの生存確認
  - 注文滞留（stale orders）や約定価格の異常検出
  - ドローダウン・ポジション上限監視と Kill Switch（kill.flag）発動
  - ログは SQLite の monitoring DB に永続化
- Portfolio
  - 候補選定、等配分／スコア配分、ポジションサイズ算出（lot 単位丸め、コストバッファ対応）
  - セクターキャップ、レジームに応じた資金乗数
- Research
  - ファクター計算（Momentum / Volatility / Value 等）
  - 特徴量探索、IC（Information Coefficient）計算、将来リターン計算
  - DuckDB を用いたローカル分析
- AI
  - ニュース記事のセンチメントを OpenAI（gpt-4o-mini 想定）でスコアリングし ai_scores に書き込み
  - マクロニュース＋ETF MA を合成して市場レジームを判定し market_regime に保存
- ツール
  - .env 作成ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading 検証レポート生成ツール（paper_verification_report）

---

必要要件（依存）
- Python 3.9+（型ヒントで | を使っているため 3.10 以上が好適ですが、バックポート次第）
- 必須ライブラリ（例）
  - duckdb
  - psutil
  - openai
- 任意（機能により必要）
  - PyYAML（config/*.yaml の構文チェックに使用。未インストールでも動作する）
- 標準ライブラリ: sqlite3, logging, threading, datetime, pathlib など

（実行環境へは requirements.txt を用意することを推奨します）

---

セットアップ手順（ローカル開発向け）
1. リポジトリをクローンして Python 仮想環境を準備
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)
2. 必要パッケージをインストール（例）
   - pip install duckdb psutil openai
   - （必要に応じて PyYAML を追加: pip install pyyaml）
3. 環境変数を設定
   - 推奨: python -m kabusys.config_setup を実行して .env を対話式に作成
   - もしくは .env を手動作成（.env.example を参考に）
   - 自動ロード: リポジトリルートに .env または .env.local があれば自動で読み込まれます（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）
4. DB ファイルの配置
   - デフォルトのパス:
     - DuckDB: data/kabusys.duckdb
     - Monitoring SQLite: data/monitoring.db
     - Paper Trading SQLite: data/paper_trading.db
   - 初回は空ファイルを配置するか、必要に応じてスクリプトで初期化してください（monitoring DB は起動時にテーブル作成を行います）
5. OpenAI 等の外部 API キーは環境変数に設定（OPENAI_API_KEY 等）

---

主要な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants API 用
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
  - paper_trading の場合、MockBrokerClient を使用し、paper_trading DB（PAPER_TRADING_SQLITE_PATH）に記録
- PAPER_FILL_MODE — paper_trading 時の約定モード: instant | partial | never | reject（デフォルト: instant）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PID_FILE_PATH — ExecutionEngine 用 PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH — Kill Switch 用 flag（デフォルト: data/kill.flag）
- MONITOR_POLL_INTERVAL — Monitoring のポーリング間隔（秒。デフォルト: 60）
- LOG_LEVEL — ログレベル: DEBUG | INFO | WARNING | ERROR | CRITICAL
- OPENAI_API_KEY — OpenAI API キー（AI モジュールで使用）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 にすると .env の自動ロードを無効化

---

使い方（主要コマンド / スクリプト）
- 環境設定ウィザード（対話式で .env を作成）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
  - Strict モード（警告も失敗扱い）: python -m kabusys.validate_config --strict
- 発注エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading のときは MockBroker を使用し、ペーパートレード DB に記録されます
  - 起動時に PID ファイル (data/execution.pid) を書き込み、stop フラグや kill.flag の影響を受けます
- 監視ループ起動（SystemMonitor を単体でポーリング）
  - python -m kabusys.run_monitoring
  - ポーリング間隔を環境変数 MONITOR_POLL_INTERVAL で上書き可能（秒、デフォルト 60）
  - 監視は常に本番 sqlite_path を参照（環境にかかわらず）
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション: --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
  - 環境変数 PAPER_TRADING_SQLITE_PATH で DB を指定可能
- AI / レジーム判定 / スコアリングはモジュール関数として利用可能
  - kabusys.ai.score_news(...)
  - kabusys.ai.regime_detector.score_regime(...)

実行上の注意:
- run_execution と run_monitoring はそれぞれプロセス優先度を "high" に設定しようとします（psutil 経由）。権限がない場合は警告を出してスキップされます。
- stop_requested.flag（data/stop_requested.flag）は run_execution と run_monitoring によるループ停止用の外部制御ファイルとして利用されます。
- kill.flag（Settings.kill_flag_path, デフォルト data/kill.flag）は KillSwitch による ExecutionEngine 停止要求（ドローダウン等）に使われます。kill.flag は KillSwitch が書き込み、ExecutionEngine 起動時にクリアする挙動が設定されている場合があります（KILL_FLAG_CLEAR_ON_START 環境変数参照）。

---

制御ファイル（フラグ / PID）
- data/execution.pid — ExecutionEngine が起動時に書き込む PID ファイル（存在チェックにより process_ok 判定）
- data/stop_requested.flag — run_execution / run_monitoring の監視ループを外部から停止するためのフラグ（存在を検知してループを終了）
- data/kill.flag — KillSwitch が書き込む停止要求ファイル。存在すると ExecutionEngine 停止条件に使われる（設定により起動時に自動クリアする場合あり）

---

ディレクトリ構成（主要ファイルと役割）
- src/kabusys/
  - __init__.py — パッケージ定義、バージョン
  - config.py — 環境変数の読み込み・Settings クラス（.env 自動ロード、必須チェックなど）
  - config_setup.py — .env 対話ウィザード（CLI）
  - validate_config.py — 起動前の設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ（psutil）
  - execution/ (発注関連コンポーネント)
    - execution_engine.py, order_manager.py, order_repository.py, broker_factory.py, reconciler.py, risk_manager.py, order_record.py, ...
  - monitoring/
    - monitoring_db.py — SQLite 永続層（テーブル作成・読み書き）
    - system_monitor.py — システム状態・データ鮮度監視
    - trade_monitor.py — 注文滞留・価格異常監視
    - risk_monitor.py — ドローダウン・ポジション数監視
    - kill_switch.py — Kill Switch 実装（kill.flag 書き込み）
    - monitoring_engine.py — 複数 Monitor を束ねるエンジン
    - alert_manager.py — 通知管理（LINE 等）※実装部分が続く想定
  - portfolio/
    - portfolio_builder.py — 候補選定・スコアソート
    - position_sizing.py — 株数計算、リスク制限、丸め
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — ファクター計算（momentum/volatility/value）
    - feature_exploration.py — 将来リターン／IC／統計サマリ
  - ai/
    - news_nlp.py — ニュース記事を LLM でセンチメント評価し ai_scores へ記録
    - regime_detector.py — ETF MA とマクロセンチメントを合成して日次レジーム判定
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成ツール

（詳細なファイルは src 以下を参照してください）

---

運用上の注意 / セキュリティ
- .env は秘密情報（API トークン・パスワード）を含むため絶対に Git へコミットしないでください。
- 本番（KABUSYS_ENV=live）での起動前に python -m kabusys.validate_config を実行して設定を確認してください。LINE 通知設定や Kill Switch の設定も確認すること。
- OpenAI API や外部 API の呼び出しはレート制限・エラーに備えたリトライ・フェイルセーフ実装がありますが、キー管理やコストに注意してください。
- run_execution / run_monitoring はプロセス優先度変更や PID ファイルを使います。OS 権限により操作が失敗する場合があります（警告ログが出ます）。

---

トラブルシューティング（よくある問題と対策）
- .env が読み込まれない:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD が 1 に設定されていないか確認
  - プロジェクトルートの判定は .git または pyproject.toml を基準に行っています（配置場所に注意）
- monitoring DB のテーブルがない / 起動時に作成されない:
  - run_monitoring または run_execution 起動時に init_monitoring_db が呼ばれてテーブルを作成します。ファイルパーミッションとパスを確認してください。
- OpenAI 呼び出しで失敗する:
  - OPENAI_API_KEY が設定されているか確認
  - ネットワークや API のレート制限により一時的に失敗することがあります（リトライとログを確認）

---

その他
- 各モジュールのドキュメントはソースの docstring に詳述されています。実装や挙動を確認したい場合は該当モジュールのヘッダコメントを参照してください。
- 新しい機能や設定を追加する場合は validate_config.py と config_setup.py を更新してユーザー側の導線を保つことを推奨します。

---

この README は主要な操作をまとめたサマリです。より詳細な API 利用方法や内部設計（StrategyModel.md / PortfolioConstruction.md 等）が別途存在することを想定しています。必要であれば README に追記・展開できます。