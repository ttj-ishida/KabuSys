KabuSys — 日本株自動売買システム
================================

このリポジトリは日本株向けの自動売買システムのコンポーネント群を含みます。
主要機能は発注エンジン（ExecutionEngine）、監視（Monitoring）、ファクター/リサーチ、ポートフォリオ構築、AI（ニュースセンチメント）などです。

以下はこのコードベースに対する README（日本語）です。

プロジェクト概要
---------------
KabuSys は日本株の自動売買を目的としたモジュール群です。設計方針の要点は以下の通りです。

- 発注ロジックと監視ロジックを分離して運用可能（Execution / Monitoring）。
- 本番 DB（SQLite）と Paper Trading 用 DB を分離可能。
- DuckDB を使った時系列・ファクタ計算・リサーチ用ワークスペース。
- OpenAI を用いたニュース NLP（センチメント評価）やレジーム判定の機能。
- ログ・PID・フラグファイルを用いた運用管理（停止フラグ / kill switch 等）。

主な機能一覧
------------
- Execution（発注）
  - ExecutionEngine を起動して注文の管理・送信・リコンシリエーションを行う。
  - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し paper_trading.db に記録（本番と分離）。
  - リスク管理（RiskManager）／OrderManager／OrderRepository などにより発注制御。

- Monitoring（監視）
  - SystemMonitor: CPU/メモリ/Disk、Execution プロセス生存、データ鮮度を監視。
  - TradeMonitor: 注文の滞留や異常約定を検出（trade_logs テーブル参照）。
  - RiskMonitor: ドローダウン・ポジション上限などを監視し、必要に応じて kill.flag を書く。
  - MonitoringEngine: 各モニタを束ねて定期実行、アラート発行。

- Portfolio（ポートフォリオ構築）
  - 候補選定、等重/スコア加重の重み計算、セクター制限、ポジションサイジング（lot サイズ丸め、aggregate cap）などの純粋関数群。

- Research（リサーチ）
  - DuckDB を用いたファクター計算（モメンタム、バリュー、ボラティリティ等）。
  - 将来リターン計算、IC（Information Coefficient）などの統計解析ユーティリティ。

- AI（OpenAI を使用）
  - news_nlp.score_news: ニュースから銘柄ごとのセンチメントを OpenAI に問い合わせ ai_scores テーブルへ書き込む。
  - regime_detector.score_regime: ETF の MA200 とマクロセンチメントから市場レジームを判定し market_regime に保存。

- ツール
  - config_setup: 対話式 .env 作成ウィザード
  - validate_config: 起動前の環境検証 CLI（required env 等をチェック）
  - tools.paper_verification_report: Paper Trading の検証レポート生成

セットアップ手順
----------------
1. リポジトリをクローンしてワークツリーに移動
   - 例: git clone ...; cd <project>

2. Python 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要なパッケージをインストール
   - 必須ライブラリの候補:
     - duckdb
     - psutil
     - openai
     - PyYAML（config の検証で任意）
   - 例:
     - pip install duckdb psutil openai PyYAML

   （requirements.txt がない場合、上記を手動でインストールしてください）

4. .env を用意する
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - もしくは .env.example を参考に作成してプロジェクトルートに .env を置く
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - AI 機能を使う場合:
     - OPENAI_API_KEY を設定

5. 設定検証（任意）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります

基本的な使い方
--------------
起動スクリプトはモジュールとして実行します（-m）。

- ExecutionEngine を起動する（発注エンジン）
  - python -m kabusys.run_execution
  - 動作モード（KABUSYS_ENV）:
    - development: 開発（発注なし）
    - paper_trading: MockBrokerClient を使用、data/paper_trading.db に記録
    - live: 本番（実際に発注）
  - 停止制御:
    - data/stop_requested.flag が存在すると起動を行わない・実行中に検知すると停止する
    - PID ファイル: data/execution.pid（Settings.pid_file_path により変更可能）
    - Kill Switch: monitoring が data/kill.flag を作成した場合、ExecutionEngine は停止される

- Monitoring を起動する（ポーリング監視）
  - python -m kabusys.run_monitoring
  - デフォルトのポーリング間隔は 60 秒。環境変数で上書き可能:
    - MONITOR_POLL_INTERVAL=30 （秒）
  - 監視用 SQLite:
    - Monitoring は KABUSYS_ENV にかかわらず settings.sqlite_path（デフォルト data/monitoring.db）を使用します
  - 停止フラグ:
    - run_monitoring は data/stop_requested.flag を検知してループを終了します

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

- AI 関連（スクリプトから呼ぶ関数例）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは DuckDB 接続を受け取り DB を直接更新します。OPENAI_API_KEY の設定を忘れずに。

運用上のポイント / 設定
-----------------------
- 環境変数（Settings で解決される主要項目）:
  - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH: 監視 DB（default data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（default data/paper_trading.db）
  - LOG_LEVEL: ログレベル（default INFO）
  - OPENAI_API_KEY: OpenAI API キー（AI 機能で必須）
  - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（run_monitoring 用）
  - KILL_FLAG_CLEAR_ON_START: ExecutionEngine 起動時に kill.flag を自動クリアするか（デフォルト 0）

- ログ:
  - 共通ログ設定: kabusys.utils.logging_setup.setup_logging
  - デフォルトログディレクトリ: logs/
  - 起動スクリプトは app_name を指定して logs/<app_name>.log に日次ローテートで出力

- DB（用途別の使い分け）:
  - DuckDB: 時系列データ・prices_daily/raw_financials 等のリサーチ・AI バッチに使用
  - SQLite monitoring.db: system_status / trade_logs / positions / risk_logs / dashboard 等の永続化
  - SQLite paper_trading.db: paper_trading 用の取引ログ（KABUSYS_ENV=paper_trading 時）

- 停止制御と Kill Switch:
  - monitoring が条件に応じて data/kill.flag を書くと ExecutionEngine に停止指示を送れます
  - kill.flag は Settings.kill_flag_path で設定可能。clear は KillSwitch.clear() または手動削除

ディレクトリ構成
----------------
（主要ファイル・モジュールのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数読み込み / Settings
  - config_setup.py               — .env 対話ウィザード
  - validate_config.py            — 起動前チェック CLI
  - run_execution.py              — ExecutionEngine 起動スクリプト
  - run_monitoring.py             — SystemMonitor ポーリングスクリプト
  - tools/
    - paper_verification_report.py — Paper Trading レポート生成
  - ai/
    - news_nlp.py                  — ニュース NLP / OpenAI 呼び出し
    - regime_detector.py           — 市場レジーム判定
  - monitoring/
    - monitoring_db.py             — monitoring 用 SQLite 永続化層
    - system_monitor.py            — システム監視
    - trade_monitor.py             — （存在する想定）注文監視ロジック
    - risk_monitor.py              — ドローダウン / ポジション上限監視
    - kill_switch.py               — kill.flag 書込・判定
    - monitoring_engine.py         — 各 Monitor を束ねる
    - alert_manager.py             — （存在する想定）アラート送信（LINE 等）
  - execution/
    - execution_engine.py          — ExecutionEngine 本体（存在する想定）
    - broker_factory.py            — Broker クライアント生成（Mock/実装の切替）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - data/
    - pipeline.py                   — （存在する想定）DuckDB データパイプラインユーティリティ
  - utils/
    - logging_setup.py
    - process_priority.py

注意事項 / 運用上の補足
---------------------
- Monitoring は run_monitoring のコメントにあるように「環境にかかわらず」settings.sqlite_path（監視用 DB）を利用します。つまり paper_trading モードでも監視 DB は本番設定のものを参照する設計になっています（重要な運用上の挙動）。
- ExecutionEngine は paper_trading モードのとき paper_trading 用 SQLite を使用して本番 DB と分離します。
- .env は絶対にリポジトリにコミットしないでください（README ヘッダにも注記があります）。
- OpenAI を利用する機能は API 呼び出しで課金が発生します。API キーの管理と利用制限に注意してください。
- psutil を使ってプロセス優先度・CPU affinity を設定しています。一部の OS では権限不足で設定に失敗する場合があります（警告ログのみで継続します）。

トラブルシューティング
----------------------
- .env の自動ロードが問題になるテスト等では環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動読み込みを無効にできます（config.py の挙動）。
- validate_config で PyYAML がないと YAML 検証をスキップします。YAML 検証が必要なら PyYAML をインストールしてください。
- Logging ディレクトリの作成に失敗するとファイル出力が無効化され、標準出力のみになります（warnings を確認してください）。

ライセンス・貢献
----------------
本 README ではライセンス情報は含まれていません。実プロジェクトに落とし込む際は LICENSE ファイルや貢献ガイドを追加してください。

以上がこのコードベースの概要と運用ガイドです。ご要望があれば、セットアップスクリプト（requirements.txt / systemd ユニット例）やより詳細な運用手順、各モジュールの API ドキュメントを追加します。どの情報を優先して追加しましょうか？