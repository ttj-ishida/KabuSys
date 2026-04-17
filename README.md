KabuSys
======

日本株向けの自動売買システム（プロトタイプ）。  
このリポジトリは売買実行、監視、ポートフォリオ構築、リサーチ、ニュースNLP（OpenAI）などのコンポーネント群を含みます。  
（ソースは src/kabusys 以下にあります）

プロジェクト概要
---------------
KabuSys は次のような目的で設計されたモジュール群です。

- 売買実行エンジン（ExecutionEngine）と注文管理（OrderManager / OrderRepository）
- 監視基盤（System / Trade / Risk Monitor）とアラート（LINE push）
- Paper Trading モード（本番 DB と分離して実行・検証可能）
- ポートフォリオ構築（候補選定・重み計算・リスク調整・ポジションサイズ決定）
- リサーチユーティリティ（ファクター計算・特徴量探索）
- ニュースを LLM（OpenAI）でスコアリングする AI モジュール
- Streamlit ベースの監視ダッシュボード、検証レポート生成ツール

主な機能一覧
--------------
- 実行/リコンシリエーション
  - ExecutionEngine を起動して注文送信・状態同期・再起動復旧を実施
  - Reconciler による OrderSent の突合とポジション差分検出
- 監視
  - SystemMonitor: CPU / メモリ / ディスク / プロセス生存チェック / データ鮮度
  - TradeMonitor: 滞留注文、約定異常価格の検出
  - RiskMonitor: ドローダウン・ポジション上限の監視、ダッシュボード更新、risk_logs 登録
  - KillSwitch: しきい値超過時に data/kill.flag を書き込み ExecutionEngine を停止
  - AlertManager: LINE push による通知（クールダウン管理）
  - Monitoring DB（SQLite）を使った永続化（monitoring_db.init_monitoring_db）
- Paper Trading / 検証
  - Paper Trading は本番 DB と分離（デフォルト: data/paper_trading.db）
  - paper_verification_report: Paper Trading の検証レポート生成（稼働率・成功率・レイテンシ等）
- ポートフォリオ構築
  - 候補選定（スコア降順・上位 N）
  - 等重配分・スコア重み配分
  - セクター上限適用、レジーム乗数（bull/neutral/bear）
  - ポジションサイズ計算（ロット丸め、aggregate cap）
- リサーチ
  - ファクター計算（momentum / volatility / value）
  - 将来リターン、IC（Information Coefficient）、統計サマリ
- AI
  - news_nlp.score_news: raw_news を集約して OpenAI で銘柄別センチメントを計算し ai_scores に書き込み
  - regime_detector.score_regime: ma200 とマクロニュースの LLM スコアを合成して市場レジーム判定
- ユーティリティ
  - Settings（環境変数管理、.env 自動読み込み）
  - process_priority：プラットフォーム差分を吸収してプロセス優先度 / CPU affinity を設定
  - Streamlit ダッシュボード（読み取り専用で監視情報を表示）

セットアップ手順
----------------
1. 必要条件
   - Python 3.9+
   - SQLite（組み込み）
   - ネットワークアクセス（OpenAI / LINE 等を使う場合）

2. リポジトリをクローン
   - git clone <this-repo>
   - ソースは src/kabusys 以下にあります。実行時は PYTHONPATH=src を指定するかパッケージとしてインストールしてください。

3. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

4. 依存ライブラリをインストール
   - 主要依存: duckdb, psutil, openai, requests, streamlit
   - 例:
     - pip install duckdb psutil openai requests streamlit

   （プロジェクトに requirements.txt がある場合は pip install -r requirements.txt を使用）

5. data ディレクトリ作成・権限確認
   - mkdir -p data
   - 実行ユーザーが書き込み可能であることを確認してください。

6. 環境変数（.env）
   - .env または .env.local に必要な設定を記述できます（Settings モジュールが自動読み込みします）。
   - 主要な環境変数（例）:
     - KABUSYS_ENV=development|paper_trading|live
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - OPENAI_API_KEY=...
     - LINE_CHANNEL_ACCESS_TOKEN=...
     - LINE_USER_ID=...
     - SQLITE_PATH=data/monitoring.db
     - DUCKDB_PATH=data/kabusys.duckdb
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - PAPER_FILL_MODE=instant|partial|never|reject
     - MONITOR_POLL_INTERVAL=60
   - 注意: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動 .env 読み込みを無効化できます。

使い方
-------
※ 実行はプロジェクトルートから PYTHONPATH=src を通すか、パッケージ化して行ってください。

基本コマンド例（開発時）
- 監視ループを起動（デフォルト polling=60s。MONITOR_POLL_INTERVAL で変更可）
  - PYTHONPATH=src python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL=30 PYTHONPATH=src python -m kabusys.run_monitoring

- 実行エンジンを起動（KABUSYS_ENV により paper_trading と実DBの挙動を切替）
  - KABUSYS_ENV=development PYTHONPATH=src python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading PYTHONPATH=src python -m kabusys.run_execution
    - paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH に記録します。

- Paper Trading 検証レポート生成
  - PYTHONPATH=src python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: data/paper_trading.db（--db で上書き可）

- Streamlit ダッシュボード起動（監視 DB を読み取り専用で表示）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- AI モジュール呼び出し（ライブラリ利用例）
  - from kabusys.ai.news_nlp import score_news
  - from kabusys.ai.regime_detector import score_regime
  - これらは DuckDB 接続（duckdb.connect）と target_date、OPENAI_API_KEY を必要とします。

- 強制停止 / 停止フラグ
  - 実行中プロセスを優雅に停止するにはプロジェクト data ディレクトリに stop_requested.flag を作成してください（run_monitoring/run_execution はこのファイルを監視して終了します）。
  - KillSwitch は data/kill.flag を書き込み ExecutionEngine の停止シグナルを発行します。

設定と注意点
--------------
- Settings クラス（src/kabusys/config.py）が環境変数から各種設定を提供します。重要な値は JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, OPENAI_API_KEY 等です。
- KABUSYS_ENV は以下のいずれか: development / paper_trading / live
  - paper_trading: 実取引 API を呼ばずに MockBroker を使い paper_trading DB に記録します（本番 DB と完全分離）。
- PAPER_FILL_MODE: paper_trading 時の約定挙動（instant / partial / never / reject）
- MONITOR_POLL_INTERVAL は監視ループのポーリング間隔（秒）。0 以下・不正値はデフォルトにフォールバックします。
- データベース:
  - SQLite を監視ログや orders 等に利用（デフォルト: data/monitoring.db / data/paper_trading.db）
  - DuckDB を時系列・リサーチ用の大規模集計に利用（デフォルト: data/kabusys.duckdb）
  - init_monitoring_db() は必要テーブルを冪等に作成します（マイグレーション処理も一部含む）

ディレクトリ構成（主要ファイル）
------------------------------
リポジトリの主要モジュールを抜粋しています（src/kabusys 以下）。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py — Paper Trading 検証レポート生成
  - ai/
    - __init__.py
    - news_nlp.py            — ニュースセンチメント（OpenAI）
    - regime_detector.py     — 市場レジーム判定（ma200 + LLM）
  - monitoring/
    - __init__.py
    - monitoring_db.py       — SQLite 用永続層（system_status / trade_logs / positions / risk_logs / dashboard）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - alert_manager.py
    - kill_switch.py
    - streamlit_dashboard.py
  - execution/
    - order_manager.py
    - reconciler.py
    - (その他 execution コンポーネント)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - utils/
    - process_priority.py
    - __init__.py
  - monitoring/ (上記)
  - data/ (実行時に作成される、設定でパス変更可)
    - monitoring.db (SQLite)
    - paper_trading.db (SQLite, paper_trading 用)
    - kabusys.duckdb (DuckDB)

補足・運用メモ
--------------
- run_monitoring / run_execution は起動時に set_process_priority("high") を呼びます。権限不足や未対応 OS の場合は警告が出ますが処理は続行します。
- KillSwitch は RiskMonitor の判定に基づいて data/kill.flag を作成します。ExecutionEngine は起動時にこのフラグを検査し、フラグがあれば起動をスキップします。
- AI モジュールは OpenAI API を利用します。API キー（OPENAI_API_KEY）が必須です。呼び出しはリトライ・バックオフ・レスポンス検証を組み込んでいますが、API コスト・レート制限には注意してください。
- Paper Trading を実行するときは PAPER_TRADING_SQLITE_PATH を確認し、検証用の DB を別途準備してください。
- Streamlit ダッシュボードは監視 DB を読み取り専用で開きます（監視プロセスが DB を使っていても参照可能なように URI の ?mode=ro オプションを使います）。

ライセンスや貢献
----------------
本 README にライセンス情報は含めていません。実際の配布時は LICENSE を追加してください。バグ報告・機能提案は Issue を作成してください。

お問い合わせ・サポート
--------------------
開発者向けのドキュメントはコード内の docstring に詳細があります。各モジュールの仕様は該当ファイル（src/kabusys 以下）を参照してください。