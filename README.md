KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株を対象とした自動売買システムのコードベースです。  
主な目的はシグナル生成 → ポートフォリオ構築 → 発注実行 → 監視（モニタリング）という一連のワークフローを提供することです。  
本リポジトリには運用用の ExecutionEngine / Monitoring サービス、ポートフォリオ構築ユーティリティ、研究用ファクター計算、AI を用いたニュースセンチメント・レジーム判定、運用支援ツールなどが含まれます。

主な特徴
--------
- ExecutionEngine（発注処理）と Monitoring（監視）を分離して起動可能
- Paper Trading（ペーパートレード）モードをサポート（本番 DB と分離）
- DuckDB（時系列 / 研究データ）と SQLite（監視・ログ）を利用
- ニュース NLP（OpenAI）によるセンチメントスコアリング機能
- 市場レジーム判定（ETF MA + マクロニュース）
- .env 対話式ウィザード・設定検証ツールを提供
- ログはコンソール + 日次ローテートファイル（logs/ 以下）で出力

機能一覧
--------
- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV による paper_trading 分離）
  - run_monitoring.py: SystemMonitor のポーリングループを起動（監視ログ記録）
- 設定管理
  - config_setup.py: .env 対話ウィザード（作成・更新）
  - validate_config.py: .env および config/*.yaml の事前検証 CLI
- ポートフォリオ構築（純関数群）
  - ポジション選択・重み計算・サイズ算出（等重・スコア重み・リスクベース）
  - セクター上限適用・レジーム乗数
- 研究用モジュール
  - factor_research.py / feature_exploration.py: ファクター計算・将来リターン・IC・統計サマリ
- AI
  - news_nlp.py: raw_news を LLM に投げて銘柄ごとのセンチメントを ai_scores に保存
  - regime_detector.py: ETF MA + マクロニュースで日次レジーム判定
- 監視（monitoring）
  - system_monitor / trade_monitor / risk_monitor / kill_switch / monitoring_engine
  - monitoring_db: SQLite テーブル定義・操作ラッパー
- ツール
  - tools/paper_verification_report.py: ペーパートレード履歴の検証レポート生成

セットアップ手順
---------------
1. 必要パッケージをインストール
   - Python 3.9+ を想定（プロジェクトの pyproject.toml／requirements を参照してください）。
   - 主な依存例:
     - duckdb
     - psutil
     - openai (AI 機能を使う場合)
     - PyYAML（validate_config の YAML 検証に必要。任意）
   - 例:
     - pip install duckdb psutil openai pyyaml

2. リポジトリルートで .env を作成
   - 対話式ウィザードを推奨:
     - python -m kabusys.config_setup
   - あるいは .env.example を参考に手動作成
   - 重要な環境変数（必須）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 主要なオプション / デフォルト値
     - KABUSYS_ENV: development | paper_trading | live  （デフォルト: development）
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
     - LOG_LEVEL: INFO
     - OPENAI_API_KEY: （AI 機能利用時に必要）
   - 自動ロードの挙動:
     - 起動時にプロジェクトルート（.git または pyproject.toml）を基準に .env / .env.local を自動ロードします。
     - テスト等で自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

3. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱いで exit(1) になります。

4. DB の初期化
   - 多くの起動スクリプトは起動時に必要なテーブルを自動作成します（init_monitoring_db）。
   - DuckDB のスキーマ（prices_daily / raw_financials 等）は別途データパイプラインで作成してください。

使い方（主要コマンド例）
---------------------
- .env 作成（対話式）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine を起動
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を利用して PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録します。
    - 起動時に data/stop_requested.flag が存在する場合は起動を中止します。
    - PID は data/execution.pid に書き出されます（設定により変更可）。
    - 停止は kill.flag（KillSwitch）や stop_requested.flag による制御が可能です（下記参照）。

- Monitoring を起動
  - python -m kabusys.run_monitoring
  - 挙動:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
    - 監視は常に本番用 sqlite_path（SQLITE_PATH）を使用します（KABUSYS_ENV に関係せず）。
    - 監視ループは data/stop_requested.flag の存在で終了します。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション --db で SQLite ファイルを指定できます（環境変数 PAPER_TRADING_SQLITE_PATH も使用可能）。

- AI 機能（ニュース NLP / レジーム判定）
  - 必要: OPENAI_API_KEY 環境変数（または各関数へ api_key を渡す）
  - ニューススコアリング:
    - kabusys.ai.score_news を呼び出し DuckDB 接続と日付を渡す（例: スクリプト／ジョブから実行）
  - レジーム判定:
    - kabusys.ai.regime_detector.score_regime を呼び出し DuckDB 接続と日付を渡す

停止・フラグ制御
----------------
- 優雅な停止（Monitoring / ExecutionEngine）
  - 共通の stop フラグ: data/stop_requested.flag
    - run_monitoring / run_execution はこのファイルの存在を監視してループを抜けます。
    - 停止させるには: touch data/stop_requested.flag（または write）
- Kill Switch（ExecutionEngine 停止トリガ）
  - data/kill.flag を KillSwitch が書き込み、ExecutionEngine に停止を要求します（KillSwitch は drawdown やポジション上限で発動）。
  - KillSwitch.clear() または起動時の環境変数で自動クリア（KILL_FLAG_CLEAR_ON_START=1）も可能ですが、本番では 0 を推奨します。

ログ
----
- setup_logging によりルートロガーが設定されます。
  - コンソール (stdout) 出力 + 日次ローテートファイル（logs/<app_name>.log）
  - デフォルトのログディレクトリ: logs/
  - 環境変数 LOG_DIR / LOG_LEVEL で上書き可能

重要な環境変数（抜粋）
---------------------
- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 運用関連
  - KABUSYS_ENV: development | paper_trading | live
  - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL
  - LOG_DIR: ログ保存ディレクトリ
  - OPENAI_API_KEY: OpenAI API キー（AI 機能で必須）
  - DUCKDB_PATH (default: data/kabusys.duckdb)
  - SQLITE_PATH (default: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db) — paper_trading 用
  - MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、デフォルト 60）
  - PAPER_FILL_MODE: ペーパートレード時の約定挙動（instant|partial|never|reject）
  - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1）

ディレクトリ構成（主なファイル）
--------------------------------
- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / 設定読み込みロジック
  - config_setup.py           — .env 対話ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — Monitoring ポーリング起動スクリプト
  - monitoring/
    - monitoring_db.py        — SQLite テーブル定義・DB 操作
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
  - execution/                 — 発注関連（Engine / OrderManager / BrokerFactory 等）※詳細は該当モジュール参照
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - data/                      — 実行時に使うファイル（data/*.db, data/execution.pid, data/kill.flag 等）を想定

運用上の注意
-------------
- production（KABUSYS_ENV=live）モードでは設定ミスで実際に発注が行われるため、validate_config の実行や LINE 通知設定などを必ず確認してください。
- kill.flag / stop_requested.flag の扱いは慎重に行ってください。特に本番では KILL_FLAG_CLEAR_ON_START=0 推奨。
- AI API を用いる機能はコストとレイテンシの影響を受けます。API キー管理・レート制限を考慮してください。
- ログ / DB ファイルの権限やディスク容量監視を怠らないでください（monitoring はリソース閾値監視機能を持ちます）。

開発者向けメモ
---------------
- 自動 .env ロードはプロジェクトルートの検出に依存します（.git または pyproject.toml）。パッケージ配布後の環境で問題がある場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を使用。
- DuckDB を使う研究モジュールは SQL を多用します。テーブル名（prices_daily, raw_financials, raw_news, ai_scores など）に合わせてデータ投入してください。
- 単体関数（portfolio/* や research/*）は副作用が少ないためユニットテストが容易です。

付録: よく使うコマンド例
----------------------
- .env 作成:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
- Execution 起動:
  - python -m kabusys.run_execution
- Monitoring 起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Paper report:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- 停止（優雅）:
  - touch data/stop_requested.flag
- Kill Switch を手動で設定（Execution 停止を要求）:
  - printf "reason..." > data/kill.flag

以上が README の要点です。必要ならば各モジュール（ExecutionEngine、OrderManager、BrokerClientFactory、monitoring の詳細など）について別途の詳細ドキュメントを作成します。どの箇所を拡張しますか？