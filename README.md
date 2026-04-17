KabuSys — 日本株自動売買システム (README)
=========================================

概要
----
KabuSys は日本株の自動売買 / 研究 / 監視を目的とした Python ベースのソフトウェアです。
主要機能は戦略のポートフォリオ構築、ポジションサイズ計算、注文発行・再同期（Reconciler）、
監視（System / Trade / Risk）、AI を使ったニュースセンチメント評価、Paper Trading の検証レポート生成などです。
設計方針として、DB（SQLite / DuckDB）を中心にデータ永続化を行い、外部 API 呼び出しは明示的に管理されています。

主な特徴
--------
- ポートフォリオ構築（候補選定、等重・スコア重み付け）
- ポジションサイズ計算（リスクベース、上限・まとめ単元考慮）
- 市場レジーム判定（ETF MA + LLM マクロセンチメント）
- ニュース NLU（OpenAI）による銘柄別センチメントスコア生成
- ExecutionEngine（ブローカー抽象化）と Reconciler による自動復旧
- 監視サブシステム（System / Trade / Risk）、アラート送信（LINE）
- Streamlit ベースの監視ダッシュボード
- Paper Trading 用データベースの分離と検証レポート生成ツール

セットアップ手順
----------------

前提
- Python 3.9+（ソースは typing | annotations を前提）
- OS: Linux / macOS / Windows（プロセス優先度・CPU affinity は OS によって動作差あり）

依存パッケージ（例）
- duckdb
- psutil
- requests
- openai
- streamlit
- （その他: 標準ライブラリ以外のモジュールを requirements.txt にまとめてください）

インストール（例）
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージのインストール
   - pip install duckdb psutil requests openai streamlit

環境変数 / .env
- プロジェクトルートに .env（または .env.local）を配置すると自動で読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により無効化可）。
- 重要な環境変数（例）:
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用トークン（必須）
  - KABU_API_PASSWORD — kabuステーション API 用パスワード（必須）
  - OPENAI_API_KEY — OpenAI API キー（AI 機能使用時）
  - KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
  - PAPER_FILL_MODE — Paper Trading の約定モード: instant | partial | never | reject（デフォルト: instant）
  - PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite のパス（デフォルト: data/paper_trading.db）
  - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
  - DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
  - LOG_LEVEL — ログレベル（DEBUG/INFO/...）

簡易 .env 例
- .env.example の内容を参考にしてください（プロジェクトルートに配置）。


使い方（主要スクリプト）
-----------------------

1) 監視ループ起動（Monitoring）
- スクリプト: src/kabusys/run_monitoring.py
- 説明: SystemMonitor を定期ポーリングし、監視ログを SQLite に記録します。
- ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒、デフォルト 60）で上書き可能。
- 起動:
  - python -m kabusys.run_monitoring
- 停止: プロジェクトルート/data/stop_requested.flag を作成すると安全に停止します。

2) 実行エンジン起動（ExecutionEngine）
- スクリプト: src/kabusys/run_execution.py
- 説明: BrokerClient を生成し ExecutionEngine を起動。KABUSYS_ENV=paper_trading の場合は MockBroker を使い、paper_trading 用 DB に記録します（本番 DB と完全分離）。
- 起動:
  - python -m kabusys.run_execution
  - Paper Trading モード:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- 停止: プロジェクトルート/data/stop_requested.flag を作成すると実行エンジンが停止します。
- PID ファイル: data/execution.pid（既存 PID が stale の場合は監視側で検出して削除します）。

3) Paper Trading 検証レポート生成
- スクリプト: src/kabusys/tools/paper_verification_report.py
- 用途: paper_trading DB（デフォルト data/paper_trading.db）から検証指標（稼働率、注文成功率、レイテンシ等）を集計して標準出力へレポート。
- 実行例:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/db.sqlite

4) 監視ダッシュボード（Streamlit）
- ファイル: src/kabusys/monitoring/streamlit_dashboard.py
- 起動:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- 説明: ダッシュボードは SQLite を読み取り専用で開きます。MonitoringEngine が先に監視 DB を作成・更新している必要があります。

5) AI 機能
- ニュースセンチメント:
  - 関数: kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
  - OpenAI API キーは api_key 引数または OPENAI_API_KEY 環境変数で指定。
- 市場レジーム判定:
  - 関数: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

運用上のメモ / 動作仕様
---------------------
- DB:
  - 監視用 SQLite: data/monitoring.db（settings.sqlite_path）
  - DuckDB: data/kabusys.duckdb（prices_daily, raw_news, raw_financials 等の大規模データ向け）
  - Paper Trading 用 SQLite（paper_trading モード）: data/paper_trading.db（settings.paper_sqlite_path）
- kill.flag（data/kill.flag）:
  - KillSwitch（監視サブシステム）により書き込まれると ExecutionEngine に停止シグナルを送ります。
  - 実行前にフラグをクリアするには、Settings.kill_flag_clear_on_start の設定や手動削除を行ってください。
- stop_requested.flag（data/stop_requested.flag）:
  - run_monitoring.py / run_execution.py の外部停止トリガ。
- プロセス優先度:
  - run_* スクリプトは起動時に set_process_priority("high") を呼び出し、可能なら優先度を引き上げます。
- Paper Trading:
  - KABUSYS_ENV=paper_trading にすると BrokerFactory が MockBrokerClient を生成し、paper_trading 専用 DB に記録され本番 DB と分離されます。
  - PAPER_FILL_MODE で約定挙動を調整できます（instant, partial, never, reject）。

ディレクトリ構成（主要ファイル）
-----------------------------
（プロジェクトの src/kabusys 配下を抜粋）

- src/kabusys/
  - __init__.py                (パッケージ定義、バージョン)
  - config.py                  (環境設定・.env 自動読み込み・Settings クラス)
  - run_monitoring.py          (SystemMonitor ポーリング起動スクリプト)
  - run_execution.py           (ExecutionEngine 起動スクリプト)
  - tools/
    - __init__.py
    - paper_verification_report.py
  - ai/
    - __init__.py
    - news_nlp.py               (ニュース NLP スコアリング)
    - regime_detector.py       (市場レジーム判定)
  - monitoring/
    - __init__.py
    - monitoring_db.py         (SQLite スキーマ + MonitoringDB クラス)
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py         (LINE 通知)
    - monitoring_engine.py
    - streamlit_dashboard.py
  - execution/
    - order_manager.py
    - reconciler.py
    - (その他: broker_factory, execution_engine, order_repository, order_record 等)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - utils/
    - __init__.py
    - process_priority.py

開発・拡張のヒント
------------------
- DB スキーマの初期化は monitoring_db.init_monitoring_db(conn) で安全に（冪等）実行できます。
- AI 関連呼び出しは OpenAI クライアントの例外を適切にハンドリングする設計です。テスト時は _call_openai_api をモックしてください。
- DuckDB / prices_daily テーブルを用いたファクター計算は research パッケージに整理されています。データが不足する場合は None を返す設計です。
- streamlit ダッシュボードは DB を読み取り専用で開きます。複数人が同時に閲覧しても問題のない設計です。

よくある運用操作
-----------------
- 監視停止（安全停止）: touch data/stop_requested.flag
- エンジン停止（監視からの kill）: data/kill.flag が作成されると run_execution 側で検出して停止
- Paper レポート生成:
  - python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD

サポート / コントリビュート
--------------------------
- バグ報告や機能追加は Issue を作成してください。設計上の注意点や API キーの取り扱い（機密）は README や .env.example に明記して管理してください。

ライセンス
---------
- 本リポジトリのライセンス情報はプロジェクトルートの LICENSE を参照してください（ここでは明示されていません）。

以上。README に追記したい点（例: requirements.txt、CI / テスト手順、.env.example の具体例等）があれば教えてください。