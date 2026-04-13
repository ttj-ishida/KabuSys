# KabuSys — README (日本語)

概要
- KabuSys は日本株の自動売買および研究・監視ツール群を含む小規模なプロジェクトです。
- 主な目的は戦略の研究（ファクター計算、特徴量解析）、ポートフォリオ構築ロジック、実行エンジン（発注／再同期）、監視・アラート、Paper Trading 検証などを提供することです。
- コードは純粋関数／モジュール化を重視しており、DuckDB（時系列ファイナンシャルデータ）や SQLite（監視・トレードログ）をデータストアに利用します。OpenAI（LLM）を使ったニュースの NLP スコアリングやレジーム判定機能も含みます。

機能一覧
- 実行関連
  - ExecutionEngine（起動スクリプト: run_execution.py）
  - ブローカークライアントの抽象化（実取引 / モックの切替）
  - OrderManager / OrderRepository / Reconciler による発注・再同期機能
- 監視関連
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine（run_monitoring.py）
  - SQLite ベースの監視 DB（monitoring_db.py）と Streamlit ダッシュボード
  - LINE へのプッシュ通知機能（AlertManager）
  - KillSwitch（リスクトリガーで Execution を停止するためのフラグファイル制御）
- ポートフォリオ構築
  - 候補選定、重み付け（等分/スコア加重）、ポジションサイズ計算、セクター上限・レジーム乗数
- 研究（Research）
  - ファクター計算（momentum/value/volatility）
  - 将来リターン・IC（Information Coefficient）・統計サマリ
- AI（OpenAI）
  - ニュース NLP による銘柄別センチメントスコアリング（news_nlp）
  - マクロ + ETF を組み合わせた市場レジーム判定（regime_detector）
- ツール
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）
- ユーティリティ
  - 環境変数 / .env ロード機能（config.py）
  - プロセス優先度 / CPU affinity 設定ユーティリティ（utils/process_priority.py）

セットアップ手順（開発マシン向けの簡易手順）
1. Python 環境
   - Python 3.9+ を推奨（プロジェクトの Python バージョンに合わせてください）
   - 仮想環境を作ることを推奨:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - 最低限必要になる主要パッケージ（例）:
     - pip install duckdb psutil requests streamlit openai
   - その他テスト用・補助ライブラリは個別に追加してください。
   - （プロダクションでは requirements.txt / poetry 等で管理することを推奨）

3. 環境変数 / .env
   - プロジェクトルートに .env / .env.local を置くことで自動読み込みされます（config.py による自動ロード。既存の OS 環境変数は保護されます）。
   - 自動ロードを無効にする場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   - 重要な環境変数（一部・デフォルト）:
     - KABUSYS_ENV = development | paper_trading | live  （デフォルト: development）
     - OPENAI_API_KEY （AI 機能を使う場合 必須）
     - JQUANTS_REFRESH_TOKEN（利用する場合）
     - KABU_API_PASSWORD（実ブローカー連携時）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 向け DB: data/paper_trading.db）
     - PAPER_FILL_MODE（paper_trading の約定挙動: instant|partial|never|reject）デフォルト: instant
     - PID_FILE_PATH（デフォルト: data/execution.pid）
     - KILL_FLAG_PATH（デフォルト: data/kill.flag）
     - LOG_LEVEL（DEBUG|INFO|WARNING|ERROR|CRITICAL）デフォルト: INFO
     - MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔秒、デフォルト: 60）

4. データベース初期化
   - monitoring 用の SQLite は起動スクリプト（run_monitoring / run_execution）で必要テーブルを自動作成します（init_monitoring_db）。
   - DuckDB のテーブル（prices_daily / raw_financials / raw_news 等）は外部 ETL やデータ取り込み工程で用意してください。

使い方（主要コマンド例）
- 監視ループ起動（SystemMonitor を定期実行）
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で指定可能（デフォルト 60 秒）。
  - 実行:
    - python -m kabusys.run_monitoring
  - 例: 30 秒間隔で実行:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- 実行エンジン起動（ExecutionEngine）
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して PAPER_TRADING_SQLITE_PATH に記録します（本番 DB と分離）。
  - 実行:
    - python -m kabusys.run_execution
  - 例（Paper Trading）:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- Streamlit ダッシュボード（監視 UI）
  - 起動:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 既存 DB を読み取り専用で開くため、MonitoringEngine が monitoring.db を作成している必要があります。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を指定する場合:
    - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

- AI / レジーム検出 / ニューススコアリング（プログラム的利用）
  - 関数として提供されています（例）:
    - from kabusys.ai.news_nlp import score_news
    - from kabusys.ai.regime_detector import score_regime
  - OPENAI_API_KEY が必要です。CLI ラッパーはありませんので、スクリプトやジョブでインポートして呼び出してください。

注意点・運用上のヒント
- .env の自動ロードは config.py でプロジェクトルート（.git または pyproject.toml）を基準に行われます。テスト等で無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- run_execution は paper_trading 環境と live 環境で SQLite の切替を自動化しています。paper_trading では PAPER_TRADING_SQLITE_PATH を使い、本番 DB と分離されます。
- run_monitoring は常に本番用の sqlite_path（Settings.sqlite_path）を使います（監視は本番 DB で行われる想定）。
- OpenAI を使う処理（news_nlp, regime_detector）は API エラー時にフォールバック動作を実装しており、過度に失敗してもプロセス全体を止めない設計です（ログに WARN/ERROR を出力します）。
- process_priority ユーティリティにより起動時にプロセス優先度を設定しますが、システムによっては権限不足で失敗する場合があります（警告でスキップ）。

主要ファイル / ディレクトリ構成
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / .env の読み込みと Settings クラス
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート CLI スクリプト
  - utils/
    - __init__.py
    - process_priority.py     — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - __init__.py
    - monitoring_db.py       — SQLite による永続化 API（テーブル作成・CRUD）
    - system_monitor.py      — CPU/メモリ/ディスク/データ鮮度/プロセス監視
    - trade_monitor.py       — 注文滞留・約定異常の検出
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - kill_switch.py         — kill.flag を使った停止シグナル出力
    - monitoring_engine.py   — 各 Monitor をまとめて定期実行するエンジン
    - alert_manager.py       — LINE 通知（クールダウン管理）
    - streamlit_dashboard.py — Streamlit ダッシュボード（監視 UI）
  - execution/
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - ...                    — ブローカー系抽象・エンジン関連（省略ファイルあり）
  - portfolio/
    - __init__.py
    - portfolio_builder.py   — 候補選定・重み計算
    - position_sizing.py     — 発注株数計算・集約キャップ調整
    - risk_adjustment.py     — セクターキャップ・レジーム乗数
  - research/
    - __init__.py
    - factor_research.py     — momentum/value/volatility 等のファクター計算
    - feature_exploration.py — 将来リターン・IC・統計サマリ
  - ai/
    - __init__.py
    - news_nlp.py            — ニュースを LLM でスコア化して ai_scores に書き込む
    - regime_detector.py     — ETF + マクロニュースを用いたレジーム判定
  - data/ (想定)
    - kabusys.duckdb         — DuckDB データベース（prices_daily 等）
    - monitoring.db          — SQLite 監視 DB
    - paper_trading.db       — SQLite Paper Trading DB（paper_trading 用）

ライセンス・貢献
- 本リポジトリのライセンスや貢献ガイドラインはプロジェクトルートの LICENSE / CONTRIBUTING.md を参照してください（存在しない場合はプロジェクトオーナーに確認してください）。

トラブルシューティング（よくある質問）
- モニタリング DB が作られない / Streamlit が DB を開けない:
  - run_monitoring または run_execution を実行して init_monitoring_db が走ることを確認してください。
- OpenAI 呼び出しで Key エラー:
  - OPENAI_API_KEY を環境変数に設定するか、関数呼び出し時に api_key 引数で渡してください。
- Paper Trading 用に DB を完全に分離したい:
  - KABUSYS_ENV=paper_trading をセットし、PAPER_TRADING_SQLITE_PATH を適切に指定して実行してください。

さらに詳しいドキュメント
- 各モジュールのドックストリングに設計意図や詳細な実装メモが含まれています。個別機能の詳細は該当モジュール（例: kabusys/research/factor_research.py, kabusys/ai/news_nlp.py など）を参照してください。

以上。必要があれば、README に含める具体的な環境変数一覧やサンプル .env、あるいは起動スクリプトの systemd ユニット例などを追記します。どの情報を優先して追加しますか？