KabuSys — 日本株自動売買システム
=============================

概要
----
KabuSys は日本株向けの自動売買システムのコードベースです。  
主に次の機能群を含みます。

- ExecutionEngine（発注エンジン）: 本番/ペーパートレードの発注・リスク管理を行う
- Monitoring（監視）: システム稼働状況、データ鮮度、注文状況、リスク指標の定期チェック
- Portfolio（銘柄選定・ポジション決定）: 候補選定、重み付け、ポジションサイズ計算、セクター制限
- Research（研究）: ファクター計算、特徴量探索、IC 等の算出
- AI（ニュース NLI / レジーム判定）: OpenAI を使ったニュースセンチメント評価と市場レジーム判定
- ユーティリティ: 設定管理、ログ設定、プロセス優先度など
- ツール: ペーパートレードの検証レポート生成スクリプト等

主な設計方針:
- 環境変数・.env による設定管理（config モジュール）
- DuckDB / SQLite を利用したデータ保存と解析
- Paper Trading は本番 DB と分離（PAPER_TRADING_SQLITE_PATH）
- LLM 呼び出しは冪等・リトライ・フェイルセーフ設計

主な機能一覧
--------------
- 実行系
  - run_execution.py: ExecutionEngine を起動。KABUSYS_ENV=paper_trading のときは MockBrokerClient を利用して data/paper_trading.db を使用
  - OrderManager / RiskManager / Reconciler などによる発注・整合処理
- 監視系
  - run_monitoring.py: SystemMonitor のポーリングループを起動（MONITOR_POLL_INTERVAL で間隔変更可）
  - MonitoringEngine: System / Trade / Risk の各 Monitor を束ねてアラートや Kill Switch 判断
  - monitoring_db: 監視ログ用 SQLite テーブル定義と永続化ロジック
  - KillSwitch: 条件に応じて data/kill.flag を書き ExecutionEngine を停止
- ポートフォリオ構築
  - 候補選定（select_candidates）
  - 等金額 / スコア重み付け（calc_equal_weights / calc_score_weights）
  - ポジション決定（calc_position_sizes）
  - セクター上限適用（apply_sector_cap）、レジーム乗数（calc_regime_multiplier）
- リサーチ
  - ファクター計算（momentum, volatility, value）
  - 将来リターン、IC、統計サマリ関数
- AI
  - news_nlp.score_news: raw_news を集約し OpenAI でセンチメントを算出して ai_scores に書込む
  - regime_detector.score_regime: ma200 とマクロニュースセンチメントを合成して market_regime に書込む
- ユーティリティ
  - config_setup.py: 対話式で .env を生成/更新するウィザード
  - validate_config.py: 起動前に環境変数・config/*.yaml を検証する CLI
  - logging_setup: 統一的なログ設定（stdout + 日次ローテートファイル）
  - process_priority: プロセス優先度 / CPU affinity の設定
- ツール
  - tools/paper_verification_report.py: ペーパートレード DB から検証レポートを生成

セットアップ手順
----------------
1. Python 環境を用意する（推奨: Python 3.10+）
2. 依存パッケージをインストール（例）:
   - duckdb
   - psutil
   - openai
   - PyYAML（config YAML 検証を使う場合）
   例:
     pip install duckdb psutil openai pyyaml
   ※ requirements.txt がある場合はそれを利用してください（本リポジトリに無い場合は上記を個別にインストール）。

3. プロジェクトルートに .env を作成する
   - 対話式ウィザードを使う:
       python -m kabusys.config_setup
   - または手動で .env を作成（最低限必要な環境変数）:
       JQUANTS_REFRESH_TOKEN=your_token_here
       KABU_API_PASSWORD=your_kabu_password_here
       KABUSYS_ENV=development
       DUCKDB_PATH=data/kabusys.duckdb
       SQLITE_PATH=data/monitoring.db
       LOG_LEVEL=INFO
     .env.example を参考にしてください。

4. 設定検証（起動前推奨）:
     python -m kabusys.validate_config
   --strict を付けると警告も失敗扱いになります。

5. データディレクトリの作成（必要に応じて）
   - default の SQLite / DuckDB / logs は data/ や logs/ 配下を使用します。ログディレクトリは LOG_DIR 環境変数で変更可能。

使い方（起動と主要コマンド）
----------------------------
- 実行エンジンを起動:
    python -m kabusys.run_execution
  挙動:
    - プロセス優先度を high に設定（可能な場合）
    - Settings によって paper_trading と production を切替
      - KABUSYS_ENV=paper_trading の場合は paper_sqlite_path（デフォルト data/paper_trading.db）を使用
    - 停止フラグ（data/stop_requested.flag）がある場合は起動をスキップ
    - 実行中は data/execution.pid を使用

- 監視ループを起動:
    python -m kabusys.run_monitoring
  挙動:
    - Settings の sqlite_path（監視 DB）に接続（監視は常に本番 sqlite_path を使用）
    - DuckDB に接続
    - SystemMonitor を定期実行（デフォルト間隔 60 秒）
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き（正の整数、デフォルト 60）
    - data/stop_requested.flag が作られるとループを終了

- .env 作成（対話式）:
    python -m kabusys.config_setup

- 設定検証:
    python -m kabusys.validate_config
    python -m kabusys.validate_config --strict

- ペーパートレード検証レポート:
    python -m kabusys.tools.paper_verification_report
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  オプション --db で SQLite ファイルパスを明示可能。環境変数 PAPER_TRADING_SQLITE_PATH にも対応。

環境変数（主要）
----------------
- JQUANTS_REFRESH_TOKEN: J-Quants API のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABUSYS_ENV: 実行環境（development | paper_trading | live） デフォルト: development
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR: ログファイル保存ディレクトリ（デフォルト logs/）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール利用時）
- PAPER_FILL_MODE: ペーパートレードでの約定挙動（instant | partial | never | reject）

重要な動作・運用メモ
-------------------
- Paper Trading の分離:
  - KABUSYS_ENV=paper_trading のとき、run_execution は paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）を用いるため、本番データと分離されます。ただし monitoring は常に sqlite_path（本番監視 DB）を参照します。
- Kill / Stop フラグ:
  - KillSwitch は Settings.kill_flag_path（デフォルト data/kill.flag）を作成して ExecutionEngine に停止シグナルを送ります。
  - run_monitoring / run_execution は data/stop_requested.flag の存在を検知してループを終了します。
- ログ:
  - logging_setup.setup_logging を各起動スクリプトで呼び出しています。stdout と日次ローテートファイルに出力します。
- プロセス優先度:
  - 起動時に set_process_priority("high") が呼ばれます。プラットフォームに依存しアクセス権限が足りない場合は警告でスキップされます。
- セキュリティ:
  - .env は絶対にリポジトリにコミットしないでください。

ディレクトリ構成
----------------
（プロジェクトルート = src 以下を想定）

- src/kabusys/
  - __init__.py
  - config.py                # 環境変数 / .env 自動ロードロジック、Settings クラス
  - config_setup.py          # .env 対話式ウィザード
  - validate_config.py       # 設定検証 CLI
  - run_execution.py         # ExecutionEngine 起動スクリプト
  - run_monitoring.py        # SystemMonitor ポーリングループ起動スクリプト
  - utils/
    - logging_setup.py       # ログ設定ユーティリティ
    - process_priority.py    # プロセス優先度 / CPU affinity
  - execution/               # 発注関連コンポーネント（エンジン、リポジトリ等）
    - (OrderManager, ExecutionEngine, BrokerFactory 等)
  - monitoring/
    - monitoring_db.py       # SQLite スキーマ & DB 操作ラッパー
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - tools/
    - paper_verification_report.py
    - __init__.py
  - data/ (運用側に作成される想定)
    - monitoring.db (デフォルト)
    - paper_trading.db (ペーパートレード時)
    - kill.flag / stop_requested.flag / execution.pid など

参考コマンドまとめ
------------------
- .env 対話式作成:
    python -m kabusys.config_setup
- 設定検証:
    python -m kabusys.validate_config
- 実行エンジン起動:
    python -m kabusys.run_execution
- 監視ループ起動:
    python -m kabusys.run_monitoring
- ペーパートレード検証レポート:
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

ライセンス・注意事項
---------------------
- 本プロジェクトは機微な金融ロジックを含みます。本番運用時は十分な検証を行い、環境変数や API キーの管理に注意してください。
- .env に秘匿情報（API キー・パスワード）を記載する場合は、リポジトリやログに漏れないよう管理してください。

以上が基本的な README です。さらに「各モジュールの API（関数一覧）や DB スキーマの詳細」「運用手順（デプロイ / systemd / Supervisor 設定例）」などを追加ご希望であれば、詳細を作成します。