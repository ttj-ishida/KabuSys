KabuSys — 自動売買フレームワーク（README）
======================================

概要
----
KabuSys は日本株向けの自動売買／リサーチ基盤のコードベースです。  
DuckDB / SQLite を用いたデータ解析・永続化、発注リポジトリ、監視（Monitoring）、Paper Trading の分離、LLM（OpenAI）を利用したニュース NLP や市場レジーム判定などの機能を含みます。

主な特徴
--------
- ポートフォリオ構築（候補選定、等重・スコア重み、リスク調整、株数決定）
- 発注管理（OrderManager / ExecutionEngine 組立て、リコンシリエーション）
- 監視機能（SystemMonitor / TradeMonitor / RiskMonitor、LINE 通知）
- Monitoring DB（SQLite）による監視ログ永続化と Streamlit ダッシュボード
- Paper Trading 環境の完全分離（専用 SQLite DB）
- ニュース文章を LLM でスコアリングする AI モジュール（OpenAI）
- 市場レジーム判定（MA + マクロニュースセンチメントの合成）
- 各種ユーティリティ（プロセス優先度設定、.env 自動読み込みなど）

セットアップ
-----------
前提
- Python 3.9+（型注釈や一部記法に依存）
- DuckDB, psutil, requests, openai, streamlit 等のパッケージが必要

1. リポジトリをクローン
   - git clone … （パスは省略）

2. 仮想環境作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install duckdb psutil requests openai streamlit
   - （実際は requirements.txt があれば pip install -r requirements.txt）

4. 環境変数設定
   - プロジェクトルートに .env / .env.local を置くと自動で読み込まれます（デフォルト）。  
     自動読み込みを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
   - 主要な環境変数（例）
     - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
     - JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
     - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
     - OPENAI_API_KEY: OpenAI API キー（AI 機能使用時）
     - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
     - DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
     - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
     - PAPER_FILL_MODE: instant | partial | never | reject（Paper Trading の約定挙動）
     - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト: 60）
     - PID_FILE_PATH / KILL_FLAG_PATH 等も設定可能

使い方（主要コマンド）
--------------------

- 監視プロセス（SystemMonitor のポーリングループ）起動
  - python -m kabusys.run_monitoring
  - 説明: プロセス優先度を高く設定し、SQLite（settings.sqlite_path）に接続して SystemMonitor を polling（MONITOR_POLL_INTERVAL 秒）で実行します。  
    注意: run_monitoring は KABUSYS_ENV にかかわらず本番用 sqlite_path を使用します。
  - 停止方法: data/stop_requested.flag を作成するか Ctrl+C（KeyboardInterrupt）。monitoring は起動時に data/stop_requested.flag を監視します。

- 実行エンジン（ExecutionEngine）起動
  - python -m kabusys.run_execution
  - 説明: プロセス優先度を高くして ExecutionEngine を起動します。KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、Paper Trading 用の SQLite（PAPER_TRADING_SQLITE_PATH）に記録します。
  - 停止方法: data/stop_requested.flag を作成すると安全停止を試みます。実行中は data/execution.pid が作成されます。

- Paper Trading 検証レポート生成（CLI）
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - 説明: paper_trading DB（デフォルト data/paper_trading.db）を集計し、稼働率・注文成功率・レイテンシなどの指標を出力します。

- Streamlit 監視ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 説明: ブラウザでダッシュボードを表示。DB を read-only で開きます。

- AI 機能（Python API）
  - ニューススコアリング: kabusys.ai.score_news（DuckDB 接続と対象日を渡す）
  - レジーム判定: kabusys.ai.regime_detector.score_regime（DuckDB 接続と対象日を渡す）
  - どちらも OpenAI API キー（OPENAI_API_KEY または引数）を必要とします。API 呼び出しはリトライやフェイルセーフ処理を備えています。

重要なファイル・フラグ
--------------------
- data/stop_requested.flag
  - run_execution / run_monitoring が存在をチェックする停止フラグ（作成で終了をトリガ）。
- data/execution.pid
  - 実行エンジン起動時に作成される PID ファイル。SystemMonitor はこの PID を見てプロセスの生存確認を行います。
- data/kill.flag
  - KillSwitch（監視による安全停止判断）が書き込むフラグ。ExecutionEngine はこのファイルを見て停止します。

ディレクトリ構成（主なモジュール）
---------------------------------
- src/kabusys/
  - __init__.py (パッケージ情報)
  - config.py
    - Settings クラス、.env 自動読み込み・検証ロジック
  - run_monitoring.py
    - SystemMonitor をポーリングで実行するスクリプト
  - run_execution.py
    - ExecutionEngine を起動するスクリプト（paper_trading 分離対応）
  - ai/
    - news_nlp.py: ニュースを OpenAI でスコアリングして ai_scores に書き込む
    - regime_detector.py: MA とマクロニュースを合成して market_regime を算出
  - monitoring/
    - monitoring_db.py: SQLite 用のスキーマ初期化・簡易永続化 API（MonitoringDB）
    - system_monitor.py: CPU/メモリ/ディスク/データ鮮度/実行プロセス監視
    - trade_monitor.py: 注文滞留・約定価格異常検出
    - risk_monitor.py: ドローダウン・ポジション上限チェック
    - kill_switch.py: 判定に基づき kill.flag を書き込む
    - alert_manager.py: LINE push 通知（クールダウン有り）
    - monitoring_engine.py: モニター群のオーケストレーション（テスト用 run_once / 本番 run）
    - streamlit_dashboard.py: Streamlit ダッシュボード
  - execution/
    - order_manager.py, reconciler.py, order_repository.py など（発注・同期）
    - execution_engine.py（起動 / セッション管理） — 起動スクリプトから利用
  - portfolio/
    - portfolio_builder.py: 候補選定・重み計算
    - position_sizing.py: 株数計算・ロット丸め・投下上限対応
    - risk_adjustment.py: セクター上限・レジーム乗数
  - research/
    - factor_research.py: Momentum/Value/Volatility 等の定量ファクター計算（DuckDB）
    - feature_exploration.py: 将来リターン・IC・統計サマリ
  - tools/
    - paper_verification_report.py: Paper Trading の検証レポート生成 CLI
  - utils/
    - process_priority.py: プロセス優先度 / CPU affinity 設定ユーティリティ

実装上のポイント・注意事項
--------------------------
- .env 自動読み込み
  - プロジェクトルート（.git または pyproject.toml の存在するディレクトリ）を基準に .env と .env.local を自動読み込みします。OS の環境変数が優先され、.env.local は .env を上書きします。自動無効化は KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
- DB の分離
  - Paper Trading（KABUSYS_ENV=paper_trading）は paper_trading 用 SQLite を使用し、本番 DB と完全に分離されます（run_execution で切替）。
  - ただし run_monitoring は KABUSYS_ENV に関係なく settings.sqlite_path（本番監視 DB）を使う点に注意してください。
- OpenAI 呼び出し
  - news_nlp / regime_detector は OpenAI を呼びます。API キーは OPENAI_API_KEY に設定するか関数引数で渡してください。呼び出しはリトライ・フェイルセーフ設計です（失敗時は代替値で継続）。
- フラグによる停止
  - 安全停止や外部からの停止は flag ファイル（data/stop_requested.flag, data/kill.flag）で行います。ファイルベースのシンプルな制御です。
- 権限・プラットフォーム差分
  - process_priority や cpu_affinity は psutil を利用。権限不足や未対応 OS の場合は警告を出してスキップします。

開発・デバッグのヒント
--------------------
- MonitoringEngine.run_once() を使うと単発で各 Monitor の動作を確認できます（テスト用）。
- DuckDB 接続を渡して research モジュールを単体実行すればファクター計算の検証が可能です。
- streamlit ダッシュボードはデータを read-only で開くので監視中の DB を安全に監視できます。

ライセンス・貢献
----------------
- （ここにライセンスや貢献方法の記載を追加してください。）

問い合わせ
----------
- 実装方針や設計ドキュメント（PortfolioConstruction.md, StrategyModel.md 等）に準拠した実装が多く含まれます。実行時の問題や環境変数設定についてはまず config.Settings のプロパティを参照してください。

以上。必要であれば README にサンプル .env.example、requirements.txt、起動・デバッグ例（詳細なコマンド）を追加します。どの情報を追加しますか？