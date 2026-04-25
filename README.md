README
=====

プロジェクト概要
--------
KabuSys は日本株向けの自動売買 / 研究支援用ライブラリ兼実行フレームワークです。本リポジトリには次のような機能群を含みます。

- 発注エンジン（ExecutionEngine）とその周辺コンポーネント（ブローカー抽象、オーダー管理、リスク管理、照合）
- 監視システム（MonitoringEngine）：システム稼働状況、注文状況、リスク監視、Kill Switch 機能
- ポートフォリオ構築ユーティリティ（候補選定、重み付け、ポジションサイズ計算、セクター制限）
- 研究モジュール（DuckDB を用いたファクター計算 / 特徴量解析）
- AI 関連ユーティリティ（ニュースのセンチメントスコアリング、レジーム判定：OpenAI API を利用）
- 開発支援ツール（.env 対話ウィザード、設定検証、ペーパートレード検証レポート生成）

主な設計方針：
- 実行環境（本番 / ペーパートレード / 開発）を分離して運用可能
- DB は DuckDB（分析）と SQLite（ログ／監視／注文履歴）を併用
- 自動化 / デーモン化を想定したファイルフラグ（PID / stop / kill）による制御
- 可能な限り副作用を抑えた純粋関数群（ポートフォリオ・研究系）

主な機能一覧
--------
- Execution
  - 実際の発注を行う ExecutionEngine（本番 / ペーパー切替可能）
  - ブローカーファクトリ経由で MockBrokerClient（paper_trading）を利用可能
  - リスク管理（ポジション上限、ドローダウン制御など）
- Monitoring
  - SystemMonitor（CPU/メモリ/ディスク、データ鮮度、Execution プロセス監視）
  - TradeMonitor（滞留注文、約定異常等の検出）
  - RiskMonitor（ドローダウン、ポジション上限の監視）
  - KillSwitch（閾値超過で data/kill.flag を書き込み Execution 停止を誘発）
  - MonitoringEngine（定期ポーリング・アラート送信）
- Portfolio
  - 候補選定（スコア降順）
  - 重み計算（等金額・スコア重み）
  - ポジションサイズ計算（リスクベース、各種制約・丸め処理）
  - セクター上限適用、レジーム乗数
- Research
  - DuckDB を用いたファクター計算（モメンタム、ボラティリティ、バリュー等）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
- AI
  - ニュース NLP（OpenAI を用いた銘柄ごとのセンチメントスコア算出）
  - レジーム判定（ETF MA とマクロセンチメントの合成）
- 開発ツール
  - .env 対話ウィザード（python -m kabusys.config_setup）
  - 設定検証 CLI（python -m kabusys.validate_config）
  - Paper Trading 検証レポート（python -m kabusys.tools.paper_verification_report）

動作要件（最低限）
--------
- Python 3.10+（typing の | 演算子や型ヒントを使用しているため）
- 必要な外部ライブラリ（主要な imports からの抜粋）:
  - duckdb
  - psutil
  - openai (AI 機能を利用する場合)
  - PyYAML（config/*.yaml の検証を行う場合に optional）
- SQLite は Python 標準ライブラリに含まれます

セットアップ手順
--------
1. リポジトリをクローンし、仮想環境を作成・有効化します。
   例:
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストールします（requirements.txt を用意している場合はそれを使用）。
   例（依存ファイルがない場合は手動でインストール）:
   - pip install duckdb psutil openai PyYAML

3. .env の初期作成（対話ウィザード）
   - python -m kabusys.config_setup
   ウィザードは J-Quants / kabuステーション パスワードなど必須項目の入力を助けます。
   生成された .env はプロジェクトルートに保存されます。※.env を Git にコミットしないでください。

4. 設定検証（起動前に必ず実行推奨）
   - python -m kabusys.validate_config
   オプション --strict を付けると警告もエラー扱いになります。

主要な環境変数（例 / デフォルト）
--------
- KABUSYS_ENV: 実行環境（development / paper_trading / live）。デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API（必須）
- KABU_API_PASSWORD: kabuステーション API（必須）
- KABU_API_BASE_URL: デフォルト http://localhost:18080/kabusapi
- LOG_LEVEL: デフォルト INFO
- DUCKDB_PATH: 分析 DB（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（paper_trading 時）
- PAPER_FILL_MODE: instant | partial | never | reject（paper_trading の約定挙動）
- OPENAI_API_KEY: OpenAI を利用する際に必要
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒。デフォルト 60）

使い方（起動 / 停止 / ツール）
--------

- Execution Engine の起動（本番／ペーパー共通）
  - python -m kabusys.run_execution
  実行時は Settings に従い paper_trading 環境であれば MockBrokerClient を利用し、ペーパートレード DB（data/paper_trading.db）に記録されます。
  起動時に data/stop_requested.flag が既に存在する場合は起動をスキップします。

- Monitoring の起動
  - python -m kabusys.run_monitoring
  監視は Settings から指定される sqlite_path（data/monitoring.db がデフォルト）にログを残します。
  ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書きできます（デフォルト 60）。

- ログ
  - logs/<app_name>.log に日次ローテーションで出力されます（デフォルト logs/ に出力）。
  - 起動時に setup_logging(app_name="execution" または "monitoring") が自動的に設定されます。

- 停止制御
  - 実行中の ExecutionEngine を強制停止させたい場合は監視側 KillSwitch による自動停止か、ファイルフラグを書き込む方法があります。
    - 手動で停止指示を出す（プロセスに対する一般的な SIGINT 等）か、監視が kill.flag を書き込むと ExecutionEngine は停止します。
  - run_monitoring.py や run_execution.py はプロジェクトルートの data/stop_requested.flag を検出するとループを抜けて終了します。停止要求は stop_requested.flag を作成することで行えます。

- .env の作成・更新
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告もエラー扱いになります。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を指定する場合:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI 機能（ニューススコアリング／レジーム判定）
  - OpenAI API キー（OPENAI_API_KEY）が必要です。
  - ライブラリ関数:
    - kabusys.ai.score_news(conn, target_date, api_key=None)
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは DuckDB 接続（DuckDBPyConnection）を引数に取り、DB のテーブル（raw_news, news_symbols, ai_scores, prices_daily 等）を参照・更新します。
  - API 呼び出しはエラー時にリトライやフォールバック処理が組み込まれています（フェイルセーフ設計）。

開発者向けメモ
--------
- .env 自動読み込み
  - プロジェクトルート（.git または pyproject.toml が見つかるディレクトリ）を起点に .env, .env.local を自動的に読み込みます。自動読み込みは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます。
- データベース
  - init_monitoring_db() は冪等でテーブルと必要なカラムのマイグレーションを行います。
- ロギング
  - setup_logging で stdout と日次ローテーションファイルを組み合わせて設定します。ログディレクトリが作れない場合はコンソール出力のみになります。
- プロセス優先度 / CPU affinity
  - set_process_priority/set_cpu_affinity が用意されており、起動スクリプトで優先度を上げるために呼んでいます（権限によっては警告が出ます）。

ディレクトリ構成（主要ファイル）
--------
src/kabusys/
- __init__.py
- config.py — 環境変数 / Settings 管理、自動 .env 読み込み
- config_setup.py — .env 対話ウィザード（CLI）
- validate_config.py — 設定検証 CLI
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — SystemMonitor ポーリング起動スクリプト

サブパッケージ（抜粋）
- ai/
  - news_nlp.py — ニュースの OpenAI ベースセンチメントスコア算出
  - regime_detector.py — 市場レジーム判定（ETF MA とマクロセンチメント）
- monitoring/
  - monitoring_db.py — SQLite 永続化層（テーブル作成・読み書き API）
  - system_monitor.py — システム状態監視（CPU/メモリ/ディスク・データ鮮度）
  - trade_monitor.py — 発注ログ監視（滞留注文・約定異常など）
  - risk_monitor.py — ドローダウン、ポジション上限監視
  - kill_switch.py — kill.flag 管理
  - monitoring_engine.py — 各モニタの統合ポーリング
  - alert_manager.py — （アラート送信ロジック、実装に依存）
- execution/
  - execution_engine.py — 実行エンジン本体（EngineConfig, run_session 等）
  - broker_factory.py — ブローカークライアント生成（本番 / mock 切替）
  - order_manager.py, order_repository.py, reconciler.py, risk_manager.py — 発注関連
- portfolio/
  - portfolio_builder.py — 候補選定・重み付け
  - position_sizing.py — 発注株数計算・スケーリング
  - risk_adjustment.py — セクターキャップ・レジーム乗数
- research/
  - factor_research.py — 各種ファクター計算（DuckDB）
  - feature_exploration.py — IC 等の研究用ユーティリティ
- utils/
  - logging_setup.py — ログ設定ユーティリティ
  - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ
- tools/
  - paper_verification_report.py — ペーパートレード検証レポート生成スクリプト

data/ （実行時作成想定）
- monitoring.db（デフォルト SQLITE_PATH）
- paper_trading.db（ペーパートレード用）
- kill.flag, stop_requested.flag, execution.pid などの制御ファイル

logs/ （デフォルトログ出力先）
- execution.log
- monitoring.log
- など（日次ローテーション）

FAQ / 注意点
--------
- KABUSYS_ENV=paper_trading の場合、mock ブローカーが使用され、本番 DB と分離されます（PAPER_TRADING_SQLITE_PATH を使用）。
- MONITOR_POLL_INTERVAL に 0 や負の値を設定すると無効扱いになりデフォルト（60秒）にフォールバックします。
- OpenAI ベースの機能は API キーが必須です。API エラー時の挙動はフォールバック（0.0 等）やリトライが組み込まれており、システム全体が停止しない設計になっています。
- .env はセキュア情報を含むため絶対にリポジトリにコミットしないでください。

貢献 / 開発
--------
- コードスタイルは既存の型ヒント・ドキュメンテーションに倣ってください。
- DB スキーマ変更やマイグレーションは monitoring_db.init_monitoring_db のように冪等で行う設計にしてください。
- ユニットテストは主要ロジック（ポートフォリオ計算、position sizing、research 等）を中心に実装してください。外部 API 呼び出しはモック化を推奨します。

問い合わせ
--------
- 実行や設定に関する問題は issue を立ててください。README の手順でうまく動かない場合は環境変数（.env）の内容（トークン類は伏せた状態）とログファイルを添えて報告してください。

以上。