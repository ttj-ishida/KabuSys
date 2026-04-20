KabuSys
=======

日本株自動売買システム（ライブラリ＋起動スクリプト群）のソースリポジトリ向け README。
このドキュメントはリポジトリ内のコード（config / 起動スクリプト / monitoring / execution / research / ai 等）を基に作成しています。

概要
----
KabuSys は日本株の自動売買およびそれを支える運用ツール群を提供します。  
主要な役割:

- 実行エンジン（ExecutionEngine）: ブローカークライアント経由で発注を行う（本番/ペーパーを切替可能）。
- 監視（Monitoring）: システム状態・注文状態・リスク監視を定期ポーリングしログ・アラートを管理、必要なら Kill Switch で停止。
- ポートフォリオ構築 / ポジションサイズ計算: シグナルから候補選定・重み付け・株数算出までの純粋関数群。
- リサーチ / ファクター計算: DuckDB 上の prices_daily 等テーブルを参照してファクターを計算。
- AI モジュール: ニュース NLP（OpenAI）による銘柄センチメント集計、マクロセンチメントによるレジーム判定。
- ユーティリティ: 環境設定ウィザード、設定検証、ログ設定等。

主な機能
--------
- 実行環境切替: KABUSYS_ENV により development / paper_trading / live を切替。paper_trading 時は MockBroker を使用し DB を分離。
- 監視ループ: SystemMonitor / TradeMonitor / RiskMonitor を定期実行、アラート発行・kill.flag 書込み等。
- Kill Switch: ドローダウンやポジション上限などの条件で停止フラグを書込み ExecutionEngine を安全停止。
- ポートフォリオ構築: 候補選定、等重/スコア重み、リスクベース配分、セクター上限、レジーム乗数。
- リサーチ: モメンタム・ボラティリティ・バリュー等のファクター計算、IC/統計サマリ。
- ニュース NLP（OpenAI）: raw_news を集約して銘柄ごとのセンチメントを ai_scores に書込む（OpenAI API 必須）。
- Paper Trading レポート: 運用検証用のパフォーマンス / 可用性レポート生成ツール。

前提 / 必要要件
---------------
- Python 3.10+（型注釈の | 合成等を使用）
- (推奨/必須ライブラリ)
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML (config ファイル検証を行う場合)
- SQLite は標準ライブラリで利用可能

インストール（例）
-----------------
1. リポジトリをクローン
   git clone <repo-url>
2. 仮想環境を作成・有効化
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
3. 依存ライブラリをインストール
   pip install duckdb psutil openai pyyaml

（requirements.txt がある場合は pip install -r requirements.txt）

設定（.env）
-----------
プロジェクトルートに .env を置くことで環境変数を設定します。自動読み込みが有効（デフォルト）で、.env.local があれば優先して上書きします。自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

主な環境変数（代表）
- KABUSYS_ENV: execution モード（development / paper_trading / live）
  - paper_trading: MockBroker を使用し paper_sqlite_path(デフォルト data/paper_trading.db) に記録
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI を使う機能で必要
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード DB（デフォルト data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- PID_FILE_PATH: ExecutionEngine の PID ファイルパス（デフォルト data/execution.pid）
- KILL_FLAG_PATH: kill.flag のパス（デフォルト data/kill.flag）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、監視スクリプトで上書き可能。デフォルト 60）

.env の初期作成は対話式ウィザードを使うと便利です（下記参照）。

セットアップ手順（推奨）
--------------------
1. .env を作成
   python -m kabusys.config_setup
   → 対話形式で .env を作成／更新します。

2. 設定検証
   python -m kabusys.validate_config
   --strict オプションで警告もエラー扱いにできます。

3. 必要な DB ファイルは自動作成される場合があります（logs/ ディレクトリも自動作成）。ただし .env で指定した親ディレクトリが存在しない場合は警告が出るので注意してください。

使い方（起動 / CLI）
-------------------

起動スクリプト（モジュール実行）
- 実行エンジン起動（バックグラウンド等で管理）
  python -m kabusys.run_execution

  動作概要:
  - プロセス優先度を高く設定
  - KABUSYS_ENV が paper_trading のときは専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用
  - ExecutionEngine をスレッドで起動し stop フラグ (data/stop_requested.flag) を監視

- 監視ループ起動
  python -m kabusys.run_monitoring

  動作概要:
  - SystemMonitor を中心に定期ポーリング
  - 環境変数 MONITOR_POLL_INTERVAL で間隔を上書き可（秒、デフォルト 60）
  - 監視は常に本番の sqlite_path（SQLITE_PATH）を参照

ユーティリティ
- .env ウィザード
  python -m kabusys.config_setup

- 設定検証
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- Paper Trading 検証レポート
  python -m kabusys.tools.paper_verification_report
  オプション:
    --from YYYY-MM-DD  --to YYYY-MM-DD  --db PATH
  環境変数 PAPER_TRADING_SQLITE_PATH で DB を指定可能。

AI 機能
- ニュース NLP（ai.score_news）
  - OpenAI API キー（OPENAI_API_KEY）が必須
  - DuckDB の raw_news / news_symbols テーブルを参照し ai_scores テーブルへ書込み
- マクロレジーム判定（ai.regime_detector.score_regime）
  - OpenAI API キー必須
  - prices_daily, raw_news 等 / market_regime に書込み

監視・停止方法
- stop_requested.flag (data/stop_requested.flag)
  - run_execution.py / run_monitoring.py はこのファイルの存在を見てループを終了します（停止フラグ）
- kill.flag (デフォルト data/kill.flag)
  - KillSwitch が条件を満たすと書込み、ExecutionEngine 側はこれを検出して停止する想定
  - Settings.kill_flag_clear_on_start が 1 の場合、起動時に自動クリアされる（本番では 0 推奨）

ログ
----
ログは kabusys.utils.logging_setup.setup_logging により管理されます。
- デフォルト: logs/<app_name>.log に日次ローテーションで出力（30日保持）
- console 出力は stdout（stderr ではない）に送られます
- LOG_DIR 環境変数または setup_logging の引数で変更可能

主要ファイル / ディレクトリ構成
-----------------------------
（主要なものを抜粋）

- src/kabusys/
  - __init__.py
  - config.py                : 環境変数・Settings 管理（自動 .env ロード含む）
  - config_setup.py          : .env 対話式ウィザード
  - validate_config.py       : 設定検証 CLI
  - run_execution.py         : ExecutionEngine 起動スクリプト
  - run_monitoring.py        : Monitoring ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py : Paper Trading の検証レポート生成スクリプト
  - ai/
    - news_nlp.py            : ニュース NLP / OpenAI 呼び出し、ai_scores 書込
    - regime_detector.py     : マクロ + ETF MA から market_regime を算出
  - portfolio/
    - portfolio_builder.py   : 候補選定・重み計算
    - risk_adjustment.py     : セクターキャップ・レジーム乗数
    - position_sizing.py     : 株数決定・aggregate cap 等
  - research/
    - factor_research.py     : モメンタム/ボラティリティ/バリュー等の計算
    - feature_exploration.py : 将来リターン・IC・統計
  - monitoring/
    - monitoring_db.py       : SQLite ベースの永続化 / マイグレーション
    - monitoring_engine.py   : 各 monitor の統括ループ
    - system_monitor.py      : システム状態・データ鮮度チェック
    - trade_monitor.py       : （注文監視関連）
    - risk_monitor.py        : ドローダウン/ポジション数監視
    - kill_switch.py         : kill.flag 管理
    - alert_manager.py       : （アラート送信管理）
  - execution/
    - execution_engine.py    : ExecutionEngine（起動/セッション管理）
    - broker_factory.py      : BrokerClientFactory（Mock / 実ブローカ）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - data/                    : (データファイル: default DB/ログ/flag 配置)
  - logs/                    : (ログファイル。自動作成)

（補足）
- monitoring_db.init_monitoring_db は起動時に必要テーブルとインデックスを作成します。既存 DB に対する軽微なマイグレーション（カラム追加）にも対応しています。
- 多くの関数は外部副作用を持たない「純粋関数」または DB 抽象化された層に分離されています。テストや差替が容易な設計になっています。

運用上の注意
-------------
- 本番（KABUSYS_ENV=live）時は .env の値を慎重に設定してください。validate_config によりライブ用チェック（LINE 等通知設定、kill flag の自動クリア設定など）を行います。
- OPENAI_API_KEY や KABU_API_PASSWORD、JQUANTS_REFRESH_TOKEN 等のシークレットは .env に保存し、絶対に Git 等へコミットしないでください。
- ペーパートレード用 DB は本番 DB と分離されています（settings.paper_sqlite_path）。KABUSYS_ENV=paper_trading の場合に自動で分離されます。
- プロセス優先度や CPU affinity の設定は psutil を利用しており、権限や OS により失敗する場合があります（ワーニングでスキップ）。

開発 / テスト
--------------
- 多くの I/O（DB、OpenAI、ブローカ）を外部依存としているため、単体テストはモック差替えで行う設計になっています（各モジュールは外部呼び出しをラップしている箇所があり、テスト時に patch 可能）。
- ロギングや DB のパスは環境変数で切替可能なので、CI 用に一時的なパスを指定して実行できます。

問い合わせ・貢献
----------------
このドキュメントはコード注釈に基づいて作成されています。実際の運用や追加機能の提案・バグ報告はリポジトリの issue / PR 機能を使ってください。

ライセンス
---------
リポジトリに従う（LICENSE ファイルを参照してください）。

---

以上がこのコードベースの概要・セットアップ・使い方の要約です。必要なら README に含めるコマンド例や .env.example のテンプレートを出力できます。どの情報を追記しますか？