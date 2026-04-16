KabuSys — 日本株向け自動売買基盤（README）
概要
本リポジトリは「KabuSys」と呼ばれる日本株自動売買／リサーチ／監視のためのライブラリ群および起動スクリプト群です。  
主な目的は以下です。
- 自動売買の実行エンジン（ExecutionEngine）とその補助コンポーネント（OrderManager, RiskManager, Reconciler 等）
- 監視（MonitoringEngine / SystemMonitor / TradeMonitor / RiskMonitor）とアラート（LINE Push）
- ポートフォリオ構築・ポジションサイズ計算（portfolio パッケージ）
- リサーチ／ファクター計算（research パッケージ）
- AI を用いたニュースセンチメント評価・レジーム判定（AI モジュール）
- Paper Trading 検証ツール（tools）

特徴（主な機能）
- 実行エンジンとブローカー抽象化（本番と paper_trading の分離）
- 監視ループ：CPU/メモリ/ディスク、プロセス生存、データ鮮度、滞留注文、約定異常などを定期記録
- Kill Switch：ドローダウンやポジション数超過等で停止フラグを書き込み、実行エンジンを安全停止
- LINE によるアラート送信（クールダウン管理つき）
- DuckDB / SQLite を用いた価格・ファクター計算および監視ログ保存
- OpenAI（gpt-4o-mini）を用いたニュース NLP スコアリングと市場レジーム判定（オプション）
- Streamlit ベースの監視ダッシュボード（読み取り専用）

セットアップ手順（開発環境）
1. リポジトリをクローンして src を PYTHONPATH に含める（またはパッケージとしてインストール）。
   - 例: git clone ... && cd <repo>
2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate (Unix/macOS) / .venv\Scripts\activate (Windows)
3. 依存パッケージをインストール（requirements.txt が無ければ以下を参考に手動インストール）
   - 必要パッケージ（主なもの）:
     - duckdb, psutil, requests, openai, streamlit
   - 例: pip install duckdb psutil requests openai streamlit
4. 環境変数の設定
   - プロジェクトルートに .env / .env.local を置くと自動でロードされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 代表的な環境変数（.env 例）:
     - KABUSYS_ENV=development | paper_trading | live
     - OPENAI_API_KEY=sk-...
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - LINE_CHANNEL_ACCESS_TOKEN=...
     - LINE_USER_ID=...
     - PAPER_FILL_MODE=instant | partial | never | reject
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - SQLITE_PATH=data/monitoring.db
     - DUCKDB_PATH=data/kabusys.duckdb
     - LOG_LEVEL=INFO
   - 注意: Settings クラスは必須の環境変数が未設定だと例外を投げます（JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD 等）。

初期ディレクトリとデータディレクトリ
- data/ 配下に SQLite / DuckDB / PID / フラグファイル等を置く設計です。起動前に data/ を作成しておくと良いです。
- 実行・監視の停止用フラグ:
  - data/stop_requested.flag — run_monitoring / run_execution が監視している停止フラグ（存在するとループを抜ける）
  - data/kill.flag — KillSwitch が書き込むフラグ（ExecutionEngine に停止指示として使用される想定）

使い方（起動・ツール）
- 実行エンジン（ExecutionEngine）起動
  - Paper Trading（ブローカーはモック、DBは data/paper_trading.db を使用）:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - 本番（live）または開発:
    - KABUSYS_ENV=live python -m kabusys.run_execution
    - KABUSYS_ENV=development python -m kabusys.run_execution
  - 挙動:
    - 起動時にプロセス優先度を "high" に設定（set_process_priority）。
    - Settings を読み込み、環境に応じて SQLite パスを切り替え。
    - ExecutionEngine をスレッドで実行し、data/stop_requested.flag の存在を監視して停止。

- 監視ループ起動（SystemMonitor 単体の長時間ポーリング）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を指定可能（デフォルト 60 秒）。
    - 例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視は常に本番用の sqlite_path を使用する（Settings.env に依らず production DB を参照する設計上の注意）。

- Streamlit 監視ダッシュボード（読み取り専用）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - DB を読み取り専用モードで開くため、MonitoringEngine が書き込んでいる DB を安全に参照できます。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db /path/to/paper_trading.db
    - 既定は data/paper_trading.db, 環境変数 PAPER_TRADING_SQLITE_PATH でも指定可。

- AI 関連（ニュース NLP / レジーム判定）
  - OpenAI API キー（OPENAI_API_KEY）を環境変数で用意するか、関数呼び出し時に api_key 引数を渡します。
  - news_nlp.score_news(conn, target_date, api_key=None) — raw_news / news_symbols から銘柄別センチメントを ai_scores テーブルへ書き込み。
  - regime_detector.score_regime(conn, target_date, api_key=None) — ETF 1321 MA とマクロニュースの LLM 結果を合成して market_regime テーブルへ書き込み。
  - 注意: API 呼び出しはリトライ・バックオフなどのフェイルセーフ実装あり。失敗時は安全側の値で継続します。

運用上のポイント・設計ノート
- 環境分離
  - KABUSYS_ENV=paper_trading の場合、paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用して本番 DB と分離するようになっています。
- プロセス優先度
  - run_execution / run_monitoring 起動時に set_process_priority("high") を呼び出します（プラットフォーム依存で権限が必要な場合あり）。
- 監視 DB マイグレーション
  - init_monitoring_db(conn) は冪等でテーブルを作成し、既存 DB に対して必要なカラム追加（マイグレーション）を行います（例: latency_ms, peak_value）。
- Kill Switch
  - RiskMonitor や MonitoringEngine の結果に応じて KillSwitch が data/kill.flag を書き込みます。ExecutionEngine 側は kill.flag を参照して安全に停止する設計になっています（実装上の取り扱いは ExecutionEngine のコードにも依存）。

ディレクトリ構成（主なファイルと説明）
- src/kabusys/
  - __init__.py: パッケージ定義、バージョン
  - config.py: 環境変数・Settings の読み込みロジック（.env 自動読み込み・検証）
  - run_execution.py: ExecutionEngine を起動するスクリプト
  - run_monitoring.py: SystemMonitor のポーリングスクリプト
  - utils/
    - process_priority.py: プロセス優先度・CPU affinity のユーティリティ（psutil ベース）
  - execution/
    - order_manager.py: 注文発行・状態遷移周りの外向け API
    - reconciler.py: 起動時の注文／ポジション突合せ（自動復旧）
    - （その他 broker / engine / order_repository 等は本リポジトリに存在）
  - monitoring/
    - monitoring_db.py: SQLite ベースの監視ログ永続化層（init と CRUD）
    - system_monitor.py: CPU/メモリ/ディスク/データ鮮度/プロセスの監視
    - trade_monitor.py: 注文滞留・約定異常のチェック
    - risk_monitor.py: ドローダウン・ポジション上限監視
    - kill_switch.py: 停止フラグの作成・管理
    - alert_manager.py: LINE Push による通知
    - monitoring_engine.py: 上記 Monitor を束ねるエンジン
    - streamlit_dashboard.py: Streamlit ベースのダッシュボード
  - portfolio/
    - portfolio_builder.py: 候補選定・等重／スコア重み計算
    - position_sizing.py: 単元丸め・リスクベース等の株数算出ロジック
    - risk_adjustment.py: セクター制限・レジーム乗数
  - research/
    - factor_research.py: モメンタム / ボラティリティ / バリュー計算（DuckDB ベース）
    - feature_exploration.py: 将来リターン計算・IC計算・統計サマリー
  - ai/
    - news_nlp.py: raw_news を OpenAI でセンチメント化して ai_scores に書き込む
    - regime_detector.py: マクロニュース + ETF MA による市場レジーム判定
  - tools/
    - paper_verification_report.py: Paper Trading のログから検証レポートを生成
  - data/ (運用時に使用するディレクトリ、例)
    - monitoring.db (SQLite)
    - kabusys.duckdb (DuckDB)
    - execution.pid
    - stop_requested.flag
    - kill.flag
    - paper_trading.db

運用例（簡単なワークフロー）
1. データ投入（prices_daily, raw_news 等を DuckDB にロード）
2. 実行エンジン起動（本番または paper）
   - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
3. 監視ループ起動（別プロセス）
   - python -m kabusys.run_monitoring
4. 監視ダッシュボード表示
   - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
5. Paper 検証レポート出力
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

補足（よくある質問）
- .env の自動読み込みを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。  
- OpenAI を使う機能は API キーが必須です。キーは環境変数 OPENAI_API_KEY にセットするか、関数呼び出し時に api_key を渡してください。  
- run_monitoring / run_execution は起動時にプロセス優先度を上げようとします。権限のない環境では警告ログが出ますが起動自体は継続します。  
- データベースや PID / フラグファイルのパスは Settings 経由でカスタマイズできます（環境変数で上書き可能）。

問い合わせ・開発メモ
- コード内に多数の docstring と実装ノートがあります。設計（PortfolioConstruction.md, StrategyModel.md 等）準拠の注釈が含まれているので実装変更時はコメントも確認してください。  
- テストスイートは同梱されていないため、ユニットテストを追加する場合は各モジュールの純粋関数（portfolio や research 部分）を中心に作成するのが簡単です。

以上がリポジトリ全体の概要と基本的な使い方です。必要であれば、環境変数の完全な一覧やサンプル .env を作成しますのでお知らせください。