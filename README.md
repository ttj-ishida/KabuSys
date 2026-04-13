README
=====

概要
----
KabuSys は日本株の自動売買および関連ツール群をまとめたプロジェクトです。  
その主な目的は以下です。

- シグナルに基づく発注エンジン（ExecutionEngine）
- 発注・約定のリコンシリエーションとリスク管理
- 監視（System / Trade / Risk）とアラート送信（LINE）
- ポートフォリオ構築・配分・ポジションサイズ計算
- 研究用ファクター計算（DuckDB を利用）
- Paper Trading の検証レポート生成
- ニュースの NLP によるセンチメント評価（OpenAI）
- 市場レジーム判定（OpenAI を利用したマクロセンチメント＋MA）

特徴（機能一覧）
----------------
- Execution
  - 発注管理（OrderManager）、OrderState マシン、ブローカ抽象化（BrokerClientFactory）
  - 起動時のリコンシリエーション（Reconciler）
  - RiskManager による各種リスク制限（ポジション比率、利用率、CB 等）
- Monitoring
  - SystemMonitor：CPU/メモリ/ディスク、プロセス生存、データ鮮度を監視して SQLite に記録
  - TradeMonitor：滞留注文、約定異常価格を検出
  - RiskMonitor：ドローダウン／ポジション上限監視、ダッシュボード更新
  - KillSwitch：旗ファイル writing による ExecutionEngine 停止シグナル
  - AlertManager：LINE Push による通知（クールダウン管理）
  - Streamlit ダッシュボード（監視データ表示）
- Portfolio
  - 候補選定、等金額／スコア加重配分、リスク調整（セクター上限）、ポジションサイズ算出（単元丸め等）
- Research
  - DuckDB を用いたファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC 計算、ファクター統計
- AI
  - ニュース記事のセンチメント評価（OpenAI）→ ai_scores へ保存
  - マクロニュース + ETF MA を使った市場レジーム判定（OpenAI）→ market_regime へ保存
- Tools
  - Paper Trading 検証レポート出力（paper_verification_report）
  - その他ユーティリティ群

前提 / 必要パッケージ
--------------------
推奨 Python バージョン: 3.10+（PEP 604 の表記等を使用）

主要依存（一例）
- duckdb
- psutil
- requests
- streamlit （ダッシュボード利用時）
- openai （AI 機能利用時）
- sqlite3（標準ライブラリ）

※ 実際の requirements.txt はプロジェクトに依存します。開発環境では仮想環境を作成してこれらをインストールしてください。

セットアップ手順
----------------
1. リポジトリをクローン／チェックアウトする
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 依存パッケージをインストール
   - pip install duckdb psutil requests streamlit openai
   - （プロジェクトに requirements.txt があれば pip install -r requirements.txt）
4. 環境変数を設定
   - プロジェクトルートに .env / .env.local を置くと自動ロードされます（デフォルト）。
   - 自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

重要な環境変数（代表）
- KABUSYS_ENV: 実行環境（development | paper_trading | live）。デフォルト: development
  - paper_trading のとき、ExecutionEngine は paper 専用 SQLite（data/paper_trading.db）を使います。
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須な機能で必要）
- KABU_API_PASSWORD: kabu API 用パスワード（必須な機能で必要）
- OPENAI_API_KEY: OpenAI を利用する機能（news_nlp / regime_detector）で必要
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: AlertManager（LINE通知）用
- SQLITE_PATH: 監視データ用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- DUCKDB_PATH: DuckDB DB ファイル（デフォルト: data/kabusys.duckdb）
- PID_FILE_PATH: ExecutionEngine の PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: Kill フラグファイル（デフォルト: data/kill.flag）
- PAPER_FILL_MODE: paper_trading の MockBroker の fill 動作（instant | partial | never | reject）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）

使い方（主要コマンド）
---------------------

1) 監視プロセスを起動（常駐）
- python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（秒）。デフォルト 60 秒。
  - 監視は KABUSYS_ENV にかかわらず production の sqlite_path（SQLITE_PATH）を使用します。
  - 起動時にプロセス優先度を "high" に試みます（プラットフォーム依存で失敗する場合は警告のみ）。

2) ExecutionEngine を起動（発注実行）
- python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、Paper Trading 用 DB（PAPER_TRADING_SQLITE_PATH）へ記録します。
  - 設定に基づき RiskManager・OrderManager 等を組み立ててセッション実行します。

3) Streamlit ダッシュボード（監視データの可視化）
- streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - SQLite を read-only（URI モード）で開いて表示します。
  - データベースが存在しない場合は MonitoringEngine を先に起動してください。

4) Paper Trading 検証レポート
- python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で別 DB を指定可能（デフォルト data/paper_trading.db）。
  - 検証基準（閾値）はスクリプト内定義（稼働率・成功率・P95 レイテンシ等）。

5) AI 系処理（ニュースセンチメント等）
- kabusys.ai.score_news を呼び出して DuckDB の raw_news から ai_scores を更新します（スクリプト形式のエントリポイントはプロジェクトに応じて実行してください）。
  - OPENAI_API_KEY が必要です。
  - 処理はバッチ・リトライ・レスポンス検証を行い、部分成功時でも既存スコアを保護する設計です。
- 市場レジーム判定は kabusys.ai.regime_detector.score_regime を使用（同様に OPENAI_API_KEY 必須）。

実行上の注意
- run_monitoring は監視用 DB に必須テーブルが存在することを保証するため init_monitoring_db を呼び出します（冪等）。
- KillSwitch は data/kill.flag を作成すると ExecutionEngine に停止シグナルを送ります。ExecutionEngine 起動時にフラグをクリアする設定もあります（Settings.kill_flag_clear_on_start）。
- ExecutionEngine は paper_trading 環境時にデータを本番 DB と分離します（安全設計）。
- .env の自動読み込み
  - プロジェクトルートは .git または pyproject.toml を基準に探索します。
  - 自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

ディレクトリ構成（主なファイルと簡単な説明）
-----------------------------------------
src/kabusys/
- __init__.py
- config.py
  - 環境変数 / .env ロード、Settings クラス（全アプリ設定を提供）
- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト
- run_execution.py
  - ExecutionEngine 起動スクリプト（paper/live 切替）
- utils/
  - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ
- monitoring/
  - monitoring_db.py — SQLite スキーマ作成・永続化 API（MonitoringDB）
  - system_monitor.py — CPU/メモリ/ディスク/プロセス/データ鮮度監視
  - trade_monitor.py — 滞留注文・約定異常検出
  - risk_monitor.py — ドローダウン / ポジション上限監視
  - kill_switch.py — kill.flag の作成・評価
  - alert_manager.py — LINE 通知
  - monitoring_engine.py — 複数 Monitor を束ねるエンジン
  - streamlit_dashboard.py — Streamlit を用いたダッシュボード
- execution/
  - order_manager.py — 発注の高レベル API（state machine）
  - reconciler.py — 起動時のリコンシリエーション（注文 + ポジション）
  - （ほか broker, order_repository, risk_manager 等：実装に応じて存在）
- portfolio/
  - portfolio_builder.py — 候補選定・スコアソート
  - position_sizing.py — 株数決定・aggregate cap・単元丸め
  - risk_adjustment.py — セクターキャップ・レジーム乗数
- research/
  - factor_research.py — Momentum / Volatility / Value の計算（DuckDB）
  - feature_exploration.py — 将来リターン・IC・統計要約
- ai/
  - news_nlp.py — ニュースの LLM ベースセンチメント評価（OpenAI）
  - regime_detector.py — MA200 + マクロセンチメント合成によるレジーム判定
- tools/
  - paper_verification_report.py — Paper Trading の検証レポート出力

主要な実装方針（補足）
-------------------
- DB は SQLite（監視用）と DuckDB（時系列・分析）を併用する設計です。
- 可能な限り「ルックアヘッドバイアス」を避ける実装が意識されています（AI / 指標計算で日付の排他条件等）。
- 外部 API 呼び出し（OpenAI / ブローカー / LINE）はフェイルセーフやリトライ、レスポンス検証を行い、部分失敗時にも他データを保護するように設計されています。
- 多くのモジュールは副作用を持たない純粋関数や小さなクラスに分割されており、単体テストしやすい構造です。

ライセンス / 貢献
-----------------
（この README にはライセンス情報は含まれていません。必要に応じて LICENSE ファイルを追加してください。）

以上。プロジェクトの他の部分に関して補足や特定コマンドのサンプルが必要であれば教えてください。