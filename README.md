KabuSys — 日本株自動売買システム（README）
======================================

概要
----
KabuSys は日本株向けの自動売買・バックテスト・リサーチ用のモジュール群です。  
本リポジトリは発注エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、ファクター計算、AI ベースのニュース NLP、ユーティリティスクリプト等を含みます。  
設計方針の特徴:
- 環境変数ベースで設定管理（.env ／ .env.local をサポート、起動時自動ロード）
- Paper Trading（ペーパートレード）モードと Live（本番）モードを分離
- DuckDB（時系列・ファクター計算）＋ SQLite（監視・発注ログ）
- OpenAI API を用いたニュースセンチメント / レジーム判定（オプション）
- ロギングは console + 日次ローテートファイルで統一

主な機能
----------
- ExecutionEngine 起動スクリプト（run_execution.py）
  - KABUSYS_ENV に応じて本番または paper_trading 専用 DB を使用
  - ブローカークライアント（実ブローカー / Mock）を透過的に切替
  - リスク管理・オーダー管理・reconciler を統合してセッション実行

- Monitoring（run_monitoring.py / monitoring package）
  - システムリソース、データ鮮度、発注ログ、リスク（ドローダウン / ポジション上限）を定期監視
  - kill.flag による緊急停止（Kill Switch）判定、アラート出力
  - 監視ログを SQLite に永続化

- Portfolio construction（portfolio package）
  - 候補選定、等金額 / スコア重み、ポジションサイズ算出、セクターキャップ、レジーム乗数等

- Research（research package）
  - DuckDB を使ったファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC（Information Coefficient）計算、ファクター統計

- AI（ai package）
  - ニュース記事を OpenAI でセンチメント付与し ai_scores に保存（news_nlp）
  - マクロ + ETF 200 日 MA を組み合わせた市場レジーム判定（regime_detector）

- ツール
  - .env 対話ウィザード: kabusys.config_setup (python -m kabusys.config_setup)
  - 設定検証 CLI: kabusys.validate_config (python -m kabusys.validate_config)
  - Paper Trading 検証レポート: kabusys.tools.paper_verification_report

必須・推奨依存
--------------
主な外部ライブラリ（実行に必要／推奨）:
- Python 3.9+
- duckdb
- psutil
- openai (AI 機能利用時)
- PyYAML（設定ファイル検証を行う場合に任意で必要）

インストール例（仮想環境）
- venv を使う例:
  python -m venv .venv
  source .venv/bin/activate
  pip install --upgrade pip
  pip install duckdb psutil openai PyYAML

セットアップ手順
----------------
1. リポジトリをクローン / 展開する
2. Python 仮想環境を作成し依存パッケージをインストール（上参照）
3. 初回設定 (.env) を作成:
   - 対話式で .env を作る:
     python -m kabusys.config_setup
   - あるいは .env.example を参考に手動作成
   - 自動ロードはデフォルトで有効。無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

4. 設定検証:
   python -m kabusys.validate_config
   --strict を付けると警告もエラー扱いで exit(1) になります。

主要な環境変数（抜粋）
--------------------
必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD     — kabuステーション API パスワード

任意 / デフォルト付き:
- KABUSYS_ENV           — 実行環境 (development|paper_trading|live)（default: development）
- DUCKDB_PATH           — DuckDB ファイルパス（default: data/kabusys.duckdb）
- SQLITE_PATH           — 監視用 SQLite（default: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード時の専用 SQLite（default: data/paper_trading.db）
- LOG_LEVEL             — ログレベル（DEBUG|INFO|...）（default: INFO）
- KABU_API_BASE_URL     — kabu API ベース URL（default: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — アラート通知（任意）
- OPENAI_API_KEY        — OpenAI API キー（AI 機能使用時に必要）
- PAPER_FILL_MODE       — paper_trading 時の約定挙動（instant|partial|never|reject）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、default: 60）
- KILL_FLAG_CLEAR_ON_START — 本番で起動時に kill_flag を自動クリアするか（0/1、default: 0）

ログ / フラグ / PID
-------------------
- ログ出力:
  - デフォルトは logs/<app_name>.log（日次ローテーション、30日保持）と stdout
  - app_name の例: "execution", "monitoring"

- フラグ・PID ファイル:
  - 停止フラグ: data/stop_requested.flag（run_execution/run_monitoring が存在を確認）
  - Kill Switch: data/kill.flag（KillSwitch が書き込み。Execution 起動時は存在確認される）
  - PID ファイル例: data/execution.pid

使い方（実行例）
----------------

- 環境セットアップ（対話式 .env を作る）
  python -m kabusys.config_setup

- 設定検証
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- 監視ループ起動（常駐プロセス）
  # デフォルト 60 秒ごとにチェック。MONITOR_POLL_INTERVAL で上書き可。
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

  run_monitoring の特徴:
  - 監視用 SQLite は Settings.sqlite_path を使用（環境に関係なく本番 path を参照）
  - data/stop_requested.flag が作られるとループを終了

- ExecutionEngine 起動（取引/ペーパートレード）
  # KABUSYS_ENV を指定して起動
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  KABUSYS_ENV=live python -m kabusys.run_execution

  実行時の挙動:
  - paper_trading 環境では MockBrokerClient を使用し data/paper_trading.db に記録（本番 DB と分離）
  - 起動時に data/stop_requested.flag が存在すると起動せず終了
  - 実行中に data/stop_requested.flag が作成されるとエンジン停止処理を行う

- Paper Trading 検証レポート生成
  python -m kabusys.tools.paper_verification_report
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  --db オプションまたは環境変数 PAPER_TRADING_SQLITE_PATH で DB パスを指定可能

- AI / レジーム判定 / ニューススコア（プログラムから呼び出す例）
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news
  conn = duckdb.connect("data/kabusys.duckdb")
  score_news(conn, target_date=date(2026,4,1), api_key="sk-...")

注意事項・運用上のポイント
------------------------
- run_monitoring は MONITOR_POLL_INTERVAL でポーリングします。0 以下は無効（デフォルト 60 秒）。
- run_monitoring は監視用 SQLite を本番 path で参照するため、監視専用 DB の取り扱いに注意してください。
- ExecutionEngine は paper_trading と live で DB を切り分けます（paper_trading 用 DB は PAPER_TRADING_SQLITE_PATH で設定）。
- Kill Switch（kill.flag）は一度書き込むと ExecutionEngine の起動や継続に影響します。KILL_FLAG_CLEAR_ON_START を 1 にすると起動時に自動クリアされますが、本番では 0 を推奨します。
- OpenAI を使うモジュールは API キーが必須です。API 呼び出しに失敗した場合はフェイルセーフ（デフォルト値）で継続する実装になっていますが、API 利用料やレート制限に注意してください。
- ログディレクトリ権限の設定によってファイルハンドラが作成できない場合はコンソール出力のみで継続します。

ディレクトリ構成（主要ファイル）
------------------------------
以下は src/kabusys 配下の主要モジュールと役割（抜粋）:

- __init__.py
- config.py            — 環境変数/設定読み込みと Settings クラス
- config_setup.py      — .env 対話ウィザード
- validate_config.py   — 起動前設定検証 CLI

- run_execution.py     — ExecutionEngine 起動スクリプト
- run_monitoring.py    — SystemMonitor ポーリングループ起動

- execution/            — 発注関連コンポーネント（Engine, OrderManager, BrokerFactory 等）
- monitoring/
  - monitoring_db.py    — SQLite 永続化層（system_status / trade_logs / positions / risk_logs / dashboard）
  - system_monitor.py   — システム状態・データ鮮度監視
  - trade_monitor.py    — 発注ログ監視（存在）
  - risk_monitor.py     — ドローダウン・ポジション上限監視
  - kill_switch.py      — kill.flag 制御
  - monitoring_engine.py— 各 Monitor を束ねるエンジン
  - alert_manager.py    — （アラート送信機能、存在）

- portfolio/
  - portfolio_builder.py — 候補選定 / 重み計算
  - position_sizing.py   — 発注株数計算（lot rounding / caps / scaling）
  - risk_adjustment.py   — セクターキャップ・レジーム乗数

- research/
  - factor_research.py   — Momentum / Volatility / Value のファクター計算（DuckDB）
  - feature_exploration.py — 将来リターン / IC / 統計サマリー

- ai/
  - news_nlp.py          — ニュースを OpenAI でスコア化して ai_scores に書き込む
  - regime_detector.py   — ETF MA + マクロニュースで市場レジームを判定

- tools/
  - paper_verification_report.py — ペーパートレードの検証レポート生成

- utils/
  - logging_setup.py     — 共通ログ設定
  - process_priority.py  — プロセス優先度 / CPU affinity 設定

data/, logs/（実行時に生成・使用）
- data/: デフォルト DB / フラグ / pid 等（例: data/monitoring.db, data/paper_trading.db, data/kill.flag, data/stop_requested.flag）
- logs/: ログファイル（<app_name>.log）

サポート・開発メモ
------------------
- YAML 設定ファイル（config/*.yaml）を持つ場合、validate_config は PyYAML があれば内容検証を行います。未インストールでもワーニングに留まります。
- 自動 .env ロード機能はプロジェクトルート（.git または pyproject.toml を検出）を基準に行います。テストで無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- テスト時は OpenAI 呼び出し関数をモックすることで外部 API 依存を外せます（各モジュール内で _call_openai_api を patch 可能）。

おわりに
--------
本 README はコードベースの主要な使い方と構成をまとめたものです。細かな実装仕様やアルゴリズムの根拠（PortfolioConstruction.md、StrategyModel.md 等の設計ドキュメント）が別途存在する想定です。運用開始前に必ず python -m kabusys.validate_config で設定を確認し、テスト環境で十分に挙動を確認してください。