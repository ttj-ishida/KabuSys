KabuSys — README
=================

概要
----
KabuSys は日本株向けの自動売買 / リサーチ / 監視を行う小規模なシステムです。本リポジトリには以下の主要機能を提供するモジュールが含まれます。

- ExecutionEngine：ブローカーとの発注・状態管理（本番/ペーパートレード切替対応）
- Monitoring：システム稼働状態・注文挙動・リスク・キルスイッチの常時計測とアラート
- AI（news_nlp / regime_detector）：OpenAI を用いたニュースセンチメント・市場レジーム判定
- Research：DuckDB を用いたファクター計算・特徴量解析
- Portfolio：銘柄選定・配分・ポジションサイズ計算（純粋関数群）
- Tools：ペーパートレード検証レポート生成などのユーティリティスクリプト

主な特徴
--------
- 本番・ペーパートレードを環境変数 KABUSYS_ENV（development / paper_trading / live）で切替。
- ペーパートレード時は MockBroker を利用し、データベースは本番と完全分離（data/paper_trading.db）。
- 監視（Monitoring）は別プロセスで動き、SQLite に監視ログを永続化（data/monitoring.db 等）。
- LINE を使ったアラート送信機能（AlertManager）。
- OpenAI（gpt-4o-mini）を用いたニュースセンチメントとレジーム判定（API キー必須）。
- Streamlit ベースの監視ダッシュボードを同梱（read-only で監視 DB を参照）。

セットアップ
----------
前提
- Python 3.10 以上（PEP 604 の型表記などを使用）
- SQLite3（通常は標準ライブラリ）
- DuckDB（duckdb Python パッケージ）
- psutil, requests, openai, streamlit など（以下のコマンドでインストールを推奨）

例（仮の requirements がない場合）:
    python -m pip install duckdb psutil requests openai streamlit

セットアップ手順（ローカル実行向け）
1. リポジトリをクローン：
    git clone <repo-url>
2. パッケージをソース開発モードでインストール（任意）：
    cd <repo>
    python -m pip install -e .
   あるいは、直接 Python 実行時に PYTHONPATH=src を指定：
    PYTHONPATH=src python -m kabusys.run_monitoring
3. 環境変数の準備：
   プロジェクトルートに .env / .env.local を置くことが可能です（自動読み込みされます）。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセット。

代表的な環境変数（用途に応じて設定してください）
- KABUSYS_ENV: execution のモード（development / paper_trading / live）
- OPENAI_API_KEY: OpenAI API キー（AI 関連機能で必須）
- JQUANTS_REFRESH_TOKEN: J-Quants API（research 用）
- KABU_API_PASSWORD: kabuステーション API パスワード（発注に必要）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレーディング用 SQLite（デフォルト: data/paper_trading.db）
- MONITOR_POLL_INTERVAL: Monitoring ポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: ペーパートレード時の約定振る舞い ("instant"|"partial"|"never"|"reject")

使い方（主要スクリプト）
--------------------

1) 監視プロセス（Monitoring）
- 概要: SystemMonitor を定期実行し、system_status / trade_logs / risk_logs / dashboard 等に記録します。
- 起動コマンド（プロジェクトルートから）:
    PYTHONPATH=src python -m kabusys.run_monitoring
  例（ポーリング間隔を 30 秒に変更）:
    MONITOR_POLL_INTERVAL=30 PYTHONPATH=src python -m kabusys.run_monitoring
- 停止: プロジェクトルートの data/stop_requested.flag を作成すると、ループは検知して終了します。

注意:
- run_monitoring は KABUSYS_ENV に関わらず本番用 sqlite_path（Settings.sqlite_path）を使用します。

2) 実行エンジン（ExecutionEngine）
- 概要: ブローカークライアントを生成し、注文・リスク管理・リコンシリエーション等を行います。KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 DB に書き込みます。
- 起動コマンド:
    PYTHONPATH=src python -m kabusys.run_execution
- 停止:
  - data/stop_requested.flag を作成すると安全に停止処理が入ります。
  - kill.flag（Settings.kill_flag_path、デフォルト data/kill.flag）は KillSwitch により書き込まれ、ExecutionEngine に停止シグナルを送る用途に使われます。
- PID ファイル: data/execution.pid（Settings.pid_file_path）を使用し、SystemMonitor は実行中のプロセス検出に利用します。

3) Streamlit ダッシュボード（監視 UI）
- コマンド例:
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- 読み取り専用 URI モードで SQLite を開きます。MonitoringEngine が起動していないと DB が存在しない旨のエラーを表示します。

4) Paper Trading 検証レポート（tools）
- スクリプト:
    python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
- 例:
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- 機能: system_status / trade_logs / risk_logs の集計を行い、稼働率・注文成功率・レイテンシ等を評価して PASS/FAIL 判定を出力します。

設定・挙動のポイント
-------------------
- .env の読み込み:
  プロジェクトルートに .env / .env.local があれば自動で読み込みます（OS 環境変数が優先されます）。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
- Settings クラス:
  環境変数の検証・既定値・パス解決を行います。必須値（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD など）を要求するプロパティがあり、アクセス時に存在しない場合は例外を投げます。
- Paper Trading 分離:
  run_execution は KABUSYS_ENV=paper_trading のとき paper_sqlite_path を使用し、本番 DB に影響を与えないようにしています。PAPER_FILL_MODE により MockBroker の約定挙動を制御可能です。
- 監視 DB マイグレーション:
  init_monitoring_db は idempotent にテーブルを作り、既存 DB にないカラム（peak_value, latency_ms）を追加するマイグレーション処理を含みます。
- プロセス優先度:
  起動時に set_process_priority("high") を呼び出しますが、権限や OS により失敗する可能性があり、その場合は警告を出して継続します（psutil を使用）。

ディレクトリ構成（主要ファイル）
------------------------------
src/
  kabusys/
    __init__.py
    config.py                         # 環境変数 / 設定管理
    run_monitoring.py                 # Monitoring のエントリポイント
    run_execution.py                  # ExecutionEngine のエントリポイント

    ai/
      news_nlp.py                     # ニュースセンチメント（OpenAI）
      regime_detector.py              # 市場レジーム判定（OpenAI）
      __init__.py

    monitoring/
      monitoring_db.py                # SQLite 永続化層（system_status, trade_logs, ...）
      system_monitor.py               # システム稼働 / データ鮮度監視
      trade_monitor.py                # 注文滞留・約定異常監視
      risk_monitor.py                 # ドローダウン・ポジション上限監視
      kill_switch.py                   # kill.flag 書き込みロジック
      alert_manager.py                # LINE push 通知
      monitoring_engine.py            # 各 Monitor の束ね（run loop / run_once）
      streamlit_dashboard.py          # streamlit ダッシュボード
      __init__.py

    execution/
      reconciler.py                    # 起動時リコンシリエーション
      order_manager.py                 # 発注フローの外向き API
      order_repository.py              # DB 操作（別ファイルの想定）
      order_record.py                  # OrderRecord / 状態列挙（別ファイル）
      broker_factory.py                # Broker client 作成（別ファイル）
      execution_engine.py              # ExecutionEngine 本体（別ファイル）
      risk_manager.py                  # リスク管理（別ファイル）
      __ (その他多くの実装想定) __

    research/
      factor_research.py               # ファクター計算（DuckDB）
      feature_exploration.py           # IC / forward returns / summary
      __init__.py

    portfolio/
      portfolio_builder.py             # 候補選定・重み算出
      position_sizing.py               # 株数計算・キャップ処理
      risk_adjustment.py               # セクターキャップ・レジーム乗数
      __init__.py

    tools/
      paper_verification_report.py     # Paper Trading 検証レポート
      __init__.py

    utils/
      process_priority.py              # プロセス優先度 & CPU affinity ユーティリティ
      __init__.py

data/                                  # 実行時に使用／生成されるディレクトリ（git 管理外想定）
  kabusys.duckdb                       # DUCKDB_PATH
  monitoring.db                         # SQLITE_PATH（監視）
  paper_trading.db                      # PAPER_TRADING_SQLITE_PATH（ペーパートレード）
  execution.pid                         # PID ファイル
  stop_requested.flag                   # 手動停止フラグ（run_*.py が監視）
  kill.flag                             # KillSwitch が書き込む停止フラグ

運用上の注意・トラブルシューティング
---------------------------------
- ファイル権限: data ディレクトリへ書き込み権限が必要です。PID ファイルや flag ファイルの作成・削除で失敗する場合は権限を確認してください。
- プロセス優先度設定: Linux/macOS で nice 値や Windows の優先度変更が権限不足で失敗することがあります（警告のみで継続します）。
- OpenAI 呼び出し: API のレート制限や一時的なエラーはリトライロジックでハンドルされますが、API キー未設定の場合は例外を投げる箇所があります（ai モジュール呼び出し時）。
- DuckDB / SQLite: DB ファイルパスは Settings で指定できます。streamlit など読み取り専用で開く場合は URI の ?mode=ro を使っています。
- テスト: 主要な AI 呼び出し部分はモックしやすい設計（_call_openai_api の差し替え等）になっています。ユニットテストを書く際はモック／パッチを活用してください。

ライセンス / 貢献
-----------------
本リポジトリのライセンス・貢献ルールはリポジトリルートの LICENSE / CONTRIBUTING を参照してください（存在しない場合は管理者に問い合わせてください）。

最後に
------
この README はコードベースの主要な使い方・構成をまとめたものです。より詳しい設計意図やアルゴリズムの説明（PortfolioConstruction.md, StrategyModel.md, etc.）は別途ドキュメントとして同梱されていることを想定しています。実行時の具体的な環境変数例・運用手順は運用ドキュメントに追記してください。