README — KabuSys（日本株自動売買システム）
======================================

概要
----
KabuSys は日本株を対象とした自動売買システムのコアライブラリ群です。  
本リポジトリは以下の主要機能をモジュール単位で提供します:
- 注文作成・管理・再同期（Execution）
- 監視・アラート・キルスイッチ（Monitoring）
- ポートフォリオ構築（Portfolio: 候補選定・重み付け・株数決定）
- リサーチ（ファクター計算・特徴量解析）
- ニュース NLP（OpenAI を用いたニュースセンチメント）
- Market Regime 判定（AI + MA ベースの合成）
- Paper Trading（本番 DB と分離された模擬売買モード）
- モニタリング用 Streamlit ダッシュボード
- 検証レポート生成ツール（paper_verification_report）

機能一覧
--------
- Execution
  - Broker 抽象化（実ブローカー / MockBroker 切替）
  - OrderManager / OrderRepository（状態管理と永続化）
  - Reconciler による再起動後の自動同期とポジション差分検出
  - RiskManager（注文制限・ドローダウンなどの保護）
- Monitoring
  - SystemMonitor: CPU/Mem/Disk/プロセス存在・データ鮮度監視
  - TradeMonitor: 注文滞留、約定異常価格の検出
  - RiskMonitor: ドローダウン・ポジション数監視とログ記録
  - KillSwitch: ルールに基づく停止フラグの書き込み
  - AlertManager: LINE Push による通知（クールダウン付き）
  - MonitoringEngine: 各 Monitor の統合ポーリング
  - Streamlit ダッシュボード（監視情報閲覧）
- Portfolio
  - 候補選定、等重・スコア加重配分、リスク調整（セクターキャップ、レジーム乗数）
  - position sizing（risk_based / equal / score）
- Research
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
- AI 関連
  - news_nlp: raw_news をまとめて OpenAI に送り、銘柄ごとにセンチメントを ai_scores に保存
  - regime_detector: ETF MA とマクロニュースセンチメントを合わせ市場レジーム判定
- ツール
  - paper_verification_report: Paper Trading DB から検証レポートを出力

前提条件 / 必要ソフトウェア
-------------------------
- Python 3.9+
- SQLite（標準ライブラリで利用）
- 必要な Python パッケージ（主要なもの）:
  - duckdb
  - psutil
  - openai
  - requests
  - streamlit (ダッシュボードを使う場合)

セットアップ手順
----------------
1. リポジトリをクローン / 配布パッケージを展開
   - 例: git clone ... && cd repository

2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - Windows: .venv\Scripts\activate
   - macOS/Linux: source .venv/bin/activate

3. 必要パッケージをインストール
   - pip install duckdb psutil openai requests streamlit
   - （プロジェクトに requirements.txt があれば pip install -r requirements.txt）

4. 環境変数設定
   - 通常はプロジェクトルートの .env / .env.local を用いると自動で読み込まれます。
   - 自動ロードを無効化する場合: export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   - 主な環境変数（代表例）:
     - KABUSYS_ENV: development | paper_trading | live  (デフォルト: development)
     - JQUANTS_REFRESH_TOKEN: 必須（J-Quants API 用）
     - KABU_API_PASSWORD: 必須（kabuステーション API 用）
     - OPENAI_API_KEY: ニュース NLP / regime_detector を使う場合必須
     - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 DB（デフォルト: data/paper_trading.db）
     - SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
     - DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知用
     - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
     - PAPER_FILL_MODE: paper_trading 時の約定モード（instant|partial|never|reject）

5. data ディレクトリの用意
   - 参考: 多くのデフォルトパスが data/*.db / data/*.flag を参照します。必要に応じて作成してください。

ユーティリティ / フラグ
-----------------------
- 停止フラグ（実行制御）
  - data/stop_requested.flag: run_monitoring / run_execution 停止検知に使用
  - data/kill.flag: KillSwitch が作成するフラグ（ExecutionEngine を停止するため）
- PID ファイル
  - data/execution.pid（ExecutionEngine 起動時に書き込み）

使い方（主要スクリプト）
-----------------------

1) 監視ループを起動（Monitoring）
- 説明: SystemMonitor を定期実行して監視ログを SQLite に保存します。プロセス優先度を "high" に設定します。
- 実行例:
  - PYTHONPATH=src python src/kabusys/run_monitoring.py
  - またはパッケージがインポート可能な状態で: python -m kabusys.run_monitoring
- オプション/環境変数:
  - MONITOR_POLL_INTERVAL: ポーリング間隔（秒、デフォルト 60）
  - 監視は Settings に従い監視用 DB（SQLITE_PATH）を使用（KABUSYS_ENV に依存せず本番 sqlite_path を使う点に注意）

2) ExecutionEngine を起動（注文処理）
- 説明: ブローカークライアントを生成して ExecutionEngine を起動します。paper_trading モードでは MockBroker を使い DB は data/paper_trading.db に分離されます。
- 実行例:
  - PYTHONPATH=src python src/kabusys/run_execution.py
  - または: python -m kabusys.run_execution
- 動作:
  - 起動時に data/stop_requested.flag が存在すると起動を辞めます。
  - 起動中は data/execution.pid に PID を書きます。停止は kill.flag により制御されます（KillSwitch が書き込む）。
  - paper_trading 向けの挙動は Settings.is_paper を参照します。

3) Streamlit ダッシュボード（監視確認）
- 説明: 監視 DB を読み取り専用で表示するダッシュボード
- 実行:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- 注意: DB は読み取り専用で開かれます（?mode=ro）。MonitoringEngine が DB を更新していることを確認してください。

4) Paper Trading 検証レポート生成
- スクリプト:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH （PAPER_TRADING_SQLITE_PATH 環境変数でも可）
- 出力: 標準出力に検証指標（稼働率、注文成功率、レイテンシ等）と PASS/FAIL を表示

5) AI 機能（ニュース NLP / レジーム判定）
- 事前に OPENAI_API_KEY を設定する必要があります。
- news_nlp.score_news(conn, target_date) や regime_detector.score_regime(conn, target_date) を呼び出して利用します。
- OpenAI 呼び出しにはリトライやクリッピング等の安全策が組み込まれていますが、API キーの管理は注意してください。

設定ローディングの挙動
--------------------
- .env / .env.local はプロジェクトルート（.git または pyproject.toml がある場所）を自動検出して読み込まれます。
- 読み込み順序: OS 環境変数 > .env.local > .env
- 自動読み込みを無効化するには: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

停止・強制停止フロー
--------------------
- 監視ループ・ExecutionEngine はプロジェクトルート/data/*.flag を参照して停止制御を行います。
  - stop_requested.flag: 手動停止（起動チェック・ループ内チェック）
  - kill.flag: KillSwitch による実行停止（Execution 停止の合図）
- KillSwitch は条件（ドローダウン超過、ポジション数超過等）に応じて data/kill.flag を生成します。

ディレクトリ構成（主要ファイル）
------------------------------
以下は本 README に含まれるコードベースの主要ファイル一覧（抜粋）です:

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数 / Settings 管理（.env 自動読み込み）
  - run_monitoring.py             — SystemMonitor ポーリング起動スクリプト
  - run_execution.py              — ExecutionEngine 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py — Paper Trading 検証レポート出力
  - ai/
    - __init__.py
    - news_nlp.py                  — ニュースセンチメント（OpenAI 連携）
    - regime_detector.py          — 市場レジーム判定（MA + マクロセンチメント）
  - monitoring/
    - __init__.py
    - monitoring_db.py            — SQLite テーブル初期化 & 永続化 API
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - streamlit_dashboard.py
  - execution/
    - reconciler.py
    - order_manager.py
    - order_repository.py (参照)
    - execution_engine.py (参照)
    - broker_factory.py (参照)
    - ...
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - utils/
    - __init__.py
    - process_priority.py

補足・実運用上の注意
-------------------
- Paper Trading と Live は DB を分離しているため、paper_trading 実行で誤って本番 DB を汚すリスクは低く設計されています（ただし環境変数の誤設定には注意）。
- OpenAI API 呼び出しはコストとレイテンシを伴います。news_nlp / regime_detector はバッチやリトライに配慮した設計ですが、実運用では API の使用量とエラー時のフォールバックを考慮してください。
- process priority / cpu affinity はプラットフォーム依存（psutil 経由）。権限不足で失敗する場合はログに警告が出てスキップされます。
- DB マイグレーションは monitoring_db.init_monitoring_db() にて基本的な追加カラムの互換処理を行いますが、複雑なスキーマ変更は手動対応が必要になる場合があります。

ライセンス / コントリビュート
------------------------------
- 本プロジェクトのライセンス情報、貢献方法、コードスタイル等はリポジトリのトップにある LICENSE / CONTRIBUTING を参照してください（存在する場合）。

問い合わせ
----------
- 実装や動作に関する質問は Issue を立てるか、プロジェクト内の担当者に連絡してください。

以上。必要であれば、README にインストール用 requirements.txt の推奨内容や具体的なサンプル .env.example を追記します。どの情報を追加したいか教えてください。