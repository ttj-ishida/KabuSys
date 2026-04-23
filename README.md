KabuSys — 日本株自動売買システム
================================

このリポジトリは日本株の自動売買／リサーチ用ライブラリ群と、それらを起動する小さな実行スクリプト群を含みます。コードはモジュール化されており、発注ロジック（Execution）、監視（Monitoring）、ポートフォリオ構築（Portfolio）、因子計算・解析（Research）、LLM を使ったニュース解析（AI）などの機能を提供します。

主な特徴
--------
- Execution（発注エンジン）:
  - 本番 / ペーパートレードを切り替え可能（KABUSYS_ENV）。
  - RiskManager / OrderManager / Reconciler 等の構成要素を備えた ExecutionEngine。
  - ペーパートレード時は専用 SQLite（data/paper_trading.db）に記録し、本番 DB と分離。

- Monitoring（監視）:
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine。
  - system_status, trade_logs, risk_logs, positions, dashboard を持つ SQLite ベースの監視 DB（data/monitoring.db）。
  - Kill Switch による停止（data/kill.flag）や stop フラグ（data/stop_requested.flag）検出。

- Portfolio（ポートフォリオ構築）:
  - 候補選定、等重・スコア重みの計算、ポジションサイズ算出（単元株丸め、上限チェック）等を純粋関数で実装。

- Research（ファクター・解析）:
  - Momentum / Volatility / Value 等のファクター計算（DuckDB を使用）。
  - 将来リターン計算、IC（Information Coefficient）や統計サマリー等。

- AI（LLM）:
  - ニュースを OpenAI（gpt-4o-mini）でスコアリングして ai_scores に保存する処理（フェイルセーフ・リトライ実装）。
  - マクロニュースと ETF MA200 を合成して市場レジームを判定し market_regime テーブルへ永続化。

- ユーティリティ:
  - 環境設定ウィザード（.env の対話式作成）と設定検証ツール。
  - ロギングセットアップ、プロセス優先度設定ユーティリティ等。

セットアップ手順
----------------
前提
- Python 3.9+（一部の型注釈や pathlib の振る舞いを使用）
- SQLite は標準ライブラリで利用可能
- 必要な外部パッケージ（主なもの）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config YAML の検証を行いたい場合のみ）
インストール例:
  pip install duckdb psutil openai PyYAML

環境変数（.env）
- 自動ロード: パッケージはプロジェクトルート（.git または pyproject.toml が存在するディレクトリ）から .env と .env.local を自動ロードします。自動ロードを無効にするには:
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

必須（主な）環境変数
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI を使う機能（news_nlp / regime_detector）で必要（直接引数で渡すことも可）

その他（よく使う）
- KABUSYS_ENV: 実行環境（development | paper_trading | live）。デフォルト: development
- DUCKDB_PATH: DuckDB ファイルパス。デフォルト data/kabusys.duckdb
- SQLITE_PATH: 監視 DB（monitoring）パス。デフォルト data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（KABUSYS_ENV=paper_trading 時に使用）。デフォルト data/paper_trading.db
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）。デフォルト INFO
- LOG_DIR: ログファイル保存先（デフォルト logs/）
- PAPER_FILL_MODE: ペーパートレードの成行/部分約定動作（instant|partial|never|reject）。デフォルト instant
- MONITOR_POLL_INTERVAL: SystemMonitor ポーリング間隔（秒）。デフォルト 60（run_monitoring にて参照）
- KILL_FLAG_CLEAR_ON_START: 本番で Kill Flag を自動クリアするか（1 = 自動クリア）。本番では 0 推奨

推奨手順
1. リポジトリルートに移動
2. 仮想環境作成・有効化
3. 依存ライブラリをインストール（上記）
4. python -m kabusys.config_setup を実行して .env を生成・編集
   - その後 python -m kabusys.validate_config で設定チェック

使い方（実行）
----------------

設定ウィザード / 検証
- .env ウィザード:
  python -m kabusys.config_setup
- 設定検証:
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict  （警告も失敗扱い）

監視ループ（Monitoring）
- 起動:
  python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒で指定可能。
  - 実行中に data/stop_requested.flag が作られるとループを安全に終了します。
  - 監視は常に settings.sqlite_path（デフォルト data/monitoring.db）を使用します（環境に依存せず本番 DB を参照する仕様）。

発注エンジン（Execution）
- 起動:
  python -m kabusys.run_execution
  - KABUSYS_ENV が paper_trading の場合、MockBrokerClient を使い PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録します（本番 DB と分離）。
  - 実行中に data/stop_requested.flag が作られるとエンジンを停止します。
  - Kill Switch（data/kill.flag）を用いることで外部から ExecutionEngine を停止させる運用が可能。

ツール
- Paper Trading 検証レポートの生成:
  python -m kabusys.tools.paper_verification_report
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  --db オプションでデータベースパスを指定可能（PAPER_TRADING_SQLITE_PATH 環境変数も利用可能）

AI / リサーチ関数（プログラム API）
- AI スコアリングやレジーム判定はモジュール関数として公開されています（CLI は限定的）。
  例（概念）:
    from kabusys.ai.news_nlp import score_news
    score_news(duckdb_conn, target_date, api_key="...")

  または
    from kabusys.ai.regime_detector import score_regime
    score_regime(duckdb_conn, target_date, api_key="...")

注意点
- OpenAI 周りは API 呼び出し・レート制限のためリトライ・バックオフ実装済みですが、API キーが必要です。
- DuckDB の接続を受け取り SQL を実行する関数群が多いので、DuckDB ファイルの準備（prices_daily / raw_financials 等のテーブル）が必要です。
- monitoring は監視 DB を初期化する機能を持ちます（init_monitoring_db）。初回起動時にテーブルとマイグレーションを作成します。
- .env は絶対に Git にコミットしないでください（config_setup の出力にも注意書きあり）。

運用 / 停止方法
- ExecutionEngine の安全停止:
  - Kill Switch: data/kill.flag を作成すると起動中のエンジンは停止処理を経て終了します（KillSwitch を使用する監視ロジックを組むと自動で作成されます）。
  - Stop リクエスト: data/stop_requested.flag をファイルシステム上に作ると run_execution / run_monitoring はループを抜けます。

ディレクトリ構成（主なファイル）
--------------------------------
（src/kabusys 以下を想定）

- kabusys/
  - __init__.py                          パッケージ定義
  - config.py                            環境変数 / 設定読み込みロジック
  - config_setup.py                      .env 対話式ウィザード
  - validate_config.py                   設定検証 CLI
  - run_execution.py                     ExecutionEngine 起動スクリプト
  - run_monitoring.py                    SystemMonitor 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py       ペーパートレード検証レポート
  - ai/
    - __init__.py
    - news_nlp.py                        ニュースの LLM スコアリング
    - regime_detector.py                 市場レジーム判定
  - monitoring/
    - monitoring_db.py                   SQLite の監視 DB レイヤ
    - system_monitor.py                  システム状態・データ鮮度監視
    - trade_monitor.py                   （TradeMonitor: 発注ログ監視）*
    - risk_monitor.py                    ドローダウン・ポジション上限監視
    - monitoring_engine.py               各モニタをまとめる
    - kill_switch.py                      Kill Switch 実装
    - alert_manager.py                   （アラート送信管理）*
  - execution/
    - broker_factory.py                  ブローカクライアント生成
    - execution_engine.py                実行時エンジン本体
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py               候補選定 / 重み計算
    - position_sizing.py                 発注株数計算
    - risk_adjustment.py                 セクターキャップ・レジーム乗数
  - research/
    - factor_research.py                 ファクター計算（momentum, volatility, value）
    - feature_exploration.py             IC / 統計サマリ
  - data/                                 （デフォルトデータディレクトリ）
    - monitoring.db (default: data/monitoring.db)
    - paper_trading.db (default: data/paper_trading.db)
  - utils/
    - logging_setup.py                   ログ初期化ユーティリティ
    - process_priority.py                プロセス優先度設定ユーティリティ

  * 一部ファイル名はここで省略している可能性があります（実行ロジックは上述の大局を参照してください）。

開発・拡張メモ
----------------
- DuckDB を用いたデータ処理は SQL と Python を混在して使えます。データパイプライン側で prices_daily / raw_financials / raw_news 等を用意しておく必要があります。
- AI（OpenAI）呼び出し部はユーティリティ関数をモックしやすく設計されており、ユニットテストで外部 API を差し替えることが容易です。
- 設定検証（validate_config）は PyYAML が無い場合は YAML 検証をスキップする実装です。config/*.yaml を用いる場合は PyYAML の導入を推奨します。

ライセンス / バージョン
-----------------------
- パッケージバージョンは kabusys.__version__ で管理（例: 0.1.0）
- ライセンス表記がこのコードベースに含まれていない場合はリポジトリルートの LICENSE を参照してください（存在する場合）。

問い合わせ・貢献
----------------
- 不具合や改善提案は Issue を立ててください。プルリクエスト歓迎です。
- 本 README はコードベースのヘルプ的ドキュメントです。詳細はソース内の docstring / コメントを参照してください。

以上。README の追加・改善希望や特定機能の詳細（例: ExecutionEngine の設定項目説明、TradeMonitor の仕様など）を教えていただければ追記します。