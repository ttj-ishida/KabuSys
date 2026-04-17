README
======

概要
----
KabuSys は日本株向けの自動売買基盤の一部を実装した Python パッケージです。  
トレード実行（ExecutionEngine）、実行監視（Monitoring）、ポートフォリオ構築、リサーチ／ファクター計算、ニュース NLP（OpenAI）によるセンチメントスコアリングなどの主要コンポーネントを含みます。

主な設計方針:
- 本番と Paper Trading を明確に分離（Paper Trading は別 SQLite DB に記録）
- DuckDB を用いた時系列・ファイナンスデータの分析
- モジュール単位で純粋関数（副作用を持たない実装）を多用
- OpenAI（gpt-4o-mini）を利用したニュース NLP／レジーム判定（API キー必要）
- 監視は SQLite にログを永続化し、LINE でアラート通知可能

機能一覧
--------
- ExecutionEngine 起動・実行（run_execution.py）
  - Broker クライアント生成（本番 / モックを切り替え）
  - OrderManager / RiskManager / Reconciler を組み合わせて実行
  - Paper Trading 時は専用 DB に記録
- Monitoring（監視）コンポーネント
  - SystemMonitor: CPU / メモリ / ディスク / プロセス生存確認 / データ鮮度監視
  - TradeMonitor: 滞留注文・約定価格異常検出
  - RiskMonitor: ドローダウンやポジション上限の監視とアラート記録
  - MonitoringEngine: 上記監視を束ねて定期ポーリング
  - AlertManager: LINE プッシュ通知（クールダウン管理）
  - KillSwitch: 条件に応じて data/kill.flag を書き込み、ExecutionEngine 停止をトリガー
  - Streamlit ダッシュボードで監視情報を可視化（streamlit_dashboard.py）
- Portfolio 構築ユーティリティ
  - 候補選定、等分配・スコア重み配分、セクターキャップ適用、ポジション数計算（単元丸め含む）
- Research（リサーチ）
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC 計算、ファクター統計サマリ
- AI（OpenAI）関連
  - news_nlp.score_news: raw_news を LLM でセンチメント評価し ai_scores に書き込み
  - regime_detector.score_regime: ETF MA200 乖離 + マクロニュースの LLM センチメントで市場レジーム判定
- ユーティリティ
  - process_priority: プラットフォーム差分を吸収したプロセス優先度 / CPU affinity 設定
  - .env 自動読み込み（プロジェクトルートの .env / .env.local）

セットアップ手順
----------------

1. 前提
   - Python 3.10+ 推奨
   - OS: Linux / macOS / Windows（プロセス優先度や CPU affinity は OS に依存する挙動あり）
   - 必要パッケージ（代表例）:
     - duckdb, psutil, openai, requests, streamlit など
   - 例: 仮想環境を作成してインストール
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
     - pip install duckdb psutil openai requests streamlit

2. リポジトリルート準備
   - プロジェクトルートに data ディレクトリを作成:
     - mkdir -p data

3. 環境変数 / .env
   - 自動読み込み: プロジェクトルートに .env または .env.local を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 主要な環境変数（最低限必要なもの）
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - OPENAI_API_KEY (AI 機能を使う場合必須)
   - 任意 / デフォルト
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト: INFO）
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
     - PAPER_FILL_MODE: instant|partial|never|reject（Paper トレード挙動）
     - PID_FILE_PATH, KILL_FLAG_PATH 等（default data/execution.pid / data/kill.flag）
   - サンプル .env（簡易）
     - JQUANTS_REFRESH_TOKEN=xxx
     - KABU_API_PASSWORD=yyy
     - OPENAI_API_KEY=zzz
     - KABUSYS_ENV=development

4. データベース初期化
   - Monitoring 用 SQLite は run_monitoring / run_execution 起動時に init_monitoring_db() で必要テーブルを作成します。通常手動初期化は不要です。

使い方
------

- 監視ループを起動（Monitoring）
  - デフォルトで本番 sqlite_path を使って監視ログを記録します（KABUSYS_ENV に依存せず本番 DB を参照する実装）。
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（秒、デフォルト 60 秒）。0 以下や不正値は 60 秒にフォールバック。
  - 停止: プロジェクトルート/data/stop_requested.flag ファイルを作ると run_monitoring が検知して終了します。
  - 実行例:
    - python -m kabusys.run_monitoring
    - または python src/kabusys/run_monitoring.py

- 実行エンジンを起動（ExecutionEngine）
  - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し、Paper Trading 用 DB (PAPER_TRADING_SQLITE_PATH) に記録します（本番 DB と完全分離）。
  - 起動時に data/stop_requested.flag が既に存在する場合は起動せず終了します。
  - 実行例:
    - python -m kabusys.run_execution
    - または python src/kabusys/run_execution.py

- Monitoring の可視化（Streamlit ダッシュボード）
  - 起動例:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - read-only URI として DB を開きます。MonitoringEngine を先に起動してログを書き込んでください。

- Paper Trading 検証レポート
  - data/paper_trading.db（または --db で指定）を解析してレポートを標準出力に出力します。
  - 実行例:
    - python -m kabusys.tools.paper_verification_report
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- OpenAI を用いた機能
  - ニュース NLP（ai.news_nlp.score_news）およびレジーム判定（ai.regime_detector.score_regime）は OPENAI_API_KEY が必要です。これらはモジュール関数として呼び出せます（外部スクリプトから import して使用）。
  - モデル: gpt-4o-mini を想定、バッチ化・リトライ・レスポンス検証を実装済み。

- 停止・強制停止
  - run_execution / run_monitoring はプロジェクトルート/data/stop_requested.flag を監視して安全にシャットダウンします。
  - KillSwitch は条件を満たすと data/kill.flag を書き込み ExecutionEngine に停止シグナルを送ります（ExecutionEngine 側は起動時に KILL_FLAG_CLEAR_ON_START 設定でフラグをクリアできます）。

運用メモ / 重要事項
------------------
- Paper Trading は本番 DB と分離されます。Paper の DB は環境変数 PAPER_TRADING_SQLITE_PATH で指定してください（デフォルト data/paper_trading.db）。
- MONITOR_POLL_INTERVAL は監視間隔（秒）。不正な値は 60 秒にフォールバックします。
- process_priority.set_process_priority("high") が起動時に呼ばれます。OS によっては権限不足で警告が出ますが無害です。
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml がある場所）から行われます。CWD に依存しないためパッケージ配布後も安定して動作します。
- OpenAI API 呼び出しはレートリミット・ネットワーク障害等に対して指数バックオフでリトライしますが、API キーがない・無効な場合は例外または警告になるため運用時は必ず設定してください。

ディレクトリ構成（主要ファイル）
-----------------------------
- src/kabusys/
  - __init__.py          — パッケージ定義（バージョン等）
  - config.py            — 環境変数 / Settings 管理（.env 自動ロード・検証含む）
  - run_monitoring.py    — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py     — ExecutionEngine 起動スクリプト
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py      — SQLite 監視ログ永続化層（テーブル定義・CRUD）
    - system_monitor.py     — CPU/メモリ/ディスク/データ鮮度/プロセス監視
    - trade_monitor.py      — 注文滞留・約定異常監視
    - risk_monitor.py       — ドローダウン・ポジション上限監視
    - kill_switch.py        — kill.flag 書き込みユーティリティ
    - alert_manager.py      — LINE 通知クライアント
    - monitoring_engine.py  — 各 Monitor を束ねるポーリングエンジン
    - streamlit_dashboard.py— Streamlit ダッシュボード（起動コマンドあり）
  - execution/
    - order_manager.py      — 発注管理 / ステートマシンへの橋渡し
    - reconciler.py         — 起動時のリコンシリエーション（注文・ポジション整合）
    - ... （BrokerFactory / ExecutionEngine 等が含まれる）
  - portfolio/
    - portfolio_builder.py  — 候補選定・重み算出
    - position_sizing.py    — 発注株数計算（単元丸め・リスク制約）
    - risk_adjustment.py    — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py    — Momentum / Volatility / Value の計算
    - feature_exploration.py— 将来リターン / IC / 統計サマリ
  - ai/
    - news_nlp.py           — ニュースセンチメント（OpenAI）
    - regime_detector.py    — 市場レジーム判定（OpenAI + MA200）
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート出力スクリプト

ライセンス / 貢献
-----------------
（このリポジトリにライセンスファイルがあればその内容に従ってください。開発・運用にあたってはテストと段階的導入を推奨します。）

補足
----
- 実運用ではログ収集 / 権限設定（プロセス優先度変更権限）や安全な API キー管理に注意してください。
- 本 README はコードベースから抽出した情報を元にまとめています。詳細な設計や追加オプションはソース内ドキュメント（関数 docstring）を参照してください。