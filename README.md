# KabuSys — 日本株自動売買システム

このリポジトリは日本株向けの自動売買フレームワーク「KabuSys」の一部実装です。
監視（Monitoring）、発注実行（Execution）、ポートフォリオ構築、リサーチ、AI（ニュースNLP / レジーム判定）などの機能を含みます。

以下はこのコードベースに対する README.md（日本語）です。

---

目次
- プロジェクト概要
- 主な機能
- 前提／依存
- セットアップ手順
- 使い方（実行方法）
- 主要環境変数（代表的なもの）
- ディレクトリ構成（概要）
- 追加のツール・ユーティリティ
- 運用上の注意

---

プロジェクト概要
- KabuSys は日本株自動売買システムのコンポーネント群です。  
  本リポジトリには、監視エンジン（MonitoringEngine）・実行エンジン（ExecutionEngine）・発注管理・リコンシリエーション・ポートフォリオ構築ロジック・リサーチ/ファクター計算・ニュースNLP（OpenAI）連携などが含まれます。
- 設計方針として「ビジネスロジックと永続化の分離」「ルックアヘッドバイアス防止」「外部 API 呼び出しのフェイルセーフ化」を重視しています。

主な機能
- System Monitor
  - CPU / メモリ / ディスク使用率の定期ログ取得
  - Execution プロセス PID チェック、データ鮮度チェック（DuckDB の prices_daily 参照）
  - SQLite に system_status を永続化
- Trade Monitor
  - 滞留（stale）注文検出、約定価格の異常検出（異常時は risk_logs に記録）
- Risk Monitor
  - ドローダウン監視（ハイウォーターマーク管理）、ポジション上限監視
  - 異常時に risk_logs を追加・dashboard を更新
- Kill Switch / Alert Manager
  - 条件に応じて data/kill.flag を書き込み、ExecutionEngine に停止指示を出す
  - LINE Messaging API による通知（クールダウン管理あり）
- MonitoringEngine
  - 上記モニタ群のポーリング束ね（テスト用 run_once / 本番用 run）
- ExecutionEngine（起動スクリプト群）
  - 発注処理、ブラウザ／API によるブローカー操作は BrokerClientFactory を介して抽象化
  - paper_trading 環境では MockBrokerClient を使用し DB を分離（data/paper_trading.db）
  - リコンシリエーション（再起動時の同期）
- Portfolio
  - 候補選定、重み計算（等金額／スコア加重）、ポジションサイズ計算、セクター制約、レジーム乗数
- Research
  - Momentum / Volatility / Value 等のファクター計算（DuckDB 利用）
  - 将来リターン計算、IC 計算、ファクター統計
- AI
  - news_nlp: raw_news を OpenAI（gpt-4o-mini）に送り銘柄ごとのセンチメントを ai_scores に書き込み
  - regime_detector: ETF(1321) の MA200 とマクロ記事の LLM センチメントを合成して市場レジームを判定
- ユーティリティ
  - process priority / cpu affinity 設定ユーティリティ
  - streamlit ベースの監視ダッシュボード
  - paper_trading の検証レポート生成スクリプト

前提 / 依存（代表的）
- Python 3.10 以上（型注釈の | 演算子などを使用）
- ライブラリ（一例）:
  - duckdb
  - psutil
  - openai
  - requests
  - streamlit
- SQLite（標準ライブラリ sqlite3 を使用）

セットアップ手順（開発環境）
1. リポジトリをクローンしてワークディレクトリへ移動
2. Python 仮想環境を作る（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows では .venv\Scripts\activate）
3. 必要パッケージをインストール
   - 例:
     pip install duckdb psutil openai requests streamlit
   - 実運用では requirements.txt を用意して pip install -r requirements.txt を推奨
4. 環境変数 / .env を準備
   - リポジトリルートに .env または .env.local を置くと自動ロードされます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）
   - 必須の環境変数（抜粋）:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - OPENAI_API_KEY（AI 機能を利用する場合）
     - KABUSYS_ENV（development|paper_trading|live、デフォルト: development）
     - 他: DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH / LINE 系など（後述）
5. データディレクトリ作成
   - data ディレクトリを作成（DB ファイルや PID / flag ファイルがここに置かれます）
   - 例: mkdir -p data

使い方（起動方法・主要コマンド）
- 実行スクリプトは src/kabusys 以下に配置されています。パッケージとして実行するか、直接スクリプトを起動できます。

1) 監視ループの起動（Monitoring）
- 説明: SystemMonitor をポーリングして監視ログを SQLite に記録します。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で指定できます（デフォルト 60 秒）。Monitoring は環境にかかわらず本番 sqlite_path を使用します（run_monitoring.py の仕様）。
- 実行例:
  - python -m kabusys.run_monitoring
  - または python src/kabusys/run_monitoring.py
- 補足:
  - 停止フラグファイル data/stop_requested.flag が存在するとループを終了します。
  - プロセス優先度を High にセットします（set_process_priority）。

2) ExecutionEngine の起動（発注エンジン）
- 説明: 発注を行うエンジンを起動します。KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、data/paper_trading.db を用います（本番 DB と分離）。
- 実行例:
  - python -m kabusys.run_execution
  - または python src/kabusys/run_execution.py
- 補足:
  - 起動時に data/stop_requested.flag が既にある場合は起動しません。
  - 実行中、stop フラグを作成するとエンジンを停止します。
  - プロセス PID を data/execution.pid に書きます。

3) streamlit ダッシュボード（監視用可視化）
- 説明: SQLite の監視 DB を参照して Web ダッシュボードを表示します。
- 実行例:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- 補足:
  - DB は読み取り専用で開きます（URI モード）。MonitoringEngine が動いていないとデータが無いことがあります。

4) Paper Trading 検証レポート生成ツール
- スクリプト: kabusys.tools.paper_verification_report
- 使用例:
  - python -m kabusys.tools.paper_verification_report
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで SQLite ファイルを指定できます（環境変数 PAPER_TRADING_SQLITE_PATH でも OK）
- 判定基準（概要）:
  - 稼働率 >= 99.0%
  - 注文成功率 (Filled/Created) >= 90.0%
  - 送信率 (Sent/Created) >= 95.0%
  - P95 レイテンシ <= 200 ms

5) AI 関連
- news_nlp.score_news / regime_detector.score_regime は OpenAI API キーが必要です（OPENAI_API_KEY 環境変数または引数で指定）。
- 使用されるモデルは gpt-4o-mini（コード内定義）。ネットワークや API の一時エラーはリトライ処理がありますが、API キー未設定の際は ValueError を発生させます。

主要な環境変数（代表的）
- KABUSYS_ENV: development | paper_trading | live（default: development）
  - paper_trading の場合、Execution は paper_sqlite_path を使用して本番 DB と分離します。
  - ただし run_monitoring は環境にかかわらず settings.sqlite_path（＝監視用 DB）を使用します（設計上の仕様）。
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を利用する場合）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 SQLite ファイルパス（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の約定ルール（instant | partial | never | reject、default: instant）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring および MonitoringEngine の間隔制御に利用）
- PID_FILE_PATH / KILL_FLAG_PATH: PID / kill.flag のパス（default data/execution.pid, data/kill.flag）
- LOG_LEVEL: ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知に用いる情報（未設定なら通知は送らない）

ディレクトリ構成（概要）
- src/kabusys/
  - __init__.py — パッケージ定義
  - config.py — 環境変数 / .env ロードと Settings クラス
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト
  - ai/
    - news_nlp.py — ニュース NLP（OpenAI）連携と ai_scores 書き込み
    - regime_detector.py — マクロ + ETF MA200 を合成してレジーム判定
  - monitoring/
    - monitoring_db.py — SQLite モニタログ永続化層（テーブル初期化・CRUD）
    - system_monitor.py — CPU/メモリ/ディスク・データ鮮度・プロセス監視
    - trade_monitor.py — 注文滞留・約定異常検出
    - risk_monitor.py — ドローダウン / ポジション上限監視
    - kill_switch.py — kill.flag の発行 / 管理
    - alert_manager.py — LINE への通知（プッシュ）
    - monitoring_engine.py — モニタ群を束ねるランナー
    - streamlit_dashboard.py — Streamlit ダッシュボード
  - execution/
    - order_manager.py — 発注状態機械（OrderManager）
    - reconciler.py — 再起動時の同期処理
    - （その他：broker_factory, execution_engine, order_repository 等が存在）
  - portfolio/
    - portfolio_builder.py — 候補選定、重み計算
    - position_sizing.py — 株数決定・投下資金制限・単元株丸め
    - risk_adjustment.py — セクターキャップ、レジーム乗数
  - research/
    - factor_research.py — Momentum/Volatility/Value 等のファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン計算、IC、統計サマリー
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成ツール
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

追加のツール・ユーティリティ
- monitoring_db.init_monitoring_db(conn): 監視用 SQLite のテーブルを作成（冪等）
- MonitoringDB クラス: system_status / trade_logs / positions / risk_logs / dashboard の読み書き API を提供
- portfolio / research の関数群は DuckDB / メモリ計算中心で副作用無しの純粋関数として設計
- streamlit_dashboard: 監視情報を簡易可視化する軽量ダッシュボード

運用上の注意（抜粋）
- .env 自動ロード:
  - プロジェクトルート（.git または pyproject.toml を基準）を検出できれば .env / .env.local を自動で読み込みます。OS 環境変数が優先されます。自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Monitoring と Execution の DB は運用上分離することを推奨します（paper_trading 用の分離あり）。
- OpenAI 連携は API キーとコストが必要です。API 呼び出しは外部サービス依存のため失敗時はフェイルセーフ（0.0 でフォールバック等）になっていますが、運用時はレート制限やコストに注意してください。
- stop/kill フラグ:
  - data/stop_requested.flag: run_monitoring/run_execution がチェックする停止フラグ（手動で作成した場合は停止されます）
  - data/kill.flag: KillSwitch が書き込むことで ExecutionEngine に停止指示（監視→実行の安全停止）を出します
- PID ファイルの stale 検出: SystemMonitor は execution.pid を参照して PID 生存確認を行い stale な PID ファイルを削除します。

最後に
- 本ドキュメントはコードをベースにしたサマリです。実運用・開発時はソースを参照しつつ、.env.example（存在する場合）やテスト環境での動作確認を行ってください。
- 追加で README に含めたい内容（例: requirements.txt、CI/CD 手順、デプロイ手順、テスト実行方法）があれば教えてください。必要に応じて追記します。