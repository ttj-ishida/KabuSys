README
======

プロジェクト概要
----------------
KabuSys は日本株向けの自動売買 / 研究プラットフォームです。本リポジトリは以下の主要機能を持ちます。

- データ格納（DuckDB / SQLite）
- ファクター計算・研究用ユーティリティ（research）
- ポートフォリオ構築・ポジションサイズ計算（portfolio）
- ExecutionEngine（発注エンジン）と監視（monitoring）
- Paper Trading 用の分離された DB と検証レポート生成ツール
- OpenAI（LLM）を使ったニュース NLP / レジーム判定（ai）

設計方針の概要：
- 本番とペーパートレードはDBを分離（paper_trading モード時に PAPER_TRADING_SQLITE_PATH を使用）
- 監視（Monitoring）は環境にかかわらず本番の sqlite_path を参照し、システム状態や取引ログを永続化
- 外部 API 呼び出し（OpenAI など）は明示的に API キーを渡すか環境変数で設定
- .env を使った設定管理をサポート（対話式ウィザードあり）

機能一覧
--------
主な機能（抜粋）：

- Execution
  - ExecutionEngine の起動スクリプト（run_execution.py）
  - Paper trading モード（MockBrokerClient を使用）で本番 DB と分離
  - PID / stop フラグによる起動・停止制御
- Monitoring
  - SystemMonitor（CPU/メモリ/ディスク状況、データ鮮度、PID の監視）
  - TradeMonitor（滞留注文・約定異常を検出）
  - RiskMonitor（ドローダウン・ポジション数制限の監視）
  - KillSwitch（条件を満たしたら data/kill.flag を書き込み実行系を停止）
  - MonitoringEngine（上記の監視を定期実行）
  - monitoring_db: SQLite に監視ログ / trade_logs / risk_logs / dashboard を永続化
- Portfolio モジュール
  - 候補抽出、重み計算、ポジションサイズ計算、セクターキャップ、レジーム乗数など
- Research
  - Momentum／Volatility／Value 等ファクター計算（DuckDB を利用）
  - 将来リターン計算、IC（Information Coefficient）などの統計ユーティリティ
- AI（OpenAI）
  - news_nlp: ニュースを LLM でスコアリングし ai_scores テーブルへ書き込み
  - regime_detector: ETF / マクロ記事を組み合わせて市場レジーム判定
- Tools
  - Paper Trading 検証レポート生成ツール（tools/paper_verification_report.py）
- 設定管理・検証
  - config_setup.py: .env を対話式で作成・更新
  - validate_config.py: 起動前の設定検証 CLI

セットアップ手順
----------------

前提
- Python 3.10+ を推奨
- Git リポジトリルートに配置されたプロジェクトを想定

1) 仮想環境（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2) 必要パッケージのインストール（例）
   - pip install duckdb psutil openai
   - PyYAML は config/*.yaml の構文検査で使用（任意）：pip install pyyaml

   （requirements.txt が無い場合は上記を手動でインストールしてください）

3) データディレクトリ作成
   - mkdir -p data

4) .env の作成（推奨: 対話式ウィザード）
   - python -m kabusys.config_setup
     - ウィザードは .env を生成します（絶対に Git にコミットしないでください）
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD

5) 設定検証
   - python -m kabusys.validate_config
     - --strict を付けると警告も失敗扱いになります

使い方
------

主要な実行コマンド例（プロジェクトルートで実行）

- ExecutionEngine を起動
  - python -m kabusys.run_execution
  - 動作モードは KABUSYS_ENV に依存:
    - development: 開発用（発注なし）
    - paper_trading: MockBrokerClient を使用（PAPER_TRADING_SQLITE_PATH に記録）
    - live: 本番ブローカーを使用
  - 起動時に data/execution.pid を書き、停止は下記のフラグファイルで制御
  - stop フラグ（プロセス即時停止）:
    - run_execution は data/stop_requested.flag の存在を監視し、検出でエンジン停止します
  - kill_switch（監視側からの停止）:
    - monitoring.KillSwitch が data/kill.flag を書き込むと ExecutionEngine 側で対応する設計です（実装は ExecutionEngine 側コードに依存）

- Monitoring を起動
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）
  - python -m kabusys.run_monitoring
  - 注意: Monitoring は KABUSYS_ENV にかかわらず settings.sqlite_path（本番 sqlite）を使用して監視ログを記録します

- Paper Trading 検証レポートを生成
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to   YYYY-MM-DD
    - --db PATH   （PAPER_TRADING_SQLITE_PATH 環境変数またはデフォルト data/paper_trading.db を使用）

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

環境変数（主なもの）
- KABUSYS_ENV (default: development)
  - valid: development | paper_trading | live
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db) — Monitoring が使う DB（常に使用）
- PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db) — paper_trading モードで Execution が使う DB
- PAPER_FILL_MODE (instant | partial | never | reject) — paper_trading の約定挙動
- OPENAI_API_KEY — AI モジュール（news_nlp / regime_detector）が必要とする場合
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — LINE 通知（任意）
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL)
- KILL_FLAG_CLEAR_ON_START (0|1) — 起動時に kill.flag を自動クリアするか（本番では 0 を推奨）
- MONITOR_POLL_INTERVAL (秒) — run_monitoring スクリプトの既定間隔を上書き

停止・強制停止
- run_execution/run_monitoring はそれぞれ data/stop_requested.flag をチェックします。停止させたい場合は該当ファイルを作成してください。
  - 例: touch data/stop_requested.flag
- KillSwitch により data/kill.flag が書かれます（監視ロジックにより作成）。kill.flag を発行されたら Execution 側で停止処理が行われる設計です。
- kill.flag を手動でクリアするには:
  - rm data/kill.flag
  - Settings.kill_flag_clear_on_start が 1 の場合、エンジン起動時に自動クリアされます（本番では 0 を推奨）。

注意点・トラブルシューティング
- 必須環境変数が未設定だと起動に失敗します。まず python -m kabusys.validate_config で検査してください。
- PyYAML がインストールされていないと config/*.yaml の検証はスキップされます（警告）。
- OpenAI を使う機能（ai.news_nlp / ai.regime_detector）は OPENAI_API_KEY が必要。不在の場合は ValueError を送出することがあります。
- Monitoring は常に settings.sqlite_path を使用します。paper_trading でも監視データは本番 sqlite に格納される点に注意してください。
- psutil によるプロセス優先度設定・CPU affinity 設定は権限やOSにより失敗する場合があります（警告ログが出ますが処理は継続します）。

ディレクトリ構成
----------------
（src/kabusys 配下の主要ファイルと役割）

- kabusys/
  - __init__.py — パッケージ定義、バージョン
  - config.py — 環境変数/.env 読み込みと Settings クラス
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 起動前設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト

  - ai/
    - __init__.py
    - news_nlp.py — ニュースの LLM スコアリング（ai_scores へ書込）
    - regime_detector.py — マクロ + ETF MA で市場レジーム判定

  - monitoring/
    - monitoring_db.py — SQLite スキーマ初期化・永続化層
    - system_monitor.py — CPU/メモリ/ディスク/データ鮮度/PID の監視
    - trade_monitor.py — 滞留注文・約定異常の検出
    - risk_monitor.py — ドローダウン / ポジション数の監視（KillSwitch と連携）
    - kill_switch.py — フラグファイルで Execution 停止を指示
    - monitoring_engine.py — 各 Monitor を束ねる実行ループ
    - alert_manager.py — （未掲示の実装）アラート送信管理

  - execution/
    - broker_factory.py — BrokerClient の生成（本番 / mock 切替）
    - execution_engine.py — 実際の発注実行ロジック
    - order_manager.py, order_repository.py, order_record.py, reconciler.py, risk_manager.py など（発注ロジック周り）

  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数決定・投下資金制御
    - risk_adjustment.py — セクターキャップ・レジーム乗数
    - __init__.py

  - research/
    - factor_research.py — モメンタム/ボラティリティ/バリュー等の計算
    - feature_exploration.py — 将来リターン・IC・統計サマリー
    - __init__.py

  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成ツール
    - __init__.py

  - data/ （実行時に使用される想定ディレクトリ）
    - monitoring.db（デフォルト）
    - paper_trading.db（paper_trading 用）
    - kabusys.duckdb（DuckDB）
    - execution.pid, stop_requested.flag, kill.flag などのフラグ / PID ファイル

SQLite / DuckDB 関連
- monitoring_db.init_monitoring_db(conn) により以下テーブルが作成されます（冪等）:
  - system_status, trade_logs, positions, risk_logs, dashboard
- DuckDB は主に prices_daily / raw_financials / raw_news 等の分析テーブルを想定

ライセンス・貢献
----------------
（この README では記載がありません。必要に応じて LICENSE を追加してください）

付記
----
- 本ドキュメントはコードベースのコメント・動作から要点を抽出したものであり、実運用に用いる場合は config/*.yaml や ExecutionEngine の詳細実装、ブローカー実装、アラート送信の実装を必ず確認してください。