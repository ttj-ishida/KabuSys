# KabuSys

日本株自動売買システムのモジュール群（ライブラリ＋実行スクリプト）。  
このリポジトリは、戦略のポートフォリオ構築、ポジションサイズ決定、実行エンジン、監視・アラート、Research 用ユーティリティ、AI を使ったニュースセンチメントなどで構成されています。

概要
- 言語: Python
- 目的: 日本株の自動売買ロジック（シグナル→配分→発注）と、発注実行の監視・検証・補助ツール群を提供する。
- 設計方針:
  - DuckDB をデータ分析用に、SQLite を監視ログ・発注ログ用に使用
  - 本番 / paper_trading を環境で分離可能
  - LLM（OpenAI）を用いたニュースセンチメント／レジーム判定機能を有するが、API失敗時は安全側で継続する（フェイルセーフ）

主な機能一覧
- 実行エンジン起動: run_execution.py（ExecutionEngine 起動、Reconciler による再同期処理）
- 監視ループ起動: run_monitoring.py（SystemMonitor を周期実行し、ログ保存）
- 監視コンポーネント:
  - SystemMonitor: CPU/メモリ/ディスク、Execution プロセス生存、データ鮮度を監視
  - TradeMonitor: 滞留注文、約定異常価格を監視
  - RiskMonitor: ドローダウン／保有数上限を監視、ダッシュボード更新・リスクログ記録
  - MonitoringEngine: 上記を束ねて定期実行、KillSwitch 評価、AlertManager による通知
- アラート: AlertManager（LINE Messaging API へのプッシュ）
- KillSwitch: 条件に応じて data/kill.flag を書き込み、ExecutionEngine 停止シグナルを送る
- Streamlit ダッシュボード: 監視 DB を可視化（streamlit_dashboard.py）
- Research:
  - ファクター計算（momentum, volatility, value）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリ
- Portfolio construction:
  - 候補選定、等分配／スコア加重、セクター制限、レジーム乗数、株数計算（単元丸め付き）
- AI 関連:
  - news_nlp.score_news: raw_news をまとめて OpenAI に投げ、銘柄別スコアを ai_scores テーブルへ書込
  - regime_detector.score_regime: ma200 乖離 と マクロニュースの LLM センチメントを合成して market_regime に書込
- ツール:
  - tools/paper_verification_report.py: Paper Trading DB から検証レポートを生成

セットアップ手順（開発環境向け・一例）
1. リポジトリをクローン
   - git clone <repo_url>
2. Python 仮想環境作成（例）
   - python -m venv .venv
   - source .venv/bin/activate（Windows: .venv\Scripts\activate）
3. 依存ライブラリをインストール
   - pip install pip --upgrade
   - pip install duckdb psutil openai requests streamlit
   - （必要に応じて他のライブラリを追加）
   - 推奨: requirements.txt を用意している場合は pip install -r requirements.txt
4. data ディレクトリ作成（起動時に自動作成されることもありますが明示的に）
   - mkdir -p data
5. 環境変数設定
   - プロジェクトルートに .env を置くか、OS 環境変数で設定
   - 主な環境変数（Settings 参照）:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
     - DUCKDB_PATH（分析 DB、デフォルト: data/kabusys.duckdb）
     - PAPER_TRADING_SQLITE_PATH（paper_trading の専用 DB、デフォルト: data/paper_trading.db）
     - PAPER_FILL_MODE（paper_trading の fill 動作: instant|partial|never|reject, デフォルト: instant）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（AlertManager 用）
     - LOG_LEVEL（DEBUG/INFO/...）
     - MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔秒。デフォルト 60）
   - .env 自動読み込み:
     - .env と .env.local をプロジェクトルートから自動読み込み（既存 OS 環境変数は保護）
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込みを無効化

使い方（主要スクリプト）
- 監視ループを起動（本番監視）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL で間隔を秒単位で上書き可能（例: MONITOR_POLL_INTERVAL=30）
  - 監視は Settings.sqlite_path（data/monitoring.db など）を使用（run_monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を参照）
  - 停止方法: Ctrl+C またはプロジェクトルートの data/stop_requested.flag を作成するとループが検知して終了
- 実行エンジンを起動（発注処理）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録する（本番 DB と完全分離）
  - run_execution は data/stop_requested.flag を検知するとエンジン停止
  - 実行中は PID を data/execution.pid に書き込む（監視が生存確認に使う）
- Streamlit ダッシュボード起動
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション: --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
  - 簡易の Pass/Fail 判定（稼働率、注文成功率、送信率、P95 レイテンシ等）
- AI 機能呼び出し（プログラムから）
  - from kabusys.ai import score_news
  - score_news(conn, target_date, api_key="...")

停止／制御用ファイル（重要）
- data/stop_requested.flag: run_monitoring/run_execution が存在を検知して安全に停止
- data/execution.pid: 実行エンジンの PID（SystemMonitor がプロセス生存を確認）
- data/kill.flag: KillSwitch により書き込まれると ExecutionEngine に停止シグナルを送る（Execution 側はこのファイル存在を確認して起動拒否／停止）

ディレクトリ構成（主要ファイル／モジュール）
- src/kabusys/
  - __init__.py (バージョン等)
  - config.py (環境変数／Settings)
  - run_monitoring.py (監視ループ起動スクリプト)
  - run_execution.py (実行エンジン起動スクリプト)
  - monitoring/
    - monitoring_db.py (SQLite テーブル定義と永続化ラッパー MonitoringDB)
    - system_monitor.py (システム状態・データ鮮度)
    - trade_monitor.py (滞留注文・約定異常)
    - risk_monitor.py (ドローダウン / ポジション上限)
    - kill_switch.py (kill.flag 書き込み)
    - alert_manager.py (LINE への通知)
    - monitoring_engine.py (各 monitor を束ねる)
    - streamlit_dashboard.py (Streamlit UI)
  - execution/
    - order_repository.py (SQLite ベースの発注 DB)
    - order_manager.py (Order state machine の外向き API)
    - reconciler.py (再起動時の同期)
    - execution_engine.py (Engine のランタイム) — ※ファイル全体はここに含まれていないがリポジトリに存在
    - broker_factory.py / broker_api.py / broker の実装（Mock / 実ブローカー）
  - portfolio/
    - portfolio_builder.py (候補選定・重み計算)
    - position_sizing.py (株数決定・スケール調整)
    - risk_adjustment.py (セクター上限・レジーム乗数)
  - research/
    - factor_research.py (momentum/value/volatility)
    - feature_exploration.py (forward returns / IC / summary)
  - ai/
    - news_nlp.py (ニュースセンチメント集約・OpenAI 呼出し)
    - regime_detector.py (市場レジーム判定)
  - tools/
    - paper_verification_report.py (Paper Trading 検証レポート)

注意事項・運用上のポイント
- DB マイグレーション: monitoring_db.init_monitoring_db は冪等的にテーブル作成・簡単なカラム追加マイグレーションを行う
- 環境管理: config.py はプロジェクトルートの .env / .env.local を自動で読み込む。テスト時は自動読み込みを無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）
- セキュリティ: API キー類（OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）は決して公開リポジトリに置かないこと
- Paper Trading: paper_trading 環境は本番 DB と完全分離される設計（PAPER_TRADING_SQLITE_PATH を使う）
- フェイルセーフ: LLM・外部 API が失敗した場合でも動作を継続する設計（多くの箇所で安全なデフォルトを採用）

トラブルシューティング（よくある項目）
- DB が開けない（Streamlit 等）: monitoring プロセスが DB をロックしているため、読み取り専用 URI を使って開くか監視プロセスを止める
- kill.flag / stop_requested.flag が残っていて起動できない: data ディレクトリ内の該当ファイルを確認し、必要に応じて削除する
- OpenAI 呼び出しで 429 や 5xx が出る: news_nlp/regime_detector は指数バックオフを実装している。キー設定やレートに注意

ライセンス・貢献
- 本ドキュメントではライセンス情報を含めていません。実際の利用・配布はリポジトリに含まれる LICENSE を確認してください。
- バグ修正・機能追加の際は、テストと .env.example の更新をお願いします。

---

必要であれば、README に含めるコマンド例（systemd ユニット例、cron/PM2 例、docker-compose 例）や、より詳しい環境変数一覧・サンプル .env.example を追加で作成します。どの情報を優先して追加しますか？