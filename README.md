KabuSys
=======

日本株向けの自動売買・リサーチ基盤（プロジェクト断片）。  
このリポジトリはトレード実行エンジン、監視・アラート、ポートフォリオ構築、リサーチ、AI（ニュースセンチメント）等のコンポーネントを含むモジュール群で構成されています。

概要
----
KabuSys は以下を目的としたモジュール群です。

- 日次／オンデマンドでの銘柄選定・配分計算（portfolio）
- 発注管理・リスク管理を行う ExecutionEngine（execution）
- システム状態や注文状況を定期監視し、Kill Switch を発動できる監視サブシステム（monitoring）
- DuckDB を用いたファクター計算・リサーチ機能（research）
- OpenAI（LLM）を利用したニュースセンチメント評価・レジーム判定（ai）
- ペーパートレード用の検証レポート生成ツール（tools）
- 設定ウィザード・検証ツール（config_setup、validate_config）
- 共通ユーティリティ（utils）

主な特徴・機能
--------------
- ExecutionEngine を本番 / ペーパートレード（完全分離 DB）で実行可能
- 監視ループ（SystemMonitor / TradeMonitor / RiskMonitor）により稼働率・データ鮮度・リスクを監視
- Kill Switch により条件（例: ドローダウン超過・ポジション上限超過）で Execution を停止
- DuckDB を利用したファクター計算（モメンタム、ボラティリティ、バリュー等）
- OpenAI を用いたニュース NLP（銘柄別センチメント）・レジーム判定（gpt-4o-mini 想定）
- ログはコンソール（stdout）と日次ローテートファイル（logs/<app>.log）に出力
- .env ベースの環境設定（config_setup による対話式生成、validate_config による検証）

セットアップ手順
----------------

前提
- Python 3.10+（typing / 型ヒントを利用）
- pip と仮想環境運用を推奨

1. リポジトリをクローンし、仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 依存ライブラリをインストール
   - requirements.txt が存在する場合:
     - pip install -r requirements.txt
   - 本コードで想定される主な依存:
     - duckdb, psutil, openai, pyyaml（設定検証で任意）

3. .env を作成
   - 対話式ウィザード（推奨）:
     - python -m kabusys.config_setup
   - もしくは .env.example を参考に直接作成
   - 自動読み込み: プロジェクトルートに .env / .env.local があると自動で読み込まれます（無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1）

4. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱い（exit 1）

5. 必須環境変数（主なもの）
   - JQUANTS_REFRESH_TOKEN（必須）
   - KABU_API_PASSWORD（必須）
   - OPENAI_API_KEY（AI 機能を使う場合）
   - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL（例: INFO, DEBUG）
   - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH（監視 DB。デフォルト: data/monitoring.db）
   - PAPER_TRADING_SQLITE_PATH（ペーパートレード専用 DB。デフォルト: data/paper_trading.db）
   - その他は config_setup で説明があります

使い方
-------

起動系スクリプト
- 監視ループ（Monitoring）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）
  - 監視は常に本番 sqlite_path を使用（環境にかかわらず）

- 実行エンジン（ExecutionEngine）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient が使われ data/paper_trading.db に記録
  - 起動時に data/stop_requested.flag が存在すると起動をスキップ
  - 実行中に stop flag を書くとエンジンを停止（stop フラグは data/stop_requested.flag）

設定関連
- 対話式作成:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config [--strict]

ツール
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH（PAPER_TRADING_SQLITE_PATH より優先）
  - デフォルト DB パス: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH 環境変数で上書き可）

AI / LLM 機能
- AI 機能（ニューススコアリング / レジーム判定）を利用する場合は OPENAI_API_KEY を設定してください。
- ニュース NLP は raw_news, news_symbols, ai_scores テーブルへ書き込みを行います。
- LLM 呼び出しはリトライロジックを内蔵し、失敗時はフェイルセーフで続行する設計です。

ログ / PID / フラグファイル
- ログ:
  - デフォルト: logs/<app_name>.log（日次ローテーション、30 日保持）
  - LOG_DIR 環境変数で変更可能
  - ログレベル: LOG_LEVEL（デフォルト INFO）
- PID / stop フラグ:
  - data/execution.pid（ExecutionEngine の PID 保存先、Settings.pid_file_path）
  - data/stop_requested.flag（run_* スクリプトがチェックする停止フラグ）
  - data/kill.flag（KillSwitch が書き込む停止指示ファイル。Settings.kill_flag_path）
  - KILL_FLAG_CLEAR_ON_START=1 により起動時に自動クリアする（本番では 0 推奨）

ディレクトリ構成（主なファイル説明）
----------------------------------

src/kabusys/
- __init__.py
- config.py
  - 環境変数の読み込み・Settings クラス（.env 自動ロードロジック含む）
- config_setup.py
  - .env を対話式に作るウィザード
- validate_config.py
  - .env / config/*.yaml の起動前検証 CLI
- run_execution.py
  - ExecutionEngine の起動スクリプト（本番 / ペーパー判定、PID/STOP 管理）
- run_monitoring.py
  - SystemMonitor ポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL 対応）

サブパッケージ
- ai/
  - news_nlp.py : OpenAI を使ったニュースセンチメント評価
  - regime_detector.py : マクロ + ETF MA から市場レジーム判定
- monitoring/
  - monitoring_db.py : SQLite 監視 DB のスキーマ・読み書き層
  - system_monitor.py : CPU/メモリ/ディスク/データ鮮度・プロセス監視
  - trade_monitor.py : （コード断片内にある想定モジュール）発注系モニタ
  - risk_monitor.py : ドローダウン・ポジション数監視
  - kill_switch.py : Kill Switch 書き込みロジック
  - monitoring_engine.py : 各モニタを束ねるランナー
  - alert_manager.py : （アラート送信ドライバ、LINE 等を想定）
- execution/
  - execution_engine.py : エンジン本体（セッション管理、order flow）
  - broker_factory.py : ブローカークライアント生成（本番/モック判定）
  - order_manager.py / order_repository.py / reconciler.py / risk_manager.py 等
- portfolio/
  - portfolio_builder.py : 候補選定・重み計算
  - position_sizing.py : 発注株数計算（ロット丸め・リスク制限）
  - risk_adjustment.py : セクターキャップ・レジーム乗数等
- research/
  - factor_research.py : momentum/volatility/value の計算（DuckDB 経由）
  - feature_exploration.py : 将来リターン・IC・統計サマリー
- tools/
  - paper_verification_report.py : ペーパートレードの検証レポート生成
- utils/
  - logging_setup.py : 共通ログ設定（Stream+TimedRotatingFileHandler）
  - process_priority.py : 優先度 / CPU affinity 設定
  - その他ユーティリティ群

補足 / 注意点
-------------
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml のあるディレクトリ）を基準に行います。自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- validate_config は PyYAML 非インストール時に YAML の検証をスキップします（警告出力）。
- AI 機能は OpenAI SDK のバージョンやレスポンス形式の変更に影響を受けるため、テストやモック化を想定した設計（テスト時に _call_openai_api をパッチ）になっています。
- データベース（SQLite / DuckDB）の初期化はコード内で必要に応じて行われますが、データファイルの親ディレクトリが存在しない場合は警告が出ます。起動スクリプトはログディレクトリや data ディレクトリの作成を試みますが、権限やパスに注意してください。
- 本番（KABUSYS_ENV=live）環境では LINE 通知などの設定を必ず確認し、KILL_FLAG_CLEAR_ON_START を 0 にしておくことを推奨します。

よく使うコマンドまとめ
---------------------
- .env 作成（対話式）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
- Execution 起動
  - python -m kabusys.run_execution
- Monitoring 起動
  - python -m kabusys.run_monitoring
- Paper Trading レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

ライセンス・貢献
----------------
（この README のテンプレートにはライセンス情報は含まれていません。必要に応じて LICENSE ファイルを追加してください。）

以上がリポジトリの概要と基本的な使い方です。必要であれば各モジュールの API 使用例（関数シグネチャ別の短いサンプル）や、docker / systemd 起動例、CI 設定例などを追記します。どの情報が欲しいか教えてください。