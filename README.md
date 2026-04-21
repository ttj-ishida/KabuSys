KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株の自動売買に関するライブラリ兼起動スクリプト群です。  
主に以下の機能を含みます。

- データパイプライン / DuckDB を使ったファクター計算（research）
- ポートフォリオ構築・株数算出（portfolio）
- 発注エンジン起動スクリプト（execution）
  - 本番 / ペーパートレード（MockBroker）を切り替え可能
- 監視エンジン（monitoring）
  - システム状態・データ鮮度・注文ログ監視、Kill Switch の発動
- AI 補助機能（news sentiment / regime detection） — OpenAI を利用
- 各種ユーティリティ（ログ設定、プロセス優先度、設定ウィザード等）
- ツール群（ペーパートレード検証レポート等）

主な特徴
--------
- 環境変数 / .env による設定管理（Settings クラス）
- paper_trading と live の DB 分離（paper_trading は data/paper_trading.db を利用）
- DuckDB を分析用 DB として使用
- 監視用 SQLite（data/monitoring.db）に監視ログを永続化
- デーモン的なポーリングループを持つ起動スクリプト（停止フラグで安全停止）
- OpenAI（gpt-4o-mini）を用いたニュース NLP / レジーム判定（API キー必要）
- ログは標準出力＋日次ローテーションファイル（logs/<app>.log）

セットアップ手順
----------------

1. レポジトリをクローンして依存をインストール
   - 必要なパッケージ（代表例）
     - duckdb
     - psutil
     - openai (AI 機能を使う場合)
     - PyYAML（config 検証で YAML 検査を行う場合）
   - 例（pip）:
     - pip install -r requirements.txt
     - （requirements.txt がない場合は上記パッケージを個別にインストール）

2. .env を作成する（対話式ウィザード推奨）
   - ウィザードを実行:
     - python -m kabusys.config_setup
   - 必要な必須環境変数:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
   - 重要なオプション:
     - KABUSYS_ENV = development | paper_trading | live （初期値: development）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
     - OPENAI_API_KEY（AI 機能利用時）
     - LOG_LEVEL（デフォルト: INFO）
     - KILL_FLAG_CLEAR_ON_START（本番での自動クリアは危険: デフォルト 0）

3. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い:
     - python -m kabusys.validate_config --strict

4. 必要ディレクトリの作成（.env 作成時に自動的に warnings が出ますが手動作成可）
   - data/（DB・PID・フラグファイル保管）
   - logs/（ログファイル）

使い方
------

起動スクリプト・ツールの実行例。

- ExecutionEngine（実際の発注処理を行うプロセス）
  - 例:
    - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用して data/paper_trading.db に記録（本番 DB と分離）
    - 起動時に data/stop_requested.flag が存在する場合は起動せず終了
    - data/execution.pid に PID を書き出す（設定によりパス変更可）
    - stop は data/stop_requested.flag を作成することで実施（監視プロセスや手動でファイル作成）

- Monitoring（監視ループ）
  - 例:
    - python -m kabusys.run_monitoring
  - 環境変数:
    - MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き（デフォルト 60 秒）
  - 挙動:
    - 監視は常に Settings.sqlite_path（本番用 monitoring.db）を使ってログを保存
    - data/stop_requested.flag を検知してループを終了

- Paper Trading 検証レポート
  - 例:
    - python -m kabusys.tools.paper_verification_report
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    - データベースを明示する場合:
      - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI 機能（ニュース NLP / レジーム判定）
  - 必須: OPENAI_API_KEY を環境変数に設定
  - API 呼び出しは kabusys.ai.news_nlp.score_news や kabusys.ai.regime_detector.score_regime を通じて行う
  - 例（ライブラリ呼び出し）:
    - from kabusys.ai.news_nlp import score_news
    - score_news(conn, target_date)  # DuckDB 接続と日付を渡す

- 設定ウィザード / 検証（再掲）
  - python -m kabusys.config_setup
  - python -m kabusys.validate_config

制御ファイル（停止 / Kill）
- data/stop_requested.flag
  - run_execution / run_monitoring はこのファイルを検知して安全に停止します（手動で作成してプロセスを停止）。
- data/kill.flag
  - KillSwitch（監視側）が条件を満たすとこのファイルを書き込んで ExecutionEngine に停止指示を送ります。
  - Settings.kill_flag_clear_on_start が 1 の場合、Engine 起動時に自動でクリアする設定があるので本番では注意。

ログ
---
- デフォルトは logs/<app_name>.log（TimedRotatingFileHandler、日次ローテーション、30日保持）と標準出力（stdout）。
- ログディレクトリは LOG_DIR 環境変数または setup_logging の引数で変更可能。

主な環境変数（抜粋）
-------------------
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
- SQLITE_PATH: data/monitoring.db（監視 DB、デフォルト）
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用）
- OPENAI_API_KEY: OpenAI API キー（AI 機能）
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト INFO）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: instant|partial|never|reject（paper_trading の挙動）
- KILL_FLAG_CLEAR_ON_START: 0|1（起動時に kill.flag を自動クリアするか）

ディレクトリ構成
----------------
（src/kabusys 以下をルートとした主要ファイル/モジュール）

- kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理、自動 .env ロード
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前の設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py  — ペーパートレード検証レポート
  - ai/
    - news_nlp.py             — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py      — 市場レジーム判定（OpenAI + ETF MA）
  - research/
    - factor_research.py      — Momentum / Volatility / Value の計算（DuckDB）
    - feature_exploration.py  — 将来リターン・IC・サマリー等
  - portfolio/
    - portfolio_builder.py    — 候補選定・等配分/スコア配分
    - position_sizing.py      — 発注株数計算・集約制限・単元丸め
    - risk_adjustment.py      — セクター上限・レジーム乗数
  - monitoring/
    - monitoring_db.py       — monitoring DB スキーマ + 操作ラッパ
    - system_monitor.py      — システム状態・データ鮮度監視
    - trade_monitor.py       — 注文ログの監視（ファイルに含まれる）
    - risk_monitor.py        — ドローダウン / ポジション上限監視
    - kill_switch.py         — kill.flag 書き込みロジック
    - monitoring_engine.py   — 各 Monitor を束ねるループ
    - alert_manager.py       — （通知送信ロジック。内容による）
  - execution/
    - execution_engine.py    — 実際の発注セッション管理（Engine）
    - broker_factory.py      — ブローカークライアント生成（Mock/Live 切替）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - data/                    — （例: data/*.db, pid, flag を置く想定のトップディレクトリ）
  - utils/
    - logging_setup.py       — ログの共通初期化
    - process_priority.py    — プロセス優先度 / CPU affinity 設定
    - その他ユーティリティ

注意事項 / 運用上のポイント
--------------------------
- 本番（KABUSYS_ENV=live）では Kill Switch / LINE 通知等を含め十分に設定を確認してください。validate_config の警告は無視しないでください。
- .env は機密情報を含むため必ず .gitignore に追加し、リポジトリにコミットしないでください。
- OpenAI を使う機能は API 使用料が発生します。API キーの管理に注意してください。
- paper_trading モードは実トレードと DB を分離するよう設計されています（PAPER_TRADING_SQLITE_PATH を利用）。本番 DB を誤って上書きしないよう注意してください。
- 監視は monitoring DB（Settings.sqlite_path）に書き込みます。run_monitoring は KABUSYS_ENV に関係なく production sqlite_path を使用する点に注意してください。

開発者向け（簡単なフロー例）
---------------------------
1. .env を作成（python -m kabusys.config_setup）
2. 設定検証（python -m kabusys.validate_config）
3. DuckDB にテスト用データを投入（ローカル/スクリプト）
4. 監視を 1 回だけ実行して挙動確認（ユニットテスト用に MonitoringEngine.run_once を利用）
5. ExecutionEngine を起動して統合テスト

お問い合わせ / 貢献
------------------
- README の改善・バグ修正・機能追加は Pull Request を歓迎します。  
- セキュリティに関わる問題が見つかった場合はリポジトリの ISSUE またはオーナーに直接ご連絡ください。

以上がプロジェクトの概要、セットアップ、使い方、ディレクトリ構成の要約です。追加で README に記載したいサンプル .env、起動例スクリプトや具体的な API の使い方（score_news のサンプル呼び出しなど）があれば追記します。必要なものを教えてください。