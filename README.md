README — KabuSys
=================

概要
----
KabuSys は日本株向けの自動売買／リサーチ基盤の一部を提供する Python パッケージです。本リポジトリは以下の主要機能を含みます:

- ExecutionEngine（発注実行エンジン）およびそれに関連するオーダー管理、リスク管理、リコンシリエーション
- Monitoring（システム監視）: プロセス稼働状況・データ鮮度・リスク（ドローダウン、ポジション上限等）の定期チェック
- Portfolio Construction（候補選定・重み付け・株数決定）用の純粋関数群
- Research（ファクター計算・特徴量探索）
- AI 支援モジュール（ニュースを LLM でスコアリング、レジーム判定）
- 各種ユーティリティ（ログ設定、プロセス優先度設定、設定ウィザード/検証ツール、ツールスクリプト）

本 README はコードベースの主要な使い方・セットアップ・ディレクトリ構成の概要を示します。

主な機能
--------
- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動（paper_trading モードでは MockBroker を使用して paper DB に記録）
  - run_monitoring.py: SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で間隔指定可）
- 設定管理
  - config_setup.py: .env の生成・対話ウィザード
  - validate_config.py: .env と config/*.yaml の検証（--strict オプションあり）
  - Settings クラスにより環境変数を集中管理（自動で .env/.env.local をロード、無効化可）
- 監視・アラート
  - monitoring モジュール: system/trade/risk 各モニタ、KillSwitch、MonitoringEngine、監視 DB（SQLite）
  - kill.flag による ExecutionEngine 停止シグナル、stop_requested.flag によるスレッド停止
- ポートフォリオ構築
  - 候補選定、等重・スコア重み、ポジションサイズ計算（単元株丸め、リスク・集約上限を考慮）
- リサーチ
  - DuckDB を用いたファクター計算（Momentum/Value/Volatility 等）、将来リターン、IC 計算など
- AI
  - ニュースのセンチメントスコア化（OpenAI を利用。api_key 必須）
  - レジーム判定モジュール（ETF + LLM を合成して bull/neutral/bear を算出）
- ツール
  - tools/paper_verification_report.py: ペーパートレードの検証レポート生成

前提（推奨）
-----------
- Python 3.10 以上（typing の | 記法などを使用）
- SQLite（組み込み）
- 必要パッケージ:
  - duckdb
  - psutil
  - openai（AI 機能を使う場合）
  - PyYAML（config YAML 検証を行う場合。任意）
インストール例:
  python -m pip install duckdb psutil openai pyyaml

セットアップ手順
----------------
1. リポジトリを取得
   - git clone ... してローカルに展開

2. 仮想環境を作成（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install duckdb psutil openai pyyaml

4. .env の作成（推奨）
   - python -m kabusys.config_setup
   - ウィザードが .env を生成します。.env は絶対に Git にコミットしないでください。

5. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱いになります。

主要な環境変数（抜粋）
---------------------
- KABUSYS_ENV: 実行環境（development / paper_trading / live）。デフォルト: development
  - paper_trading の場合、MockBroker を用いて data/paper_trading.db に記録され、本番 DB と分離されます。
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI を利用する際に必須（ai/news_nlp, ai/regime_detector 等）
- PAPER_FILL_MODE: paper_trading の約定モード（instant | partial | never | reject）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- LOG_LEVEL / LOG_DIR: ログ設定（logs/<app_name>.log 日次ローテート）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動クリア（1 にすると自動クリア。production は 0 を推奨）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒。デフォルト: 60）

起動と使い方
------------

- ExecutionEngine の起動
  - python -m kabusys.run_execution
  - 振る舞い:
    - KABUSYS_ENV=paper_trading のときは paper DB を使用（Settings.paper_sqlite_path）
    - 起動時に data/stop_requested.flag が既に存在する場合は起動せず終了
    - 実行中に data/stop_requested.flag が作成されると Engine.stop() を呼んでシャットダウン
    - execution.pid ファイル（デフォルト data/execution.pid）を出力

- Monitoring の起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可（秒）
  - 監視は本番 sqlite_path を環境にかかわらず参照して監視情報を永続化
  - run_monitoring は data/stop_requested.flag の存在で監視ループを終了する

- 停止・Kill Switch
  - KillSwitch は監視モジュールから条件達成時に data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送ります（Execution 側は kill.flag の存在で適切に停止処理を行います）
  - 管理者が明示的に停止させたい場合は data/stop_requested.flag を作成して両プロセスを止めることができます（run_* スクリプトが参照）

- ログ
  - デフォルト出力先: logs/<app_name>.log（TimedRotatingFileHandler により日次ローテート、30 日保持）
  - コンソール出力は stdout（stderr ではない）

- Paper Trading の検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB は data/paper_trading.db で、環境変数 PAPER_TRADING_SQLITE_PATH で指定可能

- AI 機能の利用
  - ai/news_nlp.score_news(conn, target_date, api_key=None) などの関数を呼ぶことでニューススコアを ai_scores テーブルに書き込み
  - api_key が None の場合は環境変数 OPENAI_API_KEY を参照
  - API 呼び出しはリトライや入力トリム・JSON バリデーション処理を含む

注意点 / 運用上のヒント
-----------------------
- .env は機密情報を含むため絶対にリポジトリへ含めないこと
- 本番（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START=0 を推奨。自動クリアは危険
- validate_config で設定漏れ・ファイルパスの親ディレクトリ確認等を事前に検出してください
- AI 機能は OpenAI API キーとクォータが必要。API 呼び出し失敗時はフェイルセーフで処理を継続する設計ですが、ログを確認してください
- プロセス優先度設定（set_process_priority）は OS によって挙動が異なり、権限不足で設定に失敗することがあるためログで確認してください
- DuckDB（分析用）と SQLite（監視・注文履歴）は別ファイルとして扱われます（設定でパス指定可）

ディレクトリ構成（主要ファイル）
-------------------------------
src/kabusys/
- __init__.py — パッケージ定義、バージョン
- config.py — Settings クラス（環境変数 / .env 自動ロード）
- config_setup.py — .env 対話ウィザード
- validate_config.py — 起動前設定検証 CLI
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — SystemMonitor 起動スクリプト

src/kabusys/utils/
- logging_setup.py — 共通ログ設定ユーティリティ
- process_priority.py — プロセス優先度 / CPU affinity 設定

src/kabusys/monitoring/
- monitoring_db.py — SQLite テーブル初期化・永続化層
- system_monitor.py, trade_monitor.py, risk_monitor.py — 各監視ロジック
- monitoring_engine.py — 監視ループ束ねクラス
- kill_switch.py — kill.flag 操作
- alert_manager.py — （アラート送信の抽象化: 実装に応じて LINE 等を呼ぶ想定）

src/kabusys/execution/
- execution_engine.py — 実行エンジン本体
- order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py — 実行関連コンポーネント（Broker と統合）

src/kabusys/portfolio/
- portfolio_builder.py — 候補選定・重み計算
- position_sizing.py — 株数決定、aggregate cap 処理
- risk_adjustment.py — セクターキャップ・レジーム乗数

src/kabusys/research/
- factor_research.py — ファクター計算（momentum/value/volatility）
- feature_exploration.py — 将来リターン / IC /統計サマリー

src/kabusys/ai/
- news_nlp.py — ニュースセンチメント（OpenAI）
- regime_detector.py — マクロ + ETF MA によるレジーム判定

src/kabusys/tools/
- paper_verification_report.py — ペーパートレード検証レポート生成

データ・ログ
- data/ — デフォルトの DB・PID・フラグファイルを置く場所（例: data/monitoring.db, data/paper_trading.db, data/execution.pid, data/kill.flag, data/stop_requested.flag）
- logs/ — ログ出力ディレクトリ（app_name ごとに日次ローテート）

ライセンス・貢献
----------------
- 本 README のライセンスはリポジトリのルートにある LICENSE を参照してください。
- バグ報告・プルリクエストはリポジトリの issue / PR を通じてお願いします。

付録: よく使うコマンド例
-----------------------
- .env 作成ウィザード:
  python -m kabusys.config_setup

- 設定検証:
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- Execution 起動:
  python -m kabusys.run_execution

- Monitoring 起動:
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- ペーパートレード検証レポート:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

最後に
------
本 README はコードベース（src/kabusys/*.py）をもとに作成しています。詳細実装・追加オプションは各モジュールの docstring / ソースを参照してください。質問や補足があれば教えてください。