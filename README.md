KabuSys — 日本株自動売買フレームワーク
=================================

概要
----
KabuSys は日本株の自動売買・リサーチ・監視機能を備えた軽量な内部フレームワークです。  
主に以下の責務を持ちます。

- 注文発行/状態管理（ExecutionEngine 周辺）
- モニタリング（システム状態・注文滞留・リスク監視）
- ポートフォリオ構築（候補選定・重み計算・ポジションサイズ算出）
- 研究支援（ファクター計算・将来リターン・IC 等）
- AI を使ったニュースセンチメント評価 / レジーム判定
- Paper Trading 用の分離された DB と検証ツール

特徴
----
- モジュール設計（execution, monitoring, portfolio, research, ai, tools）
- DuckDB / SQLite を用いたデータ処理・永続化
- OpenAI（gpt-4o-mini）を用いたニュース NLP / レジーム判定（任意）
- Streamlit ベースの監視ダッシュボード
- Paper Trading（本番 DB と分離）対応
- フラグファイルによる外部停止（kill.flag / stop_requested.flag）
- プロセス優先度設定ユーティリティ（Windows/Linux 対応）

主要機能一覧
--------------
- Execution
  - 注文生成 / Order State Machine（OrderManager）
  - ブローカー抽象化（BrokerClientFactory, Broker API プロトコル）
  - 起動時のリコンシリエーション（Reconciler）
  - Paper Trading 用 MockBroker（環境切替）
- Monitoring
  - SystemMonitor: CPU/Memory/Disk、データ鮮度、実行プロセス確認
  - TradeMonitor: 滞留注文・約定異常価格チェック
  - RiskMonitor: ドローダウン・保有上限の監視とアラート記録
  - KillSwitch / AlertManager: 条件に応じた停止フラグ作成と LINE 通知
  - MonitoringEngine: 各モニタを束ねたポーリングループ
  - Streamlit ダッシュボード（read-only で monitoring.db を参照）
- Portfolio
  - 候補選定（select_candidates）
  - 重み計算（等分配/スコア加重）
  - セクター制限適用（apply_sector_cap）
  - レジーム乗数（calc_regime_multiplier）
  - 株数決定 / 集約キャップ対応（calc_position_sizes）
- Research
  - Momentum/Volatility/Value 等のファクター計算（DuckDB 経由）
  - 将来リターン計算、IC 計算、統計サマリー
- AI
  - ニュース NLP（news_nlp.score_news）：raw_news から銘柄別センチメントを生成して ai_scores に書込み
  - レジーム判定（regime_detector.score_regime）：MA200 とマクロセンチメントの合成
- Tools
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）

セットアップ手順
-----------------
前提
- Python 3.10+ を推奨
- SQLite は標準ライブラリに同梱
- 必須 Python パッケージ（例）
  - duckdb
  - psutil
  - openai
  - requests
  - streamlit (ダッシュボード利用時)

インストール（例）
1. 仮想環境を作る
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール
   - pip install duckdb psutil openai requests streamlit

（プロジェクトに requirements.txt があればそれを利用してください）

.env（環境変数）
- 自動ロード順序: OS 環境変数 > .env.local > .env
- 自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
- 主要な環境変数（最低限必要なもの）
  - JQUANTS_REFRESH_TOKEN — J-Quants API（必須）
  - KABU_API_PASSWORD — kabuステーション API パスワード（必須）
  - OPENAI_API_KEY — OpenAI API キー（AI 機能を使う場合）
  - KABUSYS_ENV — 起動環境: development | paper_trading | live （デフォルト: development）
  - PAPER_FILL_MODE — Paper Trading の約定モード（instant|partial|never|reject）
  - PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
  - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — LINE 通知用
  - MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、run_monitoring で使用）

ディレクトリ構成
-----------------
（主要ファイル/ディレクトリのみ抜粋）
- src/kabusys/
  - __init__.py (package metadata)
  - config.py (環境変数 / Settings)
  - run_execution.py (ExecutionEngine 起動スクリプト)
  - run_monitoring.py (SystemMonitor ポーリング起動スクリプト)
  - tools/
    - paper_verification_report.py (Paper Trading 検証レポート)
  - execution/ (ExecutionEngine、OrderManager、Reconciler、OrderRepository 等)
  - monitoring/
    - monitoring_db.py (SQLite テーブル定義・永続化 API)
    - system_monitor.py, trade_monitor.py, risk_monitor.py
    - monitoring_engine.py, kill_switch.py, alert_manager.py
    - streamlit_dashboard.py (Streamlit ダッシュボード)
  - portfolio/ (portfolio_builder, position_sizing, risk_adjustment)
  - research/ (factor_research, feature_exploration)
  - ai/ (news_nlp, regime_detector)
  - utils/ (process_priority など)
- data/ (実行時生成: monitoring.db, paper_trading.db, *.pid, stop_requested.flag, kill.flag 等)

使い方
------
実行・監視関連
- 実行エンジンを起動
  - python -m kabusys.run_execution
  - 挙動
    - Settings.env に応じて本番 DB または Paper Trading DB を選択（paper_trading 時は data/paper_trading.db を使用）
    - プロセス優先度を "high" に設定する（可能なら）
    - ExecutionEngine をスレッドで起動し、data/stop_requested.flag が作られると停止する
  - PID ファイル: data/execution.pid（デフォルト）
  - 起動前に data/kill.flag があれば起動を抑止する（kill_flag_clear_on_start 環境変数で動作制御）

- 監視ループを起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で変更（デフォルト 60 秒）
  - 監視は常に本番用 sqlite_path を参照（環境に依らず）

- 外部停止 / 強制停止
  - run_monitoring / run_execution はプロジェクトルート/data/stop_requested.flag の存在を検知して終了
  - KillSwitch は data/kill.flag を作成し ExecutionEngine 側に停止シグナルを送る設計
  - kill.flag を消したい場合は rm data/kill.flag（clear メソッドで削除も可能）

監視ダッシュボード（Streamlit）
- 起動:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- 読み取り専用で監視 DB を表示（positions, orders, system status, recent risk events）

Paper Trading 検証レポート
- 使い方:
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD  （開始日）
    - --to   YYYY-MM-DD  （終了日）
    - --db PATH          （SQLite DB パス、環境変数 PAPER_TRADING_SQLITE_PATH を上書き）
- 例:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

AI 機能
- ニュース NLP（ai.score_news）およびレジーム判定（ai.regime_detector.score_regime）は OpenAI API キーに依存します。環境変数 OPENAI_API_KEY を設定するか、関数呼び出し時に api_key を渡してください。
- API 呼び出しはリトライ・バックオフやレスポンス検証を行う設計です。AI 機能はオプションです。

開発者向けメモ
----------------
- 環境ロード
  - config.py はプロジェクトルート（.git または pyproject.toml を探す）を基準に .env / .env.local を自動で読み込みます。テストで自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DB マイグレーション
  - monitoring_db.init_monitoring_db は冪等でテーブル作成と簡易マイグレーション（列追加）を行います。起動時に自動で呼ばれます。
- プロセス優先度
  - utils.process_priority.set_process_priority("high") を起動時に呼び出してプロセス優先度を上げます。権限や OS によっては設定できない場合があり、その際は警告ログになります。
- テスト
  - AI/外部 API 呼び出し部分は _call_openai_api のような内部関数を patch して差し替え可能な設計になっています。

よく使うファイル一覧（参照）
- src/kabusys/run_execution.py — 実行エンジン起動
- src/kabusys/run_monitoring.py — システム監視ループ起動
- src/kabusys/config.py — 環境変数と Settings
- src/kabusys/monitoring/ — 監視関連全般（DB、各種モニタ、KillSwitch、AlertManager、Streamlit）
- src/kabusys/portfolio/ — ポートフォリオ構築ロジック
- src/kabusys/research/ — ファクター・統計処理
- src/kabusys/ai/ — ニュース NLP / レジーム判定
- src/kabusys/tools/paper_verification_report.py — Paper Trading 検証レポート生成

ライセンス・貢献
----------------
- 本リポジトリのライセンス情報や貢献ガイドラインはプロジェクトルートの LICENSE / CONTRIBUTING を参照してください（存在する場合）。

補足（トラブルシュート）
-----------------------
- DB ファイルが見つからない / 開けない: monitoring 用は data/monitoring.db（CONFIG SQLITE_PATH）を参照。Streamlit は読み取り専用で URI ベースで開くためパスに注意してください。
- kill.flag / stop_requested.flag が残っていると起動・継続が阻害されます。問題がある場合は data/*.flag を確認してください。
- OpenAI の API 呼び出し失敗はログに記録され、AI 機能はフォールバック挙動（スコア 0.0 など）を取りうるよう設計されています。

以上が本プロジェクトの概要と利用方法です。その他、各モジュール（monitoring_db, SystemMonitor, TradeMonitor, portfolio, research, ai）内の docstring に詳細設計・注意事項が記載されていますので、実装や拡張時はそちらも参照してください。