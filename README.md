KabuSys — 日本株自動売買システム
=================

概要
---
KabuSys は日本株向けの自動売買／リサーチ用ライブラリ兼実行フレームワークです。  
主な目的は以下のとおりです。

- Strategy の研究（ファクター計算、特徴量解析）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算）
- ExecutionEngine による発注・リスク管理（paper/live 切替対応）
- 監視（System / Trade / Risk）と Kill Switch による安全停止
- AI を使ったニュースセンチメント評価・レジーム判定
- ペーパートレードの検証レポート生成

主要機能
---
- 設定管理
  - .env 自動読み込み（プロジェクトルート検出）と Settings クラスによる環境値取得
  - 対話式 .env 作成ウィザード（kabusys.config_setup）
  - 起動前の設定検証 CLI（kabusys.validate_config）

- 実行エンジン
  - run_execution: ExecutionEngine 起動スクリプト
  - KABUSYS_ENV=paper_trading 時は MockBrokerClient と専用 DB を使用（data/paper_trading.db）

- 監視
  - run_monitoring: SystemMonitor のポーリング起動スクリプト（既定 60 秒）
  - MonitoringEngine による System / Trade / Risk の統合監視
  - KillSwitch（条件に合致すると data/kill.flag を書き込んで ExecutionEngine を停止）

- データ永続化
  - DuckDB（分析用）と SQLite（監視・トレードログ）を利用
  - monitoring_db.init_monitoring_db によるスキーマ初期化 / マイグレーション

- ポートフォリオ構築（純粋関数群）
  - 候補選定、等重・スコア重み、リスク調整（セクターキャップ、レジーム乘数）、ポジションサイズ計算

- リサーチ（DuckDB を用いたファクター計算・解析）
  - momentum / volatility / value ファクター計算
  - 将来リターン計算、IC（Information Coefficient）算出、統計サマリー

- AI（OpenAI）連携
  - news_nlp.score_news: ニュース記事をまとめて LLM に送り銘柄別センチメントを ai_scores に書込
  - regime_detector.score_regime: MA200 とマクロニュースの LLM スコアを合成して market_regime を判定
  - API 呼び出しは堅牢化（リトライ、パース検証、フォールバック）済み

- ユーティリティ
  - ロギング統一設定（console + 日次ファイルローテーション）
  - プロセス優先度 / CPU affinity の設定ユーティリティ
  - ペーパートレード検証レポート生成スクリプト（tools/paper_verification_report.py）

セットアップ手順
---
1. Python 環境
   - 推奨: Python 3.9+（duckdb, psutil, openai 等が必要）
   - 仮想環境を作成して有効化してください。
     - python -m venv .venv
     - source .venv/bin/activate（Windows: .venv\Scripts\activate）

2. 依存パッケージのインストール（プロジェクトに requirements.txt が無い場合の例）
   - pip install duckdb psutil openai
   - （オプション）PyYAML を使うと validate_config が config/*.yaml を検証できます:
     - pip install PyYAML

3. .env の作成
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - もしくはプロジェクトルートの .env を手動作成してください。.env.example（未提供）を参考に以下の主要変数を設定します:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト development
     - DUCKDB_PATH (例: data/kabusys.duckdb)
     - SQLITE_PATH (例: data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB, 例: data/paper_trading.db)
     - OPENAI_API_KEY（AI 機能を使う場合）
     - LOG_LEVEL (DEBUG/INFO/...)
     - その他: LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（アラート通知用）

4. 設定検証
   - python -m kabusys.validate_config
   - --strict をつけると警告も失敗扱いになります。

使い方（主なコマンド）
---
- 監視プロセス起動
  - python -m kabusys.run_monitoring
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）
    - 停止: プロジェクトルート/data/stop_requested.flag を作成するとループが終了します

- 実行エンジン起動（発注）
  - python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading のときは paper_trading 用 DB にログを記録し、MockBroker を使用します
    - 実行中にプロセスを停止したい場合は data/stop_requested.flag を作成
    - ExecutionEngine は起動時に kill.flag の扱いを確認します（設定により起動時に消す動作もあり）

- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- AI 機能（プログラムから呼び出す）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

環境変数・設定の注意点
---
- KABUSYS_ENV: development / paper_trading / live（必ず有効な値に設定）
- PAPER_FILL_MODE: paper_trading 時の約定モード（instant|partial|never|reject）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング秒数（1以上の整数）
- ファイルパスのデフォルト:
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
  - PID / flag / log: data/*.pid, data/kill.flag, logs/<app>.log
- OpenAI を使う機能は OPENAI_API_KEY の設定が必須（関数は引数で直接渡すことも可能）

プロセス制御とフラグ
---
- stop_requested.flag
  - run_monitoring/run_execution のループ停止に利用（存在を検知して安全に終了）
  - パス: プロジェクトルート/data/stop_requested.flag
- kill.flag
  - KillSwitch が書き込むファイル。ExecutionEngine はこれを検知して停止します
  - Settings.kill_flag_path でパスを制御可能
- PID ファイル
  - ExecutionEngine は実行時に pid を data/* に書き出します（Settings.pid_file_path）

ログ
---
- ログは標準出力（stdout）とファイル（logs/<app_name>.log）に出力されます。
- デフォルトで日次ローテーション、30日分保持。
- ログディレクトリは環境変数 LOG_DIR または引数で変更可能。

ディレクトリ構成（概略）
---
src/
  kabusys/
    __init__.py
    config.py                      # 環境変数読み込み・Settings
    config_setup.py                # .env 対話式ウィザード
    validate_config.py             # 設定検証 CLI
    run_monitoring.py              # SystemMonitor ポーリング起動
    run_execution.py               # ExecutionEngine 起動スクリプト
    tools/
      paper_verification_report.py  # ペーパートレード検証レポート
    ai/
      news_nlp.py                  # ニュース NLP（OpenAI）
      regime_detector.py           # レジーム判定（MA200 + マクロ NLP）
      __init__.py
    portfolio/
      portfolio_builder.py         # 候補選定・等重/スコア重み
      position_sizing.py           # 株数決定・スケールダウン
      risk_adjustment.py           # セクター制約・レジーム乘数
      __init__.py
    research/
      factor_research.py           # ファクター計算（momentum/volatility/value）
      feature_exploration.py       # 将来リターン・IC・統計サマリ
      __init__.py
    monitoring/
      monitoring_db.py             # monitoring 用 SQLite のスキーマと DB ラッパ
      system_monitor.py            # システム・データ鮮度監視
      trade_monitor.py             # （trade_monitor 実装参照）
      risk_monitor.py              # ドローダウン・ポジション上限監視
      kill_switch.py               # Kill Switch 実装（フラグ書込）
      monitoring_engine.py         # 各モニタ統合
      alert_manager.py             # （通知管理：LINE 等の送信）
    utils/
      logging_setup.py             # 共通ログ設定
      process_priority.py          # プロセス優先度・CPU affinity
      __init__.py
    execution/                      # Execution 関連（order_manager, broker_factory, engine など）
    data/                           # データパイプライン・DuckDB スキーマ（prices_daily 等）
    research/                       # リサーチ補助
    tools/                          # 補助ツール

（注）上記はこのリポジトリに含まれる主要ファイルを抜粋した概略です。実際のファイルは src/kabusys 以下に多数あります。

よくあるトラブルシューティング
---
- 必須環境変数が未設定:
  - validate_config を実行して指摘に従ってください。
- ログディレクトリ作成失敗:
  - 権限を確認するか、環境変数 LOG_DIR で書込可能なディレクトリを指定してください。
- OpenAI 呼び出し失敗:
  - OPENAI_API_KEY の設定とネットワークアクセス（タイムアウト、レート制限）を確認してください。
- DuckDB / SQLite ファイルが見つからない:
  - 環境変数でパスを指定するか、データディレクトリを作成してください。

開発者向けのメモ
---
- 設定ファイル（config/*.yaml）は validate_config で検証可能（PyYAML が必要）
- ai モジュールは API 呼び出し部分をラップしており、テスト時は内部呼び出しをモックする設計
- ポートフォリオ・ポジションサイズの関数群は副作用を持たない純粋関数として実装されています（単体テストが容易）

最後に
---
本 README はリポジトリ内のソースから主要な動作・設定・使い方をまとめたものです。実行前に必ず python -m kabusys.validate_config で設定を確認してください。必要であれば README にプロジェクト固有の依存関係やバージョン要件（Python バージョン、ライブラリの固定バージョン）を追加してください。