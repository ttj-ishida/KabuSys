KabuSys — README
=================

概要
----
KabuSys は日本株の自動売買・リサーチ・監視モジュール群を含む軽量なトレーディングフレームワークです。  
本リポジトリは以下の主要な責務を持つコンポーネントで構成されています。

- ExecutionEngine（発注・リスク管理・リコンシリエーション）
- Monitoring（プロセス・注文・リスク監視、アラート、ダッシュボード）
- Portfolio（銘柄選定・配分・株数決定）
- Research（ファクター計算・特徴量解析）
- AI（ニュースセンチメント・市場レジーム判定）
- ユーティリティ（環境設定・プロセス優先度など）
- Tools（Paper Trading 検証レポート 等）

主な機能
--------
- 実運用／ペーパートレードの分離（KABUSYS_ENV により挙動を切替）
- 注文状態の永続化と再起動時のリコンシリエーション
- リスク監視（ドローダウン、ポジション上限、滞留注文、約定異常）
- システム監視（CPU/メモリ/ディスク、Execution プロセスの生存確認、データ鮮度）
- LINE へのアラートプッシュ（AlertManager）
- Streamlit を用いた監視ダッシュボード
- DuckDB を使ったファクター計算・リサーチモジュール
- OpenAI を用いたニュースセンチメント（AI モジュール）
- Paper Trading の検証レポート生成ツール

前提条件
--------
- Python 3.10+（typing の X | Y 表記を使用）
- 推奨パッケージ（例）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit
- SQLite（ローカルファイルで利用）
- ネットワーク（ブローカ API / OpenAI / LINE に接続する場合）

セットアップ手順
----------------
1. リポジトリをクローンして作業ディレクトリへ移動
   - 例: git clone ... && cd <repo>

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - 事前に requirements.txt があれば: pip install -r requirements.txt
   - ない場合は主要ライブラリを個別に:
     pip install duckdb psutil requests openai streamlit

4. 環境変数設定
   - プロジェクトルート (.git または pyproject.toml があるディレクトリ) に .env / .env.local を置くと自動読み込みされます（既存 OS 環境変数は保護されます）。
   - 自動ロードを無効化するには: export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   - 重要な環境変数（例）
     - KABUSYS_ENV: development | paper_trading | live  （デフォルト: development）
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - OPENAI_API_KEY（AI 機能利用時）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（監視アラート送信）
     - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
     - DUCKDB_PATH（DuckDB ファイル、デフォルト: data/kabusys.duckdb）
     - PAPER_TRADING_SQLITE_PATH（ペーパートレード専用 DB、デフォルト: data/paper_trading.db）
     - PAPER_FILL_MODE（paper_trading 時の約定挙動: instant | partial | never | reject、デフォルト: instant）
   - その他の設定は kabusys.config.Settings を参照してください（ログレベルやしきい値など多数）。

使い方（実行例）
----------------

1. ExecutionEngine を起動（本番 / ペーパー切替は KABUSYS_ENV に依存）
   - 環境例:
     export KABUSYS_ENV=paper_trading
     export OPENAI_API_KEY=...
     export KABU_API_PASSWORD=...
   - 実行:
     python -m kabusys.run_execution
   - 補足:
     - KABUSYS_ENV=paper_trading の場合、MockBrokerClient が使用され、data/paper_trading.db に書き込みます（本番 DB と完全分離）。
     - 起動時にプロセス優先度を "high" に設定します（set_process_priority）。

2. Monitoring（ポーリングループ）を起動
   - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60）。
   - 実行:
     python -m kabusys.run_monitoring
   - 注意:
     - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用します（運用監視は本番 DB を参照）。

3. Streamlit ダッシュボード（監視UI）
   - 実行:
     streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - 既存の monitoring.db を read-only で開きます。MonitoringEngine を先に起動して DB を作成しておく必要があります。

4. Paper Trading 検証レポート生成ツール
   - 使い方:
     python -m kabusys.tools.paper_verification_report
     python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - オプション:
     --db で PAPER_TRADING_SQLITE_PATH を上書き可能（デフォルト data/paper_trading.db）

5. AI 関連（ニューススコア・レジーム判定）
   - プログラムから直接呼び出し:
     from kabusys.ai.news_nlp import score_news
     from kabusys.ai.regime_detector import score_regime
   - それぞれ DuckDB 接続（duckdb.connect(...)）と target_date, api_key を渡して使用します。
   - OpenAI API キーが必要です（api_key 引数または環境変数 OPENAI_API_KEY）。

運用上の注意
-------------
- kill.flag による停止:
  - KillSwitch はリスク条件（ドローダウン等）で data/kill.flag を作成し ExecutionEngine に停止を指示できます。
  - ExecutionEngine 起動時に kill flag を消去する挙動は Settings.kill_flag_clear_on_start に依存します。
- PID ファイル:
  - ExecutionEngine は起動時に pid file（デフォルト data/execution.pid）を作成します。SystemMonitor はこの pid を見てプロセスの生存確認を行います。
- DB マイグレーション:
  - monitoring_db.init_monitoring_db は必要なテーブルとインデックスを冪等で作成します。既存 DB に列が無い場合の簡単な ALTER も行います。

開発向け / .env の取り扱い
--------------------------
- 環境変数は読み込み順: OS 環境 > .env.local > .env（自動ロード時）。
- .env のパースはシェル風（export KEY=val, quoted values, inline comments の扱い）に対応しています。
- テスト等で自動ロードを無効にする:
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

ディレクトリ構成（主要ファイル）
------------------------------
以下は主要モジュールの構成（src/kabusys 内）です。実際のツリーはリポジトリで確認してください。

- src/kabusys/
  - __init__.py
  - config.py                       — 環境変数/設定管理
  - run_execution.py                — ExecutionEngine 起動スクリプト
  - run_monitoring.py               — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py   — Paper Trading 検証レポート CLI
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - broker_factory.py
    - ... （発注関連モジュール）
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - alert_manager.py
    - kill_switch.py
    - streamlit_dashboard.py
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
  - utils/
    - process_priority.py

モニタリング DB スキーマ（概要）
------------------------------
- system_status: CPU/メモリ/ディスク/プロセス状態 の時系列
- trade_logs: 発注イベントログ（logged_at, event_type, client_order_id, code, side, qty, price, filled_qty, state, latency_ms）
- positions: 現在の保有（code, qty, avg_price, current_price, updated_at）
- risk_logs: リスクイベント（DRAWDOWN_ALERT, STALE_ORDER, PRICE_ANOMALY 等）
- dashboard: 集計（portfolio_value, cash, drawdown_pct, open_order_count, position_count, peak_value）

その他メモ
---------
- 多くの処理はフェイルセーフ設計（API 失敗時はログを残してフォールバック）になっています。例えば AI 呼び出し失敗時はスコアを 0 にフォールバックする等。
- ログレベルやしきい値は環境変数で調整可能です（Settings を参照）。
- DuckDB を利用するリサーチ系はローカルデータ（prices_daily, raw_financials, raw_news 等）に依存します。これらのテーブル準備が必要です。

貢献・テスト
------------
- 新機能追加や修正はブランチを切って Pull Request を作成してください。
- ユニットテストは各モジュールの純粋関数（portfolio / research 等）から追加することを推奨します。

ライセンス
----------
（ライセンス情報がある場合はここに記載してください）

問い合わせ
----------
不明点や質問があればコード内のドキュメンテーションコメントを参照するか、リポジトリの Issue にてお問い合わせください。

---  
以上が本プロジェクトの概要と使い方です。README に追加したい具体的なコマンドや環境変数の詳細があれば教えてください。