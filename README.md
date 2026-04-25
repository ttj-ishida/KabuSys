KabuSys — 日本株自動売買システム (README)
=========================================

概要
----
KabuSys は日本株の自動売買・調査・監視を目的とした Python パッケージ群です。  
主な責務は以下の通りです。

- 注文実行エンジン（ExecutionEngine）と発注管理
- 監視サブシステム（System / Trade / Risk）と Kill Switch
- ポートフォリオ構築・ポジションサイズ計算（純関数群）
- リサーチ用ファクター計算（DuckDB を利用）
- ニュース NLP によるセンチメント評価・レジーム判定（OpenAI）
- ペーパートレード検証レポート生成ツール

このリポジトリは、実運用（live）、ペーパートレード（paper_trading）、開発（development）を切り替え可能な設計になっています。

主な機能
--------
- Execution
  - 実際のブローカークライアントまたはモッククライアント（KABUSYS_ENV=paper_trading）での発注処理
  - OrderManager, Reconciler, RiskManager 等を組み合わせた ExecutionEngine
- Monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - system_status / trade_logs / risk_logs / positions / dashboard の永続化（SQLite）
  - KillSwitch による停止フラグ（data/kill.flag）の作成
  - stop_requested.flag による安全な停止（data/stop_requested.flag）
- Portfolio
  - 候補選定、等重・スコア加重配分、リスクに基づくポジションサイズ計算
  - セクター上限適用、レジームに応じた乗数
- Research
  - DuckDB 上の prices_daily/raw_financials を用いたモメンタム／ボラティリティ／バリュー計算
  - 将来リターン、IC（情報係数）計算、統計サマリ
- AI
  - ニュース記事を OpenAI に送信して銘柄ごとのセンチメント（ai_scores）を生成
  - マクロニュースと ETF MA を組み合わせた市場レジーム判定（market_regime）
- ユーティリティ
  - .env 対話式ウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py）
  - ペーパートレード検証レポート生成ツール（tools/paper_verification_report.py）
  - 統一的なログ設定（utils.logging_setup）

セットアップ手順
----------------
前提
- Python 3.10 以上を推奨（型注釈に新しい構文を使用）
- SQLite は標準ライブラリに含まれます
- DuckDB を利用するため duckdb パッケージが必要

インストール（例）
1. 仮想環境作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate (Linux/macOS) または .venv\Scripts\activate (Windows)
2. 必要パッケージをインストール
   - pip install duckdb psutil openai
   - PyYAML は設定ファイルの YAML 検証に任意で必要: pip install PyYAML

設定ファイルの作成
1. 対話式ウィザードで .env を作る（推奨）
   - python -m kabusys.config_setup
   - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
   - KABUSYS_ENV は development / paper_trading / live のいずれか
2. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit code 1）

データディレクトリ
- デフォルトの DB / ファイルはプロジェクトルートの data/ に作られます:
  - DuckDB: data/kabusys.duckdb (環境変数: DUCKDB_PATH)
  - Monitoring SQLite: data/monitoring.db (SQLITE_PATH)
  - Paper trading DB: data/paper_trading.db (PAPER_TRADING_SQLITE_PATH)
- ログ: logs/ ディレクトリ（LOG_DIR で変更可能）

使い方
------
主要な起動スクリプト・CLI

- 環境ウィザード（.env を生成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine を起動（本番 / ペーパー両対応）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、ペーパートレード用 DB（PAPER_TRADING_SQLITE_PATH）へ記録します
  - 実行中に data/stop_requested.flag を作成すると安全に停止します
  - Execution 起動時に pid ファイルを書き込む（Settings.pid_file_path）

- Monitoring を起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60 秒）
  - モニタリングは常に本番用 sqlite_path（Settings.sqlite_path）を使用して監視ログを書き込みます
  - data/stop_requested.flag により停止できます

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH（PAPER_TRADING_SQLITE_PATH 環境変数より優先）
  - 出力: 稼働率・注文成功率・レイテンシ等のサマリと PASS/FAIL 判定

環境変数（主なもの）
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 運用系:
  - KABUSYS_ENV: development | paper_trading | live
  - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL
  - LOG_DIR: ログ出力ディレクトリ（デフォルト: logs）
- DB パス:
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (監視用、デフォルト: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB、デフォルト: data/paper_trading.db)
- AI:
  - OPENAI_API_KEY（news_nlp / regime_detector が必要な場合）
- その他:
  - MONITOR_POLL_INTERVAL（run_monitoring のポーリング秒数）
  - KILL_FLAG_CLEAR_ON_START（Execution 起動時に kill.flag を自動クリアするか、"1" で有効）

停止 / Kill Switch
- 監視や実行の停止は主に次の方法で行われます:
  - data/stop_requested.flag を作成すると run_execution/run_monitoring のループが検知して安全停止します
  - KillSwitch（監視側）は条件に応じて data/kill.flag を書き込み、ExecutionEngine に停止を促します
  - KILL_FLAG_CLEAR_ON_START=1 に設定すると起動時に kill.flag を自動クリアできます（本番では 0 推奨）

開発者向け / ライブラリ利用例
- リサーチ関数（DuckDB 接続を渡して使用）
  - 例:
    - from kabusys.research import calc_momentum, calc_volatility, calc_value
    - conn = duckdb.connect("data/kabusys.duckdb")
    - calc_momentum(conn, target_date)
- ポートフォリオ関数（純関数）
  - from kabusys.portfolio import select_candidates, calc_equal_weights, calc_position_sizes
  - 関数は DB に依存しないメモリ内計算を行います

ディレクトリ構成（主要ファイル）
--------------------------------
src/kabusys/
- __init__.py
- config.py                  — 環境変数・設定管理（.env 自動ロード含む）
- config_setup.py            — .env 対話ウィザード
- validate_config.py         — 設定検証 CLI
- run_execution.py           — ExecutionEngine 起動スクリプト
- run_monitoring.py          — Monitoring 起動スクリプト

subpackages:
- ai/
  - news_nlp.py              — ニュースを OpenAI でスコアリングして ai_scores に書込む
  - regime_detector.py       — ETF MA + マクロニュースで市場レジーム判定
- monitoring/
  - monitoring_engine.py     — 各 Monitor を束ねる
  - system_monitor.py        — システム状態・データ鮮度監視
  - trade_monitor.py         — (trade 監視ロジック)
  - risk_monitor.py          — ドローダウン・ポジション上限監視
  - monitoring_db.py         — SQLite 永続化レイヤ（init / MonitoringDB）
  - kill_switch.py           — kill.flag 書き込みユーティリティ
  - alert_manager.py         — （通知管理: LINE 等、実装箇所参照）
- execution/
  - execution_engine.py      — ExecutionEngine (起動・セッション管理)
  - order_manager.py         — 注文管理
  - order_repository.py      — DB リポジトリ
  - risk_manager.py          — Risk 管理ロジック
  - broker_factory.py        — BrokerClient の生成（本番 / mock 切替）
  - reconciler.py            — 注文整合処理
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- tools/
  - paper_verification_report.py
- utils/
  - logging_setup.py         — 共通ログ設定ユーティリティ
  - process_priority.py      — プロセス優先度 & CPU affinity ユーティリティ

注意事項 / 運用上のヒント
-----------------------
- .env は機密情報（API トークン等）を含むため絶対にリポジトリへコミットしないでください。
- 本番環境（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START を 0 にしておくことを推奨します。
- OpenAI を利用する機能は API 料金が発生します。API キー・利用頻度には注意してください。
- DuckDB / SQLite のファイルはバックアップやアクセス権を適切に管理してください。
- サービス実行は systemd / supervisor / コンテナ を使って常駐させることを推奨します。run_* スクリプトはプロセス優先度を高める処理を行います（set_process_priority("high")）。

その他
-----
- 設定や挙動の詳細はソース内の docstring / コメントに解説を多く含めています。実装の理解や拡張はソースを参照してください。
- YAML 設定ファイル（config/*.yaml）テンプレート生成用スクリプト等があれば README を更新して手順を追記してください。

問題報告 / 貢献
----------------
- 不具合や改善提案は Issue を作成してください。プルリクエスト歓迎します。

以上。必要があれば README に含めるサンプル .env、systemd ユニットファイルの例、実行例を追記します。どの情報が欲しいか教えてください。