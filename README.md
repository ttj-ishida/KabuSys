KabuSys — 日本株自動売買プラットフォーム（README）
=================================================

概要
----
KabuSys は日本株向けの自動売買システムのコンポーネント群です。本リポジトリには以下の主要機能が含まれます。

- 注文実行エンジン（ExecutionEngine）および発注管理（OrderManager / Reconciler）
- 監視サブシステム（SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch / AlertManager）
- ポートフォリオ構築ユーティリティ（候補選定・重み付け・ポジションサイズ計算・セクター制限）
- リサーチ用モジュール（ファクター計算・特徴量探索）
- AI 統合（ニュース NLP によるセンチメント集計・市場レジーム判定）
- 運用ツール（Paper Trading 検証レポート、Streamlit ダッシュボード）

設計上のポイント
- DB: DuckDB（価格などの時系列データ）と SQLite（監視ログ・発注ログ）を併用
- Paper Trading は本番 DB と分離（data/paper_trading.db を利用）
- LLM（OpenAI）呼び出しは冪等・フェイルセーフに設計（リトライ / フォールバック）
- 実運用向けにプロセス優先度設定や kill.flag による安全停止機構を備える

主な機能一覧
----------------
- 実行（run_execution.py）
  - ブローカークライアントを介した発注、リスク管理、再帰的リコンシリエーション
  - KABUSYS_ENV=paper_trading でモックブローカーと paper_trading 用 DB を使用

- 監視（run_monitoring.py / MonitoringEngine）
  - システムリソース・データ鮮度・滞留注文・約定異常・ドローダウン等の監視
  - LINE を用いたアラート通知（AlertManager）
  - KillSwitch による自動停止指示（data/kill.flag）

- ポートフォリオ（kabusys.portfolio）
  - シグナルから候補選定、等分/スコア加重、セクター制限、ポジションサイズ算出

- リサーチ（kabusys.research）
  - momentum/value/volatility ファクター計算、将来リターン計算、IC 計測、統計サマリ

- AI（kabusys.ai）
  - news_nlp.score_news: ニュース記事を LLM でスコア化して ai_scores に書き込み
  - regime_detector.score_regime: ETF（1321）MA とマクロニュースでレジーム判定

- ツール
  - paper_verification_report: Paper Trading の検証レポート生成
  - streamlit_dashboard: 監視ダッシュボード（Streamlit）

セットアップ手順
----------------
前提
- Python 3.10 以上（typing の | 演算子などを使用）
- Git クローン後、プロジェクトルートに移動

1) 仮想環境作成（任意）
- python -m venv .venv
- source .venv/bin/activate  (Linux/macOS) または .venv\Scripts\activate (Windows)

2) 依存パッケージをインストール
- pip install -U pip
- pip install duckdb psutil openai requests streamlit

（本リポジトリに requirements.txt があれば pip install -r requirements.txt を推奨）

3) パッケージを開発モードでインストール（便利）
- pip install -e .

4) data ディレクトリ作成（DBファイルやフラグファイルを置く）
- mkdir -p data

環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN — J-Quants API トークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト http://localhost:18080/kabusapi）
- OPENAI_API_KEY — OpenAI API キー（AI 機能を使う場合）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — LINE 通知を使用する場合
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE — paper_trading の約定モード（instant|partial|never|reject、デフォルト instant）
- PID_FILE_PATH — ExecutionEngine の PID ファイル位置（デフォルト data/execution.pid）
- KILL_FLAG_PATH — kill.flag のパス（デフォルト data/kill.flag）
- KABUSYS_ENV — 実行環境（development | paper_trading | live、デフォルト development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒、デフォルト 60）。1 未満や不正値は無視してデフォルトにフォールバック。

例: .env（プロジェクトルート）
- JQUANTS_REFRESH_TOKEN=...
- KABU_API_PASSWORD=...
- OPENAI_API_KEY=...
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
- KABUSYS_ENV=development
- LOG_LEVEL=INFO

使い方（起動例 / コマンド）
--------------------------

注意: package をインストールしない場合は PYTHONPATH=src を指定して -m 実行してください。
例: PYTHONPATH=src python -m kabusys.run_monitoring

1) 監視ループ（Monitoring）
- 簡単実行（src を PYTHONPATH に含める）
  - PYTHONPATH=src python -m kabusys.run_monitoring
- 環境変数でポーリング間隔を変更:
  - MONITOR_POLL_INTERVAL=30 PYTHONPATH=src python -m kabusys.run_monitoring

実装ノート:
- 監視は必ず本番の sqlite_path を使用（KABUSYS_ENV に依存せず監視 DB は本番 DB を参照）
- data/stop_requested.flag を配置するとループが安全に終了します

2) 実行エンジン（ExecutionEngine）
- 本番/開発/ペーパートレードの切替は KABUSYS_ENV で制御
- Paper Trading（モックブローカー + 専用 DB）:
  - KABUSYS_ENV=paper_trading PYTHONPATH=src python -m kabusys.run_execution
- 本番/開発:
  - KABUSYS_ENV=live PYTHONPATH=src python -m kabusys.run_execution

実行時の挙動:
- 起動時に data/stop_requested.flag が存在する場合は起動せず終了
- 実行中に data/stop_requested.flag が作成されると安全に停止処理を行う
- pid ファイルは data/execution.pid（Settings.pid_file_path）に書き込まれます

3) Streamlit ダッシュボード（監視可視化）
- streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- 既存の monitoring.db を read-only モードで開く（DB が存在しない場合はエラー）

4) Paper Trading 検証レポート
- python -m kabusys.tools.paper_verification_report
- 期間指定:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- DB 指定:
  - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

5) AI 機能
- ニュース NLP スコアリング:
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - DuckDB 接続（kabusys.ai.score_news は OpenAI API キーが必要）
- レジーム判定:
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
- API キーは引数で渡すか OPENAI_API_KEY 環境変数を設定

運用メモ / 実装の注意点
---------------------
- Paper Trading は本番 DB とファイル分離されています（PAPER_TRADING_SQLITE_PATH）
- .env 自動読み込み:
  - プロジェクトルート（.git / pyproject.toml）を基準に .env と .env.local を自動で読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）
- プロセス優先度:
  - 起動時 set_process_priority("high") を呼んで高優先度に設定しようとしますが、権限不足などで失敗しても警告ログのみで継続します
- Kill Switch:
  - RiskMonitor が閾値を超えた場合、KillSwitch が data/kill.flag を作成して ExecutionEngine に停止指示を出します（ExecutionEngine は起動時にオプションでこれを参照・クリアできます）
- DB マイグレーション:
  - monitoring_db.init_monitoring_db は既存 DB に対して安全にカラム追加を行います（冪等）

ディレクトリ構成（主要ファイル）
------------------------------
（src 以下を想定）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor 起動スクリプト

  - ai/
    - news_nlp.py            — ニュース NLP スコアリング（OpenAI 統合）
    - regime_detector.py     — 市場レジーム判定

  - execution/
    - order_manager.py
    - reconciler.py
    - ...                    — ブローカー連携、OrderRepository 等（部分省略）

  - monitoring/
    - monitoring_db.py       — monitoring 用 SQLite 層（init / MonitoringDB）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
    - streamlit_dashboard.py

  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py

  - research/
    - factor_research.py
    - feature_exploration.py

  - tools/
    - paper_verification_report.py

  - utils/
    - process_priority.py

運用上の推奨
-----------
- 本番環境では KABUSYS_ENV=live を使用し、適切な権限でプロセス優先度設定を許可してください。
- OpenAI 呼び出し（news_nlp / regime_detector）は API コストとレイテンシを考慮して運用してください（API キーは安全に管理）。
- 監視ログ（data/monitoring.db）を定期的にバックアップしてください。
- Paper Trading を本番と混同しないように DB ファイル名/パスを明確に分離してください。

開発 / 貢献
------------
- バグ報告・機能追加は Issue/PR へお願いします。
- 新しい DB スキーマ変更は init_monitoring_db にマイグレーション処理を追加してください（既存 DB と互換性を保つこと）。

ライセンス
---------
- 本リポジトリにはライセンスファイルが付属していない場合があります。商用利用や再配布を行う場合は、プロジェクト固有のライセンス情報を確認してください。

付録: よく使う実行例
-------------------
- 監視（デフォルト 60s 間隔）
  - MONITOR_POLL_INTERVAL=60 PYTHONPATH=src python -m kabusys.run_monitoring

- ExecutionEngine（ペーパートレード）
  - KABUSYS_ENV=paper_trading PYTHONPATH=src python -m kabusys.run_execution

- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

最後に
-----
この README はリポジトリ内のコード（docstring と Settings）を基に作成しています。実行前に .env を正しく設定し、必要な DB ファイルを用意してください。必要であれば README に追記する内容（より詳細な運用手順やデプロイ手順、CI/CD、テスト方法など）を教えてください。