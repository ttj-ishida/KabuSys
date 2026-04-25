README
======

概要
----
KabuSys は日本株の自動売買 / リサーチ基盤を想定した Python パッケージです。  
主に以下の役割を持つコンポーネントを含みます。

- ExecutionEngine（発注・リスク管理・注文管理）
- Monitoring（システム稼働・注文状況・リスク監視）
- Portfolio / Position sizing（銘柄選定・配分・株数計算）
- Research（ファクター計算・特徴量解析）
- AI 補助（ニュース NLP によるセンチメント、レジーム判定）
- CLI ユーティリティ（.env ウィザード、設定検証、レポート生成）

設計上のポイント
- Paper trading（ペーパートレード）と live（本番）は SQLite DB を分離して運用可能
- DuckDB を分析用 DB として想定
- .env 経由で設定を管理（自動ロード機能あり。無効化も可）
- ロギングは統一された setup_logging を用いてコンソール + 日次ローテーションファイル出力
- OpenAI を用いた LLM 呼び出し部はリトライや検証、部分失敗時の安全処理を組み込んでいる

主な機能一覧
----------------
- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV=paper_trading の場合は Mock ブローカーを使用し専用 DB に記録）
  - run_monitoring.py: SystemMonitor をポーリングする監視ループ（MONITOR_POLL_INTERVAL で間隔指定可能）
- 設定管理
  - config_setup.py: .env を対話式で作成 / 更新するウィザード
  - validate_config.py: .env と config/*.yaml の簡易検証（--strict オプションあり）
- 監視・アラート
  - monitoring/：SystemMonitor, TradeMonitor, RiskMonitor, KillSwitch, MonitoringEngine 等
  - monitoring_db.py: 監視ログ用 SQLite テーブルの初期化・読み書き
- ポートフォリオ構築
  - portfolio/: 候補選定、重み計算、セクター上限、ポジションサイズ計算
- リサーチ
  - research/: ファクター計算（momentum/value/volatility）、forward returns、IC 計算など（DuckDB を想定）
- AI
  - ai/news_nlp.py: raw_news を集約して OpenAI で銘柄別センチメントを算出して ai_scores に書き込む
  - ai/regime_detector.py: ETF の MA とマクロ記事の LLM 評価を合成して market_regime を決定
- ユーティリティ
  - tools/paper_verification_report.py: ペーパートレード DB から検証レポートを生成

セットアップ手順
----------------
1. Python (3.9+ 想定) を準備する
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 依存ライブラリをインストール
   - pip install duckdb psutil openai
   - （オプション）PyYAML を入れると validate_config が config/*.yaml をパースして検証します:
     pip install pyyaml
4. プロジェクトルートで .env を作成
   - 対話的に作成: python -m kabusys.config_setup
   - もしくは .env.example を参照して手動作成
   - 自動ロードはデフォルトで有効（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）
5. 設定検証（任意）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit 1）

主要な環境変数（よく使うもの）
- KABUSYS_ENV: 実行環境（development / paper_trading / live）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（monitoring.db）パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: 本番アラート用（任意）
- LOG_LEVEL: ログレベル（DEBUG/INFO/…）
- OPENAI_API_KEY: OpenAI を利用する機能で必要（news_nlp / regime_detector）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒。デフォルト 60）
- PAPER_FILL_MODE: ペーパートレードでの約定挙動（instant/partial/never/reject）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（デフォルト 0。本番では 0 推奨）

使い方（実行例）
----------------
- 環境設定ウィザード（.env を作る）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳格モード: python -m kabusys.validate_config --strict

- ExecutionEngine（発注プロセス）起動
  - 本番的に: KABUSYS_ENV=live python -m kabusys.run_execution
  - ペーパートレード: KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - paper_trading の場合、MockBrokerClient を使い PAPER_TRADING_SQLITE_PATH に記録され、本番 DB と分離される
  - stop シグナル:
    - run_execution はプロジェクト内 data/stop_requested.flag を監視します。存在すると停止します。
    - 実行時に data/execution.pid が作成される（プロセス管理用）

- Monitoring 起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数で間隔を変更可能（例: export MONITOR_POLL_INTERVAL=30）
  - run_monitoring は data/stop_requested.flag を監視して終了します
  - Monitoring は設定環境にかかわらず本番 sqlite_path を使用して監視データを記録します

- ペーパートレード検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

- AI / リサーチ系 API の呼び出し（プログラムから）
  - news_nlp.score_news(duckdb_conn, target_date, api_key=...)
  - ai.regime_detector.score_regime(duckdb_conn, target_date, api_key=...)
  - research.calc_momentum(duckdb_conn, target_date) などをインポートして利用

ログ
----
- デフォルトのログ出力先: logs/<app_name>.log（日次ローテーション、30日保持）および stdout
- setup_logging() を全スクリプトから呼ぶことで一貫したログフォーマットになります

停止・KILL スイッチ
-------------------
- KillSwitch（monitoring/kill_switch.py）は risk_monitor の結果等から条件を満たすと data/kill.flag を書き込みます。
- ExecutionEngine はこの kill.flag を検出すると安全に停止するため、運用上の緊急停止手段として利用できます。
- 注意: KILL_FLAG_CLEAR_ON_START=1 は本番で危険（自動クリアされるため）。

データベース (簡単な説明)
-----------------------
- DuckDB: 価格・ファクター等の分析用（DUCKDB_PATH）
- SQLite (monitoring.db): system_status, trade_logs, positions, risk_logs, dashboard 等の監視・履歴用
- SQLite (paper_trading.db): ペーパートレード専用の発注ログ等（KABUSYS_ENV=paper_trading 時に使用）

ディレクトリ構成
-----------------
src/kabusys/
- __init__.py                   -- パッケージ定義、__version__
- config.py                     -- 環境変数 / 設定読み込みロジック（.env 自動ロードを含む）
- config_setup.py               -- .env を対話式に作成するウィザード
- validate_config.py            -- 起動前の設定検証ツール
- run_execution.py              -- ExecutionEngine 起動スクリプト
- run_monitoring.py             -- SystemMonitor ポーリング起動スクリプト
- utils/
  - logging_setup.py            -- ロギング初期化ユーティリティ
  - process_priority.py         -- プロセス優先度 / CPU affinity ユーティリティ
- monitoring/
  - monitoring_db.py            -- SQLite テーブル初期化 / 永続化層
  - system_monitor.py           -- システム・データ鮮度監視
  - trade_monitor.py            -- 注文関連監視（存在）
  - risk_monitor.py             -- ドローダウン / ポジション上限監視
  - kill_switch.py              -- kill.flag 制御
  - monitoring_engine.py        -- モニタリングの統合ポーリング
  - alert_manager.py            -- アラート送信管理（存在）
- execution/                    -- ExecutionEngine、BrokerFactory、OrderManager 等（存在）
- portfolio/
  - portfolio_builder.py        -- 候補選定・重み計算
  - position_sizing.py          -- 株数決定・スケール調整
  - risk_adjustment.py          -- セクター上限・レジーム乗数
- research/
  - factor_research.py          -- momentum/volatility/value ファクター計算
  - feature_exploration.py      -- forward returns / IC / summary 等
- ai/
  - news_nlp.py                 -- ニュース NLP スコアリング（OpenAI 呼び出し、DB 書込）
  - regime_detector.py          -- マクロ + MA 合成で市場レジーム判定
- tools/
  - paper_verification_report.py-- ペーパートレード検証レポート生成スクリプト
- data/                         -- 実行時に使用されるファイル配置想定（logs, db, flag 等）

補足 / 運用上の注意
-------------------
- .env は絶対にバージョン管理にコミットしないでください（機密情報を含む）。
- Production (KABUSYS_ENV=live) では LINE 通知や kill flag の扱い等設定を慎重に行ってください（validate_config で警告が出ます）。
- OpenAI API を使用する機能は API キーとコストに注意し、テスト時はモック化することを推奨します。
- run_monitoring / run_execution は stop flag (data/stop_requested.flag) を見て終了するため、手動停止やプロセスマネージャからの制御と併用してください。

ライセンス・バージョン
---------------------
- パッケージ版の __version__ は src/kabusys/__init__.py で管理（例: 0.1.0）

問い合わせ / 開発者向け
-----------------------
- ロガー名や DB スキーマは実装内にドキュメントがあるため、拡張する場合は既存のコントラクト（戻り値・テーブルカラム順）に合わせてください。
- LLM 呼び出し部はテスト時にモック可能なように設計されています（内部の API 呼び出し関数を patch する）。

以上。README に不足する具体的な実装や追加の CLI を希望する場合は、どの機能のドキュメントを詳細化するか教えてください。