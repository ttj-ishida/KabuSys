KabuSys — 日本株自動売買システム
=================================

概要
----
KabuSys は日本株向けの自動売買フレームワークです。戦略・ポートフォリオ構築、発注エンジン（ExecutionEngine）、監視（Monitoring）、リサーチ（DuckDB を用いたファクター計算）、および AI 補助（ニュースセンチメント・レジーム判定）を備えたモジュール群で構成されています。

主な特徴
--------
- 実行モード切替: KABUSYS_ENV による development / paper_trading / live の切替。
  - paper_trading モードでは MockBrokerClient を使い、本番 DB と分離された data/paper_trading.db に記録。
- ExecutionEngine（発注エンジン）と Monitoring（監視）を独立して起動可能。
- 監視:
  - システム状態（CPU/メモリ/ディスク・データ鮮度）と Execution プロセスの存在を定期チェック。
  - ドローダウンやポジション数上限の監視、Kill Switch（data/kill.flag）によるエンジン停止シグナル。
- ポートフォリオ構築:
  - 候補選定、ウェイト計算（等金額／スコア加重）、ポジションサイズ計算（リスクベース、単元株丸め）、
    セクターキャップ、レジーム乗数適用。
- リサーチ:
  - DuckDB ベースのファクター計算（モメンタム、ボラティリティ、バリュー）、将来リターン・IC 計算等。
- AI:
  - OpenAI を使ったニュースセンチメント（news_nlp.score_news）とレジーム判定（regime_detector.score_regime）。
  - 冪等書き込み・リトライロジック・レスポンス検証を備える。
- ツール:
  - ペーパートレード検証レポート生成スクリプト（kabusys.tools.paper_verification_report）。

セットアップ
----------

1. Python
   - Python 3.10+ を想定（typing 機能などを使用）。
2. 依存パッケージ（例）
   - duckdb, psutil, openai, PyYAML（config 検証時に必要）
   - 例: pip install duckdb psutil openai PyYAML
   - （プロジェクトに requirements.txt がある場合は pip install -r requirements.txt を推奨）
3. リポジトリルート構成を維持してクローンまたは配置（この README は src/kabusys 下のモジュールを前提とします）。
   - 開発時は PYTHONPATH を src に向けるか、パッケージをインストールしてください:
     - 例: export PYTHONPATH=$(pwd)/src
     - または pip install -e .

環境変数 / .env
----------------
.env を使用して設定を管理します。対話形式で生成するには次を実行してください:

- .env 作成ウィザード:
  - python -m kabusys.config_setup

必須（最低限）:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）

有用な環境変数の一覧（主なもの）:
- KABUSYS_ENV: development | paper_trading | live（default: development）
- DUCKDB_PATH: 分析用 DuckDB（default: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（default: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（default: data/paper_trading.db）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR (default: INFO)
- LOG_DIR: ログ保存ディレクトリ（default: logs）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合に必須）
- PAPER_FILL_MODE: paper_trading 時の MockBroker の応答方法（instant|partial|never|reject、default: instant）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、default: 60）

設定検証:
- python -m kabusys.validate_config
  - --strict を付けると警告があっても exit(1) になります。

使い方（主要スクリプト）
-----------------------

注意: パッケージがインポート可能な状態であること（PYTHONPATH または pip install -e .）。

1. 監視ループ起動（本番想定）
   - python -m kabusys.run_monitoring
   - 動作:
     - ログ設定を行い（logs/monitoring.log）、プロセス優先度を high に設定（可能な場合）。
     - Settings から sqlite_path（monitoring DB）・duckdb_path を読み、Monitoring DB を初期化。
     - SystemMonitor.check_once() をポーリング実行。
     - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）。
     - 監視は常に「本番用」sqlite_path を使う（KABUSYS_ENV に関係なく）。

2. 実行エンジン起動（ExecutionEngine）
   - python -m kabusys.run_execution
   - 動作:
     - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し、data/paper_trading.db を利用（本番 DB と完全分離）。
     - broker client の生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
     - data/stop_requested.flag を検知すると安全に停止。
     - PID ファイル: data/execution.pid（設定に応じて変更可）

3. ペーパートレード検証レポート
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - デフォルト DB: env または data/paper_trading.db

4. AI 関連（プログラムから呼び出す）
   - ニュースセンチメント: from kabusys.ai import score_news
     - score_news(conn, target_date, api_key=None)
     - OpenAI API キーが必要（api_key 引数または OPENAI_API_KEY 環境変数）
   - レジーム判定: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

ログ
---
- ログはデフォルトで logs/<app_name>.log（TimedRotatingFileHandler）に日次ローテートで保存されます。
- ログディレクトリは LOG_DIR 環境変数または setup_logging の引数で指定可能。
- ログレベルは LOG_LEVEL 環境変数で制御。

運用上のファイル / フラグ
------------------------
- data/stop_requested.flag — run_execution/run_monitoring が検知する停止フラグ（手動で作成すると安全に停止）。
- data/kill.flag — KillSwitch が書き込むと ExecutionEngine に停止を促す（設定により起動時に自動クリア可）。
- data/execution.pid — Execution エンジンの PID（デフォルト設定場所）。
- DB ファイル:
  - data/kabusys.duckdb（分析用）
  - data/monitoring.db（監視用 SQLite）
  - data/paper_trading.db（paper_trading 用 SQLite）

ディレクトリ構成（主要ファイル）
--------------------------------
src/
  kabusys/
    __init__.py
    config.py                      # 環境変数 / Settings
    config_setup.py                # .env 対話ウィザード
    validate_config.py             # 設定検証 CLI
    run_monitoring.py              # 監視ループ起動スクリプト
    run_execution.py               # Execution エンジン起動スクリプト

    ai/
      news_nlp.py                  # ニュース NLP（OpenAI）によるスコアリング
      regime_detector.py           # レジーム判定（MA + マクロセンチメント）

    monitoring/
      monitoring_db.py             # monitoring DB 層（SQLite 用）
      system_monitor.py            # システム状態・データ鮮度監視
      trade_monitor.py             # 発注ログ監視（滞留注文など）※実装ファイルあり
      risk_monitor.py              # ドローダウン / ポジション上限監視
      monitoring_engine.py         # 各 Monitor を束ねるエンジン
      kill_switch.py               # Kill Switch

    execution/                      # 発注エンジン関連（BrokerFactory, Engine, OrderManager 等）
      ...

    portfolio/
      portfolio_builder.py          # 候補選定・等分配/スコア加重
      position_sizing.py            # 株数決定（リスクベース等）
      risk_adjustment.py            # セクターキャップ・レジーム乗数

    research/
      factor_research.py            # ファクター計算（momentum, volatility, value）
      feature_exploration.py        # 将来リターン, IC, 統計サマリ

    data/                           # データパイプライン・DuckDB 用コード等
      pipeline.py

    tools/
      paper_verification_report.py  # Paper Trading 検証レポート

    utils/
      logging_setup.py              # ログ設定ユーティリティ
      process_priority.py           # プロセス優先度 / CPU affinity

補足・運用上の注意
------------------
- KABUSYS_ENV の設定に注意:
  - live に設定する場合は必須環境変数や通知設定（LINE など）を十分確認してください。
- MONITOR は監視用途のため、run_monitoring は監視 DB（SQLITE_PATH）を常に本番パスとして使用します。開発時の取り扱いに注意してください。
- AI 機能を使用するには OPENAI_API_KEY が必要です。API 呼び出しに対してはリトライ・レスポンス検証が実装されていますが、API 利用量に注意してください。
- process_priority（高優先度設定）は OS 権限やプラットフォーム依存で失敗する場合があります（AccessDenied など）。その場合は警告ログを確認してください。
- DuckDB / SQLite のファイルは適切なバックアップポリシーを用意してください。

よくある操作例
--------------
- .env を作成:
  - python -m kabusys.config_setup
- 設定を検証:
  - python -m kabusys.validate_config
- 監視起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- 実行エンジン起動:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

ライセンス / バージョン
-----------------------
- パッケージバージョンは kabusys.__version__ で参照できます（現状 0.1.0）。

お問い合わせ / 開発
-------------------
- 開発者向け: src を PYTHONPATH に追加するか、pip install -e . してパッケージを開発インストールしてください。
- 各モジュールはユニットテストを想定した設計（純粋関数・外部依存の注入、API 呼び出し箇所の差し替え可能）になっています。テストを書く際はモックで外部依存を置き換えてください。

以上が README の概略です。必要ならば「インストール手順をもっと詳細に」「systemd / supervisor 用のサンプル unit」や「config ファイル（config/*.yaml）の説明」を追記します。どちらを優先しましょうか？