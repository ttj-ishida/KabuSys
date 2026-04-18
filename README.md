KabuSys — 日本株自動売買システム（README）
=====================================

概要
----
KabuSys は日本株の自動売買・研究・監視を目的とした Python パッケージです。本リポジトリは以下の主要機能を含みます。

- 売買 ExecutionEngine（本番 / ペーパートレードの分離）
- 監視（System / Trade / Risk）と Kill Switch
- ポートフォリオ構築（候補選定・重み算出・ポジションサイジング・セクター制限）
- リサーチ（ファクター計算・特徴量探索）
- AI 製ニュース NLP（OpenAI を用いたセンチメント評価）
- 運用補助ツール（設定ウィザード、設定検証、ペーパートレード検証レポート等）

主な特徴
--------
- 環境別分離: KABUSYS_ENV により development / paper_trading / live を切替。ペーパートレードは本番 DB と分離（data/paper_trading.db 等）。
- 簡易な監視ループ: system/trade/risk を定期チェックしてログ（SQLite）へ永続化。条件に応じて data/kill.flag を書き込み ExecutionEngine を安全に停止。
- DuckDB を分析用 DB として利用（prices_daily, raw_financials 等の集計に使用）。
- OpenAI（gpt-4o-mini）を用いたニュースセンチメントのバッチ評価（API キー必須・失敗時はフォールバック処理）。
- ログは stdout と日次ローテートファイル（logs/<app>.log）に出力。ログレベルは環境変数で制御可。

前提 / 推奨環境
----------------
- Python 3.10+
- 必要パッケージ（例）
  - duckdb
  - psutil
  - openai
  - PyYAML（config の内容検証を行う場合）
- （推奨）仮想環境を作成して依存をインストールしてください。

セットアップ手順
----------------
1. リポジトリをクローンし、仮想環境を作成・有効化：
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール（プロジェクトの requirements.txt がある想定）:
   - pip install -r requirements.txt
   - ない場合は最低限 duckdb, psutil, openai を入れてください:
     - pip install duckdb psutil openai

3. .env を作成（対話式ウィザード推奨）:
   - python -m kabusys.config_setup
     - このウィザードは .env（デフォルト: プロジェクトルート/.env）を生成します。
   - 生成後は設定を検証:
     - python -m kabusys.validate_config
     - --strict を付けると警告も失敗扱いになります。

4. データディレクトリの準備:
   - デフォルトの DB / フラグ / PID ファイルは data/ 下に作成されます。必要に応じて .env でパスを変更してください。
   - ログはデフォルト logs/ に出力されます。

重要な環境変数（抜粋）
---------------------
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABUSYS_ENV: execution モード（development | paper_trading | live） デフォルト: development
- OPENAI_API_KEY: OpenAI を使用する機能（ai.score_news / regime_detector）で必須
- PAPER_FILL_MODE: ペーパートレード時の約定モード（instant | partial | never | reject）。デフォルト: instant
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR: ログ保存先（デフォルト: logs/）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1、本番では 0 推奨）

使い方（起動・主要コマンド）
----------------------------
- 環境構築・検証
  - python -m kabusys.config_setup         # .env の作成/更新ウィザード
  - python -m kabusys.validate_config      # 環境設定の検証 (--strict オプションあり)

- ExecutionEngine（本番/ペーパーの売買エンジン）起動
  - python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し、ペーパートレード DB（PAPER_TRADING_SQLITE_PATH）に書き込みます。
    - 起動時に data/stop_requested.flag が存在する場合は起動を行いません。
    - 停止は data/stop_requested.flag を作成することで行えます。
    - PID ファイルは data/execution.pid（デフォルト）に作成されます。

- Monitoring（定期監視）起動
  - python -m kabusys.run_monitoring
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（秒、デフォルト 60）。
    - 監視は監視 DB（Settings.sqlite_path）にログを残します（init_monitoring_db が自動作成）。
    - stop_requested.flag を検出するとループを終了します。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
    - PAPER_TRADING_SQLITE_PATH 環境変数で SQLite パスを指定可能。

- AI 関連（スクリプトとして単体起動はなし。関数呼び出しを通じて利用）
  - news_nlp.score_news(conn, target_date, api_key=None) — OpenAI API により銘柄別ニューススコアを ai_scores テーブルへ書込
  - regime_detector.score_regime(conn, target_date, api_key=None) — 市場レジーム判定を market_regime テーブルへ書込
  - どちらも OPENAI_API_KEY を環境変数として設定するか api_key を明示してください。

停止・Kill Switch の仕組み
-------------------------
- stop_requested.flag:
  - run_execution/run_monitoring はプロジェクトの data/stop_requested.flag を監視しており、存在すると安全に停止します（運用中の即時停止等に使用）。
- kill.flag:
  - KillSwitch は条件（ドローダウン超過、ポジション上限など）を満たすと data/kill.flag を書き込みます。ExecutionEngine は起動時にこれを検出することで発注を停止します。
  - KILL_FLAG_CLEAR_ON_START=1 に設定すると起動時に自動クリアします（本番では 0 推奨）。

ログ
----
- setup_logging によって root ロガーは stdout と日次ローテートファイル（logs/<app_name>.log）へ出力されます。
- LOG_LEVEL / LOG_DIR 環境変数で制御できます。

DB 初期化
---------
- run_* スクリプト起動時に init_monitoring_db が呼ばれ、監視用テーブルが作成されます（冪等）。
- DuckDB ファイルは分析・リサーチ用途で使用されます（prices_daily / raw_financials 等のテーブルを想定）。

ディレクトリ構成（主要ファイル・用途）
------------------------------------
以下は src/kabusys 配下の主要モジュールの一覧と簡単な説明です（抜粋）。

- __init__.py
  - パッケージ定義（__version__ 等）

- run_execution.py
  - ExecutionEngine の起動スクリプト（スレッド実行、PID/stop フラグの取り扱い、paper_trading 分離）

- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL で設定可能）

- config.py
  - Settings クラス：環境変数 / .env の読み込みと設定値取得ロジックを提供
  - 自動 .env ロード (.env, .env.local) をサポート（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可）

- config_setup.py
  - .env 対話式ウィザード（対話入力で .env を生成）

- validate_config.py
  - 起動前チェック CLI（必須環境変数や config/*.yaml の存在・簡易検証）

- utils/
  - logging_setup.py: ログ設定ユーティリティ（stdout + TimedRotatingFileHandler）
  - process_priority.py: プロセス優先度・CPU affinity 設定（psutil 使用）
  - その他ユーティリティ収容

- monitoring/
  - monitoring_db.py: SQLite を使う永続層（テーブル作成・CRUD ヘルパ）
  - system_monitor.py: システム状態・データ鮮度チェック
  - trade_monitor.py: 発注 / 約定の健全性チェック（滞留注文・異常約定など）
  - risk_monitor.py: ドローダウン・ポジション上限監視
  - kill_switch.py: kill.flag の評価・書き込み
  - monitoring_engine.py: 監視モジュールを束ねるランナー
  - alert_manager.py: （通知管理。LINE/他の通知機能を想定）

- execution/
  - execution_engine.py, order_manager, order_repository, reconciler, risk_manager, broker_factory
  - Execution の実装（Broker クライアントの抽象化・ペーパー/本番対応）

- portfolio/
  - portfolio_builder.py: 候補選定・重み算出（等配分・スコア加重）
  - position_sizing.py: 発注株数計算（risk_based / equal / score）
  - risk_adjustment.py: セクター上限・レジーム乗数

- research/
  - factor_research.py: Momentum / Volatility / Value 等のファクター計算（DuckDB 経由）
  - feature_exploration.py: 将来リターン計算・IC 計算・統計要約

- ai/
  - news_nlp.py: ニュース記事を LLM でスコアリングし ai_scores を更新
  - regime_detector.py: ETF の MA 乖離 + マクロ NLP で市場レジーム判定

- tools/
  - paper_verification_report.py: ペーパートレード DB を解析して検証レポートを出力

補足・運用上の注意
------------------
- .env は機密情報を含むため絶対に Git にコミットしないでください（config_setup にもその旨注意書きあり）。
- 本番（KABUSYS_ENV=live）では kill.flag の自動クリアや設定値に注意してください（validate_config は live の場合に追加警告を出します）。
- OpenAI を使う機能は API コスト・レイテンシが発生します。API キーは安全に管理してください。
- DuckDB / SQLite のパスは複数プロセスで共有するとロック等の問題が発生する場合があります。特に書き込みが多い場合は運用設計に注意してください。

開発者向け
----------
- テストや CI では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動的な .env 読込を無効化できます。
- モジュール設計は副作用をなるべく抑え、DB 書き込みは各レポジトリ/DB 層で管理する方針です。
- OpenAI API 呼び出し部分はリトライ・バックオフ・レスポンスバリデーションを備えています。テストでは _call_openai_api をモックしてください。

ライセンス / 貢献
-----------------
README にライセンス情報は含めていません。実運用・配布の際は適切なライセンス・貢献規約を付与してください。

最後に
-----
この README はソースの主要部分から要点を抽出してまとめたものです。実行時の詳細な挙動や追加のユーティリティはソースコードの該当ファイル（monitoring/*.py, execution/*.py, ai/*.py など）を参照してください。必要であれば README を拡張してコマンド例や運用手順（systemd / supervisor 用の unit ファイル例、バックアップ方針など）を加えます。希望があれば教えてください。