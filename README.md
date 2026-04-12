KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株の自動売買・研究・監視を目的としたモジュール群です。  
DuckDB / SQLite を用いたデータ処理、バックテスト・ファクター計算、発注エンジン（ExecutionEngine）、監視エンジン（MonitoringEngine）、LLM を用いたニュースセンチメント評価などの機能を持ちます。

主な特徴
--------
- ExecutionEngine：ブローカー抽象化（実運用 / ペーパートレード対応）、発注管理、リスク管理、再同期（Reconciler）
- Monitoring：システム監視（CPU/メモリ/ディスク・プロセス生存）、注文滞留・約定異常・ドローダウン監視、LINE によるアラート送信
- AI モジュール：OpenAI を用いたニュースセンチメント（news_nlp）・市場レジーム判定（regime_detector）
- Research：DuckDB 上でのファクター計算（Momentum / Volatility / Value）・IC計算など
- Portfolio：候補選定、重み計算、ポジションサイズ決定、セクター制限・レジーム乗数など（純粋関数群）
- 運用ツール：Paper Trading 検証レポート生成、Streamlit 監視ダッシュボード
- 設定管理：.env 自動読み込み（プロジェクトルート検出）、環境ごとの挙動切替（KABUSYS_ENV）

動作環境
--------
- Python 3.10+
- 主要依存パッケージ（抜粋）:
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit (監視ダッシュボード利用時)
- SQLite（標準ライブラリで利用）

セットアップ手順
----------------
1. リポジトリをチェックアウト：
   - git clone <repo-url>
   - cd <repo-root>

2. 仮想環境作成（推奨）：
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール：
   - pip install duckdb psutil requests openai streamlit
   - （プロジェクトに requirements.txt があれば pip install -r requirements.txt）

4. 環境変数（.env）を準備：
   - プロジェクトルートに .env / .env.local を置くと自動で読み込まれます（既存 OS 環境変数は保護）。
   - 自動ロードを無効にする場合：KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

   主要な環境変数例:
   - JQUANTS_REFRESH_TOKEN=...
   - KABU_API_PASSWORD=...
   - OPENAI_API_KEY=...        （AI 機能使用時に必須）
   - KABUSYS_ENV=development|paper_trading|live  （デフォルト: development）
   - SQLITE_PATH=data/monitoring.db
   - DUCKDB_PATH=data/kabusys.duckdb
   - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
   - PAPER_FILL_MODE=instant|partial|never|reject  （paper_trading 用）
   - LINE_CHANNEL_ACCESS_TOKEN=...  （監視アラート送信）
   - LINE_USER_ID=...
   - LOG_LEVEL=INFO

5. データディレクトリを作成：
   - mkdir -p data

注意:
- .env のパースはシェルライク（export KEY=val, クォート、コメント処理など）に対応します。
- Settings クラスがアプリケーションの設定をラップしています（kabusys.config.Settings）。

使い方
------

実行（ExecutionEngine）
- 本番 / 開発 / paper_trading を Settings.env（KABUSYS_ENV）で切替。
- 実行コマンド：
  - python -m kabusys.run_execution
  - run_execution は起動時にプロセス優先度を "high" に設定します。
- Paper trading:
  - KABUSYS_ENV=paper_trading にすると MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ全記録を行い本番DBと分離します。
  - PAPER_FILL_MODE 環境変数で模擬約定挙動（instant, partial, never, reject）を指定可能。

監視（Monitoring）
- ポーリングループ起動:
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能。デフォルト 60 秒。
- 監視は Settings.sqlite_path（デフォルト data/monitoring.db）にログを永続化します（run_monitoring は環境に関わらず本番 sqlite_path を使用する仕様）。
- run_monitoring も起動時にプロセス優先度を high に設定します。

Streamlit ダッシュボード
- 起動:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- ダッシュボードは監視 DB を read-only モードで開き、ダッシュボード/ポジション/注文/システム情報を表示します。

Paper Trading 検証レポート
- レポート生成:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db data/paper_trading.db
- 出力は標準出力に要約（稼働率・注文成功率・送信率・レイテンシ等）と PASS/FAIL 判定を表示します。

AI（ニュース / レジーム判定）
- ニュースセンチメント:
  - 関数: kabusys.ai.score_news(conn, target_date, api_key=None)
  - OpenAI API キーが必要（api_key 引数または OPENAI_API_KEY 環境変数）。
- 市場レジーム:
  - 関数: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - DuckDB 上の prices_daily / raw_news を参照し、ma200 とマクロセンチメントを合成して market_regime テーブルへ書き込みます。
- 両者とも外部 API の一時エラー（レート制限等）に対して指数バックオフでリトライし、失敗時はフェイルセーフ（代替値）で継続する設計です。

ライブラリ / 研究 API（例）
- ファクター計算:
  - kabusys.research.calc_momentum(conn, target_date)
  - kabusys.research.calc_volatility(conn, target_date)
  - kabusys.research.calc_value(conn, target_date)
- 特徴量探索:
  - kabusys.research.calc_forward_returns(...)
  - kabusys.research.calc_ic(...)
  - kabusys.research.factor_summary(...)

設定と挙動の補足
- Settings（kabusys.config.Settings）で設定値を取得します。KABUSYS_ENV は development / paper_trading / live のいずれか。
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング秒数（デフォルト 60）。
- kill.flag（Settings.kill_flag_path、デフォルト data/kill.flag）:
  - KillSwitch が条件を満たすとファイルを書き、ExecutionEngine に停止シグナルを与える。
  - ExecutionEngine 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時にフラグをクリアできます（Settings.kill_flag_clear_on_start）。
- PID ファイル（Settings.pid_file_path、デフォルト data/execution.pid）を用いたプロセス生存チェック。

ディレクトリ構成（主要ファイル・モジュール）
-----------------------------------------
src/kabusys/
- __init__.py
  - パッケージ定義（__version__）
- config.py
  - .env 自動ロード、Settings クラス（環境・パス・しきい値等）
- run_execution.py
  - ExecutionEngine 起動スクリプト（paper_trading モード対応）
- run_monitoring.py
  - SystemMonitor ポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL）
- tools/
  - paper_verification_report.py
    - ペーパートレード検証レポート生成 CLI
- data/ (想定)
  - kabusys.duckdb, monitoring.db, paper_trading.db など
- portfolio/
  - portfolio_builder.py — 候補選定・重み計算
  - position_sizing.py — 株数決定（単元丸め・リスク調整・aggregate cap）
  - risk_adjustment.py — セクター上限・レジーム乗数
- research/
  - factor_research.py — Momentum/Volatility/Value 等のファクター計算
  - feature_exploration.py — 将来リターン、IC、統計サマリ
- ai/
  - news_nlp.py — ニュースの LLM センチメント評価（ai_scores へ書き込み）
  - regime_detector.py — ETF MA + マクロセンチメントによるレジーム判定
- monitoring/
  - monitoring_db.py — SQLite による監視ログ永続化 / DB 初期化
  - system_monitor.py — CPU/メモリ/ディスク/データ鮮度/プロセスチェック
  - trade_monitor.py — 注文滞留／約定異常の検出
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - kill_switch.py — フラグファイルによる停止シグナル生成
  - alert_manager.py — LINE push による通知（クールダウン管理）
  - monitoring_engine.py — 各 Monitor を束ねるループ
  - streamlit_dashboard.py — Streamlit ベースの監視ダッシュボード
- execution/
  - order_manager.py — 発注ワークフロー（作成・送信・同期）
  - reconciler.py — 再起動時の照合・ポジション差分検出
  - （その他、ブローカー抽象などが存在する想定）
- utils/
  - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

開発・運用に関する注意点
-----------------------
- DB マイグレーション:
  - monitoring_db.init_monitoring_db は冪等にテーブル・インデックスを作成し、既存列の追加マイグレーションも行います。
- フェイルセーフ設計:
  - AI 呼び出しやブローカー API の一時失敗は多くの箇所で安全にフォールバック（0 相当、スキップ、ログ）するようになっています。
- 時刻・データの扱い:
  - LLM 向けのニュースウィンドウ・ファクター計算はルックアヘッドバイアスを防ぐ設計（内部で date.today() 等を参照しない箇所が多い）です。
- 権限:
  - set_process_priority では OS による権限不足があると警告に留めて処理を継続します。

サンプル運用フロー（簡易）
-------------------------
1. データロード（DuckDB に prices_daily / raw_financials / raw_news 等を準備）
2. 監視を常時起動:
   - python -m kabusys.run_monitoring
3. 実運用エンジンを起動:
   - python -m kabusys.run_execution
4. 日次でニューススコア・レジーム判定を実行（cron 等）:
   - Python スクリプト内で kabusys.ai.score_news / score_regime を呼び出す
5. 監視ダッシュボードで状況確認:
   - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

ライセンス・貢献
----------------
- 本 README ではライセンス情報を含めていません。実プロジェクトでは LICENSE を参照してください。  
- バグ報告・機能改善は Issue / PR で歓迎します。

最後に
------
この README はコードベースの主要設計・運用方法のサマリです。各モジュールには関数・クラスの docstring が充実しているため、詳細は該当ファイルを参照してください。必要ならば、各モジュール向けの詳細ドキュメント（API 例、設定例、運用手順）を追加で作成します。