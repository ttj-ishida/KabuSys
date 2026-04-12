KabuSys — 日本株自動売買システム
=================================

本ドキュメントは、このリポジトリ内の主要モジュール群（実行エンジン・監視・ポートフォリオ構築・リサーチ・AI補助など）を簡潔に説明し、開発 / 運用のためのセットアップ・実行手順をまとめた README です。

プロジェクト概要
---------------
KabuSys は日本株の自動売買システムの骨格を提供する Python パッケージです。主な機能は次の通りです。

- 実行エンジン（ExecutionEngine）: ブローカー API 経由での発注・注文管理、リスク制御、再起動時のリコンシリエーション
- 監視（Monitoring）: システム状態・注文滞留・約定異常・ドローダウン監視、LINE へのアラート送信、kill フラグによる安全停止
- ポートフォリオ構築: 候補選定、重み計算、ポジションサイズ算出、セクター制限・レジーム乗数
- リサーチ: ファクター計算（モメンタム / ボラティリティ / バリュー）、特徴量探索、IC 計算
- AI 補助: ニュース NLP による銘柄別センチメント（OpenAI）および市場レジーム判定
- 運用ツール: Paper Trading 検証レポート生成、Streamlit ベースの監視ダッシュボード

主な機能一覧
-------------
- Execution:
  - 起動スクリプト: python -m kabusys.run_execution
  - Paper Trading モードでは MockBrokerClient を使用し、本番 DB と分離して data/paper_trading.db に記録
- Monitoring:
  - 起動スクリプト: python -m kabusys.run_monitoring
  - system_status / trade_logs / positions / risk_logs / dashboard を SQLite に永続化
  - kill.flag による ExecutionEngine 停止シグナルを生成
  - LINE によるプッシュ通知（AlertManager）
  - Streamlit ダッシュボード（src/kabusys/monitoring/streamlit_dashboard.py）
- Portfolio:
  - 候補選定、等分配 / スコア加重、リスク調整、ポジションサイズ計算（整数ロット処理・aggregate cap）
- Research:
  - DuckDB を用いた factor 計算（prices_daily / raw_financials を参照）
  - forward returns、IC、統計サマリ
- AI:
  - news_nlp.score_news(conn, target_date, api_key=None)
  - regime_detector.score_regime(conn, target_date, api_key=None)
  - OpenAI API（gpt-4o-mini）の呼び出しに対応（API キー必須）

必要条件（依存ライブラリ）
-----------------------
- Python 3.9+
- duckdb
- psutil
- requests
- streamlit (ダッシュボード実行時)
- openai (AI 機能利用時)
- sqlite3（標準ライブラリ）

（pip などでインストールしてください。例: pip install duckdb psutil requests streamlit openai）

設定（環境変数）
----------------
アプリケーション設定は環境変数または .env / .env.local で行います。自動で .env を読み込む仕組みがあり、プロジェクトルート（.git または pyproject.toml のあるディレクトリ）を探索して読み込みます。自動読み込みを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

主な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- OPENAI_API_KEY (AI 機能利用時に必要)
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
  - paper_trading の場合、Execution は専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (監視 DB、デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db)
- PID_FILE_PATH (デフォルト: data/execution.pid)
- KILL_FLAG_PATH (デフォルト: data/kill.flag)
- PAPER_FILL_MODE (paper_trading の MockBroker の約定挙動。instant / partial / never / reject)
- LOG_LEVEL (DEBUG / INFO / WARNING / ERROR / CRITICAL)
- MONITOR_POLL_INTERVAL (run_monitoring のポーリング間隔 秒、デフォルト 60。0 以下は無効扱いでデフォルトにフォールバック)

セットアップ手順
---------------
1. リポジトリをチェックアウト
2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate (Unix)
3. 依存パッケージをインストール
   - pip install duckdb psutil requests streamlit openai
4. .env を作成（.env.example を参考に必要項目を設定）
   - JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、（OPENAI_API_KEY など）

初回実行時に監視 DB の初期化が自動で行われます（init_monitoring_db）。monitoring DB のスキーマは冪等で作成され、必要に応じて簡単なマイグレーション（カラム追加）を行います。

使い方（実行例）
----------------

- Execution Engine を起動する
  - 通常（本番 / dev / paper_trading に応じて挙動が変わります）
    - KABUSYS_ENV=paper_trading を設定すると paper_trading 用の DB を使い、MockBrokerClient を動かします。
  - コマンド:
    - python -m kabusys.run_execution
  - 注意:
    - 起動時にプロセス優先度を "high" に設定します（psutil による操作）。権限不足で設定に失敗することがありますが、その場合は警告が出て処理は継続します。
    - PID を PID_FILE_PATH に書きます。監視側はこの PID を参照して Execution プロセスの生存確認を行います。

- Monitoring を起動する
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き（例: MONITOR_POLL_INTERVAL=120）
  - 監視は Settings による sqlite_path（監視 DB）を使用します（KABUSYS_ENV に依らず本番 sqlite_path を参照する設計の箇所に注意）。

- Streamlit ダッシュボード（監視情報閲覧）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 監視 DB を読み取り専用で開きます。MonitoringEngine が DB を作成してデータを書き込んでから閲覧してください。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH （PAPER_TRADING_SQLITE_PATH 環境変数で代替可能）
  - 出力: 稼働率、注文成功率、送信率、P95 レイテンシ等のサマリと PASS/FAIL 判定

- AI（ニュース NLP / レジーム判定）をプログラムから呼ぶ
  - from kabusys.ai import score_news
    - score_news(conn, target_date, api_key=None)
  - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, target_date, api_key=None)
  - 注: api_key 引数または環境変数 OPENAI_API_KEY が必要。未設定時は ValueError を送出します。
  - OpenAI API 呼び出しはネットワークエラーや 429/5xx をリトライする実装が入っていますが、API キーのレート制限等には注意してください。

重要な挙動・設計メモ
-------------------
- 環境分離:
  - KABUSYS_ENV=paper_trading の場合、Execution は data/paper_trading.db（既定）を使用し、本番監視 DB と完全に分離されます。
- kill.flag:
  - KillSwitch はリスク条件（ドローダウン、ポジション上限等）で data/kill.flag を書き出し ExecutionEngine に停止シグナルを送ります。起動時に設定でクリアすることができます（Settings.kill_flag_clear_on_start）。
- PID ファイル:
  - ExecutionEngine は PID を PID_FILE_PATH に書き込み、SystemMonitor はそれを参照してプロセスの存在・stale PID を検出します。stale PID は監視側で検出・削除され、risk_logs に記録されます。
- DB マイグレーション:
  - init_monitoring_db() はテーブル作成後に既存テーブルにカラムがない場合は ALTER TABLE でカラムを追加する簡易マイグレーションを行います（例: trade_logs.latency_ms, dashboard.peak_value）。
- Process Priority / CPU affinity:
  - 起動スクリプトは set_process_priority("high") を呼びます。プラットフォーム依存で失敗する可能性があります（権限不足や未対応 OS）。CPU affinity 設定関数も utils にありますが、明示的な呼び出しが必要です。
- DuckDB / prices データ:
  - research モジュールは DuckDB の prices_daily / raw_financials を参照して各種ファクターを計算します。DuckDB の DB ファイルパスは DUCKDB_PATH で設定します。

ディレクトリ構成（要約）
----------------------
（src/kabusys 配下の主要ファイル・サブパッケージを抜粋）

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数読み込み・Settings クラス
  - run_execution.py              — ExecutionEngine 起動スクリプト
  - run_monitoring.py             — SystemMonitor 単独起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート
  - ai/
    - news_nlp.py                 — ニュース NLP / OpenAI 呼び出し
    - regime_detector.py          — 市場レジーム判定
  - monitoring/
    - monitoring_db.py            — SQLite 層（init + MonitoringDB）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
    - streamlit_dashboard.py
  - execution/
    - order_manager.py
    - reconciler.py
    - ...（broker_factory などブローカー連携周りの実装）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - utils/
    - process_priority.py

ライセンス・貢献
----------------
本 README はコードベースの説明を目的とした内部ドキュメントです。外部利用や配布についてはリポジトリ付属の LICENSE を参照してください。バグ修正や機能改善の Pull Request は歓迎します。

補足（よくある質問）
-------------------
- Q: MONITOR_POLL_INTERVAL に 0 を入れると？
  - A: 0 以下は無効値として警告ログが出力され、デフォルト 60 秒にフォールバックします（time.sleep に 0 以下を渡すと ValueError のため）。

- Q: OpenAI API をローカルでテストしたい
  - A: OPENAI_API_KEY を設定してください。API 呼び出し部分はテスト時に差し替えやモックがしやすい設計（_call_openai_api を patch）になっています。

- Q: 監視 DB を別 DB にしたい
  - A: 環境変数 SQLITE_PATH を変更してください。monitoring 初期化は init_monitoring_db() により冪等に実行されます。

必要があれば実行コマンドの例や .env のテンプレート、各モジュールの API 使用例（関数呼び出しサンプル）を追記します。どの情報を優先して追加したいか教えてください。