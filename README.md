KabuSys — README
=================

概要
----
KabuSys は日本株向けの自動売買 / リサーチ / 監視プラットフォームのコードベースです。本リポジトリは以下の主要機能を含みます:

- 注文発行・状態管理（Execution）
- 発注ログ・監視データの永続化（SQLite）
- 時系列・ファクター計算（DuckDB を利用した Research）
- ポートフォリオ構築（候補選定、重み付け、株数計算）
- 監視エンジン（システム状態、滞留注文、リスク監視、アラート）
- AI モジュール（ニュースのセンチメント評価・市場レジーム判定、OpenAI を用いる）
- Paper Trading 用の分離された DB / モックブローカー
- Streamlit ダッシュボード、検証レポート生成ツール

特徴（機能一覧）
----------------
- Settings: .env / 環境変数から設定を読み込み。自動ロードはプロジェクトルート（.git / pyproject.toml）を基準に行う。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可。
- Execution:
  - run_execution.py による ExecutionEngine 起動（KABUSYS_ENV=paper_trading の場合は MockBroker と paper_trading DB を使用）
  - OrderManager / Reconciler による起動時の自動復旧・照合
- Monitoring:
  - run_monitoring.py による SystemMonitor ポーリング（MONITOR_POLL_INTERVAL で間隔上書き可、デフォルト 60 秒）
  - System / Trade / Risk モニタ、KillSwitch（データに基づく実行停止フラグの書込み）
  - AlertManager による LINE Push 通知（設定されている場合）
  - Streamlit ダッシュボード（監視データの可視化）
  - monitoring DB 初期化 & マイグレーション処理
- Research:
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン・IC 計算、ファクター統計要約
  - DuckDB を用いた SQL + Python 実装（prices_daily / raw_financials 参照）
- AI:
  - news_nlp: raw_news をまとめて OpenAI へ送信し、銘柄ごとのセンチメント ai_scores を書き込む
  - regime_detector: ETF（1321）MA200 乖離とマクロ記事の LLM センチメントを合成して日次レジーム判定を行い DB 保存
- Tools:
  - paper_verification_report: Paper Trading DB（data/paper_trading.db）を解析して検証レポートを出力

セットアップ手順
----------------
前提:
- Python 3.10+（型ヒントや union 演算子の使用のため推奨）
- システムに DuckDB, SQLite, psutil 等が導入可能であること

1. リポジトリをチェックアウト:
   git clone <repository-url>

2. 仮想環境作成・有効化:
   python -m venv .venv
   source .venv/bin/activate  # POSIX
   .venv\Scripts\activate     # Windows

3. 必要パッケージをインストール:
   - requirements.txt がある場合:
     pip install -r requirements.txt
   - 明示的に必要なパッケージ（最低限）:
     pip install duckdb psutil requests openai streamlit

4. 環境変数 / .env の準備:
   - プロジェクトルートに .env または .env.local を置くと自動で読み込まれます（OS 環境変数が優先）。
   - 自動ロードを無効化するには: export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   - 主要な環境変数（一部）:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - JQUANTS_REFRESH_TOKEN: （必須）
     - KABU_API_PASSWORD: （必須）
     - OPENAI_API_KEY: OpenAI を利用する機能で必要
     - DUCKDB_PATH: デフォルト data/kabusys.duckdb
     - SQLITE_PATH: デフォルト data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: デフォルト data/paper_trading.db
     - PID_FILE_PATH: デフォルト data/execution.pid
     - KILL_FLAG_PATH: デフォルト data/kill.flag
     - PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）
     - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）

5. データディレクトリ作成:
   mkdir -p data

使い方（起動・操作方法）
-----------------------

監視ループの起動
- MONITOR_POLL_INTERVAL を使ってポーリング間隔を変更できます（秒）。
- 例:
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- run_monitoring の挙動:
  - プロセス優先度を high に設定し、monitoring 用 SQLite（settings.sqlite_path）と DuckDB に接続します。
  - SystemMonitor.check_once を定期実行し、system_status 等に記録します。
  - 監視は常に本番用の sqlite_path を参照（KABUSYS_ENV に依存しない点に注意）。

ExecutionEngine の起動
- Paper Trading モード:
  - KABUSYS_ENV=paper_trading を設定すると MockBrokerClient を使用し、Paper Trading 専用 DB（PAPER_TRADING_SQLITE_PATH）に書き込みます（本番 DB と完全分離）。
- 例:
  python -m kabusys.run_execution

Paper Trading 検証レポート
- ツール:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

Streamlit ダッシュボード（監視）
- 起動方法（例: ローカルの monitoring.db を読み込む）:
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- ダッシュボードでは Positions / Orders / System / Overview を確認できます（読み取り専用で開きます）。

AI モジュール実行（ニューススコア / レジーム判定）
- OpenAI API キーを環境変数 OPENAI_API_KEY に設定するか、関数呼び出しで渡してください。
- プログラムから利用する例（Python）:
  from kabusys.ai.news_nlp import score_news
  # conn: duckdb connection, target_date: datetime.date
  score_news(conn, target_date, api_key="sk-...")

  from kabusys.ai.regime_detector import score_regime
  score_regime(conn, target_date, api_key="sk-...")

注意点・運用上のポイント
- .env の自動読み込み:
  - プロジェクトルート（.git / pyproject.toml）を基準に .env / .env.local を順に読み込みます。
  - OS 環境変数は保護され、.env.local で上書きされません（ただし override=True で .env.local は上書きするが protected による制御あり）。
- PID / Kill flag:
  - ExecutionEngine は PID ファイル（デフォルト data/execution.pid）を書きます。Monitoring は PID の存在／生存確認を行い、stale PID を検出した場合は削除してイベントログに記録します。
  - KillSwitch は data/kill.flag を書き込むことで ExecutionEngine に停止シグナルを送ります（ファイル存在チェックを行う設計）。
- Paper Trading 分離:
  - paper_trading 環境は本番の monitoring DB と分離しているため、本番データを汚さずに検証できます。
- OpenAI 利用:
  - API 呼び出しはレート制限・ネットワーク障害・サーバーエラーを考慮してリトライ処理を実装していますが、API キー未設定時は例外を投げます。運用時はキー管理に注意してください。
- ロギング:
  - 各 run スクリプトは logging.basicConfig(level=logging.INFO) を使用して基本ログ出力を行います。環境変数 LOG_LEVEL で変更できます（DEBUG/INFO/WARNING/ERROR/CRITICAL）。

ディレクトリ構成（主要ファイル）
------------------------------
以下は src/kabusys 以下の主要なモジュールと簡単な説明です。

- src/kabusys/
  - __init__.py — パッケージ定義（__version__ 等）
  - config.py — 環境変数・設定読み込み（Settings クラス）
  - run_monitoring.py — SystemMonitor のポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト（paper_trading モード対応）
- src/kabusys/monitoring/
  - monitoring_db.py — SQLite テーブル作成・永続化レイヤ
  - system_monitor.py — システム状態・データ鮮度チェック
  - trade_monitor.py — 注文滞留・約定価格異常チェック
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - monitoring_engine.py — 各 Monitor を束ねるエンジン
  - kill_switch.py — フラグファイルで Execution を停止させる仕組み
  - alert_manager.py — LINE Push 通知ラッパ
  - streamlit_dashboard.py — 監視ダッシュボード（Streamlit）
- src/kabusys/execution/
  - order_manager.py — 注文ライフサイクル管理
  - reconciler.py — 起動時の注文/ポジション再照合
  - （他に broker_factory, execution_engine 等が存在）
- src/kabusys/portfolio/
  - portfolio_builder.py — 候補選定・スコア順ソート
  - position_sizing.py — 株数計算・投下制限・単元丸め
  - risk_adjustment.py — セクターキャップ・レジーム乗数
- src/kabusys/research/
  - factor_research.py — momentum/value/volatility 等のファクター計算（DuckDB）
  - feature_exploration.py — 将来リターン計算・IC・統計サマリ
- src/kabusys/ai/
  - news_nlp.py — ニュースをまとめて OpenAI に投げ、ai_scores を書き込む
  - regime_detector.py — マクロ記事 + ETF MA 乖離で市場レジーム判定
- src/kabusys/tools/
  - paper_verification_report.py — Paper Trading の検証レポート生成ツール
- src/kabusys/utils/
  - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

開発者向け補足
----------------
- 型ヒントとドキュメントコメントが整備されています。既存関数はテストしやすい純粋関数設計（副作用を持たない箇所）になっている箇所が多く、ユニットテストの追加が容易です。
- DuckDB を用いたクエリは SQL をそのまま記述しており、分析処理の変更は比較的容易です。
- DB マイグレーションは簡易的に PRAGMA や ALTER TABLE で行っています。運用時はバックアップを推奨します。

ライセンス・貢献
----------------
（ここにライセンス情報、貢献方法、連絡先などを追記してください）

以上。運用や導入で不明点があれば、どの機能について詳しく知りたいか教えてください。