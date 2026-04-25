KabuSys — 日本株自動売買システム
=================================

このリポジトリは日本株の自動売買システム（KabuSys）のコードベースです。
トレーディング実行エンジン、監視・アラート、ポートフォリオ構築、ファクター計算、
および AI を用いたニュース NLP / レジーム判定などのコンポーネントを含みます。

以下は本コードベースの概要、機能、セットアップ手順、使い方、ディレクトリ構成の説明です。

プロジェクト概要
----------------
KabuSys は以下のような機能群を持つ自動売買プラットフォームです。

- データ格納・分析用に DuckDB を使用
- 監視・ロギング用に SQLite（monitoring.db）を使用
- ExecutionEngine によりブローカーへ発注を行う（paper_trading モードあり）
- ポートフォリオ構築（候補選定・重み付け・株数決定・セクター制限）
- リスク管理（ドローダウン監視・ポジション上限）
- 監視エンジン（System / Trade / Risk の統合、Kill Switch）
- AI モジュール（OpenAI を用いたニュースセンチメント、レジーム判定）
- 開発支援ツール（.env ウィザード、設定検証、ペーパートレード検証レポート）

主な特徴
-------
- モジュール化された純粋関数群（ポートフォリオ構築、リスク調整、ポジションサイジング）
- DuckDB を利用したデータ分析・ファクター計算（prices_daily / raw_financials 等）
- OpenAI を用いたニュースセンチメント（ai.news_nlp）およびレジーム判定（ai.regime_detector）
- 監視と自動停止（Kill Switch）による安全弁
- paper_trading モードでは発注をモック化し、本番 DB と完全分離

セットアップ手順
----------------

前提
- Python 3.10 以上を推奨（typing 機能や型注釈を使用）
- OS: Linux / macOS / Windows（ただし process priority / cpu affinity はプラットフォーム差あり）

1. リポジトリを取得
   - git clone ... またはアーカイブ展開

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  または  .venv\Scripts\activate

3. 必須パッケージをインストール
   - （requirements.txt が用意されている場合）pip install -r requirements.txt
   - 最低限の依存例:
     - pip install duckdb psutil openai PyYAML
   - テストや開発で追加パッケージが必要な場合があるので適宜追加してください。

4. .env を作成（ウィザード推奨）
   - python -m kabusys.config_setup
   - 対話式に必要な環境変数を設定します。
   - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
   - OpenAI を使う場合: OPENAI_API_KEY を設定

5. 設定検証（起動前に実行推奨）
   - python -m kabusys.validate_config
   - --strict オプションを付けると警告も失敗扱いになります。

主要な環境変数（代表）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL
- DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
- SQLITE_PATH: data/monitoring.db（監視 DB、デフォルト）
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用）
- PAPER_FILL_MODE: instant | partial | never | reject（paper_trading の約定動作）
- OPENAI_API_KEY: OpenAI API キー（AI モジュールで必要）
- LOG_DIR: ログファイル保存先（デフォルト: logs/）
- KILL_FLAG_CLEAR_ON_START: 1|0（本番では 0 推奨）

使い方（主要コマンド）
--------------------

1. 環境作成ウィザード
   - python -m kabusys.config_setup
   - .env を生成・更新します（.env は Git にコミットしないでください）。

2. 設定検証
   - python -m kabusys.validate_config
   - 問題がある箇所を検出します。

3. 実行エンジン起動（ExecutionEngine）
   - python -m kabusys.run_execution
   - 起動時に Settings に基づき paper_trading ならモックブローカーを使用し PAPER_TRADING_SQLITE_PATH に記録します。
   - 起動前に data/stop_requested.flag が存在すると起動せず終了します。
   - 停止は data/stop_requested.flag を作ることで行えます（run scripts はこのフラグを監視）。

4. 監視ループ起動（Monitoring）
   - python -m kabusys.run_monitoring
   - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書きできます（デフォルト: 60 秒）。
   - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path（Settings.sqlite_path）を使用します。
   - 停止は data/stop_requested.flag を作成。

5. ペーパートレード検証レポート
   - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
   - PAPER_TRADING_SQLITE_PATH、または --db で DB パスを指定できます。

6. AI 関連
   - ai.news_nlp.score_news(conn, target_date, api_key=None) — DuckDB 接続を渡してニューススコアを算出・ai_scores テーブルへ書き込み
   - ai.regime_detector.score_regime(conn, target_date, api_key=None) — レジームを計算して market_regime テーブルへ書き込み
   - これらは Python から直接呼び出すか、適宜スクリプトを作成して実行します。
   - OpenAI API の呼び出しには OPENAI_API_KEY が必要です。

運用上の注意
- .env は絶対に Git にコミットしないでください（APIキー・パスワードを含む）。
- 本番環境（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START=0 を推奨します。
- 監視ループは monitoring 用の sqlite_path を使います（run_monitoring は environment にかかわらず本番 sqlite_path を参照します）。
- run_execution は paper_trading の場合 paper_sqlite_path を使用して本番 DB と分離します。
- ログは logs/<app_name>.log に日次ローテーションで保存されます（デフォルト logs ディレクトリ）。

停止・再起動
- 停止フラグ: data/stop_requested.flag（run_monitoring / run_execution が存在を検知して終了）
- Kill Switch: data/kill.flag（KillSwitch が作成する停止シグナル。ExecutionEngine 側で扱う）
- kill.flag をクリアするには: rm data/kill.flag（Settings.kill_flag_clear_on_start=1 の場合起動時に自動クリアされることがあるため本番では注意）

ディレクトリ構成（抜粋）
-----------------------

src/kabusys/
- __init__.py
- config.py
  - Settings クラス: 環境変数の解決・検証ロジック
- config_setup.py
  - .env 対話式ウィザード
- validate_config.py
  - 起動前チェックツール
- run_execution.py
  - ExecutionEngine 起動スクリプト（paper_trading モード対応）
- run_monitoring.py
  - SystemMonitor ポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL）
- utils/
  - logging_setup.py — ログ設定（console + 日次ローテートファイルハンドラ）
  - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ
- monitoring/
  - monitoring_db.py — SQLite スキーマ定義と永続化 API（MonitoringDB）
  - system_monitor.py — システム状態・データ鮮度監視
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - trade_monitor.py — （trade 監視ロジック）
  - kill_switch.py — kill.flag の作成 / 評価
  - monitoring_engine.py — 各 Monitor をまとめるエンジン
  - alert_manager.py — （アラート送信ロジック）
- execution/
  - execution_engine.py — ExecutionEngine 実装（発注ループ等）
  - broker_factory.py — Broker クライアントの生成（モック含む）
  - order_manager.py / order_repository.py / reconciler.py / risk_manager.py — 発注管理関連
- portfolio/
  - portfolio_builder.py — 候補選定・重み計算
  - position_sizing.py — 株数決定・スケーリング・単元丸め
  - risk_adjustment.py — セクター上限・レジーム乗数
- research/
  - factor_research.py — Momentum / Volatility / Value ファクター計算（DuckDB）
  - feature_exploration.py — 将来リターン / IC / 統計サマリー等
- ai/
  - news_nlp.py — ニュースセンチメント（OpenAI）および ai_scores 書き込み
  - regime_detector.py — レジーム判定（MA200 + マクロニュース）
- tools/
  - paper_verification_report.py — ペーパートレード検証レポート生成ツール
- data/ （ランタイムで生成する想定）
  - monitoring.db（デフォルト SQLITE_PATH）
  - kabusys.duckdb（デフォルト DUCKDB_PATH）
  - paper_trading.db（PAPER_TRADING_SQLITE_PATH のデフォルト）
  - execution.pid / stop_requested.flag / kill.flag など制御ファイル

API / コード上の主要ポイント（補足）
- Logging: kabusys.utils.logging_setup.setup_logging を全起動スクリプトで使用して一貫したログ設定を行います。
- Process priority: 起動時に set_process_priority("high") を呼び出します（権限により失敗しても警告で継続）。
- MonitoringDB.init_monitoring_db は冪等にテーブルとカラムのマイグレーションを行います。
- news_nlp と regime_detector は OpenAI API 呼び出しを行い、429/ネットワーク断/5xx を対象に指数バックオフでリトライします。API キーは OPENAI_API_KEY を使用。

よくある操作例
-------------
- ウィザードで .env を作る:
  - python -m kabusys.config_setup
- 設定チェック（問題がなければ 0 が返る）:
  - python -m kabusys.validate_config
- 実行エンジン（ペーパートレード）を起動:
  - export KABUSYS_ENV=paper_trading
  - python -m kabusys.run_execution
- 監視ループを起動（ポーリング 30 秒）:
  - export MONITOR_POLL_INTERVAL=30
  - python -m kabusys.run_monitoring
- ペーパートレードの検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

ライセンス・注意
----------------
- 本 README はコードベースの概要説明です。実運用の前に必ず validate_config とユニットテストを実行し、安全策（Kill Switch やアラート設定）を確認してください。
- 実際のマネーを動かす場合は、リスク管理設定・ログ監視・オフライン検証を十分に行ってください。

問題報告・貢献
--------------
バグ報告や機能提案は Issue を立ててください。贡献する場合は PR を送付してください。

以上。必要であれば README に含めたい追加のコマンド例や環境変数の例（.env サンプル）を作成します。どの形式がよいか教えてください。