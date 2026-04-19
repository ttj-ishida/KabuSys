README
======

概要
----
KabuSys は日本株の自動売買・リサーチ・監視を目的とした Python パッケージです。本コードベースは次の主要機能を含みます:

- 実際の発注処理を担う ExecutionEngine（本番 / ペーパートレード切替）
- システム稼働・注文状況・リスクを監視する Monitoring
- ポートフォリオ構築（候補選択・重み付け・ポジションサイズ計算・セクター制限）
- リサーチ用のファクター計算・特徴量解析（DuckDB ベース）
- ニュースを LLM（OpenAI）でスコアリングする AI モジュール
- 各種ユーティリティ（ログ設定、プロセス優先度設定、設定ウィザード / 検証）
- 運用補助ツール（Paper Trading 検証レポート生成など）

主要な設計方針:
- 環境変数で動作モード切替（KABUSYS_ENV：development / paper_trading / live）
- DuckDB（分析用）・SQLite（監視 / 発注履歴）を併用
- 本番用データとペーパートレード用データは分離（PAPER_TRADING_SQLITE_PATH）
- OpenAI を使う処理は API キーが必須。失敗時はフォールバックして安全に継続する設計

機能一覧
--------
- 実行関連
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV=paper_trading のとき MockBroker を使用）
  - Broker/Risk/Order/Reconcilier 等の組み立て

- 監視関連
  - run_monitoring.py: SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で間隔指定可）
  - MonitoringEngine: System/Trade/Risk の各モニターを束ねてアラート・Kill Switch 評価
  - KillSwitch: フラグファイルによる ExecutionEngine 停止シグナル生成
  - MonitoringDB: SQLite ベースの永続化層（system_status, trade_logs, risk_logs, positions, dashboard など）

- ポートフォリオ構築
  - 選定（select_candidates）、重み付け（等金額・スコア加重）
  - セクター上限適用（apply_sector_cap）
  - ポジションサイズ計算（calc_position_sizes）

- リサーチ
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC 計算、統計サマリ等

- AI（OpenAI）
  - ニュースセンチメントスコアリング（news_nlp.score_news）
  - 市場レジーム判定（regime_detector.score_regime）
  - 安全なリトライ・レスポンス検証ロジックを内包

- ツール
  - config_setup.py: 対話式 .env 作成ウィザード
  - validate_config.py: 起動前の設定検証 CLI
  - tools/paper_verification_report.py: ペーパートレード DB の検証レポート生成

セットアップ手順
----------------
前提:
- Python 3.10 以上（typing の | 演算子を使用）
- システムに DuckDB、psutil、openai 等をインストールしてください。

推奨インストール（例）:
- 仮想環境作成
  - python -m venv .venv
  - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

- 必要パッケージ（最低限）:
  - pip install duckdb psutil openai PyYAML

（プロジェクトに requirements.txt がない場合は上記を参考にインストールしてください）

.env の作成:
1. 対話式ウィザードで作成:
   - python -m kabusys.config_setup
   - 画面の指示に従い J-Quants トークン / kabu API パスワード などを入力します。

2. 作成後、設定検証:
   - python -m kabusys.validate_config
   - 問題があれば指摘内容に従って .env を修正してください。
   - 本番運用前は python -m kabusys.validate_config --strict を推奨（警告もエラー扱い）

重要な環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV（development / paper_trading / live、デフォルト development）
- DUCKDB_PATH（デフォルト data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（ペーパートレード用 DB、デフォルト data/paper_trading.db）
- OPENAI_API_KEY（AI 機能を利用する場合必須）
- LOG_LEVEL（デフォルト INFO）
- KILL_FLAG_CLEAR_ON_START（0/1。本番では 0 推奨）

使い方（実行例）
----------------

ログ設定
- ログはデフォルトで logs/<app_name>.log に日次ローテーションで保存されます（logs ディレクトリが自動作成されます）。
- 環境変数 LOG_DIR で変更可能。

実行コンポーネント
- 監視ループを起動:
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を指定可能（デフォルト 60）
  - 監視は Settings.sqlite_path を使用（env に関わらず production path を使用）

- 実行エンジンを起動:
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading のとき、MockBrokerClient を使用して data/paper_trading.db に記録します。
  - 起動時に data/stop_requested.flag が存在すれば起動を行いません。

停止・Kill
- run_monitoring / run_execution ともにプロジェクトルート/data/stop_requested.flag をチェックして停止します（スクリプト側で検知して終了）。
- KillSwitch（監視の一部）は data/kill.flag を書き込み、ExecutionEngine に停止を促します。
- 実行前に KILL_FLAG_CLEAR_ON_START を設定した場合自動でクリアされる挙動に注意（本番では 0 推奨）。

ツール
- ペーパートレード検証レポート:
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD --to YYYY-MM-DD
    - --db PATH （PAPER_TRADING_SQLITE_PATH 環境変数の代替）
  - レポート内容: 稼働率、注文成功率、送信率、P95 レイテンシなど。閾値を超えると FAIL 判定になります。

AI 機能
- news_nlp.score_news / regime_detector.score_regime を利用する場合は OPENAI_API_KEY を設定してください。
- OpenAI API 呼び出しはリトライ・検証ロジックを含むため、API レート制限等に対して安定性を持たせています。

設定と注意点
- Monitoring は設定にかかわらず Settings.sqlite_path を使って監視 DB に書きます（監視データは本番 DB に記録されるため、運用時は注意）。
- Execution は KABUSYS_ENV が paper_trading のとき paper_sqlite_path を使用して本番 DB と分離します。
- PAPER_FILL_MODE（instant / partial / never / reject）はペーパートレードの約定挙動を制御します。
- process_priority.set_process_priority を起動時に呼び出してプロセス優先度を調整しますが、権限により設定できない場合は警告になります。
- DuckDB への書き込みは duckdb 接続を使います。DuckDB ファイルパスは DUCKDB_PATH で指定します。

ディレクトリ構成（抜粋）
----------------------
src/kabusys/
- __init__.py                     パッケージ定義、バージョン
- config.py                       環境変数読み込み / Settings クラス
- config_setup.py                 .env 対話式ウィザード
- validate_config.py              設定検証 CLI
- run_execution.py                ExecutionEngine 起動スクリプト
- run_monitoring.py               SystemMonitor 起動スクリプト

サブパッケージ / モジュール
- execution/                       発注関連（BrokerFactory、ExecutionEngine、OrderManager 等）
- monitoring/
  - monitoring_db.py               SQLite 永続化層
  - system_monitor.py              システム状態 / データ鮮度監視
  - trade_monitor.py               注文滞留・約定監視（コード内で参照）
  - risk_monitor.py                ドローダウン・ポジション上限監視
  - monitoring_engine.py           モニター束ね処理
  - kill_switch.py                 フラグファイルによる停止スイッチ
  - alert_manager.py               （アラート送信管理。コード内参照）
- portfolio/
  - portfolio_builder.py           候補選定・重み計算
  - position_sizing.py             株数算出・集約制限
  - risk_adjustment.py             セクター制限・レジーム乗数
- research/
  - factor_research.py             ファクター計算（momentum/volatility/value）
  - feature_exploration.py         forward returns / IC / summary
- ai/
  - news_nlp.py                    ニュース NLP スコアリング（OpenAI）
  - regime_detector.py             市場レジーム判定（OpenAI + ETF MA）
- utils/
  - logging_setup.py               統一的ログ設定
  - process_priority.py            プロセス優先度 / CPU affinity ユーティリティ
- tools/
  - paper_verification_report.py   ペーパートレード検証レポート

data/（実行時に利用・生成）
- data/kabusys.duckdb              DuckDB（デフォルト）
- data/monitoring.db               監視用 SQLite（デフォルト）
- data/paper_trading.db            ペーパートレード用 SQLite（paper_trading 時）
- data/execution.pid               Execution 用 PID ファイル
- data/kill.flag                   KillSwitch が書き込むフラグ
- data/stop_requested.flag         手動でループ停止を要求するためのフラグ

logs/（デフォルトログ出力先）
- logs/<app_name>.log              日次ローテートで出力（例: logs/execution.log, logs/monitoring.log）

開発者向けメモ
---------------
- DuckDB 接続は research / ai モジュールで SQL を組んで結果を取得する設計です。テーブル定義はコード中ドキュメントやデータパイプラインに依存します。
- .env の自動ロードは config.py に実装されています。テスト時など自動ロードを抑制する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
- validate_config.py は起動前チェックに使えます。--strict をつけると警告も失敗扱いになります。
- OpenAI 呼び出し部分はテストがしやすいようにプライベート関数（_call_openai_api）を差し替え可能になっています（unittest.mock でモックしやすい）。

ライセンス・貢献
----------------
- 本リポジトリ固有のライセンスやコントリビュート手順はリポジトリルートの LICENSE / CONTRIBUTING を参照してください（本コードスニペットには含まれていません）。

サポート・問い合わせ
--------------------
- バグ報告や使い方の質問はリポジトリの issue に記載してください。可能であればログ（logs/*.log）と実行時の .env（機密情報は除く）を添えてください。

以上。必要であれば README にインストール手順の具体的なコマンドや .env のサンプルテンプレートを追加します。どの情報を追記しますか？