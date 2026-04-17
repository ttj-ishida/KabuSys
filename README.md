README
======

プロジェクト概要
----------------
KabuSys は日本株向けの自動売買・リサーチ・監視ツール群です。本リポジトリは以下の主要機能を含みます。
- 実運用向け ExecutionEngine（発注・注文管理・リコンシリエーション）
- 監視基盤（システム監視、注文監視、リスク監視、アラート送信）
- ポートフォリオ構築ユーティリティ（候補選定、重み付け、株数計算、セクター制限）
- リサーチ用ファクター計算・特徴量解析
- AI を使ったニュースセンチメント評価・市場レジーム判定（OpenAI を利用）
- Paper Trading 用の分離された DB と検証レポート生成ツール
- Streamlit ベースの監視ダッシュボード

主な設計方針：
- DB は SQLite（監視用 / paper trading 用）と DuckDB（時系列・ファクタ演算用）を併用
- 本番/Paper は環境変数で分離（paper_trading 環境では発注 API をモック化）
- 監視・AI 呼び出し等は失敗してもフェイルセーフ（例外を許容して継続）
- .env ファイルの自動ロード機能を備え、配布後も CWD に依存しない挙動

主な機能一覧
-------------
- run_execution.py: ExecutionEngine の起動（発注ループ・リスク管理・リコン）
  - KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用し data/paper_trading.db に記録
- run_monitoring.py: SystemMonitor のポーリング起動（デフォルト 60 秒）
  - 環境変数 MONITOR_POLL_INTERVAL で間隔を変更可能
- monitoring:
  - system_monitor: CPU / メモリ / ディスク / データ鮮度 / PID 存在を監視
  - trade_monitor: 注文滞留・異常約定価格を検出
  - risk_monitor: ドローダウン・ポジション上限を検出しリスクログに永続化
  - kill_switch: 条件成立時に data/kill.flag を書き ExecutionEngine を停止させる仕組み
  - alert_manager: LINE API へのプッシュ通知（クールダウン管理）
  - streamlit_dashboard: 監視用ダッシュボード（streamlit で閲覧）
- portfolio:
  - 銘柄選定・スコア重み・等金額重み、位置サイズの算出、セクター制限、レジーム乗数
- research:
  - factor_research: Momentum / Volatility / Value 等のファクターを DuckDB 上で計算
  - feature_exploration: 将来リターン計算、IC（スピアマン）や統計要約
- ai:
  - news_nlp.score_news: raw_news を集約して OpenAI でセンチメントを算出 → ai_scores に保存
  - regime_detector.score_regime: ETF 1321 の MA200 乖離とマクロセンチメントを合成して market_regime を更新
- tools:
  - paper_verification_report: Paper Trading DB を解析して検証レポートを標準出力

セットアップ手順
----------------
前提
- Python 3.10+（typing で | 演算子を使用）
- SQLite（Python 標準ライブラリで使用）
- 推奨パッケージ（pip インストール）：
  - duckdb
  - psutil
  - openai
  - requests
  - streamlit (ダッシュボード利用時)

例（仮想環境）
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - pip install duckdb psutil openai requests streamlit

3. 環境変数の準備
   - プロジェクトルートに .env を置く（.env.example を参考）
   - 自動ロードはデフォルトで有効（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化）
   - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD（実行部分による）

代表的な環境変数（重要なもの）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能使用時に必須）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用（任意）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite のパス（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading 時の約定モード（instant|partial|never|reject、デフォルト instant）
- PID_FILE_PATH: ExecutionEngine の PID ファイル（デフォルト data/execution.pid）
- KILL_FLAG_PATH: KillSwitch の flag ファイル（デフォルト data/kill.flag）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）

使い方（起動・コマンド例）
-------------------------

1) ExecutionEngine を起動（本番／paper）
- 本番（既定の KABUSYS_ENV=development を明示的に上書きし live にする等は .env で設定）
  - python -m kabusys.run_execution
- Paper Trading（MockBroker を使用、DB を分離）
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

2) Monitoring を起動（SystemMonitor の簡易ポーリング）
- python -m kabusys.run_monitoring
- ポーリング間隔を変更する場合:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

3) Streamlit ダッシュボード（監視データ閲覧）
- streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- ダッシュボードは監視 DB を read-only で開くため、MonitoringEngine を先に動作させてデータを生成しておく必要があります。

4) Paper Trading 検証レポート出力
- python -m kabusys.tools.paper_verification_report
- 期間指定:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- 別 DB 指定:
  - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

5) AI / リサーチ機能の実行（サンプル）
- OpenAI キーを設定した上で、Python スクリプト内から関数を呼ぶか REPL から:
  - from kabusys.ai.news_nlp import score_news
  - score_news(duckdb_conn, target_date, api_key="...")

注意点・運用に関する補足
- run_execution は起動時に data/stop_requested.flag の存在を確認します。stop フラグを利用して安全停止する運用が想定されています。
- kill_switch は条件成立時に KILL_FLAG_PATH（デフォルト data/kill.flag）を書き込み、ExecutionEngine に対して停止シグナルを送ります。
- Monitoring は常に「本番の sqlite_path」を使って監視データを記録します（環境にかかわらず）。
- Paper Trading は専用 DB（PAPER_TRADING_SQLITE_PATH）に記録され、本番 DB と完全に分離されます。
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行われます。自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

ディレクトリ構成（抜粋）
---------------------
src/
  kabusys/
    __init__.py                 — パッケージ定義、バージョン
    config.py                   — 環境変数 / Settings 管理（.env 自動ロード含む）
    run_execution.py            — ExecutionEngine 起動スクリプト
    run_monitoring.py           — SystemMonitor 起動スクリプト
    tools/
      paper_verification_report.py — Paper Trading 検証レポート生成
    utils/
      process_priority.py       — プロセス優先度 / CPU affinity ユーティリティ
    monitoring/
      __init__.py
      monitoring_db.py          — SQLite スキーマ初期化 + 永続化 API
      system_monitor.py
      trade_monitor.py
      risk_monitor.py
      kill_switch.py
      alert_manager.py
      monitoring_engine.py
      streamlit_dashboard.py
    execution/
      order_manager.py
      reconciler.py
      ...                       — Execution 系の他ファイル（broker_factory 等）
    portfolio/
      portfolio_builder.py
      position_sizing.py
      risk_adjustment.py
    research/
      factor_research.py
      feature_exploration.py
    ai/
      news_nlp.py
      regime_detector.py
    data/                       — 実行時に使用される SQLite / DuckDB / flag / pid など（既定: data/*.db）
    ... (その他モジュール)

重要なファイル・データ（実行時）
- data/monitoring.db           — 監視ログ SQLite（init_monitoring_db で自動作成・マイグレーション）
- data/paper_trading.db       — Paper Trading 専用 SQLite（PAPER_TRADING_SQLITE_PATH）
- data/kabusys.duckdb         — DuckDB（時系列・ファクタ計算用）
- data/execution.pid          — ExecutionEngine の PID（存在チェックに使用）
- data/stop_requested.flag    — run_*.py が監視している停止フラグ
- data/kill.flag              — KillSwitch による停止指示ファイル（ExecutionEngine 停止トリガ）

開発・拡張メモ
- DuckDB のテーブル（prices_daily / raw_financials / raw_news 等）を用意すると research / ai 機能が動作します。
- OpenAI 呼び出しは外部 API に依存するため、テスト時は各モジュール内の _call_openai_api をモックして振る舞いを制御できます（コード内にその旨の注釈あり）。
- monitoring_db.init_monitoring_db() は冪等で実行でき、既存スキーマに対する簡単なマイグレーションもサポートします（例: latency_ms / peak_value の追加）。

ライセンス / 貢献
----------------
（本 README には記載されていません。必要に応じて LICENSE ファイルを追加してください）

お問い合わせ / 参照
------------------
- .env.example（プロジェクトルート）を参照して環境変数を設定してください。
- 実行時のログは Python の logging を使って標準出力に出ます。デバッグ時は LOG_LEVEL=DEBUG を設定してください。

以上。必要であれば各コマンドの具体的な実行例や .env.example のテンプレートを追記します。