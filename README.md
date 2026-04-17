KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株の自動売買・研究・監視を目的とした小規模なシステム群です。本リポジトリは以下の主要機能を持ちます。

- 発注エンジン（ExecutionEngine）と注文管理（OrderManager / OrderRepository）
- モニタリング（システム状態、注文滞留、リスク監視）とアラート送信（LINE）
- Paper Trading 用の分離された DB / モックブローカ実行
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ計算・セクター制限）
- 研究用ファクター計算（モメンタム / ボラティリティ / バリュー）と特徴量解析ユーティリティ
- ニュース NLP（OpenAI を使った銘柄センチメントスコアリング）
- 検証レポート出力ツール（paper_verification_report）
- Streamlit ベースの監視ダッシュボード

主な設計方針
- DuckDB を使った時系列データ処理（prices_daily / raw_financials 等）
- SQLite を監視ログ・注文ログ保存に使用
- Paper Trading は本番 DB と分離（data/paper_trading.db など）
- 外部 API 呼び出し（OpenAI など）は明示的に API キーを渡すか環境変数を使う
- ルックアヘッドバイアスを避ける（date.now 参照を限定する設計）

機能一覧
-------
- Execution
  - ExecutionEngine 起動スクリプト: src/kabusys/run_execution.py
  - ブローカーファクトリ、OrderManager、Reconciler（起動時リコンシリエーション）
  - Paper Trading モード（環境変数 KABUSYS_ENV=paper_trading）で MockBroker を使い DB を分離
- Monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor による定期チェック
  - MonitoringEngine（ポーリングループ）
  - kill_switch（条件に応じた停止フラグ書き込み）
  - AlertManager（LINE Push による通知）
  - SQLite ベースの監視 DB 初期化・ラッパー（monitoring_db）
  - Streamlit ダッシュボード（src/kabusys/monitoring/streamlit_dashboard.py）
- AI / NLP
  - news_nlp: OpenAI を用いた銘柄ごとのニュースセンチメント化（ai_scores への書き込み）
  - regime_detector: ma200 とマクロニュースの LLM 評価を合成して市場レジーム判定
- Research
  - factor_research: momentum / volatility / value のファクター計算（DuckDB 経由）
  - feature_exploration: 将来リターン計算、IC（スピアマン）や統計サマリー
- Portfolio
  - portfolio_builder: 候補選定と重み（等分 / スコア加重）
  - position_sizing: 株数計算、単元丸め、aggregate cap スケーリング
  - risk_adjustment: セクター上限適用、レジーム乗数計算
- Tools
  - paper_verification_report: Paper Trading の検証レポート生成スクリプト（コマンドライン）

セットアップ手順
----------------

前提
- Python 3.9+（コードの型ヒントに合わせてください）
- 必要な外部ライブラリ（例: duckdb, psutil, requests, openai, streamlit）

推奨手順（プロジェクトルートで実行）
1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - pip install -U pip
   - pip install duckdb psutil requests openai streamlit

   （requirements.txt がある場合は pip install -r requirements.txt）

3. パッケージとして使う（任意）
   - プロジェクトルート直下に src/ が配置されている想定です。
   - 開発モードでインストールすると python -m kabusys.* が使いやすくなります:
     - pip install -e .

環境変数（主要）
- KABUSYS_ENV: 起動環境。値: development | paper_trading | live（デフォルト: development）
  - paper_trading の場合、実行は PAPER_TRADING_SQLITE_PATH（data/paper_trading.db）を使用
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須：一部機能で）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須：ブローカー連携）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で使用）
- PAPER_FILL_MODE: Paper Trading の約定モード（instant|partial|never|reject、デフォルト: instant）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite パス（デフォルト: data/paper_trading.db）
- SQLITE_PATH: 監視 DB パス（デフォルト: data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: AlertManager（LINE）用
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）※ run_monitoring で参照
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1: config.py による .env 自動ロードを無効化

ヒント: 自動で .env ファイル（プロジェクトルートの .env と .env.local）を読み込みます。テストなどで自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

使い方
------

1) 監視ループ起動（Monitoring）
- コマンド:
  - python -m kabusys.run_monitoring
- 説明:
  - SystemMonitor をポーリングして monitoring DB に記録します。
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - 監視は KABUSYS_ENV に関わらず sqlite_path（production 相当）を使用します。
  - 停止はプロジェクトルート data/stop_requested.flag の作成で検出します。

2) 実行エンジン起動（Execution Engine）
- コマンド:
  - python -m kabusys.run_execution
- 説明:
  - ExecutionEngine を起動して発注処理を行います。
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、Paper Trading 用 DB（PAPER_TRADING_SQLITE_PATH）を使用します。
  - 起動時に data/stop_requested.flag が存在すると起動せず終了します。
  - 実行中は data/execution.pid に PID が書き込まれます。監視はこの PID ファイルの存在を確認してプロセス生存を判断します。

3) Streamlit ダッシュボード
- コマンド:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- 説明:
  - 監視 DB を read-only で開いてダッシュボードを表示します。
  - MonitoringEngine を先に起動してデータを蓄積してください。

4) Paper Trading 検証レポート
- コマンド:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定: --from YYYY-MM-DD --to YYYY-MM-DD
  - DB 指定: --db PATH （PAPER_TRADING_SQLITE_PATH 環境変数で代替可能）
- 説明:
  - Paper Trading DB（data/paper_trading.db）を集計して稼働率、注文成功率、レイテンシなどを出力します。

5) AI / News スコアリング・レジーム判定
- news_nlp.score_news および regime_detector.score_regime は DuckDB 接続と target_date, api_key を受け取る関数 API です。
- 実行例（スクリプト呼び出しはありません。外部ジョブから呼ぶ想定）:
  - from kabusys.ai.news_nlp import score_news
  - score_news(conn, target_date, api_key="...")

停止・制御フロー
- stop_requested.flag（data/stop_requested.flag）: run_monitoring / run_execution で定期チェックされる停止フラグ
- kill.flag（Settings.kill_flag_path デフォルト data/kill.flag）: KillSwitch が書き込むことで ExecutionEngine に安全停止シグナルを送る
- pid_file（Settings.pid_file_path）: ExecutionEngine の稼働確認に使用

ディレクトリ構成（主要ファイル）
------------------------------
（src/kabusys 配下の主要モジュールと簡単な説明）

- kabusys/
  - __init__.py              — パッケージ定義（バージョン等）
  - config.py                — 環境設定 / .env 読み込み / Settings クラス
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成 CLI
  - utils/
    - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py       — SQLite 監視 DB 初期化と MonitoringDB ラッパー
    - system_monitor.py      — システム状態 / データ鮮度チェック
    - trade_monitor.py       — 注文滞留 / 約定異常チェック
    - risk_monitor.py        — ドローダウン / ポジション上限監視
    - kill_switch.py         — 停止フラグ書き込みユーティリティ
    - alert_manager.py       — LINE Push 通知管理
    - monitoring_engine.py   — 各 Monitor を束ねるポーリングロジック
    - streamlit_dashboard.py — Streamlit ダッシュボード
  - execution/
    - order_manager.py       — OrderManager（発注・状態遷移）
    - reconciler.py          — 起動時リコンシリエーション（突合せ）
    - (その他: broker_factory, order_repository, execution_engine 等が存在想定)
  - portfolio/
    - portfolio_builder.py   — 候補選定、等重/スコア重み
    - position_sizing.py     — 株数決定・aggregate cap
    - risk_adjustment.py     — セクター制限・レジーム乗数
  - research/
    - factor_research.py     — Momentum/Volatility/Value ファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン / IC / 統計サマリ
  - ai/
    - news_nlp.py            — ニュースの LLM センチメント化 / ai_scores 書込
    - regime_detector.py     — 市場レジーム判定（ma200 + LLM）
  - data/                    — 実行時に使われる DB / フラグファイル置き場（例: data/monitoring.db）

実用上の注意
-------------
- DB スキーマの初期化: run_monitoring / run_execution 起動時に monitoring DB を初期化する処理が走ります（冪等）。
- Paper Trading: paper_trading 環境では本番の注文 DB と完全分離するよう設計されています。必ず KABUSYS_ENV=paper_trading を設定してから実行してください。
- OpenAI API: 呼び出しは課金対象です。API キーを環境変数または関数引数で明示的に渡してください。レスポンスの検証やリトライロジックを含み、失敗時はフェイルセーフ（0.0 等にフォールバック）する設計です。
- process priority / affinity: 管理者権限が必要になる場合があります。権限不足時は警告ログを出してスキップします。
- .env 取り扱い: config.py はプロジェクトルートの .env / .env.local を自動で読み込みます。必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

サンプル .env（最小）
------------------
# .env.example の例（値は置き換えてください）
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
OPENAI_API_KEY=sk-...
JQUANTS_REFRESH_TOKEN=xxxxxxxx
KABU_API_PASSWORD=your_kabu_password
LINE_CHANNEL_ACCESS_TOKEN=
LINE_USER_ID=

貢献・テスト
-------------
- 新しい機能追加やバグ修正は PR を送ってください。
- 単体テストフレームワーク等は本リポジトリに含まれていませんが、モジュール設計は純粋関数と DI（接続/クライアント注入）を意識しているため、ユニットテストが書きやすくなっています。

ライセンス
----------
- 本 README はコードベースから生成したドキュメントです。ライセンス情報はリポジトリの LICENSE ファイルを参照してください。

以上。必要であれば、README に載せる系の環境変数一覧を表形式で詳細にしたり、よくある運用手順（デプロイ、バックアップ、監視アラート設定方法）を追記します。どの情報をもっと詳しく記載しますか？