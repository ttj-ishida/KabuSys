README
=====

概要
----
KabuSys は日本株向けの自動売買 / リサーチ基盤のコード群です。本リポジトリには以下の主要機能を含みます:

- 実行エンジン（ExecutionEngine）: 注文の作成・送信・管理、リスク管理、再起動時のリコンシリエーション
- 監視（Monitoring）: プロセス・システムリソース・注文状態・ドローダウン等のポーリング監視、アラート送信、停止フラグ（Kill Switch）
- ポートフォリオ構築ロジック: 候補選定、重み計算、ポジションサイズ決定、セクター制約等の純粋関数群
- リサーチ / ファクター計算: Momentum/Volatility/Value 等のファクター計算、将来リターン・IC 計算
- AI 補助: ニュース NLP によるセンチメントスコアリング、レジーム判定（OpenAI を利用）
- ユーティリティ: プロセス優先度設定、Streamlit ダッシュボード表示、Paper Trading 検証レポート生成

特徴一覧
--------
主なコンポーネントと機能:

- Execution
  - BrokerClientFactory に基づく本番 / Paper Trading 切替（KABUSYS_ENV）
  - OrderManager / OrderRepository による DB 永続化と状態管理
  - RiskManager による発注制御（最大ポジション比率・資金利用率等）
  - Reconciler による起動時リコンシリエーション（未確定注文の照合・ポジション差分検知）

- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク/プロセス生存/データ鮮度監視
  - TradeMonitor: 滞留注文／約定異常価格検出
  - RiskMonitor: ドローダウン、ポジション上限監視とログ記録
  - KillSwitch: データベース上の閾値超過時に data/kill.flag を書き込み ExecutionEngine 停止
  - AlertManager: LINE Push による通知（クールダウン制御）
  - Streamlit ダッシュボードで監視情報の可視化

- Portfolio
  - 候補選定（スコア順ソート）、等配分／スコア加重配分、リスクベースの発注数量決定
  - セクター上限適用、レジーム乗数（bull/neutral/bear による投下資金調整）

- Research / AI
  - DuckDB を使ったファクター計算（prices_daily / raw_financials を参照）
  - ニュースを OpenAI に送って銘柄別センチメントを ai_scores に保存
  - マクロニュース x ETF の MA 乖離を組み合わせたレジーム判定

セットアップ手順
---------------
前提: Python 3.9+（実行環境に合わせて適宜）

1. リポジトリのクローン / 作業ディレクトリへ移動
   - 例: git clone <repo> && cd <repo>

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージのインストール
   - requirements.txt がない場合は主要依存をインストール:
     pip install duckdb psutil requests streamlit openai

   （プロジェクトに requirements.txt があればそれを使ってください:
    pip install -r requirements.txt）

4. 環境変数の設定
   - プロジェクトルートに .env / .env.local を置くと自動ロードされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須（実行内容に応じて）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - OpenAI 機能を使う場合:
     - OPENAI_API_KEY
   - 主な設定変数（後述の「環境変数一覧」を参照）

5. data ディレクトリ作成（必要なら）
   - mkdir -p data

6. DB 初期化
   - run_monitoring / run_execution は起動時に monitoring DB のテーブル作成（init_monitoring_db）を行います。特別な初期化は不要です。

主要な環境変数（抜粋）
--------------------
Settings クラスで扱われる環境変数（重要なものを抜粋）:

- KABUSYS_ENV: 起動環境（development | paper_trading | live）デフォルト: development
  - paper_trading の場合は MockBrokerClient を使用し、Paper 用 SQLite（PAPER_TRADING_SQLITE_PATH）に記録する
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: AlertManager（LINE 通知）用
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（monitoring）ファイル（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading 時のフィル設定（instant | partial | never | reject、デフォルト: instant）
- PID_FILE_PATH / KILL_FLAG_PATH: Execution 用 pid ファイル / kill.flag パス
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）

使い方（コマンド例）
------------------

1. 監視ループを起動（SystemMonitor を定期実行して monitoring DB を蓄積）
   - python -m kabusys.run_monitoring
   - 環境変数でポーリング間隔を変更:
     MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

   実行中は data/stop_requested.flag を作成すれば次のポーリングでループを終了します（run_monitoring は _STOP_FLAG を監視）。

2. 実行エンジンを起動（注文/発注処理を行う）
   - python -m kabusys.run_execution
   - KABUSYS_ENV=paper_trading を設定すると Paper Trading モード（MockBrokerClient）になり、data/paper_trading.db に記録します。
   - 実行エンジンも data/stop_requested.flag を監視し、存在時は起動・実行を停止します。

3. Streamlit 監視ダッシュボード
   - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - 起動後、ブラウザでダッシュボードを確認できます（読み取り専用で DB を開きます）。

4. Paper Trading 検証レポート生成
   - python -m kabusys.tools.paper_verification_report
   - 期間指定:
     python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - DB 指定:
     python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

5. AI 関連（ニュース NLP / レジーム判定）
   - ai.news_nlp.score_news(conn, target_date, api_key=...)
   - ai.regime_detector.score_regime(conn, target_date, api_key=...)
   - これらは DuckDB 接続（prices_daily / raw_news / テーブル群）を受け取り、OpenAI を呼びます。OPENAI_API_KEY を環境変数で渡すことも可能。

停止・フラグ管理
----------------
- data/stop_requested.flag: run_monitoring と run_execution のスクリプトが監視する「ソフト停止」フラグ。存在するとループを終了します（管理用）。
- data/execution.pid: ExecutionEngine 実行時に PID を書くファイル（SystemMonitor はこの PID によってプロセス生存チェックを行います）。
- data/kill.flag: KillSwitch が重大なリスク（ドローダウン超過など）を検出した際に書き込み、ExecutionEngine に停止を促します。KillSwitch は冪等に書き込みを行います。

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py — パッケージ定義（バージョン等）
- config.py — 環境変数/設定読み取り（.env ロード自動化含む）
- run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
- run_execution.py — ExecutionEngine 起動スクリプト（paper_trading 切替対応）

src/kabusys/monitoring/
- monitoring_db.py — monitoring 用 SQLite テーブル定義 / DB 操作ラッパー
- system_monitor.py — CPU/メモリ/ディスク/プロセス/データ鮮度チェック
- trade_monitor.py — 注文滞留・約定異常チェック
- risk_monitor.py — ドローダウン / ポジション上限管理
- kill_switch.py — kill.flag の作成・管理
- monitoring_engine.py — 各 Monitor を束ねるエンジン（テスト用 run_once / 本番 run）
- alert_manager.py — LINE 通知ラッパー
- streamlit_dashboard.py — Streamlit ダッシュボード

src/kabusys/execution/
- order_manager.py — 発注ロジックと状態遷移
- order_repository.py — Orders DB アクセス（SQLite）
- reconciler.py — 起動時の注文/ポジション照合
- execution_engine.py, broker_factory.py など（実行に関する他モジュール）

src/kabusys/portfolio/
- portfolio_builder.py — 候補選定・重み計算
- position_sizing.py — 株数算出・単元丸め・集約キャップ
- risk_adjustment.py — セクターキャップ・レジーム乗数

src/kabusys/research/
- factor_research.py — Momentum/Volatility/Value 等のファクター計算（DuckDB）
- feature_exploration.py — 将来リターン, IC, 統計サマリ等

src/kabusys/ai/
- news_nlp.py — ニュース NLP スコアリング（OpenAI 呼び出し）
- regime_detector.py — マクロ × ETF MA で市場レジーム判定

src/kabusys/tools/
- paper_verification_report.py — Paper Trading 検証レポート生成スクリプト

src/kabusys/utils/
- process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

注意事項 / 実運用への留意点
-------------------------
- Paper Trading モードは本番 DB と分離されます（PAPER_TRADING_SQLITE_PATH を使用）。
- OpenAI を呼ぶモジュールは API エラーやレスポンスの不整合に対してフォールバック（ゼロスコアやスキップ）するよう設計されていますが、APIキーや料金に注意してください。
- monitoring DB のスキーマは init_monitoring_db により冪等で作成 / マイグレーションされます。
- .env 自動ロードはプロジェクトルート（.git または pyproject.toml）を探索して行われます。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- process priority / cpu affinity の変更はプラットフォーム依存で例外を吸収する形になっています。権限 (sudo 等) が必要な場合があります。

貢献 / 開発
------------
- 新しい機能やバグ修正は PR でお願いします。テストや型チェック / フォーマッタの導入を推奨します。
- 大きな設計変更（DB スキーマ、外部 API の呼び出し仕様など）はドキュメントを更新してください。

サンプル実行（まとめ）
--------------------
- 開発モードで Execution 起動（Paper Trading を使わない簡易例）:
  KABUSYS_ENV=development python -m kabusys.run_execution

- Paper Trading 実行（Mock broker、検証用 DB）:
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- 監視ループ（デフォルト 60 秒）:
  python -m kabusys.run_monitoring

- Streamlit ダッシュボード:
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper 検証レポート（例）:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

この README はコードベースから主要点を抜粋した要約です。詳細は各モジュールの docstring / コメントを参照してください。