# KabuSys — README

このリポジトリは日本株向けの自動売買システム「KabuSys」の一部実装です。  
本 README はコードベース（src/kabusys 以下）を元にプロジェクト概要、機能、セットアップ、使い方、ディレクトリ構成を日本語でまとめたものです。

注意: 実運用を意図した完全実装ではなく、モジュール群（ポートフォリオ構築、リサーチ、発注エンジン、監視、AI 集約など）を含む設計実装サンプルです。

概要
- 名前: KabuSys
- 目的: 日本株の自動売買パイプライン（信号生成 → ポートフォリオ構築 → 注文実行 → 監視／アラート）を提供するライブラリ／ランタイム。
- 主な技術:
  - SQLite（監視ログ / 発注ログ等）
  - DuckDB（時系列株価・財務データ分析）
  - psutil（プロセス／リソース監視）
  - requests, LINE Messaging API（監視アラート）
  - OpenAI（ニュース NLP / レジーム判定）
  - Streamlit（監視ダッシュボード）

主要な機能一覧
- Execution
  - ExecutionEngine 起動スクリプト（src/kabusys/run_execution.py）
  - Broker クライアント（実運用 / Paper Trading 用 Mock に対応）
  - OrderManager / OrderRepository：注文状態管理・DB 永続化
  - Reconciler：再起動時の受注・ポジション突合
  - RiskManager：発注前リスクチェック（設定に基づく）
- Monitoring（監視）
  - SystemMonitor：CPU / メモリ / ディスク / プロセス PID / データ鮮度監視
  - TradeMonitor：滞留注文・約定異常価格検出
  - RiskMonitor：ドローダウン・ポジション上限監視とリスクイベント記録
  - KillSwitch：条件に応じて停止フラグ（data/kill.flag）を生成し ExecutionEngine を停止可能
  - AlertManager：LINE への一方向通知（クールダウン機能あり）
  - MonitoringEngine：上記モニタの束ねと定期実行
  - Streamlit ダッシュボード（src/kabusys/monitoring/streamlit_dashboard.py）
- Research / Signals
  - factor_research：モメンタム / ボラティリティ / バリュー等ファクター計算（DuckDB）
  - feature_exploration：将来リターン計算、IC 計算、統計サマリ
- Portfolio construction
  - portfolio_builder：候補選定・重み計算（等配分・スコア加重）
  - risk_adjustment：セクターキャップ、レジーム乗数
  - position_sizing：株数決定・単元丸め・aggregate cap
- AI
  - news_nlp：ニュース記事を LLM（OpenAI）でセンチメント化して ai_scores テーブルへ書き込み
  - regime_detector：ETF + マクロニュースから市場レジーム判定（bull/neutral/bear）
- ユーティリティ
  - config.Settings：環境変数 / .env 自動読み込み、各種設定のラッパ
  - process_priority：プロセス優先度／CPU affinity 設定ユーティリティ
  - tools.paper_verification_report：Paper Trading の検証レポート生成スクリプト

セットアップ手順（ローカル開発）
1. Python 環境
   - 推奨: Python 3.10+（コードは型ヒントで Union 表現などを使用）
   - 仮想環境を作成:
     - python -m venv .venv
     - source .venv/bin/activate (Windows: .venv\Scripts\activate)

2. 依存パッケージ（例）
   - 必要な主要パッケージ（pip）:
     - duckdb
     - psutil
     - requests
     - openai
     - streamlit
   - インストール例:
     - pip install duckdb psutil requests openai streamlit

   （実際の requirements.txt はこのリポジトリに含まれていないため、上記を参考に追加してください。）

3. プロジェクトルートと .env
   - Settings モジュールはプロジェクトルート（.git または pyproject.toml を基準）を自動検出して .env / .env.local を読み込みます（環境変数が優先）。
   - 自動ロードを無効にしたい場合:
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
   - 代表的な環境変数（.env 例）:
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - OPENAI_API_KEY=...
     - KABUSYS_ENV=development | paper_trading | live
     - PAPER_FILL_MODE=instant|partial|never|reject
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - SQLITE_PATH=data/monitoring.db
     - DUCKDB_PATH=data/kabusys.duckdb
     - LINE_CHANNEL_ACCESS_TOKEN=...
     - LINE_USER_ID=...
     - LOG_LEVEL=INFO
     - MONITOR_POLL_INTERVAL=60  (監視ポーリング間隔、秒)

4. データディレクトリ
   - data/ ディレクトリを作る（監視 DB・PID・フラグファイルがここに置かれることを想定）:
     - mkdir -p data

使い方（代表的なコマンドと説明）
- 監視ループの起動
  - python src/kabusys/run_monitoring.py
  - 特記事項:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト: 60 秒）
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計
    - 起動時にプロセス優先度を "high" に設定しようとします（権限により失敗する場合はスキップ）

- Execution エンジンの起動
  - python src/kabusys/run_execution.py
  - 特記事項:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、Paper Trading 用の専用 SQLite（PAPER_TRADING_SQLITE_PATH, default: data/paper_trading.db）に記録して本番 DB と分離
    - 起動時、data/stop_requested.flag が存在すると起動せず終了します
    - 実行中に stop flag を置くことでスレッドを停止できます（data/stop_requested.flag を作成）

- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 監視 DB を読み取り専用で開いて簡易ダッシュボード表示

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db path/to/paper_trading.db （環境変数 PAPER_TRADING_SQLITE_PATH より優先して使用）

- AI / レジーム判定・ニューススコアリング（ライブラリ API）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - DuckDB 接続を渡して指定日にニューススコアを作成・ai_scores テーブルへ書込み
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - DuckDB 接続を渡して市場レジーム判定を行い market_regime テーブルに書込み
  - どちらも OPENAI_API_KEY 環境変数を使用可能。未設定の場合は引数で渡す必要あり。

停止・キル関連
- run_monitoring.py / run_execution.py はそれぞれプロセス優先度設定やポーリング／スレッド監視を行います。
- 停止フラグ:
  - data/stop_requested.flag: run_monitoring/run_execution のループを終了させるために使用（スクリプトは存在をチェックし検出したら終了）
  - KillSwitch はリスク条件によって data/kill.flag を書き込み（ExecutionEngine 停止要求）。ExecutionEngine 側は kill.flag の有無を参照して停止するよう設計されています。
- ExecutionEngine 側は pid ファイル（data/execution.pid など）を使用し stale PID の検出と削除を行います。

設定と制約（Settings より）
- KABUSYS_ENV: development | paper_trading | live（無効値は例外）
- PAPER_FILL_MODE: instant | partial | never | reject（paper trading の約定挙動制御）
- CPU / Memory / Disk の閾値は Settings 経由で環境変数から設定可能（CPU_THRESHOLD_PCT 等）
- .env 自動読み込み順序: OS 環境変数 > .env.local > .env（OS 環境変数は保護され上書きされない）
- .env が存在しない場合やプロジェクトルートが検出できない場合は自動ロードをスキップ

主要ディレクトリ構成（src/kabusys）
- src/kabusys/
  - __init__.py (パッケージ定義)
  - config.py (Settings / .env 読み込み)
  - run_monitoring.py (SystemMonitor のポーリングループ起動スクリプト)
  - run_execution.py (ExecutionEngine 起動スクリプト)
  - utils/
    - process_priority.py (プロセス優先度 / CPU affinity ユーティリティ)
  - monitoring/
    - __init__.py
    - monitoring_db.py (SQLite テーブル初期化 / CRUD ラッパ)
    - system_monitor.py (システム / データ鮮度監視)
    - trade_monitor.py (滞留注文 / 約定異常検出)
    - risk_monitor.py (ドローダウン / ポジション上限監視)
    - kill_switch.py (kill.flag 書き込みユーティリティ)
    - alert_manager.py (LINE 送信)
    - monitoring_engine.py (複数 monitor を束ねる)
    - streamlit_dashboard.py (Streamlit ダッシュボード)
  - execution/
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - execution_engine.py (エンジン本体 が存在する想定)
    - broker_factory.py / broker_api.py (ブローカー抽象)
  - portfolio/
    - portfolio_builder.py (候補選定 / 重み)
    - position_sizing.py (株数計算 / 単元丸め)
    - risk_adjustment.py (セクターキャップ / レジーム乗数)
  - research/
    - factor_research.py (ファクター計算)
    - feature_exploration.py (IC / 統計等)
  - ai/
    - news_nlp.py (ニュース -> AI スコア)
    - regime_detector.py (市場レジーム判定)
  - data/ (実行時に使用する SQLite / DuckDB / PID / flag ファイル置き場を想定; 手動で作成)
  - tools/
    - paper_verification_report.py (Paper Trading 検証レポート)

補足・実務上の注意
- DB マイグレーション: monitoring_db.init_monitoring_db() は冪等にテーブルを作り、既存テーブルに対する簡易マイグレーション（カラム追加）も行います。
- ロギング: 起動スクリプトは logging.basicConfig(level=logging.INFO) を使用。LOG_LEVEL 環境変数で変更可能。
- セキュリティ: 環境変数に API キーやパスワードを設定する設計。 .env ファイルの取り扱いは注意してください。
- テスト: 各モジュールは副作用を最小化する設計だが、外部 API 呼び出し（OpenAI / Broker / LINE）はモック化してテストすることを推奨します（コード中にも patch 対応箇所あり）。

よく使うコマンドまとめ
- 依存インストール:
  - pip install duckdb psutil requests openai streamlit
- 監視開始:
  - python src/kabusys/run_monitoring.py
- 実行エンジン開始:
  - python src/kabusys/run_execution.py
- Streamlit ダッシュボード:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- Paper 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

以上がこのコードベースの README です。必要であれば、インストール用の requirements.txt や .env.example、運用手順書（起動・停止・ログローテーション・バックアップ等）を追加で作成できます。どの情報を優先して追加しましょうか？