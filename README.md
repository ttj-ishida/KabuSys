# KabuSys

日本株向け自動売買システム（ライブラリ＋起動スクリプト群）

このリポジトリは、戦略算出・ポートフォリオ構築・発注実行・監視・研究・AIベースのニュース評価などを統合した日本株自動売買基盤です。モジュールは可能な限り純粋関数/小さい責務に分割されており、実運用向けの耐障害性（ログローテーション、DB マイグレーション、フェイルセーフ等）を備えています。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方（起動・ツール）
- 環境変数（主要）
- ディレクトリ構成（抜粋）
- 重要な実装メモ / 運用上の注意

---

プロジェクト概要
- KabuSys は日本株の自動売買システム基盤です。
- 戦略（ファクター計算 / 特徴量解析）、ポートフォリオ構築、ポジションサイジング、発注管理、リスク監視、監視/アラート、AI を使ったニュースセンチメント/レジーム判定、研究用ユーティリティなどを含みます。
- 発注部分は実際の kabuステーション API と接続する実装（BrokerClient）を利用できます。`KABUSYS_ENV=paper_trading` にすると MockBrokerClient を使用して paper DB（data/paper_trading.db）へ記録し、本番 DB と分離できます。

主な機能一覧
- 設定管理
  - .env を対話形式で作成するウィザード（kabusys.config_setup）
  - 起動前設定検証 CLI（kabusys.validate_config）
- 実行エンジン
  - ExecutionEngine（発注ループ、注文管理、リスクチェック、reconciler 等）
  - Paper trading モード（本番 DB と分離）
- 監視 / Kill Switch
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねた MonitoringEngine
  - kill.flag による ExecutionEngine 停止（KillSwitch）
  - ログ/監視データは SQLite（monitoring.db）に保存
- ポートフォリオ構築（純粋関数）
  - 候補選定、等重/スコア重み、リスク調整（セクターキャップ、レジーム乗数）、株数決定（lot 単位・aggregate cap）
- 研究モジュール
  - DuckDB を使ったファクター計算（モメンタム、ボラティリティ、バリュー）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリ
- AI モジュール（OpenAI）
  - ニュースのセンチメントを LLM で評価して ai_scores テーブルへ格納（news_nlp）
  - マクロ記事と ETF MA200 乖離を組み合わせた市場レジーム判定（regime_detector）
- ユーティリティ
  - 統一的なログ設定（TimedRotatingFileHandler + stdout）
  - プロセス優先度 / CPU affinity 設定ユーティリティ
  - Paper Trading 検証レポート生成ツール（tools.paper_verification_report）

セットアップ手順（ローカル開発向けの推奨例）
1. リポジトリをクローン
   - git clone <repo-url>
2. Python 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate（Windows: .venv\Scripts\activate）
3. 依存ライブラリをインストール
   - pip install --upgrade pip
   - 必須（例）:
     - pip install duckdb psutil openai
   - 追加 / 開発:
     - pip install PyYAML
   - （requirements.txt があればそれを使用してください）
4. .env の作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - あるいは手動でプロジェクトルートに .env を作成してください。
   - 必須環境変数（起動前に設定必須）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - AI 機能を使うなら:
     - OPENAI_API_KEY
5. DB ファイル/ディレクトリの準備
   - デフォルトで必要になるパス:
     - data/kabusys.duckdb（DuckDB、分析用）
     - data/monitoring.db（監視用 SQLite）
     - data/paper_trading.db（paper_trading モード時の DB）
   - ログディレクトリ:
     - logs/（setup_logging が作成する想定）
6. 起動前設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになる

使い方（主要スクリプト）
- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- ExecutionEngine（発注エンジン）起動
  - python -m kabusys.run_execution
  - 補足:
    - KABUSYS_ENV=paper_trading を指定すると MockBrokerClient を使用し、data/paper_trading.db に記録します（本番 DB と完全分離）。
    - 起動時に data/stop_requested.flag が存在すると起動せず終了します（外部停止フラグ）。
    - ExecutionEngine は data/execution.pid に PID を書きます（設定により変更可能）。
- Monitoring（監視）起動
  - python -m kabusys.run_monitoring
  - 補足:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を変更可能（デフォルト 60）。
    - Monitoring は KABUSYS_ENV に関わらず production 相当の sqlite_path を使用する（監視 DB を混同しないため）。
    - 同じく data/stop_requested.flag を検知すると監視ループを終了します。
- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH（PAPER_TRADING_SQLITE_PATH 環境変数の代替）
- AI モジュール（プログラム的利用）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - conn は DuckDB 接続（duckdb.connect(...)）
    - api_key 未指定なら環境変数 OPENAI_API_KEY を参照
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

主要な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: execution 動作モード（development | paper_trading | live）デフォルト: development
- PAPER_FILL_MODE: paper_trading の MockBrokerClient の fill モード（instant | partial | never | reject）デフォルト: instant
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite DB パス（デフォルト: data/paper_trading.db）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- OPENAI_API_KEY: OpenAI API キー（AI 機能に必要）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- LOG_DIR: ログファイル配置先（デフォルト: logs/）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動でクリアするか（デフォルト 0。本番では 0 推奨）
- KILL_FLAG_PATH: kill.flag のパス（デフォルト: data/kill.flag）
- PID_FILE_PATH: Execution の pid ファイル（デフォルト: data/execution.pid）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動で .env をロードする処理を無効化します（テスト用）

ディレクトリ構成（抜粋: src/kabusys）
- __init__.py
- config.py                — 環境変数 / .env 自動読み込みロジック、Settings クラス
- config_setup.py          — .env 対話式ウィザード
- validate_config.py       — 起動前の設定検証 CLI
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — Monitoring の起動スクリプト
- tools/
  - paper_verification_report.py — Paper Trading の検証レポートツール
- ai/
  - news_nlp.py             — ニュースを LLM でスコアリングして ai_scores に書き込む
  - regime_detector.py      — マクロ + ETF MA200 による市場レジーム判定
- monitoring/
  - monitoring_db.py        — SQLite テーブル作成・永続化 API
  - monitoring_engine.py    — 各 Monitor の結合ロジック（ポーリング）
  - system_monitor.py       — CPU/メモリ/ディスク/データ鮮度監視
  - trade_monitor.py        — （存在）発注ログの監視（滞留注文等）※詳細はコード参照
  - risk_monitor.py         — ドローダウン / ポジション上限監視
  - kill_switch.py          — kill.flag 書き込みユーティリティ
  - alert_manager.py        — （存在）アラート配信ロジック（LINE など）
- execution/
  - execution_engine.py     — ExecutionEngine 実装（発注ループ等）
  - broker_factory.py       — Broker クライアント生成（本番 / Mock 切替）
  - order_manager.py        — 注文管理
  - order_repository.py     — 注文永続化（SQLite など）
  - reconciler.py           — 注文差分解消ロジック
  - risk_manager.py         — 実行時リスクチェック
- portfolio/
  - portfolio_builder.py    — 候補選定 / 重み計算
  - position_sizing.py      — 株数決定アルゴリズム
  - risk_adjustment.py      — セクターキャップ / レジーム乗数
- research/
  - factor_research.py      — モメンタム / ボラティリティ / バリュー計算
  - feature_exploration.py  — 将来リターン / IC / 統計サマリ
- utils/
  - logging_setup.py        — ログ設定ユーティリティ（stdout + 日次ローテーション）
  - process_priority.py     — プロセス優先度 / CPU affinity 設定ユーティリティ

（ルート）
- config/*.yaml            — 各種設定テンプレート（system_config.yaml 等）
- data/                    — デフォルト DB / フラグ置き場（data/*.db, stop_requested.flag, kill.flag, execution.pid など）
- logs/                    — ログファイル（app_name.log が出力される）

実装メモ / 運用上の注意
- Monitoring は常に Settings.sqlite_path（監視 DB）を使用します。run_monitoring は KABUSYS_ENV に依存せず本番 sqlite_path を参照する点に注意してください。
- run_execution は KABUSYS_ENV=paper_trading の場合、paper_trading_db を使用する（本番 DB と分離）。
- kill.flag / stop_requested.flag:
  - kill.flag: KillSwitch によって Execution 停止用に書き込まれる。Execution 側ではこのフラグを検知して安全停止します。
  - stop_requested.flag: 起動スクリプト（run_execution / run_monitoring）が外部より起動を止めるために参照するフラグファイル。
- process_priority の設定は OS 権限に依存します。nice 値や Windows の優先度変更が拒否される場合はログに警告が出ますが処理は継続します。
- OpenAI を使う機能（news_nlp / regime_detector）は API キーとネットワークアクセスを必要とし、外部呼び出しに失敗した場合はフェイルセーフ（0.0やスキップ）で動作するよう設計されています。API レスポンスのバリデーションやリトライロジックを実装していますが、実運用ではコストとレート制限に注意してください。
- DB マイグレーション: monitoring_db.init_monitoring_db は冪等で実行できます。既存 DB へ新カラム追加の簡素なマイグレーションロジックを含みます。

トラブルシューティング（よくある質問）
- 「.env が読み込まれない」:
  - デフォルトでプロジェクトルート（.git または pyproject.toml を基準）を探して .env を自動読み込みします。テストなどで自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 「起動してもプロセスが停止する / 優先度が設定できない」:
  - OS 権限不足の可能性があります。root 権限や適切な権限が必要な場合がありますが、設定失敗時は警告ログを出して続行します。
- 「AI モジュールが動作しない」:
  - OPENAI_API_KEY が設定されているか、ネットワークと料金（API 使用制限）が問題ないか確認してください。

ライセンス / 貢献
- この README はコードベース説明用のテンプレートです。ライセンスや貢献ルールはリポジトリのトップレベルファイル（LICENSE 等）を参照してください。

---

必要に応じて README の各セクションを実際のプロジェクトの README.md に合わせて調整してください（依存関係の厳密なリストや実行例、CI/CD 手順等）。README の補足や実行例の追加を希望される場合は、どのコマンド／シナリオを詳述するか教えてください。