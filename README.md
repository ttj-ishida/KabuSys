KabuSys — 日本株自動売買システム
==============================

このリポジトリは日本株の自動売買システム（KabuSys）のコアコンポーネント群を含みます。
主に「監視（Monitoring）」「注文実行（Execution）」「ポートフォリオ構築」「リサーチ/ファクター計算」「AI（ニュースセンチメント／レジーム判定）」などの機能を提供します。

要点
- 言語: Python
- パッケージ構成: src/kabusys 以下にモジュール群を配置
- デフォルトの永続化: SQLite（監視ログ等）および DuckDB（時系列・ファクターデータ）

機能一覧
- 実行系
  - ExecutionEngine 起動スクリプト（src/kabusys/run_execution.py）
    - 本番・Paper Trading を環境変数 KABUSYS_ENV により切替
    - Paper Trading の場合は MockBroker を用いて data/paper_trading.db に記録（本番 DB と分離）
    - 起動時にプロセス優先度を上げる処理あり
- 監視系
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine（src/kabusys/monitoring）
  - run_monitoring 起動スクリプト（src/kabusys/run_monitoring.py）
    - 定期ポーリングでシステム状態・データ鮮度・滞留注文・リスク事象を記録
    - stop フラグファイルで安全停止
  - SQLite ベースの監視 DB レイヤ（monitoring_db.py）
  - Streamlit ダッシュボード（src/kabusys/monitoring/streamlit_dashboard.py）
  - LINE へのアラート送信（AlertManager）
  - KillSwitch による ExecutionEngine 停止シグナル生成（kill.flag）
- ポートフォリオ構築
  - 候補選定（score/ rank ベース）、等重・スコア重み配分（portfolio/portfolio_builder.py）
  - リスク調整（セクターキャップ、レジーム乗数）（portfolio/risk_adjustment.py）
  - 株数算出・単元切り上げ・投下資金スケーリング（portfolio/position_sizing.py）
- リサーチ（research）
  - ファクター計算（momentum / value / volatility）（research/factor_research.py）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリ（research/feature_exploration.py）
- AI（OpenAI）
  - ニュースセンチメント: raw_news をまとめて LLM に投げ、ai_scores に保存（ai/news_nlp.py）
  - 市場レジーム判定: ETF (1321) の MA200 とマクロ記事の LLM センチメントを合成（ai/regime_detector.py）
  - OpenAI の利用は API キー（OPENAI_API_KEY）を必要とする
- ユーティリティ
  - 環境変数管理（.env 自動ロード機能: src/kabusys/config.py）
  - プロセス優先度 / CPU affinity 設定ユーティリティ（utils/process_priority.py）
- ツール
  - Paper Trading 検証レポート生成スクリプト（tools/paper_verification_report.py）

セットアップ手順（ローカルでの実行例）
1. リポジトリをクローン
   - 任意のディレクトリにリポジトリをチェックアウトします。
2. Python 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate（Windows: .venv\Scripts\activate）
3. 依存ライブラリをインストール
   - requirements.txt がある場合: pip install -r requirements.txt
   - 主に必要なパッケージ（目安）:
     - duckdb, psutil, requests, openai, streamlit
   - 例: pip install duckdb psutil requests openai streamlit
4. 環境変数の設定
   - .env または OS 環境変数で設定可能（src/kabusys/config.py が自動で .env / .env.local を読み込みます）
   - 自動ロードを無効にする場合: export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   - 代表的な環境変数:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - JQUANTS_REFRESH_TOKEN: 必須（J-Quants API 用）
     - KABU_API_PASSWORD: 必須（kabuステーション API 用）
     - OPENAI_API_KEY: OpenAI を使う機能で必須
     - PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）
     - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
     - SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
     - DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
     - PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START 等（監視/制御用）
   - サンプル .env:
     - KABUSYS_ENV=paper_trading
     - OPENAI_API_KEY=sk-...
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
5. 初期データディレクトリを準備
   - data/ ディレクトリを作成（README 内のデフォルトファイルがここに置かれます）
   - mkdir -p data
6. パッケージのインストール（開発時）
   - プロジェクトを編集可能モードでインストールすると python -m kabusys.* がパッケージとして動きます:
     - pip install -e .

使い方（主要な実行例）
- 監視ループ起動
  - 簡易（パッケージをインストールしている場合）
    - python -m kabusys.run_monitoring
  - ソース直起動（PYTHONPATH に src を追加）
    - PYTHONPATH=src python src/kabusys/run_monitoring.py
  - ポーリング間隔を環境変数で上書き:
    - export MONITOR_POLL_INTERVAL=120  # 120秒
  - 監視は常に本番 sqlite_path を使います（KABUSYS_ENV に依らず）
  - 停止: プロジェクトルート/data/stop_requested.flag を作成するとループが安全に終了します
- 実行エンジン起動（注文実行）
  - 本番（注意して実行してください）
    - python -m kabusys.run_execution
  - Paper Trading モード
    - export KABUSYS_ENV=paper_trading
    - python -m kabusys.run_execution
    - Paper Trading は settings.paper_sqlite_path（デフォルト data/paper_trading.db）に完全分離して記録します
  - 停止: 同じく data/stop_requested.flag を作成 → 実行ループが検出して停止します
- Streamlit ダッシュボード（監視データの可視化）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を指定する場合:
    - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
- AI/LLM 機能（ニューススコア／レジーム判定）
  - OPENAI_API_KEY が必要です（引数で明示的に渡すことも可能な関数があります）
  - これらはライブラリ関数として利用することを想定:
    - from kabusys.ai.news_nlp import score_news
    - from kabusys.ai.regime_detector import score_regime

運用上のファイル・フラグ
- data/stop_requested.flag
  - 管理者がこのファイルを作ると run_monitoring / run_execution が安全に停止します
- data/kill.flag
  - KillSwitch がリスク条件により作成（ExecutionEngine に停止を要求）
- data/execution.pid
  - ExecutionEngine が稼働時に PID を書き込むファイル（SystemMonitor が stale PID を検知）
- DB ファイル（既定値）
  - SQLite 監視 DB: data/monitoring.db
  - Paper Trading SQLite: data/paper_trading.db
  - DuckDB: data/kabusys.duckdb

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数/.env 読み込みと Settings
  - run_monitoring.py             — SystemMonitor ポーリング起動スクリプト
  - run_execution.py              — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート CLI
  - ai/
    - news_nlp.py                 — ニュースの LLM センチメント集計・書き込み
    - regime_detector.py          — レジーム判定（MA200 + マクロセンチメント）
  - monitoring/
    - monitoring_db.py            — SQLite 監視 DB 初期化 / 永続化 API
    - system_monitor.py           — CPU/メモリ/ディスク/プロセス/データ鮮度監視
    - trade_monitor.py            — 注文滞留 / 約定異常チェック
    - risk_monitor.py             — ドローダウン・ポジション上限監視
    - kill_switch.py              — kill.flag の作成/管理
    - alert_manager.py            — LINE 送信クライアント
    - monitoring_engine.py        — 各 Monitor を束ねるエンジン
    - streamlit_dashboard.py      — Streamlit ダッシュボード
  - execution/
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - execution_engine.py         — 実行エンジン本体（主要ロジックはここ）
    - broker_factory.py
    - broker_api.py
    - order_record.py
    - order_repository.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - utils/
    - process_priority.py         — プロセス優先度 / CPU affinity 設定ユーティリティ

注意事項 / 運用上の留意点
- 環境切替
  - KABUSYS_ENV によって一部挙動が変わります（paper_trading では本番ブローカーに接続せず DB を分離）
- DB マイグレーション
  - monitoring_db.init_monitoring_db() は冪等でテーブル作成や軽微なカラム追加（マイグレーション）を行います
- セキュリティ
  - API キーやパスワード等は .env や .env.local に保存する場合、適切にアクセス制御してください
  - .env.local は .env をオーバーライド可能で、ローカル秘匿値の管理に便利です
- LLM 呼び出し
  - OpenAI の呼び出しはネットワークエラーや 429 に対してリトライロジックを実装していますが、API 利用料やレートには注意してください
- テスト / 開発
  - 環境変数の自動ロードを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください
  - テスト時はモック可能な箇所（OpenAI 呼び出し等）が設計上考慮されています（関数を差し替えてテスト可能）

貢献 / 拡張案
- 銘柄別単元情報（lot_size）のマスタ化による position sizing の拡張
- ai/news_nlp と regime_detector の共通化（現在はテスト容易性のため別実装）
- より詳細なマイグレーションフレームワーク導入（Alembic 等ではなく軽量な独自仕組みでも可）
- モニタリングメトリクスの外部送信（Prometheus / Grafana 連携）

問い合わせ
- 実行や設定で不明点があれば、具体的な実行コマンド・環境変数設定内容・発生したログを提示して質問してください。

以上がリポジトリの概要・セットアップ・実行方法です。必要があれば、具体的な .env のテンプレートや systemd / Supervisor ユニットファイル例、Docker 化手順なども追記します。どの情報を追加希望か教えてください。