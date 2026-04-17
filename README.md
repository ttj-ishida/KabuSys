README
=====

概要
----
KabuSys は日本株向けの自動売買 / 研究 / 監視を目的とした Python ベースの小規模フレームワークです。  
主な機能は、注文実行エンジン（ExecutionEngine）、監視コンポーネント（MonitoringEngine）、ポートフォリオ構築・ポジション決定ロジック、ファクター計算・研究ツール、そして AI を用いたニュースセンチメント評価などを含みます。

特徴（機能一覧）
----------------
- Execution
  - ExecutionEngine を通じた発注フロー（OrderManager / RiskManager / Reconciler 等）
  - paper_trading モード（モックブローカーを使用、実運用 DB と分離）
  - 再起動時のリコンシリエーション（起動時の注文・ポジション同期）

- Monitoring
  - システム状態監視（CPU / メモリ / ディスク / Execution プロセス検出）
  - 注文滞留・約定価格異常の検出
  - ドローダウン・ポジション上限監視と kill.flag による停止シグナル発行
  - LINE による通知（AlertManager）
  - Streamlit ベースの監視ダッシュボード

- Portfolio
  - 候補選定・重み計算（等分配・スコア加重）
  - セクター上限適用、レジーム乗数
  - ポジションサイズ計算（単元株丸め、リスクベース等）

- Research / Data
  - DuckDB を用いたファクター計算（モメンタム／バリュー／ボラティリティ等）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー

- AI
  - OpenAI を使ったニュースセンチメント（ai_scores への書き込み）
  - マクロニュース＋ETF MA200 を組み合わせた市場レジーム判定

セットアップ手順
----------------
前提
- Python 3.10 以上（型ヒントに PEP 604 の | 記法を利用）
- SQLite（標準ライブラリ）、DuckDB、外部ライブラリが必要

推奨パッケージ（例）
- duckdb
- psutil
- openai
- requests
- streamlit

pip でのインストール例:
    pip install duckdb psutil openai requests streamlit

リポジトリ初期化
1. プロジェクトルートに移動（README が配置される想定）  
2. data ディレクトリを作成（必要に応じて）:
    mkdir -p data

環境変数設定
- .env または環境変数で設定できます。自動ロード機能によりプロジェクトルートの .env / .env.local を読み込みます（テスト時等に無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。

主要な環境変数（必須 / 重要）
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants API 用トークン
- KABU_API_PASSWORD (必須) — kabuステーション API 用パスワード
- OPENAI_API_KEY — OpenAI 呼び出しに必要
- KABUSYS_ENV — 環境。development / paper_trading / live（デフォルト: development）
  - paper_trading を指定すると Execution は MockBroker を使い、DB は data/paper_trading.db を使用
- PAPER_FILL_MODE — paper_trading 時の約定振る舞い（instant|partial|never|reject、デフォルト: instant）
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- PID_FILE_PATH — Execution の PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH — kill.flag のパス（デフォルト: data/kill.flag）
- MONITOR_POLL_INTERVAL — Monitoring のポーリング間隔（秒、デフォルト: 60）
- LOG_LEVEL — ログレベル（DEBUG|INFO|...、デフォルト: INFO）

使い方（実行例）
----------------

1) 監視ループ起動（Monitoring）
- デフォルトで production 相当の監視 DB（Settings.sqlite_path）を使用して動作します。ポーリング間隔は MONITOR_POLL_INTERVAL で上書き可能（秒）。

起動:
    python -m kabusys.run_monitoring

例（30秒間隔）:
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

停止:
- プロセスは Ctrl+C でも停止します。またプロジェクトルート/data/stop_requested.flag を作成すると安全にループを抜けて終了します。

2) 実行エンジン起動（Execution）
- KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、paper_trading 用 DB に記録します（本番 DB と分離）。

起動:
    python -m kabusys.run_execution

例（ペーパートレード）:
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution

停止:
- data/stop_requested.flag を作成すると ExecutionEngine に停止指示が送られます。KillSwitch が作動すると data/kill.flag が作られ、外部的にエンジンを停止させる運用も可能です。

3) Paper Trading 検証レポート（ツール）
- paper_trading DB の内容を集約して検証レポートを標準出力に出します。

実行例:
    python -m kabusys.tools.paper_verification_report
期間指定:
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
DB 指定:
    python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

4) 監視ダッシュボード（Streamlit）
- データベースを読み取り専用で開き、ダッシュボードを表示します。

起動例:
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

5) AI 関連
- ニューススコアリング / レジーム判定は OpenAI API キーを必要とします。モジュール API をプログラムから呼び出して利用できます（例: kabusys.ai.score_news）。

運用上の注意
- run_monitoring は KABUSYS_ENV に関係なく設定された sqlite_path（本番用）を監視に使用します。実行エンジンは env に応じて DB を切り替えます（paper_trading）。
- Process 優先度は起動時に set_process_priority("high") を試みます（権限不足などで警告が出る場合があります）。
- kill.flag / stop_requested.flag / execution.pid などのファイルは data/ 配下に作成されます。ファイルの存在でプロセス制御を行います。

ディレクトリ構成（主なファイル説明）
----------------------------------
src/kabusys/
- __init__.py
  - パッケージ初期化、バージョン等

- config.py
  - 環境変数・設定の読み込みと Settings クラス（.env 自動ロード、各種パス・設定取得）

- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL で間隔制御）

- run_execution.py
  - ExecutionEngine 起動スクリプト（paper_trading 時は MockBroker を使用）

- ai/
  - news_nlp.py — OpenAI を用いてニュースのセンチメントを算出・ai_scores に書き込む
  - regime_detector.py — MA200 とマクロニュースを組み合わせて市場レジーム判定

- monitoring/
  - monitoring_db.py — SQLite テーブル作成・読み書き用クラス（MonitoringDB）
  - system_monitor.py — システム状態・データ鮮度チェック
  - trade_monitor.py — 注文滞留・約定異常チェック
  - risk_monitor.py — ドローダウン・ポジション上限チェック
  - kill_switch.py — kill.flag の生成・管理
  - alert_manager.py — LINE Push 通知ラッパー
  - monitoring_engine.py — 各モニタの統合ランナー
  - streamlit_dashboard.py — Streamlit ダッシュボード

- execution/
  - order_manager.py — 注文作成・状態遷移管理
  - reconciler.py — 起動時の注文・ポジション同期
  - （その他 execution 関連コンポーネント：broker_factory, order_repository 等）

- portfolio/
  - portfolio_builder.py — 候補選定・重み計算
  - position_sizing.py — 発注株数算出
  - risk_adjustment.py — セクターキャップ・レジーム乗数

- research/
  - factor_research.py — ファクター計算（momentum/value/volatility）
  - feature_exploration.py — 将来リターン、IC、統計サマリー
  - __init__.py — 研究用 API エクスポート

- tools/
  - paper_verification_report.py — Paper Trading 検証レポート出力ツール

- utils/
  - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

data/
- デフォルトの DB / PID / フラグファイル等が格納されるディレクトリ（例: data/monitoring.db, data/paper_trading.db, data/execution.pid, data/kill.flag, data/stop_requested.flag）

補足（よくある操作）
------------------
- stop_requested.flag の設置で安全に run_monitoring / run_execution を停止できます。
- kill.flag は KillSwitch により生成され、エンジン停止のトリガーとして扱います。手動で削除することも可能です（KillSwitch.clear 相当）。
- Paper トレード環境を完全に分離したい場合は KABUSYS_ENV=paper_trading と PAPER_TRADING_SQLITE_PATH を利用してください。

ライセンス・貢献
----------------
本 README はコードベースから抽出した情報に基づき作成しています。実際の利用時はテスト環境で十分に検証のうえ運用してください。貢献・バグ報告はリポジトリの PR / Issue にお願いします。