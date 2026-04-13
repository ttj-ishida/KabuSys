README
======

概要
----
KabuSys は日本株向けの自動売買システム（ライブラリ兼ランタイム）です。  
本リポジトリは戦略用ファクター計算、ポートフォリオ構築、発注 / リコンシリエーション、監視・アラート、Paper Trading 検証や LLM を用いたニュースセンチメント評価などのコンポーネントを含みます。  
コードはモジュール化されており、実運用（live）、Paper Trading、開発（development）を切り替えて利用できます。

主な機能
--------
- 発注実行エンジン（ExecutionEngine）:
  - Broker クライアント生成（本番/Mock を切り替え可能）
  - OrderManager / OrderRepository を使った注文管理
  - リコンシリエーション（起動時の状態同期）
  - リスク管理（ポジション上限・ドローダウン等）
- 監視（Monitoring）:
  - SystemMonitor: CPU/Mem/Disk、プロセス存在確認、データ鮮度チェック
  - TradeMonitor: 注文滞留・約定価格異常チェック
  - RiskMonitor: ドローダウン・ポジション上限監視、ダッシュボード更新
  - KillSwitch: フラグファイルで ExecutionEngine を停止させる仕組み
  - AlertManager: LINE Push によるアラート送信（クールダウンあり）
  - Streamlit ベースの監視ダッシュボード（読み取り専用）
- 研究/リサーチ:
  - ファクター計算（モメンタム、ボラティリティ、バリュー等）
  - 将来リターン計算、IC（スピアマン）などの解析ユーティリティ
- ポートフォリオ構築:
  - 候補選定、等金額/スコア重み、リスク調整（セクター制限）、ポジションサイズ算出（単元丸め・集約キャップ）
- AI（LLM）関連:
  - news_nlp: ニュースを OpenAI（gpt-4o-mini 等）に投げて銘柄毎のセンチメントを ai_scores テーブルに格納
  - regime_detector: ETF とマクロニュースのセンチメントを混合して市場レジームを判定・永続化
- ツール:
  - Paper Trading の検証レポート生成スクリプト（paper_verification_report）
  - Streamlit ダッシュボード

依存関係（代表）
----------------
主要なランタイム依存（プロジェクト全体で使用）:
- Python 3.10+（typing の | 演算子等を使用）
- duckdb
- psutil
- requests
- openai（AI 機能を使う場合）
- streamlit（ダッシュボード起動時）
- sqlite3（標準ライブラリ）

セットアップ手順
---------------
1. リポジトリをクローンしてワークディレクトリへ移動:
   - git clone ... && cd <repo>

2. 仮想環境作成・有効化（推奨）:
   - python -m venv .venv
   - source .venv/bin/activate  # Unix/macOS
   - .venv\Scripts\activate     # Windows

3. 依存パッケージをインストール:
   - pip install -r requirements.txt
     ※ requirements.txt が無い場合は最低限以下を入れてください:
       pip install duckdb psutil requests openai streamlit

4. 環境変数（.env）設定:
   - プロジェクトルートの .env または .env.local に設定可能。自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化）。
   - 主な環境変数（例）:
     - KABUSYS_ENV=development | paper_trading | live
     - SQLITE_PATH=data/monitoring.db
     - DUCKDB_PATH=data/kabusys.duckdb
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - PID_FILE_PATH=data/execution.pid
     - KILL_FLAG_PATH=data/kill.flag
     - OPENAI_API_KEY=sk-...
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - LINE_CHANNEL_ACCESS_TOKEN=...
     - LINE_USER_ID=...
     - PAPER_FILL_MODE=instant|partial|never|reject
     - MONITOR_POLL_INTERVAL=60  # run_monitoring のポーリング間隔（秒）

   - Settings クラスが各変数のデフォルトや妥当性チェックを提供しています（kabusys/config.py を参照）。

使い方（実行コマンド）
--------------------

- 実行エンジン（ExecutionEngine）を起動:
  - 環境変数でモードを切り替え:
    - export KABUSYS_ENV=paper_trading
    - export KABUSYS_ENV=live
  - 実行:
    - python -m kabusys.run_execution
  - 動作メモ:
    - paper_trading モードでは専用の SQLite（PAPER_TRADING_SQLITE_PATH、デフォルト data/paper_trading.db）と MockBrokerClient を使用し、本番 DB とは完全に分離されます。
    - 起動時にプロセス優先度を "high" に設定しようとします（権限がない場合は警告のみ）。

- 監視ループを起動:
  - デフォルトポーリング間隔は 60 秒。環境変数 MONITOR_POLL_INTERVAL で上書き可能（秒）。0 以下や無効な値はデフォルトにフォールバックします。
  - 実行:
    - python -m kabusys.run_monitoring
  - 動作メモ:
    - monitoring は KABUSYS_ENV にかかわらず settings.sqlite_path（デフォルト data/monitoring.db）を使用します（監視ログは常に本番 DB に書く設計）。
    - PID ファイルや kill.flag を用いたプロセス監視・停止の仕組みがあります（Settings.pid_file_path / kill_flag_path）。

- Paper Trading 検証レポート生成:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション --db で SQLite パスを指定できます（デフォルト data/paper_trading.db または環境変数 PAPER_TRADING_SQLITE_PATH）。

- Streamlit 監視ダッシュボード:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 読み取り専用で monitoring DB を表示します。DB が存在しない場合は MonitoringEngine を起動してください。

- AI（ニュースセンチメント / レジーム判定）:
  - OpenAI API キーが必要（OPENAI_API_KEY 環境変数、または関数引数で指定）。
  - モジュール API:
    - kabusys.ai.score_news(conn, target_date, api_key=None)
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは DuckDB 接続（prices_daily / raw_news 等を持つ）を受け取ります。呼び出し元でスケジューリングしてください。
  - API 呼び出しはリトライやフォールバック（失敗時は 0.0）等の堅牢化が入っています。

設定・ファイルパス（デフォルト）
------------------------------
- データベース:
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- PID / Kill flag:
  - PID_FILE_PATH: data/execution.pid
  - KILL_FLAG_PATH: data/kill.flag
- Paper fill mode:
  - PAPER_FILL_MODE: instant（instant|partial|never|reject）

ディレクトリ構成（src/kabusys の主要ファイル）
-----------------------------------------
- __init__.py
  - パッケージメタ情報（__version__ 等）
- config.py
  - 環境変数読み込み・Settings 提供（.env 自動読み込み機能あり）
- run_execution.py
  - ExecutionEngine 起動スクリプト（KABUSYS_ENV による Paper/Live 切替）
- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト
- execution/
  - order_manager.py, reconciler.py, order_repository.py 等
  - ブローカー抽象、OrderState 管理、リコンシリエーションロジック
- monitoring/
  - monitoring_db.py: SQLite 永続化（system_status, trade_logs, positions, risk_logs, dashboard 等）
  - system_monitor.py: システム状態・データ鮮度チェック
  - trade_monitor.py: 注文滞留・約定異常検出
  - risk_monitor.py: ドローダウン・ポジション数監視
  - kill_switch.py: kill.flag の管理
  - alert_manager.py: LINE への通知
  - monitoring_engine.py: 各 Monitor を束ねるランナー
  - streamlit_dashboard.py: Streamlit での可視化
- portfolio/
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py
  - 候補選定・重み付け・ポジションサイズ・セクターキャップ等
- research/
  - factor_research.py, feature_exploration.py
  - ファクター算出・将来リターン・IC 計算など
- ai/
  - news_nlp.py: ニュースを LLM に投げて銘柄ごとスコア化し ai_scores に保存
  - regime_detector.py: マクロ + ETF MA を使って市場レジーム判定
- tools/
  - paper_verification_report.py: Paper Trading DB に対する検証レポート生成
- utils/
  - process_priority.py: プロセス優先度 / CPU affinity 設定ユーティリティ

開発メモ / 注意点
----------------
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml を探索）から行われます。CWD に依存せず動作するよう設計されています。自動ロードを止めたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- run_monitoring は監視ログ用 SQLite（settings.sqlite_path）を用います。環境にかかわらず監視ログは単一の DB に集約する設計です。
- process priority / cpu affinity の設定はプラットフォーム依存であり権限不足や未対応 OS の場合は警告を出してスキップします。
- AI 機能を使う場合は OpenAI API 利用料やレート制限に注意してください。score_news / score_regime はリトライやバックオフ、部分失敗の保護（書き込み単位の絞り込み）など堅牢化があります。
- Paper Trading 環境は本番 DB と分離されるよう設計されています。誤って本番 DB に書き込まないよう env の設定を確認してください。

サンプル .env（最小）
---------------------
例:
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
PID_FILE_PATH=data/execution.pid
KILL_FLAG_PATH=data/kill.flag
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=secret
JQUANTS_REFRESH_TOKEN=...
LINE_CHANNEL_ACCESS_TOKEN=
LINE_USER_ID=

サポート / 拡張
----------------
- 新しいブローカーを追加する場合は execution/broker_factory.py と BrokerAPIProtocol を実装してください。
- ファクターやポートフォリオロジックは research/ と portfolio/ に分離されているため、ユニットテストが容易です（純粋関数が多い）。
- DuckDB のスキーマ（prices_daily, raw_financials, raw_news 等）に合わせたデータロードパイプラインを別途用意してください（kabusys.data.pipeline を参照）。

以上です。運用上の疑問や README に追記したい内容があれば教えてください。